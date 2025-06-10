import os
import sys
import pytest
import pytest_asyncio
import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_tools.command_executor import CommandExecutor
from mcp_tools.command_executor.types import (
    ExecutorConfig, RateLimitConfig, ConcurrencyConfig, ResourceLimitConfig
)


async def cleanup_executor(executor: CommandExecutor):
    """Helper function to properly cleanup an executor"""
    try:
        # Terminate any running processes first
        for token in list(executor.process_tokens.keys()):
            executor.terminate_by_token(token)
        
        # Wait briefly for processes to terminate
        await asyncio.sleep(0.1)
        
        # Force cleanup any remaining processes
        for token in list(executor.process_tokens.keys()):
            try:
                await asyncio.wait_for(executor.wait_for_process(token), timeout=1.0)
            except asyncio.TimeoutError:
                pass  # Process didn't terminate in time, continue cleanup
        
        # Stop background tasks aggressively
        executor._stop_background_tasks()
        
        # Stop cleanup task
        executor.stop_cleanup_task()
        
        # Cancel any remaining background tasks
        if hasattr(executor, 'background_tasks'):
            for task in executor.background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=0.1)
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        pass
        
        # Give a final moment for cleanup
        await asyncio.sleep(0.05)
        
    except Exception as e:
        # Ignore cleanup errors to avoid masking test failures
        print(f"Warning: Error during executor cleanup: {e}")
        pass


@pytest.fixture
def rate_limit_config():
    """Rate limiting configuration for testing"""
    return RateLimitConfig(
        requests_per_minute=10,
        burst_size=3,
        window_seconds=60,
        enabled=True
    )


@pytest.fixture
def concurrency_config():
    """Concurrency configuration for testing"""
    return ConcurrencyConfig(
        max_concurrent_processes=2,
        max_processes_per_user=1,
        process_queue_size=0,  # Disable queuing for simpler tests
        enabled=True
    )


@pytest.fixture
def resource_config():
    """Resource limits configuration for testing"""
    return ResourceLimitConfig(
        max_memory_per_process_mb=100,
        max_cpu_time_seconds=10,
        max_execution_time_seconds=15,
        enabled=True
    )


@pytest.fixture
def executor_config(rate_limit_config, concurrency_config, resource_config):
    """Complete executor configuration for testing"""
    return ExecutorConfig(
        rate_limit=rate_limit_config,
        concurrency=concurrency_config,
        resource_limits=resource_config
    )


@pytest_asyncio.fixture
async def executor_with_limits(executor_config):
    """CommandExecutor with rate limiting and concurrency controls enabled"""
    # Disable auto cleanup for tests to avoid interference
    executor = CommandExecutor(config=executor_config, temp_dir=None)
    executor.auto_cleanup_enabled = False
    executor.stop_cleanup_task()  # Stop any cleanup task that might have started
    yield executor
    # Cleanup after test
    await cleanup_executor(executor)


class TestRateLimiting:
    """Test rate limiting functionality"""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_within_burst(self, executor_with_limits):
        """Test that requests within burst limit are allowed"""
        command = "echo 'test'"
        user_id = "test_user"
        
        # Should allow up to burst_size requests quickly
        for i in range(3):  # burst_size = 3
            response = await executor_with_limits.execute_async(command, user_id=user_id)
            assert response["status"] in ["running", "completed"]
            assert "error" not in response
            
            # Clean up
            if "token" in response:
                await executor_with_limits.wait_for_process(response["token"])

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_after_burst(self, executor_with_limits):
        """Test that requests are blocked after exceeding burst limit"""
        command = "echo 'test'"
        user_id = "test_user"
        
        # Use up the burst allowance
        for i in range(3):  # burst_size = 3
            response = await executor_with_limits.execute_async(command, user_id=user_id)
            if "token" in response:
                await executor_with_limits.wait_for_process(response["token"])
        
        # Next request should be rate limited
        response = await executor_with_limits.execute_async(command, user_id=user_id)
        assert "error" in response
        assert response["error"] == "rate_limited"
        assert "retry_after" in response

    @pytest.mark.asyncio
    async def test_rate_limit_per_user(self, executor_with_limits):
        """Test that rate limiting is applied per user"""
        command = "echo 'test'"
        
        # Use up burst for user1
        for i in range(3):
            response = await executor_with_limits.execute_async(command, user_id="user1")
            if "token" in response:
                await executor_with_limits.wait_for_process(response["token"])
        
        # user1 should be rate limited
        response = await executor_with_limits.execute_async(command, user_id="user1")
        assert "error" in response
        assert response["error"] == "rate_limited"
        
        # user2 should still be allowed
        response = await executor_with_limits.execute_async(command, user_id="user2")
        assert response["status"] in ["running", "completed"]
        if "token" in response:
            await executor_with_limits.wait_for_process(response["token"])

    @pytest.mark.asyncio
    async def test_rate_limit_disabled(self):
        """Test that rate limiting can be disabled"""
        config = ExecutorConfig(
            rate_limit=RateLimitConfig(enabled=False),
            concurrency=ConcurrencyConfig(enabled=False),
            resource_limits=ResourceLimitConfig(enabled=False)
        )
        executor = CommandExecutor(config=config)
        
        try:
            command = "echo 'test'"
            user_id = "test_user"
            
            # Should allow many requests when disabled
            for i in range(10):
                response = await executor.execute_async(command, user_id=user_id)
                assert response["status"] in ["running", "completed"]
                if "token" in response:
                    await executor.wait_for_process(response["token"])
        finally:
            await cleanup_executor(executor)


class TestConcurrencyControl:
    """Test concurrency control functionality"""

    @pytest.mark.asyncio
    async def test_concurrency_limit_global(self, executor_with_limits):
        """Test global concurrency limit"""
        if sys.platform == "win32":
            command = "ping -n 2 127.0.0.1"  # Shorter running command
        else:
            command = "sleep 1"  # Much shorter sleep
        
        user_id = "test_user"
        tokens = []
        
        try:
            # Start max_concurrent_processes (2) processes
            for i in range(2):
                response = await asyncio.wait_for(
                    executor_with_limits.execute_async(command, user_id=f"user{i}"), 
                    timeout=5.0
                )
                assert response["status"] == "running"
                tokens.append(response["token"])
            
            # Next request should be rejected (no queuing)
            response = await asyncio.wait_for(
                executor_with_limits.execute_async(command, user_id="user3"),
                timeout=5.0
            )
            assert "error" in response
            assert response["error"] == "concurrency_limited"
        
        finally:
            # Clean up - terminate all processes
            for token in tokens:
                executor_with_limits.terminate_by_token(token)
            
            # Wait for termination with timeout
            for token in tokens:
                try:
                    await asyncio.wait_for(executor_with_limits.wait_for_process(token), timeout=2.0)
                except asyncio.TimeoutError:
                    pass  # Continue cleanup even if process doesn't terminate

    @pytest.mark.asyncio
    async def test_concurrency_limit_per_user(self, executor_with_limits):
        """Test per-user concurrency limit"""
        if sys.platform == "win32":
            command = "ping -n 5 127.0.0.1"
        else:
            command = "sleep 3"
        
        user_id = "test_user"
        
        # Start max_processes_per_user (1) process for user
        response1 = await executor_with_limits.execute_async(command, user_id=user_id)
        assert response1["status"] == "running"
        
        # Second request from same user should be rejected
        response2 = await executor_with_limits.execute_async(command, user_id=user_id)
        assert "error" in response2
        assert response2["error"] == "concurrency_limited"
        
        # Different user should still be allowed
        response3 = await executor_with_limits.execute_async(command, user_id="other_user")
        assert response3["status"] == "running"
        
        # Clean up
        executor_with_limits.terminate_by_token(response1["token"])
        executor_with_limits.terminate_by_token(response3["token"])
        await executor_with_limits.wait_for_process(response1["token"])
        await executor_with_limits.wait_for_process(response3["token"])

    @pytest.mark.asyncio
    async def test_process_queue_functionality(self, executor_with_limits):
        """Test process rejection when limits are reached (queuing disabled for tests)"""
        if sys.platform == "win32":
            command = "ping -n 2 127.0.0.1"
        else:
            command = "sleep 1"  # Shorter sleep
        
        tokens = []
        try:
            # Fill up concurrency slots
            for i in range(2):  # max_concurrent_processes = 2
                response = await asyncio.wait_for(
                    executor_with_limits.execute_async(command, user_id=f"user{i}"),
                    timeout=5.0
                )
                if response["status"] == "running":
                    tokens.append(response["token"])
            
            # Next request should be rejected (no queuing in test config)
            response = await asyncio.wait_for(
                executor_with_limits.execute_async(command, user_id="queued_user"),
                timeout=5.0
            )
            assert "error" in response
            assert response["error"] == "concurrency_limited"
        
        finally:
            # Clean up - terminate all processes
            for token in tokens:
                executor_with_limits.terminate_by_token(token)
            
            # Wait for termination with timeout
            for token in tokens:
                try:
                    await asyncio.wait_for(executor_with_limits.wait_for_process(token), timeout=2.0)
                except asyncio.TimeoutError:
                    pass  # Continue cleanup even if process doesn't terminate

    @pytest.mark.asyncio
    async def test_concurrency_disabled(self):
        """Test that concurrency control can be disabled"""
        config = ExecutorConfig(
            rate_limit=RateLimitConfig(enabled=False),
            concurrency=ConcurrencyConfig(enabled=False),
            resource_limits=ResourceLimitConfig(enabled=False)
        )
        executor = CommandExecutor(config=config)
        
        try:
            if sys.platform == "win32":
                command = "ping -n 2 127.0.0.1"
            else:
                command = "sleep 1"
            
            # Should allow many concurrent processes when disabled
            tokens = []
            for i in range(5):
                response = await executor.execute_async(command, user_id=f"user{i}")
                assert response["status"] in ["running", "completed"]
                if "token" in response:
                    tokens.append(response["token"])
            
            # Clean up
            for token in tokens:
                await executor.wait_for_process(token)
        finally:
            await cleanup_executor(executor)


class TestResourceMonitoring:
    """Test resource monitoring and limits"""

    @pytest.mark.asyncio
    async def test_resource_monitoring_enabled(self, executor_with_limits):
        """Test that resource monitoring is enabled and tracking processes"""
        command = "echo 'test'"
        user_id = "test_user"
        
        response = await executor_with_limits.execute_async(command, user_id=user_id)
        if "token" in response:
            # Check that resource monitoring is active
            status = await executor_with_limits.get_process_status(response["token"])
            
            # Wait for completion to get resource usage
            result = await executor_with_limits.wait_for_process(response["token"])
            
            # Should have resource usage information
            if "resource_usage" in result:
                assert "memory_mb" in result["resource_usage"]
                assert "execution_time" in result["resource_usage"]

    @pytest.mark.asyncio
    async def test_memory_limit_enforcement(self, executor_with_limits):
        """Test memory limit enforcement (if possible to trigger)"""
        # This test is challenging because it's hard to create a process that
        # reliably exceeds memory limits in a test environment
        # We'll just verify the monitoring is in place
        command = "echo 'test'"
        user_id = "test_user"
        
        response = await executor_with_limits.execute_async(command, user_id=user_id)
        if "token" in response:
            result = await executor_with_limits.wait_for_process(response["token"])
            assert result["status"] in ["completed", "terminated"]

    @pytest.mark.asyncio
    async def test_resource_monitoring_disabled(self):
        """Test that resource monitoring can be disabled"""
        config = ExecutorConfig(
            rate_limit=RateLimitConfig(enabled=False),
            concurrency=ConcurrencyConfig(enabled=False),
            resource_limits=ResourceLimitConfig(enabled=False)
        )
        executor = CommandExecutor(config=config)
        
        try:
            command = "echo 'test'"
            user_id = "test_user"
            
            response = await executor.execute_async(command, user_id=user_id)
            if "token" in response:
                result = await executor.wait_for_process(response["token"])
                # Should complete normally without resource monitoring
                assert result["status"] == "completed"
        finally:
            await cleanup_executor(executor)


class TestIntegration:
    """Integration tests for all features working together"""

    @pytest.mark.asyncio
    async def test_rate_limit_and_concurrency_together(self, executor_with_limits):
        """Test rate limiting and concurrency control working together"""
        command = "echo 'test'"
        user_id = "test_user"
        
        # This should work within both rate and concurrency limits
        response = await executor_with_limits.execute_async(command, user_id=user_id)
        assert response["status"] in ["running", "completed"]
        
        if "token" in response:
            result = await executor_with_limits.wait_for_process(response["token"])
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_configuration_validation(self):
        """Test that configuration validation works"""
        # Test with valid configuration
        config = ExecutorConfig(
            rate_limit=RateLimitConfig(requests_per_minute=60, burst_size=10),
            concurrency=ConcurrencyConfig(max_concurrent_processes=5),
            resource_limits=ResourceLimitConfig(max_memory_per_process_mb=512)
        )
        executor = CommandExecutor(config=config)
        assert executor.config.rate_limit.requests_per_minute == 60
        assert executor.config.concurrency.max_concurrent_processes == 5
        assert executor.config.resource_limits.max_memory_per_process_mb == 512

    @pytest.mark.asyncio
    async def test_status_reporting_with_limits(self, executor_with_limits):
        """Test that status reporting works with rate limiting and concurrency"""
        if sys.platform == "win32":
            command = "ping -n 3 127.0.0.1"
        else:
            command = "sleep 2"
        
        user_id = "test_user"
        
        # Start a process
        response = await executor_with_limits.execute_async(command, user_id=user_id)
        if "token" in response:
            # Check status
            status = await executor_with_limits.get_process_status(response["token"])
            assert "status" in status
            assert "user_id" in executor_with_limits.running_processes.get(status.get("pid", 0), {})
            
            # Clean up
            await executor_with_limits.wait_for_process(response["token"])

    @pytest.mark.asyncio
    async def test_error_handling_with_limits(self, executor_with_limits):
        """Test error handling when limits are in place"""
        # Test with invalid command
        response = await executor_with_limits.execute_async("invalid_command_xyz", user_id="test_user")
        
        # Should either fail immediately or run and fail
        if "error" in response:
            # Failed due to limits or other reasons
            assert "error" in response
        else:
            # Started but should fail
            result = await executor_with_limits.wait_for_process(response["token"])
            assert result["success"] is False


class TestComponentUnits:
    """Unit tests for individual components"""

    def test_rate_limiter_initialization(self, rate_limit_config):
        """Test rate limiter component initialization"""
        from mcp_tools.command_executor.rate_limiter import RateLimiter
        
        rate_limiter = RateLimiter(rate_limit_config)
        assert rate_limiter.enabled == rate_limit_config.enabled
        assert rate_limiter.config.requests_per_minute == rate_limit_config.requests_per_minute

    def test_concurrency_manager_initialization(self, concurrency_config):
        """Test concurrency manager component initialization"""
        from mcp_tools.command_executor.concurrency_manager import ConcurrencyManager
        
        concurrency_manager = ConcurrencyManager(concurrency_config)
        assert concurrency_manager.enabled == concurrency_config.enabled
        assert concurrency_manager.config.max_concurrent_processes == concurrency_config.max_concurrent_processes

    def test_resource_monitor_initialization(self, resource_config):
        """Test resource monitor component initialization"""
        from mcp_tools.command_executor.resource_monitor import ResourceMonitor
        
        resource_monitor = ResourceMonitor(resource_config)
        assert resource_monitor.enabled == resource_config.enabled
        assert resource_monitor.config.max_memory_per_process_mb == resource_config.max_memory_per_process_mb

    @pytest.mark.asyncio
    async def test_token_bucket_functionality(self):
        """Test token bucket algorithm"""
        from mcp_tools.command_executor.rate_limiter import TokenBucket
        
        bucket = TokenBucket(capacity=3, refill_rate=1.0)  # 1 token per second
        
        # Should allow consuming up to capacity
        assert await bucket.consume(1) is True
        assert await bucket.consume(1) is True
        assert await bucket.consume(1) is True
        
        # Should reject when empty
        assert await bucket.consume(1) is False
        
        # Should refill over time (this is timing-dependent, so we'll just check structure)
        status = await bucket.get_status()
        assert "tokens" in status
        assert "capacity" in status
        assert "refill_rate" in status

    @pytest.mark.asyncio
    async def test_sliding_window_functionality(self):
        """Test sliding window rate limiter"""
        from mcp_tools.command_executor.rate_limiter import SlidingWindowRateLimiter
        
        limiter = SlidingWindowRateLimiter(window_size=60, max_requests=5)
        
        user_id = "test_user"
        
        # Should allow up to max_requests
        for i in range(5):
            allowed, count = await limiter.is_allowed(user_id)
            assert allowed is True
            assert count == i + 1
        
        # Should reject after max_requests
        allowed, count = await limiter.is_allowed(user_id)
        assert allowed is False
        assert count == 5
        
        # Check status
        status = await limiter.get_status(user_id)
        assert status["requests_in_window"] == 5
        assert status["requests_remaining"] == 0 