"""
End-to-end test for MCP progress notifications with real client-server communication.

This test validates the complete MCP progress notification flow:
1. Client sends tool call with progressToken in request meta
2. Server registers the progress token
3. Server sends periodic progress notifications during execution
4. Server unregisters token after completion
"""

import pytest
import asyncio
import logging
import time
import uuid
from mcp import types
from .conftest import create_mcp_client

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestMCPProgressE2E:
    """End-to-end tests for MCP progress notifications."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        __import__('os').name == 'nt',
        reason="Skipping on Windows due to async process handling"
    )
    async def test_real_mcp_progress_notifications_with_sleep_command(self, mcp_client_info):
        """
        Test real MCP progress notifications end-to-end:
        - Client sends tool call with progressToken
        - Server sends progress notifications
        - Client receives progress notifications
        - Token is properly cleaned up
        """
        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        progress_notifications = []
        progress_token = str(uuid.uuid4())

        logger.info("=" * 80)
        logger.info(f"TEST: Real MCP Progress E2E (token: {progress_token})")
        logger.info("=" * 80)

        async with create_mcp_client(server_url, worker_id) as session:
            # Set up a custom message handler to capture progress notifications
            original_handler = session._message_handler

            async def custom_handler(message):
                """Capture progress notifications."""
                # Check if this is a progress notification BEFORE calling original handler
                if isinstance(message, types.ServerNotification):
                    # ServerNotification is a RootModel, the actual notification is in .root
                    notif = message.root
                    if isinstance(notif, types.ProgressNotification):
                        logger.info(f"📊 Progress notification received: {notif}")
                        progress_notifications.append({
                            "progress_token": notif.params.progressToken,
                            "progress": notif.params.progress,
                            "total": notif.params.total,
                            "timestamp": time.time()
                        })

                # Call original handler
                await original_handler(message)

            # Monkey-patch the message handler
            session._message_handler = custom_handler

            logger.info(f"Sending tool call with progress token: {progress_token}")

            # Create a CallToolRequest with meta.progressToken
            # We need to use send_request directly to include meta
            request = types.ClientRequest(
                types.CallToolRequest(
                    method="tools/call",
                    params=types.CallToolRequestParams(
                        name="command_executor",
                        arguments={"command": "sleep 10"},
                        _meta=types.RequestParams.Meta(
                            progressToken=progress_token
                        )
                    )
                )
            )

            start_time = time.time()
            result = await session.send_request(
                request,
                types.CallToolResult
            )
            execution_time = time.time() - start_time

            logger.info(f"Command completed in {execution_time:.2f}s")
            logger.info(f"Result: {result}")

            # Give time for any final notifications
            await asyncio.sleep(0.5)

            logger.info("=" * 80)
            logger.info("TEST: Verifying progress notifications")
            logger.info("=" * 80)

            # Log all received notifications
            logger.info(f"Total progress notifications received: {len(progress_notifications)}")
            for i, notif in enumerate(progress_notifications):
                logger.info(f"  Notification {i+1}:")
                logger.info(f"    Token: {notif['progress_token']}")
                logger.info(f"    Progress: {notif['progress']:.2f}")
                logger.info(f"    Total: {notif['total']}")

            # Verify we received progress notifications
            assert len(progress_notifications) > 0, \
                f"Should have received at least one progress notification, got {len(progress_notifications)}"

            # Verify all notifications have the correct token
            for notif in progress_notifications:
                assert notif['progress_token'] == progress_token, \
                    f"Progress token mismatch: expected {progress_token}, got {notif['progress_token']}"

            # Verify progress is monotonically increasing
            if len(progress_notifications) > 1:
                for i in range(1, len(progress_notifications)):
                    assert progress_notifications[i]['progress'] >= progress_notifications[i-1]['progress'], \
                        "Progress should be monotonically increasing"

            # Check for final notification (where progress == total)
            final_notif = progress_notifications[-1]
            if final_notif['total'] is not None:
                logger.info(f"✅ Final notification: progress={final_notif['progress']:.2f}, total={final_notif['total']:.2f}")
                # Allow for small floating point differences
                assert abs(final_notif['progress'] - final_notif['total']) < 1.0, \
                    f"Final notification should have progress ~= total"

            logger.info("=" * 80)
            logger.info("✅ All progress notification tests passed!")
            logger.info("=" * 80)

    @pytest.mark.asyncio
    async def test_tool_call_without_progress_token_works_normally(self, mcp_client_info):
        """
        Test that tool calls without progress tokens still work normally.
        """
        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            # Regular call_tool without progress token
            result = await session.call_tool(
                "command_executor",
                {"command": "echo 'no progress token'"}
            )

            assert result is not None
            assert len(result.content) > 0
            logger.info("✅ Tool call without progress token works normally")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        __import__('os').name == 'nt',
        reason="Skipping on Windows due to test worker compatibility issues"
    )
    async def test_concurrent_progress_tokens_dont_interfere(self, mcp_client_info):
        """
        Test that concurrent tool calls with different progress tokens
        don't interfere with each other.
        """
        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        progress_by_token = {}
        token1 = str(uuid.uuid4())
        token2 = str(uuid.uuid4())

        logger.info(f"Testing concurrent progress with tokens: {token1}, {token2}")

        async with create_mcp_client(server_url, worker_id) as session:
            # Set up message handler to capture notifications
            original_handler = session._message_handler

            async def custom_handler(message):
                if isinstance(message, types.ServerNotification):
                    notif = message.root
                    if isinstance(notif, types.ProgressNotification):
                        token = notif.params.progressToken
                        if token not in progress_by_token:
                            progress_by_token[token] = []
                        progress_by_token[token].append({
                            "progress": notif.params.progress,
                            "total": notif.params.total
                        })

                await original_handler(message)

            session._message_handler = custom_handler

            # Execute two commands concurrently with different progress tokens
            async def run_with_progress(token, command):
                request = types.ClientRequest(
                    types.CallToolRequest(
                        method="tools/call",
                        params=types.CallToolRequestParams(
                            name="command_executor",
                            arguments={"command": command},
                            _meta=types.RequestParams.Meta(progressToken=token)
                        )
                    )
                )
                return await session.send_request(request, types.CallToolResult)

            results = await asyncio.gather(
                run_with_progress(token1, "sleep 5"),
                run_with_progress(token2, "sleep 5")
            )

            # Give time for final notifications
            await asyncio.sleep(0.5)

            # Verify both commands completed
            assert all(r is not None for r in results)

            # Verify we got progress for both tokens
            logger.info(f"Progress notifications by token:")
            logger.info(f"  Token 1: {len(progress_by_token.get(token1, []))} notifications")
            logger.info(f"  Token 2: {len(progress_by_token.get(token2, []))} notifications")

            assert token1 in progress_by_token, f"Should have received progress for token1"
            assert token2 in progress_by_token, f"Should have received progress for token2"

            assert len(progress_by_token[token1]) > 0, \
                f"Should have received progress notifications for token1"
            assert len(progress_by_token[token2]) > 0, \
                f"Should have received progress notifications for token2"

            logger.info("✅ Concurrent progress tokens work independently")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        __import__('os').name == 'nt',
        reason="Skipping on Windows due to test worker compatibility issues"
    )
    async def test_progress_token_cleanup_after_completion(self, mcp_client_info):
        """
        Test that progress tokens are properly cleaned up after command completion.
        """
        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            from server import main as server_main
            progress_handler = server_main.progress_handler

            # Get initial active tokens count
            initial_metrics = progress_handler.get_metrics()
            initial_tokens = initial_metrics['active_tokens']

            # Execute command with progress token
            token = str(uuid.uuid4())
            request = types.ClientRequest(
                types.CallToolRequest(
                    method="tools/call",
                    params=types.CallToolRequestParams(
                        name="command_executor",
                        arguments={"command": "echo 'test'"},
                        _meta=types.RequestParams.Meta(progressToken=token)
                    )
                )
            )

            result = await session.send_request(request, types.CallToolResult)
            assert result is not None

            # Give time for cleanup
            await asyncio.sleep(0.5)

            # Verify token was cleaned up
            final_metrics = progress_handler.get_metrics()
            final_tokens = final_metrics['active_tokens']

            logger.info(f"Active tokens: initial={initial_tokens}, final={final_tokens}")
            assert final_tokens == initial_tokens, \
                f"Active tokens should be back to initial count after cleanup"

            logger.info("✅ Progress token properly cleaned up after completion")
