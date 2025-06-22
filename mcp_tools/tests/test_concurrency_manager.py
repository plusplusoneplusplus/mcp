"""Tests for the concurrency manager functionality."""

import pytest
import threading
import time as time_module
from unittest.mock import patch

from utils.concurrency import (
    ConcurrencyManager,
    ConcurrencyConfig,
    OperationContext,
    get_concurrency_manager,
    parse_concurrency_config
)


class TestConcurrencyConfig:
    """Test ConcurrencyConfig functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ConcurrencyConfig()
        assert config.max_concurrent == 1

    def test_custom_config(self):
        """Test custom configuration."""
        config = ConcurrencyConfig(max_concurrent=3)
        assert config.max_concurrent == 3


class TestOperationContext:
    """Test OperationContext functionality."""

    def test_basic_context(self):
        """Test basic operation context creation."""
        context = OperationContext(
            operation_id="test_op_123",
            operation_type="test_operation"
        )

        assert context.operation_id == "test_op_123"
        assert context.operation_type == "test_operation"
        assert context.start_time is not None

    def test_default_operation_type(self):
        """Test default operation type."""
        context = OperationContext(operation_id="test_op")
        assert context.operation_type == "operation"


class TestConcurrencyManager:
    """Test ConcurrencyManager functionality."""

    @pytest.fixture
    def manager(self):
        """Create a fresh concurrency manager for each test."""
        return ConcurrencyManager()

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return ConcurrencyConfig(max_concurrent=2)

    @pytest.fixture
    def context(self):
        """Create a test operation context."""
        return OperationContext(
            operation_id="test_op_123",
            operation_type="test_operation"
        )

    def test_register_config(self, manager, config):
        """Test registering concurrency configuration."""
        manager.register_config("test_tool", config)
        assert "test_tool" in manager._configs
        assert manager._configs["test_tool"] == config

    def test_can_start_operation_no_config(self, manager, context):
        """Test that operations are allowed when no config is registered."""
        result = manager.can_start_operation("unknown_tool", context)
        assert result["allowed"] is True

    def test_can_start_operation_within_limit(self, manager, config, context):
        """Test that operations are allowed within the limit."""
        manager.register_config("test_tool", config)

        result = manager.can_start_operation("test_tool", context)
        assert result["allowed"] is True

    def test_can_start_operation_exceeds_limit(self, manager, config):
        """Test that operations are rejected when limit is exceeded."""
        manager.register_config("test_tool", config)

        # Start operations up to the limit
        for i in range(config.max_concurrent):
            context = OperationContext(
                operation_id=f"test_op_{i}",
                operation_type="test_operation"
            )
            result = manager.start_operation("test_tool", context)
            assert result["success"] is True

        # Next operation should be rejected
        context = OperationContext(
            operation_id="test_op_overflow",
            operation_type="test_operation"
        )
        result = manager.can_start_operation("test_tool", context)
        assert result["allowed"] is False
        assert result["error"] == "concurrency_limit_exceeded"
        assert result["current_operations"] == config.max_concurrent
        assert result["max_allowed"] == config.max_concurrent

    def test_start_and_finish_operation(self, manager, config, context):
        """Test starting and finishing operations."""
        manager.register_config("test_tool", config)

        # Start operation
        result = manager.start_operation("test_tool", context)
        assert result["success"] is True

        # Check that operation is tracked
        active_ops = manager.get_active_operations("test_tool")
        assert active_ops["count"] == 1

        # Finish operation
        result = manager.finish_operation(context.operation_id)
        assert result["success"] is True

        # Check that operation is no longer tracked
        active_ops = manager.get_active_operations("test_tool")
        assert active_ops["count"] == 0

    def test_finish_unknown_operation(self, manager):
        """Test finishing an unknown operation."""
        result = manager.finish_operation("unknown_op")
        assert result["success"] is False
        assert result["error"] == "operation_not_found"

    def test_different_tools(self, manager):
        """Test that different tools are tracked separately."""
        config = ConcurrencyConfig(max_concurrent=1)
        manager.register_config("tool1", config)
        manager.register_config("tool2", config)

        # Start operation for first tool
        context1 = OperationContext(
            operation_id="op1",
            operation_type="test_operation"
        )
        result = manager.start_operation("tool1", context1)
        assert result["success"] is True

        # Start operation for second tool (should be allowed)
        context2 = OperationContext(
            operation_id="op2",
            operation_type="test_operation"
        )
        result = manager.start_operation("tool2", context2)
        assert result["success"] is True

        # Start another operation for first tool (should be rejected)
        context3 = OperationContext(
            operation_id="op3",
            operation_type="test_operation"
        )
        result = manager.start_operation("tool1", context3)
        assert result["success"] is False

    def test_get_active_operations_all(self, manager, config):
        """Test getting all active operations."""
        manager.register_config("test_tool", config)

        # Start some operations
        contexts = []
        for i in range(2):
            context = OperationContext(
                operation_id=f"op_{i}",
                operation_type="test_operation"
            )
            contexts.append(context)
            manager.start_operation("test_tool", context)

        # Get all active operations
        active_ops = manager.get_active_operations()
        assert "test_tool" in active_ops
        assert active_ops["test_tool"]["count"] == 2
        assert len(active_ops["test_tool"]["operations"]) == 2

    def test_get_active_operations_by_tool(self, manager, config):
        """Test getting active operations for a specific tool."""
        manager.register_config("test_tool", config)

        context = OperationContext(
            operation_id="test_op",
            operation_type="test_operation"
        )
        manager.start_operation("test_tool", context)

        # Get operations for specific tool
        active_ops = manager.get_active_operations("test_tool")
        assert active_ops["tool_name"] == "test_tool"
        assert active_ops["count"] == 1
        assert len(active_ops["operations"]) == 1
        assert active_ops["operations"][0]["operation_id"] == "test_op"


class TestConcurrencyManagerThreadSafety:
    """Test thread safety of the concurrency manager."""

    def test_concurrent_operations(self):
        """Test concurrent access to the concurrency manager."""
        manager = ConcurrencyManager()
        config = ConcurrencyConfig(max_concurrent=3)
        manager.register_config("test_tool", config)

        results = []
        errors = []

        def start_operation(op_id):
            try:
                context = OperationContext(
                    operation_id=f"op_{op_id}",
                    operation_type="test_operation"
                )
                result = manager.start_operation("test_tool", context)
                results.append((op_id, result))

                # Simulate some work
                time_module.sleep(0.1)

                # Finish the operation
                manager.finish_operation(context.operation_id)
            except Exception as e:
                errors.append((op_id, str(e)))

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=start_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(results) == 5

        # Some operations should succeed, some should fail due to concurrency limits
        successful = [r for r in results if r[1]["success"]]
        failed = [r for r in results if not r[1]["success"]]

        # At least some should succeed and some should fail
        assert len(successful) >= 1
        assert len(failed) >= 1


class TestParseConcurrencyConfig:
    """Test parsing concurrency configuration from YAML data."""

    def test_parse_basic_config(self):
        """Test parsing basic configuration."""
        config_data = {
            "max_concurrent": 5
        }
        config = parse_concurrency_config(config_data)
        assert config.max_concurrent == 5

    def test_parse_config_with_defaults(self):
        """Test parsing configuration with default values."""
        config_data = {}
        config = parse_concurrency_config(config_data)
        assert config.max_concurrent == 1

    def test_parse_empty_config(self):
        """Test parsing empty configuration."""
        config = parse_concurrency_config({})
        assert config.max_concurrent == 1


class TestGlobalConcurrencyManager:
    """Test global concurrency manager instance."""

    def test_get_global_instance(self):
        """Test getting the global concurrency manager instance."""
        manager1 = get_concurrency_manager()
        manager2 = get_concurrency_manager()

        # Should return the same instance
        assert manager1 is manager2
        assert isinstance(manager1, ConcurrencyManager)


class TestConcurrencyManagerEdgeCases:
    """Test edge cases and error conditions for concurrency manager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh concurrency manager for each test."""
        return ConcurrencyManager()

    def test_cleanup_stale_operations(self, manager):
        """Test cleanup of stale operations."""
        config = ConcurrencyConfig(max_concurrent=5)
        manager.register_config("test_tool", config)

        # Start some operations
        contexts = []
        for i in range(3):
            context = OperationContext(
                operation_id=f"op_{i}",
                operation_type="test_operation"
            )
            contexts.append(context)
            manager.start_operation("test_tool", context)

        # Mock time to make operations appear stale
        with patch('time.time') as mock_time:
            # Current time is 3700 seconds after start
            mock_time.return_value = contexts[0].start_time + 3700

            # Cleanup with 1 hour threshold
            result = manager.cleanup_stale_operations(max_age_seconds=3600)

            assert result["cleaned_count"] == 3
            assert result["max_age_seconds"] == 3600
            assert len(result["stale_operations"]) == 3

        # Verify operations were cleaned up
        active_ops = manager.get_active_operations("test_tool")
        assert active_ops["count"] == 0

    def test_cleanup_no_stale_operations(self, manager):
        """Test cleanup when no operations are stale."""
        config = ConcurrencyConfig(max_concurrent=2)
        manager.register_config("test_tool", config)

        # Start a recent operation
        context = OperationContext(
            operation_id="recent_op",
            operation_type="test_operation"
        )
        manager.start_operation("test_tool", context)

        # Cleanup with 1 hour threshold (operation is recent)
        result = manager.cleanup_stale_operations(max_age_seconds=3600)

        assert result["cleaned_count"] == 0
        assert result["max_age_seconds"] == 3600
        assert len(result["stale_operations"]) == 0

        # Verify operation is still active
        active_ops = manager.get_active_operations("test_tool")
        assert active_ops["count"] == 1

    def test_operation_duration_tracking(self, manager):
        """Test that operation durations are tracked correctly."""
        config = ConcurrencyConfig(max_concurrent=3)
        manager.register_config("test_tool", config)

        # Start operation
        context = OperationContext(
            operation_id="duration_test",
            operation_type="test_operation"
        )
        manager.start_operation("test_tool", context)

        # Wait a bit
        time_module.sleep(0.1)

        # Check duration
        active_ops = manager.get_active_operations("test_tool")
        operation = active_ops["operations"][0]
        assert operation["duration"] > 0.05  # Should be at least 50ms
        assert operation["operation_id"] == "duration_test"
        assert operation["operation_type"] == "test_operation"

    def test_multiple_tools_isolation(self, manager):
        """Test that operations for different tools are properly isolated."""
        config1 = ConcurrencyConfig(max_concurrent=1)
        config2 = ConcurrencyConfig(max_concurrent=2)

        manager.register_config("tool1", config1)
        manager.register_config("tool2", config2)

        # Fill up tool1
        context1 = OperationContext(operation_id="tool1_op1", operation_type="op")
        result = manager.start_operation("tool1", context1)
        assert result["success"] is True

        # tool1 should be at capacity
        context1_overflow = OperationContext(operation_id="tool1_op2", operation_type="op")
        result = manager.start_operation("tool1", context1_overflow)
        assert result["success"] is False

        # tool2 should still accept operations
        context2_1 = OperationContext(operation_id="tool2_op1", operation_type="op")
        result = manager.start_operation("tool2", context2_1)
        assert result["success"] is True

        context2_2 = OperationContext(operation_id="tool2_op2", operation_type="op")
        result = manager.start_operation("tool2", context2_2)
        assert result["success"] is True

        # tool2 should now be at capacity
        context2_overflow = OperationContext(operation_id="tool2_op3", operation_type="op")
        result = manager.start_operation("tool2", context2_overflow)
        assert result["success"] is False

        # Check active operations
        all_ops = manager.get_active_operations()
        assert all_ops["tool1"]["count"] == 1
        assert all_ops["tool2"]["count"] == 2

    def test_start_operation_without_config(self, manager):
        """Test starting operations for tools without registered configs."""
        context = OperationContext(
            operation_id="unregistered_op",
            operation_type="test_operation"
        )

        # Should succeed even without config
        result = manager.start_operation("unregistered_tool", context)
        assert result["success"] is True

        # Operation should be tracked in contexts but not in active_operations
        assert context.operation_id in manager._operation_contexts
        assert "unregistered_tool" not in manager._active_operations

        # Cleanup should work
        result = manager.finish_operation(context.operation_id)
        assert result["success"] is True

    def test_get_active_operations_empty_tool(self, manager):
        """Test getting active operations for a tool with no operations."""
        config = ConcurrencyConfig(max_concurrent=1)
        manager.register_config("empty_tool", config)

        active_ops = manager.get_active_operations("empty_tool")
        assert active_ops["tool_name"] == "empty_tool"
        assert active_ops["count"] == 0
        assert active_ops["operations"] == []

    def test_get_active_operations_unknown_tool(self, manager):
        """Test getting active operations for an unknown tool."""
        active_ops = manager.get_active_operations("unknown_tool")
        assert active_ops["tool_name"] == "unknown_tool"
        assert active_ops["count"] == 0
        assert active_ops["operations"] == []

    def test_operation_context_auto_start_time(self):
        """Test that OperationContext automatically sets start_time."""
        start_time_before = time_module.time()
        context = OperationContext(operation_id="test_op")
        start_time_after = time_module.time()

        assert start_time_before <= context.start_time <= start_time_after

    def test_operation_context_explicit_start_time(self):
        """Test that OperationContext accepts explicit start_time."""
        explicit_time = 1234567890.0
        context = OperationContext(
            operation_id="test_op",
            start_time=explicit_time
        )

        assert context.start_time == explicit_time

    def test_concurrency_config_validation(self):
        """Test ConcurrencyConfig with various values."""
        # Test with zero (edge case)
        config = ConcurrencyConfig(max_concurrent=0)
        assert config.max_concurrent == 0

        # Test with large number
        config = ConcurrencyConfig(max_concurrent=1000)
        assert config.max_concurrent == 1000

    def test_register_config_overwrite(self, manager):
        """Test that registering a config overwrites the previous one."""
        config1 = ConcurrencyConfig(max_concurrent=1)
        config2 = ConcurrencyConfig(max_concurrent=5)

        manager.register_config("test_tool", config1)
        assert manager._configs["test_tool"].max_concurrent == 1

        manager.register_config("test_tool", config2)
        assert manager._configs["test_tool"].max_concurrent == 5

    def test_finish_operation_cleanup_empty_sets(self, manager):
        """Test that empty operation sets are cleaned up when finishing operations."""
        config = ConcurrencyConfig(max_concurrent=2)
        manager.register_config("test_tool", config)

        # Start and finish an operation
        context = OperationContext(operation_id="cleanup_test", operation_type="test")
        manager.start_operation("test_tool", context)

        # Verify tool is in active_operations
        assert "test_tool" in manager._active_operations

        # Finish the operation
        manager.finish_operation(context.operation_id)

        # Verify empty set was cleaned up
        assert "test_tool" not in manager._active_operations

    def test_error_message_content(self, manager):
        """Test that error messages contain expected information."""
        config = ConcurrencyConfig(max_concurrent=1)
        manager.register_config("test_tool", config)

        # Start operation to reach limit
        context1 = OperationContext(operation_id="op1", operation_type="test")
        manager.start_operation("test_tool", context1)

        # Try to start another operation
        context2 = OperationContext(operation_id="op2", operation_type="test")
        result = manager.can_start_operation("test_tool", context2)

        assert result["allowed"] is False
        assert result["error"] == "concurrency_limit_exceeded"
        assert "maximum concurrent operations (1) already running" in result["message"]
        assert "test_tool" in result["message"]
        assert result["retry_after"] == "Please wait for the current operation to complete before retrying"
        assert result["current_operations"] == 1
        assert result["max_allowed"] == 1
        assert result["tool_name"] == "test_tool"


class TestConcurrencyManagerPerformance:
    """Test performance characteristics of the concurrency manager."""

    def test_large_number_of_operations(self):
        """Test handling a large number of operations efficiently."""
        manager = ConcurrencyManager()
        config = ConcurrencyConfig(max_concurrent=100)
        manager.register_config("test_tool", config)

        # Start many operations
        contexts = []
        for i in range(100):
            context = OperationContext(
                operation_id=f"perf_op_{i}",
                operation_type="performance_test"
            )
            contexts.append(context)
            result = manager.start_operation("test_tool", context)
            assert result["success"] is True

        # Verify all operations are tracked
        active_ops = manager.get_active_operations("test_tool")
        assert active_ops["count"] == 100

        # Finish all operations
        for context in contexts:
            result = manager.finish_operation(context.operation_id)
            assert result["success"] is True

        # Verify cleanup
        active_ops = manager.get_active_operations("test_tool")
        assert active_ops["count"] == 0

    def test_concurrent_config_registration(self):
        """Test that config registration is thread-safe."""
        manager = ConcurrencyManager()
        errors = []

        def register_config(tool_name, max_concurrent):
            try:
                config = ConcurrencyConfig(max_concurrent=max_concurrent)
                manager.register_config(tool_name, config)
            except Exception as e:
                errors.append(str(e))

        # Register configs concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=register_config,
                args=(f"tool_{i}", i + 1)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0

        # All configs should be registered
        for i in range(10):
            assert f"tool_{i}" in manager._configs
            assert manager._configs[f"tool_{i}"].max_concurrent == i + 1


class TestConcurrencyManagerIntegration:
    """Integration tests for concurrency manager."""

    def test_real_world_scenario(self):
        """Test a realistic scenario with multiple tools and operations."""
        manager = ConcurrencyManager()

        # Configure different tools with different limits
        manager.register_config("pr_tool", ConcurrencyConfig(max_concurrent=1))
        manager.register_config("file_tool", ConcurrencyConfig(max_concurrent=3))
        manager.register_config("api_tool", ConcurrencyConfig(max_concurrent=2))

        # Simulate concurrent operations
        operations = [
            ("pr_tool", "create_pr_1"),
            ("file_tool", "read_file_1"),
            ("file_tool", "write_file_1"),
            ("api_tool", "fetch_data_1"),
            ("api_tool", "post_data_1"),
            ("pr_tool", "create_pr_2"),  # Should fail
            ("file_tool", "read_file_2"),
            ("file_tool", "write_file_2"),  # Should fail (3 is limit)
        ]

        results = []
        for tool_name, op_id in operations:
            context = OperationContext(
                operation_id=op_id,
                operation_type="integration_test"
            )
            result = manager.start_operation(tool_name, context)
            results.append((tool_name, op_id, result["success"]))

        # Check expected results
        expected_success = {
            "create_pr_1": True,
            "read_file_1": True,
            "write_file_1": True,
            "fetch_data_1": True,
            "post_data_1": True,
            "create_pr_2": False,  # PR tool limit exceeded
            "read_file_2": True,
            "write_file_2": False,  # File tool limit exceeded
        }

        for tool_name, op_id, success in results:
            assert success == expected_success[op_id], f"Operation {op_id} success mismatch"

        # Verify active operation counts
        all_ops = manager.get_active_operations()
        assert all_ops["pr_tool"]["count"] == 1
        assert all_ops["file_tool"]["count"] == 3
        assert all_ops["api_tool"]["count"] == 2

    def test_mixed_config_and_no_config_tools(self):
        """Test mixing tools with and without concurrency configs."""
        manager = ConcurrencyManager()

        # Only configure one tool
        manager.register_config("limited_tool", ConcurrencyConfig(max_concurrent=1))

        # Start operations on both configured and unconfigured tools
        context1 = OperationContext(operation_id="limited_op", operation_type="test")
        result1 = manager.start_operation("limited_tool", context1)
        assert result1["success"] is True

        context2 = OperationContext(operation_id="unlimited_op", operation_type="test")
        result2 = manager.start_operation("unlimited_tool", context2)
        assert result2["success"] is True

        # Limited tool should reject additional operations
        context3 = OperationContext(operation_id="limited_op2", operation_type="test")
        result3 = manager.start_operation("limited_tool", context3)
        assert result3["success"] is False

        # Unlimited tool should accept more operations
        context4 = OperationContext(operation_id="unlimited_op2", operation_type="test")
        result4 = manager.start_operation("unlimited_tool", context4)
        assert result4["success"] is True

        # Check active operations
        all_ops = manager.get_active_operations()
        assert "limited_tool" in all_ops
        assert all_ops["limited_tool"]["count"] == 1
        # unlimited_tool operations are tracked in contexts but not active_operations
        assert "unlimited_tool" not in all_ops
