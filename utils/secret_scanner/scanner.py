from typing import List
from detect_secrets.core.plugins import initialize
from detect_secrets.settings import get_settings
import io
import math
import re


def shannon_entropy(data: str) -> float:
    if not data:
        return 0.0
    entropy = 0
    length = len(data)
    for x in set(data):
        p_x = data.count(x) / length
        entropy -= p_x * math.log2(p_x)
    return entropy


def is_password_like(s: str) -> bool:
    # At least 12 chars, contains 3 of 4: upper, lower, digit, special, and entropy > 3.5
    if len(s) < 12:
        return False
    classes = 0
    if re.search(r'[A-Z]', s):
        classes += 1
    if re.search(r'[a-z]', s):
        classes += 1
    if re.search(r'\d', s):
        classes += 1
    if re.search(r'[^A-Za-z0-9]', s):
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
        tokens = re.findall(r'\b\w[\w!@#$%^&*()_+\-=\[\]{};:\'\",.<>/?`~|]+\b', line)
        for token in tokens:
            if is_password_like(token):
                findings.append({
                    'RuleID': 'PasswordLikeString',
                    'LineNumber': i,
                    'SecretType': 'PasswordLikeString',
                    'SecretValue': token,
                })
    return findings


def is_password_like_loose(s: str) -> bool:
    if len(s) < 12:
        return False
    classes = 0
    if re.search(r'[A-Z]', s):
        classes += 1
    if re.search(r'[a-z]', s):
        classes += 1
    if re.search(r'\d', s):
        classes += 1
    if re.search(r'[^A-Za-z0-9]', s):
        classes += 1
    if classes >= 2 or shannon_entropy(s) > 3.0:
        return True
    return False


def find_custom_password_like_strings(raw_content: str) -> List[dict]:
    findings = []
    for i, line in enumerate(raw_content.splitlines(), 1):
        # Find any sequence of 12+ non-whitespace characters
        tokens = re.findall(r'\S{12,}', line)
        for token in tokens:
            if is_password_like_loose(token):
                findings.append({
                    'RuleID': 'PasswordLikeString',
                    'LineNumber': i,
                    'SecretType': 'PasswordLikeString',
                    'SecretValue': token,
                })
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
        'KeywordDetector': {},  # Default config is empty
        'Base64HighEntropyString': {'base64_limit': 4.5}, # Default from detect-secrets
        'HexHighEntropyString': {'hex_limit': 3.0}        # Default from detect-secrets
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
    seen = set() # To avoid duplicate findings

    # Run detect-secrets plugins
    for i, line_content in enumerate(raw_content.splitlines(), 1):
        for plugin in plugins:
            try:
                results = plugin.analyze_line(filename='in-memory', line=line_content, line_number=i)
                for secret in results:
                    # Create a unique key for the finding to avoid duplicates
                    finding_key = (i, secret.secret_value, secret.type)
                    if finding_key not in seen:
                        leaks.append({
                            'RuleID': secret.type, # Or plugin.secret_type for consistency
                            'LineNumber': i,
                            'SecretType': secret.type,
                            'SecretValue': secret.secret_value,
                        })
                        seen.add(finding_key)
            except Exception as e:
                # print(f"Error analyzing line with plugin {plugin.__class__.__name__}: {e}")
                pass # Continue with other plugins/lines

    # Add custom password-like string findings
    custom_findings = find_custom_password_like_strings(raw_content)
    for finding in custom_findings:
        finding_key = (finding['LineNumber'], finding['SecretValue'], finding['SecretType'])
        if finding_key not in seen:
            leaks.append(finding)
            seen.add(finding_key)
            
    return leaks 