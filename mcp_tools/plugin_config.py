"""Plugin configuration system for MCP tools.

This module provides a configuration system for the plugin registry,
allowing customization of tool discovery and registration behavior.
"""

import os
import logging
from typing import List, Dict, Any, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginConfig:
    """Configuration for the plugin system."""

    def __init__(self):
        """Initialize plugin configuration with default values."""
        # Whether to automatically register code-based tools
        self.register_code_tools = True

        # Whether to automatically register YAML-based tools
        self.register_yaml_tools = True

        # Whether code tools should be skipped if YAML definitions exist
        self.yaml_overrides_code = True

        # Set of tool class names to exclude from registration
        self.excluded_base_classes = {"ToolInterface", "YamlToolBase"}

        # Path to YAML tool definitions
        self.yaml_tool_paths = []

        # Path to plugin root directories
        self.plugin_roots = []

        # Tool names to always exclude regardless of source
        self.excluded_tool_names = set()

        # Load environment-based configuration
        self._load_from_env()

    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Check if code tools should be registered
        env_code_tools = os.environ.get("MCP_REGISTER_CODE_TOOLS", "").lower()
        if env_code_tools in ("0", "false", "no"):
            self.register_code_tools = False
        elif env_code_tools in ("1", "true", "yes"):
            self.register_code_tools = True

        # Check if YAML tools should be registered
        env_yaml_tools = os.environ.get("MCP_REGISTER_YAML_TOOLS", "").lower()
        if env_yaml_tools in ("0", "false", "no"):
            self.register_yaml_tools = False
        elif env_yaml_tools in ("1", "true", "yes"):
            self.register_yaml_tools = True

        # Check if YAML should override code
        env_yaml_override = os.environ.get("MCP_YAML_OVERRIDES_CODE", "").lower()
        if env_yaml_override in ("0", "false", "no"):
            self.yaml_overrides_code = False
        elif env_yaml_override in ("1", "true", "yes"):
            self.yaml_overrides_code = True

        # Get additional excluded base classes
        env_excluded = os.environ.get("MCP_EXCLUDED_BASE_CLASSES", "")
        if env_excluded:
            additional_excluded = {
                cls.strip() for cls in env_excluded.split(",") if cls.strip()
            }
            self.excluded_base_classes.update(additional_excluded)

        # Get excluded tool names
        env_excluded_tools = os.environ.get("MCP_EXCLUDED_TOOL_NAMES", "")
        if env_excluded_tools:
            excluded_tools = {
                tool.strip() for tool in env_excluded_tools.split(",") if tool.strip()
            }
            self.excluded_tool_names.update(excluded_tools)

        # Get YAML tool paths
        env_yaml_paths = os.environ.get("MCP_YAML_TOOL_PATHS", "")
        if env_yaml_paths:
            self.yaml_tool_paths = [
                Path(p.strip()) for p in env_yaml_paths.split(",") if p.strip()
            ]

        # Get plugin root paths
        env_plugin_roots = os.environ.get("MCP_PLUGIN_ROOTS", "")
        if env_plugin_roots:
            self.plugin_roots = [
                Path(p.strip()) for p in env_plugin_roots.split(",") if p.strip()
            ]
        else:
            # Default plugin root if not specified
            default_plugin_root = Path(__file__).resolve().parent.parent / "plugins"
            if default_plugin_root.exists() and default_plugin_root.is_dir():
                self.plugin_roots = [default_plugin_root]
                logger.info(f"Using default plugin root: {default_plugin_root}")

        # Log the configuration
        logger.debug(
            f"Plugin configuration loaded from environment: "
            f"register_code_tools={self.register_code_tools}, "
            f"register_yaml_tools={self.register_yaml_tools}, "
            f"yaml_overrides_code={self.yaml_overrides_code}, "
            f"plugin_roots={self.plugin_roots}"
        )

    def should_register_tool_class(
        self, class_name: str, tool_name: str, yaml_tools: Set[str]
    ) -> bool:
        """Determine if a tool class should be registered.

        Args:
            class_name: Name of the class
            tool_name: Name of the tool
            yaml_tools: Set of tool names defined in YAML

        Returns:
            True if the tool should be registered, False otherwise
        """
        # Check if the class is in the excluded base classes
        if class_name in self.excluded_base_classes:
            logger.debug(f"Skipping registration of excluded base class: {class_name}")
            return False

        # Check if the tool name is explicitly excluded
        if tool_name in self.excluded_tool_names:
            logger.debug(f"Skipping registration of excluded tool: {tool_name}")
            return False

        # Check if there's a YAML definition that should override this
        # Only apply this rule to non-YAML tools (classes not starting with YamlTool_)
        if (
            self.yaml_overrides_code
            and tool_name in yaml_tools
            and not class_name.startswith("YamlTool_")
        ):
            logger.info(
                f"Skipping registration of {class_name} (tool: {tool_name}) because a YAML definition exists"
            )
            return False

        return True

    def get_yaml_tool_paths(self) -> List[Path]:
        """Get the paths to look for YAML tool definitions.

        Returns:
            List of paths to check for tools.yaml
        """
        paths = []

        # First priority: Check PRIVATE_TOOL_ROOT if set
        private_tool_root = os.environ.get("PRIVATE_TOOL_ROOT")
        if private_tool_root:
            private_path = Path(private_tool_root)
            if private_path.exists():
                paths.append(private_path)
                logger.info(f"Added PRIVATE_TOOL_ROOT path: {private_path}")

        # Second priority: Check MCP_YAML_TOOL_PATHS if set
        yaml_paths = os.environ.get("MCP_YAML_TOOL_PATHS", "")
        if yaml_paths:
            for path in yaml_paths.split(","):
                path = Path(path.strip())
                if path.exists() and path not in paths:
                    paths.append(path)
                    logger.info(f"Added MCP_YAML_TOOL_PATHS path: {path}")

        # If no paths are configured, use defaults
        if not paths:
            server_dir = Path(__file__).resolve().parent.parent / "server"
            private_dir = server_dir / ".private"
            current_dir = Path(os.getcwd())

            paths = [private_dir, server_dir, current_dir]
            logger.info(f"Using default paths: {paths}")

        return paths

    def get_plugin_roots(self) -> List[Path]:
        """Get the plugin root directories.

        Returns:
            List of plugin root directories
        """
        return self.plugin_roots

    def is_source_enabled(self, source: str) -> bool:
        """Check if a specific tool source is enabled.

        Args:
            source: The tool source to check ("code" or "yaml")

        Returns:
            True if the source is enabled, False otherwise
        """
        if source == "code":
            return self.register_code_tools
        elif source == "yaml":
            return self.register_yaml_tools
        else:
            # Unknown sources are only enabled if both code and yaml are enabled
            return self.register_code_tools and self.register_yaml_tools


# Create a singleton instance
config = PluginConfig()
