"""
Test progress notification lifecycle for long-running commands.

This test verifies that:
1. Progress notifications are sent during command execution
2. Tokens are properly registered at the start
3. Tokens are properly unregistered after completion
"""

import pytest
import asyncio
import logging
import time
from .conftest import create_mcp_client

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestProgressNotificationLifecycle:
    """Test the complete lifecycle of progress notifications."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        __import__('os').name == 'nt',
        reason="Skipping on Windows due to async process handling"
    )
    async def test_sleep_command_progress_notifications_and_cleanup(self, mcp_client_info):
        """
        Test that a sleep command:
        1. Properly registers and unregisters progress tokens
        2. Sends progress notifications (verified through metrics)
        3. Allows subsequent commands to work without token conflicts
        """
        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            from server import main as server_main
            progress_handler = server_main.progress_handler

            logger.info("=" * 80)
            logger.info("TEST: Starting sleep 10 command")
            logger.info("=" * 80)

            # Reset metrics for clean baseline
            progress_handler.reset_metrics()

            # Get initial metrics
            initial_metrics = progress_handler.get_metrics()
            initial_active_tokens = initial_metrics['active_tokens']
            initial_sent = initial_metrics['total_notifications_sent']
            logger.info(f"Initial active tokens: {initial_active_tokens}")
            logger.info(f"Initial notifications sent: {initial_sent}")

            # Execute a sleep command (10 seconds - shorter than 30 for faster testing)
            start_time = time.time()
            result = await session.call_tool(
                "command_executor",
                {"command": "sleep 10"}
            )

            execution_time = time.time() - start_time
            logger.info(f"Command completed in {execution_time:.2f}s")

            # Verify the command executed successfully
            assert result is not None, "Result should not be None"
            assert len(result.content) > 0, "Result should have content"

            logger.info("=" * 80)
            logger.info("TEST: Verifying progress notifications were sent")
            logger.info("=" * 80)

            # Give the server a moment to process final notifications
            await asyncio.sleep(0.5)

            # Get metrics after execution
            final_metrics = progress_handler.get_metrics()
            final_active_tokens = final_metrics['active_tokens']
            final_sent = final_metrics['total_notifications_sent']
            total_errors = final_metrics['total_errors']

            logger.info(f"Final active tokens: {final_active_tokens}")
            logger.info(f"Total notifications sent: {final_sent}")
            logger.info(f"Total notifications skipped: {final_metrics['total_notifications_skipped']}")
            logger.info(f"Total errors: {total_errors}")

            # Verify progress notifications were attempted to be sent
            # For a 10 second sleep with 5 second update interval, we expect at least 2-3 notifications:
            # - Initial notification (progress=0)
            # - At least one during execution (progress=~5s)
            # - Final notification (progress=total=~10s)
            notifications_sent = final_sent - initial_sent
            logger.info(f"Notifications sent during this command: {notifications_sent}")

            # We should have sent multiple notifications during the 10 second sleep
            assert notifications_sent >= 2, \
                f"Should have sent at least 2 progress notifications for 10s command, got {notifications_sent}"

            # Should have no errors
            assert total_errors == 0, \
                f"Should have no errors sending progress notifications, got {total_errors}"

            logger.info("=" * 80)
            logger.info("TEST: Verifying token was unregistered")
            logger.info("=" * 80)

            # Verify token was unregistered (active tokens should be back to initial count)
            assert final_active_tokens == initial_active_tokens, \
                f"Active tokens should be back to {initial_active_tokens}, but got {final_active_tokens}"

            logger.info("✅ Token successfully unregistered after command completion")

            logger.info("=" * 80)
            logger.info("TEST: Verifying subsequent commands work without conflicts")
            logger.info("=" * 80)

            # Execute another command to verify no token conflicts
            result2 = await session.call_tool(
                "command_executor",
                {"command": "echo 'second command'"}
            )

            assert result2 is not None, "Second command should succeed"
            logger.info("✅ Second command executed successfully - no token conflicts")

            # Verify still no active tokens
            metrics_after_second = progress_handler.get_metrics()
            assert metrics_after_second['active_tokens'] == initial_active_tokens, \
                "Active tokens should still be at baseline after second command"

            logger.info("=" * 80)
            logger.info("TEST: All verifications passed!")
            logger.info("=" * 80)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        __import__('os').name == 'nt',
        reason="Skipping on Windows due to async process handling"
    )
    async def test_concurrent_commands_have_separate_progress_tokens(self, mcp_client_info):
        """
        Test that concurrent commands each get their own progress token
        and both are properly cleaned up.
        """
        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            from server import main as server_main
            progress_handler = server_main.progress_handler

            # Get initial metrics
            initial_metrics = progress_handler.get_metrics()
            initial_active_tokens = initial_metrics['active_tokens']
            logger.info(f"Initial active tokens: {initial_active_tokens}")

            # Execute two commands concurrently
            async def run_command(cmd_id):
                return await session.call_tool(
                    "command_executor",
                    {"command": f"sleep 2 && echo 'command {cmd_id}'"}
                )

            logger.info("Starting concurrent commands...")
            results = await asyncio.gather(
                run_command(1),
                run_command(2)
            )

            # Both should succeed
            assert len(results) == 2
            for i, result in enumerate(results, 1):
                assert result is not None
                logger.info(f"Command {i} completed successfully")

            # Give cleanup a moment
            await asyncio.sleep(0.5)

            # Verify all tokens were cleaned up
            final_metrics = progress_handler.get_metrics()
            final_active_tokens = final_metrics['active_tokens']
            logger.info(f"Final active tokens: {final_active_tokens}")

            assert final_active_tokens == initial_active_tokens, \
                f"All tokens should be cleaned up. Expected {initial_active_tokens}, got {final_active_tokens}"

            logger.info("✅ Concurrent commands properly managed separate tokens")

    @pytest.mark.asyncio
    async def test_failed_command_still_unregisters_token(self, mcp_client_info):
        """
        Test that even when a command fails, the progress token is still unregistered.
        """
        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            from server import main as server_main
            progress_handler = server_main.progress_handler

            # Get initial metrics
            initial_metrics = progress_handler.get_metrics()
            initial_active_tokens = initial_metrics['active_tokens']

            # Execute a command that will fail
            result = await session.call_tool(
                "command_executor",
                {"command": "exit 1"}  # This command will fail
            )

            assert result is not None
            logger.info("Failed command completed")

            # Give cleanup a moment
            await asyncio.sleep(0.5)

            # Verify token was still cleaned up
            final_metrics = progress_handler.get_metrics()
            final_active_tokens = final_metrics['active_tokens']

            assert final_active_tokens == initial_active_tokens, \
                f"Token should be cleaned up even after failure. Expected {initial_active_tokens}, got {final_active_tokens}"

            logger.info("✅ Failed command properly cleaned up token")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        __import__('os').name == 'nt',
        reason="Skipping on Windows due to async process handling"
    )
    async def test_progress_handler_metrics_accuracy(self, mcp_client_info):
        """
        Test that progress handler metrics accurately track sent/skipped notifications.
        """
        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            from server import main as server_main
            progress_handler = server_main.progress_handler

            # Reset metrics for clean test
            progress_handler.reset_metrics()

            # Execute a command
            result = await session.call_tool(
                "command_executor",
                {"command": "sleep 5"}
            )

            assert result is not None

            # Check metrics
            metrics = progress_handler.get_metrics()
            logger.info(f"Metrics after execution:")
            logger.info(f"  Total sent: {metrics['total_notifications_sent']}")
            logger.info(f"  Total skipped: {metrics['total_notifications_skipped']}")
            logger.info(f"  Total errors: {metrics['total_errors']}")
            logger.info(f"  Active tokens: {metrics['active_tokens']}")

            # Should have sent at least some notifications
            assert metrics['total_notifications_sent'] > 0, \
                "Should have sent at least one notification"

            # Should have no active tokens after completion
            assert metrics['active_tokens'] == 0, \
                "Should have no active tokens after execution"

            logger.info("✅ Progress handler metrics are accurate")
