"""
Unit tests for MCPProgressHandler.

Tests the progress notification handler's core functionality including
token registration, rate limiting, metrics tracking, and error handling.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from server.mcp_progress_handler import MCPProgressHandler, create_progress_callback, ProgressMetrics


class TestMCPProgressHandler:
    """Test suite for MCPProgressHandler."""

    def test_initialization(self):
        """Test handler initialization with default and custom parameters."""
        # Default initialization
        handler = MCPProgressHandler()
        assert handler.min_update_interval == 0.1
        assert handler.max_update_interval == 5.0
        assert len(handler.active_tokens) == 0
        assert handler.metrics.total_notifications_sent == 0

        # Custom initialization
        handler = MCPProgressHandler(min_update_interval=0.5, max_update_interval=10.0)
        assert handler.min_update_interval == 0.5
        assert handler.max_update_interval == 10.0

    def test_register_token(self):
        """Test token registration."""
        handler = MCPProgressHandler()

        # Register a token
        handler.register_token("test-token-123")
        assert "test-token-123" in handler.active_tokens
        assert handler.active_tokens["test-token-123"] is True
        assert handler.metrics.active_tokens == 1

        # Register another token
        handler.register_token("test-token-456")
        assert len(handler.active_tokens) == 2
        assert handler.metrics.active_tokens == 2

    def test_unregister_token(self):
        """Test token unregistration."""
        handler = MCPProgressHandler()

        # Register and unregister
        handler.register_token("test-token-123")
        assert handler.metrics.active_tokens == 1

        handler.unregister_token("test-token-123")
        assert "test-token-123" not in handler.active_tokens
        assert handler.metrics.active_tokens == 0

        # Unregister non-existent token (should not error)
        handler.unregister_token("non-existent")
        assert handler.metrics.active_tokens == 0

    def test_is_active(self):
        """Test checking if token is active."""
        handler = MCPProgressHandler()

        handler.register_token("test-token-123")
        assert handler.is_active("test-token-123") is True
        assert handler.is_active("non-existent") is False

        handler.unregister_token("test-token-123")
        assert handler.is_active("test-token-123") is False

    def test_get_active_token_count(self):
        """Test getting active token count."""
        handler = MCPProgressHandler()

        assert handler.get_active_token_count() == 0

        handler.register_token("token-1")
        handler.register_token("token-2")
        handler.register_token("token-3")
        assert handler.get_active_token_count() == 3

        handler.unregister_token("token-2")
        assert handler.get_active_token_count() == 2

    def test_clear_all(self):
        """Test clearing all tokens and state."""
        handler = MCPProgressHandler()

        # Register tokens and send some progress
        handler.register_token("token-1")
        handler.register_token("token-2")
        handler._rate_limiters["token-1"] = time.time()
        handler._last_progress["token-1"] = 50.0

        # Clear all
        handler.clear_all()
        assert len(handler.active_tokens) == 0
        assert len(handler._rate_limiters) == 0
        assert len(handler._last_progress) == 0
        assert handler.metrics.active_tokens == 0

    def test_get_metrics(self):
        """Test getting metrics."""
        handler = MCPProgressHandler()

        # Initial metrics
        metrics = handler.get_metrics()
        assert metrics["total_notifications_sent"] == 0
        assert metrics["total_notifications_skipped"] == 0
        assert metrics["total_errors"] == 0
        assert metrics["active_tokens"] == 0
        assert metrics["last_error"] is None

        # Register tokens
        handler.register_token("token-1")
        handler.register_token("token-2")
        metrics = handler.get_metrics()
        assert metrics["active_tokens"] == 2

    def test_reset_metrics(self):
        """Test resetting metrics while keeping active tokens."""
        handler = MCPProgressHandler()

        # Register tokens and update metrics
        handler.register_token("token-1")
        handler.metrics.total_notifications_sent = 10
        handler.metrics.total_notifications_skipped = 5
        handler.metrics.total_errors = 2

        # Reset metrics
        handler.reset_metrics()
        assert handler.metrics.total_notifications_sent == 0
        assert handler.metrics.total_notifications_skipped == 0
        assert handler.metrics.total_errors == 0
        assert handler.metrics.active_tokens == 1  # Token still active

    @pytest.mark.asyncio
    async def test_send_progress_inactive_token(self):
        """Test sending progress for inactive token."""
        handler = MCPProgressHandler()

        # Try to send progress without registering token
        result = await handler.send_progress("unregistered-token", 50, 100, "Test")
        assert result is False
        assert handler.metrics.total_notifications_sent == 0

    @pytest.mark.asyncio
    async def test_send_progress_rate_limiting(self):
        """Test progress rate limiting."""
        handler = MCPProgressHandler(min_update_interval=1.0)
        handler.register_token("test-token")

        # Mock the server and session
        mock_session = AsyncMock()
        mock_context = Mock()
        mock_context.session = mock_session

        with patch('server.mcp_progress_handler.server') as mock_server:
            mock_server.request_context = mock_context

            # First update should go through
            result = await handler.send_progress("test-token", 10, 100, "First")
            assert result is True
            assert handler.metrics.total_notifications_sent == 1

            # Second update immediately after should be rate-limited
            result = await handler.send_progress("test-token", 20, 100, "Second")
            assert result is False
            assert handler.metrics.total_notifications_skipped == 1

            # Wait for rate limit to pass
            await asyncio.sleep(1.1)

            # Third update should go through
            result = await handler.send_progress("test-token", 30, 100, "Third")
            assert result is True
            assert handler.metrics.total_notifications_sent == 2

    @pytest.mark.asyncio
    async def test_send_progress_final_update(self):
        """Test that final updates always go through regardless of rate limiting."""
        handler = MCPProgressHandler(min_update_interval=10.0)  # Long interval
        handler.register_token("test-token")

        # Mock the server and session
        mock_session = AsyncMock()
        mock_context = Mock()
        mock_context.session = mock_session

        with patch('server.mcp_progress_handler.server') as mock_server:
            mock_server.request_context = mock_context

            # Send initial progress
            await handler.send_progress("test-token", 10, 100, "Start")
            assert handler.metrics.total_notifications_sent == 1

            # Send final progress immediately (should not be rate-limited)
            result = await handler.send_progress("test-token", 100, 100, "Complete")
            assert result is True
            assert handler.metrics.total_notifications_sent == 2
            assert handler.metrics.total_notifications_skipped == 0

    @pytest.mark.asyncio
    async def test_send_progress_max_interval(self):
        """Test that updates are forced after max_update_interval."""
        handler = MCPProgressHandler(min_update_interval=1.0, max_update_interval=0.5)
        handler.register_token("test-token")

        # Mock the server and session
        mock_session = AsyncMock()
        mock_context = Mock()
        mock_context.session = mock_session

        with patch('server.mcp_progress_handler.server') as mock_server:
            mock_server.request_context = mock_context

            # First update
            await handler.send_progress("test-token", 10, 100, "First")
            assert handler.metrics.total_notifications_sent == 1

            # Wait for max interval
            await asyncio.sleep(0.6)

            # Second update should go through despite min_interval not being met
            result = await handler.send_progress("test-token", 20, 100, "Second")
            assert result is True
            assert handler.metrics.total_notifications_sent == 2

    @pytest.mark.asyncio
    async def test_send_progress_no_context(self):
        """Test error handling when no request context is available."""
        handler = MCPProgressHandler()
        handler.register_token("test-token")

        with patch('server.mcp_progress_handler.server') as mock_server:
            # Simulate no request context
            mock_server.request_context = Mock()
            type(mock_server.request_context).session = property(
                lambda self: (_ for _ in ()).throw(LookupError("No context"))
            )

            result = await handler.send_progress("test-token", 50, 100, "Test")
            assert result is False
            assert handler.metrics.total_errors == 1
            assert "No active request context" in handler.metrics.last_error

    @pytest.mark.asyncio
    async def test_send_progress_exception(self):
        """Test error handling when sending progress fails."""
        handler = MCPProgressHandler()
        handler.register_token("test-token")

        # Mock the server to raise an exception
        with patch('server.mcp_progress_handler.server') as mock_server:
            mock_server.request_context = Mock()
            mock_server.request_context.session.send_progress_notification = AsyncMock(
                side_effect=Exception("Network error")
            )

            result = await handler.send_progress("test-token", 50, 100, "Test")
            assert result is False
            assert handler.metrics.total_errors == 1
            assert "Network error" in handler.metrics.last_error

    @pytest.mark.asyncio
    async def test_send_progress_monotonic_validation(self):
        """Test validation of monotonically increasing progress."""
        handler = MCPProgressHandler()
        handler.register_token("test-token")

        # Mock the server and session
        mock_session = AsyncMock()
        mock_context = Mock()
        mock_context.session = mock_session

        with patch('server.mcp_progress_handler.server') as mock_server:
            mock_server.request_context = mock_context

            # Send progress
            await handler.send_progress("test-token", 50, 100, "Halfway")

            # Try to send lower progress (should log warning but still send)
            await asyncio.sleep(0.2)  # Wait for rate limit
            result = await handler.send_progress("test-token", 30, 100, "Going backwards")
            assert result is True  # Still sends, but logs warning

    def test_create_progress_callback(self):
        """Test creating a progress callback."""
        handler = MCPProgressHandler()
        handler.register_token("test-token")

        callback = create_progress_callback(handler, "test-token")
        assert callable(callback)
        assert asyncio.iscoroutinefunction(callback)

    @pytest.mark.asyncio
    async def test_progress_callback_functionality(self):
        """Test that created progress callback works correctly."""
        handler = MCPProgressHandler()
        handler.register_token("test-token")

        # Mock the server and session
        mock_session = AsyncMock()
        mock_context = Mock()
        mock_context.session = mock_session

        with patch('server.mcp_progress_handler.server') as mock_server:
            mock_server.request_context = mock_context

            callback = create_progress_callback(handler, "test-token")

            # Use the callback
            await callback(25, 100, "Quarter done")
            assert handler.metrics.total_notifications_sent == 1

            await asyncio.sleep(0.2)
            await callback(75, 100, "Three quarters done")
            assert handler.metrics.total_notifications_sent == 2


class TestProgressMetrics:
    """Test suite for ProgressMetrics dataclass."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = ProgressMetrics()
        assert metrics.total_notifications_sent == 0
        assert metrics.total_notifications_skipped == 0
        assert metrics.total_errors == 0
        assert metrics.active_tokens == 0
        assert metrics.last_error is None
        assert metrics.last_error_time is None

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = ProgressMetrics(
            total_notifications_sent=10,
            total_notifications_skipped=5,
            total_errors=2,
            active_tokens=3
        )

        result = metrics.to_dict()
        assert result["total_notifications_sent"] == 10
        assert result["total_notifications_skipped"] == 5
        assert result["total_errors"] == 2
        assert result["active_tokens"] == 3
        assert result["last_error"] is None
        assert result["last_error_time"] is None

    def test_metrics_with_error(self):
        """Test metrics with error information."""
        error_time = datetime.now()
        metrics = ProgressMetrics(
            total_errors=1,
            last_error="Test error",
            last_error_time=error_time
        )

        result = metrics.to_dict()
        assert result["total_errors"] == 1
        assert result["last_error"] == "Test error"
        assert result["last_error_time"] == error_time.isoformat()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
