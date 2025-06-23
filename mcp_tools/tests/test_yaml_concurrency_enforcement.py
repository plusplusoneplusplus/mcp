"""Tests for concurrency enforcement in YAML tool execution.

This module provides comprehensive test coverage for the concurrency control
enforcement feature implemented in Issue #334.

Tests cover:
1. Concurrency limit enforcement during tool execution
2. Operation lifecycle management (start/finish)
3. Error handling for concurrency violations
4. Integration with existing concurrency manager
5. Async tool execution with concurrency controls
6. Edge cases and error scenarios
"""

import pytest
import asyncio
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional

from mcp_tools.yaml_tools import YamlToolBase
from utils.concurrency import ConcurrencyManager, ConcurrencyConfig, OperationContext
from mcp_tools.interfaces import CommandExecutorInterface


class MockCommandExecutor(CommandExecutorInterface):
    """Mock command executor for testing."""

    def __init__(self):
        self.executed_commands = []
        self.async_results = []
        self.mock_results = {}

    @property
    def name(self) -> str:
        return "mock_command_executor"

    @property
    def description(self) -> str:
        return "Mock command executor for testing"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        return {"success": True}

    def execute(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        self.executed_commands.append(command)
        return self.mock_results.get(command, {"status": "completed", "returncode": 0})

    async def execute_async(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        self.executed_commands.append(command)
        result = {
            "token": f"mock_token_{len(self.executed_commands)}",
            "status": "running",
            "pid": 12345,
            "command": command
        }
        self.async_results.append(result)
        return result

    async def query_process(self, token: str, wait: bool = False, timeout: Optional[float] = None) -> Dict[str, Any]:
        return {"status": "completed", "returncode": 0}

    def terminate_by_token(self, token: str) -> bool:
        return True

    def list_running_processes(self) -> list:
        return []

    async def start_periodic_status_reporter(self, interval: float = 30.0, enabled: bool = True) -> None:
        pass

    async def stop_periodic_status_reporter(self) -> None:
        pass


@pytest.fixture
def mock_command_executor():
    """Provide a mock command executor."""
    return MockCommandExecutor()


@pytest.fixture
def concurrency_manager():
    """Provide a fresh concurrency manager for each test."""
    return ConcurrencyManager()


@pytest.fixture
def yaml_tool_with_concurrency():
    """Create a YAML tool with concurrency configuration."""
    tool_data = {
        "name": "test_concurrent_tool",
        "description": "Test tool with concurrency limits",
        "type": "script",
        "concurrency": {
            "max_concurrent": 1
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        },
        "scripts": {
            "linux": "echo '{message}'",
            "darwin": "echo '{message}'",
            "windows": "echo {message}"
        }
    }
    return YamlToolBase(tool_name="test_concurrent_tool", tool_data=tool_data)


@pytest.fixture
def yaml_tool_no_concurrency():
    """Create a YAML tool without concurrency configuration."""
    tool_data = {
        "name": "test_unlimited_tool",
        "description": "Test tool without concurrency limits",
        "type": "script",
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
    return YamlToolBase(tool_name="test_unlimited_tool", tool_data=tool_data)


class TestConcurrencyEnforcementBasic:
    """Test basic concurrency enforcement functionality."""

    @pytest.mark.asyncio
    async def test_tool_execution_with_concurrency_allowed(
        self, yaml_tool_with_concurrency, mock_command_executor, concurrency_manager
    ):
        """Test that tool execution proceeds when concurrency limit is not exceeded."""
        # Register concurrency config
        config = ConcurrencyConfig(max_concurrent=2)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Set up tool with dependencies
        yaml_tool_with_concurrency._command_executor = mock_command_executor

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            result = await yaml_tool_with_concurrency.execute_tool({"message": "test"})

        # Verify execution completed successfully
        assert isinstance(result, list)
        assert len(result) > 0
        assert len(mock_command_executor.executed_commands) > 0

        # Verify no active operations remain
        active_ops = concurrency_manager.get_active_operations("test_concurrent_tool")
        assert active_ops["count"] == 0

    @pytest.mark.asyncio
    async def test_tool_execution_with_concurrency_rejected(
        self, yaml_tool_with_concurrency, mock_command_executor, concurrency_manager
    ):
        """Test that tool execution is rejected when concurrency limit is exceeded."""
        # Register concurrency config with limit of 1
        config = ConcurrencyConfig(max_concurrent=1)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Start one operation manually to fill the limit
        context = OperationContext(operation_id="blocking_op", operation_type="test")
        start_result = concurrency_manager.start_operation("test_concurrent_tool", context)
        assert start_result["success"] is True

        # Set up tool with dependencies
        yaml_tool_with_concurrency._command_executor = mock_command_executor

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            result = await yaml_tool_with_concurrency.execute_tool({"message": "test"})

        # Verify execution was rejected
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["error"] == "concurrency_limit_exceeded"
        assert "maximum concurrent operations" in result["message"]
        assert result["current_operations"] == 1
        assert result["max_allowed"] == 1
        assert result["tool_name"] == "test_concurrent_tool"

        # Verify no command was executed
        assert len(mock_command_executor.executed_commands) == 0

    @pytest.mark.asyncio
    async def test_tool_execution_without_concurrency_config(
        self, yaml_tool_no_concurrency, mock_command_executor, concurrency_manager
    ):
        """Test that tools without concurrency config execute without limits."""
        # Set up tool with dependencies
        yaml_tool_no_concurrency._command_executor = mock_command_executor

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            result = await yaml_tool_no_concurrency.execute_tool({"message": "test"})

        # Verify execution completed successfully
        assert isinstance(result, list)
        assert len(result) > 0
        assert len(mock_command_executor.executed_commands) > 0

    @pytest.mark.asyncio
    async def test_operation_lifecycle_management(
        self, yaml_tool_with_concurrency, mock_command_executor, concurrency_manager
    ):
        """Test that operations are properly tracked throughout their lifecycle."""
        # Register concurrency config
        config = ConcurrencyConfig(max_concurrent=2)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Set up tool with dependencies
        yaml_tool_with_concurrency._command_executor = mock_command_executor

        # Track operation lifecycle
        operation_ids = []
        original_start = concurrency_manager.start_operation
        original_finish = concurrency_manager.finish_operation

        def track_start(tool_name, context):
            operation_ids.append(context.operation_id)
            return original_start(tool_name, context)

        def track_finish(operation_id):
            assert operation_id in operation_ids
            return original_finish(operation_id)

        concurrency_manager.start_operation = track_start
        concurrency_manager.finish_operation = track_finish

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            result = await yaml_tool_with_concurrency.execute_tool({"message": "test"})

        # Verify operation was tracked
        assert len(operation_ids) == 1
        assert isinstance(result, list)

        # Verify operation was cleaned up
        active_ops = concurrency_manager.get_active_operations("test_concurrent_tool")
        assert active_ops["count"] == 0


class TestConcurrencyEnforcementErrorHandling:
    """Test error handling in concurrency enforcement."""

    @pytest.mark.asyncio
    async def test_execution_error_with_operation_cleanup(
        self, yaml_tool_with_concurrency, concurrency_manager
    ):
        """Test that operations are cleaned up even when execution fails."""
        # Register concurrency config
        config = ConcurrencyConfig(max_concurrent=1)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Set up tool with failing command executor
        failing_executor = MagicMock()
        failing_executor.execute_async = AsyncMock(side_effect=Exception("Execution failed"))
        yaml_tool_with_concurrency._command_executor = failing_executor

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            # Execution should fail but not raise exception
            try:
                result = await yaml_tool_with_concurrency.execute_tool({"message": "test"})
                # If we get here, the exception was handled
                assert True
            except Exception:
                # If exception propagates, that's also acceptable
                pass

        # Verify operation was cleaned up despite the error
        active_ops = concurrency_manager.get_active_operations("test_concurrent_tool")
        assert active_ops["count"] == 0

    @pytest.mark.asyncio
    async def test_start_operation_failure_handling(
        self, yaml_tool_with_concurrency, mock_command_executor, concurrency_manager
    ):
        """Test handling of start_operation failures."""
        # Register concurrency config
        config = ConcurrencyConfig(max_concurrent=1)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Mock start_operation to fail
        original_start = concurrency_manager.start_operation
        def failing_start(tool_name, context):
            return {"success": False, "error": "start_failed", "message": "Failed to start operation"}

        concurrency_manager.start_operation = failing_start

        # Set up tool with dependencies
        yaml_tool_with_concurrency._command_executor = mock_command_executor

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            result = await yaml_tool_with_concurrency.execute_tool({"message": "test"})

        # Verify execution was rejected due to start failure
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["error"] == "Failed to start operation tracking"

        # Verify no command was executed
        assert len(mock_command_executor.executed_commands) == 0

    @pytest.mark.asyncio
    async def test_finish_operation_failure_handling(
        self, yaml_tool_with_concurrency, mock_command_executor, concurrency_manager
    ):
        """Test handling of finish_operation failures."""
        # Register concurrency config
        config = ConcurrencyConfig(max_concurrent=1)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Mock finish_operation to fail
        original_finish = concurrency_manager.finish_operation
        def failing_finish(operation_id):
            return {"success": False, "error": "finish_failed", "message": "Failed to finish operation"}

        concurrency_manager.finish_operation = failing_finish

        # Set up tool with dependencies
        yaml_tool_with_concurrency._command_executor = mock_command_executor

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            result = await yaml_tool_with_concurrency.execute_tool({"message": "test"})

        # Verify execution completed despite finish failure
        assert isinstance(result, list)
        assert len(result) > 0
        assert len(mock_command_executor.executed_commands) > 0


class TestConcurrencyEnforcementConcurrentExecution:
    """Test concurrent execution scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_executions_within_limit(
        self, yaml_tool_with_concurrency, mock_command_executor, concurrency_manager
    ):
        """Test multiple concurrent executions within the concurrency limit."""
        # Register concurrency config with limit of 3
        config = ConcurrencyConfig(max_concurrent=3)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Create multiple tool instances
        tools = []
        for i in range(3):
            tool = YamlToolBase(
                tool_name="test_concurrent_tool",
                tool_data=yaml_tool_with_concurrency._tool_data,
                command_executor=MockCommandExecutor()
            )
            tools.append(tool)

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            # Execute tools concurrently
            tasks = [tool.execute_tool({"message": f"test_{i}"}) for i, tool in enumerate(tools)]
            results = await asyncio.gather(*tasks)

        # Verify all executions completed successfully
        assert len(results) == 3
        for result in results:
            assert isinstance(result, list)
            assert len(result) > 0

        # Verify all operations were cleaned up
        active_ops = concurrency_manager.get_active_operations("test_concurrent_tool")
        assert active_ops["count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_concurrent_executions_exceeding_limit(
        self, yaml_tool_with_concurrency, concurrency_manager
    ):
        """Test multiple concurrent executions exceeding the concurrency limit."""
        # Register concurrency config with limit of 1 (more restrictive)
        config = ConcurrencyConfig(max_concurrent=1)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Pre-fill the concurrency limit by starting one operation manually
        blocking_context = OperationContext(operation_id="blocking_op", operation_type="blocking")
        start_result = concurrency_manager.start_operation("test_concurrent_tool", blocking_context)
        assert start_result["success"] is True

        try:
            # Create multiple tool instances that should all be rejected
            tools = []
            for i in range(3):
                tool = YamlToolBase(
                    tool_name="test_concurrent_tool",
                    tool_data=yaml_tool_with_concurrency._tool_data,
                    command_executor=MockCommandExecutor()
                )
                tools.append(tool)

            # Mock the concurrency manager
            with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
                # Execute tools concurrently - all should be rejected
                tasks = [tool.execute_tool({"message": f"test_{i}"}) for i, tool in enumerate(tools)]
                results = await asyncio.gather(*tasks)

            # Verify results - all should be rejected since limit is already filled
            assert len(results) == 3

            successful_results = [r for r in results if isinstance(r, list)]
            rejected_results = [r for r in results if isinstance(r, dict) and not r.get("success", True)]

            # All should be rejected due to the blocking operation
            assert len(successful_results) == 0
            assert len(rejected_results) == 3

            # Verify rejected results have correct error format
            for result in rejected_results:
                assert result["error"] == "concurrency_limit_exceeded"
                assert "maximum concurrent operations" in result["message"]
                assert result["current_operations"] == 1
                assert result["max_allowed"] == 1

        finally:
            # Clean up the blocking operation
            concurrency_manager.finish_operation("blocking_op")

        # Verify all operations were cleaned up
        active_ops = concurrency_manager.get_active_operations("test_concurrent_tool")
        assert active_ops["count"] == 0


class TestConcurrencyEnforcementIntegration:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_integration_with_different_tool_types(self, concurrency_manager):
        """Test concurrency enforcement with different tool types."""
        # Test with task-type tool
        task_tool_data = {
            "name": "test_task_tool",
            "description": "Test task tool with concurrency",
            "type": "task",
            "concurrency": {"max_concurrent": 1},
            "inputSchema": {"type": "object", "properties": {}}
        }

        task_tool = YamlToolBase(
            tool_name="test_task_tool",
            tool_data=task_tool_data,
            command_executor=MockCommandExecutor()
        )

        # Register concurrency config
        config = ConcurrencyConfig(max_concurrent=1)
        concurrency_manager.register_config("test_task_tool", config)

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            result = await task_tool.execute_tool({})

        # Verify execution completed (even if not fully implemented)
        assert result is not None

        # Verify operation was cleaned up
        active_ops = concurrency_manager.get_active_operations("test_task_tool")
        assert active_ops["count"] == 0

    @pytest.mark.asyncio
    async def test_unique_operation_id_generation(
        self, yaml_tool_with_concurrency, mock_command_executor, concurrency_manager
    ):
        """Test that unique operation IDs are generated for each execution."""
        # Register concurrency config
        config = ConcurrencyConfig(max_concurrent=5)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Set up tool with dependencies
        yaml_tool_with_concurrency._command_executor = mock_command_executor

        # Track generated operation IDs
        operation_ids = []
        original_start = concurrency_manager.start_operation

        def track_operation_id(tool_name, context):
            operation_ids.append(context.operation_id)
            return original_start(tool_name, context)

        concurrency_manager.start_operation = track_operation_id

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            # Execute tool multiple times
            for i in range(3):
                result = await yaml_tool_with_concurrency.execute_tool({"message": f"test_{i}"})
                assert isinstance(result, list)

        # Verify unique operation IDs were generated
        assert len(operation_ids) == 3
        assert len(set(operation_ids)) == 3  # All unique

        # Verify all operations were cleaned up
        active_ops = concurrency_manager.get_active_operations("test_concurrent_tool")
        assert active_ops["count"] == 0

    @pytest.mark.asyncio
    async def test_operation_context_properties(
        self, yaml_tool_with_concurrency, mock_command_executor, concurrency_manager
    ):
        """Test that operation context has correct properties."""
        # Register concurrency config
        config = ConcurrencyConfig(max_concurrent=1)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Set up tool with dependencies
        yaml_tool_with_concurrency._command_executor = mock_command_executor

        # Track operation context
        operation_contexts = []
        original_start = concurrency_manager.start_operation

        def track_context(tool_name, context):
            operation_contexts.append(context)
            return original_start(tool_name, context)

        concurrency_manager.start_operation = track_context

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            result = await yaml_tool_with_concurrency.execute_tool({"message": "test"})

        # Verify operation context properties
        assert len(operation_contexts) == 1
        context = operation_contexts[0]

        assert context.operation_type == "tool_execution"
        assert context.operation_id is not None
        assert len(context.operation_id) > 0
        assert context.start_time is not None

        # Verify result
        assert isinstance(result, list)


class TestConcurrencyEnforcementEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_no_command_executor_with_concurrency(
        self, yaml_tool_with_concurrency, concurrency_manager
    ):
        """Test tool execution when command executor is not available."""
        # Register concurrency config
        config = ConcurrencyConfig(max_concurrent=1)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Set tool with no command executor
        yaml_tool_with_concurrency._command_executor = None

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            result = await yaml_tool_with_concurrency.execute_tool({"message": "test"})

        # Verify execution was rejected due to missing command executor
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["error"] == "Command executor not available"

        # Verify no operations were started
        active_ops = concurrency_manager.get_active_operations("test_concurrent_tool")
        assert active_ops["count"] == 0

    @pytest.mark.asyncio
    async def test_concurrency_manager_unavailable(
        self, yaml_tool_with_concurrency, mock_command_executor
    ):
        """Test handling when concurrency manager is unavailable."""
        # Set up tool with dependencies
        yaml_tool_with_concurrency._command_executor = mock_command_executor

        # Mock get_concurrency_manager to raise exception
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', side_effect=Exception("Manager unavailable")):
            # Execution should fail gracefully
            with pytest.raises(Exception):
                await yaml_tool_with_concurrency.execute_tool({"message": "test"})

    @pytest.mark.asyncio
    async def test_zero_concurrency_limit(self, yaml_tool_with_concurrency, mock_command_executor, concurrency_manager):
        """Test behavior with zero concurrency limit."""
        # Register concurrency config with zero limit
        config = ConcurrencyConfig(max_concurrent=0)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Set up tool with dependencies
        yaml_tool_with_concurrency._command_executor = mock_command_executor

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            result = await yaml_tool_with_concurrency.execute_tool({"message": "test"})

        # Verify execution was rejected
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["error"] == "concurrency_limit_exceeded"
        assert result["max_allowed"] == 0

        # Verify no command was executed
        assert len(mock_command_executor.executed_commands) == 0


class TestConcurrencyEnforcementPerformance:
    """Test performance aspects of concurrency enforcement."""

    @pytest.mark.asyncio
    async def test_concurrency_overhead_minimal(
        self, yaml_tool_no_concurrency, mock_command_executor, concurrency_manager
    ):
        """Test that concurrency enforcement adds minimal overhead for unlimited tools."""
        import time

        # Set up tool with dependencies
        yaml_tool_no_concurrency._command_executor = mock_command_executor

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            # Measure execution time
            start_time = time.time()
            result = await yaml_tool_no_concurrency.execute_tool({"message": "test"})
            end_time = time.time()

        # Verify execution completed successfully
        assert isinstance(result, list)
        assert len(result) > 0

        # Verify execution was reasonably fast (less than 1 second for mock)
        execution_time = end_time - start_time
        assert execution_time < 1.0

    @pytest.mark.asyncio
    async def test_high_concurrency_limit_handling(
        self, yaml_tool_with_concurrency, mock_command_executor, concurrency_manager
    ):
        """Test handling of very high concurrency limits."""
        # Register concurrency config with high limit
        config = ConcurrencyConfig(max_concurrent=1000)
        concurrency_manager.register_config("test_concurrent_tool", config)

        # Set up tool with dependencies
        yaml_tool_with_concurrency._command_executor = mock_command_executor

        # Mock the concurrency manager
        with patch('mcp_tools.yaml_tools.get_concurrency_manager', return_value=concurrency_manager):
            result = await yaml_tool_with_concurrency.execute_tool({"message": "test"})

        # Verify execution completed successfully
        assert isinstance(result, list)
        assert len(result) > 0
        assert len(mock_command_executor.executed_commands) > 0

        # Verify operation was cleaned up
        active_ops = concurrency_manager.get_active_operations("test_concurrent_tool")
        assert active_ops["count"] == 0
