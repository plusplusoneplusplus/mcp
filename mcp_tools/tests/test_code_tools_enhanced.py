"""Enhanced comprehensive test coverage for all code-based tools.

This module provides enhanced testing of all code-based tools using
improved fixtures and more detailed validation.
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, List, Type
from unittest.mock import patch, MagicMock, AsyncMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import from mcp_tools package
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import registry, discover_and_register_tools
from mcp_tools.dependency import injector
from mcp_tools.plugin_config import config

# Import test fixtures
from fixtures.test_fixtures import (
    mock_external_dependencies,
    sample_tool_arguments,
    generate_tool_specific_args,
    get_tool_category,
    ToolTestResult
)

# Configure logger for tests
logger = logging.getLogger(__name__)


@pytest.fixture
def clean_registry():
    """Fixture to provide a clean registry for each test."""
    # Save the original registry state
    original_tools = registry.tools.copy()
    original_instances = registry.instances.copy()
    original_yaml_tool_names = registry.yaml_tool_names.copy()
    original_tool_sources = registry.tool_sources.copy()
    original_discovered_paths = registry.discovered_paths.copy()

    # Clear the registry
    registry.clear()

    yield registry

    # Restore the original registry state
    registry.tools = original_tools
    registry.instances = original_instances
    registry.yaml_tool_names = original_yaml_tool_names
    registry.tool_sources = original_tool_sources
    registry.discovered_paths = original_discovered_paths


@pytest.fixture
def clean_injector():
    """Fixture to provide a clean dependency injector for each test."""
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

    # Enable only code tools for these tests
    config.register_code_tools = True
    config.register_yaml_tools = False
    config.yaml_overrides_code = False

    yield config

    # Restore original config
    config.register_code_tools = original_register_code_tools
    config.register_yaml_tools = original_register_yaml_tools
    config.yaml_overrides_code = original_yaml_overrides_code


class TestEnhancedCodeToolsCoverage:
    """Enhanced comprehensive test coverage for code-based tools."""

    def test_comprehensive_tool_validation(self, clean_registry, clean_injector, mock_config, mock_external_dependencies):
        """Comprehensive validation of all code-based tools."""
        # Discover and register tools
        discover_and_register_tools()

        # Get all code-based tools
        code_tools = registry.get_tools_by_source("code")

        # Initialize test result tracker
        test_results = ToolTestResult()

        logger.info(f"Starting comprehensive validation of {len(code_tools)} code-based tools")

        for tool_class in code_tools:
            try:
                # Test instantiation
                instance = tool_class()
                tool_name = instance.name
                category = get_tool_category(tool_name)

                # Test 1: Basic instantiation
                test_results.add_result(
                    tool_name=tool_name,
                    tool_class=tool_class.__name__,
                    test_type="instantiation",
                    success=True,
                    category=category
                )

                # Test 2: Interface compliance
                interface_valid = all([
                    hasattr(instance, 'name'),
                    hasattr(instance, 'description'),
                    hasattr(instance, 'input_schema'),
                    hasattr(instance, 'execute_tool')
                ])

                test_results.add_result(
                    tool_name=tool_name,
                    tool_class=tool_class.__name__,
                    test_type="interface_compliance",
                    success=interface_valid,
                    error=None if interface_valid else "Missing required interface methods",
                    category=category
                )

                # Test 3: Metadata validation
                try:
                    name = instance.name
                    description = instance.description
                    input_schema = instance.input_schema

                    metadata_valid = (
                        isinstance(name, str) and len(name.strip()) > 0 and
                        isinstance(description, str) and len(description.strip()) > 0 and
                        isinstance(input_schema, dict) and "type" in input_schema
                    )

                    test_results.add_result(
                        tool_name=tool_name,
                        tool_class=tool_class.__name__,
                        test_type="metadata_validation",
                        success=metadata_valid,
                        error=None if metadata_valid else "Invalid metadata format",
                        category=category
                    )

                except Exception as e:
                    test_results.add_result(
                        tool_name=tool_name,
                        tool_class=tool_class.__name__,
                        test_type="metadata_validation",
                        success=False,
                        error=f"Metadata access error: {str(e)}",
                        category=category
                    )

                # Test 4: Registry integration
                try:
                    registry_instance = registry.get_tool_instance(tool_name)
                    registry_valid = (
                        registry_instance is not None and
                        hasattr(registry_instance, 'name') and
                        registry_instance.name == tool_name
                    )

                    test_results.add_result(
                        tool_name=tool_name,
                        tool_class=tool_class.__name__,
                        test_type="registry_integration",
                        success=registry_valid,
                        error=None if registry_valid else "Registry integration failed",
                        category=category
                    )

                except Exception as e:
                    test_results.add_result(
                        tool_name=tool_name,
                        tool_class=tool_class.__name__,
                        test_type="registry_integration",
                        success=False,
                        error=f"Registry error: {str(e)}",
                        category=category
                    )

            except Exception as e:
                # Failed instantiation
                test_results.add_result(
                    tool_name="unknown",
                    tool_class=tool_class.__name__,
                    test_type="instantiation",
                    success=False,
                    error=f"Instantiation failed: {str(e)}",
                    category="unknown"
                )

        # Print comprehensive summary
        test_results.print_summary(logger)

        # Assert overall success criteria
        summary = test_results.get_summary()
        assert summary['total'] > 0, "No tools were tested"
        assert summary['success_rate'] >= 0.8, f"Success rate too low: {summary['success_rate']:.1%}"

    @pytest.mark.asyncio
    async def test_enhanced_tool_execution(self, clean_registry, clean_injector, mock_config,
                                         mock_external_dependencies, sample_tool_arguments):
        """Enhanced testing of tool execution with category-specific arguments."""
        # Discover and register tools
        discover_and_register_tools()

        # Get all code-based tools
        code_tools = registry.get_tools_by_source("code")

        # Initialize test result tracker
        test_results = ToolTestResult()

        logger.info(f"Starting enhanced execution testing of {len(code_tools)} code-based tools")

        for tool_class in code_tools:
            try:
                instance = tool_class()
                tool_name = instance.name
                category = get_tool_category(tool_name)

                # Generate tool-specific arguments
                input_schema = instance.input_schema
                test_args = generate_tool_specific_args(tool_name, input_schema)

                logger.debug(f"Testing {tool_name} ({category}) with args: {test_args}")

                # Execute the tool
                result = await instance.execute_tool(test_args)

                # Validate result format
                result_valid = isinstance(result, (dict, str, int, float, bool, list))

                test_results.add_result(
                    tool_name=tool_name,
                    tool_class=tool_class.__name__,
                    test_type="execution",
                    success=result_valid,
                    error=None if result_valid else f"Invalid result type: {type(result)}",
                    category=category,
                    result_type=type(result).__name__,
                    args_used=test_args
                )

                # Additional validation for dict results
                if isinstance(result, dict):
                    has_success_indicator = any(key in result for key in ['success', 'status', 'error'])
                    test_results.add_result(
                        tool_name=tool_name,
                        tool_class=tool_class.__name__,
                        test_type="result_format",
                        success=has_success_indicator,
                        error=None if has_success_indicator else "Dict result missing success/status/error indicator",
                        category=category
                    )

            except Exception as e:
                test_results.add_result(
                    tool_name=getattr(instance, 'name', 'unknown') if 'instance' in locals() else 'unknown',
                    tool_class=tool_class.__name__,
                    test_type="execution",
                    success=False,
                    error=f"Execution failed: {str(e)}",
                    category=get_tool_category(getattr(instance, 'name', 'unknown') if 'instance' in locals() else 'unknown')
                )

        # Print comprehensive summary
        test_results.print_summary(logger)

        # Assert execution success criteria
        summary = test_results.get_summary()
        execution_stats = summary['by_test_type'].get('execution', {'successful': 0, 'total': 1})
        execution_rate = execution_stats['successful'] / execution_stats['total']

        assert execution_rate >= 0.7, f"Execution success rate too low: {execution_rate:.1%}"

    def test_tool_categorization_and_coverage(self, clean_registry, clean_injector, mock_config):
        """Test tool categorization and ensure coverage across different categories."""
        # Discover and register tools
        discover_and_register_tools()

        # Get all code-based tools
        code_tools = registry.get_tools_by_source("code")

        # Categorize tools
        categories = {}
        for tool_class in code_tools:
            instance = tool_class()
            tool_name = instance.name
            category = get_tool_category(tool_name)

            if category not in categories:
                categories[category] = []
            categories[category].append(tool_name)

        logger.info("Tool categorization results:")
        for category, tools in categories.items():
            logger.info(f"  {category}: {len(tools)} tools - {tools}")

        # Verify we have tools in major categories
        expected_categories = ['browser', 'command', 'time']
        for expected_cat in expected_categories:
            assert expected_cat in categories, f"No tools found in expected category: {expected_cat}"
            assert len(categories[expected_cat]) > 0, f"Empty category: {expected_cat}"

        # Verify total coverage
        total_tools = sum(len(tools) for tools in categories.values())
        assert total_tools >= 10, f"Expected at least 10 tools, found {total_tools}"

    def test_dependency_injection_integration(self, clean_registry, clean_injector, mock_config):
        """Test integration with dependency injection system."""
        # Discover and register tools
        discover_and_register_tools()

        # Resolve dependencies
        injector.resolve_all_dependencies()

        # Get all instances through dependency injection
        all_instances = injector.get_filtered_instances()

        logger.info(f"Dependency injection created {len(all_instances)} tool instances")

        # Verify instances are valid
        for tool_name, instance in all_instances.items():
            assert hasattr(instance, 'name'), f"Instance {tool_name} missing 'name' property"
            assert hasattr(instance, 'description'), f"Instance {tool_name} missing 'description' property"
            assert hasattr(instance, 'input_schema'), f"Instance {tool_name} missing 'input_schema' property"
            assert hasattr(instance, 'execute_tool'), f"Instance {tool_name} missing 'execute_tool' method"
            assert instance.name == tool_name, f"Instance name mismatch: {instance.name} != {tool_name}"

        # Verify consistency with registry
        registry_tools = registry.get_tools_by_source("code")
        registry_tool_names = {tool().name for tool in registry_tools}
        injector_tool_names = set(all_instances.keys())

        # All injector tools should be in registry
        assert injector_tool_names.issubset(registry_tool_names), \
            f"Injector has tools not in registry: {injector_tool_names - registry_tool_names}"

    def test_tool_schema_validation(self, clean_registry, clean_injector, mock_config):
        """Test detailed validation of tool input schemas."""
        # Discover and register tools
        discover_and_register_tools()

        # Get all code-based tools
        code_tools = registry.get_tools_by_source("code")

        schema_validation_results = []

        for tool_class in code_tools:
            try:
                instance = tool_class()
                tool_name = instance.name
                input_schema = instance.input_schema

                # Validate schema structure
                schema_issues = []

                if not isinstance(input_schema, dict):
                    schema_issues.append("Schema is not a dictionary")
                else:
                    # Check required fields
                    if "type" not in input_schema:
                        schema_issues.append("Missing 'type' field")

                    # Check properties structure
                    if "properties" in input_schema:
                        properties = input_schema["properties"]
                        if not isinstance(properties, dict):
                            schema_issues.append("'properties' is not a dictionary")
                        else:
                            # Validate each property
                            for prop_name, prop_schema in properties.items():
                                if not isinstance(prop_schema, dict):
                                    schema_issues.append(f"Property '{prop_name}' schema is not a dictionary")
                                elif "type" not in prop_schema and "enum" not in prop_schema:
                                    schema_issues.append(f"Property '{prop_name}' missing type or enum")

                    # Check required array
                    if "required" in input_schema:
                        required = input_schema["required"]
                        if not isinstance(required, list):
                            schema_issues.append("'required' is not a list")

                schema_validation_results.append({
                    "tool_name": tool_name,
                    "tool_class": tool_class.__name__,
                    "valid": len(schema_issues) == 0,
                    "issues": schema_issues
                })

            except Exception as e:
                schema_validation_results.append({
                    "tool_name": "unknown",
                    "tool_class": tool_class.__name__,
                    "valid": False,
                    "issues": [f"Schema access error: {str(e)}"]
                })

        # Log results
        valid_schemas = [r for r in schema_validation_results if r["valid"]]
        invalid_schemas = [r for r in schema_validation_results if not r["valid"]]

        logger.info(f"Schema validation results: {len(valid_schemas)} valid, {len(invalid_schemas)} invalid")

        if invalid_schemas:
            logger.warning("Invalid schemas found:")
            for result in invalid_schemas:
                logger.warning(f"  {result['tool_name']} ({result['tool_class']}): {result['issues']}")

        # Assert schema quality
        schema_success_rate = len(valid_schemas) / len(schema_validation_results)
        assert schema_success_rate >= 0.9, f"Schema validation success rate too low: {schema_success_rate:.1%}"


def test_final_comprehensive_summary(clean_registry, clean_injector, mock_config):
    """Provide a final comprehensive summary of all code tools testing."""
    # Discover and register tools
    discover_and_register_tools()

    # Get comprehensive information
    code_tools = registry.get_tools_by_source("code")
    tool_sources = registry.get_tool_sources()

    # Categorize tools
    categories = {}
    tool_details = []

    for tool_class in code_tools:
        instance = tool_class()
        tool_name = instance.name
        category = get_tool_category(tool_name)

        if category not in categories:
            categories[category] = []
        categories[category].append(tool_name)

        tool_details.append({
            'name': tool_name,
            'class': tool_class.__name__,
            'category': category,
            'description': instance.description[:100] + "..." if len(instance.description) > 100 else instance.description,
            'has_operation': 'operation' in instance.input_schema.get('properties', {}),
            'required_params': instance.input_schema.get('required', [])
        })

    # Generate final summary
    logger.info("=" * 80)
    logger.info("FINAL COMPREHENSIVE CODE TOOLS TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total code-based tools discovered and tested: {len(code_tools)}")
    logger.info(f"Source distribution: {len([s for s in tool_sources.values() if s == 'code'])} code, {len([s for s in tool_sources.values() if s == 'yaml'])} yaml")

    logger.info(f"\nTools by category:")
    for category, tools in sorted(categories.items()):
        logger.info(f"  {category.upper()}: {len(tools)} tools")
        for tool in sorted(tools):
            logger.info(f"    - {tool}")

    logger.info(f"\nDetailed tool information:")
    for tool in sorted(tool_details, key=lambda x: (x['category'], x['name'])):
        logger.info(f"  {tool['name']} ({tool['class']})")
        logger.info(f"    Category: {tool['category']}")
        logger.info(f"    Description: {tool['description']}")
        logger.info(f"    Has operation param: {tool['has_operation']}")
        logger.info(f"    Required params: {tool['required_params']}")
        logger.info("")

    logger.info("=" * 80)

    # Final assertions
    assert len(code_tools) >= 10, f"Expected at least 10 code tools, found {len(code_tools)}"
    assert len(categories) >= 5, f"Expected at least 5 tool categories, found {len(categories)}"
    assert all(len(tools) > 0 for tools in categories.values()), "Found empty tool categories"


def get_tool_category(tool_name: str) -> str:
    """Determine the category of a tool based on its name."""
    if 'browser' in tool_name.lower() or 'capture' in tool_name.lower():
        return 'browser'
    elif 'command' in tool_name.lower() or 'executor' in tool_name.lower():
        return 'command'
    elif 'time' in tool_name.lower():
        return 'time'
    elif 'git' in tool_name.lower():
        return 'git'
    elif 'azure' in tool_name.lower():
        return 'azure'
    elif 'knowledge' in tool_name.lower():
        return 'knowledge'
    elif 'summarizer' in tool_name.lower():
        return 'summarizer'
    elif 'kusto' in tool_name.lower():
        return 'kusto'
    else:
        return 'other'


def test_enhanced_tool_discovery_and_categorization(clean_registry, clean_injector, mock_config):
    """Test enhanced tool discovery with categorization."""
    discover_and_register_tools()
    code_tools = registry.get_tools_by_source("code")

    # Categorize tools
    categories = {}
    for tool_class in code_tools:
        instance = tool_class()
        tool_name = instance.name
        category = get_tool_category(tool_name)

        if category not in categories:
            categories[category] = []
        categories[category].append(tool_name)

    logger.info("Enhanced tool categorization results:")
    for category, tools in categories.items():
        logger.info(f"  {category}: {len(tools)} tools - {tools}")

    # Assertions
    assert len(code_tools) >= 10, f"Expected at least 10 tools, found {len(code_tools)}"
    assert len(categories) >= 5, f"Expected at least 5 categories, found {len(categories)}"

    # Verify major categories exist
    expected_categories = ['browser', 'command', 'time']
    for expected_cat in expected_categories:
        assert expected_cat in categories, f"Missing expected category: {expected_cat}"


@pytest.mark.asyncio
async def test_enhanced_tool_execution_by_category(clean_registry, clean_injector, mock_config):
    """Test tool execution with category-specific handling."""
    discover_and_register_tools()
    code_tools = registry.get_tools_by_source("code")

    execution_results = {}

    with patch('subprocess.run') as mock_subprocess, \
         patch('asyncio.create_subprocess_shell') as mock_async_subprocess, \
         patch('mcp_tools.browser.factory.BrowserClientFactory.create_client') as mock_browser:

        # Configure mocks
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="mock output", stderr="")
        mock_async_subprocess.return_value = AsyncMock()
        mock_browser.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_browser.return_value.__aexit__ = AsyncMock(return_value=None)

        for tool_class in code_tools:
            try:
                instance = tool_class()
                tool_name = instance.name
                category = get_tool_category(tool_name)

                # Generate category-specific arguments
                test_args = generate_category_args(category, instance.input_schema)

                # Execute tool
                result = await instance.execute_tool(test_args)

                if category not in execution_results:
                    execution_results[category] = {'success': 0, 'total': 0}

                execution_results[category]['total'] += 1
                if isinstance(result, (dict, str, int, float, bool, list)):
                    execution_results[category]['success'] += 1

            except Exception as e:
                category = get_tool_category(getattr(instance, 'name', 'unknown') if 'instance' in locals() else 'unknown')
                if category not in execution_results:
                    execution_results[category] = {'success': 0, 'total': 0}
                execution_results[category]['total'] += 1

    # Log results by category
    logger.info("Execution results by category:")
    for category, stats in execution_results.items():
        success_rate = stats['success'] / stats['total'] if stats['total'] > 0 else 0
        logger.info(f"  {category}: {stats['success']}/{stats['total']} ({success_rate:.1%})")

    # Assert overall success
    total_success = sum(stats['success'] for stats in execution_results.values())
    total_tests = sum(stats['total'] for stats in execution_results.values())
    overall_rate = total_success / total_tests if total_tests > 0 else 0

    assert overall_rate >= 0.7, f"Overall execution success rate too low: {overall_rate:.1%}"


def generate_category_args(category: str, input_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Generate category-specific test arguments."""
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    args = {}

    # Add required arguments
    for prop_name, prop_schema in properties.items():
        if prop_name in required:
            prop_type = prop_schema.get("type", "string")
            default_value = prop_schema.get("default")
            enum_values = prop_schema.get("enum")

            if default_value is not None:
                args[prop_name] = default_value
            elif enum_values:
                args[prop_name] = enum_values[0]
            elif prop_type == "string":
                args[prop_name] = get_category_string_value(prop_name, category)
            elif prop_type == "integer":
                args[prop_name] = 1
            elif prop_type == "number":
                args[prop_name] = 1.0
            elif prop_type == "boolean":
                args[prop_name] = True
            elif prop_type == "array":
                args[prop_name] = []
            elif prop_type == "object":
                args[prop_name] = {}

    # Add common operation if present
    if "operation" in properties and "operation" not in args:
        args["operation"] = get_category_operation(category)

    return args


def get_category_string_value(prop_name: str, category: str) -> str:
    """Get category-specific string values."""
    if prop_name == "command":
        return "echo 'test'"
    elif prop_name == "url":
        return "https://example.com"
    elif prop_name == "operation":
        return get_category_operation(category)
    elif prop_name in ["repo_path", "path", "directory"]:
        return "/tmp/test"
    elif prop_name in ["organization", "org"]:
        return "test-org"
    elif prop_name in ["project", "proj"]:
        return "test-project"
    elif prop_name in ["query", "search"]:
        return "test query"
    elif prop_name in ["collection", "index"]:
        return "test-collection"
    elif prop_name in ["timezone", "tz"]:
        return "UTC"
    else:
        return "test_value"


def get_category_operation(category: str) -> str:
    """Get default operation for category."""
    operation_map = {
        'browser': 'get_page_html',
        'command': 'execute',
        'time': 'get_time',
        'git': 'status',
        'azure': 'list',
        'knowledge': 'search',
        'summarizer': 'summarize',
        'kusto': 'query'
    }
    return operation_map.get(category, 'test')


def test_tool_schema_quality(clean_registry, clean_injector, mock_config):
    """Test the quality of tool input schemas."""
    discover_and_register_tools()
    code_tools = registry.get_tools_by_source("code")

    schema_quality_results = []

    for tool_class in code_tools:
        try:
            instance = tool_class()
            tool_name = instance.name
            input_schema = instance.input_schema

            quality_score = 0
            max_score = 5

            # Check basic structure (1 point)
            if isinstance(input_schema, dict) and "type" in input_schema:
                quality_score += 1

            # Check properties exist (1 point)
            if "properties" in input_schema and isinstance(input_schema["properties"], dict):
                quality_score += 1

            # Check property descriptions (1 point)
            properties = input_schema.get("properties", {})
            if properties and all("description" in prop for prop in properties.values() if isinstance(prop, dict)):
                quality_score += 1

            # Check required array (1 point)
            if "required" in input_schema and isinstance(input_schema["required"], list):
                quality_score += 1

            # Check operation parameter (1 point)
            if "operation" in properties:
                quality_score += 1

            schema_quality_results.append({
                "tool_name": tool_name,
                "quality_score": quality_score,
                "max_score": max_score,
                "percentage": (quality_score / max_score) * 100
            })

        except Exception as e:
            schema_quality_results.append({
                "tool_name": "unknown",
                "quality_score": 0,
                "max_score": 5,
                "percentage": 0,
                "error": str(e)
            })

    # Calculate average quality
    avg_quality = sum(r["percentage"] for r in schema_quality_results) / len(schema_quality_results)

    logger.info(f"Schema quality results (average: {avg_quality:.1f}%):")
    for result in sorted(schema_quality_results, key=lambda x: x["percentage"], reverse=True):
        logger.info(f"  {result['tool_name']}: {result['quality_score']}/{result['max_score']} ({result['percentage']:.1f}%)")

    # Assert quality standards
    assert avg_quality >= 70, f"Average schema quality too low: {avg_quality:.1f}%"
    high_quality_tools = [r for r in schema_quality_results if r["percentage"] >= 80]
    assert len(high_quality_tools) >= len(schema_quality_results) * 0.6, "Not enough high-quality schemas"


def test_comprehensive_final_summary(clean_registry, clean_injector, mock_config):
    """Provide comprehensive final summary of all testing."""
    discover_and_register_tools()
    code_tools = registry.get_tools_by_source("code")

    # Collect comprehensive data
    tool_data = []
    categories = {}

    for tool_class in code_tools:
        instance = tool_class()
        tool_name = instance.name
        category = get_tool_category(tool_name)

        if category not in categories:
            categories[category] = []
        categories[category].append(tool_name)

        tool_data.append({
            'name': tool_name,
            'class': tool_class.__name__,
            'category': category,
            'description_length': len(instance.description),
            'has_operation': 'operation' in instance.input_schema.get('properties', {}),
            'required_count': len(instance.input_schema.get('required', [])),
            'property_count': len(instance.input_schema.get('properties', {}))
        })

    # Generate comprehensive summary
    logger.info("=" * 80)
    logger.info("COMPREHENSIVE CODE TOOLS TESTING SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total tools tested: {len(code_tools)}")
    logger.info(f"Categories found: {len(categories)}")

    logger.info("\nTools by category:")
    for category, tools in sorted(categories.items()):
        logger.info(f"  {category.upper()}: {len(tools)} tools")
        for tool in sorted(tools):
            logger.info(f"    - {tool}")

    logger.info("\nTool statistics:")
    avg_desc_length = sum(t['description_length'] for t in tool_data) / len(tool_data)
    tools_with_operation = len([t for t in tool_data if t['has_operation']])
    avg_required_params = sum(t['required_count'] for t in tool_data) / len(tool_data)
    avg_total_params = sum(t['property_count'] for t in tool_data) / len(tool_data)

    logger.info(f"  Average description length: {avg_desc_length:.1f} characters")
    logger.info(f"  Tools with operation parameter: {tools_with_operation}/{len(tool_data)} ({tools_with_operation/len(tool_data):.1%})")
    logger.info(f"  Average required parameters: {avg_required_params:.1f}")
    logger.info(f"  Average total parameters: {avg_total_params:.1f}")

    logger.info("=" * 80)

    # Final comprehensive assertions
    assert len(code_tools) >= 15, f"Expected at least 15 tools, found {len(code_tools)}"
    assert len(categories) >= 6, f"Expected at least 6 categories, found {len(categories)}"
    assert tools_with_operation >= len(tool_data) * 0.5, f"Expected at least 50% of tools to have operation parameters, found {tools_with_operation}/{len(tool_data)} ({tools_with_operation/len(tool_data):.1%})"
    assert avg_desc_length >= 20, "Tool descriptions too short on average"
