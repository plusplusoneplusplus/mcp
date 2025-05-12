import time
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool
from typing import Dict, Any

from mcp_tools import time_util


@register_tool
class TimeTool(ToolInterface):
    @property
    def name(self) -> str:
        return "time_tool"

    @property
    def description(self) -> str:
        return (
            "Returns a time string. If 'time_point' is missing or 'now', returns the current time. "
            "If 'delta' is provided, shifts the time_point by the delta (e.g., '5m', '2d', '3h', '42s'). "
            "Always respects the timezone (default 'UTC')."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform (get_time)",
                    "enum": ["get_time"],
                    "default": "get_time",
                },
                "time_point": {
                    "type": "string",
                    "description": "The base time as a string (optional, defaults to now). Use 'now' for current time.",
                    "nullable": True,
                },
                "delta": {
                    "type": "string",
                    "description": (
                        "A delta string to add to the time_point (e.g., '5m', '2d', '3h', '42s'). "
                        "Optional."
                    ),
                    "nullable": True,
                },
                "timezone": {
                    "type": "string",
                    "description": "The timezone name (IANA, e.g. 'UTC', 'Asia/Shanghai'). Default is 'UTC'",
                    "default": "UTC",
                },
            },
            "required": ["operation"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]):
        op = arguments.get("operation", "get_time")
        timezone = arguments.get("timezone", "UTC")
        if op == "get_time":
            time_point = arguments.get("time_point")
            delta = arguments.get("delta")
            try:
                return time_util.get_time(time_point, delta, timezone)
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": f"Unknown operation: {op}"}


get_time = time_util.get_time

__all__ = ["TimeTool", "get_time"]
