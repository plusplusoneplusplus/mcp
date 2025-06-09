import os
import pytest

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import registry
from mcp_tools.plugin_config import PluginConfig, config

class DummyTool(ToolInterface):
    """Simple tool for testing exclusion."""

    @property
    def name(self) -> str:
        return "dummy_tool"

    @property
    def description(self) -> str:
        return "Dummy tool for testing"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True}


def test_excluded_tool_single(monkeypatch):
    """Tools listed in MCP_EXCLUDED_TOOL_NAMES are not registered."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "dummy_tool")
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == {"dummy_tool"}
    assert not cfg.should_register_tool_class("DummyTool", "dummy_tool", set())


def test_excluded_tool_multiple_whitespace(monkeypatch):
    """Comma separated values and whitespace are parsed correctly."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "tool_a, tool_b , tool_c")
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == {"tool_a", "tool_b", "tool_c"}


def test_excluded_tool_integration(monkeypatch):
    """Plugin registry skips tools specified in MCP_EXCLUDED_TOOL_NAMES."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "dummy_tool")
    config._load_from_env()
    registry.clear()
    registry.register_tool(DummyTool, source="code")
    assert "dummy_tool" not in registry.tools
