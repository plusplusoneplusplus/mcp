"""Comprehensive tests for the tool-level enabled flag functionality."""

import pytest
from unittest.mock import patch

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import registry, register_tool
from mcp_tools.dependency import injector
from mcp_tools.plugin_config import config


# Mock tool classes for testing
class MockEnabledTool(ToolInterface):
    """Mock tool that is enabled by default."""

    @property
    def name(self) -> str:
        return "mock_enabled_tool"

    @property
    def description(self) -> str:
        return "A mock tool that is enabled"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True, "message": "Enabled tool executed"}


class MockDisabledTool(ToolInterface):
    """Mock tool that is disabled."""

    @property
    def name(self) -> str:
        return "mock_disabled_tool"

    @property
    def description(self) -> str:
        return "A mock tool that is disabled"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True, "message": "Disabled tool executed"}


@pytest.fixture
def clean_registry():
    """Fixture to provide a clean registry for each test."""
    # Save the original registry state
    original_tools = registry.tools.copy()
    original_instances = registry.instances.copy()
    original_yaml_tool_names = registry.yaml_tool_names.copy()
    original_tool_sources = registry.tool_sources.copy()
    original_tool_ecosystems = registry.tool_ecosystems.copy()
    original_tool_os = registry.tool_os.copy()
    original_tool_enabled = registry.tool_enabled.copy()

    # Clear the registry
    registry.clear()

    yield registry

    # Restore the original registry state
    registry.tools = original_tools
    registry.instances = original_instances
    registry.yaml_tool_names = original_yaml_tool_names
    registry.tool_sources = original_tool_sources
    registry.tool_ecosystems = original_tool_ecosystems
    registry.tool_os = original_tool_os
    registry.tool_enabled = original_tool_enabled


@pytest.fixture
def clean_injector():
    """Fixture to provide a clean injector for each test."""
    # Save the original injector state
    original_dependencies = injector.dependencies.copy()
    original_tool_constructors = injector.tool_constructors.copy()
    original_instances = injector.instances.copy()

    # Clear the injector
    injector.clear()

    yield injector

    # Restore the original injector state
    injector.dependencies = original_dependencies
    injector.tool_constructors = original_tool_constructors
    injector.instances = original_instances


@pytest.fixture
def mock_config():
    """Fixture to provide a clean configuration for each test."""
    # Save original config state
    original_register_code_tools = config.register_code_tools
    original_register_yaml_tools = config.register_yaml_tools
    original_yaml_overrides_code = config.yaml_overrides_code

    # Reset to defaults for testing
    config.register_code_tools = True
    config.register_yaml_tools = True
    config.yaml_overrides_code = False

    yield config

    # Restore original config
    config.register_code_tools = original_register_code_tools
    config.register_yaml_tools = original_register_yaml_tools
    config.yaml_overrides_code = original_yaml_overrides_code


def test_register_tool_with_enabled_true(clean_registry):
    """Test registering a tool with enabled=True (default)."""
    # Register tool with enabled=True (explicit)
    clean_registry.register_tool(MockEnabledTool, source="code", enabled=True)

    # Check if tool is registered
    assert "mock_enabled_tool" in clean_registry.tools

    # Check enabled state
    tool_enabled = clean_registry.get_tool_enabled()
    assert "mock_enabled_tool" in tool_enabled
    assert tool_enabled["mock_enabled_tool"] is True


def test_register_tool_with_enabled_false(clean_registry):
    """Test registering a tool with enabled=False."""
    # Register tool with enabled=False
    clean_registry.register_tool(MockDisabledTool, source="code", enabled=False)

    # Check if tool is registered
    assert "mock_disabled_tool" in clean_registry.tools

    # Check enabled state
    tool_enabled = clean_registry.get_tool_enabled()
    assert "mock_disabled_tool" in tool_enabled
    assert tool_enabled["mock_disabled_tool"] is False


def test_register_tool_default_enabled(clean_registry):
    """Test that tools are enabled by default when enabled parameter is not specified."""
    # Register tool without specifying enabled parameter
    clean_registry.register_tool(MockEnabledTool, source="code")

    # Check enabled state (should default to True)
    tool_enabled = clean_registry.get_tool_enabled()
    assert tool_enabled["mock_enabled_tool"] is True


def test_decorator_with_enabled_true(clean_registry):
    """Test using the @register_tool decorator with enabled=True."""

    @register_tool(enabled=True)
    class DecoratedEnabledTool(ToolInterface):
        @property
        def name(self) -> str:
            return "decorated_enabled_tool"

        @property
        def description(self) -> str:
            return "A decorated enabled tool"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    # Check if tool is registered
    assert "decorated_enabled_tool" in clean_registry.tools

    # Check enabled state
    tool_enabled = clean_registry.get_tool_enabled()
    assert tool_enabled["decorated_enabled_tool"] is True

    # Check class metadata
    assert hasattr(DecoratedEnabledTool, "_mcp_enabled")
    assert DecoratedEnabledTool._mcp_enabled is True


def test_decorator_with_enabled_false(clean_registry):
    """Test using the @register_tool decorator with enabled=False."""

    @register_tool(enabled=False)
    class DecoratedDisabledTool(ToolInterface):
        @property
        def name(self) -> str:
            return "decorated_disabled_tool"

        @property
        def description(self) -> str:
            return "A decorated disabled tool"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    # Check if tool is registered
    assert "decorated_disabled_tool" in clean_registry.tools

    # Check enabled state
    tool_enabled = clean_registry.get_tool_enabled()
    assert tool_enabled["decorated_disabled_tool"] is False

    # Check class metadata
    assert hasattr(DecoratedDisabledTool, "_mcp_enabled")
    assert DecoratedDisabledTool._mcp_enabled is False


def test_decorator_default_enabled(clean_registry):
    """Test that @register_tool decorator defaults to enabled=True."""

    @register_tool
    class DecoratedDefaultTool(ToolInterface):
        @property
        def name(self) -> str:
            return "decorated_default_tool"

        @property
        def description(self) -> str:
            return "A decorated tool with default enabled"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    # Check enabled state (should default to True)
    tool_enabled = clean_registry.get_tool_enabled()
    assert tool_enabled["decorated_default_tool"] is True


def test_filtered_instances_excludes_disabled_tools(
    clean_registry, clean_injector, mock_config
):
    """Test that get_filtered_instances excludes disabled tools."""
    # Register both enabled and disabled tools
    clean_registry.register_tool(MockEnabledTool, source="code", enabled=True)
    clean_registry.register_tool(MockDisabledTool, source="code", enabled=False)

    # Create instances
    clean_registry._simple_get_tool_instance("mock_enabled_tool")
    clean_registry._simple_get_tool_instance("mock_disabled_tool")

    # Copy instances to injector
    clean_injector.instances = clean_registry.instances.copy()

    # Get filtered instances
    filtered_instances = clean_injector.get_filtered_instances()

    # Check that only enabled tool is in filtered instances
    assert "mock_enabled_tool" in filtered_instances
    assert "mock_disabled_tool" not in filtered_instances


def test_filtered_instances_with_multiple_disabled_tools(
    clean_registry, clean_injector, mock_config
):
    """Test filtering with multiple disabled tools."""

    # Create additional mock tools
    class MockTool1(ToolInterface):
        @property
        def name(self) -> str:
            return "mock_tool_1"

        @property
        def description(self) -> str:
            return "Mock tool 1"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    class MockTool2(ToolInterface):
        @property
        def name(self) -> str:
            return "mock_tool_2"

        @property
        def description(self) -> str:
            return "Mock tool 2"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    class MockTool3(ToolInterface):
        @property
        def name(self) -> str:
            return "mock_tool_3"

        @property
        def description(self) -> str:
            return "Mock tool 3"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    # Register tools with different enabled states
    clean_registry.register_tool(MockTool1, source="code", enabled=True)
    clean_registry.register_tool(MockTool2, source="code", enabled=False)
    clean_registry.register_tool(MockTool3, source="code", enabled=True)

    # Create instances
    clean_registry._simple_get_tool_instance("mock_tool_1")
    clean_registry._simple_get_tool_instance("mock_tool_2")
    clean_registry._simple_get_tool_instance("mock_tool_3")

    # Copy instances to injector
    clean_injector.instances = clean_registry.instances.copy()

    # Get filtered instances
    filtered_instances = clean_injector.get_filtered_instances()

    # Check that only enabled tools are in filtered instances
    assert "mock_tool_1" in filtered_instances
    assert "mock_tool_2" not in filtered_instances
    assert "mock_tool_3" in filtered_instances
    assert len(filtered_instances) == 2


def test_enabled_flag_with_other_metadata(clean_registry):
    """Test that enabled flag works correctly with other metadata (ecosystem, os_type)."""

    @register_tool(
        source="code", ecosystem="test-ecosystem", os_type="all", enabled=False
    )
    class ComplexTool(ToolInterface):
        @property
        def name(self) -> str:
            return "complex_tool"

        @property
        def description(self) -> str:
            return "A tool with multiple metadata fields"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    # Check all metadata
    assert "complex_tool" in clean_registry.tools

    tool_sources = clean_registry.get_tool_sources()
    assert tool_sources["complex_tool"] == "code"

    tool_ecosystems = clean_registry.get_tool_ecosystems()
    assert tool_ecosystems["complex_tool"] == "test-ecosystem"

    tool_os = clean_registry.get_tool_os()
    assert tool_os["complex_tool"] == "all"

    tool_enabled = clean_registry.get_tool_enabled()
    assert tool_enabled["complex_tool"] is False

    # Check class metadata
    assert ComplexTool._mcp_source == "code"
    assert ComplexTool._mcp_ecosystem == "test-ecosystem"
    assert ComplexTool._mcp_os == "all"
    assert ComplexTool._mcp_enabled is False


def test_get_tool_enabled_returns_copy(clean_registry):
    """Test that get_tool_enabled returns a copy and not a reference."""
    clean_registry.register_tool(MockEnabledTool, source="code", enabled=True)

    # Get the enabled dict
    tool_enabled_1 = clean_registry.get_tool_enabled()

    # Modify the returned dict
    tool_enabled_1["mock_enabled_tool"] = False

    # Get the enabled dict again
    tool_enabled_2 = clean_registry.get_tool_enabled()

    # Check that the original is not modified
    assert tool_enabled_2["mock_enabled_tool"] is True


def test_clear_registry_clears_enabled_state(clean_registry):
    """Test that clearing the registry also clears the enabled state."""
    clean_registry.register_tool(MockEnabledTool, source="code", enabled=True)
    clean_registry.register_tool(MockDisabledTool, source="code", enabled=False)

    # Check that tools are registered
    assert len(clean_registry.tools) == 2
    assert len(clean_registry.get_tool_enabled()) == 2

    # Clear the registry
    clean_registry.clear()

    # Check that enabled state is cleared
    assert len(clean_registry.get_tool_enabled()) == 0
    assert len(clean_registry.tools) == 0


def test_disabled_tool_not_in_list_tools(clean_registry, clean_injector, mock_config):
    """Test that disabled tools don't appear in list_tools (simulated)."""
    # Register enabled and disabled tools
    clean_registry.register_tool(MockEnabledTool, source="code", enabled=True)
    clean_registry.register_tool(MockDisabledTool, source="code", enabled=False)

    # Create instances
    clean_registry._simple_get_tool_instance("mock_enabled_tool")
    clean_registry._simple_get_tool_instance("mock_disabled_tool")

    # Copy instances to injector
    clean_injector.instances = clean_registry.instances.copy()

    # Simulate what list_tools does
    tool_instances = list(clean_injector.get_filtered_instances().values())

    # Check that only enabled tool is returned
    assert len(tool_instances) == 1
    assert tool_instances[0].name == "mock_enabled_tool"


@pytest.mark.parametrize(
    "enabled_state,should_be_filtered",
    [
        (True, True),  # Enabled tools should be included
        (False, False),  # Disabled tools should be excluded
    ],
)
def test_parametrized_enabled_filtering(
    clean_registry, clean_injector, mock_config, enabled_state, should_be_filtered
):
    """Parametrized test for enabled flag filtering."""

    class ParametrizedTool(ToolInterface):
        @property
        def name(self) -> str:
            return "parametrized_tool"

        @property
        def description(self) -> str:
            return "A parametrized test tool"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    # Register tool with specified enabled state
    clean_registry.register_tool(ParametrizedTool, source="code", enabled=enabled_state)

    # Create instance
    clean_registry._simple_get_tool_instance("parametrized_tool")

    # Copy instances to injector
    clean_injector.instances = clean_registry.instances.copy()

    # Get filtered instances
    filtered_instances = clean_injector.get_filtered_instances()

    # Check if tool is filtered correctly
    if should_be_filtered:
        assert "parametrized_tool" in filtered_instances
    else:
        assert "parametrized_tool" not in filtered_instances


def test_enabled_flag_with_source_filtering(
    clean_registry, clean_injector, mock_config
):
    """Test that enabled flag works in combination with source filtering."""

    class CodeTool(ToolInterface):
        @property
        def name(self) -> str:
            return "code_tool"

        @property
        def description(self) -> str:
            return "A code tool"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    class YamlTool(ToolInterface):
        @property
        def name(self) -> str:
            return "yaml_tool"

        @property
        def description(self) -> str:
            return "A YAML tool"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    # Register tools with different sources and enabled states
    clean_registry.register_tool(CodeTool, source="code", enabled=True)
    clean_registry.register_tool(YamlTool, source="yaml", enabled=False)

    # Create instances
    clean_registry._simple_get_tool_instance("code_tool")
    clean_registry._simple_get_tool_instance("yaml_tool")

    # Copy instances to injector
    clean_injector.instances = clean_registry.instances.copy()

    # Test with both sources enabled
    mock_config.register_code_tools = True
    mock_config.register_yaml_tools = True
    filtered = clean_injector.get_filtered_instances()
    assert "code_tool" in filtered
    assert "yaml_tool" not in filtered  # Disabled by enabled flag

    # Test with only code enabled
    mock_config.register_code_tools = True
    mock_config.register_yaml_tools = False
    filtered = clean_injector.get_filtered_instances()
    assert "code_tool" in filtered
    assert "yaml_tool" not in filtered  # Disabled by both source and enabled flag

    # Test with only YAML enabled
    mock_config.register_code_tools = False
    mock_config.register_yaml_tools = True
    filtered = clean_injector.get_filtered_instances()
    assert "code_tool" not in filtered  # Disabled by source filtering
    assert "yaml_tool" not in filtered  # Disabled by enabled flag


def test_enabled_flag_precedence_over_source(
    clean_registry, clean_injector, mock_config
):
    """Test that enabled=False takes precedence even when source is enabled."""

    class DisabledCodeTool(ToolInterface):
        @property
        def name(self) -> str:
            return "disabled_code_tool"

        @property
        def description(self) -> str:
            return "A disabled code tool"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    # Register disabled code tool
    clean_registry.register_tool(DisabledCodeTool, source="code", enabled=False)

    # Create instance
    clean_registry._simple_get_tool_instance("disabled_code_tool")

    # Copy instances to injector
    clean_injector.instances = clean_registry.instances.copy()

    # Enable code tools in config
    mock_config.register_code_tools = True

    # Get filtered instances
    filtered = clean_injector.get_filtered_instances()

    # Tool should still be excluded due to enabled=False
    assert "disabled_code_tool" not in filtered
