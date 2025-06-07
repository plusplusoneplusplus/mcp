import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, patch

import pytest

from mcp_tools.yaml_tools import YamlToolBase
from mcp_tools.interfaces import CommandExecutorInterface


class SimpleMockExecutor(CommandExecutorInterface):
    """Minimal command executor for testing."""

    def __init__(self):
        self.executed = []
        self.async_result = {"token": "tkn", "status": "running", "pid": 1}
        self.query_result = {"status": "running", "pid": 1}

    @property
    def name(self) -> str:
        return "simple"

    @property
    def description(self) -> str:
        return "simple executor"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object"}

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        return {}

    def execute(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        self.executed.append(command)
        return {}

    async def execute_async(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        self.executed.append(command)
        return self.async_result

    async def query_process(self, token: str, wait: bool = False, timeout: Optional[float] = None) -> Dict[str, Any]:
        return self.query_result

    def terminate_by_token(self, token: str) -> bool:
        return True

    def list_running_processes(self) -> list:
        return []

    async def start_periodic_status_reporter(self, interval: float = 30.0, enabled: bool = True) -> None:
        return None

    async def stop_periodic_status_reporter(self) -> None:
        return None


@pytest.fixture
def mock_executor():
    return SimpleMockExecutor()


@pytest.mark.asyncio
async def test_execute_task_success(mock_executor):
    tool = YamlToolBase(tool_name="execute_task", command_executor=mock_executor)
    tasks = {"hello": {"commands": {"linux": "echo hi"}}}
    with patch.object(tool, "_load_tasks_from_yaml", return_value=tasks), \
         patch("platform.system", return_value="Linux"), \
         patch.object(tool, "_get_server_dir", return_value=Path("/dir")):
        result = await tool._execute_task({"task_name": "hello"})
    assert mock_executor.executed[0] == "echo hi"
    assert result[0]["type"] == "text"
    assert "token" in result[0]["text"]


@pytest.mark.asyncio
async def test_execute_task_no_task(mock_executor):
    tool = YamlToolBase(tool_name="execute_task", command_executor=mock_executor)
    with patch.object(tool, "_load_tasks_from_yaml", return_value={}):
        result = await tool._execute_task({"task_name": "missing"})
    assert "not found" in result[0]["text"]


@pytest.mark.asyncio
async def test_execute_task_no_command_for_os(mock_executor):
    tool = YamlToolBase(tool_name="execute_task", command_executor=mock_executor)
    tasks = {"task1": {"commands": {"windows": "dir"}}}
    with patch.object(tool, "_load_tasks_from_yaml", return_value=tasks), \
         patch("platform.system", return_value="Linux"):
        result = await tool._execute_task({"task_name": "task1"})
    assert "No command" in result[0]["text"]
    assert "linux" in result[0]["text"]


@pytest.mark.asyncio
async def test_query_status_completed(mock_executor):
    tool = YamlToolBase(tool_name="query_task_status", command_executor=mock_executor)
    mock_executor.query_result = {"status": "completed", "success": True, "output": "done", "pid": 5}
    result = await tool._query_status({"token": "abc"})
    assert "Process completed" in result[0]["text"]
    assert "abc" in result[0]["text"]


@pytest.mark.asyncio
async def test_query_status_missing_token(mock_executor):
    tool = YamlToolBase(tool_name="query_task_status", command_executor=mock_executor)
    result = await tool._query_status({})
    assert "Token is required" in result[0]["text"]


@pytest.mark.asyncio
async def test_list_tasks(mock_executor):
    tool = YamlToolBase(tool_name="list_tasks", command_executor=mock_executor)
    tasks = {"a": {"description": "first"}, "b": {"description": "second"}}
    with patch.object(tool, "_load_tasks_from_yaml", return_value=tasks):
        result = await tool._list_tasks()
    assert "Available tasks" in result[0]["text"]
    assert "a: first" in result[0]["text"]


@pytest.mark.asyncio
async def test_list_tasks_none(mock_executor):
    tool = YamlToolBase(tool_name="list_tasks", command_executor=mock_executor)
    with patch.object(tool, "_load_tasks_from_yaml", return_value={}):
        result = await tool._list_tasks()
    assert result[0]["text"] == "No tasks available"


@pytest.mark.asyncio
async def test_list_instructions(mock_executor):
    tool = YamlToolBase(tool_name="list_instructions", command_executor=mock_executor)
    result = await tool._list_instructions()
    assert result[0]["text"] == "No instructions available"


@pytest.mark.asyncio
async def test_get_instruction_missing_name(mock_executor):
    tool = YamlToolBase(tool_name="get_instruction", command_executor=mock_executor)
    result = await tool._get_instruction({})
    assert "Instruction name is required" in result[0]["text"]

