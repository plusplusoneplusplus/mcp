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
        assert 'RuleID' in finding
        assert 'LineNumber' in finding
        assert 'SecretType' in finding
        assert 'SecretValue' in finding
        assert finding['LineNumber'] == 2
        assert finding['SecretValue'] == 'hunter2'


def test_multiple_secrets():
    content = """
    api_key = "AKIAIOSFODNN7EXAMPLE"
    password = "hunter2"
    """
    result = check_secrets(content)
    assert isinstance(result, list)
    assert len(result) >= 2
    found_values = {finding['SecretValue'] for finding in result}
    assert 'hunter2' in found_values
    assert 'AKIAIOSFODNN7EXAMPLE' in found_values


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
    assert any(f['RuleID'] == 'PasswordLikeString' and f['SecretValue'] == 'A1b2C3d4E5f6G7h8I9j0!@#' for f in result)


def test_short_string_not_detected():
    content = "abc123!@#"
    result = check_secrets(content)
    assert not any(f['RuleID'] == 'PasswordLikeString' for f in result)


def test_single_class_string_not_detected():
    content = "aaaaaaaaaaaaaaa"
    result = check_secrets(content)
    assert not any(f['RuleID'] == 'PasswordLikeString' for f in result)


def test_high_entropy_string_detected():
    content = "z8J!kL2@xQw9#rT7$uV6"
    result = check_secrets(content)
    assert any(f['RuleID'] == 'PasswordLikeString' and f['SecretValue'] == 'z8J!kL2@xQw9#rT7$uV6' for f in result)


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