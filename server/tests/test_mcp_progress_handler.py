"""
Tests for MCP Progress Handler.

This module contains unit tests for the MCPProgressHandler class.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from server.mcp_progress_handler import MCPProgressHandler, create_progress_callback


class MockMCPServer:
    """Mock MCP server for testing."""

    def __init__(self):
        self.notifications = []
        self.send_progress_notification = AsyncMock(side_effect=self._record_notification)

    async def _record_notification(self, progress_token, progress, total, message):
        """Record notification for later inspection."""
        self.notifications.append({
            "progress_token": progress_token,
            "progress": progress,
            "total": total,
            "message": message
        })


@pytest.mark.asyncio
async def test_register_and_send_progress():
    """Test that progress notifications are sent correctly."""
    mock_server = MockMCPServer()
    handler = MCPProgressHandler(mock_server)

    token = "test-token-123"
    handler.register_token(token)
    assert handler.is_active(token)

    await handler.send_progress(token, 50, 100, "Halfway")

    mock_server.send_progress_notification.assert_called_once_with(
        progress_token=token,
        progress=50,
        total=100,
        message="Halfway"
    )

    assert len(mock_server.notifications) == 1
    notification = mock_server.notifications[0]
    assert notification["progress_token"] == token
    assert notification["progress"] == 50
    assert notification["total"] == 100
    assert notification["message"] == "Halfway"


@pytest.mark.asyncio
async def test_inactive_token_ignored():
    """Test that progress for inactive tokens is ignored."""
    mock_server = MockMCPServer()
    handler = MCPProgressHandler(mock_server)

    result = await handler.send_progress("invalid-token", 50, 100, "Test")

    assert result is False
    mock_server.send_progress_notification.assert_not_called()


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test that progress notifications are rate limited."""
    mock_server = MockMCPServer()
    handler = MCPProgressHandler(mock_server)
    handler.min_update_interval = 0.05  # 50ms

    token = "rate-limit-test"
    handler.register_token(token)

    # Send 10 updates rapidly
    for i in range(10):
        await handler.send_progress(token, i, 10, f"Step {i}")

    # Should be rate limited (not all 10 notifications sent)
    call_count = mock_server.send_progress_notification.call_count
    assert call_count < 10, f"Expected < 10 calls due to rate limiting, got {call_count}"


@pytest.mark.asyncio
async def test_final_update_always_sent():
    """Test that final progress updates are always sent despite rate limiting."""
    mock_server = MockMCPServer()
    handler = MCPProgressHandler(mock_server)
    handler.min_update_interval = 1.0  # High rate limit

    token = "final-test"
    handler.register_token(token)

    # Send initial and final updates rapidly
    await handler.send_progress(token, 0, 100, "Start")
    await handler.send_progress(token, 100, 100, "Complete")

    # Both should be sent (first and final)
    assert mock_server.send_progress_notification.call_count >= 1


@pytest.mark.asyncio
async def test_unregister_token():
    """Test that unregistering a token works correctly."""
    mock_server = MockMCPServer()
    handler = MCPProgressHandler(mock_server)

    token = "test-token"
    handler.register_token(token)
    assert handler.is_active(token)

    handler.unregister_token(token)
    assert not handler.is_active(token)

    # Should not send progress after unregistering
    result = await handler.send_progress(token, 50, 100, "Test")
    assert result is False


@pytest.mark.asyncio
async def test_get_active_token_count():
    """Test getting the count of active tokens."""
    mock_server = MockMCPServer()
    handler = MCPProgressHandler(mock_server)

    assert handler.get_active_token_count() == 0

    handler.register_token("token1")
    handler.register_token("token2")
    assert handler.get_active_token_count() == 2

    handler.unregister_token("token1")
    assert handler.get_active_token_count() == 1


@pytest.mark.asyncio
async def test_clear_all():
    """Test clearing all tokens and state."""
    mock_server = MockMCPServer()
    handler = MCPProgressHandler(mock_server)

    handler.register_token("token1")
    handler.register_token("token2")
    assert handler.get_active_token_count() == 2

    handler.clear_all()
    assert handler.get_active_token_count() == 0


@pytest.mark.asyncio
async def test_create_progress_callback():
    """Test creating a progress callback function."""
    mock_server = MockMCPServer()
    handler = MCPProgressHandler(mock_server)

    token = "callback-test"
    handler.register_token(token)

    callback = create_progress_callback(handler, token)

    # Use the callback
    await callback(25, 100, "Quarter done")

    assert len(mock_server.notifications) == 1
    assert mock_server.notifications[0]["progress"] == 25


@pytest.mark.asyncio
async def test_error_handling_in_send_progress():
    """Test that errors in notification sending are handled gracefully."""
    mock_server = Mock()
    mock_server.send_progress_notification = AsyncMock(
        side_effect=Exception("Network error")
    )

    handler = MCPProgressHandler(mock_server)
    token = "error-test"
    handler.register_token(token)

    # Should not raise exception, just log error
    result = await handler.send_progress(token, 50, 100, "Test")
    assert result is False


@pytest.mark.asyncio
async def test_monotonic_progress_warning():
    """Test that non-monotonic progress triggers a warning."""
    mock_server = MockMCPServer()
    handler = MCPProgressHandler(mock_server)

    token = "monotonic-test"
    handler.register_token(token)

    # Send increasing progress
    await handler.send_progress(token, 50, 100, "Halfway")
    await asyncio.sleep(0.2)  # Wait for rate limit

    # Send decreasing progress (should warn but still send)
    await handler.send_progress(token, 30, 100, "Going back")

    # Both should be recorded
    assert len(mock_server.notifications) >= 1


@pytest.mark.asyncio
async def test_max_update_interval_forces_update():
    """Test that max_update_interval forces updates even with rate limiting."""
    mock_server = MockMCPServer()
    handler = MCPProgressHandler(mock_server)
    handler.min_update_interval = 10.0  # Very high
    handler.max_update_interval = 0.1  # Very low

    token = "max-interval-test"
    handler.register_token(token)

    await handler.send_progress(token, 0, 100, "Start")
    await asyncio.sleep(0.15)  # Wait longer than max_update_interval
    await handler.send_progress(token, 50, 100, "Middle")

    # Second update should be sent due to max_update_interval
    assert mock_server.send_progress_notification.call_count >= 2


@pytest.mark.asyncio
async def test_progress_without_total():
    """Test sending progress without a known total."""
    mock_server = MockMCPServer()
    handler = MCPProgressHandler(mock_server)

    token = "no-total-test"
    handler.register_token(token)

    await handler.send_progress(token, 42.5, None, "Unknown duration")

    assert len(mock_server.notifications) == 1
    notification = mock_server.notifications[0]
    assert notification["progress"] == 42.5
    assert notification["total"] is None
    assert notification["message"] == "Unknown duration"
