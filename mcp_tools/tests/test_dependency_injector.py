"""Tests for the dependency injector with source filtering."""

import pytest
from unittest.mock import patch, MagicMock

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import registry, register_tool
from mcp_tools.dependency import injector, DependencyInjector
from mcp_tools.plugin_config import config


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
    
    # Reset to defaults for testing
    config.register_code_tools = True
    config.register_yaml_tools = True
    
    yield config
    
    # Restore original config
    config.register_code_tools = original_register_code_tools
    config.register_yaml_tools = original_register_yaml_tools


@pytest.fixture
def setup_tools(clean_registry, clean_injector):
    """Setup tools in the registry and create instances."""
    # Register tools with sources
    code_tool_class = clean_registry.register_tool(MockCodeTool, source="code")
    yaml_tool_class = clean_registry.register_tool(MockYamlTool, source="yaml")
    
    # Verify tools were registered correctly
    assert "mock_code_tool" in clean_registry.tools
    assert "mock_yaml_tool" in clean_registry.tools
    
    # Get tool sources to verify
    tool_sources = clean_registry.get_tool_sources()
    assert tool_sources["mock_code_tool"] == "code"
    assert tool_sources["mock_yaml_tool"] == "yaml"
    
    # Create instances directly in the injector
    code_instance = MockCodeTool()
    yaml_instance = MockYamlTool()
    
    clean_injector.instances["mock_code_tool"] = code_instance
    clean_injector.instances["mock_yaml_tool"] = yaml_instance
    
    # Disable YAML overriding code to avoid issues in tests
    old_yaml_overrides = config.yaml_overrides_code
    config.yaml_overrides_code = False
    
    yield {
        "code_tool_class": code_tool_class,
        "yaml_tool_class": yaml_tool_class,
        "code_instance": code_instance,
        "yaml_instance": yaml_instance
    }
    
    # Restore original setting
    config.yaml_overrides_code = old_yaml_overrides


def test_get_filtered_instances_all_enabled(setup_tools, mock_config):
    """Test get_filtered_instances with all sources enabled."""
    # Configure sources
    mock_config.register_code_tools = True
    mock_config.register_yaml_tools = True
    
    # Get filtered instances
    filtered = injector.get_filtered_instances()
    
    # Check all tools are included
    assert len(filtered) == 2
    assert "mock_code_tool" in filtered
    assert "mock_yaml_tool" in filtered


def test_get_filtered_instances_code_only(setup_tools, mock_config):
    """Test get_filtered_instances with only code tools enabled."""
    # Configure sources
    mock_config.register_code_tools = True
    mock_config.register_yaml_tools = False
    
    # Get filtered instances
    filtered = injector.get_filtered_instances()
    
    # Check only code tools are included
    assert len(filtered) == 1
    assert "mock_code_tool" in filtered
    assert "mock_yaml_tool" not in filtered


def test_get_filtered_instances_yaml_only(setup_tools, mock_config):
    """Test get_filtered_instances with only YAML tools enabled."""
    # Configure sources
    mock_config.register_code_tools = False
    mock_config.register_yaml_tools = True
    
    # Get filtered instances
    filtered = injector.get_filtered_instances()
    
    # Check only YAML tools are included
    assert len(filtered) == 1
    assert "mock_code_tool" not in filtered
    assert "mock_yaml_tool" in filtered


def test_get_filtered_instances_none_enabled(setup_tools, mock_config):
    """Test get_filtered_instances with no sources enabled."""
    # Configure sources
    mock_config.register_code_tools = False
    mock_config.register_yaml_tools = False
    
    # Get filtered instances
    filtered = injector.get_filtered_instances()
    
    # Check no tools are included
    assert len(filtered) == 0


def test_resolve_all_dependencies_filtering(clean_registry, clean_injector, mock_config):
    """Test that resolve_all_dependencies returns filtered instances."""
    # Register tools with sources
    clean_registry.register_tool(MockCodeTool, source="code")
    clean_registry.register_tool(MockYamlTool, source="yaml")
    
    # Mock analyzer to avoid constructor issues in testing
    with patch.object(clean_injector, 'analyze_tool_constructor') as mock_analyze:
        mock_analyze.return_value = {
            "parameters": {},
            "has_var_kwargs": False
        }
        
        # Test with all sources enabled
        mock_config.register_code_tools = True
        mock_config.register_yaml_tools = True
        
        resolved = clean_injector.resolve_all_dependencies()
        assert len(resolved) == 2
        assert "mock_code_tool" in resolved
        assert "mock_yaml_tool" in resolved
        
        # Reset for next test
        clean_injector.instances.clear()
        
        # Test with only code enabled
        mock_config.register_code_tools = True
        mock_config.register_yaml_tools = False
        
        resolved = clean_injector.resolve_all_dependencies()
        assert len(resolved) == 1
        assert "mock_code_tool" in resolved
        assert "mock_yaml_tool" not in resolved
        
        # Reset for next test
        clean_injector.instances.clear()
        
        # Test with only YAML enabled
        mock_config.register_code_tools = False
        mock_config.register_yaml_tools = True
        
        resolved = clean_injector.resolve_all_dependencies()
        assert len(resolved) == 1
        assert "mock_code_tool" not in resolved
        assert "mock_yaml_tool" in resolved
        
        # Reset for next test
        clean_injector.instances.clear()
        
        # Test with no sources enabled
        mock_config.register_code_tools = False
        mock_config.register_yaml_tools = False
        
        resolved = clean_injector.resolve_all_dependencies()
        assert len(resolved) == 0


def test_get_all_instances_no_filtering(setup_tools):
    """Test get_all_instances returns all instances regardless of source."""
    # Get all instances without filtering
    all_instances = injector.get_all_instances()
    
    # Check all tools are included regardless of config
    assert len(all_instances) == 2
    assert "mock_code_tool" in all_instances
    assert "mock_yaml_tool" in all_instances
    
    # Test with sources disabled (should still return all)
    with patch("mcp_tools.plugin_config.config") as mock_config:
        mock_config.register_code_tools = False
        mock_config.register_yaml_tools = False
        
        all_instances = injector.get_all_instances()
        
        assert len(all_instances) == 2
        assert "mock_code_tool" in all_instances
        assert "mock_yaml_tool" in all_instances 