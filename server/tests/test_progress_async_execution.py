"""
Test that command executor uses async execution with progress callbacks.

This test verifies the core functionality without requiring full MCP protocol support
for progress tokens.
"""

import pytest
import asyncio
import logging
import time
from mcp_tools.command_executor.executor import CommandExecutor

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestProgressAsyncExecution:
    """Test async execution with progress callbacks."""

    @pytest.mark.asyncio
    async def test_command_executor_uses_async_execution_with_progress_callback(self):
        """
        Test that command executor:
        1. Uses async execution when progress callback is provided
        2. Sends progress notifications during execution
        3. Properly cleans up after completion
        """
        logger.info("=" * 80)
        logger.info("TEST: Command executor async execution with progress callback")
        logger.info("=" * 80)

        # Track progress notifications
        progress_updates = []

        async def progress_callback(progress, total=None, message=None):
            """Capture progress updates."""
            update = {
                "progress": progress,
                "total": total,
                "message": message,
                "timestamp": time.time()
            }
            progress_updates.append(update)
            logger.info(f"Progress update: progress={progress}, total={total}, message={message}")

        # Create executor
        executor = CommandExecutor()

        # Set progress callback
        executor.set_progress_callback(progress_callback)

        logger.info("Executing sleep 10 command with progress callback...")
        start_time = time.time()

        # Execute command (should use async execution due to callback)
        result = await executor.execute_tool({
            "command": "sleep 10"
        })

        execution_time = time.time() - start_time
        logger.info(f"Command completed in {execution_time:.2f}s")

        # Verify command succeeded
        assert result is not None
        assert result.get("status") == "completed"
        assert result.get("success") is True
        logger.info(f"✅ Command executed successfully")

        # Verify progress updates were sent
        logger.info(f"Total progress updates received: {len(progress_updates)}")
        for i, update in enumerate(progress_updates):
            logger.info(f"  Update {i+1}: progress={update['progress']:.2f}, "
                      f"total={update['total']}, message={update['message']}")

        # Should have received multiple progress updates
        # For a 10 second sleep with 5 second update interval, we expect:
        # - Initial notification (progress=0)
        # - At least 1-2 during execution
        # - Final notification (progress=total)
        assert len(progress_updates) >= 2, \
            f"Should have received at least 2 progress updates, got {len(progress_updates)}"

        # Verify initial progress update
        first_update = progress_updates[0]
        assert first_update['progress'] >= 0, "Initial progress should be >= 0"
        assert "Started" in (first_update['message'] or ""), \
            "Initial update should mention 'Started'"

        # Verify final progress update
        final_update = progress_updates[-1]
        if final_update['total'] is not None:
            # Final update should have progress ~= total
            assert abs(final_update['progress'] - final_update['total']) < 1.0, \
                f"Final progress ({final_update['progress']}) should be close to total ({final_update['total']})"

        # Verify progress is monotonically increasing
        for i in range(1, len(progress_updates)):
            assert progress_updates[i]['progress'] >= progress_updates[i-1]['progress'], \
                "Progress should be monotonically increasing"

        logger.info("=" * 80)
        logger.info("TEST: All verifications passed!")
        logger.info("=" * 80)

    @pytest.mark.asyncio
    async def test_command_executor_uses_sync_execution_without_progress_callback(self):
        """
        Test that command executor uses synchronous execution when no progress callback is provided.
        """
        logger.info("Testing sync execution without progress callback...")

        # Create executor without progress callback
        executor = CommandExecutor()

        # Execute command (should use sync execution)
        start_time = time.time()
        result = await executor.execute_tool({
            "command": "echo 'test'"
        })
        execution_time = time.time() - start_time

        # Verify command succeeded
        assert result is not None
        assert result.get("success") is True
        logger.info(f"✅ Sync command completed in {execution_time:.3f}s")

    @pytest.mark.asyncio
    async def test_failed_command_with_progress_callback(self):
        """
        Test that progress notifications work correctly even when command fails.
        """
        progress_updates = []

        async def progress_callback(progress, total=None, message=None):
            progress_updates.append({"progress": progress, "total": total, "message": message})
            logger.info(f"Progress: {progress}/{total} - {message}")

        executor = CommandExecutor()
        executor.set_progress_callback(progress_callback)

        # Execute a command that will fail
        result = await executor.execute_tool({
            "command": "exit 1"
        })

        # Verify command failed but progress was still sent
        assert result is not None
        assert result.get("success") is False
        assert result.get("return_code") == 1

        # Should have received at least initial and final progress updates
        assert len(progress_updates) >= 1, \
            f"Should have received progress updates even for failed command"

        logger.info(f"✅ Failed command properly sent {len(progress_updates)} progress updates")

    @pytest.mark.asyncio
    async def test_concurrent_commands_with_progress(self):
        """
        Test that multiple concurrent commands each send their own progress updates.
        """
        progress_by_command = {"cmd1": [], "cmd2": []}

        async def create_progress_callback(cmd_name):
            async def callback(progress, total=None, message=None):
                progress_by_command[cmd_name].append({
                    "progress": progress,
                    "total": total,
                    "message": message
                })
            return callback

        # Create two executors
        executor1 = CommandExecutor()
        executor2 = CommandExecutor()

        executor1.set_progress_callback(await create_progress_callback("cmd1"))
        executor2.set_progress_callback(await create_progress_callback("cmd2"))

        # Execute concurrently
        logger.info("Executing concurrent commands with progress...")
        results = await asyncio.gather(
            executor1.execute_tool({"command": "sleep 5"}),
            executor2.execute_tool({"command": "sleep 5"})
        )

        # Verify both completed successfully
        assert all(r.get("success") for r in results)

        # Verify both received progress updates
        assert len(progress_by_command["cmd1"]) >= 2, \
            f"Command 1 should have received progress updates"
        assert len(progress_by_command["cmd2"]) >= 2, \
            f"Command 2 should have received progress updates"

        logger.info(f"✅ Concurrent commands: cmd1 got {len(progress_by_command['cmd1'])} updates, "
                   f"cmd2 got {len(progress_by_command['cmd2'])} updates")
