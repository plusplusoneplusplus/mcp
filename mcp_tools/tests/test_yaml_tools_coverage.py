"""Comprehensive test coverage for YAML-defined tools.

This module provides comprehensive test coverage for all YAML-defined tools that are
loaded from configuration files and registered through the mcp_tools.yaml_tools system.

This addresses GitHub issue #100: Add comprehensive test coverage for YAML-defined tools.

The tests in this module:
1. Discover all YAML-defined tools from configuration using registry.get_tools_by_source("yaml")
2. Test each YAML tool with valid arguments
3. Test YAML tool parsing and validation
4. Verify tool execution returns expected response format
5. Verify tool metadata from YAML is correctly applied
6. Test different YAML configuration scenarios
7. Use proper fixtures and avoid side effects
"""

import pytest
import logging
import asyncio
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typing import Dict, Any, List, Type, Optional

from mcp_tools.yaml_tools import YamlToolBase, load_yaml_tools, get_yaml_tool_names
from mcp_tools.plugin import registry, register_tool
from mcp_tools.plugin_config import config
from mcp_tools.interfaces import ToolInterface, CommandExecutorInterface


class MockCommandExecutorForCoverage(CommandExecutorInterface):
    """Mock command executor for comprehensive coverage testing."""

    def __init__(self):
        self.executed_commands = []
        self.call_count = 0

    @property
    def name(self) -> str:
        return "mock_coverage_executor"

    @property
    def description(self) -> str:
        return "Mock command executor for comprehensive coverage testing"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        self.call_count += 1
        return {"success": True, "call_count": self.call_count}

    def execute(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        self.executed_commands.append(command)
        return {"status": "completed", "returncode": 0, "stdout": f"Executed: {command}"}

    async def execute_async(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        self.executed_commands.append(command)
        return {"token": f"token-{len(self.executed_commands)}", "status": "running", "pid": 12345}

    async def query_process(self, token: str, wait: bool = False, timeout: Optional[float] = None) -> Dict[str, Any]:
        return {"status": "completed", "returncode": 0, "output": f"Process {token} completed"}

    def terminate_by_token(self, token: str) -> bool:
        return True

    def list_running_processes(self) -> List[Dict[str, Any]]:
        return []

    async def start_periodic_status_reporter(self, interval: float = 30.0, enabled: bool = True) -> None:
        pass

    async def stop_periodic_status_reporter(self) -> None:
        pass


@pytest.fixture
def clean_registry():
    """Fixture to provide a clean registry for each test."""
    original_tools = registry.tools.copy()
    original_instances = registry.instances.copy()
    original_tool_sources = registry.tool_sources.copy()
    original_yaml_tool_names = registry.yaml_tool_names.copy()

    yield registry

    registry.tools = original_tools
    registry.instances = original_instances
    registry.tool_sources = original_tool_sources
    registry.yaml_tool_names = original_yaml_tool_names


@pytest.fixture
def mock_coverage_executor():
    """Fixture providing a mock command executor for coverage testing."""
    return MockCommandExecutorForCoverage()


@pytest.fixture
def comprehensive_yaml_config():
    """Fixture providing comprehensive YAML configuration for testing."""
    return {
        "tools": {
            "coverage_test_echo": {
                "description": "Echo tool for comprehensive coverage testing",
                "type": "script",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to echo"},
                        "count": {"type": "integer", "default": 1, "description": "Number of times to echo"}
                    },
                    "required": ["message"]
                },
                "scripts": {
                    "linux": "echo '{message}' | head -n {count}",
                    "darwin": "echo '{message}' | head -n {count}",
                    "windows": "echo {message}"
                }
            },
            "coverage_test_simple": {
                "description": "Simple tool for coverage testing",
                "type": "object",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"}
                    }
                }
            }
        }
    }


class TestYamlToolsComprehensiveCoverage:
    """Comprehensive test coverage for YAML-defined tools."""

    def test_yaml_tool_discovery_and_registration(self, clean_registry, comprehensive_yaml_config):
        """Test that YAML tools are properly discovered and registered with 'yaml' source."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        
        with patch("mcp_tools.yaml_tools.register_tool", mock_register), \
             patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=comprehensive_yaml_config):
            
            classes = load_yaml_tools()
            
            assert len(classes) == 2
            assert mock_register.call_count == 2
            
            for call in mock_register.call_args_list:
                assert call.kwargs.get("source") == "yaml"

    def test_registry_get_tools_by_source_yaml(self, clean_registry, comprehensive_yaml_config):
        """Test registry.get_tools_by_source('yaml') returns all YAML-defined tools."""
        # Clear registry to start fresh
        registry.tools.clear()
        registry.tool_sources.clear()
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=comprehensive_yaml_config):
            
            classes = load_yaml_tools()
            
            for tool_class in classes:
                registry.register_tool(tool_class, source="yaml")
            
            yaml_tools = registry.get_tools_by_source("yaml")
            assert len(yaml_tools) == 2
            
            tool_sources = registry.get_tool_sources()
            for tool_class in yaml_tools:
                instance = tool_class()
                assert tool_sources.get(instance.name) == "yaml"

    @pytest.mark.asyncio
    async def test_yaml_tool_execution_with_valid_arguments(self, clean_registry, comprehensive_yaml_config, mock_coverage_executor):
        """Test each YAML tool execution with valid sample arguments."""
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=comprehensive_yaml_config):
            
            classes = load_yaml_tools()
            
            test_arguments = {
                "coverage_test_echo": {"message": "Hello Coverage Test", "count": 2},
                "coverage_test_simple": {"input": "test input"}
            }
            
            for tool_class in classes:
                instance = tool_class(command_executor=mock_coverage_executor)
                tool_name = instance.name
                
                if tool_name in test_arguments:
                    arguments = test_arguments[tool_name]
                    result = await instance.execute_tool(arguments)
                    assert result is not None

    def test_yaml_tool_metadata_validation(self, clean_registry, comprehensive_yaml_config):
        """Test that YAML tool metadata is correctly applied and validated."""
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=comprehensive_yaml_config):
            
            classes = load_yaml_tools()
            
            for tool_class in classes:
                instance = tool_class()
                tool_data = comprehensive_yaml_config["tools"][instance.name]
                
                assert instance.description == tool_data["description"]
                assert isinstance(instance.input_schema, dict)
                assert instance.input_schema["type"] == "object"
                
                expected_type = tool_data.get("type", "object")
                assert instance._tool_type == expected_type

    def test_get_yaml_tool_names_coverage(self, clean_registry):
        """Test get_yaml_tool_names function for comprehensive coverage."""
        test_config = {
            "tools": {
                "name_test_1": {"description": "First tool"},
                "name_test_2": {"description": "Second tool"}
            }
        }
        
        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=test_config):
            tool_names = get_yaml_tool_names()
            
            assert isinstance(tool_names, set)
            assert len(tool_names) == 2
            assert tool_names == {"name_test_1", "name_test_2"}

    def test_yaml_configuration_scenarios(self, clean_registry):
        """Test different YAML configuration scenarios."""
        
        # Scenario 1: Minimal configuration
        minimal_config = {
            "tools": {
                "minimal_tool": {
                    "description": "Minimal tool",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            }
        }
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=minimal_config):
            
            classes = load_yaml_tools()
            assert len(classes) == 1
            
            instance = classes[0]()
            assert instance.name == "minimal_tool"
            assert instance.description == "Minimal tool"
            assert instance._tool_type == "object"  # Default type
            assert instance.input_schema["type"] == "object"
        
        # Scenario 2: Tool with custom parameters
        custom_params_config = {
            "tools": {
                "custom_params_tool": {
                    "description": "Tool with custom parameters",
                    "type": "script",
                    "inputSchema": {"type": "object", "properties": {}},
                    "parameters": {
                        "custom_param1": "value1",
                        "custom_param2": "value2"
                    },
                    "scripts": {
                        "linux": "echo {custom_param1} {custom_param2}",
                        "darwin": "echo {custom_param1} {custom_param2}",
                        "windows": "echo {custom_param1} {custom_param2}"
                    }
                }
            }
        }
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=custom_params_config):
            
            classes = load_yaml_tools()
            assert len(classes) == 1
            
            instance = classes[0]()
            assert instance.name == "custom_params_tool"
            assert instance._tool_data["parameters"]["custom_param1"] == "value1"
            assert instance._tool_data["parameters"]["custom_param2"] == "value2"

    def test_yaml_tool_loading_and_parsing_edge_cases(self, clean_registry):
        """Test YAML tool loading and parsing edge cases."""
        
        # Test empty tools section
        empty_tools_config = {"tools": {}}
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=empty_tools_config):
            
            classes = load_yaml_tools()
            assert len(classes) == 0
        
        # Test missing tools section
        no_tools_config = {"other_section": {}}
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=no_tools_config):
            
            classes = load_yaml_tools()
            assert len(classes) == 0
        
        # Test tool with missing description (should use empty string)
        missing_desc_config = {
            "tools": {
                "no_desc_tool": {
                    "description": "",
                    "type": "object",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            }
        }
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=missing_desc_config):
            
            classes = load_yaml_tools()
            assert len(classes) == 1
            
            instance = classes[0]()
            assert instance.name == "no_desc_tool"
            assert instance.description == ""

    @pytest.mark.asyncio
    async def test_yaml_tool_execution_response_format(self, clean_registry, mock_coverage_executor):
        """Test that YAML tool execution returns expected response format."""
        
        script_tool_config = {
            "tools": {
                "response_format_test": {
                    "description": "Tool for testing response format",
                    "type": "script",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"message": {"type": "string"}},
                        "required": ["message"]
                    },
                    "scripts": {
                        "linux": "echo '{message}'",
                        "darwin": "echo '{message}'",
                        "windows": "echo {message}"
                    }
                }
            }
        }
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=script_tool_config):
            
            classes = load_yaml_tools()
            instance = classes[0](command_executor=mock_coverage_executor)
            
            # Execute with valid arguments
            result = await instance.execute_tool({"message": "test"})
            
            # Verify response format
            assert isinstance(result, list)
            assert len(result) > 0
            
            for item in result:
                assert isinstance(item, dict)
                assert "type" in item
                assert item["type"] in ["text", "resource"]  # Expected response types
                
                if item["type"] == "text":
                    assert "text" in item
                    assert isinstance(item["text"], str)

    def test_yaml_tool_source_tracking_integration(self, clean_registry, comprehensive_yaml_config):
        """Test integration of YAML tool source tracking with registry."""
        # Clear registry to start fresh
        registry.tools.clear()
        registry.tool_sources.clear()
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=comprehensive_yaml_config):
            
            # Load YAML tools
            classes = load_yaml_tools()
            
            # Register tools with registry
            for tool_class in classes:
                registry.register_tool(tool_class, source="yaml")
            
            # Verify source tracking
            tool_sources = registry.get_tool_sources()
            yaml_tools = registry.get_tools_by_source("yaml")
            code_tools = registry.get_tools_by_source("code")
            
            # All our test tools should be tracked as "yaml"
            for tool_class in classes:
                instance = tool_class()
                assert tool_sources.get(instance.name) == "yaml"
            
            # Verify get_tools_by_source filtering
            assert len(yaml_tools) == 2  # Our 2 test tools
            
            # Verify YAML tools are not in code tools
            yaml_tool_names = {cls._tool_name for cls in yaml_tools}
            code_tool_names = {cls().name for cls in code_tools}
            assert yaml_tool_names.isdisjoint(code_tool_names)

    def test_yaml_tools_with_fixtures_no_side_effects(self, clean_registry):
        """Test that YAML tool tests use proper fixtures and don't have side effects."""
        
        # Record initial registry state
        initial_tools_count = len(registry.tools)
        initial_instances_count = len(registry.instances)
        initial_sources_count = len(registry.tool_sources)
        
        test_config = {
            "tools": {
                "side_effect_test": {
                    "description": "Tool for testing side effects",
                    "type": "object",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            }
        }
        
        # Mock register_tool to prevent actual registration
        mock_register = MagicMock(return_value=lambda cls: cls)
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=test_config), \
             patch("mcp_tools.yaml_tools.register_tool", mock_register):
            
            # Load tools within the test
            classes = load_yaml_tools()
            assert len(classes) == 1
            
            # Create instance
            instance = classes[0]()
            assert instance.name == "side_effect_test"
        
        # After test completion, registry should be restored by fixture
        # (This is verified by the clean_registry fixture cleanup)
        assert len(registry.tools) == initial_tools_count
        assert len(registry.instances) == initial_instances_count
        assert len(registry.tool_sources) == initial_sources_count

    @pytest.mark.asyncio
    async def test_comprehensive_workflow_integration(self, clean_registry, mock_coverage_executor):
        """Test complete workflow: discovery -> registration -> execution."""
        # Clear registry to start fresh
        registry.tools.clear()
        registry.tool_sources.clear()
        
        workflow_config = {
            "tools": {
                "workflow_test": {
                    "description": "Tool for workflow integration testing",
                    "type": "script",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["test", "validate"]},
                            "data": {"type": "string"}
                        },
                        "required": ["action"]
                    },
                    "scripts": {
                        "linux": "echo 'Workflow {action}: {data}'",
                        "darwin": "echo 'Workflow {action}: {data}'",
                        "windows": "echo Workflow {action}: {data}"
                    }
                }
            }
        }
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=workflow_config):
            
            # Step 1: Discovery
            classes = load_yaml_tools()
            assert len(classes) == 1
            
            # Step 2: Registration
            tool_class = classes[0]
            registry.register_tool(tool_class, source="yaml")
            
            # Step 3: Verification of registration
            yaml_tools = registry.get_tools_by_source("yaml")
            assert len(yaml_tools) == 1
            assert yaml_tools[0] == tool_class
            
            # Step 4: Tool instantiation and execution
            instance = tool_class(command_executor=mock_coverage_executor)
            
            # Test with valid enum value
            result = await instance.execute_tool({"action": "test", "data": "sample data"})
            assert isinstance(result, list)
            assert len(result) > 0
            
            # Verify command was executed
            assert len(mock_coverage_executor.executed_commands) > 0
            executed_command = mock_coverage_executor.executed_commands[-1]
            assert "Workflow test: sample data" in executed_command


class TestYamlToolsErrorScenarios:
    """Test error scenarios for comprehensive coverage."""

    def test_yaml_tool_validation_errors(self, clean_registry):
        """Test YAML tool validation error scenarios."""
        
        # Invalid tool configuration - missing required fields
        invalid_config = {
            "tools": {
                "invalid_tool": {
                    # Missing description
                    "inputSchema": "not_a_dict"  # Invalid schema type
                }
            }
        }
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=invalid_config):
            
            # Should handle invalid configuration gracefully
            classes = load_yaml_tools()
            
            # Tool should still be created but with defaults
            if classes:  # If any tools were created despite errors
                instance = classes[0]()
                assert instance.name == "invalid_tool"
                assert instance.description == ""  # Default empty description
                # Input schema should be corrected to default
                assert isinstance(instance.input_schema, dict)

    @pytest.mark.asyncio
    async def test_yaml_tool_execution_errors(self, clean_registry):
        """Test YAML tool execution error scenarios."""
        
        error_config = {
            "tools": {
                "error_test": {
                    "description": "Tool for testing execution errors",
                    "type": "script",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"required_param": {"type": "string"}},
                        "required": ["required_param"]
                    },
                    "scripts": {
                        "linux": "echo '{required_param}'",
                        "darwin": "echo '{required_param}'",
                        "windows": "echo {required_param}"
                    }
                }
            }
        }
        
        with patch.object(config, "register_yaml_tools", True), \
             patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=error_config):
            
            classes = load_yaml_tools()
            
            # Mock dependency injection to return None for command executor
            with patch('mcp_tools.dependency.injector.get_tool_instance') as mock_get_instance:
                mock_get_instance.return_value = None
                instance = classes[0]()  # No command executor provided
                
                # Test execution without command executor
                result = await instance.execute_tool({"required_param": "test"})
                assert result == {"success": False, "error": "Command executor not available"}
            
            # Test execution with invalid arguments (missing required parameter)
            mock_executor = MockCommandExecutorForCoverage()
            instance_with_executor = classes[0](command_executor=mock_executor)
            
            result = await instance_with_executor.execute_tool({})  # Missing required_param
            assert isinstance(result, list)
            assert len(result) > 0
            assert "validation error" in result[0]["text"].lower() 