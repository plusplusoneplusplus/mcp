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


# Tests for simplified ecosystem and OS configuration

def test_ecosystem_config_default():
    """Test default ecosystem configuration (all enabled)."""
    cfg = PluginConfig()
    assert cfg.enabled_ecosystems == set()
    assert cfg.is_ecosystem_enabled("microsoft")
    assert cfg.is_ecosystem_enabled("general")
    assert cfg.is_ecosystem_enabled(None)


def test_ecosystem_config_asterisk(monkeypatch):
    """Test ecosystem configuration with asterisk (all enabled)."""
    monkeypatch.setenv("MCP_ECOSYSTEMS", "*")
    cfg = PluginConfig()
    assert cfg.enabled_ecosystems == set()
    assert cfg.is_ecosystem_enabled("microsoft")
    assert cfg.is_ecosystem_enabled("general")
    assert cfg.is_ecosystem_enabled("unknown")


def test_ecosystem_config_specific_ecosystems(monkeypatch):
    """Test ecosystem configuration with specific ecosystems."""
    monkeypatch.setenv("MCP_ECOSYSTEMS", "microsoft,general")
    cfg = PluginConfig()
    assert cfg.enabled_ecosystems == {"microsoft", "general"}
    assert cfg.is_ecosystem_enabled("microsoft")
    assert cfg.is_ecosystem_enabled("general")
    assert not cfg.is_ecosystem_enabled("unknown")


def test_ecosystem_config_single_ecosystem(monkeypatch):
    """Test ecosystem configuration with single ecosystem."""
    monkeypatch.setenv("MCP_ECOSYSTEMS", "microsoft")
    cfg = PluginConfig()
    assert cfg.enabled_ecosystems == {"microsoft"}
    assert cfg.is_ecosystem_enabled("microsoft")
    assert not cfg.is_ecosystem_enabled("general")
    assert not cfg.is_ecosystem_enabled("unknown")


def test_ecosystem_config_case_insensitive(monkeypatch):
    """Test ecosystem configuration is case insensitive."""
    monkeypatch.setenv("MCP_ECOSYSTEMS", "Microsoft,GENERAL")
    cfg = PluginConfig()
    assert cfg.enabled_ecosystems == {"microsoft", "general"}
    assert cfg.is_ecosystem_enabled("Microsoft")
    assert cfg.is_ecosystem_enabled("MICROSOFT")
    assert cfg.is_ecosystem_enabled("general")
    assert cfg.is_ecosystem_enabled("GENERAL")


def test_ecosystem_config_whitespace_handling(monkeypatch):
    """Test ecosystem configuration handles whitespace correctly."""
    monkeypatch.setenv("MCP_ECOSYSTEMS", " microsoft , general , ")
    cfg = PluginConfig()
    assert cfg.enabled_ecosystems == {"microsoft", "general"}
    assert cfg.is_ecosystem_enabled("microsoft")
    assert cfg.is_ecosystem_enabled("general")


def test_ecosystem_config_empty_values(monkeypatch):
    """Test ecosystem configuration ignores empty values."""
    monkeypatch.setenv("MCP_ECOSYSTEMS", "microsoft,,general,")
    cfg = PluginConfig()
    assert cfg.enabled_ecosystems == {"microsoft", "general"}


def test_os_config_default(monkeypatch):
    """Test default OS configuration (auto-detected)."""
    # Mock the platform to get predictable results
    monkeypatch.setattr("platform.system", lambda: "Linux")
    cfg = PluginConfig()
    # With auto-detection, should detect "non-windows" for Linux
    assert cfg.enabled_os == {"non-windows"}
    assert not cfg.is_os_enabled("windows")
    assert cfg.is_os_enabled("non-windows")
    assert cfg.is_os_enabled("all")  # Tools with os_type="all" are always compatible
    assert cfg.is_os_enabled(None)  # None is always enabled for backward compatibility


def test_os_config_asterisk(monkeypatch):
    """Test OS configuration with asterisk (all enabled)."""
    monkeypatch.setenv("MCP_OS", "*")
    cfg = PluginConfig()
    assert cfg.enabled_os == set()
    assert cfg.is_os_enabled("windows")
    assert cfg.is_os_enabled("non-windows")
    assert cfg.is_os_enabled("all")


def test_os_config_specific_os(monkeypatch):
    """Test OS configuration with specific OS types."""
    monkeypatch.setenv("MCP_OS", "windows,non-windows")
    cfg = PluginConfig()
    assert cfg.enabled_os == {"windows", "non-windows"}
    assert cfg.is_os_enabled("windows")
    assert cfg.is_os_enabled("non-windows")
    assert cfg.is_os_enabled("all")  # Tools with os_type="all" are always compatible


def test_os_config_single_os(monkeypatch):
    """Test OS configuration with single OS."""
    monkeypatch.setenv("MCP_OS", "windows")
    cfg = PluginConfig()
    assert cfg.enabled_os == {"windows"}
    assert cfg.is_os_enabled("windows")
    assert not cfg.is_os_enabled("non-windows")
    assert cfg.is_os_enabled("all")  # Tools with os_type="all" are always compatible


def test_os_config_case_insensitive(monkeypatch):
    """Test OS configuration is case insensitive."""
    monkeypatch.setenv("MCP_OS", "Windows,NON-WINDOWS")
    cfg = PluginConfig()
    assert cfg.enabled_os == {"windows", "non-windows"}
    assert cfg.is_os_enabled("Windows")
    assert cfg.is_os_enabled("WINDOWS")
    assert cfg.is_os_enabled("non-windows")
    assert cfg.is_os_enabled("NON-WINDOWS")


def test_os_config_whitespace_handling(monkeypatch):
    """Test OS configuration handles whitespace correctly."""
    monkeypatch.setenv("MCP_OS", " windows , non-windows , ")
    cfg = PluginConfig()
    assert cfg.enabled_os == {"windows", "non-windows"}
    assert cfg.is_os_enabled("windows")
    assert cfg.is_os_enabled("non-windows")


def test_os_config_empty_values(monkeypatch):
    """Test OS configuration ignores empty values."""
    monkeypatch.setenv("MCP_OS", "windows,,non-windows,")
    cfg = PluginConfig()
    assert cfg.enabled_os == {"windows", "non-windows"}


def test_tool_registration_ecosystem_filtering(monkeypatch):
    """Test tool registration respects ecosystem filtering."""
    monkeypatch.setenv("MCP_ECOSYSTEMS", "microsoft")
    cfg = PluginConfig()

    # Microsoft ecosystem tools should be registered
    assert cfg.should_register_tool_class("TestTool", "test_tool", set(), ecosystem="microsoft")

    # General ecosystem tools should not be registered
    assert not cfg.should_register_tool_class("TestTool", "test_tool", set(), ecosystem="general")

    # Tools without ecosystem should be registered (backward compatibility)
    assert cfg.should_register_tool_class("TestTool", "test_tool", set(), ecosystem=None)


def test_tool_registration_os_filtering(monkeypatch):
    """Test tool registration respects OS filtering."""
    monkeypatch.setenv("MCP_OS", "windows")
    cfg = PluginConfig()

    # Windows tools should be registered
    assert cfg.should_register_tool_class("TestTool", "test_tool", set(), os_type="windows")

    # Non-windows tools should not be registered
    assert not cfg.should_register_tool_class("TestTool", "test_tool", set(), os_type="non-windows")

    # Tools without OS should be registered (backward compatibility)
    assert cfg.should_register_tool_class("TestTool", "test_tool", set(), os_type=None)


def test_tool_registration_combined_filtering(monkeypatch):
    """Test tool registration with both ecosystem and OS filtering."""
    monkeypatch.setenv("MCP_ECOSYSTEMS", "microsoft")
    monkeypatch.setenv("MCP_OS", "windows")
    cfg = PluginConfig()

    # Both ecosystem and OS match
    assert cfg.should_register_tool_class("TestTool", "test_tool", set(), ecosystem="microsoft", os_type="windows")

    # Ecosystem matches, OS doesn't
    assert not cfg.should_register_tool_class("TestTool", "test_tool", set(), ecosystem="microsoft", os_type="non-windows")

    # OS matches, ecosystem doesn't
    assert not cfg.should_register_tool_class("TestTool", "test_tool", set(), ecosystem="general", os_type="windows")

    # Neither matches
    assert not cfg.should_register_tool_class("TestTool", "test_tool", set(), ecosystem="general", os_type="non-windows")


def test_enable_disable_ecosystem():
    """Test enable/disable ecosystem methods."""
    cfg = PluginConfig()

    # Initially all ecosystems are enabled (empty set)
    assert cfg.enabled_ecosystems == set()
    assert cfg.is_ecosystem_enabled("microsoft")

    # Enable specific ecosystem
    cfg.enable_ecosystem("microsoft")
    assert cfg.enabled_ecosystems == {"microsoft"}
    assert cfg.is_ecosystem_enabled("microsoft")
    assert not cfg.is_ecosystem_enabled("general")

    # Enable another ecosystem
    cfg.enable_ecosystem("general")
    assert cfg.enabled_ecosystems == {"microsoft", "general"}
    assert cfg.is_ecosystem_enabled("microsoft")
    assert cfg.is_ecosystem_enabled("general")

    # Disable an ecosystem
    cfg.disable_ecosystem("microsoft")
    assert cfg.enabled_ecosystems == {"general"}
    assert not cfg.is_ecosystem_enabled("microsoft")
    assert cfg.is_ecosystem_enabled("general")


def test_enable_disable_os(monkeypatch):
    """Test enable/disable OS methods."""
    # Mock the platform to get predictable results
    monkeypatch.setattr("platform.system", lambda: "Linux")
    cfg = PluginConfig()

    # Initially OS is auto-detected (non-windows for Linux)
    assert cfg.enabled_os == {"non-windows"}
    assert cfg.is_os_enabled("non-windows")

    # Enable specific OS
    cfg.enable_os("windows")
    assert cfg.enabled_os == {"non-windows", "windows"}
    assert cfg.is_os_enabled("windows")
    assert cfg.is_os_enabled("non-windows")

    # Disable an OS
    cfg.disable_os("windows")
    assert cfg.enabled_os == {"non-windows"}
    assert not cfg.is_os_enabled("windows")
    assert cfg.is_os_enabled("non-windows")


def test_backward_compatibility_ecosystem_os():
    """Test that tools without ecosystem/OS metadata are always enabled."""
    cfg = PluginConfig()

    # Enable only specific ecosystem and OS
    cfg.enabled_ecosystems = {"microsoft"}
    cfg.enabled_os = {"windows"}

    # Tool without ecosystem/OS should still be enabled
    assert cfg.should_register_tool_class("Tool", "test_tool", set(), ecosystem=None, os_type=None)

    # Tool with matching ecosystem but no OS should be enabled
    assert cfg.should_register_tool_class("Tool", "test_tool", set(), ecosystem="microsoft", os_type=None)

    # Tool with matching OS but no ecosystem should be enabled
    assert cfg.should_register_tool_class("Tool", "test_tool", set(), ecosystem=None, os_type="windows")


# OS Auto-Detection Tests

def test_detect_current_os_windows(monkeypatch):
    """Test OS detection for Windows platform."""
    monkeypatch.setattr("platform.system", lambda: "Windows")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "windows"


def test_detect_current_os_darwin(monkeypatch):
    """Test OS detection for Darwin/macOS platform."""
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "non-windows"


def test_detect_current_os_linux(monkeypatch):
    """Test OS detection for Linux platform."""
    monkeypatch.setattr("platform.system", lambda: "Linux")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "non-windows"


def test_detect_current_os_unknown(monkeypatch):
    """Test OS detection for unknown platform."""
    monkeypatch.setattr("platform.system", lambda: "FreeBSD")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "*"


def test_detect_current_os_case_insensitive(monkeypatch):
    """Test OS detection is case-insensitive."""
    monkeypatch.setattr("platform.system", lambda: "WINDOWS")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "windows"

    monkeypatch.setattr("platform.system", lambda: "darwin")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "non-windows"


def test_os_auto_detection_when_env_empty(monkeypatch):
    """Test that OS is auto-detected when MCP_OS is empty."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "Darwin")

    cfg = PluginConfig()
    assert cfg.enabled_os == {"non-windows"}


def test_os_auto_detection_when_env_unset(monkeypatch):
    """Test that OS is auto-detected when MCP_OS is not set."""
    monkeypatch.delenv("MCP_OS", raising=False)
    monkeypatch.setattr("platform.system", lambda: "Windows")

    cfg = PluginConfig()
    assert cfg.enabled_os == {"windows"}


def test_os_auto_detection_when_env_whitespace(monkeypatch):
    """Test that OS is auto-detected when MCP_OS contains only whitespace."""
    monkeypatch.setenv("MCP_OS", "   ")
    monkeypatch.setattr("platform.system", lambda: "Linux")

    cfg = PluginConfig()
    assert cfg.enabled_os == {"non-windows"}


def test_os_auto_detection_fallback_to_all(monkeypatch):
    """Test that auto-detection falls back to all OS types for unknown platforms."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "UnknownOS")

    cfg = PluginConfig()
    assert cfg.enabled_os == set()  # Empty set means all enabled


def test_os_explicit_config_overrides_auto_detection(monkeypatch):
    """Test that explicit MCP_OS configuration overrides auto-detection."""
    monkeypatch.setenv("MCP_OS", "windows")
    monkeypatch.setattr("platform.system", lambda: "Darwin")  # Different from config

    cfg = PluginConfig()
    assert cfg.enabled_os == {"windows"}  # Should use explicit config, not auto-detected


def test_os_asterisk_config_overrides_auto_detection(monkeypatch):
    """Test that MCP_OS=* overrides auto-detection."""
    monkeypatch.setenv("MCP_OS", "*")
    monkeypatch.setattr("platform.system", lambda: "Windows")

    cfg = PluginConfig()
    assert cfg.enabled_os == set()  # Empty set means all enabled


def test_os_auto_detection_logging(monkeypatch, caplog):
    """Test that auto-detection logs the detected OS."""
    import logging

    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "Darwin")

    with caplog.at_level(logging.INFO):
        cfg = PluginConfig()

    assert "Auto-detected OS: non-windows" in caplog.text


def test_os_auto_detection_unknown_platform_warning(monkeypatch, caplog):
    """Test that unknown platforms generate a warning during auto-detection."""
    import logging

    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "WeirdOS")

    with caplog.at_level(logging.WARNING):
        cfg = PluginConfig()

    assert "Unknown platform 'weirdos', defaulting to all OS types" in caplog.text


def test_tool_registration_with_auto_detected_os_windows(monkeypatch):
    """Test tool registration filtering with auto-detected Windows OS."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "Windows")

    cfg = PluginConfig()

    # Windows-specific tool should be registered
    assert cfg.should_register_tool_class("WindowsTool", "windows_tool", set(), os_type="windows")

    # Non-Windows tool should not be registered
    assert not cfg.should_register_tool_class("LinuxTool", "linux_tool", set(), os_type="non-windows")

    # Tool without OS specification should be registered
    assert cfg.should_register_tool_class("GenericTool", "generic_tool", set(), os_type=None)


def test_tool_registration_with_auto_detected_os_macos(monkeypatch):
    """Test tool registration filtering with auto-detected macOS."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "Darwin")

    cfg = PluginConfig()

    # Non-Windows tool should be registered
    assert cfg.should_register_tool_class("MacOSTool", "macos_tool", set(), os_type="non-windows")

    # Windows tool should not be registered
    assert not cfg.should_register_tool_class("WindowsTool", "windows_tool", set(), os_type="windows")

    # Tool without OS specification should be registered
    assert cfg.should_register_tool_class("GenericTool", "generic_tool", set(), os_type=None)


def test_tool_registration_with_auto_detected_os_linux(monkeypatch):
    """Test tool registration filtering with auto-detected Linux."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "Linux")

    cfg = PluginConfig()

    # Non-Windows tool should be registered
    assert cfg.should_register_tool_class("LinuxTool", "linux_tool", set(), os_type="non-windows")

    # Windows tool should not be registered
    assert not cfg.should_register_tool_class("WindowsTool", "windows_tool", set(), os_type="windows")

    # Tool without OS specification should be registered
    assert cfg.should_register_tool_class("GenericTool", "generic_tool", set(), os_type=None)


def test_tool_registration_with_auto_detected_unknown_os(monkeypatch):
    """Test tool registration filtering with auto-detected unknown OS (fallback to all)."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "FreeBSD")

    cfg = PluginConfig()

    # All tools should be registered when OS detection falls back to "*"
    assert cfg.should_register_tool_class("WindowsTool", "windows_tool", set(), os_type="windows")
    assert cfg.should_register_tool_class("LinuxTool", "linux_tool", set(), os_type="non-windows")
    assert cfg.should_register_tool_class("GenericTool", "generic_tool", set(), os_type=None)


def test_os_auto_detection_integration_with_ecosystem_filtering(monkeypatch):
    """Test that OS auto-detection works correctly with ecosystem filtering."""
    monkeypatch.setenv("MCP_OS", "")  # Enable auto-detection
    monkeypatch.setenv("MCP_ECOSYSTEMS", "microsoft")  # Only Microsoft ecosystem
    monkeypatch.setattr("platform.system", lambda: "Windows")

    cfg = PluginConfig()

    # Tool with matching ecosystem and auto-detected OS should be registered
    assert cfg.should_register_tool_class(
        "MSWindowsTool", "ms_windows_tool", set(),
        ecosystem="microsoft", os_type="windows"
    )

    # Tool with matching ecosystem but wrong OS should not be registered
    assert not cfg.should_register_tool_class(
        "MSLinuxTool", "ms_linux_tool", set(),
        ecosystem="microsoft", os_type="non-windows"
    )

    # Tool with wrong ecosystem should not be registered regardless of OS
    assert not cfg.should_register_tool_class(
        "GeneralWindowsTool", "general_windows_tool", set(),
        ecosystem="general", os_type="windows"
    )


# OS Auto-Detection Tests

def test_detect_current_os_windows(monkeypatch):
    """Test OS detection for Windows platform."""
    monkeypatch.setattr("platform.system", lambda: "Windows")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "windows"


def test_detect_current_os_darwin(monkeypatch):
    """Test OS detection for Darwin/macOS platform."""
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "non-windows"


def test_detect_current_os_linux(monkeypatch):
    """Test OS detection for Linux platform."""
    monkeypatch.setattr("platform.system", lambda: "Linux")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "non-windows"


def test_detect_current_os_unknown(monkeypatch):
    """Test OS detection for unknown platform."""
    monkeypatch.setattr("platform.system", lambda: "FreeBSD")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "*"


def test_detect_current_os_case_insensitive(monkeypatch):
    """Test OS detection is case-insensitive."""
    monkeypatch.setattr("platform.system", lambda: "WINDOWS")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "windows"

    monkeypatch.setattr("platform.system", lambda: "darwin")
    cfg = PluginConfig()
    assert cfg._detect_current_os() == "non-windows"


def test_os_auto_detection_when_env_empty(monkeypatch):
    """Test that OS is auto-detected when MCP_OS is empty."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "Darwin")

    cfg = PluginConfig()
    assert cfg.enabled_os == {"non-windows"}


def test_os_auto_detection_when_env_unset(monkeypatch):
    """Test that OS is auto-detected when MCP_OS is not set."""
    monkeypatch.delenv("MCP_OS", raising=False)
    monkeypatch.setattr("platform.system", lambda: "Windows")

    cfg = PluginConfig()
    assert cfg.enabled_os == {"windows"}


def test_os_auto_detection_when_env_whitespace(monkeypatch):
    """Test that OS is auto-detected when MCP_OS contains only whitespace."""
    monkeypatch.setenv("MCP_OS", "   ")
    monkeypatch.setattr("platform.system", lambda: "Linux")

    cfg = PluginConfig()
    assert cfg.enabled_os == {"non-windows"}


def test_os_auto_detection_fallback_to_all(monkeypatch):
    """Test that auto-detection falls back to all OS types for unknown platforms."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "UnknownOS")

    cfg = PluginConfig()
    assert cfg.enabled_os == set()  # Empty set means all enabled


def test_os_explicit_config_overrides_auto_detection(monkeypatch):
    """Test that explicit MCP_OS configuration overrides auto-detection."""
    monkeypatch.setenv("MCP_OS", "windows")
    monkeypatch.setattr("platform.system", lambda: "Darwin")  # Different from config

    cfg = PluginConfig()
    assert cfg.enabled_os == {"windows"}  # Should use explicit config, not auto-detected


def test_os_asterisk_config_overrides_auto_detection(monkeypatch):
    """Test that MCP_OS=* overrides auto-detection."""
    monkeypatch.setenv("MCP_OS", "*")
    monkeypatch.setattr("platform.system", lambda: "Windows")

    cfg = PluginConfig()
    assert cfg.enabled_os == set()  # Empty set means all enabled


def test_os_auto_detection_logging(monkeypatch, caplog):
    """Test that auto-detection logs the detected OS."""
    import logging

    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "Darwin")

    with caplog.at_level(logging.INFO):
        cfg = PluginConfig()

    assert "Auto-detected OS: non-windows" in caplog.text


def test_os_auto_detection_unknown_platform_warning(monkeypatch, caplog):
    """Test that unknown platforms generate a warning during auto-detection."""
    import logging

    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "WeirdOS")

    with caplog.at_level(logging.WARNING):
        cfg = PluginConfig()

    assert "Unknown platform 'weirdos', defaulting to all OS types" in caplog.text


def test_tool_registration_with_auto_detected_os_windows(monkeypatch):
    """Test tool registration filtering with auto-detected Windows OS."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "Windows")

    cfg = PluginConfig()

    # Windows-specific tool should be registered
    assert cfg.should_register_tool_class("WindowsTool", "windows_tool", set(), os_type="windows")

    # Non-Windows tool should not be registered
    assert not cfg.should_register_tool_class("LinuxTool", "linux_tool", set(), os_type="non-windows")

    # Tool without OS specification should be registered
    assert cfg.should_register_tool_class("GenericTool", "generic_tool", set(), os_type=None)


def test_tool_registration_with_auto_detected_os_macos(monkeypatch):
    """Test tool registration filtering with auto-detected macOS."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "Darwin")

    cfg = PluginConfig()

    # Non-Windows tool should be registered
    assert cfg.should_register_tool_class("MacOSTool", "macos_tool", set(), os_type="non-windows")

    # Windows tool should not be registered
    assert not cfg.should_register_tool_class("WindowsTool", "windows_tool", set(), os_type="windows")

    # Tool without OS specification should be registered
    assert cfg.should_register_tool_class("GenericTool", "generic_tool", set(), os_type=None)


def test_tool_registration_with_auto_detected_os_linux(monkeypatch):
    """Test tool registration filtering with auto-detected Linux."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "Linux")

    cfg = PluginConfig()

    # Non-Windows tool should be registered
    assert cfg.should_register_tool_class("LinuxTool", "linux_tool", set(), os_type="non-windows")

    # Windows tool should not be registered
    assert not cfg.should_register_tool_class("WindowsTool", "windows_tool", set(), os_type="windows")

    # Tool without OS specification should be registered
    assert cfg.should_register_tool_class("GenericTool", "generic_tool", set(), os_type=None)


def test_tool_registration_with_auto_detected_unknown_os(monkeypatch):
    """Test tool registration filtering with auto-detected unknown OS (fallback to all)."""
    monkeypatch.setenv("MCP_OS", "")
    monkeypatch.setattr("platform.system", lambda: "FreeBSD")

    cfg = PluginConfig()

    # All tools should be registered when OS detection falls back to "*"
    assert cfg.should_register_tool_class("WindowsTool", "windows_tool", set(), os_type="windows")
    assert cfg.should_register_tool_class("LinuxTool", "linux_tool", set(), os_type="non-windows")
    assert cfg.should_register_tool_class("GenericTool", "generic_tool", set(), os_type=None)


def test_os_auto_detection_integration_with_ecosystem_filtering(monkeypatch):
    """Test that OS auto-detection works correctly with ecosystem filtering."""
    monkeypatch.setenv("MCP_OS", "")  # Enable auto-detection
    monkeypatch.setenv("MCP_ECOSYSTEMS", "microsoft")  # Only Microsoft ecosystem
    monkeypatch.setattr("platform.system", lambda: "Windows")

    cfg = PluginConfig()

    # Tool with matching ecosystem and auto-detected OS should be registered
    assert cfg.should_register_tool_class(
        "MSWindowsTool", "ms_windows_tool", set(),
        ecosystem="microsoft", os_type="windows"
    )

    # Tool with matching ecosystem but wrong OS should not be registered
    assert not cfg.should_register_tool_class(
        "MSLinuxTool", "ms_linux_tool", set(),
        ecosystem="microsoft", os_type="non-windows"
    )

    # Tool with wrong ecosystem should not be registered regardless of OS
    assert not cfg.should_register_tool_class(
        "GeneralWindowsTool", "general_windows_tool", set(),
        ecosystem="general", os_type="windows"
    )
