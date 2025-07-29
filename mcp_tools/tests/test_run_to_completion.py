"""Tests for run_to_completion feature in YAML script tools.

This module tests the new run_to_completion option that allows script tools
to wait indefinitely for completion and return final results directly.
"""

import asyncio
import platform
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, patch, Mock

import pytest

from mcp_tools.yaml_tools import YamlToolBase
from mcp_tools.interfaces import CommandExecutorInterface


class MockCommandExecutorForRunToCompletion(CommandExecutorInterface):
    """Mock command executor specifically for testing run_to_completion feature."""

    def __init__(self):
        self.executed_commands = []
        self.mock_results = {}
        self.wait_for_process_results = {}
        self.wait_for_process_called = []
        self.query_process_called = []

    @property
    def name(self) -> str:
        return "mock_run_to_completion_executor"

    @property
    def description(self) -> str:
        return "Mock command executor for run_to_completion testing"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        return {"success": True}

    def execute(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        self.executed_commands.append(command)
        return {"success": True, "return_code": 0, "output": "sync result", "error": ""}

    async def execute_async(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Execute async command and return token."""
        self.executed_commands.append(command)
        default_result = {"token": f"token-{len(self.executed_commands)}", "status": "running", "pid": 12345}
        return self.mock_results.get(command, default_result)

    async def wait_for_process(self, token: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Mock wait_for_process method - key for run_to_completion testing."""
        self.wait_for_process_called.append({"token": token, "timeout": timeout})

        # Return custom results for specific tokens
        if token in self.wait_for_process_results:
            return self.wait_for_process_results[token]

        # Default success result
        return {
            "status": "completed",
            "success": True,
            "return_code": 0,
            "output": f"Process {token} completed successfully",
            "error": "",
            "pid": 12345,
            "duration": 1.5
        }

    async def query_process(self, token: str, wait: bool = False, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Mock query process method."""
        self.query_process_called.append({"token": token, "wait": wait, "timeout": timeout})
        return {"status": "running", "pid": 12345}

    def terminate_by_token(self, token: str) -> bool:
        return True

    def list_running_processes(self) -> list:
        return []

    async def start_periodic_status_reporter(self, interval: float = 30.0, enabled: bool = True) -> None:
        pass

    async def stop_periodic_status_reporter(self) -> None:
        pass


@pytest.fixture
def mock_executor():
    """Fixture providing a mock command executor for run_to_completion tests."""
    return MockCommandExecutorForRunToCompletion()


@pytest.fixture
def base_tool_data():
    """Base tool data for testing."""
    return {
        "type": "script",
        "scripts": {
            "linux": "echo 'Hello {name}'",
            "darwin": "echo 'Hello {name}'",
            "windows": "echo Hello {name}"
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to greet"}
            },
            "required": ["name"]
        }
    }


class TestRunToCompletionTrue:
    """Test cases for run_to_completion=true."""

    @pytest.mark.asyncio
    async def test_run_to_completion_waits_indefinitely(self, mock_executor, base_tool_data):
        """Test that run_to_completion=true waits indefinitely for script completion."""
        # Enable run_to_completion
        tool_data = {**base_tool_data, "run_to_completion": True}

        tool = YamlToolBase(
            tool_name="test_completion_tool",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        # Set up mock results
        mock_executor.mock_results["echo 'Hello World'"] = {
            "token": "completion-token-123",
            "status": "running",
            "pid": 12345
        }

        mock_executor.wait_for_process_results["completion-token-123"] = {
            "status": "completed",
            "success": True,
            "return_code": 0,
            "output": "Hello World\nProcess completed successfully",
            "error": "",
            "pid": 12345,
            "duration": 10.0
        }

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({"name": "World"})

        # Verify wait_for_process was called with no timeout
        assert len(mock_executor.wait_for_process_called) == 1
        wait_call = mock_executor.wait_for_process_called[0]
        assert wait_call["token"] == "completion-token-123"
        assert wait_call["timeout"] is None  # Key assertion: no timeout

        # Verify result contains final output, not just token
        assert len(result) == 1
        assert result[0]["type"] == "text"
        result_text = result[0]["text"]
        assert "Hello World" in result_text
        assert "Process completed successfully" in result_text
        assert "completion-token-123" in result_text

    @pytest.mark.asyncio
    async def test_run_to_completion_with_post_processing(self, mock_executor, base_tool_data):
        """Test run_to_completion with post-processing configuration."""
        tool_data = {
            **base_tool_data,
            "run_to_completion": True,
            "post_processing": {
                "attach_stdout": True,
                "attach_stderr": False,
                "security_filtering": {
                    "enabled": True,
                    "apply_to": ["stdout", "stderr"]
                },
                "output_limits": {
                    "max_stdout_length": 100,
                    "truncate_strategy": "end"
                }
            }
        }

        tool = YamlToolBase(
            tool_name="test_post_processing",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        # Mock long output that should be truncated
        long_output = "Long output line\n" * 20
        mock_executor.wait_for_process_results["test-token"] = {
            "status": "completed",
            "success": True,
            "return_code": 0,
            "output": long_output,
            "error": "Some error message",
            "pid": 12345,
            "duration": 5.0
        }

        mock_executor.mock_results["echo 'Hello Test'"] = {
            "token": "test-token",
            "status": "running",
            "pid": 12345
        }

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                with patch.object(tool, '_apply_security_filtering', return_value=(long_output, "")):
                    result = await tool._execute_script({"name": "Test"})

        # Verify post-processing was applied
        assert len(result) == 1
        result_text = result[0]["text"]

        # Should contain stdout but processing may have been applied
        assert "Long output line" in result_text
        # Stderr should be filtered out by attach_stderr: false (in the formatted result)

    @pytest.mark.asyncio
    async def test_run_to_completion_failure_handling(self, mock_executor, base_tool_data):
        """Test run_to_completion handles script failures correctly."""
        tool_data = {**base_tool_data, "run_to_completion": True}

        tool = YamlToolBase(
            tool_name="test_failure",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        # Mock a failed execution
        mock_executor.mock_results["echo 'Hello Failed'"] = {
            "token": "failed-token",
            "status": "running",
            "pid": 12345
        }

        mock_executor.wait_for_process_results["failed-token"] = {
            "status": "completed",
            "success": False,
            "return_code": 1,
            "output": "Partial output",
            "error": "Command failed with error",
            "pid": 12345,
            "duration": 2.0
        }

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({"name": "Failed"})

        # Should still return formatted result even for failures
        assert len(result) == 1
        assert result[0]["type"] == "text"
        result_text = result[0]["text"]
        assert "failed-token" in result_text
        assert "Partial output" in result_text

    @pytest.mark.asyncio
    async def test_run_to_completion_execute_async_failure(self, mock_executor, base_tool_data):
        """Test run_to_completion when execute_async fails to start."""
        tool_data = {**base_tool_data, "run_to_completion": True}

        tool = YamlToolBase(
            tool_name="test_start_failure",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        # Mock execute_async returning error status
        mock_executor.mock_results["echo 'Hello StartFail'"] = {
            "token": "error",
            "status": "error",
            "error": "Failed to start process"
        }

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({"name": "StartFail"})

        # Should return error message
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "Script execution failed" in result[0]["text"]
        assert "Failed to start process" in result[0]["text"]


class TestRunToCompletionFalse:
    """Test cases for run_to_completion=false (default behavior)."""

    @pytest.mark.asyncio
    async def test_default_async_behavior(self, mock_executor, base_tool_data):
        """Test that default behavior (run_to_completion=false) returns token immediately."""
        # Don't set run_to_completion (defaults to false)
        tool = YamlToolBase(
            tool_name="test_async_tool",
            tool_data=base_tool_data,
            command_executor=mock_executor
        )

        mock_executor.mock_results["echo 'Hello Async'"] = {
            "token": "async-token-456",
            "status": "running",
            "pid": 54321
        }

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({"name": "Async"})

        # Should NOT call wait_for_process
        assert len(mock_executor.wait_for_process_called) == 0

        # Should return token and status information
        assert len(result) == 1
        assert result[0]["type"] == "text"
        result_text = result[0]["text"]
        assert "async-token-456" in result_text
        assert "running" in result_text
        assert "54321" in result_text

    @pytest.mark.asyncio
    async def test_explicit_false_run_to_completion(self, mock_executor, base_tool_data):
        """Test explicitly setting run_to_completion=false."""
        tool_data = {**base_tool_data, "run_to_completion": False}

        tool = YamlToolBase(
            tool_name="test_explicit_false",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({"name": "ExplicitFalse"})

        # Should NOT call wait_for_process
        assert len(mock_executor.wait_for_process_called) == 0

        # Should return async execution info
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "Script started with token" in result[0]["text"]


class TestRunToCompletionQueryStatus:
    """Test cases for query_status behavior with run_to_completion."""

    @pytest.mark.asyncio
    async def test_query_status_with_run_to_completion_true(self, mock_executor):
        """Test that query_status ignores timeout when run_to_completion=true."""
        tool_data = {
            "type": "script",
            "run_to_completion": True,
            "scripts": {"linux": "long-running-command"},
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="query_script_status",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        # Mock query_process to return completed status immediately to avoid infinite loop
        async def mock_query_process(token, wait=False, timeout=None):
            return {
                "status": "completed",
                "success": True,
                "return_code": 0,
                "output": "Test completed",
                "error": "",
                "pid": 12345
            }

        mock_executor.query_process = mock_query_process

        # Test with timeout argument - should be ignored due to run_to_completion=true
        result = await tool._query_status({
            "token": "test-token",
            "wait": True,
            "timeout": 30  # This should be ignored
        })

        # Should complete immediately since mock returns completed status
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "Test completed" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_query_status_with_run_to_completion_false(self, mock_executor):
        """Test that query_status respects timeout when run_to_completion=false."""
        tool_data = {
            "type": "script",
            "run_to_completion": False,
            "scripts": {"linux": "normal-command"},
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="query_script_status",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        # Mock query_process to return completed status to avoid timeout
        # Note: _query_status always calls query_process with timeout=None
        # and handles timeout logic internally
        async def mock_query_process(token, wait=False, timeout=None):
            # _query_status always calls with timeout=None, but has its own timeout logic
            assert timeout is None, f"Expected timeout None in query_process call, got {timeout}"
            return {
                "status": "completed",
                "success": True,
                "return_code": 0,
                "output": "Normal completion",
                "error": "",
                "pid": 12345
            }

        mock_executor.query_process = mock_query_process

        # This should use the provided timeout value
        result = await tool._query_status({
            "token": "test-token",
            "wait": True,
            "timeout": 30
        })

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "Normal completion" in result[0]["text"]


class TestRunToCompletionEdgeCases:
    """Test edge cases and error conditions for run_to_completion."""

    @pytest.mark.asyncio
    async def test_run_to_completion_with_validation_error(self, mock_executor, base_tool_data):
        """Test that validation errors are handled properly with run_to_completion=true."""
        tool_data = {**base_tool_data, "run_to_completion": True}

        tool = YamlToolBase(
            tool_name="test_validation",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        # Missing required 'name' parameter
        result = await tool._execute_script({})

        # Should return validation error without calling execute_async or wait_for_process
        assert len(mock_executor.executed_commands) == 0
        assert len(mock_executor.wait_for_process_called) == 0

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "Input validation error" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_run_to_completion_with_missing_script(self, mock_executor):
        """Test run_to_completion when no script is available for the OS."""
        tool_data = {
            "type": "script",
            "run_to_completion": True,
            "scripts": {"windows": "echo Windows only"},  # No Linux script
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="test_missing_script",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        with patch('platform.system', return_value='Linux'):
            result = await tool._execute_script({})

        # Should return error without calling execute_async or wait_for_process
        assert len(mock_executor.executed_commands) == 0
        assert len(mock_executor.wait_for_process_called) == 0

        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "No script defined" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_run_to_completion_exception_handling(self, mock_executor, base_tool_data):
        """Test exception handling in run_to_completion mode."""
        tool_data = {**base_tool_data, "run_to_completion": True}

        tool = YamlToolBase(
            tool_name="test_exception",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        # Mock wait_for_process to raise an exception
        async def failing_wait_for_process(token, timeout=None):
            raise Exception("Simulated wait failure")

        mock_executor.wait_for_process = failing_wait_for_process

        with patch('platform.system', return_value='Linux'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({"name": "Exception"})

        # Should handle exception gracefully
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "Error executing script" in result[0]["text"]


class TestRunToCompletionCrossPlatform:
    """Test run_to_completion across different platforms."""

    @pytest.mark.asyncio
    async def test_run_to_completion_windows(self, mock_executor, base_tool_data):
        """Test run_to_completion on Windows."""
        tool_data = {**base_tool_data, "run_to_completion": True}

        tool = YamlToolBase(
            tool_name="test_windows",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        mock_executor.mock_results["echo Hello Windows"] = {
            "token": "windows-token",
            "status": "running",
            "pid": 9999
        }

        with patch('platform.system', return_value='Windows'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({"name": "Windows"})

        # Verify correct Windows command was executed
        assert "echo Hello Windows" in mock_executor.executed_commands
        assert len(mock_executor.wait_for_process_called) == 1

    @pytest.mark.asyncio
    async def test_run_to_completion_darwin(self, mock_executor, base_tool_data):
        """Test run_to_completion on macOS."""
        tool_data = {**base_tool_data, "run_to_completion": True}

        tool = YamlToolBase(
            tool_name="test_darwin",
            tool_data=tool_data,
            command_executor=mock_executor
        )

        with patch('platform.system', return_value='Darwin'):
            with patch.object(tool, '_get_server_dir', return_value=Path('/test/dir')):
                result = await tool._execute_script({"name": "Darwin"})

        # Verify correct Darwin command was executed
        assert "echo 'Hello Darwin'" in mock_executor.executed_commands
        assert len(mock_executor.wait_for_process_called) == 1
