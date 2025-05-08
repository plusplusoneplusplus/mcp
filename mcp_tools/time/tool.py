import datetime
from typing import Union, Dict, Any
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool
import re
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # For Python <3.9, if needed


def parse_delta_string(delta_str: str) -> datetime.timedelta:
    """
    Parse a delta string like '5m', '-2d', '3h', '-42s' into a timedelta.
    Supports: s (seconds), m (minutes), h (hours), d (days)
    Allows optional leading minus for negative deltas.
    """
    match = re.fullmatch(r"([+-]?\d+)([smhd])", delta_str.strip())
    if not match:
        raise ValueError(f"Invalid delta string: {delta_str}")
    value, unit = match.groups()
    value = int(value)
    if unit == 's':
        return datetime.timedelta(seconds=value)
    elif unit == 'm':
        return datetime.timedelta(minutes=value)
    elif unit == 'h':
        return datetime.timedelta(hours=value)
    elif unit == 'd':
        return datetime.timedelta(days=value)
    else:
        raise ValueError(f"Unknown delta unit: {unit}")


def get_time(time_point: Union[str, None] = None, delta: Union[str, None] = None, timezone: str = "UTC") -> str:
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        tz = ZoneInfo("UTC")
    if not time_point or time_point == "now":
        base_time = datetime.datetime.now(tz)
    else:
        base_time = datetime.datetime.strptime(time_point, "%Y-%m-%d %H:%M:%S")
        base_time = base_time.replace(tzinfo=tz)
    if delta:
        delta_td = parse_delta_string(delta)
        base_time = base_time + delta_td
    return base_time.strftime("%Y-%m-%d %H:%M:%S")

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
                    "default": "get_time"
                },
                "time_point": {
                    "type": "string",
                    "description": "The base time as a string (optional, defaults to now). Use 'now' for current time.",
                    "nullable": True
                },
                "delta": {
                    "type": "string",
                    "description": (
                        "A delta string to add to the time_point (e.g., '5m', '2d', '3h', '42s'). "
                        "Optional."
                    ),
                    "nullable": True
                },
                "timezone": {
                    "type": "string",
                    "description": "The timezone name (IANA, e.g. 'UTC', 'Asia/Shanghai'). Default is 'UTC'",
                    "default": "UTC"
                }
            },
            "required": ["operation"]
        }

    async def execute_tool(self, arguments: Dict[str, Any]):
        op = arguments.get("operation", "get_time")
        timezone = arguments.get("timezone", "UTC")
        if op == "get_time":
            time_point = arguments.get("time_point")
            delta = arguments.get("delta")
            try:
                return get_time(time_point, delta, timezone)
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": f"Unknown operation: {op}"}

__all__ = ["TimeTool", "get_time"] 