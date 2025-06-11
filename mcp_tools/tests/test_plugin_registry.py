"""Tests for the plugin registry and tool source tracking."""

import pytest
from unittest.mock import patch, MagicMock

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import registry, register_tool, PluginRegistry
from mcp_tools.plugin_config import config, PluginConfig


# Mock tool classes for testing
class MockCodeTool(ToolInterface):
    """Mock tool for testing code-based tools."""

    @property
    def name(self) -> str:
        return "mock_code_tool"

    @property
    def description(self) -> str:
        return "A mock code-based tool for testing"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True, "message": "Code tool executed"}


class MockYamlTool(ToolInterface):
    """Mock tool for testing YAML-based tools."""

    @property
    def name(self) -> str:
        return "mock_yaml_tool"

    @property
    def description(self) -> str:
        return "A mock YAML-based tool for testing"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True, "message": "YAML tool executed"}


@pytest.fixture
def clean_registry():
    """Fixture to provide a clean registry for each test."""
    # Save the original registry state
    original_tools = registry.tools.copy()
    original_instances = registry.instances.copy()
    original_yaml_tool_names = registry.yaml_tool_names.copy()
    original_tool_sources = registry.tool_sources.copy()

    # Clear the registry
    registry.clear()

    yield registry

    # Restore the original registry state
    registry.tools = original_tools
    registry.instances = original_instances
    registry.yaml_tool_names = original_yaml_tool_names
    registry.tool_sources = original_tool_sources


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
    config.yaml_overrides_code = False  # Disable YAML overriding code

    yield config

    # Restore original config
    config.register_code_tools = original_register_code_tools
    config.register_yaml_tools = original_register_yaml_tools
    config.yaml_overrides_code = original_yaml_overrides_code


def test_register_tool_with_source(clean_registry):
    """Test registering tools with explicit sources."""
    # Register tools with explicit sources
    clean_registry.register_tool(MockCodeTool, source="code")
    clean_registry.register_tool(MockYamlTool, source="yaml")

    # Check if tools are registered
    assert "mock_code_tool" in clean_registry.tools
    assert "mock_yaml_tool" in clean_registry.tools

    # Check sources
    tool_sources = clean_registry.get_tool_sources()
    assert "mock_code_tool" in tool_sources
    assert "mock_yaml_tool" in tool_sources
    assert tool_sources["mock_code_tool"] == "code"
    assert tool_sources["mock_yaml_tool"] == "yaml"


def test_register_tool_decorator(clean_registry):
    """Test registering tools using the decorator."""

    # Use decorator with default source (code)
    @register_tool
    class DecoratedCodeTool(ToolInterface):
        @property
        def name(self) -> str:
            return "decorated_code_tool"

        @property
        def description(self) -> str:
            return "A decorated code tool"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    # Use decorator with explicit source (yaml)
    @register_tool(source="yaml")
    class DecoratedYamlTool(ToolInterface):
        @property
        def name(self) -> str:
            return "decorated_yaml_tool"

        @property
        def description(self) -> str:
            return "A decorated yaml tool"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute_tool(self, arguments: dict) -> any:
            return {"success": True}

    # Check if tools are registered
    assert "decorated_code_tool" in clean_registry.tools
    assert "decorated_yaml_tool" in clean_registry.tools

    # Check sources
    tool_sources = clean_registry.get_tool_sources()
    assert tool_sources["decorated_code_tool"] == "code"
    assert tool_sources["decorated_yaml_tool"] == "yaml"


def test_get_tools_by_source(clean_registry):
    """Test getting tools filtered by source."""
    # Register tools with different sources
    clean_registry.register_tool(MockCodeTool, source="code")
    clean_registry.register_tool(MockYamlTool, source="yaml")

    # Get tools by source
    code_tools = clean_registry.get_tools_by_source("code")
    yaml_tools = clean_registry.get_tools_by_source("yaml")

    # Check results
    assert len(code_tools) == 1
    assert len(yaml_tools) == 1
    assert code_tools[0] == MockCodeTool
    assert yaml_tools[0] == MockYamlTool


@pytest.mark.parametrize(
    "code_enabled,yaml_enabled,expected_count",
    [
        (True, True, 2),  # Both enabled -> 2 tools
        (True, False, 1),  # Only code enabled -> 1 tool
        (False, True, 1),  # Only yaml enabled -> 1 tool
        (False, False, 0),  # Both disabled -> 0 tools
    ],
)
def test_filtered_instances(
    clean_registry, mock_config, code_enabled, yaml_enabled, expected_count
):
    """Test filtered instances based on configuration."""
    # Configure enabled sources
    mock_config.register_code_tools = code_enabled
    mock_config.register_yaml_tools = yaml_enabled

    # Register tools with different sources
    clean_registry.register_tool(MockCodeTool, source="code")
    clean_registry.register_tool(MockYamlTool, source="yaml")

    # Create instances
    clean_registry._simple_get_tool_instance("mock_code_tool")
    clean_registry._simple_get_tool_instance("mock_yaml_tool")

    # Use mock dependency injector to avoid circular imports in test
    with patch("mcp_tools.dependency.injector") as mock_injector:
        # Setup mock injector
        if code_enabled and yaml_enabled:
            mock_injector.get_filtered_instances.return_value = clean_registry.instances
        elif code_enabled:
            mock_injector.get_filtered_instances.return_value = {
                "mock_code_tool": clean_registry.instances["mock_code_tool"]
            }
        elif yaml_enabled:
            mock_injector.get_filtered_instances.return_value = {
                "mock_yaml_tool": clean_registry.instances["mock_yaml_tool"]
            }
        else:
            mock_injector.get_filtered_instances.return_value = {}

        # Get filtered instances
        filtered_instances = clean_registry.get_all_instances()

        # Check results
        assert len(filtered_instances) == expected_count

        if code_enabled:
            assert any(isinstance(inst, MockCodeTool) for inst in filtered_instances)
        else:
            assert not any(
                isinstance(inst, MockCodeTool) for inst in filtered_instances
            )

        if yaml_enabled:
            assert any(isinstance(inst, MockYamlTool) for inst in filtered_instances)
        else:
            assert not any(
                isinstance(inst, MockYamlTool) for inst in filtered_instances
            )


def test_plugin_config_source_enabled(mock_config):
    """Test the is_source_enabled method in PluginConfig."""
    # Test with both sources enabled
    mock_config.register_code_tools = True
    mock_config.register_yaml_tools = True

    assert mock_config.is_source_enabled("code") is True
    assert mock_config.is_source_enabled("yaml") is True
    assert mock_config.is_source_enabled("unknown") is True

    # Test with only code enabled
    mock_config.register_code_tools = True
    mock_config.register_yaml_tools = False

    assert mock_config.is_source_enabled("code") is True
    assert mock_config.is_source_enabled("yaml") is False
    assert mock_config.is_source_enabled("unknown") is False

    # Test with only yaml enabled
    mock_config.register_code_tools = False
    mock_config.register_yaml_tools = True

    assert mock_config.is_source_enabled("code") is False
    assert mock_config.is_source_enabled("yaml") is True
    assert mock_config.is_source_enabled("unknown") is False

    # Test with both sources disabled
    mock_config.register_code_tools = False
    mock_config.register_yaml_tools = False

    assert mock_config.is_source_enabled("code") is False
    assert mock_config.is_source_enabled("yaml") is False
    assert mock_config.is_source_enabled("unknown") is False


def test_valid_tool_sources():
    """Test that only the expected tool source types exist.

    This test intentionally breaks when a new tool source type is added,
    forcing developers to update tests for the new source type.
    """
    # Register tools with different valid sources
    clean_registry = PluginRegistry()
    clean_registry.clear()  # Reset to clean state

    # Register tools with different sources
    clean_registry.register_tool(MockCodeTool, source="code")
    clean_registry.register_tool(MockYamlTool, source="yaml")

    # Get all unique sources
    tool_sources = clean_registry.get_tool_sources()
    unique_sources = set(tool_sources.values())

    # This assertion will fail when a new source type is added,
    # forcing developers to update the test
    assert unique_sources == {
        "code",
        "yaml",
    }, f"""
    =====================================================================
    ATTENTION: Tool source types have changed!

    Expected source types: code, yaml
    Actual source types: {', '.join(sorted(unique_sources))}

    If you are adding a new tool source type:
    1. Update this test to include the new source type in the assertion
    2. Add tests for the new source type's behavior
    3. Update the plugin_config.is_source_enabled method to handle the new source
    =====================================================================
    """


def test_discover_plugin_directory_with_multiple_tool_files(clean_registry, tmp_path):
    """Test that discover_plugin_directory can find all files ending with tool.py."""
    # Create a temporary plugin directory structure
    plugin_dir = tmp_path / "test_plugin"
    plugin_dir.mkdir()

    # Create __init__.py to make it a valid Python package
    (plugin_dir / "__init__.py").write_text("")

    # Create multiple tool files
    repo_tool_content = """
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

@register_tool
class TestRepoTool(ToolInterface):
    @property
    def name(self) -> str:
        return "test_repo_tool"

    @property
    def description(self) -> str:
        return "Test repository tool"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True, "tool": "repo"}
"""

    pr_tool_content = """
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

@register_tool
class TestPRTool(ToolInterface):
    @property
    def name(self) -> str:
        return "test_pr_tool"

    @property
    def description(self) -> str:
        return "Test PR tool"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True, "tool": "pr"}
"""

    workitem_tool_content = """
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

@register_tool
class TestWorkItemTool(ToolInterface):
    @property
    def name(self) -> str:
        return "test_workitem_tool"

    @property
    def description(self) -> str:
        return "Test work item tool"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True, "tool": "workitem"}
"""

    # Write the tool files
    (plugin_dir / "repo_tool.py").write_text(repo_tool_content)
    (plugin_dir / "pr_tool.py").write_text(pr_tool_content)
    (plugin_dir / "workitem_tool.py").write_text(workitem_tool_content)

    # Also create a non-tool file to ensure it's ignored
    (plugin_dir / "helper.py").write_text("# This is not a tool file")

    # Discover plugins in the directory
    clean_registry.discover_plugin_directory(tmp_path)

    # Verify that all three tools were discovered
    assert "test_repo_tool" in clean_registry.tools
    assert "test_pr_tool" in clean_registry.tools
    assert "test_workitem_tool" in clean_registry.tools

    # Verify the tool classes are correct
    assert clean_registry.tools["test_repo_tool"].__name__ == "TestRepoTool"
    assert clean_registry.tools["test_pr_tool"].__name__ == "TestPRTool"
    assert clean_registry.tools["test_workitem_tool"].__name__ == "TestWorkItemTool"

    # Verify all tools are marked as code-based
    tool_sources = clean_registry.get_tool_sources()
    assert tool_sources["test_repo_tool"] == "code"
    assert tool_sources["test_pr_tool"] == "code"
    assert tool_sources["test_workitem_tool"] == "code"


def test_discover_plugin_directory_ignores_non_tool_files(clean_registry, tmp_path):
    """Test that discover_plugin_directory ignores files that don't end with tool.py."""
    # Create a temporary plugin directory structure
    plugin_dir = tmp_path / "test_plugin"
    plugin_dir.mkdir()

    # Create __init__.py to make it a valid Python package
    (plugin_dir / "__init__.py").write_text("")

    # Create a valid tool file
    tool_content = """
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

@register_tool
class ValidTool(ToolInterface):
    @property
    def name(self) -> str:
        return "valid_tool"

    @property
    def description(self) -> str:
        return "A valid tool"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True}
"""

    # Create files that should be ignored
    invalid_content = """
from mcp_tools.interfaces import ToolInterface

class InvalidTool(ToolInterface):
    @property
    def name(self) -> str:
        return "invalid_tool"

    @property
    def description(self) -> str:
        return "This should be ignored"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True}
"""

    # Write files
    (plugin_dir / "valid_tool.py").write_text(tool_content)  # Should be discovered
    (plugin_dir / "helper.py").write_text(invalid_content)  # Should be ignored
    (plugin_dir / "utils.py").write_text(invalid_content)  # Should be ignored
    (plugin_dir / "config.py").write_text(invalid_content)  # Should be ignored

    # Discover plugins in the directory
    clean_registry.discover_plugin_directory(tmp_path)

    # Verify only the valid tool was discovered
    assert "valid_tool" in clean_registry.tools
    assert "invalid_tool" not in clean_registry.tools

    # Verify we only have one tool registered
    assert len(clean_registry.tools) == 1
