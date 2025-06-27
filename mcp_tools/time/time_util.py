import datetime
from typing import Union, Dict, Any
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
    if unit == "s":
        return datetime.timedelta(seconds=value)
    elif unit == "m":
        return datetime.timedelta(minutes=value)
    elif unit == "h":
        return datetime.timedelta(hours=value)
    elif unit == "d":
        return datetime.timedelta(days=value)
    else:
        raise ValueError(f"Unknown delta unit: {unit}")


def get_time(
    time_point: Union[str, None] = None,
    delta: Union[str, None] = None,
    timezone: str = "UTC",
) -> str:
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
