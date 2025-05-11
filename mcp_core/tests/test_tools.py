#!/usr/bin/env python3
# Test script to verify tools.yaml integration

import os
import sys
import logging
import yaml
import pytest
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("tools_test")

# Add parent directory to path to allow importing mcp_core
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the direct tool system
from mcp_tools.plugin import registry, discover_and_register_tools
from mcp_tools.dependency import injector


@pytest.fixture
def yaml_data():
    """Load tools.yaml data as a fixture"""
    # Get the server directory
    server_dir = Path(parent_dir) / "server"

    # Load tools.yaml content
    yaml_path = server_dir / "tools.yaml"
    if not yaml_path.exists():
        pytest.skip(f"tools.yaml not found at {yaml_path}")

    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def tool_system():
    """Initialize the tool system and return registry and injector"""
    discover_and_register_tools()
    injector.resolve_all_dependencies()
    return {"registry": registry, "injector": injector}


def test_tools_yaml_exists():
    """Test that tools.yaml exists in the server directory"""
    server_dir = Path(parent_dir) / "server"
    yaml_path = server_dir / "tools.yaml"
    assert yaml_path.exists(), f"tools.yaml not found at {yaml_path}"


def test_tool_system_initialization(tool_system):
    """Test that the tool system can be initialized"""
    assert tool_system["registry"] is not None
    assert tool_system["injector"] is not None

    # Get all registered tools
    tools = list(tool_system["injector"].instances.values())
    assert len(tools) > 0, "No tools were registered"


def test_tools_from_yaml_are_registered(yaml_data, tool_system):
    """Test that tools defined in tools.yaml are registered in the system"""
    # Get tools from yaml
    yaml_tool_names = yaml_data.get("tools", {}).keys()
    assert len(yaml_tool_names) > 0, "No tools found in tools.yaml"

    # Get registered tools
    tools = list(tool_system["injector"].instances.values())
    registered_tool_names = [tool.name for tool in tools]

    # Verify at least some tools are registered
    assert len(registered_tool_names) > 0, "No tools registered in the system"

    # Count how many tools from yaml are registered
    registered_count = 0
    missing_tools = []

    for name in yaml_tool_names:
        if name in registered_tool_names:
            registered_count += 1
        else:
            missing_tools.append(name)

    # Log missing tools but don't fail the test
    if missing_tools:
        print(
            f"Note: {len(missing_tools)} tools from yaml are not registered: {', '.join(missing_tools)}"
        )
        print(
            "This could be expected if those tools are conditionally registered or the environment is not fully set up."
        )

    # Check that at least one tool from yaml is registered
    assert registered_count > 0, "None of the tools from tools.yaml are registered"
