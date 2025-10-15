"""Tests for concurrency wait timeout feature.

This module tests the wait timeout feature added to the concurrency control system,
which allows tools to wait for a slot to become available instead of immediately rejecting.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from mcp_tools.yaml_tools import YamlToolBase
from utils.concurrency import ConcurrencyManager, ConcurrencyConfig, OperationContext


class MockCommandExecutor:
    """Mock command executor for testing."""

    def __init__(self):
        self.executed_commands = []

    async def execute_async(self, command: str, timeout=None):
        self.executed_commands.append(command)
        return {
            "token": f"mock_token_{len(self.executed_commands)}",
            "status": "running",
            "pid": 12345,
            "command": command
        }


@pytest.fixture
def concurrency_manager():
    """Provide a fresh concurrency manager for each test."""
    return ConcurrencyManager()


@pytest.fixture
def yaml_tool_with_wait_timeout():
    """Create a YAML tool with concurrency wait timeout."""
    tool_data = {
        "name": "test_wait_tool",
        "description": "Test tool with wait timeout",
        "type": "script",
        "concurrency": {
            "max_concurrent": 1,
            "wait_timeout": 5  # 5 seconds for testing
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            }
        },
        "scripts": {
            "linux": "echo '{message}'",
            "darwin": "echo '{message}'",
            "windows": "echo {message}"
        }
    }
    return YamlToolBase(tool_name="test_wait_tool", tool_data=tool_data)


class TestConcurrencyWaitTimeout:
    """Test concurrency wait timeout functionality."""

    @pytest.mark.asyncio
    async def test_wait_timeout_slot_becomes_available(
        self, yaml_tool_with_wait_timeout, concurrency_manager
    ):
        """Test that tool execution waits and succeeds when a slot becomes available."""
        # Register concurrency config with wait timeout
        config = ConcurrencyConfig(max_concurrent=1, wait_timeout=5)
        concurrency_manager.register_config("test_wait_tool", config)

        # Set up tool
        yaml_tool_with_wait_timeout._command_executor = MockCommandExecutor()

        # Start a blocking operation
        blocking_context = OperationContext(operation_id="blocking_op", operation_type="blocking")
        start_result = concurrency_manager.start_operation("test_wait_tool", blocking_context)
        assert start_result["success"] is True

        # Create a task to finish the blocking operation after 2 seconds
        async def finish_blocking_after_delay():
            await asyncio.sleep(2)
            concurrency_manager.finish_operation("blocking_op")

        # Start the delayed finish task
        finish_task = asyncio.create_task(finish_blocking_after_delay())

        try:
            # Mock the concurrency manager
            with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
                # Execute the tool - should wait and succeed
                result = await yaml_tool_with_wait_timeout.execute_tool({"message": "test"})

            # Verify execution succeeded
            assert isinstance(result, list)
            assert len(result) > 0
            assert len(yaml_tool_with_wait_timeout._command_executor.executed_commands) > 0

        finally:
            # Ensure cleanup
            await finish_task

        # Verify all operations are cleaned up
        active_ops = concurrency_manager.get_active_operations("test_wait_tool")
        assert active_ops["count"] == 0

    @pytest.mark.asyncio
    async def test_wait_timeout_expires(
        self, yaml_tool_with_wait_timeout, concurrency_manager
    ):
        """Test that tool execution times out if no slot becomes available."""
        # Register concurrency config with short wait timeout
        config = ConcurrencyConfig(max_concurrent=1, wait_timeout=2)
        concurrency_manager.register_config("test_wait_tool", config)

        # Set up tool
        yaml_tool_with_wait_timeout._command_executor = MockCommandExecutor()

        # Start a blocking operation that won't be finished
        blocking_context = OperationContext(operation_id="blocking_op", operation_type="blocking")
        start_result = concurrency_manager.start_operation("test_wait_tool", blocking_context)
        assert start_result["success"] is True

        try:
            # Mock the concurrency manager
            with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
                # Execute the tool - should wait and timeout
                result = await yaml_tool_with_wait_timeout.execute_tool({"message": "test"})

            # Verify execution was rejected due to timeout
            assert isinstance(result, dict)
            assert result["success"] is False
            assert result["error"] == "concurrency_limit_exceeded"
            assert "waited" in result["message"]
            assert "waited_seconds" in result
            assert result["waited_seconds"] >= 2  # Should have waited at least 2 seconds

            # Verify no command was executed
            assert len(yaml_tool_with_wait_timeout._command_executor.executed_commands) == 0

        finally:
            # Clean up the blocking operation
            concurrency_manager.finish_operation("blocking_op")

    @pytest.mark.asyncio
    async def test_no_wait_timeout_immediate_rejection(
        self, concurrency_manager
    ):
        """Test that tool without wait_timeout rejects immediately."""
        # Create tool without wait_timeout
        tool_data = {
            "name": "test_no_wait_tool",
            "description": "Test tool without wait timeout",
            "type": "script",
            "concurrency": {
                "max_concurrent": 1
                # No wait_timeout specified
            },
            "inputSchema": {
                "type": "object",
                "properties": {}
            },
            "scripts": {
                "linux": "echo 'test'",
                "darwin": "echo 'test'",
                "windows": "echo test"
            }
        }
        tool = YamlToolBase(tool_name="test_no_wait_tool", tool_data=tool_data)
        tool._command_executor = MockCommandExecutor()

        # Register concurrency config without wait timeout
        config = ConcurrencyConfig(max_concurrent=1, wait_timeout=None)
        concurrency_manager.register_config("test_no_wait_tool", config)

        # Start a blocking operation
        blocking_context = OperationContext(operation_id="blocking_op", operation_type="blocking")
        start_result = concurrency_manager.start_operation("test_no_wait_tool", blocking_context)
        assert start_result["success"] is True

        try:
            # Mock the concurrency manager
            with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
                # Execute the tool - should reject immediately
                import time
                start_time = time.time()
                result = await tool.execute_tool({})
                elapsed = time.time() - start_time

            # Verify execution was rejected immediately (within 0.5 seconds)
            assert elapsed < 0.5
            assert isinstance(result, dict)
            assert result["success"] is False
            assert result["error"] == "concurrency_limit_exceeded"
            assert "waited_seconds" not in result  # Should not have waited

        finally:
            # Clean up the blocking operation
            concurrency_manager.finish_operation("blocking_op")

    @pytest.mark.asyncio
    async def test_wait_timeout_with_multiple_waiters(
        self, yaml_tool_with_wait_timeout, concurrency_manager
    ):
        """Test multiple tools waiting for a slot."""
        # Register concurrency config with wait timeout
        config = ConcurrencyConfig(max_concurrent=1, wait_timeout=5)
        concurrency_manager.register_config("test_wait_tool", config)

        # Create multiple tool instances
        tools = []
        for i in range(3):
            tool = YamlToolBase(
                tool_name="test_wait_tool",
                tool_data=yaml_tool_with_wait_timeout._tool_data
            )
            tool._command_executor = MockCommandExecutor()
            tools.append(tool)

        # Start a blocking operation
        blocking_context = OperationContext(operation_id="blocking_op", operation_type="blocking")
        start_result = concurrency_manager.start_operation("test_wait_tool", blocking_context)
        assert start_result["success"] is True

        # Create a task to finish the blocking operation after 1 second
        async def finish_blocking_after_delay():
            await asyncio.sleep(1)
            concurrency_manager.finish_operation("blocking_op")

        finish_task = asyncio.create_task(finish_blocking_after_delay())

        try:
            # Mock the concurrency manager
            with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
                # Execute all tools concurrently - they should wait and execute one by one
                tasks = [tool.execute_tool({"message": f"test_{i}"}) for i, tool in enumerate(tools)]
                results = await asyncio.gather(*tasks)

            # At least one should succeed (the first one after blocking operation finishes)
            successful_results = [r for r in results if isinstance(r, list)]
            assert len(successful_results) >= 1

            # Some may timeout or succeed depending on timing
            # Just verify the behavior is consistent
            for result in results:
                assert result is not None

        finally:
            # Ensure cleanup
            await finish_task

    @pytest.mark.asyncio
    async def test_wait_timeout_zero_means_no_wait(
        self, concurrency_manager
    ):
        """Test that wait_timeout=0 means no waiting."""
        # Create tool with zero wait_timeout
        tool_data = {
            "name": "test_zero_wait_tool",
            "description": "Test tool with zero wait timeout",
            "type": "script",
            "concurrency": {
                "max_concurrent": 1,
                "wait_timeout": 0
            },
            "inputSchema": {"type": "object", "properties": {}},
            "scripts": {"darwin": "echo 'test'", "linux": "echo 'test'", "windows": "echo test"}
        }
        tool = YamlToolBase(tool_name="test_zero_wait_tool", tool_data=tool_data)
        tool._command_executor = MockCommandExecutor()

        # Register concurrency config with zero wait timeout
        config = ConcurrencyConfig(max_concurrent=1, wait_timeout=0)
        concurrency_manager.register_config("test_zero_wait_tool", config)

        # Start a blocking operation
        blocking_context = OperationContext(operation_id="blocking_op", operation_type="blocking")
        start_result = concurrency_manager.start_operation("test_zero_wait_tool", blocking_context)
        assert start_result["success"] is True

        try:
            # Mock the concurrency manager
            with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
                # Execute the tool - should reject immediately
                import time
                start_time = time.time()
                result = await tool.execute_tool({})
                elapsed = time.time() - start_time

            # Verify execution was rejected immediately
            assert elapsed < 0.5
            assert isinstance(result, dict)
            assert result["success"] is False

        finally:
            # Clean up the blocking operation
            concurrency_manager.finish_operation("blocking_op")
