"""Integration tests for tool source tracking and filtering."""

import pytest
import os
from unittest.mock import patch

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import registry, register_tool, discover_and_register_tools
from mcp_tools.dependency import injector
from mcp_tools.plugin_config import config


# Test tool classes with different sources
class TestCodeTool(ToolInterface):
    """Test code-based tool."""
    
    @property
    def name(self) -> str:
        return "test_code_tool"
        
    @property
    def description(self) -> str:
        return "Test code tool"
        
    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}
    
    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True}


@register_tool(source="yaml")
class TestYamlTool(ToolInterface):
    """Test YAML-based tool using decorator."""
    
    @property
    def name(self) -> str:
        return "test_yaml_tool"
        
    @property
    def description(self) -> str:
        return "Test YAML tool"
        
    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}
    
    async def execute_tool(self, arguments: dict) -> any:
        return {"success": True}


@pytest.fixture
def clean_environment():
    """Reset the environment, registry, and injector for each test."""
    # Save original environment variables
    original_env = {
        "MCP_REGISTER_CODE_TOOLS": os.environ.get("MCP_REGISTER_CODE_TOOLS"),
        "MCP_REGISTER_YAML_TOOLS": os.environ.get("MCP_REGISTER_YAML_TOOLS")
    }
    
    # Save registry state
    original_tools = registry.tools.copy()
    original_instances = registry.instances.copy()
    original_yaml_tool_names = registry.yaml_tool_names.copy()
    original_tool_sources = registry.tool_sources.copy()
    original_discovered_paths = registry.discovered_paths.copy()
    
    # Save injector state
    original_dependencies = injector.dependencies.copy()
    original_tool_constructors = injector.tool_constructors.copy()
    original_injector_instances = injector.instances.copy()
    
    # Clear everything
    registry.clear()
    injector.clear()
    
    # Reset environment variables
    for key in original_env:
        if original_env[key] is not None:
            os.environ[key] = original_env[key]
        elif key in os.environ:
            del os.environ[key]
    
    # Reset configuration
    config._load_from_env()
    
    yield
    
    # Restore everything
    registry.tools = original_tools
    registry.instances = original_instances
    registry.yaml_tool_names = original_yaml_tool_names
    registry.tool_sources = original_tool_sources
    registry.discovered_paths = original_discovered_paths
    
    injector.dependencies = original_dependencies
    injector.tool_constructors = original_tool_constructors
    injector.instances = original_injector_instances
    
    # Restore environment variables
    for key in original_env:
        if original_env[key] is not None:
            os.environ[key] = original_env[key]
        elif key in os.environ:
            del os.environ[key]
    
    # Reset configuration
    config._load_from_env()


def mock_discover_yaml_tools():
    """Mock function to discover and register YAML tools."""
    # Register a YAML tool directly without the decorator to avoid override checks
    yaml_tool_class = type('DirectYamlTool', (ToolInterface,), {
        'name': property(lambda self: "test_yaml_tool"),
        'description': property(lambda self: "Test YAML tool (direct)"),
        'input_schema': property(lambda self: {"type": "object", "properties": {}}),
        'execute_tool': lambda self, *args, **kwargs: {"success": True}
    })
    registry.register_tool(yaml_tool_class, source="yaml")
    return [yaml_tool_class]


@pytest.mark.parametrize("code_enabled,yaml_enabled,expected_tools", [
    (True, True, ["test_code_tool", "test_yaml_tool"]),  # Both enabled
    (True, False, ["test_code_tool"]),                  # Only code enabled
    (False, True, ["test_yaml_tool"]),                  # Only YAML enabled
    (False, False, [])                                  # None enabled
])
def test_end_to_end_tool_filtering(clean_environment, code_enabled, yaml_enabled, expected_tools):
    """Test the entire workflow from registration to filtering with environment variables."""
    # Set environment variables
    os.environ["MCP_REGISTER_CODE_TOOLS"] = "1" if code_enabled else "0"
    os.environ["MCP_REGISTER_YAML_TOOLS"] = "1" if yaml_enabled else "0"
    # Disable YAML overriding code
    os.environ["MCP_YAML_OVERRIDES_CODE"] = "0"
    
    # Reload configuration
    config._load_from_env()
    
    # Register the code tool directly since it won't be discovered
    if code_enabled:
        registry.register_tool(TestCodeTool, source="code")
    
    # Register YAML tools if enabled (skipping discovery process which is complex to mock)
    if yaml_enabled:
        # Create and register a direct YAML tool
        mock_discover_yaml_tools()
    
    # Create instances through dependency injector
    injector.resolve_all_dependencies()
    
    # Get filtered instances
    filtered_instances = injector.get_filtered_instances()
    
    # Verify correct tools were included
    assert len(filtered_instances) == len(expected_tools)
    for tool_name in expected_tools:
        assert tool_name in filtered_instances, f"Tool {tool_name} should be in filtered instances"


@pytest.mark.parametrize("tool_name,source,should_be_enabled", [
    ("test_code_tool", "code", True),     # Code tool with code enabled
    ("test_code_tool", "code", False),    # Code tool with code disabled
    ("test_yaml_tool", "yaml", True),     # YAML tool with YAML enabled
    ("test_yaml_tool", "yaml", False),    # YAML tool with YAML disabled
])
def test_server_tool_call_filtering(clean_environment, tool_name, source, should_be_enabled):
    """Test that server tool calling respects the source configuration."""
    # Configure sources
    os.environ["MCP_REGISTER_CODE_TOOLS"] = "1" if source == "code" and should_be_enabled else "0"
    os.environ["MCP_REGISTER_YAML_TOOLS"] = "1" if source == "yaml" and should_be_enabled else "0"
    
    # Reload configuration
    config._load_from_env()
    
    # Register tools
    registry.register_tool(TestCodeTool, source="code")
    registry.register_tool(TestYamlTool, source="yaml")
    
    # Create instances
    tool_instance = registry._simple_get_tool_instance(tool_name)
    assert tool_instance is not None, f"Failed to create instance for {tool_name}"
    
    # Mock server-side logic to check source before calling tool
    tool_sources = registry.get_tool_sources()
    source_from_registry = tool_sources.get(tool_name, "unknown")
    
    # Check if tool should be enabled based on its source
    is_enabled = config.is_source_enabled(source_from_registry)
    
    # Verify result matches expectation
    assert is_enabled == should_be_enabled


def test_source_tracking_persistence(clean_environment):
    """Test that tool sources are correctly tracked and persisted."""
    # Register tools with explicit sources
    registry.register_tool(TestCodeTool, source="code")
    
    # Create a dynamic tool class for custom source
    custom_tool_class = type('CustomSourceTool', (ToolInterface,), {
        'name': property(lambda self: "test_yaml_tool"),
        'description': property(lambda self: "Test custom source tool"),
        'input_schema': property(lambda self: {"type": "object", "properties": {}}),
        'execute_tool': lambda self, *args, **kwargs: {"success": True}
    })
    registry.register_tool(custom_tool_class, source="custom_source")
    
    # Verify sources are tracked
    tool_sources = registry.get_tool_sources()
    assert tool_sources["test_code_tool"] == "code"
    assert tool_sources["test_yaml_tool"] == "custom_source"
    
    # Clear only instances but keep sources
    registry.instances.clear()
    
    # Verify sources are still tracked
    tool_sources = registry.get_tool_sources()
    assert tool_sources["test_code_tool"] == "code"
    assert tool_sources["test_yaml_tool"] == "custom_source" 