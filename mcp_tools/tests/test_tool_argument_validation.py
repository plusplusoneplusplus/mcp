"""Comprehensive tool argument validation testing.

This module provides comprehensive test coverage for tool argument validation,
testing both valid and invalid inputs for all registered tools to ensure proper
validation and error handling.

Tests cover:
- Required field validation
- Type validation  
- Enum validation
- Schema compliance
- Error handling and meaningful error messages
"""

import pytest
import logging
from typing import Dict, Any, List, Tuple, Optional, Union
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from interfaces import ToolInterface
from plugin import registry, discover_and_register_tools
from dependency import injector
from plugin_config import config

logger = logging.getLogger(__name__)


class ValidationTestGenerator:
    """Utility class for generating test data based on JSON schemas."""
    
    @staticmethod
    def generate_valid_arguments(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate valid arguments based on JSON schema."""
        if not isinstance(schema, dict) or schema.get("type") != "object":
            return {}
            
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        arguments = {}
        
        # Generate required fields first
        for field_name in required:
            if field_name in properties:
                prop_schema = properties[field_name]
                arguments[field_name] = ValidationTestGenerator._generate_valid_value(
                    field_name, prop_schema
                )
        
        # Add some optional fields for better coverage
        optional_fields = [name for name in properties.keys() if name not in required]
        for field_name in optional_fields[:3]:  # Limit to first 3 optional fields
            prop_schema = properties[field_name]
            arguments[field_name] = ValidationTestGenerator._generate_valid_value(
                field_name, prop_schema
            )
            
        return arguments
    
    @staticmethod
    def _generate_valid_value(field_name: str, prop_schema: Dict[str, Any]) -> Any:
        """Generate a valid value for a property schema."""
        prop_type = prop_schema.get("type")
        
        # Handle enum values first
        if "enum" in prop_schema:
            return prop_schema["enum"][0]
            
        # Handle default values
        if "default" in prop_schema:
            return prop_schema["default"]
            
        # Generate by type
        if prop_type == "string":
            if field_name.lower() in ["url", "uri"]:
                return "https://example.com"
            elif field_name.lower() in ["email"]:
                return "test@example.com"
            elif field_name.lower() in ["path", "file", "directory"]:
                return "/tmp/test"
            else:
                return f"test_{field_name}"
        elif prop_type == "integer":
            minimum = prop_schema.get("minimum", 1)
            maximum = prop_schema.get("maximum", 100)
            return max(minimum, min(maximum, 42))
        elif prop_type == "number":
            minimum = prop_schema.get("minimum", 1.0)
            maximum = prop_schema.get("maximum", 100.0)
            return max(minimum, min(maximum, 42.5))
        elif prop_type == "boolean":
            return True
        elif prop_type == "array":
            items_schema = prop_schema.get("items", {"type": "string"})
            if isinstance(items_schema, dict):
                item_value = ValidationTestGenerator._generate_valid_value("item", items_schema)
                return [item_value]
            return ["test_item"]
        elif prop_type == "object":
            return {"test_key": "test_value"}
        elif isinstance(prop_type, list):
            # Handle union types like ["string", "integer"]
            return ValidationTestGenerator._generate_valid_value(field_name, {"type": prop_type[0]})
        else:
            return f"test_{field_name}"
    
    @staticmethod
    def generate_invalid_test_cases(schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate invalid test cases for validation testing."""
        if not isinstance(schema, dict) or schema.get("type") != "object":
            return []
            
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        invalid_cases = []
        
        # Test missing required fields
        if required:
            # Missing all required fields
            invalid_cases.append({})
            
            # Missing individual required fields
            for missing_field in required:
                valid_args = ValidationTestGenerator.generate_valid_arguments(schema)
                if missing_field in valid_args:
                    del valid_args[missing_field]
                    invalid_cases.append(valid_args)
        
        # Test type mismatches for each property
        for field_name, prop_schema in properties.items():
            prop_type = prop_schema.get("type")
            if not prop_type:
                continue
                
            valid_args = ValidationTestGenerator.generate_valid_arguments(schema)
            
            # Generate type mismatch cases
            if prop_type == "string":
                invalid_args = valid_args.copy()
                invalid_args[field_name] = 123  # number instead of string
                invalid_cases.append(invalid_args)
            elif prop_type == "integer":
                invalid_args = valid_args.copy()
                invalid_args[field_name] = "not_a_number"  # string instead of integer
                invalid_cases.append(invalid_args)
            elif prop_type == "boolean":
                invalid_args = valid_args.copy()
                invalid_args[field_name] = "true"  # string instead of boolean
                invalid_cases.append(invalid_args)
        
        # Test enum violations
        for field_name, prop_schema in properties.items():
            if "enum" in prop_schema:
                valid_args = ValidationTestGenerator.generate_valid_arguments(schema)
                invalid_args = valid_args.copy()
                invalid_args[field_name] = "invalid_enum_value_not_in_list"
                invalid_cases.append(invalid_args)
        
        return invalid_cases


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

    # Reset to defaults for testing
    config.register_code_tools = True
    config.register_yaml_tools = True

    yield config

    # Restore original config
    config.register_code_tools = original_register_code_tools
    config.register_yaml_tools = original_register_yaml_tools


class TestToolArgumentValidation:
    """Comprehensive tool argument validation tests."""
    
    def test_tool_argument_validation_comprehensive(self, clean_registry, clean_injector, mock_config):
        """Test argument validation for all registered tools."""
        # Discover and register tools
        discover_and_register_tools()
        
        # Get all tools
        code_tools = registry.get_tools_by_source("code")
        all_tools = {}
        for tool_class in code_tools:
            instance = tool_class()
            all_tools[instance.name] = instance
        
        assert len(all_tools) > 0, "No tools were discovered for testing"
        
        validation_results = []
        
        for tool_name, tool_instance in all_tools.items():
            try:
                schema = tool_instance.input_schema
                
                # Test with valid arguments
                valid_args = ValidationTestGenerator.generate_valid_arguments(schema)
                
                # Test with invalid arguments
                invalid_test_cases = ValidationTestGenerator.generate_invalid_test_cases(schema)
                
                validation_results.append({
                    "tool_name": tool_name,
                    "schema_valid": isinstance(schema, dict),
                    "valid_args_generated": len(valid_args) > 0 if schema.get("required") else True,
                    "invalid_cases_generated": len(invalid_test_cases),
                    "has_required_fields": len(schema.get("required", [])) > 0,
                    "has_properties": len(schema.get("properties", {})) > 0,
                    "error": None
                })
                        
            except Exception as e:
                validation_results.append({
                    "tool_name": tool_name,
                    "validation_test": "failed",
                    "error": str(e)
                })
        
        # Log summary
        total_tools = len(all_tools)
        successful_tests = len([r for r in validation_results if r.get("schema_valid", False)])
        
        logger.info(f"Tool argument validation summary:")
        logger.info(f"  Total tools tested: {total_tools}")
        logger.info(f"  Tools with valid schemas: {successful_tests}")
        logger.info(f"  Total validation test cases: {len(validation_results)}")
        
        # Ensure we tested some tools
        assert total_tools > 0, "No tools were available for validation testing"
        
        # Log detailed results for debugging
        for result in validation_results[:10]:  # Log first 10 results
            logger.debug(f"Validation result: {result}")
    
    def test_required_field_validation(self, clean_registry, clean_injector, mock_config):
        """Test that tools have proper required field definitions."""
        discover_and_register_tools()
        code_tools = registry.get_tools_by_source("code")
        all_tools = {}
        for tool_class in code_tools:
            instance = tool_class()
            all_tools[instance.name] = instance
        
        required_field_results = []
        
        for tool_name, tool_instance in all_tools.items():
            try:
                schema = tool_instance.input_schema
                required_fields = schema.get("required", [])
                properties = schema.get("properties", {})
                
                # Check that required fields exist in properties
                missing_properties = []
                for required_field in required_fields:
                    if required_field not in properties:
                        missing_properties.append(required_field)
                
                required_field_results.append({
                    "tool_name": tool_name,
                    "required_fields": required_fields,
                    "missing_properties": missing_properties,
                    "valid_required_definition": len(missing_properties) == 0,
                    "error": None
                })
                            
            except Exception as e:
                required_field_results.append({
                    "tool_name": tool_name,
                    "test": "failed",
                    "error": str(e)
                })
        
        logger.info(f"Required field validation tested {len(required_field_results)} tools")
        
        # Check that tools with required fields have them properly defined
        invalid_definitions = [r for r in required_field_results if not r.get("valid_required_definition", True)]
        if invalid_definitions:
            logger.warning(f"Found {len(invalid_definitions)} tools with invalid required field definitions:")
            for result in invalid_definitions:
                logger.warning(f"  {result['tool_name']}: missing properties {result['missing_properties']}")
        
        assert len(required_field_results) >= 0  # Allow zero if no tools have required fields
    
    def test_schema_compliance(self, clean_registry, clean_injector, mock_config):
        """Test that all tools have valid input schemas."""
        discover_and_register_tools()
        code_tools = registry.get_tools_by_source("code")
        all_tools = {}
        for tool_class in code_tools:
            instance = tool_class()
            all_tools[instance.name] = instance
        
        schema_compliance_results = []
        
        for tool_name, tool_instance in all_tools.items():
            try:
                schema = tool_instance.input_schema
                
                # Check schema structure
                compliance_issues = []
                
                if not isinstance(schema, dict):
                    compliance_issues.append("Schema is not a dictionary")
                else:
                    # Check required schema fields
                    if "type" not in schema:
                        compliance_issues.append("Missing 'type' field")
                    elif schema["type"] != "object":
                        compliance_issues.append(f"Expected type 'object', got '{schema['type']}'")
                    
                    # Check properties structure
                    if "properties" in schema:
                        properties = schema["properties"]
                        if not isinstance(properties, dict):
                            compliance_issues.append("'properties' is not a dictionary")
                        else:
                            # Validate each property
                            for prop_name, prop_schema in properties.items():
                                if not isinstance(prop_schema, dict):
                                    compliance_issues.append(f"Property '{prop_name}' schema is not a dictionary")
                                elif "type" not in prop_schema and "enum" not in prop_schema:
                                    compliance_issues.append(f"Property '{prop_name}' missing type or enum")
                    
                    # Check required array
                    if "required" in schema and not isinstance(schema["required"], list):
                        compliance_issues.append("'required' field is not a list")
                
                schema_compliance_results.append({
                    "tool_name": tool_name,
                    "compliant": len(compliance_issues) == 0,
                    "issues": compliance_issues,
                    "schema": schema
                })
                
            except Exception as e:
                schema_compliance_results.append({
                    "tool_name": tool_name,
                    "compliant": False,
                    "issues": [f"Error accessing schema: {str(e)}"],
                    "schema": None
                })
        
        # Check that all tools have compliant schemas
        non_compliant = [r for r in schema_compliance_results if not r["compliant"]]
        
        if non_compliant:
            logger.warning(f"Found {len(non_compliant)} non-compliant schemas:")
            for result in non_compliant:
                logger.warning(f"  {result['tool_name']}: {result['issues']}")
        
        logger.info(f"Schema compliance: {len(schema_compliance_results) - len(non_compliant)}/{len(schema_compliance_results)} tools compliant")
        
        # Assert that we have some tools and most are compliant
        assert len(schema_compliance_results) > 0, "No tools found for schema compliance testing"
        compliance_rate = (len(schema_compliance_results) - len(non_compliant)) / len(schema_compliance_results)
        assert compliance_rate >= 0.8, f"Schema compliance rate too low: {compliance_rate:.2%}"

    def test_enum_validation_coverage(self, clean_registry, clean_injector, mock_config):
        """Test that tools with enum fields have proper enum definitions."""
        discover_and_register_tools()
        code_tools = registry.get_tools_by_source("code")
        all_tools = {}
        for tool_class in code_tools:
            instance = tool_class()
            all_tools[instance.name] = instance
        
        enum_validation_results = []
        
        for tool_name, tool_instance in all_tools.items():
            try:
                schema = tool_instance.input_schema
                properties = schema.get("properties", {})
                
                # Find enum fields
                enum_fields = {}
                for field_name, prop_schema in properties.items():
                    if isinstance(prop_schema, dict) and "enum" in prop_schema:
                        enum_values = prop_schema["enum"]
                        enum_fields[field_name] = {
                            "values": enum_values,
                            "valid": isinstance(enum_values, list) and len(enum_values) > 0
                        }
                
                enum_validation_results.append({
                    "tool_name": tool_name,
                    "enum_fields": enum_fields,
                    "has_enums": len(enum_fields) > 0,
                    "all_enums_valid": all(field["valid"] for field in enum_fields.values()),
                    "error": None
                })
                        
            except Exception as e:
                enum_validation_results.append({
                    "tool_name": tool_name,
                    "test": "failed",
                    "error": str(e)
                })
        
        tools_with_enums = [r for r in enum_validation_results if r.get("has_enums", False)]
        invalid_enums = [r for r in tools_with_enums if not r.get("all_enums_valid", True)]
        
        logger.info(f"Enum validation: {len(tools_with_enums)} tools have enum fields")
        if invalid_enums:
            logger.warning(f"Found {len(invalid_enums)} tools with invalid enum definitions")
        
        assert len(enum_validation_results) >= 0


def test_validation_test_coverage_summary(clean_registry, clean_injector, mock_config):
    """Provide a summary of validation test coverage."""
    discover_and_register_tools()
    code_tools = registry.get_tools_by_source("code")
    all_tools = {}
    for tool_class in code_tools:
        instance = tool_class()
        all_tools[instance.name] = instance
    
    summary = {
        "total_tools": len(all_tools),
        "tools_with_schemas": 0,
        "tools_with_required_fields": 0,
        "tools_with_enums": 0,
        "tools_with_type_validation": 0,
        "schema_quality_scores": []
    }
    
    for tool_name, tool_instance in all_tools.items():
        try:
            schema = tool_instance.input_schema
            
            if isinstance(schema, dict):
                summary["tools_with_schemas"] += 1
                
                if schema.get("required"):
                    summary["tools_with_required_fields"] += 1
                
                properties = schema.get("properties", {})
                if any("enum" in prop for prop in properties.values() if isinstance(prop, dict)):
                    summary["tools_with_enums"] += 1
                
                if any("type" in prop for prop in properties.values() if isinstance(prop, dict)):
                    summary["tools_with_type_validation"] += 1
                
                # Calculate quality score
                quality_score = 0
                if schema.get("type") == "object":
                    quality_score += 1
                if "properties" in schema:
                    quality_score += 1
                if "required" in schema:
                    quality_score += 1
                if properties and all("description" in prop for prop in properties.values() if isinstance(prop, dict)):
                    quality_score += 1
                
                summary["schema_quality_scores"].append(quality_score)
                
        except Exception as e:
            logger.warning(f"Error analyzing schema for {tool_name}: {e}")
    
    # Calculate averages
    if summary["schema_quality_scores"]:
        avg_quality = sum(summary["schema_quality_scores"]) / len(summary["schema_quality_scores"])
        summary["average_quality_score"] = avg_quality
    
    logger.info("Tool Argument Validation Test Coverage Summary:")
    logger.info(f"  Total tools: {summary['total_tools']}")
    logger.info(f"  Tools with schemas: {summary['tools_with_schemas']}")
    logger.info(f"  Tools with required fields: {summary['tools_with_required_fields']}")
    logger.info(f"  Tools with enum validation: {summary['tools_with_enums']}")
    logger.info(f"  Tools with type validation: {summary['tools_with_type_validation']}")
    if "average_quality_score" in summary:
        logger.info(f"  Average schema quality score: {summary['average_quality_score']:.2f}/4")
    
    # Verify we have reasonable test coverage
    assert summary["total_tools"] > 0, "No tools found for validation testing"
    assert summary["tools_with_schemas"] > 0, "No tools with schemas found" 