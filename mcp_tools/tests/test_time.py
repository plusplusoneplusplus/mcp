import re
import datetime
import pytest
from mcp_tools.time.tool import get_time, TimeTool

# Utility for async test
pytestmark = pytest.mark.asyncio

def test_get_time_now_default_utc():
    now_str = get_time()
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", now_str)

def test_get_time_now_timezone():
    utc_time = get_time(time_point="now", timezone="UTC")
    sh_time = get_time(time_point="now", timezone="Asia/Shanghai")
    assert utc_time != sh_time
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", sh_time)

def test_get_time_with_time_point():
    base = "2024-07-01 12:00:00"
    result = get_time(time_point=base, timezone="UTC")
    assert result == base

def test_get_time_with_delta_minutes():
    base = "2024-07-01 12:00:00"
    result = get_time(time_point=base, delta="5m", timezone="UTC")
    assert result == "2024-07-01 12:05:00"

def test_get_time_with_delta_days():
    base = "2024-07-01 12:00:00"
    result = get_time(time_point=base, delta="2d", timezone="UTC")
    assert result == "2024-07-03 12:00:00"

def test_get_time_with_delta_hours():
    base = "2024-07-01 12:00:00"
    result = get_time(time_point=base, delta="3h", timezone="UTC")
    assert result == "2024-07-01 15:00:00"

def test_get_time_with_delta_seconds():
    base = "2024-07-01 12:00:00"
    result = get_time(time_point=base, delta="42s", timezone="UTC")
    assert result == "2024-07-01 12:00:42"

def test_get_time_now_with_delta():
    now = datetime.datetime.now(datetime.timezone.utc)
    result = get_time(time_point="now", delta="1m", timezone="UTC")
    dt = datetime.datetime.strptime(result, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
    assert 58 <= (dt - now).total_seconds() <= 62

def test_get_time_invalid_delta():
    with pytest.raises(ValueError):
        get_time(time_point="2024-07-01 12:00:00", delta="bad", timezone="UTC")

def test_get_time_invalid_timezone():
    base = "2024-07-01 12:00:00"
    # Should fallback to UTC
    result = get_time(time_point=base, delta="1m", timezone="Invalid/Zone")
    assert result == "2024-07-01 12:01:00"

# Async tests for TimeTool
import asyncio

async def test_time_tool_get_time_now():
    tool = TimeTool()
    result = await tool.execute_tool({"operation": "get_time"})
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result)

async def test_time_tool_get_time_with_delta():
    tool = TimeTool()
    base = "2024-07-01 12:00:00"
    result = await tool.execute_tool({"operation": "get_time", "time_point": base, "delta": "5m", "timezone": "UTC"})
    assert result == "2024-07-01 12:05:00"

async def test_time_tool_get_time_now_with_delta():
    tool = TimeTool()
    now = datetime.datetime.now(datetime.timezone.utc)
    result = await tool.execute_tool({"operation": "get_time", "time_point": "now", "delta": "1m", "timezone": "UTC"})
    dt = datetime.datetime.strptime(result, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
    assert 58 <= (dt - now).total_seconds() <= 62

async def test_time_tool_get_time_invalid_delta():
    tool = TimeTool()
    res = await tool.execute_tool({"operation": "get_time", "time_point": "2024-07-01 12:00:00", "delta": "bad"})
    assert not res["success"]
    assert "Invalid delta string" in res["error"]

async def test_time_tool_unknown_operation():
    tool = TimeTool()
    res = await tool.execute_tool({"operation": "unknown_op"})
    assert not res["success"]
    assert "Unknown operation" in res["error"] 