# MCP Time Tool

This tool provides simple time-related utilities for MCP tools.

## Interfaces

### 1. `get_current_time(fmt: str = "%Y-%m-%d %H:%M:%S") -> str`
Returns the current time as a formatted string.
- `fmt`: (optional) Format string for `datetime.strftime`. Default: `%Y-%m-%d %H:%M:%S`.

### 2. `get_time_delta(time_point: Union[str, datetime.datetime], fmt: str = "%Y-%m-%d %H:%M:%S", in_delta: bool = False) -> Union[datetime.timedelta, str]`
Returns the time delta between now and a given time point.
- `time_point`: The time point as a string (in the given format) or a `datetime` object.
- `fmt`: (optional) The format string if `time_point` is a string. Default: `%Y-%m-%d %H:%M:%S`.
- `in_delta`: (optional) If `True`, returns a user-friendly string (e.g., `1m`, `2h`, `3d`, `42s`). If `False`, returns a `datetime.timedelta` object.

## Example Usage
```python
from mcp_tools.time import get_current_time, get_time_delta

now = get_current_time()
print(f"Current time: {now}")

delta = get_time_delta("2024-07-01 12:00:00")
print(f"Time since 2024-07-01 12:00:00: {delta}")
``` 