"""Tests for the concurrency manager functionality."""

import pytest
import threading
import time as time_module
from unittest.mock import patch

from mcp_tools.concurrency_manager import (
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