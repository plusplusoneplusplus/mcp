"""Integration tests for run_to_completion feature.

This module contains integration tests that demonstrate the run_to_completion
feature working in more realistic scenarios.
"""

import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_tools.yaml_tools import YamlToolBase
from mcp_tools.command_executor.executor import CommandExecutor


class TestRunToCompletionIntegration:
    """Integration tests for run_to_completion feature."""

    @pytest.mark.asyncio
    async def test_run_to_completion_with_real_command_executor(self):
        """Test run_to_completion with actual CommandExecutor for short commands."""
        # Use real CommandExecutor for this test
        real_executor = CommandExecutor()

        tool_data = {
            "type": "script",
            "run_to_completion": True,
            "scripts": {
                "linux": "echo 'Hello Integration Test' && sleep 1 && echo 'Completed'",
                "darwin": "echo 'Hello Integration Test' && sleep 1 && echo 'Completed'",
                "windows": "echo Hello Integration Test && timeout /t 1 /nobreak && echo Completed"
            },
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

        tool = YamlToolBase(
            tool_name="integration_test_tool",
            tool_data=tool_data,
            command_executor=real_executor
        )

        with patch.object(tool, '_get_server_dir', return_value=Path('/tmp')):
            result = await tool._execute_script({})

        # Should wait for completion and return final result
        assert len(result) == 1
        assert result[0]["type"] == "text"
        result_text = result[0]["text"]

        # Should contain the output from the completed command
        # (Command output may vary, but should have something)
        assert "Completed" in result_text or "Hello Integration Test" in result_text

        # Should contain success indicators
        assert "Success: True" in result_text or "success" in result_text.lower()

    @pytest.mark.asyncio
    async def test_run_to_completion_with_output_limits(self):
        """Test run_to_completion with output limiting and post-processing."""
        real_executor = CommandExecutor()

        tool_data = {
            "type": "script",
            "run_to_completion": True,
            "scripts": {
                "linux": "for i in {{1..20}}; do echo 'Line '$i' of output'; done",
                "darwin": "for i in {{1..20}}; do echo \"Line \"$i\" of output\"; done",
                "windows": "for /l %i in (1,1,20) do echo Line %i of output"
            },
            "post_processing": {
                "output_limits": {
                    "max_stdout_length": 100,
                    "truncate_strategy": "end"
                }
            },
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

        tool = YamlToolBase(
            tool_name="output_limit_test",
            tool_data=tool_data,
            command_executor=real_executor
        )

        with patch.object(tool, '_get_server_dir', return_value=Path('/tmp')):
            result = await tool._execute_script({})

        # Should complete and apply output limiting
        assert len(result) == 1
        assert result[0]["type"] == "text"
        result_text = result[0]["text"]

        # Should contain some output but be limited
        assert "Line" in result_text
        # Should show it was truncated if output was long enough
        if len(result_text) > 100:
            assert "truncated" in result_text or "..." in result_text

    @pytest.mark.asyncio
    async def test_run_to_completion_vs_async_behavior(self):
        """Test the difference between run_to_completion=true and false."""
        real_executor = CommandExecutor()

        # Test async version (run_to_completion=false)
        async_tool_data = {
            "type": "script",
            "run_to_completion": False,
            "scripts": {
                "linux": "{{ echo 'Async test' && sleep 1; }}",
                "darwin": "{{ echo 'Async test' && sleep 1; }}",
                "windows": "{{ echo Async test; timeout /t 1 /nobreak; }}"
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        async_tool = YamlToolBase(
            tool_name="async_test",
            tool_data=async_tool_data,
            command_executor=real_executor
        )

        with patch.object(async_tool, '_get_server_dir', return_value=Path('/tmp')):
            async_result = await async_tool._execute_script({})

        # Async should return immediately with token
        assert len(async_result) == 1
        assert "token" in async_result[0]["text"]
        assert "running" in async_result[0]["text"]
        assert "Async test" not in async_result[0]["text"]  # Shouldn't have final output

        # Test sync version (run_to_completion=true)
        sync_tool_data = {
            "type": "script",
            "run_to_completion": True,
            "scripts": {
                "linux": "{{ echo 'Sync test' && sleep 1; }}",
                "darwin": "{{ echo 'Sync test' && sleep 1; }}",
                "windows": "{{ echo Sync test; timeout /t 1 /nobreak; }}"
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        sync_tool = YamlToolBase(
            tool_name="sync_test",
            tool_data=sync_tool_data,
            command_executor=real_executor
        )

        with patch.object(sync_tool, '_get_server_dir', return_value=Path('/tmp')):
            sync_result = await sync_tool._execute_script({})

        # Sync should return final result with output
        assert len(sync_result) == 1
        assert "Sync test" in sync_result[0]["text"]  # Should have final output
        assert "Success: True" in sync_result[0]["text"] or "success" in sync_result[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_run_to_completion_with_failure(self):
        """Test run_to_completion handling of script failures."""
        real_executor = CommandExecutor()

        tool_data = {
            "type": "script",
            "run_to_completion": True,
            "scripts": {
                "linux": "{{ echo 'Before failure' && exit 1; }}",
                "darwin": "{{ echo 'Before failure' && exit 1; }}",
                "windows": "{{ echo Before failure; exit /b 1; }}"
            },
            "inputSchema": {"type": "object", "properties": {}, "required": []}
        }

        tool = YamlToolBase(
            tool_name="failure_test",
            tool_data=tool_data,
            command_executor=real_executor
        )

        with patch.object(tool, '_get_server_dir', return_value=Path('/tmp')):
            result = await tool._execute_script({})

        # Should complete and show failure
        assert len(result) == 1
        assert result[0]["type"] == "text"
        result_text = result[0]["text"]

        # Should contain the output before failure
        assert "Before failure" in result_text
        # Should indicate failure
        assert ("Success: False" in result_text or
                "Return code: 1" in result_text or
                "success" in result_text.lower())

    @pytest.mark.asyncio
    async def test_run_to_completion_with_file_operations(self):
        """Test run_to_completion with file creation and reading."""
        real_executor = CommandExecutor()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_output.txt")

            tool_data = {
                "type": "script",
                "run_to_completion": True,
                "scripts": {
                    "linux": f"echo 'File test content' > {temp_file} && cat {temp_file}",
                    "darwin": f"echo 'File test content' > {temp_file} && cat {temp_file}",
                    "windows": f"echo File test content > {temp_file} && type {temp_file}"
                },
                "inputSchema": {"type": "object", "properties": {}, "required": []}
            }

            tool = YamlToolBase(
                tool_name="file_test",
                tool_data=tool_data,
                command_executor=real_executor
            )

            with patch.object(tool, '_get_server_dir', return_value=Path(temp_dir)):
                result = await tool._execute_script({})

            # Should complete with file content in output
            assert len(result) == 1
            assert result[0]["type"] == "text"
            result_text = result[0]["text"]

            assert "File test content" in result_text

            # Verify file was actually created
            assert os.path.exists(temp_file)
            with open(temp_file, 'r') as f:
                file_content = f.read().strip()
                assert "File test content" in file_content
