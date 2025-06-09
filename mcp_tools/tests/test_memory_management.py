"""
Tests for CommandExecutor memory management functionality.

This module tests the memory leak prevention features including:
- LRU eviction when max completed processes limit is reached
- TTL-based cleanup of expired processes
- Background cleanup task functionality
- Manual cleanup methods
- Memory statistics reporting
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from collections import OrderedDict

from mcp_tools.command_executor.executor import CommandExecutor


class TestMemoryManagement:
    """Test memory management features of CommandExecutor."""

    @pytest.fixture
    def executor_with_limits(self):
        """Create a CommandExecutor with small limits for testing."""
        with patch('mcp_tools.command_executor.executor.env_manager') as mock_env:
            # Configure small limits for testing
            mock_env.load.return_value = None
            mock_env.get_setting.side_effect = lambda key, default: {
                "max_completed_processes": 3,
                "completed_process_ttl": 2,  # 2 seconds TTL
                "auto_cleanup_enabled": False,  # Disable for manual testing
                "cleanup_interval": 1,  # 1 second interval
                "periodic_status_enabled": False,
                "periodic_status_interval": 30.0,
                "periodic_status_max_command_length": 60,
            }.get(key, default)
            
            executor = CommandExecutor()
            yield executor
            
            # Cleanup
            executor.stop_cleanup_task()

    @pytest.fixture
    def executor_with_auto_cleanup(self):
        """Create a CommandExecutor with auto cleanup enabled."""
        with patch('mcp_tools.command_executor.executor.env_manager') as mock_env:
            mock_env.load.return_value = None
            mock_env.get_setting.side_effect = lambda key, default: {
                "max_completed_processes": 5,
                "completed_process_ttl": 1,  # 1 second TTL
                "auto_cleanup_enabled": True,
                "cleanup_interval": 0.5,  # 0.5 second interval
                "periodic_status_enabled": False,
                "periodic_status_interval": 30.0,
                "periodic_status_max_command_length": 60,
            }.get(key, default)
            
            executor = CommandExecutor()
            yield executor
            
            # Cleanup
            executor.stop_cleanup_task()

    def test_lru_eviction_when_limit_exceeded(self, executor_with_limits):
        """Test that oldest completed processes are evicted when limit is exceeded."""
        executor = executor_with_limits
        
        # Add processes up to the limit
        for i in range(3):
            token = f"token_{i}"
            result = {"status": "completed", "output": f"output_{i}"}
            executor.completed_processes[token] = result
            executor.completed_process_timestamps[token] = time.time()
        
        assert len(executor.completed_processes) == 3
        
        # Add one more process - should trigger eviction
        token_new = "token_new"
        result_new = {"status": "completed", "output": "output_new"}
        executor.completed_processes[token_new] = result_new
        executor.completed_process_timestamps[token_new] = time.time()
        executor._enforce_completed_process_limit()
        
        # Should still have 3 processes, oldest should be evicted
        assert len(executor.completed_processes) == 3
        assert "token_0" not in executor.completed_processes  # Oldest evicted
        assert "token_new" in executor.completed_processes  # New one kept
        assert "token_0" not in executor.completed_process_timestamps

    def test_ttl_cleanup_removes_expired_processes(self, executor_with_limits):
        """Test that expired processes are removed based on TTL."""
        executor = executor_with_limits
        
        # Add some processes with different timestamps
        current_time = time.time()
        
        # Old process (expired)
        executor.completed_processes["old_token"] = {"status": "completed"}
        executor.completed_process_timestamps["old_token"] = current_time - 5  # 5 seconds ago
        
        # Recent process (not expired)
        executor.completed_processes["new_token"] = {"status": "completed"}
        executor.completed_process_timestamps["new_token"] = current_time - 1  # 1 second ago
        
        # Run cleanup
        cleanup_count = executor._cleanup_expired_processes()
        
        # Old process should be removed, new one should remain
        assert cleanup_count == 1
        assert "old_token" not in executor.completed_processes
        assert "new_token" in executor.completed_processes
        assert "old_token" not in executor.completed_process_timestamps

    def test_manual_cleanup_with_force_all(self, executor_with_limits):
        """Test manual cleanup with force_all option."""
        executor = executor_with_limits
        
        # Add some processes
        for i in range(3):
            token = f"token_{i}"
            executor.completed_processes[token] = {"status": "completed"}
            executor.completed_process_timestamps[token] = time.time()
        
        assert len(executor.completed_processes) == 3
        
        # Force cleanup all
        result = executor.cleanup_completed_processes(force_all=True)
        
        assert result["initial_count"] == 3
        assert result["cleaned_count"] == 3
        assert result["remaining_count"] == 0
        assert result["force_all"] is True
        assert len(executor.completed_processes) == 0
        assert len(executor.completed_process_timestamps) == 0

    def test_manual_cleanup_without_force(self, executor_with_limits):
        """Test manual cleanup without force_all (TTL-based only)."""
        executor = executor_with_limits
        
        current_time = time.time()
        
        # Add expired and non-expired processes
        executor.completed_processes["expired"] = {"status": "completed"}
        executor.completed_process_timestamps["expired"] = current_time - 5
        
        executor.completed_processes["fresh"] = {"status": "completed"}
        executor.completed_process_timestamps["fresh"] = current_time
        
        # Manual cleanup (TTL-based)
        result = executor.cleanup_completed_processes(force_all=False)
        
        assert result["initial_count"] == 2
        assert result["cleaned_count"] == 1  # Only expired one
        assert result["remaining_count"] == 1
        assert result["force_all"] is False
        assert "expired" not in executor.completed_processes
        assert "fresh" in executor.completed_processes

    def test_memory_stats_reporting(self, executor_with_limits):
        """Test memory statistics reporting."""
        executor = executor_with_limits
        
        # Add some processes with different ages
        current_time = time.time()
        executor.completed_processes["token1"] = {"status": "completed"}
        executor.completed_process_timestamps["token1"] = current_time - 10
        
        executor.completed_processes["token2"] = {"status": "completed"}
        executor.completed_process_timestamps["token2"] = current_time - 5
        
        stats = executor.get_memory_stats()
        
        assert stats["completed_processes_count"] == 2
        assert stats["max_completed_processes"] == 3
        assert stats["completed_process_ttl"] == 2
        assert stats["auto_cleanup_enabled"] is False
        assert stats["cleanup_interval"] == 1
        assert "oldest_process_age" in stats
        assert "newest_process_age" in stats
        assert "average_process_age" in stats
        assert stats["oldest_process_age"] >= 10
        assert stats["newest_process_age"] >= 5

    def test_memory_stats_empty_processes(self, executor_with_limits):
        """Test memory statistics when no completed processes exist."""
        executor = executor_with_limits
        
        stats = executor.get_memory_stats()
        
        assert stats["completed_processes_count"] == 0
        assert "oldest_process_age" not in stats
        assert "newest_process_age" not in stats
        assert "average_process_age" not in stats

    @pytest.mark.asyncio
    async def test_background_cleanup_task(self, executor_with_auto_cleanup):
        """Test that background cleanup task works correctly."""
        executor = executor_with_auto_cleanup
        
        # Ensure cleanup task is running
        executor._ensure_cleanup_task_running()
        
        # Add an expired process (older than TTL of 1 second)
        current_time = time.time()
        executor.completed_processes["expired"] = {"status": "completed"}
        executor.completed_process_timestamps["expired"] = current_time - 2  # Expired (2 seconds ago)
        
        # Add a fresh process
        executor.completed_processes["fresh"] = {"status": "completed"}
        executor.completed_process_timestamps["fresh"] = current_time
        
        assert len(executor.completed_processes) == 2
        
        # Wait for cleanup task to run (should run every 0.5 seconds, TTL is 1 second)
        await asyncio.sleep(1.0)  # Wait 1 second for cleanup to happen
        
        # Expired process should be cleaned up
        assert "expired" not in executor.completed_processes
        assert "fresh" in executor.completed_processes
        assert len(executor.completed_processes) == 1

    def test_lru_behavior_on_access(self, executor_with_limits):
        """Test that accessing completed processes updates LRU order."""
        executor = executor_with_limits
        
        # Add processes
        for i in range(3):
            token = f"token_{i}"
            executor.completed_processes[token] = {"status": "completed"}
            executor.completed_process_timestamps[token] = time.time()
        
        # Access the first token (should move to end)
        result = executor.completed_processes["token_0"]
        executor.completed_processes.move_to_end("token_0")
        
        # Add one more process to trigger eviction
        executor.completed_processes["token_new"] = {"status": "completed"}
        executor.completed_process_timestamps["token_new"] = time.time()
        executor._enforce_completed_process_limit()
        
        # token_1 should be evicted (oldest), token_0 should remain (recently accessed)
        assert len(executor.completed_processes) == 3
        assert "token_1" not in executor.completed_processes  # Evicted
        assert "token_0" in executor.completed_processes  # Recently accessed, kept
        assert "token_2" in executor.completed_processes
        assert "token_new" in executor.completed_processes

    @pytest.mark.asyncio
    async def test_cleanup_task_start_stop(self, executor_with_limits):
        """Test starting and stopping cleanup task."""
        executor = executor_with_limits
        
        # Initially no task
        assert executor.cleanup_task is None
        
        # Start task (now that we have an event loop)
        executor.auto_cleanup_enabled = True
        executor.start_cleanup_task()
        assert executor.cleanup_task is not None
        assert not executor.cleanup_task.done()
        
        # Stop task
        executor.stop_cleanup_task()
        assert executor.cleanup_task is None

    def test_cleanup_task_not_started_when_disabled(self, executor_with_limits):
        """Test that cleanup task is not started when auto_cleanup_enabled is False."""
        executor = executor_with_limits
        
        # Should not start task when disabled
        executor.auto_cleanup_enabled = False
        executor.start_cleanup_task()
        assert executor.cleanup_task is None

    def test_zero_ttl_disables_ttl_cleanup(self, executor_with_limits):
        """Test that TTL cleanup is disabled when TTL is set to 0."""
        executor = executor_with_limits
        executor.completed_process_ttl = 0
        
        # Add old process
        current_time = time.time()
        executor.completed_processes["old"] = {"status": "completed"}
        executor.completed_process_timestamps["old"] = current_time - 100
        
        # Cleanup should not remove anything when TTL is 0
        cleanup_count = executor._cleanup_expired_processes()
        assert cleanup_count == 0
        assert "old" in executor.completed_processes

    @pytest.mark.asyncio
    async def test_destructor_cleanup(self, executor_with_limits):
        """Test that destructor properly cleans up background task."""
        executor = executor_with_limits
        
        # Start task (now that we have an event loop)
        executor.auto_cleanup_enabled = True
        executor.start_cleanup_task()
        assert executor.cleanup_task is not None
        
        # Call destructor
        executor.__del__()
        
        # Task should be cleaned up (this test mainly ensures no exceptions)
        # We can't easily test the task state after __del__ due to cleanup

    @pytest.mark.asyncio
    async def test_integration_with_wait_for_process(self, executor_with_limits):
        """Test integration with wait_for_process method."""
        executor = executor_with_limits
        
        # Mock a completed process scenario
        token = "test_token"
        pid = 12345
        
        # Set up mock process data
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        async def mock_wait():
            return None
        mock_process.wait = mock_wait
        
        executor.process_tokens[token] = pid
        executor.running_processes[pid] = {
            "process": mock_process,
            "command": "echo test",
            "stdout_path": "/tmp/stdout",
            "stderr_path": "/tmp/stderr",
            "token": token,
            "start_time": time.time()
        }
        executor.temp_files[pid] = ("/tmp/stdout", "/tmp/stderr")
        
        # Mock file reading
        with patch.object(executor, '_read_temp_file') as mock_read:
            mock_read.return_value = "test output"
            
            with patch.object(executor, '_cleanup_temp_files') as mock_cleanup:
                mock_cleanup.return_value = None
                
                # Call wait_for_process
                result = await executor.wait_for_process(token)
                
                # Verify result is stored with timestamp and limits enforced
                assert token in executor.completed_processes
                assert token in executor.completed_process_timestamps
                assert result["status"] == "completed"
                assert result["output"] == "test output"
                
                # Verify the result is the same as what's stored
                stored_result = executor.completed_processes[token]
                assert stored_result == result 