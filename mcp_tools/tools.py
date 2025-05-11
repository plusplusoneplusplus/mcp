import os
import yaml
from pathlib import Path
from mcp_tools.command_executor import executor


def _find_tools_yaml():
    """Find the tools.yaml file in the project."""
    # Look in common locations for tools.yaml
    possible_paths = [
        Path("server/tools.yaml"),  # From project root
        Path("tools.yaml"),  # From project root
        Path("../server/tools.yaml"),  # From mcp_tools directory
        Path("../tools.yaml"),  # From mcp_tools directory
        Path.cwd() / "server" / "tools.yaml",
        Path.cwd() / "tools.yaml",
    ]

    # Check PRIVATE_TOOL_ROOT environment variable if set
    if "PRIVATE_TOOL_ROOT" in os.environ:
        private_root = Path(os.environ["PRIVATE_TOOL_ROOT"])
        possible_paths.insert(0, private_root / "tools.yaml")

    # Check TOOLS_YAML_PATH environment variable if set
    if "TOOLS_YAML_PATH" in os.environ:
        possible_paths.insert(0, Path(os.environ["TOOLS_YAML_PATH"]))

    for path in possible_paths:
        if path.exists():
            print(f"Found tools.yaml at: {path}")
            return path

    return None


def load_tasks_from_yaml():
    """Load tasks from a YAML file."""
    yaml_path = _find_tools_yaml()
    if not yaml_path:
        # If we can't find a tools.yaml, return an empty dict
        print("Warning: Could not find tools.yaml file")
        return {}

    with open(yaml_path, "r") as f:
        try:
            data = yaml.safe_load(f)
            if not data:
                return {}
            return data.get("tasks", {})
        except yaml.YAMLError as e:
            print(f"Error parsing YAML: {e}")
            return {}


def load_tools_from_yaml():
    """Load tools from a YAML file."""
    yaml_path = _find_tools_yaml()
    if not yaml_path:
        # If we can't find a tools.yaml, return an empty dict
        print("Warning: Could not find tools.yaml file")
        return {}

    with open(yaml_path, "r") as f:
        try:
            data = yaml.safe_load(f)
            if not data:
                return {}
            return data.get("tools", {})
        except yaml.YAMLError as e:
            print(f"Error parsing YAML: {e}")
            return {}


# Export the executor module directly so it can be imported as mcp_tools.tools.executor
__all__ = ["load_tasks_from_yaml", "load_tools_from_yaml", "executor"]
