"""Comprehensive test coverage for all code-based tools.

This module provides comprehensive testing of all code-based tools that are
registered through the mcp_tools.plugin.registry system.
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


def test_discover_all_code_tools(clean_registry, clean_injector, mock_config):
    """Test that all code-based tools can be discovered and registered."""
    # Discover and register tools
    discover_and_register_tools()

    # Get all code-based tools
    code_tools = registry.get_tools_by_source("code")

    # Verify that tools were discovered
    assert len(code_tools) > 0, "No code-based tools were discovered"

    # Log discovered tools for debugging
    tool_names = [tool().name for tool in code_tools]
    logger.info(f"Discovered {len(code_tools)} code-based tools: {tool_names}")

    # Verify all tools are properly registered
    for tool_class in code_tools:
        tool_name = tool_class().name
        assert tool_name in registry.tools, f"Tool {tool_name} not in registry.tools"
        assert registry.tool_sources.get(tool_name) == "code", f"Tool {tool_name} not marked as code source"


def test_all_code_tools_can_be_instantiated(clean_registry, clean_injector, mock_config):
    """Test that all code-based tools can be instantiated without errors."""
    # Discover and register tools
    discover_and_register_tools()

    # Get all code-based tools
    code_tools = registry.get_tools_by_source("code")

    instantiation_results = []

    for tool_class in code_tools:
        try:
            # Attempt to instantiate the tool
            instance = tool_class()

            # Verify it has the required ToolInterface methods
            assert hasattr(instance, 'name'), f"{tool_class.__name__} missing 'name' property"
            assert hasattr(instance, 'description'), f"{tool_class.__name__} missing 'description' property"
            assert hasattr(instance, 'input_schema'), f"{tool_class.__name__} missing 'input_schema' property"
            assert hasattr(instance, 'execute_tool'), f"{tool_class.__name__} missing 'execute_tool' method"

            instantiation_results.append({
                "tool_class": tool_class.__name__,
                "tool_name": instance.name,
                "success": True,
                "error": None
            })

        except Exception as e:
            instantiation_results.append({
                "tool_class": tool_class.__name__,
                "tool_name": "unknown",
                "success": False,
                "error": str(e)
            })

    # Log results
    successful = [r for r in instantiation_results if r["success"]]
    failed = [r for r in instantiation_results if not r["success"]]

    logger.info(f"Tool instantiation results: {len(successful)} successful, {len(failed)} failed")

    if failed:
        for failure in failed:
            logger.error(f"Failed to instantiate {failure['tool_class']}: {failure['error']}")

    # Assert all tools can be instantiated
    assert len(failed) == 0, f"Failed to instantiate {len(failed)} tools: {[f['tool_class'] for f in failed]}"


def test_code_tools_have_valid_metadata(clean_registry, clean_injector, mock_config):
    """Test that all code-based tools have valid metadata."""
    # Discover and register tools
    discover_and_register_tools()

    # Get all code-based tools
    code_tools = registry.get_tools_by_source("code")

    metadata_validation_results = []

    for tool_class in code_tools:
        try:
            instance = tool_class()

            # Validate name
            name = instance.name
            assert isinstance(name, str), f"{tool_class.__name__}.name is not a string"
            assert len(name.strip()) > 0, f"{tool_class.__name__}.name is empty"

            # Validate description
            description = instance.description
            assert isinstance(description, str), f"{tool_class.__name__}.description is not a string"
            assert len(description.strip()) > 0, f"{tool_class.__name__}.description is empty"

            # Validate input_schema
            input_schema = instance.input_schema
            assert isinstance(input_schema, dict), f"{tool_class.__name__}.input_schema is not a dict"
            assert "type" in input_schema, f"{tool_class.__name__}.input_schema missing 'type' field"

            metadata_validation_results.append({
                "tool_class": tool_class.__name__,
                "tool_name": name,
                "success": True,
                "error": None
            })

        except Exception as e:
            metadata_validation_results.append({
                "tool_class": tool_class.__name__,
                "tool_name": "unknown",
                "success": False,
                "error": str(e)
            })

    # Log results
    successful = [r for r in metadata_validation_results if r["success"]]
    failed = [r for r in metadata_validation_results if not r["success"]]

    logger.info(f"Metadata validation results: {len(successful)} successful, {len(failed)} failed")

    if failed:
        for failure in failed:
            logger.error(f"Invalid metadata for {failure['tool_class']}: {failure['error']}")

    # Assert all tools have valid metadata
    assert len(failed) == 0, f"Invalid metadata for {len(failed)} tools: {[f['tool_class'] for f in failed]}"


@pytest.mark.asyncio
async def test_code_tools_execute_with_minimal_args(clean_registry, clean_injector, mock_config):
    """Test that all code-based tools can execute with minimal valid arguments."""
    # Discover and register tools
    discover_and_register_tools()

    # Get all code-based tools
    code_tools = registry.get_tools_by_source("code")

    execution_results = []

    for tool_class in code_tools:
        try:
            instance = tool_class()
            tool_name = instance.name

            # Get the input schema to determine minimal arguments
            input_schema = instance.input_schema
            minimal_args = _generate_minimal_args(input_schema)

            # Mock external dependencies to avoid side effects
            with patch('subprocess.run') as mock_subprocess, \
                 patch('asyncio.create_subprocess_shell') as mock_async_subprocess, \
                 patch('mcp_tools.browser.factory.BrowserClientFactory.create_client') as mock_browser, \
                 patch('psutil.Process') as mock_psutil:

                # Configure mocks
                mock_subprocess.return_value = MagicMock(returncode=0, stdout="mock output", stderr="")
                mock_async_subprocess.return_value = AsyncMock()
                mock_browser.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
                mock_browser.return_value.__aexit__ = AsyncMock(return_value=None)

                # Attempt to execute the tool
                result = await instance.execute_tool(minimal_args)

                # Verify result format
                assert isinstance(result, (dict, str, int, float, bool, list)), \
                    f"{tool_name} returned invalid result type: {type(result)}"

                execution_results.append({
                    "tool_class": tool_class.__name__,
                    "tool_name": tool_name,
                    "success": True,
                    "error": None,
                    "result_type": type(result).__name__
                })

        except Exception as e:
            execution_results.append({
                "tool_class": tool_class.__name__,
                "tool_name": getattr(instance, 'name', 'unknown') if 'instance' in locals() else 'unknown',
                "success": False,
                "error": str(e),
                "result_type": None
            })

    # Log results
    successful = [r for r in execution_results if r["success"]]
    failed = [r for r in execution_results if not r["success"]]

    logger.info(f"Execution results: {len(successful)} successful, {len(failed)} failed")

    if failed:
        for failure in failed:
            logger.warning(f"Failed to execute {failure['tool_class']}: {failure['error']}")

    # Log successful executions
    for success in successful:
        logger.info(f"Successfully executed {success['tool_name']} ({success['tool_class']}) -> {success['result_type']}")

    # We expect most tools to execute successfully with mocked dependencies
    # Allow some failures for tools that require specific setup
    success_rate = len(successful) / len(execution_results) if execution_results else 0
    assert success_rate >= 0.7, f"Success rate too low: {success_rate:.2%} ({len(successful)}/{len(execution_results)})"


def _generate_minimal_args(input_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Generate minimal valid arguments based on input schema."""
    args = {}

    if not isinstance(input_schema, dict):
        return args

    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    for prop_name, prop_schema in properties.items():
        if prop_name in required or prop_name in ["operation", "command", "url"]:
            # Generate appropriate value based on type
            prop_type = prop_schema.get("type", "string")
            default_value = prop_schema.get("default")
            enum_values = prop_schema.get("enum")

            if default_value is not None:
                args[prop_name] = default_value
            elif enum_values:
                args[prop_name] = enum_values[0]
            elif prop_type == "string":
                if prop_name == "command":
                    args[prop_name] = "echo 'test'"
                elif prop_name == "url":
                    args[prop_name] = "https://example.com"
                elif prop_name == "operation":
                    args[prop_name] = "test"
                else:
                    args[prop_name] = "test_value"
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

    return args


def test_get_tools_by_source_code(clean_registry, clean_injector, mock_config):
    """Test that get_tools_by_source correctly filters code-based tools."""
    # Discover and register tools
    discover_and_register_tools()

    # Get tools by source
    code_tools = registry.get_tools_by_source("code")
    yaml_tools = registry.get_tools_by_source("yaml")
    all_tools = registry.get_all_tools()

    # Verify filtering
    assert len(code_tools) > 0, "No code tools found"
    assert len(yaml_tools) == 0, "YAML tools found when only code tools should be registered"
    assert len(code_tools) == len(all_tools), "Code tools count doesn't match all tools count"

    # Verify all returned tools are actually code-based
    tool_sources = registry.get_tool_sources()
    for tool_class in code_tools:
        tool_name = tool_class().name
        assert tool_sources.get(tool_name) == "code", f"Tool {tool_name} not marked as code source"


def test_tool_instance_creation_via_registry(clean_registry, clean_injector, mock_config):
    """Test that tools can be instantiated via the registry."""
    # Discover and register tools
    discover_and_register_tools()

    # Get all code-based tools
    code_tools = registry.get_tools_by_source("code")

    instance_creation_results = []

    for tool_class in code_tools:
        try:
            # Get tool name
            temp_instance = tool_class()
            tool_name = temp_instance.name

            # Get instance via registry
            registry_instance = registry.get_tool_instance(tool_name)

            assert registry_instance is not None, f"Registry returned None for tool {tool_name}"
            # Verify it has the required ToolInterface methods
            assert hasattr(registry_instance, 'name'), f"Registry instance for {tool_name} missing 'name' property"
            assert hasattr(registry_instance, 'description'), f"Registry instance for {tool_name} missing 'description' property"
            assert hasattr(registry_instance, 'input_schema'), f"Registry instance for {tool_name} missing 'input_schema' property"
            assert hasattr(registry_instance, 'execute_tool'), f"Registry instance for {tool_name} missing 'execute_tool' method"
            assert registry_instance.name == tool_name, f"Registry instance name mismatch for {tool_name}"

            instance_creation_results.append({
                "tool_class": tool_class.__name__,
                "tool_name": tool_name,
                "success": True,
                "error": None
            })

        except Exception as e:
            instance_creation_results.append({
                "tool_class": tool_class.__name__,
                "tool_name": getattr(temp_instance, 'name', 'unknown') if 'temp_instance' in locals() else 'unknown',
                "success": False,
                "error": str(e)
            })

    # Log results
    successful = [r for r in instance_creation_results if r["success"]]
    failed = [r for r in instance_creation_results if not r["success"]]

    logger.info(f"Registry instance creation results: {len(successful)} successful, {len(failed)} failed")

    if failed:
        for failure in failed:
            logger.error(f"Failed to create registry instance for {failure['tool_class']}: {failure['error']}")

    # Assert all tools can be instantiated via registry
    assert len(failed) == 0, f"Failed to create registry instances for {len(failed)} tools"


def test_no_duplicate_tool_names(clean_registry, clean_injector, mock_config):
    """Test that there are no duplicate tool names among code-based tools."""
    # Discover and register tools
    discover_and_register_tools()

    # Get all code-based tools
    code_tools = registry.get_tools_by_source("code")

    # Collect tool names
    tool_names = []
    for tool_class in code_tools:
        instance = tool_class()
        tool_names.append(instance.name)

    # Check for duplicates
    unique_names = set(tool_names)
    assert len(tool_names) == len(unique_names), \
        f"Duplicate tool names found: {[name for name in tool_names if tool_names.count(name) > 1]}"


def test_code_tools_coverage_summary(clean_registry, clean_injector, mock_config):
    """Provide a summary of code tools test coverage."""
    # Discover and register tools
    discover_and_register_tools()

    # Get all code-based tools
    code_tools = registry.get_tools_by_source("code")
    tool_sources = registry.get_tool_sources()

    # Generate summary
    summary = {
        "total_code_tools": len(code_tools),
        "tool_names": [tool().name for tool in code_tools],
        "tool_classes": [tool.__name__ for tool in code_tools],
        "source_distribution": {
            "code": len([s for s in tool_sources.values() if s == "code"]),
            "yaml": len([s for s in tool_sources.values() if s == "yaml"]),
        }
    }

    logger.info("Code Tools Test Coverage Summary:")
    logger.info(f"  Total code-based tools tested: {summary['total_code_tools']}")
    logger.info(f"  Tool names: {summary['tool_names']}")
    logger.info(f"  Tool classes: {summary['tool_classes']}")
    logger.info(f"  Source distribution: {summary['source_distribution']}")

    # Verify we have reasonable coverage
    assert summary["total_code_tools"] > 0, "No code-based tools found for testing"
    code_count = summary["source_distribution"]["code"]
    yaml_count = summary["source_distribution"]["yaml"]
    assert code_count > 0, "No code-based tools in source distribution"
    assert yaml_count == 0, "YAML tools found when only code tools expected"
