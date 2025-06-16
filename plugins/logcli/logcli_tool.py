import logging
import subprocess
from typing import Any, Dict, List

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool


@register_tool
class LogCliTool(ToolInterface):
    """Interact with Grafana Loki via the ``logcli`` command line tool."""

    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        return "logcli"

    @property
    def description(self) -> str:
        return "Query a Loki server using the logcli command line"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["query", "labels"],
                    "description": "logcli operation to perform",
                },
                "query": {
                    "type": "string",
                    "description": "LogQL query string",
                    "nullable": True,
                },
                "label": {
                    "type": "string",
                    "description": "Label name for labels operation",
                    "nullable": True,
                },
                "since": {
                    "type": "string",
                    "description": "Start time for range queries",
                    "nullable": True,
                },
                "until": {
                    "type": "string",
                    "description": "End time for range queries",
                    "nullable": True,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of log lines",
                    "default": 20,
                },
            },
            "required": ["operation"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"error": "Missing required parameter: operation"}
        return await self.execute_function(operation, arguments)

    async def execute_function(
        self, function_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        if function_name == "query":
            query = parameters.get("query")
            if not query:
                return {"success": False, "error": "Missing required parameter: query"}
            since = parameters.get("since")
            until = parameters.get("until")
            limit = parameters.get("limit")
            cmd: List[str] = ["logcli", "query", query]
            if since:
                cmd.extend(["--since", str(since)])
            if until:
                cmd.extend(["--until", str(until)])
            if limit is not None:
                cmd.extend(["--limit", str(limit)])
            return self._run_logcli(cmd)

        if function_name == "labels":
            cmd = ["logcli", "labels"]
            label = parameters.get("label")
            if label:
                cmd.append(label)
            return self._run_logcli(cmd)

        return {"success": False, "error": f"Unknown logcli operation: {function_name}"}

    def _run_logcli(self, cmd: List[str]) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr.strip() or "logcli command failed",
                }
            return {"success": True, "result": result.stdout.strip()}
        except FileNotFoundError:
            return {"success": False, "error": "logcli not found"}
        except Exception as e:  # pragma: no cover - unexpected errors
            self.logger.error(f"Error running logcli command {' '.join(cmd)}: {e}")
            return {"success": False, "error": str(e)}
