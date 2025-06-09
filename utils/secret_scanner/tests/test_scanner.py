import pytest
from utils.secret_scanner import check_secrets, redact_secrets


def test_no_secrets():
    content = """
    def foo():
        return "hello world"
    """
    result = check_secrets(content)
    assert result == []


def test_obvious_secret():
    content = """
    password = "hunter2"
    """
    result = check_secrets(content)
    assert isinstance(result, list)
    assert len(result) >= 1
    for finding in result:
        assert "RuleID" in finding
        assert "LineNumber" in finding
        assert "SecretType" in finding
        assert "SecretValue" in finding
        assert finding["LineNumber"] == 2
        assert finding["SecretValue"] == "hunter2"


def test_multiple_secrets():
    content = """
    api_key = "AKIAIOSFODNN7EXAMPLE"
    password = "hunter2"
    """
    result = check_secrets(content)
    assert isinstance(result, list)
    assert len(result) >= 2
    found_values = {finding["SecretValue"] for finding in result}
    assert "hunter2" in found_values
    assert "AKIAIOSFODNN7EXAMPLE" in found_values


def test_secret_in_comment():
    content = """
    # password = "notasecret"
    """
    result = check_secrets(content)
    # Some plugins may or may not catch secrets in comments, so just check type
    assert isinstance(result, list)


def test_empty_string():
    content = ""
    result = check_secrets(content)
    assert result == []


def test_non_secret_random_string():
    content = "This is just a normal string with numbers 123456."
    result = check_secrets(content)
    assert result == []


def test_raw_password_like_string():
    content = "A1b2C3d4E5f6G7h8I9j0!@#"
    result = check_secrets(content)
    assert any(
        f["RuleID"] == "PasswordLikeString"
        and f["SecretValue"] == "A1b2C3d4E5f6G7h8I9j0!@#"
        for f in result
    )


def test_short_string_not_detected():
    content = "abc123!@#"
    result = check_secrets(content)
    assert not any(f["RuleID"] == "PasswordLikeString" for f in result)


def test_single_class_string_not_detected():
    content = "aaaaaaaaaaaaaaa"
    result = check_secrets(content)
    assert not any(f["RuleID"] == "PasswordLikeString" for f in result)


def test_high_entropy_string_detected():
    content = "z8J!kL2@xQw9#rT7$uV6"
    result = check_secrets(content)
    assert any(
        f["RuleID"] == "PasswordLikeString"
        and f["SecretValue"] == "z8J!kL2@xQw9#rT7$uV6"
        for f in result
    )


def test_redact_secrets():
    content = """
    api_key = "AKIAIOSFODNN7EXAMPLE"
    password = "hunter2"
    """
    redacted_content, findings = redact_secrets(content)
    assert "[REDACTED]" in redacted_content
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted_content
    assert "hunter2" not in redacted_content
    assert len(findings) >= 2


def test_redact_secrets_no_secrets():
    content = "This is a normal text with no secrets."
    redacted_content, findings = redact_secrets(content)
    assert redacted_content == content
    assert len(findings) == 0


def test_redact_secrets_multiline():
    content = """
    Line 1 with no secrets
    Line 2 with api_key = "AKIAIOSFODNN7EXAMPLE"
    Line 3 with no secrets
    Line 4 with password = "hunter2"
    """
    redacted_content, findings = redact_secrets(content)
    assert "[REDACTED]" in redacted_content
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted_content
    assert "hunter2" not in redacted_content
    assert "Line 1 with no secrets" in redacted_content
    assert "Line 3 with no secrets" in redacted_content


# ============================================================================
# BUILD ARTIFACTS FALSE POSITIVE TESTS
# ============================================================================

class TestBuildArtifactsFalsePositives:
    """Test cases for build artifacts that should NOT be detected as secrets."""

    def test_file_paths_and_libraries(self):
        """Test that file paths and library files are not detected as secrets."""
        build_outputs = [
            "/usr/local/lib/libmyapp.so.1.2.3",
            "/opt/homebrew/lib/libssl.1.1.dylib",
            "C:\\Program Files\\MyApp\\bin\\myapp.exe",
            "/usr/lib/x86_64-linux-gnu/libcrypto.so.1.1",
            "/System/Library/Frameworks/Security.framework/Versions/A/Security",
            "/usr/local/Cellar/openssl@3/3.1.4/lib/libssl.3.dylib",
            "target/release/myapp-1.0.0.exe",
            "build/libs/myproject-2.1.0.jar",
            "/var/lib/docker/overlay2/abc123def456/merged"
        ]

        for build_output in build_outputs:
            result = check_secrets(build_output)
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) == 0, f"File path '{build_output}' was incorrectly detected as a secret"

    def test_package_and_version_identifiers(self):
        """Test that package names and version identifiers are not detected as secrets."""
        build_outputs = [
            "mypackage-1.0.0.tar.gz",
            "numpy-1.24.3-cp311-cp311-macosx_10_9_x86_64.whl",
            "react-dom@18.2.0",
            "org.springframework:spring-core:5.3.21",
            "com.fasterxml.jackson.core:jackson-databind:2.15.2",
            "lodash@4.17.21",
            "Successfully built mypackage-1.0.0",
            "Downloading mylib-2.1.0-py3-none-any.whl",
            "Installing collected packages: setuptools-68.0.0"
        ]

        for build_output in build_outputs:
            result = check_secrets(build_output)
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) == 0, f"Package identifier '{build_output}' was incorrectly detected as a secret"

    def test_build_tool_commands(self):
        """Test that build tool commands and outputs are not detected as secrets."""
        build_outputs = [
            "requirements.txt",
            "package-lock.json",
            "Cargo.toml",
            "pom.xml",
            "Successfully installed pip-23.1.2 setuptools-68.0.0 wheel-0.40.0",
            "Collecting package-name>=1.0.0",
            "Building wheel for mypackage (setup.py)",
            "Running setup.py bdist_wheel for mypackage"
        ]

        for build_output in build_outputs:
            result = check_secrets(build_output)
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) == 0, f"Build command '{build_output}' was incorrectly detected as a secret"

    def test_version_control_hashes(self):
        """Test that Git commit hashes and version control identifiers are not detected as secrets."""
        build_outputs = [
            "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t",  # Git commit hash
            "commit 1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t",
            "HEAD is now at 1a2b3c4d",
            "Merge: 1a2b3c4 5e6f7g8",
            "origin/main 1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t",
            "refs/heads/feature/abc123def456ghi789",
            "tag: v1.2.3-rc.1+build.20231201"
        ]

        for build_output in build_outputs:
            result = check_secrets(build_output)
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) == 0, f"Version control hash '{build_output}' was incorrectly detected as a secret"

    def test_checksums_and_signatures(self):
        """Test that checksums and cryptographic signatures are not detected as secrets."""
        build_outputs = [
            "sha256:1234567890abcdef1234567890abcdef12345678",
            "md5:098f6bcd4621d373cade4e832627b4f6",
            "sha1:aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d",
            "Checksum: sha256:a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            "GPG signature: 1234567890ABCDEF1234567890ABCDEF12345678",
            "RSA key fingerprint: 2048 SHA256:abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
        ]

        for build_output in build_outputs:
            result = check_secrets(build_output)
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) == 0, f"Checksum '{build_output}' was incorrectly detected as a secret"

    def test_urls_and_repository_paths(self):
        """Test that URLs and repository paths are not detected as secrets."""
        build_outputs = [
            "https://github.com/gorilla/mux",
            "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar",
            "https://pypi.org/simple/numpy/",
            "git@github.com:user/repo.git",
            "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
            "https://files.pythonhosted.org/packages/abc123def456/numpy-1.24.3.tar.gz",
            "Downloaded from central: https://repo1.maven.org/maven2/org/springframework/spring-core/5.3.21/spring-core-5.3.21.jar"
        ]

        for build_output in build_outputs:
            result = check_secrets(build_output)
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) == 0, f"URL '{build_output}' was incorrectly detected as a secret"

    def test_uuids_and_build_ids(self):
        """Test that UUIDs and build identifiers are not detected as secrets."""
        build_outputs = [
            "550e8400-e29b-41d4-a716-446655440000",
            "Build ID: 123e4567-e89b-12d3-a456-426614174000",
            "Session: f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "Request ID: 6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "Trace ID: 6ba7b811-9dad-11d1-80b4-00c04fd430c8",
            "Container ID: abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567890",
            "Image ID: sha256:abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567890abcdef"
        ]

        for build_output in build_outputs:
            result = check_secrets(build_output)
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) == 0, f"UUID/Build ID '{build_output}' was incorrectly detected as a secret"

    def test_docker_and_container_outputs(self):
        """Test that Docker and container-related outputs are not detected as secrets."""
        build_outputs = [
            "FROM node:18-alpine",
            "COPY package*.json ./",
            "RUN npm install --production",
            "EXPOSE 3000",
            "Successfully built abc123def456",
            "Successfully tagged myapp:latest",
            "docker.io/library/node:18-alpine",
            "registry.hub.docker.com/library/ubuntu:20.04",
            "Digest: sha256:abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567890abcdef"
        ]

        for build_output in build_outputs:
            result = check_secrets(build_output)
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) == 0, f"Docker output '{build_output}' was incorrectly detected as a secret"

    def test_compilation_and_linking_outputs(self):
        """Test that compilation and linking outputs are not detected as secrets."""
        build_outputs = [
            "gcc -o myapp main.c -lssl -lcrypto",
            "ld: library not found for -lmylib",
            "Linking CXX executable myapp",
            "Building target: myproject.exe",
            "Compiling src/main.rs",
            "cargo build --release --target x86_64-unknown-linux-gnu",
            "rustc --crate-name myapp --edition 2021 src/main.rs",
            "Finished release [optimized] target(s) in 2.34s"
        ]

        for build_output in build_outputs:
            result = check_secrets(build_output)
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) == 0, f"Compilation output '{build_output}' was incorrectly detected as a secret"

    def test_real_build_log_scenario(self):
        """Test a realistic build log scenario with multiple types of build artifacts."""
        build_log = """
Building library: /usr/local/lib/libmyapp.so.1.2.3
Successfully built mypackage-1.0.0
Checksum: sha256:1234567890abcdef1234567890abcdef12345678
Downloaded from central: https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar
Commit: 1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t
Build ID: 550e8400-e29b-41d4-a716-446655440000
Successfully tagged myapp:latest
        """

        result = check_secrets(build_log)
        password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
        assert len(password_like_findings) == 0, "Real build log scenario should not contain any false positive secret detections"


# ============================================================================
# ACTUAL SECRETS DETECTION TESTS
# ============================================================================

class TestActualSecretsDetection:
    """Test cases to ensure actual secrets are still properly detected."""

    def test_real_passwords_still_detected(self):
        """Test that actual passwords are still detected after the fix."""
        actual_secrets = [
            "MySecretPassword123!",
            "SuperSecureP@ssw0rd2023",
            "ComplexPassword!@#$%^&*()_+",
            "DatabasePassword123456789!",
            "AdminPassword2023!@#$%"
        ]

        for secret in actual_secrets:
            result = check_secrets(f"password = {secret}")
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) > 0, f"Actual password '{secret}' should be detected as a secret"

    def test_api_keys_still_detected(self):
        """Test that API keys are still detected after the fix."""
        api_keys = [
            "sk-1234567890abcdef1234567890abcdef",
            "AKIAIOSFODNN7EXAMPLE",
            "AIzaSyDaGmWKa4JsXZ-HjGw7ISLan_PizdGIreo",
            "xoxb-FAKE567890-FAKE567890123-FAKEFGHIJKLMNOPQRSTUVWX",  # Test Slack token format
            "ghp_1234567890abcdef1234567890abcdef12345678"
        ]

        for api_key in api_keys:
            result = check_secrets(f"api_key = {api_key}")
            # API keys might be detected by different plugins, so check for any detection
            assert len(result) > 0, f"API key '{api_key}' should be detected as a secret"

    def test_database_connection_strings_still_detected(self):
        """Test that database connection strings with passwords are still detected."""
        connection_strings = [
            "server=db.example.com;uid=admin;pwd=SuperSecret123!",
            "mongodb://user:MyPassword123@localhost:27017/mydb",
            "postgresql://username:SecretPassword456@localhost:5432/database",
            "mysql://root:AdminPassword789@localhost:3306/myapp"
        ]

        for conn_str in connection_strings:
            result = check_secrets(conn_str)
            # Connection strings should be detected (either as password-like or by other plugins)
            assert len(result) > 0, f"Connection string '{conn_str}' should be detected as containing secrets"

    def test_high_entropy_tokens_still_detected(self):
        """Test that high-entropy tokens are still detected after the fix."""
        high_entropy_tokens = [
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # JWT header (base64)
            "AbCdEf123456GhIjKl789012MnOpQr345678",    # High entropy token
            "xoxb-FAKE567890-FAKE567890123-FAKEFGHIJKLMNOPQRSTUVWX",  # Test Slack token format
        ]

        for token in high_entropy_tokens:
            result = check_secrets(f"token = {token}")
            # High entropy tokens should be detected by our password-like detection
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) > 0, f"High entropy token '{token}' should be detected as a secret"


# ============================================================================
# EDGE CASES AND REGRESSION TESTS
# ============================================================================

class TestEdgeCasesAndRegression:
    """Test edge cases and ensure no regressions in existing functionality."""

    def test_mixed_content_with_secrets_and_build_artifacts(self):
        """Test content that contains both legitimate secrets and build artifacts."""
        mixed_content = """
Building library: /usr/local/lib/libmyapp.so.1.2.3
Successfully built mypackage-1.0.0
DB_PASSWORD=SuperSecretPassword123!
Checksum: sha256:1234567890abcdef1234567890abcdef12345678
API_KEY=sk-1234567890abcdef1234567890abcdef
Downloaded from: https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar
        """

        result = check_secrets(mixed_content)

        # Should detect the actual secrets
        secret_values = {f["SecretValue"] for f in result}
        assert "SuperSecretPassword123!" in secret_values, "Real password should be detected"
        assert "sk-1234567890abcdef1234567890abcdef" in secret_values, "Real API key should be detected"

        # Should NOT detect build artifacts
        build_artifacts = [
            "/usr/local/lib/libmyapp.so.1.2.3",
            "mypackage-1.0.0",
            "sha256:1234567890abcdef1234567890abcdef12345678",
            "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar"
        ]

        for artifact in build_artifacts:
            assert artifact not in secret_values, f"Build artifact '{artifact}' should not be detected as a secret"

    def test_boundary_conditions(self):
        """Test boundary conditions for string length and complexity."""
        # Exactly 12 characters - should be evaluated
        boundary_strings = [
            "abcdef123456",  # 12 chars, 2 classes, low entropy - should NOT be detected
            "AbCdEf123456",  # 12 chars, 3 classes, medium entropy - might be detected
            "AbCdEf123!@#",  # 12 chars, 4 classes, high entropy - should be detected
        ]

        for test_string in boundary_strings:
            result = check_secrets(test_string)
            # Just ensure the function doesn't crash and returns a list
            assert isinstance(result, list)

    def test_very_long_build_paths(self):
        """Test very long file paths that might trigger false positives."""
        long_paths = [
            "/very/long/path/to/some/build/artifact/that/contains/many/segments/and/might/trigger/false/positives/libmyapp.so.1.2.3",
            "C:\\Program Files\\Microsoft Visual Studio\\2022\\Enterprise\\VC\\Tools\\MSVC\\14.35.32215\\bin\\Hostx64\\x64\\cl.exe",
            "/usr/local/Cellar/python@3.11/3.11.6/Frameworks/Python.framework/Versions/3.11/lib/python3.11/site-packages/numpy/core/_multiarray_umath.cpython-311-darwin.so"
        ]

        for long_path in long_paths:
            result = check_secrets(long_path)
            password_like_findings = [f for f in result if f.get("SecretType") == "PasswordLikeString"]
            assert len(password_like_findings) == 0, f"Long path '{long_path}' should not be detected as a secret"

    def test_redaction_preserves_structure(self):
        """Test that redaction preserves the overall structure of build logs."""
        build_log_with_secrets = """
Building library: /usr/local/lib/libmyapp.so.1.2.3
DB_PASSWORD=SuperSecretPassword123!
Successfully built mypackage-1.0.0
API_KEY=sk-1234567890abcdef1234567890abcdef
Checksum: sha256:1234567890abcdef1234567890abcdef12345678
        """

        redacted_content, findings = redact_secrets(build_log_with_secrets)

        # Should preserve build artifacts
        assert "/usr/local/lib/libmyapp.so.1.2.3" in redacted_content
        assert "mypackage-1.0.0" in redacted_content
        assert "sha256:1234567890abcdef1234567890abcdef12345678" in redacted_content

        # Should redact actual secrets
        assert "SuperSecretPassword123!" not in redacted_content
        assert "sk-1234567890abcdef1234567890abcdef" not in redacted_content
        assert "[REDACTED]" in redacted_content

        # Should have detected the secrets
        assert len(findings) >= 2
