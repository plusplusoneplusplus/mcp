import shutil
import subprocess
import pytest

from mcp_tools.command_executor.tmux_executor import TmuxExecutor

# Skip tests if tmux is not available
if shutil.which("tmux") is None:
    pytest.skip("tmux is not available", allow_module_level=True)


def test_create_session_send_keys_and_capture():
    executor = TmuxExecutor()
    session = "mcp_test_session"

    # Create session
    result = executor.create_session(session)
    assert result["success"] is True

    # Send a command and capture output
    send_result = executor.send_keys(
        session, "echo hello", enter=True, capture=True
    )
    assert send_result["success"] is True
    assert "hello" in send_result.get("output", "")

    # Close the session
    close_result = executor.close_session(session)
    assert close_result["success"] is True
