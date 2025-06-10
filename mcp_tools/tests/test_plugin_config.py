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


class CaseSensitiveTool(ToolInterface):
    """Tool for testing case sensitivity."""

    @property
    def name(self) -> str:
        return "CaseSensitive_Tool"

    @property
    def description(self) -> str:
        return "Tool for case sensitivity testing"

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


# Additional comprehensive tests for MCP_EXCLUDED_TOOL_NAMES

def test_excluded_tool_names_empty_string(monkeypatch):
    """Empty MCP_EXCLUDED_TOOL_NAMES should not exclude any tools."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "")
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == set()
    assert cfg.should_register_tool_class("DummyTool", "dummy_tool", set())


def test_excluded_tool_names_whitespace_only(monkeypatch):
    """MCP_EXCLUDED_TOOL_NAMES with only whitespace should not exclude any tools."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "   ")
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == set()
    assert cfg.should_register_tool_class("DummyTool", "dummy_tool", set())


def test_excluded_tool_names_empty_comma_separated(monkeypatch):
    """Empty values in comma-separated list should be ignored."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "tool_a,,tool_b, ,tool_c")
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == {"tool_a", "tool_b", "tool_c"}


def test_excluded_tool_names_single_comma(monkeypatch):
    """Single comma should not create empty exclusions."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", ",")
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == set()


def test_excluded_tool_names_trailing_comma(monkeypatch):
    """Trailing comma should not create empty exclusions."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "tool_a,tool_b,")
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == {"tool_a", "tool_b"}


def test_excluded_tool_names_leading_comma(monkeypatch):
    """Leading comma should not create empty exclusions."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", ",tool_a,tool_b")
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == {"tool_a", "tool_b"}


def test_excluded_tool_names_case_sensitivity(monkeypatch):
    """Tool exclusion should be case-sensitive."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "CaseSensitive_Tool")
    cfg = PluginConfig()
    
    # Exact match should be excluded
    assert not cfg.should_register_tool_class("CaseSensitiveTool", "CaseSensitive_Tool", set())
    
    # Different case should not be excluded
    assert cfg.should_register_tool_class("CaseSensitiveTool", "casesensitive_tool", set())
    assert cfg.should_register_tool_class("CaseSensitiveTool", "CASESENSITIVE_TOOL", set())


def test_excluded_tool_names_non_existent_tools(monkeypatch):
    """Excluding non-existent tools should not cause errors."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "non_existent_tool,another_fake_tool")
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == {"non_existent_tool", "another_fake_tool"}
    
    # Real tools should still work normally
    assert cfg.should_register_tool_class("DummyTool", "dummy_tool", set())


def test_excluded_tool_names_special_characters(monkeypatch):
    """Tool names with special characters should be handled correctly."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "tool-with-dashes,tool_with_underscores,tool.with.dots")
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == {"tool-with-dashes", "tool_with_underscores", "tool.with.dots"}


def test_excluded_tool_names_unicode_characters(monkeypatch):
    """Tool names with unicode characters should be handled correctly."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "tool_with_émojis,tool_with_中文")
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == {"tool_with_émojis", "tool_with_中文"}


def test_excluded_tool_names_very_long_list(monkeypatch):
    """Very long lists of excluded tools should be handled correctly."""
    # Create a list of 100 tool names
    tool_names = [f"tool_{i}" for i in range(100)]
    excluded_tools_str = ",".join(tool_names)
    
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", excluded_tools_str)
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == set(tool_names)
    assert len(cfg.excluded_tool_names) == 100


def test_excluded_tool_names_integration_multiple_tools(monkeypatch):
    """Multiple tools should be properly excluded from registry."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "dummy_tool,another_dummy_tool")
    config._load_from_env()
    registry.clear()
    
    # Try to register both tools
    result1 = registry.register_tool(DummyTool, source="code")
    result2 = registry.register_tool(AnotherDummyTool, source="code")
    
    # Both should be excluded
    assert result1 is None
    assert result2 is None
    assert "dummy_tool" not in registry.tools
    assert "another_dummy_tool" not in registry.tools


def test_excluded_tool_names_integration_partial_exclusion(monkeypatch):
    """Only specified tools should be excluded, others should be registered."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "dummy_tool")
    config._load_from_env()
    registry.clear()
    
    # Try to register both tools
    result1 = registry.register_tool(DummyTool, source="code")
    result2 = registry.register_tool(AnotherDummyTool, source="code")
    
    # Only dummy_tool should be excluded
    assert result1 is None
    assert result2 is not None
    assert "dummy_tool" not in registry.tools
    assert "another_dummy_tool" in registry.tools


def test_excluded_tool_names_with_yaml_tools(monkeypatch):
    """Exclusion should work with YAML tools as well."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "dummy_tool")
    cfg = PluginConfig()
    
    # Test with YAML tools set (simulating YAML override scenario)
    yaml_tools = {"dummy_tool", "other_yaml_tool"}
    
    # Tool should be excluded regardless of YAML presence
    assert not cfg.should_register_tool_class("DummyTool", "dummy_tool", yaml_tools)
    
    # Other tools should work normally
    assert cfg.should_register_tool_class("AnotherTool", "other_tool", yaml_tools)


def test_excluded_tool_names_precedence_over_yaml_override(monkeypatch):
    """Exclusion should take precedence over YAML override logic."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "dummy_tool")
    cfg = PluginConfig()
    cfg.yaml_overrides_code = True
    
    yaml_tools = {"dummy_tool"}  # Tool exists in YAML
    
    # Tool should be excluded even though YAML override would normally apply
    assert not cfg.should_register_tool_class("DummyTool", "dummy_tool", yaml_tools)


def test_excluded_tool_names_with_base_class_exclusion(monkeypatch):
    """Tool exclusion should work alongside base class exclusion."""
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "dummy_tool")
    monkeypatch.setenv("MCP_EXCLUDED_BASE_CLASSES", "AnotherDummyTool")
    cfg = PluginConfig()
    
    # Both exclusion mechanisms should work
    assert not cfg.should_register_tool_class("DummyTool", "dummy_tool", set())  # Excluded by name
    assert not cfg.should_register_tool_class("AnotherDummyTool", "another_tool", set())  # Excluded by class


def test_excluded_tool_names_environment_reload(monkeypatch):
    """Configuration should properly reload when environment changes."""
    # Start with no exclusions
    cfg = PluginConfig()
    assert cfg.excluded_tool_names == set()
    
    # Set exclusions and reload
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "dummy_tool")
    cfg._load_from_env()
    assert cfg.excluded_tool_names == {"dummy_tool"}
    
    # Change exclusions and reload again (need to clear first since _load_from_env updates)
    cfg.excluded_tool_names.clear()  # Clear existing exclusions
    monkeypatch.setenv("MCP_EXCLUDED_TOOL_NAMES", "another_tool,third_tool")
    cfg._load_from_env()
    assert cfg.excluded_tool_names == {"another_tool", "third_tool"}


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
