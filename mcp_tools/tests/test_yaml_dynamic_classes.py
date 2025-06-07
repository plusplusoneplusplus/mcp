"""Tests for dynamic YAML tool class creation and registration.

This module tests the complex process of dynamically creating Python classes from YAML
definitions using the type() function and registering them with the plugin system.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock, call
from typing import Dict, Any, Type

from mcp_tools.yaml_tools import YamlToolBase, load_yaml_tools
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import registry, register_tool
from mcp_tools.plugin_config import config


class TestDynamicClassCreation:
    """Test cases for dynamic class creation using type()."""

    def test_class_creation_with_type_function(self, monkeypatch):
        """Test that classes are created using type() with proper inheritance."""
        # Mock the registration to avoid side effects
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        # Mock YAML data
        yaml_data = {
            "tools": {
                "test_tool": {
                    "description": "Test tool description",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"param": {"type": "string"}},
                        "required": ["param"]
                    }
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        # Verify class was created
        assert len(classes) == 1
        tool_class = classes[0]

        # Verify class name follows convention
        assert tool_class.__name__ == "YamlTool_test_tool"

        # Verify inheritance
        assert issubclass(tool_class, YamlToolBase)
        assert issubclass(tool_class, ToolInterface)

        # Verify class attributes are set
        assert hasattr(tool_class, "_tool_name")
        assert hasattr(tool_class, "_tool_data")
        assert tool_class._tool_name == "test_tool"
        assert tool_class._tool_data == yaml_data["tools"]["test_tool"]

    def test_class_attribute_setting(self, monkeypatch):
        """Test that class attributes (_tool_name, _tool_data) are set correctly."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        tool_data = {
            "description": "Custom tool",
            "inputSchema": {"type": "object", "properties": {}},
            "type": "script",
            "custom_field": "custom_value"
        }

        yaml_data = {"tools": {"custom_tool": tool_data}}

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        tool_class = classes[0]

        # Verify attributes are set correctly
        assert tool_class._tool_name == "custom_tool"
        assert tool_class._tool_data == tool_data
        assert tool_class._tool_data["custom_field"] == "custom_value"

    def test_class_naming_conventions(self, monkeypatch):
        """Test that class names follow the YamlTool_{name} convention."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "simple_tool": {"description": "Simple", "inputSchema": {"type": "object"}},
                "complex_tool_name": {"description": "Complex", "inputSchema": {"type": "object"}},
                "tool123": {"description": "Numeric", "inputSchema": {"type": "object"}},
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        # Verify naming convention
        class_names = [cls.__name__ for cls in classes]
        expected_names = ["YamlTool_simple_tool", "YamlTool_complex_tool_name", "YamlTool_tool123"]
        
        assert len(class_names) == 3
        for expected_name in expected_names:
            assert expected_name in class_names

    def test_class_instantiation_and_validation(self, monkeypatch):
        """Test that created classes can be instantiated and validated."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "instantiation_test": {
                    "description": "Test instantiation",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"message": {"type": "string"}},
                        "required": ["message"]
                    }
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        tool_class = classes[0]

        # Test instantiation
        instance = tool_class()
        
        # Verify instance properties
        assert instance.name == "instantiation_test"
        assert instance.description == "Test instantiation"
        assert instance.input_schema["type"] == "object"
        assert "message" in instance.input_schema["properties"]
        assert instance.input_schema["required"] == ["message"]

        # Verify instance is of correct type
        assert isinstance(instance, YamlToolBase)
        assert isinstance(instance, ToolInterface)

    def test_multiple_class_creation(self, monkeypatch):
        """Test creating multiple classes from multiple tool definitions."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "tool_one": {"description": "First tool", "inputSchema": {"type": "object"}},
                "tool_two": {"description": "Second tool", "inputSchema": {"type": "object"}},
                "tool_three": {"description": "Third tool", "inputSchema": {"type": "object"}},
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        # Verify all classes were created
        assert len(classes) == 3

        # Verify each class is unique and properly configured
        tool_names = []
        for tool_class in classes:
            instance = tool_class()
            tool_names.append(instance.name)
            assert isinstance(instance, YamlToolBase)

        assert set(tool_names) == {"tool_one", "tool_two", "tool_three"}


class TestToolRegistrationProcess:
    """Test cases for the tool registration process."""

    def test_registration_with_decorator(self, monkeypatch):
        """Test registration with @register_tool(source="yaml") decorator."""
        # Mock the registry to capture registration calls
        mock_registry = MagicMock()
        monkeypatch.setattr("mcp_tools.yaml_tools.registry", mock_registry)
        
        # Mock the register_tool decorator
        mock_register = MagicMock()
        def mock_register_func(source="code"):
            def decorator(cls):
                mock_register(source=source, cls=cls)
                return cls
            return decorator
        
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register_func)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "registration_test": {
                    "description": "Test registration",
                    "inputSchema": {"type": "object"}
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        # Verify registration was called with correct source
        mock_register.assert_called_once()
        call_args = mock_register.call_args
        assert call_args.kwargs["source"] == "yaml"
        assert issubclass(call_args.kwargs["cls"], YamlToolBase)

    def test_registration_error_handling(self, monkeypatch, caplog):
        """Test error handling during registration process."""
        # Mock register_tool to raise an exception
        def failing_register(source="code"):
            def decorator(cls):
                raise Exception("Registration failed")
            return decorator

        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", failing_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "failing_tool": {
                    "description": "This will fail",
                    "inputSchema": {"type": "object"}
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            caplog.set_level(logging.ERROR)
            classes = load_yaml_tools()

        # Verify error was logged and no classes were returned
        assert len(classes) == 0
        assert any("Registration failed" in record.message for record in caplog.records)

    def test_tool_source_tracking(self, monkeypatch):
        """Test that tool source is tracked correctly."""
        # Create a real registry instance for testing
        from mcp_tools.plugin import PluginRegistry
        test_registry = PluginRegistry()
        test_registry.clear()  # Start clean

        monkeypatch.setattr("mcp_tools.yaml_tools.registry", test_registry)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "source_test": {
                    "description": "Test source tracking",
                    "inputSchema": {"type": "object"}
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        # Verify tool was registered with correct source
        assert len(classes) == 1
        tool_sources = test_registry.get_tool_sources()
        assert "source_test" in tool_sources
        assert tool_sources["source_test"] == "yaml"


class TestClassValidationAndTesting:
    """Test cases for class validation and testing."""

    def test_instantiation_testing_of_created_classes(self, monkeypatch):
        """Test that the load_yaml_tools function tests instantiation of created classes."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "validation_test": {
                    "description": "Test validation",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            }
        }

        # Track instantiation by patching YamlToolBase.__init__
        instantiation_calls = []
        original_init = YamlToolBase.__init__
        
        def tracked_init(self, *args, **kwargs):
            instantiation_calls.append((self.__class__.__name__, args, kwargs))
            return original_init(self, *args, **kwargs)

        with patch.object(YamlToolBase, "__init__", tracked_init):
            with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
                classes = load_yaml_tools()

        # Verify instantiation test occurred during class validation
        assert len(classes) == 1
        assert len(instantiation_calls) > 0
        # The load_yaml_tools function creates test instances to validate the classes
        assert any("YamlTool_validation_test" in call[0] for call in instantiation_calls)

    def test_property_validation(self, monkeypatch):
        """Test validation of name, description, and input_schema properties."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "property_test": {
                    "description": "Property validation test",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"param1": {"type": "string"}},
                        "required": ["param1"]
                    }
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        tool_class = classes[0]
        instance = tool_class()

        # Validate properties
        assert instance.name == "property_test"
        assert instance.description == "Property validation test"
        assert isinstance(instance.input_schema, dict)
        assert instance.input_schema["type"] == "object"
        assert "param1" in instance.input_schema["properties"]
        assert instance.input_schema["required"] == ["param1"]

    def test_method_availability_and_functionality(self, monkeypatch):
        """Test that required methods are available and functional."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "method_test": {
                    "description": "Method test",
                    "inputSchema": {"type": "object"}
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        tool_class = classes[0]
        instance = tool_class()

        # Verify required methods exist
        assert hasattr(instance, "name")
        assert hasattr(instance, "description")
        assert hasattr(instance, "input_schema")
        assert hasattr(instance, "execute_tool")

        # Verify methods are callable
        assert callable(getattr(instance, "execute_tool"))

        # Verify property methods work
        assert isinstance(instance.name, str)
        assert isinstance(instance.description, str)
        assert isinstance(instance.input_schema, dict)

    def test_class_inheritance_verification(self, monkeypatch):
        """Test that created classes properly inherit from YamlToolBase."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "inheritance_test": {
                    "description": "Inheritance test",
                    "inputSchema": {"type": "object"}
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        tool_class = classes[0]

        # Verify inheritance chain
        assert issubclass(tool_class, YamlToolBase)
        assert issubclass(tool_class, ToolInterface)

        # Verify MRO (Method Resolution Order)
        mro = tool_class.__mro__
        assert YamlToolBase in mro
        assert ToolInterface in mro

        # Verify instance inheritance
        instance = tool_class()
        assert isinstance(instance, YamlToolBase)
        assert isinstance(instance, ToolInterface)


class TestIntegrationWithPluginSystem:
    """Test cases for integration with the plugin system."""

    def test_registry_integration_testing(self, monkeypatch):
        """Test integration with plugin registry."""
        # Use a clean registry for testing
        from mcp_tools.plugin import PluginRegistry
        test_registry = PluginRegistry()
        test_registry.clear()

        monkeypatch.setattr("mcp_tools.yaml_tools.registry", test_registry)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "registry_integration": {
                    "description": "Registry integration test",
                    "inputSchema": {"type": "object"}
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        # Verify tool is in registry
        assert "registry_integration" in test_registry.tools
        assert len(test_registry.tools) == 1

        # Verify tool can be retrieved from registry
        tool_instance = test_registry.get_tool_instance("registry_integration")
        assert tool_instance is not None
        assert tool_instance.name == "registry_integration"

    def test_tool_discovery_and_enumeration(self, monkeypatch):
        """Test tool discovery and enumeration through registry."""
        from mcp_tools.plugin import PluginRegistry
        test_registry = PluginRegistry()
        test_registry.clear()

        monkeypatch.setattr("mcp_tools.yaml_tools.registry", test_registry)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "discovery_tool_1": {"description": "First tool", "inputSchema": {"type": "object"}},
                "discovery_tool_2": {"description": "Second tool", "inputSchema": {"type": "object"}},
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        # Test enumeration
        all_tools = test_registry.get_all_tools()
        assert len(all_tools) == 2

        tool_names = [tool.__name__ for tool in all_tools]
        assert "YamlTool_discovery_tool_1" in tool_names
        assert "YamlTool_discovery_tool_2" in tool_names

    def test_source_filtering_and_management(self, monkeypatch):
        """Test source filtering and management."""
        from mcp_tools.plugin import PluginRegistry
        test_registry = PluginRegistry()
        test_registry.clear()

        monkeypatch.setattr("mcp_tools.yaml_tools.registry", test_registry)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "source_filter_test": {
                    "description": "Source filter test",
                    "inputSchema": {"type": "object"}
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        # Test source filtering
        yaml_tools = test_registry.get_tools_by_source("yaml")
        assert len(yaml_tools) == 1
        assert yaml_tools[0].__name__ == "YamlTool_source_filter_test"

        code_tools = test_registry.get_tools_by_source("code")
        assert len(code_tools) == 0

    def test_dependency_injection_compatibility(self, monkeypatch):
        """Test compatibility with dependency injection system."""
        mock_injector = MagicMock()
        mock_command_executor = MagicMock()
        mock_injector.get_tool_instance.return_value = mock_command_executor

        monkeypatch.setattr("mcp_tools.yaml_tools.injector", mock_injector)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", lambda **kw: lambda cls: cls)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "injection_test": {
                    "description": "Dependency injection test",
                    "inputSchema": {"type": "object"}
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        tool_class = classes[0]
        instance = tool_class()

        # Verify dependency injection was attempted
        mock_injector.get_tool_instance.assert_called_with("command_executor")
        assert instance._command_executor == mock_command_executor


class TestErrorHandlingAndEdgeCases:
    """Test cases for error handling during class creation."""

    def test_class_creation_with_invalid_tool_data(self, monkeypatch, caplog):
        """Test error handling when tool data is invalid."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        # Invalid tool data - missing required fields
        yaml_data = {
            "tools": {
                "invalid_tool": {
                    # Missing description and inputSchema
                    "type": "script"
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            caplog.set_level(logging.ERROR)
            classes = load_yaml_tools()

        # Verify error handling
        assert len(classes) == 0
        assert any("validation" in record.message.lower() for record in caplog.records)

    def test_class_creation_with_malformed_schema(self, monkeypatch, caplog):
        """Test error handling with malformed input schema."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "malformed_schema": {
                    "description": "Tool with malformed schema",
                    "inputSchema": "not_a_dict"  # Should be a dict
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            caplog.set_level(logging.ERROR)
            classes = load_yaml_tools()

        assert len(classes) == 0
        assert any("validation" in record.message.lower() for record in caplog.records)

    def test_instantiation_failure_handling(self, monkeypatch, caplog):
        """Test handling of instantiation failures during validation."""
        # Mock register_tool
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "instantiation_failure": {
                    "description": "This will fail instantiation",
                    "inputSchema": {"type": "object"}
                }
            }
        }

        # Mock YamlToolBase.__init__ to raise an exception
        original_init = YamlToolBase.__init__
        def failing_init(self, *args, **kwargs):
            raise Exception("Instantiation failed")

        with patch.object(YamlToolBase, "__init__", failing_init):
            with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
                caplog.set_level(logging.ERROR)
                classes = load_yaml_tools()

        # Verify error was handled
        assert len(classes) == 0
        assert any("instantiation" in record.message.lower() for record in caplog.records)

    def test_disabled_tools_handling(self, monkeypatch):
        """Test that disabled tools are not processed."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "enabled_tool": {
                    "description": "This tool is enabled",
                    "inputSchema": {"type": "object"},
                    "enabled": True
                },
                "disabled_tool": {
                    "description": "This tool is disabled",
                    "inputSchema": {"type": "object"},
                    "enabled": False
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        # Only enabled tool should be processed
        assert len(classes) == 1
        instance = classes[0]()
        assert instance.name == "enabled_tool"

    def test_empty_tools_section_handling(self, monkeypatch):
        """Test handling of empty tools section."""
        mock_register = MagicMock(return_value=lambda cls: cls)
        monkeypatch.setattr("mcp_tools.yaml_tools.register_tool", mock_register)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {"tools": {}}

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        assert len(classes) == 0

    def test_yaml_loading_failure_handling(self, monkeypatch, caplog):
        """Test handling of YAML loading failures."""
        monkeypatch.setattr(config, "register_yaml_tools", True)

        # Mock _load_yaml_from_locations to raise an exception
        with patch.object(YamlToolBase, "_load_yaml_from_locations", side_effect=Exception("YAML load failed")):
            caplog.set_level(logging.ERROR)
            classes = load_yaml_tools()

        assert len(classes) == 0
        assert any("YAML load failed" in record.message for record in caplog.records)


class TestCoverageAndIntegration:
    """Test cases to ensure comprehensive coverage of class creation logic."""

    def test_complete_workflow_integration(self, monkeypatch):
        """Test the complete workflow from YAML to registered class."""
        from mcp_tools.plugin import PluginRegistry
        test_registry = PluginRegistry()
        test_registry.clear()

        monkeypatch.setattr("mcp_tools.yaml_tools.registry", test_registry)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "complete_workflow": {
                    "description": "Complete workflow test",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"input": {"type": "string"}},
                        "required": ["input"]
                    },
                    "type": "script",
                    "custom_property": "custom_value"
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        # Verify complete workflow
        assert len(classes) == 1
        
        # Verify class creation
        tool_class = classes[0]
        assert tool_class.__name__ == "YamlTool_complete_workflow"
        assert issubclass(tool_class, YamlToolBase)
        
        # Verify class attributes
        assert tool_class._tool_name == "complete_workflow"
        assert tool_class._tool_data["custom_property"] == "custom_value"
        
        # Verify instantiation
        instance = tool_class()
        assert instance.name == "complete_workflow"
        assert instance.description == "Complete workflow test"
        assert instance._tool_type == "script"
        
        # Verify registry integration
        assert "complete_workflow" in test_registry.tools
        assert test_registry.get_tool_sources()["complete_workflow"] == "yaml"
        
        # Verify tool can be retrieved and used
        retrieved_instance = test_registry.get_tool_instance("complete_workflow")
        assert retrieved_instance is not None
        assert retrieved_instance.name == "complete_workflow"

    def test_multiple_tools_with_different_configurations(self, monkeypatch):
        """Test handling multiple tools with different configurations."""
        from mcp_tools.plugin import PluginRegistry
        test_registry = PluginRegistry()
        test_registry.clear()

        monkeypatch.setattr("mcp_tools.yaml_tools.registry", test_registry)
        monkeypatch.setattr(config, "register_yaml_tools", True)

        yaml_data = {
            "tools": {
                "simple_tool": {
                    "description": "Simple tool",
                    "inputSchema": {"type": "object"}
                },
                "complex_tool": {
                    "description": "Complex tool with many properties",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "param1": {"type": "string"},
                            "param2": {"type": "integer"},
                            "param3": {"type": "boolean"}
                        },
                        "required": ["param1", "param2"]
                    },
                    "type": "task",
                    "timeout": 30,
                    "retries": 3
                },
                "minimal_tool": {
                    "description": "Minimal configuration",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            }
        }

        with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
            classes = load_yaml_tools()

        # Verify all tools were created
        assert len(classes) == 3
        
        # Verify each tool has correct configuration
        instances = [cls() for cls in classes]
        tool_names = [inst.name for inst in instances]
        
        assert "simple_tool" in tool_names
        assert "complex_tool" in tool_names
        assert "minimal_tool" in tool_names
        
        # Verify complex tool has additional properties
        complex_instance = next(inst for inst in instances if inst.name == "complex_tool")
        assert complex_instance._tool_data["timeout"] == 30
        assert complex_instance._tool_data["retries"] == 3
        assert complex_instance._tool_type == "task"
        
        # Verify all are registered correctly
        assert len(test_registry.tools) == 3
        yaml_tools = test_registry.get_tools_by_source("yaml")
        assert len(yaml_tools) == 3 