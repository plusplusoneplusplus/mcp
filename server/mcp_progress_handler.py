"""MCP Progress Handler for managing progress notifications.

This module provides the MCPProgressHandler class for managing MCP progress
notifications for active requests. It handles token registration, rate limiting,
and sending progress updates to clients.
"""

from typing import Optional, Dict, Callable, Awaitable
import logging
import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime


# Type alias for progress callback
ProgressCallback = Callable[[float, Optional[float], Optional[str]], Awaitable[None]]

# Module-level variable that will be set during server initialization
# This allows tests to patch it
server = None


@dataclass
class ProgressMetrics:
    """Metrics for progress notification tracking."""
    total_notifications_sent: int = 0
    total_notifications_skipped: int = 0
    total_errors: int = 0
    active_tokens: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "total_notifications_sent": self.total_notifications_sent,
            "total_notifications_skipped": self.total_notifications_skipped,
            "total_errors": self.total_errors,
            "active_tokens": self.active_tokens,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
        }


class MCPProgressHandler:
    """Manages MCP progress notifications for active requests.

    This handler tracks active progress tokens from incoming requests and provides
    functionality to send progress notifications with rate limiting to prevent
    notification flooding.

    Example:
        handler = MCPProgressHandler()

        # Register a progress token from request
        handler.register_token("token-123")

        # Send progress updates (must be called within MCP request context)
        await handler.send_progress("token-123", 50, 100, "Halfway done")

        # Unregister when complete
        handler.unregister_token("token-123")
    """

    def __init__(
        self,
        min_update_interval: float = 0.1,
        max_update_interval: float = 5.0
    ):
        """Initialize the progress handler.

        Args:
            min_update_interval: Minimum seconds between updates (default 0.1s)
            max_update_interval: Maximum seconds between forced updates (default 5.0s)
        """
        self.active_tokens: Dict[str, bool] = {}  # Track active progress tokens
        self.logger = logging.getLogger(__name__)
        self._rate_limiters: Dict[str, float] = {}  # Last update time per token
        self._last_progress: Dict[str, float] = {}  # Last progress value per token
        self.min_update_interval = min_update_interval  # 100ms minimum between updates
        self.max_update_interval = max_update_interval  # 5s maximum between updates
        self.metrics = ProgressMetrics()  # Track metrics

    def register_token(self, progress_token: str) -> None:
        """Register a progress token from incoming request.

        Args:
            progress_token: The progress token to register
        """
        self.active_tokens[progress_token] = True
        self._rate_limiters[progress_token] = 0
        self._last_progress[progress_token] = -1  # Initialize to -1 to allow first update
        self.metrics.active_tokens = len(self.active_tokens)
        self.logger.debug(f"Registered progress token: {progress_token}")

    def unregister_token(self, progress_token: str) -> None:
        """Unregister token when operation completes.

        Args:
            progress_token: The progress token to unregister
        """
        self.active_tokens.pop(progress_token, None)
        self._rate_limiters.pop(progress_token, None)
        self._last_progress.pop(progress_token, None)
        self.metrics.active_tokens = len(self.active_tokens)
        self.logger.debug(f"Unregistered progress token: {progress_token}")

    async def send_progress(
        self,
        progress_token: str,
        progress: float,
        total: Optional[float] = None,
        message: Optional[str] = None
    ) -> bool:
        """Send MCP progress notification with rate limiting.

        This method implements rate limiting to prevent notification flooding:
        - Updates are skipped if less than min_update_interval has passed
        - Updates are forced if more than max_update_interval has passed
        - Final updates (progress == total) are always sent

        Args:
            progress_token: The progress token for this operation
            progress: Current progress value (must increase monotonically)
            total: Optional total expected value
            message: Optional human-readable progress message

        Returns:
            bool: True if notification was sent, False if skipped due to rate limiting
        """
        if progress_token not in self.active_tokens:
            self.logger.warning(
                f"Attempted to send progress for inactive token: {progress_token}"
            )
            return False

        # Get current time
        current_time = time.time()
        last_update = self._rate_limiters.get(progress_token, 0)
        time_since_last = current_time - last_update

        # Get last progress value
        last_progress = self._last_progress.get(progress_token, -1)

        # Check if this is the final update
        is_final = total is not None and progress >= total

        # Rate limiting logic:
        # 1. Always send if it's the final update
        # 2. Always send if max_update_interval has passed (prevent stale updates)
        # 3. Skip if less than min_update_interval has passed (prevent flooding)
        # 4. Always send if progress value changed significantly
        should_send = (
            is_final or
            time_since_last >= self.max_update_interval or
            time_since_last >= self.min_update_interval
        )

        if not should_send:
            self.metrics.total_notifications_skipped += 1
            self.logger.debug(
                f"Skipping progress update for {progress_token} due to rate limiting "
                f"(time_since_last={time_since_last:.3f}s)"
            )
            return False

        # Validate monotonic progress
        if progress < last_progress and not is_final:
            self.logger.warning(
                f"Progress decreased for {progress_token}: {last_progress} -> {progress}. "
                f"MCP spec requires monotonically increasing progress."
            )

        self._rate_limiters[progress_token] = current_time
        self._last_progress[progress_token] = progress

        try:
            # Get the global server instance
            # Note: This must be set during server initialization
            global server
            if server is None:
                # Try to import if not set yet
                try:
                    from server import main
                    server = main.server
                except ImportError:
                    self.logger.warning("Server not initialized yet")
                    return False

            # Get the request context to access the session
            try:
                context = server.request_context
                session = context.session

                # Send notification through MCP session
                # Note: MCP spec doesn't include 'message' in progress params
                # Messages should be logged separately or included in tool output
                await session.send_progress_notification(
                    progress_token=progress_token,
                    progress=progress,
                    total=total
                )

                self.metrics.total_notifications_sent += 1
                self.logger.debug(
                    f"Sent progress: {progress}/{total if total else '?'} - {message}"
                )
                return True

            except LookupError:
                # No request context available (e.g., called outside of request)
                self.metrics.total_errors += 1
                self.metrics.last_error = "No active request context"
                self.metrics.last_error_time = datetime.now()
                self.logger.warning(
                    f"Cannot send progress - no active request context"
                )
                return False

        except Exception as e:
            self.metrics.total_errors += 1
            self.metrics.last_error = str(e)
            self.metrics.last_error_time = datetime.now()
            self.logger.error(
                f"Failed to send progress notification: {e}",
                exc_info=True
            )
            return False

    def is_active(self, progress_token: str) -> bool:
        """Check if progress token is still active.

        Args:
            progress_token: The progress token to check

        Returns:
            bool: True if the token is active, False otherwise
        """
        return progress_token in self.active_tokens

    def get_active_token_count(self) -> int:
        """Get the number of currently active tokens.

        Returns:
            int: The number of active progress tokens
        """
        return len(self.active_tokens)

    def clear_all(self) -> None:
        """Clear all active tokens and state.

        This is useful for testing or cleanup scenarios.
        """
        self.active_tokens.clear()
        self._rate_limiters.clear()
        self._last_progress.clear()
        self.metrics.active_tokens = 0
        self.logger.info("Cleared all progress handler state")

    def get_metrics(self) -> Dict:
        """Get current metrics for monitoring and debugging.

        Returns:
            Dictionary containing progress notification metrics
        """
        self.metrics.active_tokens = len(self.active_tokens)
        return self.metrics.to_dict()

    def reset_metrics(self) -> None:
        """Reset metrics counters (keeps active tokens)."""
        active_count = len(self.active_tokens)
        self.metrics = ProgressMetrics(active_tokens=active_count)
        self.logger.info("Reset progress handler metrics")


def create_progress_callback(
    handler: MCPProgressHandler,
    progress_token: str
) -> ProgressCallback:
    """Create a progress callback function for a specific token.

    This is a convenience function that creates a callback suitable for use
    with tools and async jobs.

    Args:
        handler: The MCPProgressHandler instance
        progress_token: The progress token to use

    Returns:
        A progress callback function

    Example:
        handler = MCPProgressHandler()
        handler.register_token("token-123")

        callback = create_progress_callback(handler, "token-123")
        await some_long_operation(progress_callback=callback)
    """
    async def callback(
        progress: float,
        total: Optional[float] = None,
        message: Optional[str] = None
    ) -> None:
        await handler.send_progress(progress_token, progress, total, message)

    return callback
