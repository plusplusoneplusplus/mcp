import subprocess
import shutil
from typing import Dict, Any, Optional

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool


def _has_tmux() -> bool:
    """Check if tmux is available on the system."""
    return shutil.which("tmux") is not None


@register_tool
class TmuxExecutor(ToolInterface):
    """Execute commands inside a tmux session using ``send-keys``."""

    @property
    def name(self) -> str:
        return "tmux_executor"

    @property
    def description(self) -> str:
        return (
            "Interact with tmux sessions using send-keys. Useful for automating "
            "commands that require interactive authentication."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["create_session", "send_keys", "close_session"],
                    "default": "send_keys",
                },
                "session_name": {
                    "type": "string",
                    "description": "Target tmux session name",
                },
                "keys": {
                    "type": "string",
                    "description": "Keys to send to the session (for send_keys)",
                    "nullable": True,
                },
                "enter": {
                    "type": "boolean",
                    "description": "Send Enter after keys (for send_keys)",
                    "default": True,
                },
                "capture": {
                    "type": "boolean",
                    "description": "Capture pane output after sending keys",
                    "default": False,
                },
                "start_command": {
                    "type": "string",
                    "description": "Command to run when creating a session",
                    "nullable": True,
                },
            },
            "required": ["operation", "session_name"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        op = arguments.get("operation", "send_keys")
        session = arguments.get("session_name")
        keys = arguments.get("keys")
        enter = arguments.get("enter", True)
        capture = arguments.get("capture", False)
        start_command = arguments.get("start_command")

        if not _has_tmux():
            return {"success": False, "error": "tmux is not available"}

        if op == "create_session":
            return self.create_session(session, start_command)
        elif op == "send_keys":
            if keys is None:
                return {"success": False, "error": "keys parameter required"}
            return self.send_keys(session, keys, enter, capture)
        elif op == "close_session":
            return self.close_session(session)
        else:
            return {"success": False, "error": f"Unknown operation: {op}"}

    def _run_tmux(self, args: list) -> subprocess.CompletedProcess:
        return subprocess.run(["tmux", *args], capture_output=True, text=True)

    def session_exists(self, session_name: str) -> bool:
        result = self._run_tmux(["has-session", "-t", session_name])
        return result.returncode == 0

    def create_session(
        self, session_name: str, start_command: Optional[str] = None
    ) -> Dict[str, Any]:
        if self.session_exists(session_name):
            created = False
        else:
            result = self._run_tmux(["new-session", "-d", "-s", session_name])
            if result.returncode != 0:
                return {"success": False, "error": result.stderr.strip()}
            created = True
        if start_command:
            self.send_keys(session_name, start_command, enter=True)
        return {"success": True, "session": session_name, "created": created}

    def send_keys(
        self, session_name: str, keys: str, enter: bool = True, capture: bool = False
    ) -> Dict[str, Any]:
        args = ["send-keys", "-t", session_name, keys]
        if enter:
            args.append("Enter")
        result = self._run_tmux(args)
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip()}

        response = {"success": True, "session": session_name}
        if capture:
            capture_result = self._run_tmux(["capture-pane", "-pt", session_name])
            if capture_result.returncode == 0:
                response["output"] = capture_result.stdout
            else:
                response["output"] = ""
        return response

    def close_session(self, session_name: str) -> Dict[str, Any]:
        result = self._run_tmux(["kill-session", "-t", session_name])
        if result.returncode == 0:
            return {"success": True, "session": session_name}
        return {"success": False, "error": result.stderr.strip()}
