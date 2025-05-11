import os
import sys
import tempfile
import shutil
from pathlib import Path
import pytest

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use config module instead of server.environment
from config import env, env_manager


def setup_test_directory():
    """Set up a temporary directory with test configuration files"""
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory: {temp_dir}")

    # Create tools.yaml in the temporary directory
    tools_yaml = Path(temp_dir) / "tools.yaml"
    with open(tools_yaml, "w") as f:
        f.write(
            """
tools:
  private_test_tool:
    name: Private Test Tool
    description: A private test tool loaded from PRIVATE_TOOL_ROOT
    type: script
    script: private_test_script.ps1
    inputSchema:
      type: object
      properties:
        param1:
          type: string
          description: Test parameter
      required:
        - param1

tasks:
  private_test_task:
    description: A private test task from PRIVATE_TOOL_ROOT
    commands:
      windows: echo This is a private task from PRIVATE_TOOL_ROOT
      linux: echo This is a private task from PRIVATE_TOOL_ROOT
      darwin: echo This is a private task from PRIVATE_TOOL_ROOT
"""
        )

    # Create a test script
    test_script = Path(temp_dir) / "private_test_script.ps1"
    with open(test_script, "w") as f:
        f.write(
            """
param (
    [string]$param1
)

Write-Output "Private test script executed with parameter: $param1"
"""
        )

    # Create prompts.yaml in the temporary directory
    prompts_yaml = Path(temp_dir) / "prompts.yaml"
    with open(prompts_yaml, "w") as f:
        f.write(
            """
prompts:
  private_test_prompt:
    name: Private Test Prompt
    description: A private test prompt loaded from PRIVATE_TOOL_ROOT
    arguments:
      - name: param1
        description: Test parameter
        required: true
    template: "This is a private prompt template with {param1}"
    enabled: true
"""
        )

    return temp_dir


@pytest.fixture
def private_tool_root():
    """Fixture to set up and tear down a temporary private tool root directory"""
    # Set up test directory
    temp_dir = setup_test_directory()

    # Store original value to restore later
    original_value = os.environ.get("PRIVATE_TOOL_ROOT")

    # Set PRIVATE_TOOL_ROOT environment variable for the test
    os.environ["PRIVATE_TOOL_ROOT"] = temp_dir

    # Reset the environment manager singleton
    env_manager._initialize()

    # Manually set the repository_info.private_tool_root
    env_manager.repository_info.private_tool_root = temp_dir

    # Load environment (this would normally come from .env files)
    env_manager.env_variables["PRIVATE_TOOL_ROOT"] = temp_dir

    # Yield the temp directory path for the test to use
    yield temp_dir

    # Clean up after the test
    shutil.rmtree(temp_dir)
    print(f"\nCleaned up temporary directory: {temp_dir}")

    # Restore original environment variable
    if original_value:
        os.environ["PRIVATE_TOOL_ROOT"] = original_value
        env_manager.repository_info.private_tool_root = original_value
        env_manager.env_variables["PRIVATE_TOOL_ROOT"] = original_value
    else:
        if "PRIVATE_TOOL_ROOT" in os.environ:
            del os.environ["PRIVATE_TOOL_ROOT"]
        env_manager.repository_info.private_tool_root = None
        if "PRIVATE_TOOL_ROOT" in env_manager.env_variables:
            del env_manager.env_variables["PRIVATE_TOOL_ROOT"]


def test_private_tool_root_is_set(private_tool_root):
    """Test that the PRIVATE_TOOL_ROOT environment variable is set correctly"""
    # Verify the environment variable is loaded
    tool_root = env.get_private_tool_root()
    print(f"PRIVATE_TOOL_ROOT: {tool_root}")
    assert tool_root == private_tool_root


def test_private_tools_loading(private_tool_root):
    """Test loading tools from PRIVATE_TOOL_ROOT"""
    # Import and test tools loading
    from mcp_tools.tools import load_tools_from_yaml

    # Load tools and verify the private test tool is loaded
    tools = load_tools_from_yaml()
    print("\nLoaded tools:")
    for name, tool in tools.items():
        print(f"- {name}: {tool.get('description', 'No description')}")

    assert "private_test_tool" in tools
    assert (
        tools["private_test_tool"]["description"]
        == "A private test tool loaded from PRIVATE_TOOL_ROOT"
    )


def test_private_tasks_loading(private_tool_root):
    """Test loading tasks from PRIVATE_TOOL_ROOT"""
    # Import and test tasks loading
    from mcp_tools.tools import load_tasks_from_yaml

    # Load tasks and verify the private test task is loaded
    tasks = load_tasks_from_yaml()
    print("\nLoaded tasks:")
    for name, task in tasks.items():
        print(f"- {name}: {task.get('description', 'No description')}")

    assert "private_test_task" in tasks
    assert (
        tasks["private_test_task"]["description"]
        == "A private test task from PRIVATE_TOOL_ROOT"
    )


def test_private_prompts_loading(private_tool_root):
    """Test loading prompts from PRIVATE_TOOL_ROOT"""
    # Test prompts loading
    from server.prompts import load_prompts_from_yaml

    # Ensure the config module knows about the private_tool_root
    print(f"Private tool root before loading prompts: {env.get_private_tool_root()}")

    # Load prompts and verify the private test prompt is loaded
    prompts = load_prompts_from_yaml()
    print("\nLoaded prompts:")
    for name, prompt in prompts.items():
        print(f"- {name}: {prompt.get('description', 'No description')}")

    assert "private_test_prompt" in prompts
    assert (
        prompts["private_test_prompt"]["description"]
        == "A private test prompt loaded from PRIVATE_TOOL_ROOT"
    )


if __name__ == "__main__":
    # When running directly, use pytest to run the tests
    pytest.main(["-xvs", __file__])
