from typing import List, Dict, Tuple
from detect_secrets.core.plugins import initialize
from detect_secrets.settings import get_settings
import io
import math
import re


def shannon_entropy(data: str) -> float:
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    for x in set(data):
        p_x = data.count(x) / length
        entropy -= p_x * math.log2(p_x)
    return entropy


# Build-safe patterns that should NOT be detected as secrets
BUILD_SAFE_PATTERNS = [
    # File paths and libraries
    r'^/[a-zA-Z0-9/_.-]+\.(so|dll|exe|jar|whl|framework|dylib)(\.\d+)*$',
    r'^[a-zA-Z]:\\[a-zA-Z0-9\\/_. -]+\.(exe|dll|jar|whl)$',
    r'^[a-zA-Z]:\\[a-zA-Z0-9\\/_. -]+\\[a-zA-Z0-9\\/_. -]+$',  # Windows paths
    r'^target/[a-zA-Z0-9/_.-]+\.(exe|jar|whl)$',
    r'^build/[a-zA-Z0-9/_.-]+\.(exe|jar|whl)$',

    # Package files and version identifiers
    r'^[a-zA-Z0-9._-]+-\d+\.\d+\.\d+.*\.(whl|jar|tar\.gz|tgz|zip)$',
    r'^[a-zA-Z0-9._-]+@\d+\.\d+\.\d+$',
    r'^[a-zA-Z0-9._-]+:\d+\.\d+\.\d+$',
    r'^[a-zA-Z0-9._-]+-\d+\.\d+\.\d+(-[a-zA-Z0-9._-]+)*$',

    # Checksums and hashes
    r'^(sha256|sha1|md5):[a-f0-9]+$',
    r'^[a-f0-9]{32}$',  # MD5
    r'^[a-f0-9]{40}$',  # SHA1/Git commit
    r'^[a-f0-9]{64}$',  # SHA256

    # UUIDs
    r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',

    # URLs and repository paths
    r'^https?://[a-zA-Z0-9._/-]+$',
    r'^git@[a-zA-Z0-9._-]+:[a-zA-Z0-9._/-]+\.git$',

    # Docker and container identifiers
    r'^[a-zA-Z0-9._/-]+:[a-zA-Z0-9._-]+$',  # Docker image tags
    r'^(docker\.io/|registry\.hub\.docker\.com/)[a-zA-Z0-9._/-]+$',

    # Build tool files
    r'^(requirements|package-lock|Cargo|pom)\.(txt|json|toml|xml)$',

    # Maven coordinates
    r'^[a-zA-Z0-9._-]+:[a-zA-Z0-9._-]+:[a-zA-Z0-9._-]+$',

    # Version control references
    r'^(refs/heads/|origin/|tag: )[a-zA-Z0-9._/-]+$',

    # Common build output patterns
    r'^Successfully (built|tagged|installed) [a-zA-Z0-9._-]+$',
    r'^(Downloading|Collecting|Building|Compiling|Linking) [a-zA-Z0-9._/-]+$',
    r'^(FROM|COPY|RUN|EXPOSE) [a-zA-Z0-9._/: -]+$',

    # MSBuild and Visual Studio specific patterns
    r'^[a-zA-Z0-9._-]+\.vcxproj$',  # Visual Studio project files
    r'^[a-zA-Z0-9._-]+\.sln$',      # Visual Studio solution files
    r'^[a-zA-Z0-9._-]+\.lib$',      # Library files
    r'^[a-zA-Z0-9._-]+\.pdb$',      # Program database files
    r'^[a-zA-Z0-9._-]+\.res$',      # Resource files
    r'^[a-zA-Z0-9._-]+\.obj$',      # Object files
    r'^[a-zA-Z0-9._-]+\.tlog$',     # Build log files
    r'^vc\d+\.pdb$',                # Visual C++ compiler database
    r'^\d+\.\d+\.\d+\+[a-f0-9]+$', # Version numbers with commit hash
    r'^build-session-\d{8}-\d{6}-[a-z0-9]+$',  # Build session IDs
    r'^req-[a-z0-9]+-[a-z0-9]+$',  # Request IDs

    # MSBuild task names and build steps
    r'^[A-Z][a-zA-Z]+:$',          # MSBuild task names ending with colon
    r'^"[A-Z][a-zA-Z]+"$',         # Quoted MSBuild task names
    r'^\([A-Z/_]+\)$',             # Compiler/linker flags in parentheses
    r'^/[A-Z]+:[A-Z0-9_]+$',       # Compiler flags like /MACHINE:X64

    # Windows system libraries
    r'^[a-z0-9]+\.lib$',           # System library files
    r'^Multi-threaded$',           # Runtime library names
    r'^Optimization:$',            # Build setting labels
]

# Compile patterns for performance
COMPILED_BUILD_SAFE_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in BUILD_SAFE_PATTERNS]


def is_build_safe_pattern(s: str) -> bool:
    """Check if a string matches any build-safe pattern."""
    s = s.strip()
    for pattern in COMPILED_BUILD_SAFE_PATTERNS:
        if pattern.match(s):
            return True
    return False


def has_build_context_keywords(line: str) -> bool:
    """Check if the line contains build-related context keywords."""
    build_keywords = [
        'building', 'built', 'compile', 'compiling', 'linking', 'installing', 'installed',
        'downloading', 'downloaded', 'collecting', 'successfully', 'checksum', 'digest',
        'from central', 'maven', 'npm', 'pip', 'cargo', 'docker', 'image', 'tag',
        'commit', 'branch', 'merge', 'refs/', 'origin/', 'target/', 'build/',
        'requirements.txt', 'package.json', 'pom.xml', 'cargo.toml',
        'container id', 'build id', 'session:', 'request id', 'trace id',
        'from node', 'copy', 'run npm', 'expose', 'head is now', 'image id',
        # MSBuild and Visual Studio specific keywords
        'msbuild', 'visual studio', 'vcxproj', 'solution', 'project', 'clcompile',
        'link:', 'resourcecompile', 'preparefor', 'initialize', 'finalize',
        'validate', 'configuration', 'platform toolset', 'windows sdk',
        'msvc', 'cl.exe', 'link.exe', 'rc.exe', 'generating code', 'finished generating',
        'creating directory', 'deleting file', 'touching', 'because', 'was specified',
        'build engine', 'copyright', 'microsoft corporation', 'all rights reserved',
        'build started', 'build succeeded', 'warning(s)', 'error(s)', 'time elapsed',
        'optimization', 'runtime library', 'security check', 'function-level linking',
        'floating point', 'exception handling', 'buffer security', 'control flow',
        'generate debug', 'comdat folding', 'references', 'link time code',
        'subsystem', 'target machine', 'data execution', 'randomized base',
        'dependencies resolved', 'system library', 'build artifacts',
        'executable', 'debug symbols', 'import library', 'resources',
        'compiler database', 'build environment', 'build machine', 'build user',
        'build timestamp', 'build session', 'build request', 'performance metrics',
        'compilation time', 'linking time', 'resource compilation', 'cpu usage',
        'memory usage', 'disk i/o', 'network i/o', 'file checksums'
    ]

    line_lower = line.lower()
    return any(keyword in line_lower for keyword in build_keywords)


def is_password_like(s: str) -> bool:
    # At least 12 chars, contains 3 of 4: upper, lower, digit, special, and entropy > 3.5
    if len(s) < 12:
        return False
    classes = 0
    if re.search(r"[A-Z]", s):
        classes += 1
    if re.search(r"[a-z]", s):
        classes += 1
    if re.search(r"\d", s):
        classes += 1
    if re.search(r"[^A-Za-z0-9]", s):
        classes += 1
    if classes < 3:
        return False
    if shannon_entropy(s) < 3.5:
        return False
    return True


def find_password_like_strings(raw_content: str) -> List[dict]:
    findings = []
    for i, line in enumerate(raw_content.splitlines(), 1):
        # Tokenize by whitespace and quotes
        tokens = re.findall(r"\b\w[\w!@#$%^&*()_+\-=\[\]{};:\'\",.<>/?`~|]+\b", line)
        for token in tokens:
            if is_password_like(token):
                findings.append(
                    {
                        "RuleID": "PasswordLikeString",
                        "LineNumber": i,
                        "SecretType": "PasswordLikeString",
                        "SecretValue": token,
                    }
                )
    return findings


def is_password_like_loose(s: str) -> bool:
    """
    Improved password-like detection with build context awareness.

    Reduces false positives by:
    1. Checking against build-safe patterns first
    2. Using balanced entropy and complexity thresholds
    3. Adding context-aware exclusions for build artifacts
    4. Maintaining detection of actual secrets
    """
    # Quick length check
    if len(s) < 12:
        return False

    # Check if it matches any build-safe pattern
    if is_build_safe_pattern(s):
        return False

    # Count character classes
    classes = 0
    if re.search(r"[A-Z]", s):
        classes += 1
    if re.search(r"[a-z]", s):
        classes += 1
    if re.search(r"\d", s):
        classes += 1
    if re.search(r"[^A-Za-z0-9]", s):
        classes += 1

    # Calculate entropy
    entropy = shannon_entropy(s)

    # Use balanced thresholds: require either high complexity OR high entropy
    # This allows detection of both complex passwords and high-entropy tokens
    high_complexity = classes >= 3
    high_entropy = entropy > 3.5
    medium_entropy = entropy > 3.0

    # Require either:
    # 1. High complexity (3+ classes) AND medium entropy (3.0+), OR
    # 2. High entropy (3.5+) regardless of complexity
    if not (high_entropy or (high_complexity and medium_entropy)):
        return False

    # Additional checks for common non-secret patterns

    # Skip if it's mostly repeating characters (but allow some repetition for real passwords)
    if len(set(s)) < len(s) * 0.4:  # Less than 40% unique characters
        return False

    # Skip if it looks like a file path (even if not caught by patterns)
    if '/' in s and (s.startswith('/') or '.' in s):
        return False

    # Skip if it looks like a Windows path
    if '\\' in s and (':' in s or s.count('\\') >= 2):
        return False

    # Skip if it looks like a simple URL without credentials
    if s.startswith(('http://', 'https://', 'ftp://')) and '://' in s and '@' not in s:
        return False

    # Skip git URLs without credentials
    if s.startswith('git@') and ':' in s and '/' in s and not any(c in s for c in ['password', 'pwd', 'secret']):
        return False

    # Skip if it looks like a version identifier
    if re.match(r'^[a-zA-Z0-9._-]+-\d+\.\d+', s):
        return False

    # Skip if it looks like a checksum
    if ':' in s and re.match(r'^[a-zA-Z0-9]+:[a-f0-9]+$', s):
        return False

    # Skip if it looks like a git commit hash (40 hex chars)
    if re.match(r'^[a-f0-9]{40}$', s):
        return False

    # Skip if it looks like a long container/build ID (all lowercase alphanumeric)
    if len(s) > 30 and re.match(r'^[a-z0-9]+$', s):
        return False

    # Skip if it contains common file extensions
    if any(ext in s.lower() for ext in ['.json', '.xml', '.txt', '.jar', '.exe', '.dll', '.lib', '.pdb', '.obj', '.res', '.vcxproj', '.sln']):
        return False

    # Skip MSBuild task names and build steps
    if s.endswith(':') and len(s) > 12 and s[:-1].isalpha():
        return False

    # Skip quoted strings that look like build task names
    if s.startswith('"') and s.endswith('"') and len(s) > 12:
        inner = s[1:-1]
        if inner.isalpha() or inner.replace(' ', '').isalpha():
            return False

    # Skip compiler/linker flags in parentheses
    if s.startswith('(') and s.endswith(')') and '/' in s:
        return False

    # Skip system library names
    if s.lower().endswith('.lib') and len(s) < 20:
        return False

    # Skip common build setting labels
    if s.endswith(':') and any(word in s.lower() for word in ['optimization', 'library', 'security', 'linking', 'point', 'handling', 'debug', 'folding', 'machine', 'execution', 'base']):
        return False

    return True


def find_custom_password_like_strings(raw_content: str) -> List[dict]:
    findings = []
    for i, line in enumerate(raw_content.splitlines(), 1):
        # Skip lines with build context keywords
        if has_build_context_keywords(line):
            continue

        # Skip lines that look like file paths
        line_stripped = line.strip()
        if (line_stripped.startswith('/') or
            (len(line_stripped) > 3 and line_stripped[1:3] == ':\\') or
            line_stripped.startswith('target/') or
            line_stripped.startswith('build/')):
            continue

        # Find any sequence of 12+ non-whitespace characters
        tokens = re.findall(r"\S{12,}", line)

        # Also extract potential passwords from connection strings and environment variables
        # Look for patterns like ://user:password@ or pwd=password or password=value  # pragma: allowlist secret
        connection_patterns = [
            r'://[^:]+:([^@]{12,})@',  # ://user:password@  # pragma: allowlist secret
            r'pwd=([^;\s]{12,})',      # pwd=password
            r'password=([^;\s&]{12,})', # password=value
            r'passwd=([^;\s&]{12,})',   # passwd=value
            r'API_KEY=([^;\s&]{12,})',  # API_KEY=value
            r'SECRET=([^;\s&]{12,})',   # SECRET=value
            r'TOKEN=([^;\s&]{12,})',    # TOKEN=value
        ]

        for pattern in connection_patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                if len(match) >= 12:
                    tokens.append(match)

        for token in tokens:
            if is_password_like_loose(token):
                findings.append(
                    {
                        "RuleID": "PasswordLikeString",
                        "LineNumber": i,
                        "SecretType": "PasswordLikeString",
                        "SecretValue": token,
                    }
                )
    return findings


def check_secrets(raw_content: str) -> List[dict]:
    """
    Scan an in-memory string for hard-coded secrets.
    Returns a list of findings, each with keys like RuleID, LineNumber, SecretType, and SecretValue.
    """
    settings = get_settings()

    # Ensure essential plugin CLASS NAMES are configured for instantiation.
    # These are added with default configurations if not already present in settings.
    # (e.g., loaded from a baseline file or user-defined config)
    essential_plugins_config = {
        "KeywordDetector": {},  # Default config is empty
        "Base64HighEntropyString": {"base64_limit": 4.5},  # Default from detect-secrets
        "HexHighEntropyString": {"hex_limit": 3.0},  # Default from detect-secrets
    }

    for class_name, config in essential_plugins_config.items():
        if class_name not in settings.plugins:
            settings.plugins[class_name] = config

    # Initialize ALL plugins that are now listed in settings.plugins
    # using their class names.
    active_plugin_classnames = list(settings.plugins.keys())
    plugins = []
    for classname in active_plugin_classnames:
        try:
            # from_plugin_classname uses the config from settings.plugins[classname]
            plugin_instance = initialize.from_plugin_classname(classname)
            plugins.append(plugin_instance)
        except TypeError:
            # Optionally log if a plugin classname in settings fails to initialize
            # For now, we'll just skip it if it's misconfigured beyond the defaults we ensure.
            # print(f"Warning: Could not initialize plugin {classname}")
            pass

    leaks = []
    seen = set()  # To avoid duplicate findings

    # Run detect-secrets plugins
    for i, line_content in enumerate(raw_content.splitlines(), 1):
        for plugin in plugins:
            try:
                results = plugin.analyze_line(
                    filename="in-memory", line=line_content, line_number=i
                )
                for secret in results:
                    # Create a unique key for the finding to avoid duplicates
                    finding_key = (i, secret.secret_value, secret.type)
                    if finding_key not in seen:
                        leaks.append(
                            {
                                "RuleID": secret.type,  # Or plugin.secret_type for consistency
                                "LineNumber": i,
                                "SecretType": secret.type,
                                "SecretValue": secret.secret_value,
                            }
                        )
                        seen.add(finding_key)
            except Exception as e:
                # print(f"Error analyzing line with plugin {plugin.__class__.__name__}: {e}")
                pass  # Continue with other plugins/lines

    # Add custom password-like string findings
    custom_findings = find_custom_password_like_strings(raw_content)
    for finding in custom_findings:
        finding_key = (
            finding["LineNumber"],
            finding["SecretValue"],
            finding["SecretType"],
        )
        if finding_key not in seen:
            leaks.append(finding)
            seen.add(finding_key)

    return leaks


def redact_secrets(content: str) -> Tuple[str, List[Dict]]:
    """
    Scan content for secrets and redact them with '[REDACTED]'.

    Args:
        content: The text content to scan and redact.

    Returns:
        A tuple containing:
        - The redacted content
        - A list of findings that were redacted
    """
    findings = check_secrets(content)
    redacted_content = content

    # Sort findings by line number and then by position within the line (if available)
    # to process from end to beginning to avoid affecting positions
    sorted_findings = sorted(
        findings, key=lambda x: (x["LineNumber"], -len(x["SecretValue"])), reverse=True
    )

    lines = redacted_content.splitlines(True)  # Keep line endings

    for finding in sorted_findings:
        line_num = finding["LineNumber"] - 1  # Convert to 0-indexed
        if 0 <= line_num < len(lines):
            secret_value = finding["SecretValue"]
            lines[line_num] = lines[line_num].replace(secret_value, "[REDACTED]")

    return "".join(lines), findings
