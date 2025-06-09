"""Tests for security filtering functionality in YamlToolBase.

This module tests the new security_filtering post-processing feature that automatically
detects and redacts sensitive information from script outputs using the existing
utils.secret_scanner infrastructure.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from mcp_tools.yaml_tools import YamlToolBase


class MockCommandExecutor:
    """Mock command executor for testing security filtering."""

    def __init__(self):
        self.mock_results = {}

    async def execute_async(self, command: str, timeout=None):
        return {"token": "test-token", "status": "running", "pid": 12345}

    async def query_process(self, token: str, wait=False, timeout=None):
        return self.mock_results.get(token, {
            "status": "completed",
            "success": True,
            "output": "Normal output without secrets",
            "error": "Normal error without secrets",
            "return_code": 0
        })


@pytest.fixture
def mock_command_executor():
    """Fixture providing a mock command executor."""
    return MockCommandExecutor()


class TestSecurityFilteringConfiguration:
    """Test cases for security filtering configuration."""

    @pytest.mark.asyncio
    async def test_security_filtering_enabled_by_default(self, mock_command_executor):
        """Test that security filtering is enabled by default."""
        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        # Mock output with potential secrets
        mock_command_executor.mock_results["test-token"] = {
            "status": "completed",
            "success": True,
            "output": "DB_PASSWORD=secret123",
            "error": "Debug info",
            "return_code": 0
        }

        # Mock the redact_secrets function to simulate redaction
        def mock_redact_secrets(content):
            redacted = content.replace("secret123", "[REDACTED]")
            findings = [{"SecretType": "Password", "LineNumber": 1}] if "secret" in content else []
            return redacted, findings

        with patch('mcp_tools.yaml_tools.redact_secrets', side_effect=mock_redact_secrets):
            with patch.object(tool, '_log_security_findings') as mock_log:
                result = await tool._query_status({"token": "test-token"})
                
                # Check that secrets were redacted by default
                result_text = result[0]["text"]
                assert "[REDACTED]" in result_text
                assert "secret123" not in result_text
                
                # Check that security findings were logged
                mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_security_filtering_explicitly_disabled(self, mock_command_executor):
        """Test that security filtering can be explicitly disabled."""
        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "post_processing": {
                "security_filtering": {
                    "enabled": False
                }
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        # Mock output with potential secrets
        mock_command_executor.mock_results["test-token"] = {
            "status": "completed",
            "success": True,
            "output": "DB_PASSWORD=secret123",
            "error": "Debug info",
            "return_code": 0
        }

        with patch('mcp_tools.yaml_tools.redact_secrets') as mock_redact:
            result = await tool._query_status({"token": "test-token"})
            
            # redact_secrets should not be called when explicitly disabled
            mock_redact.assert_not_called()
            
            # Original content should be preserved
            result_text = result[0]["text"]
            assert "DB_PASSWORD=secret123" in result_text

    @pytest.mark.asyncio
    async def test_security_filtering_enabled(self, mock_command_executor):
        """Test that security filtering works when enabled."""
        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "post_processing": {
                "security_filtering": {
                    "enabled": True
                }
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        # Mock output with potential secrets
        mock_command_executor.mock_results["test-token"] = {
            "status": "completed",
            "success": True,
            "output": "DB_PASSWORD=secret123",
            "error": "Debug: password=mysecret",
            "return_code": 0
        }

        # Mock the redact_secrets function to simulate redaction
        def mock_redact_secrets(content):
            redacted = content.replace("secret123", "[REDACTED]").replace("mysecret", "[REDACTED]")
            findings = [{"SecretType": "Password", "LineNumber": 1}] if "secret" in content else []
            return redacted, findings

        with patch('mcp_tools.yaml_tools.redact_secrets', side_effect=mock_redact_secrets):
            with patch.object(tool, '_log_security_findings') as mock_log:
                result = await tool._query_status({"token": "test-token"})
                
                # Check that secrets were redacted
                result_text = result[0]["text"]
                assert "[REDACTED]" in result_text
                assert "secret123" not in result_text
                assert "mysecret" not in result_text
                
                # Check that security findings were logged
                mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_security_filtering_stdout_only(self, mock_command_executor):
        """Test security filtering applied to stdout only."""
        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "post_processing": {
                "security_filtering": {
                    "enabled": True,
                    "apply_to": ["stdout"]
                }
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        # Mock output with secrets in both stdout and stderr
        mock_command_executor.mock_results["test-token"] = {
            "status": "completed",
            "success": True,
            "output": "DB_PASSWORD=secret123",
            "error": "Debug: password=mysecret",
            "return_code": 0
        }

        def mock_redact_secrets(content):
            if "DB_PASSWORD=secret123" in content:
                # This is stdout - should be redacted
                return content.replace("secret123", "[REDACTED]"), [{"SecretType": "Password", "LineNumber": 1}]
            else:
                # This is stderr - should not be processed
                return content, []

        with patch('mcp_tools.yaml_tools.redact_secrets', side_effect=mock_redact_secrets) as mock_redact:
            result = await tool._query_status({"token": "test-token"})
            
            result_text = result[0]["text"]
            # stdout should be redacted
            assert "DB_PASSWORD=[REDACTED]" in result_text
            # stderr should remain unchanged
            assert "password=mysecret" in result_text
            
            # redact_secrets should be called only once (for stdout)
            assert mock_redact.call_count == 1

    @pytest.mark.asyncio
    async def test_security_filtering_stderr_only(self, mock_command_executor):
        """Test security filtering applied to stderr only."""
        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "post_processing": {
                "security_filtering": {
                    "enabled": True,
                    "apply_to": ["stderr"]
                }
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        # Mock output with secrets in both stdout and stderr
        mock_command_executor.mock_results["test-token"] = {
            "status": "completed",
            "success": True,
            "output": "DB_PASSWORD=secret123",
            "error": "Debug: password=mysecret",
            "return_code": 0
        }

        def mock_redact_secrets(content):
            if "password=mysecret" in content:
                # This is stderr - should be redacted
                return content.replace("mysecret", "[REDACTED]"), [{"SecretType": "Password", "LineNumber": 1}]
            else:
                # This is stdout - should not be processed
                return content, []

        with patch('mcp_tools.yaml_tools.redact_secrets', side_effect=mock_redact_secrets) as mock_redact:
            result = await tool._query_status({"token": "test-token"})
            
            result_text = result[0]["text"]
            # stdout should remain unchanged
            assert "DB_PASSWORD=secret123" in result_text
            # stderr should be redacted
            assert "password=[REDACTED]" in result_text
            
            # redact_secrets should be called only once (for stderr)
            assert mock_redact.call_count == 1

    @pytest.mark.asyncio
    async def test_security_filtering_log_findings_disabled(self, mock_command_executor):
        """Test that security findings logging can be disabled."""
        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "post_processing": {
                "security_filtering": {
                    "enabled": True,
                    "log_findings": False
                }
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        # Mock output with secrets
        mock_command_executor.mock_results["test-token"] = {
            "status": "completed",
            "success": True,
            "output": "DB_PASSWORD=secret123",
            "error": "",
            "return_code": 0
        }

        def mock_redact_secrets(content):
            return content.replace("secret123", "[REDACTED]"), [{"SecretType": "Password", "LineNumber": 1}]

        with patch('mcp_tools.yaml_tools.redact_secrets', side_effect=mock_redact_secrets):
            with patch.object(tool, '_log_security_findings') as mock_log:
                result = await tool._query_status({"token": "test-token"})
                
                # Security findings should not be logged
                mock_log.assert_not_called()
                
                # But redaction should still happen
                result_text = result[0]["text"]
                assert "[REDACTED]" in result_text


class TestSecurityFilteringHelperMethods:
    """Test cases for security filtering helper methods."""

    def test_apply_security_filtering_both_outputs(self):
        """Test _apply_security_filtering with both stdout and stderr."""
        tool_data = {"type": "script"}
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)

        config = {
            "apply_to": ["stdout", "stderr"],
            "log_findings": False
        }

        def mock_redact_secrets(content):
            if "secret" in content:
                return content.replace("secret", "[REDACTED]"), [{"SecretType": "Password", "LineNumber": 1}]
            return content, []

        with patch('mcp_tools.yaml_tools.redact_secrets', side_effect=mock_redact_secrets):
            filtered_stdout, filtered_stderr = tool._apply_security_filtering(
                "stdout with secret", "stderr with secret", config
            )

        assert filtered_stdout == "stdout with [REDACTED]"
        assert filtered_stderr == "stderr with [REDACTED]"

    def test_apply_security_filtering_no_secrets(self):
        """Test _apply_security_filtering with content that has no secrets."""
        tool_data = {"type": "script"}
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)

        config = {
            "apply_to": ["stdout", "stderr"],
            "log_findings": False
        }

        def mock_redact_secrets(content):
            return content, []  # No secrets found

        with patch('mcp_tools.yaml_tools.redact_secrets', side_effect=mock_redact_secrets):
            filtered_stdout, filtered_stderr = tool._apply_security_filtering(
                "clean stdout", "clean stderr", config
            )

        assert filtered_stdout == "clean stdout"
        assert filtered_stderr == "clean stderr"

    def test_log_security_findings(self):
        """Test _log_security_findings method."""
        tool_data = {"type": "script"}
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)

        findings = [
            {"SecretType": "Password", "LineNumber": 1, "SecretValue": "secret1"},
            {"SecretType": "API_Key", "LineNumber": 5, "SecretValue": "key123"}
        ]

        with patch('mcp_tools.yaml_tools.logger') as mock_logger:
            tool._log_security_findings(findings)

            # Should log a security alert
            assert mock_logger.warning.call_count >= 1
            
            # Check that the main security alert was logged
            main_alert_call = mock_logger.warning.call_args_list[0]
            assert "SECURITY ALERT" in main_alert_call[0][0]
            assert "2 potential secrets" in main_alert_call[0][0]

    def test_summarize_line_numbers_single(self):
        """Test _summarize_line_numbers with a single line number."""
        tool_data = {"type": "script"}
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)

        result = tool._summarize_line_numbers([5])
        assert result == "line 5"

    def test_summarize_line_numbers_two(self):
        """Test _summarize_line_numbers with two line numbers."""
        tool_data = {"type": "script"}
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)

        result = tool._summarize_line_numbers([3, 7])
        assert result == "lines 3 and 7"

    def test_summarize_line_numbers_range(self):
        """Test _summarize_line_numbers with consecutive line numbers."""
        tool_data = {"type": "script"}
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)

        result = tool._summarize_line_numbers([1, 2, 3, 4, 5])
        assert result == "lines 1-5"

    def test_summarize_line_numbers_mixed(self):
        """Test _summarize_line_numbers with mixed ranges and individual lines."""
        tool_data = {"type": "script"}
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)

        result = tool._summarize_line_numbers([1, 2, 3, 5, 7, 8, 10])
        assert result == "lines 1-3, 5, 7-8, and 10"

    def test_summarize_line_numbers_empty(self):
        """Test _summarize_line_numbers with empty list."""
        tool_data = {"type": "script"}
        tool = YamlToolBase(tool_name="test_tool", tool_data=tool_data)

        result = tool._summarize_line_numbers([])
        assert result == "unknown locations"


class TestSecurityFilteringIntegration:
    """Integration tests for security filtering with existing post-processing."""

    @pytest.mark.asyncio
    async def test_security_filtering_with_output_attachment_config(self, mock_command_executor):
        """Test security filtering combined with output attachment configuration."""
        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "post_processing": {
                "attach_stderr": False,  # Don't attach stderr
                "security_filtering": {
                    "enabled": True,
                    "apply_to": ["stdout", "stderr"]  # Filter both even though stderr won't be attached
                }
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        # Mock output with secrets in both stdout and stderr
        mock_command_executor.mock_results["test-token"] = {
            "status": "completed",
            "success": True,
            "output": "DB_PASSWORD=secret123",
            "error": "Debug: password=mysecret",
            "return_code": 0
        }

        def mock_redact_secrets(content):
            redacted = content.replace("secret123", "[REDACTED]").replace("mysecret", "[REDACTED]")
            findings = [{"SecretType": "Password", "LineNumber": 1}] if "secret" in content else []
            return redacted, findings

        with patch('mcp_tools.yaml_tools.redact_secrets', side_effect=mock_redact_secrets):
            result = await tool._query_status({"token": "test-token"})
            
            result_text = result[0]["text"]
            # stdout should be redacted and included
            assert "DB_PASSWORD=[REDACTED]" in result_text
            # stderr should be redacted but not included due to attach_stderr: false
            assert "password=mysecret" not in result_text
            assert "password=[REDACTED]" not in result_text 