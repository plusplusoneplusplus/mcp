import os
import pytest

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import registry
from mcp_tools.plugin_config import PluginConfig, config


@pytest.fixture(autouse=True)
def reset_plugin_state():
    """Reset plugin registry and config state before each test."""
    # Clear registry
    registry.clear()
    
    # Reset config to default state
    config.plugin_enable_mode = "all"
    config.enabled_plugins = set()
    config.disabled_plugins = set()
    config.excluded_tool_names = set()
    
    yield
    
    # Clean up after test
    registry.clear()

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


class AnotherDummyTool(ToolInterface):
    """Another simple tool for testing."""

    @property
    def name(self) -> str:
        return "another_dummy_tool"

    @property
    def description(self) -> str:
        return "Another dummy tool for testing"

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


# New tests for plugin enable/disable functionality

def test_plugin_enable_mode_default():
    """Default plugin enable mode should be 'all'."""
    cfg = PluginConfig()
    assert cfg.plugin_enable_mode == "all"


def test_plugin_enable_mode_from_env(monkeypatch):
    """Plugin enable mode should be loaded from MCP_PLUGIN_MODE environment variable."""
    monkeypatch.setenv("MCP_PLUGIN_MODE", "whitelist")
    cfg = PluginConfig()
    assert cfg.plugin_enable_mode == "whitelist"


def test_plugin_enable_mode_invalid(monkeypatch):
    """Invalid plugin enable mode should default to 'all'."""
    monkeypatch.setenv("MCP_PLUGIN_MODE", "invalid_mode")
    cfg = PluginConfig()
    assert cfg.plugin_enable_mode == "all"


def test_enabled_plugins_from_env(monkeypatch):
    """Enabled plugins should be loaded from MCP_ENABLED_PLUGINS environment variable."""
    monkeypatch.setenv("MCP_ENABLED_PLUGINS", "tool_a, tool_b , tool_c")
    cfg = PluginConfig()
    assert cfg.enabled_plugins == {"tool_a", "tool_b", "tool_c"}


def test_disabled_plugins_from_env(monkeypatch):
    """Disabled plugins should be loaded from MCP_DISABLED_PLUGINS environment variable."""
    monkeypatch.setenv("MCP_DISABLED_PLUGINS", "tool_x, tool_y , tool_z")
    cfg = PluginConfig()
    assert cfg.disabled_plugins == {"tool_x", "tool_y", "tool_z"}


def test_is_plugin_enabled_all_mode():
    """In 'all' mode, all plugins should be enabled unless explicitly disabled."""
    cfg = PluginConfig()
    cfg.plugin_enable_mode = "all"
    cfg.disabled_plugins = {"disabled_tool"}
    
    assert cfg.is_plugin_enabled("any_tool")
    assert not cfg.is_plugin_enabled("disabled_tool")


def test_is_plugin_enabled_whitelist_mode():
    """In 'whitelist' mode, only explicitly enabled plugins should be enabled."""
    cfg = PluginConfig()
    cfg.plugin_enable_mode = "whitelist"
    cfg.enabled_plugins = {"enabled_tool"}
    
    assert cfg.is_plugin_enabled("enabled_tool")
    assert not cfg.is_plugin_enabled("other_tool")


def test_is_plugin_enabled_blacklist_mode():
    """In 'blacklist' mode, all plugins should be enabled except explicitly disabled ones."""
    cfg = PluginConfig()
    cfg.plugin_enable_mode = "blacklist"
    cfg.disabled_plugins = {"disabled_tool"}
    
    assert cfg.is_plugin_enabled("any_tool")
    assert not cfg.is_plugin_enabled("disabled_tool")


def test_enable_plugin():
    """enable_plugin should add plugin to enabled set and remove from disabled set."""
    cfg = PluginConfig()
    cfg.disabled_plugins = {"test_tool"}
    
    cfg.enable_plugin("test_tool")
    
    assert "test_tool" in cfg.enabled_plugins
    assert "test_tool" not in cfg.disabled_plugins


def test_disable_plugin():
    """disable_plugin should add plugin to disabled set and remove from enabled set."""
    cfg = PluginConfig()
    cfg.enabled_plugins = {"test_tool"}
    
    cfg.disable_plugin("test_tool")
    
    assert "test_tool" in cfg.disabled_plugins
    assert "test_tool" not in cfg.enabled_plugins


def test_should_register_tool_class_disabled_plugin():
    """should_register_tool_class should return False for disabled plugins."""
    cfg = PluginConfig()
    cfg.disable_plugin("dummy_tool")
    
    assert not cfg.should_register_tool_class("DummyTool", "dummy_tool", set())


def test_should_register_tool_class_enabled_plugin():
    """should_register_tool_class should return True for enabled plugins."""
    cfg = PluginConfig()
    cfg.plugin_enable_mode = "whitelist"
    cfg.enable_plugin("dummy_tool")
    
    assert cfg.should_register_tool_class("DummyTool", "dummy_tool", set())


def test_plugin_registration_respects_enable_disable(monkeypatch):
    """Plugin registry should respect enable/disable settings during registration."""
    # Set up environment to disable dummy_tool
    monkeypatch.setenv("MCP_PLUGIN_MODE", "blacklist")
    monkeypatch.setenv("MCP_DISABLED_PLUGINS", "dummy_tool")
    
    # Reload configuration
    config._load_from_env()
    registry.clear()
    
    # Try to register the tool
    result = registry.register_tool(DummyTool, source="code")
    
    # Tool should not be registered
    assert result is None
    assert "dummy_tool" not in registry.tools


def test_plugin_registration_whitelist_mode(monkeypatch):
    """Plugin registry should only register whitelisted plugins in whitelist mode."""
    # Set up environment for whitelist mode
    monkeypatch.setenv("MCP_PLUGIN_MODE", "whitelist")
    monkeypatch.setenv("MCP_ENABLED_PLUGINS", "another_dummy_tool")
    
    # Reload configuration
    config._load_from_env()
    registry.clear()
    
    # Try to register both tools
    result1 = registry.register_tool(DummyTool, source="code")
    result2 = registry.register_tool(AnotherDummyTool, source="code")
    
    # Only the whitelisted tool should be registered
    assert result1 is None
    assert result2 is not None
    assert "dummy_tool" not in registry.tools
    assert "another_dummy_tool" in registry.tools


def test_get_available_plugins_basic():
    """get_available_plugins should return plugin information from registry."""
    # Set up config with some plugins
    config.enabled_plugins = {"enabled_tool"}
    config.disabled_plugins = {"disabled_tool"}
    
    # Register a tool to test registry integration
    registry.register_tool(DummyTool, source="code")
    
    plugins = config.get_available_plugins()
    
    # Should include the registered tool
    assert "dummy_tool" in plugins
    assert plugins["dummy_tool"]["enabled"] is True  # Not in disabled set
    
    # Should include configured plugins
    assert "enabled_tool" in plugins
    assert "disabled_tool" in plugins
    assert plugins["enabled_tool"]["enabled"] is True
    assert plugins["disabled_tool"]["enabled"] is False


def test_backward_compatibility():
    """Existing functionality should continue to work without plugin enable/disable settings."""
    cfg = PluginConfig()
    
    # Test that existing exclusion still works
    cfg.excluded_tool_names.add("excluded_tool")
    assert not cfg.should_register_tool_class("ExcludedTool", "excluded_tool", set())
    
    # Test that normal tools are still registered by default
    assert cfg.should_register_tool_class("NormalTool", "normal_tool", set())


def test_environment_variable_integration(monkeypatch):
    """All environment variables should work together correctly."""
    monkeypatch.setenv("MCP_PLUGIN_MODE", "blacklist")
    monkeypatch.setenv("MCP_ENABLED_PLUGINS", "tool_a, tool_b")
    monkeypatch.setenv("MCP_DISABLED_PLUGINS", "tool_c, tool_d")
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "tool_e")
    
    cfg = PluginConfig()
    
    assert cfg.plugin_enable_mode == "blacklist"
    assert cfg.enabled_plugins == {"tool_a", "tool_b"}
    assert cfg.disabled_plugins == {"tool_c", "tool_d"}
    assert cfg.excluded_tool_names == {"tool_e"}
    
    # Test plugin status
    assert cfg.is_plugin_enabled("tool_a")  # Explicitly enabled
    assert cfg.is_plugin_enabled("tool_b")  # Explicitly enabled
    assert not cfg.is_plugin_enabled("tool_c")  # Explicitly disabled
    assert not cfg.is_plugin_enabled("tool_d")  # Explicitly disabled
    assert cfg.is_plugin_enabled("tool_f")  # Not configured, should be enabled in blacklist mode
    
    # Test exclusion still works
    assert not cfg.should_register_tool_class("ToolE", "tool_e", set())


def test_plugin_registry_get_available_plugins():
    """Plugin registry should provide comprehensive plugin metadata."""
    # Reset config to default state
    config.plugin_enable_mode = "all"
    config.enabled_plugins = set()
    config.disabled_plugins = set()
    
    registry.clear()
    registry.register_tool(DummyTool, source="code")
    registry.register_tool(AnotherDummyTool, source="yaml")
    
    plugins = registry.get_available_plugins()
    
    assert "dummy_tool" in plugins
    assert "another_dummy_tool" in plugins
    
    dummy_metadata = plugins["dummy_tool"]
    assert dummy_metadata["name"] == "dummy_tool"
    assert dummy_metadata["class_name"] == "DummyTool"
    assert dummy_metadata["source"] == "code"
    assert dummy_metadata["registered"] is True
    
    another_metadata = plugins["another_dummy_tool"]
    assert another_metadata["source"] == "yaml"


def test_plugin_registry_get_enabled_disabled_plugins():
    """Plugin registry should correctly filter enabled and disabled plugins."""
    # Set up configuration
    config.plugin_enable_mode = "blacklist"
    config.disabled_plugins = {"dummy_tool"}
    config.enabled_plugins = set()
    
    registry.clear()
    registry.register_tool(DummyTool, source="code")
    registry.register_tool(AnotherDummyTool, source="code")
    
    enabled_plugins = registry.get_enabled_plugins()
    disabled_plugins = registry.get_disabled_plugins()
    
    assert "another_dummy_tool" in enabled_plugins
    assert "dummy_tool" in disabled_plugins
    assert "dummy_tool" not in enabled_plugins
    assert "another_dummy_tool" not in disabled_plugins
