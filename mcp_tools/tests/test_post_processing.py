"""Tests for post-processing functionality in YamlToolBase.

This module tests the new post_processing configuration feature that allows
controlling which outputs (stdout/stderr) are attached to script execution results.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from mcp_tools.yaml_tools import YamlToolBase


class MockCommandExecutor:
    """Mock command executor for testing post-processing."""

    def __init__(self):
        self.mock_results = {}

    async def execute_async(self, command: str, timeout=None):
        return {"token": "test-token", "status": "running", "pid": 12345}

    async def query_process(self, token: str, wait=False, timeout=None):
        return self.mock_results.get(token, {
            "status": "completed",
            "success": True,
            "output": "This is stdout output",
            "error": "This is stderr output",
            "return_code": 0
        })


@pytest.fixture
def mock_command_executor():
    """Fixture providing a mock command executor."""
    return MockCommandExecutor()


class TestPostProcessingConfiguration:
    """Test cases for post-processing configuration."""

    @pytest.mark.asyncio
    async def test_default_behavior_no_post_processing(self, mock_command_executor):
        """Test that without post_processing config, both stdout and stderr are included."""
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

        # Test the query status method
        result = await tool._query_status({"token": "test-token"})

        # Should include both output and error
        result_text = result[0]["text"]
        assert "This is stdout output" in result_text
        assert "This is stderr output" in result_text

    @pytest.mark.asyncio
    async def test_attach_stdout_false(self, mock_command_executor):
        """Test that attach_stdout: false excludes stdout from result."""
        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "post_processing": {
                "attach_stdout": False
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        result = await tool._query_status({"token": "test-token"})
        result_text = result[0]["text"]

        # Should not include stdout but should include stderr
        assert "This is stdout output" not in result_text
        assert "This is stderr output" in result_text

    @pytest.mark.asyncio
    async def test_attach_stderr_false(self, mock_command_executor):
        """Test that attach_stderr: false excludes stderr from result."""
        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "post_processing": {
                "attach_stderr": False
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        result = await tool._query_status({"token": "test-token"})
        result_text = result[0]["text"]

        # Should include stdout but not stderr
        assert "This is stdout output" in result_text
        assert "This is stderr output" not in result_text

    @pytest.mark.asyncio
    async def test_stderr_on_failure_only_success(self, mock_command_executor):
        """Test stderr_on_failure_only: true with successful command (should hide stderr)."""
        # Mock successful execution
        mock_command_executor.mock_results["test-token"] = {
            "status": "completed",
            "success": True,
            "output": "Success output",
            "error": "Debug info in stderr",
            "return_code": 0
        }

        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "post_processing": {
                "stderr_on_failure_only": True
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        result = await tool._query_status({"token": "test-token"})
        result_text = result[0]["text"]

        # Should include stdout but not stderr (since command succeeded)
        assert "Success output" in result_text
        assert "Debug info in stderr" not in result_text

    @pytest.mark.asyncio
    async def test_stderr_on_failure_only_failure(self, mock_command_executor):
        """Test stderr_on_failure_only: true with failed command (should show stderr)."""
        # Mock failed execution
        mock_command_executor.mock_results["test-token"] = {
            "status": "completed",
            "success": False,
            "output": "Partial output",
            "error": "Error details in stderr",
            "return_code": 1
        }

        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "post_processing": {
                "stderr_on_failure_only": True
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        result = await tool._query_status({"token": "test-token"})
        result_text = result[0]["text"]

        # Should include both stdout and stderr (since command failed)
        assert "Partial output" in result_text
        assert "Error details in stderr" in result_text

    @pytest.mark.asyncio
    async def test_combined_configuration(self, mock_command_executor):
        """Test combination of multiple post-processing options."""
        tool_data = {
            "type": "script",
            "scripts": {"darwin": "echo 'test'"},
            "post_processing": {
                "attach_stdout": True,
                "attach_stderr": False,
                "stderr_on_failure_only": True  # This should be ignored since attach_stderr is False
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_tool",
            tool_data=tool_data,
            command_executor=mock_command_executor
        )

        result = await tool._query_status({"token": "test-token"})
        result_text = result[0]["text"]

        # Should include stdout but not stderr (attach_stderr takes precedence)
        assert "This is stdout output" in result_text
        assert "This is stderr output" not in result_text


class TestPostProcessingHelperMethods:
    """Test cases for post-processing helper methods."""

    def test_apply_output_attachment_config_defaults(self):
        """Test _apply_output_attachment_config with default configuration."""
        tool = YamlToolBase(tool_name="test")

        result = {
            "output": "stdout content",
            "error": "stderr content",
            "success": True
        }

        # Empty config should use defaults (include both)
        processed = tool._apply_output_attachment_config(result, {})

        assert processed["output"] == "stdout content"
        assert processed["error"] == "stderr content"

    def test_apply_output_attachment_config_attach_stdout_false(self):
        """Test _apply_output_attachment_config with attach_stdout: false."""
        tool = YamlToolBase(tool_name="test")

        result = {
            "output": "stdout content",
            "error": "stderr content",
            "success": True
        }

        config = {"attach_stdout": False}
        processed = tool._apply_output_attachment_config(result, config)

        assert processed["output"] == ""
        assert processed["error"] == "stderr content"

    def test_apply_output_attachment_config_attach_stderr_false(self):
        """Test _apply_output_attachment_config with attach_stderr: false."""
        tool = YamlToolBase(tool_name="test")

        result = {
            "output": "stdout content",
            "error": "stderr content",
            "success": True
        }

        config = {"attach_stderr": False}
        processed = tool._apply_output_attachment_config(result, config)

        assert processed["output"] == "stdout content"
        assert processed["error"] == ""

    def test_apply_output_attachment_config_stderr_on_failure_only_success(self):
        """Test stderr_on_failure_only with successful command."""
        tool = YamlToolBase(tool_name="test")

        result = {
            "output": "stdout content",
            "error": "stderr content",
            "success": True
        }

        config = {"stderr_on_failure_only": True}
        processed = tool._apply_output_attachment_config(result, config)

        assert processed["output"] == "stdout content"
        assert processed["error"] == ""  # Should be empty for successful command

    def test_apply_output_attachment_config_stderr_on_failure_only_failure(self):
        """Test stderr_on_failure_only with failed command."""
        tool = YamlToolBase(tool_name="test")

        result = {
            "output": "stdout content",
            "error": "stderr content",
            "success": False
        }

        config = {"stderr_on_failure_only": True}
        processed = tool._apply_output_attachment_config(result, config)

        assert processed["output"] == "stdout content"
        assert processed["error"] == "stderr content"  # Should be preserved for failed command

    def test_format_result_with_both_outputs(self):
        """Test _format_result with both stdout and stderr."""
        tool = YamlToolBase(tool_name="test")

        result = {
            "output": "stdout content",
            "error": "stderr content",
            "success": True
        }

        formatted = tool._format_result(result, "test-token")

        assert "Process completed (token: test-token)" in formatted
        assert "Success: True" in formatted
        assert "Output:\nstdout content" in formatted
        assert "Error:\nstderr content" in formatted

    def test_format_result_stdout_only(self):
        """Test _format_result with only stdout."""
        tool = YamlToolBase(tool_name="test")

        result = {
            "output": "stdout content",
            "error": "",
            "success": True
        }

        formatted = tool._format_result(result, "test-token")

        assert "Process completed (token: test-token)" in formatted
        assert "Success: True" in formatted
        assert "Output:\nstdout content" in formatted
        assert "Error:" not in formatted

    def test_format_result_stderr_only(self):
        """Test _format_result with only stderr."""
        tool = YamlToolBase(tool_name="test")

        result = {
            "output": "",
            "error": "stderr content",
            "success": False
        }

        formatted = tool._format_result(result, "test-token")

        assert "Process completed (token: test-token)" in formatted
        assert "Success: False" in formatted
        assert "Output:" not in formatted
        assert "Error:\nstderr content" in formatted

    def test_format_result_no_outputs(self):
        """Test _format_result with no outputs."""
        tool = YamlToolBase(tool_name="test")

        result = {
            "output": "",
            "error": "",
            "success": True
        }

        formatted = tool._format_result(result, "test-token")

        assert "Process completed (token: test-token)" in formatted
        assert "Success: True" in formatted
        assert "Output:" not in formatted
        assert "Error:" not in formatted
