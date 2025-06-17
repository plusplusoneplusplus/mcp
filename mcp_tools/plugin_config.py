"""Plugin configuration system for MCP tools.

This module provides a configuration system for the plugin registry,
allowing customization of tool discovery and registration behavior.
"""

import os
import logging
from typing import List, Dict, Any, Set, Optional
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

        # Plugin enable/disable configuration
        self.enabled_plugins = set()  # Explicitly enabled plugins
        self.disabled_plugins = set()  # Explicitly disabled plugins
        self.plugin_enable_mode = "all"  # "all", "whitelist", "blacklist"

        # Ecosystem filtering configuration
        self.enabled_ecosystems = set()  # Explicitly enabled ecosystems
        self.disabled_ecosystems = set()  # Explicitly disabled ecosystems
        self.ecosystem_enable_mode = "all"  # "all", "whitelist", "blacklist"

        # OS filtering configuration
        self.enabled_os = set()  # Explicitly enabled OS types
        self.disabled_os = set()  # Explicitly disabled OS types
        self.os_enable_mode = "all"  # "all", "whitelist", "blacklist"

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

        # Load plugin enable/disable configuration
        self._load_plugin_config_from_env()

        # Load ecosystem configuration
        self._load_ecosystem_config_from_env()

        # Load OS configuration
        self._load_os_config_from_env()

        # Log the configuration
        logger.debug(
            f"Plugin configuration loaded from environment: "
            f"register_code_tools={self.register_code_tools}, "
            f"register_yaml_tools={self.register_yaml_tools}, "
            f"yaml_overrides_code={self.yaml_overrides_code}, "
            f"plugin_roots={self.plugin_roots}, "
            f"plugin_enable_mode={self.plugin_enable_mode}, "
            f"ecosystem_enable_mode={self.ecosystem_enable_mode}"
        )

    def _load_plugin_config_from_env(self):
        """Load plugin enable/disable configuration from environment variables."""
        # Get plugin enable mode
        env_plugin_mode = os.environ.get("MCP_PLUGIN_MODE", "all").lower()
        if env_plugin_mode in ("all", "whitelist", "blacklist"):
            self.plugin_enable_mode = env_plugin_mode
        else:
            logger.warning(f"Invalid MCP_PLUGIN_MODE value: {env_plugin_mode}. Using 'all'")
            self.plugin_enable_mode = "all"

        # Get enabled plugins
        env_enabled_plugins = os.environ.get("MCP_ENABLED_PLUGINS", "")
        if env_enabled_plugins:
            enabled_plugins = {
                plugin.strip() for plugin in env_enabled_plugins.split(",") if plugin.strip()
            }
            self.enabled_plugins.update(enabled_plugins)
            logger.info(f"Enabled plugins from environment: {self.enabled_plugins}")

        # Get disabled plugins
        env_disabled_plugins = os.environ.get("MCP_DISABLED_PLUGINS", "")
        if env_disabled_plugins:
            disabled_plugins = {
                plugin.strip() for plugin in env_disabled_plugins.split(",") if plugin.strip()
            }
            self.disabled_plugins.update(disabled_plugins)
            logger.info(f"Disabled plugins from environment: {self.disabled_plugins}")

    def _load_ecosystem_config_from_env(self):
        """Load ecosystem enable/disable configuration from environment variables."""
        # Get ecosystem enable mode
        env_ecosystem_mode = os.environ.get("MCP_ECOSYSTEM_MODE", "all").lower()
        if env_ecosystem_mode in ("all", "whitelist", "blacklist"):
            self.ecosystem_enable_mode = env_ecosystem_mode
        else:
            logger.warning(f"Invalid MCP_ECOSYSTEM_MODE value: {env_ecosystem_mode}. Using 'all'")
            self.ecosystem_enable_mode = "all"

        # Get enabled ecosystems
        env_enabled_ecosystems = os.environ.get("MCP_ENABLED_ECOSYSTEMS", "")
        if env_enabled_ecosystems:
            enabled_ecosystems = {
                ecosystem.strip().lower() for ecosystem in env_enabled_ecosystems.split(",") if ecosystem.strip()
            }
            self.enabled_ecosystems.update(enabled_ecosystems)
            logger.info(f"Enabled ecosystems from environment: {self.enabled_ecosystems}")

        # Get disabled ecosystems
        env_disabled_ecosystems = os.environ.get("MCP_DISABLED_ECOSYSTEMS", "")
        if env_disabled_ecosystems:
            disabled_ecosystems = {
                ecosystem.strip().lower() for ecosystem in env_disabled_ecosystems.split(",") if ecosystem.strip()
            }
            self.disabled_ecosystems.update(disabled_ecosystems)
            logger.info(f"Disabled ecosystems from environment: {self.disabled_ecosystems}")

    def _load_os_config_from_env(self):
        """Load OS enable/disable configuration from environment variables."""
        # Get OS enable mode
        env_os_mode = os.environ.get("MCP_OS_MODE", "all").lower()
        if env_os_mode in ("all", "whitelist", "blacklist"):
            self.os_enable_mode = env_os_mode
        else:
            logger.warning(f"Invalid MCP_OS_MODE value: {env_os_mode}. Using 'all'")
            self.os_enable_mode = "all"

        # Get enabled OS types
        env_enabled_os = os.environ.get("MCP_ENABLED_OS", "")
        if env_enabled_os:
            enabled_os = {
                os_type.strip().lower() for os_type in env_enabled_os.split(",") if os_type.strip()
            }
            self.enabled_os.update(enabled_os)
            logger.info(f"Enabled OS types from environment: {self.enabled_os}")

        # Get disabled OS types
        env_disabled_os = os.environ.get("MCP_DISABLED_OS", "")
        if env_disabled_os:
            disabled_os = {
                os_type.strip().lower() for os_type in env_disabled_os.split(",") if os_type.strip()
            }
            self.disabled_os.update(disabled_os)
            logger.info(f"Disabled OS types from environment: {self.disabled_os}")

    def should_register_tool_class(
        self, class_name: str, tool_name: str, yaml_tools: Set[str],
        ecosystem: Optional[str] = None, os: Optional[str] = None
    ) -> bool:
        """Determine if a tool class should be registered.

        Args:
            class_name: Name of the class
            tool_name: Name of the tool
            yaml_tools: Set of tool names defined in YAML
            ecosystem: Ecosystem the tool belongs to (e.g., "microsoft", "general")
            os: OS compatibility ("windows", "non-windows", "all")

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

        # Check plugin enable/disable status
        if not self.is_plugin_enabled(tool_name):
            logger.debug(f"Skipping registration of disabled plugin: {tool_name}")
            return False

        # Check ecosystem enable/disable status
        if not self.is_ecosystem_enabled(ecosystem):
            logger.debug(f"Skipping registration of tool '{tool_name}' from disabled ecosystem: {ecosystem}")
            return False

        # Check OS enable/disable status
        if not self.is_os_enabled(os):
            logger.debug(f"Skipping registration of tool '{tool_name}' from disabled OS: {os}")
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

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled based on the current configuration.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            True if the plugin should be enabled, False otherwise
        """
        # If plugin is explicitly disabled, return False
        if plugin_name in self.disabled_plugins:
            return False

        # Handle different enable modes
        if self.plugin_enable_mode == "all":
            # All plugins are enabled by default unless explicitly disabled
            return True
        elif self.plugin_enable_mode == "whitelist":
            # Only explicitly enabled plugins are allowed
            return plugin_name in self.enabled_plugins
        elif self.plugin_enable_mode == "blacklist":
            # All plugins are enabled except those explicitly disabled
            return plugin_name not in self.disabled_plugins
        else:
            # Default to all enabled for unknown modes
            logger.warning(f"Unknown plugin enable mode: {self.plugin_enable_mode}")
            return True

    def is_ecosystem_enabled(self, ecosystem: Optional[str]) -> bool:
        """Check if an ecosystem is enabled based on the current configuration.

        Args:
            ecosystem: Name of the ecosystem to check (case-insensitive)

        Returns:
            True if the ecosystem should be enabled, False otherwise
        """
        # If no ecosystem is specified, treat as enabled (backward compatibility)
        if ecosystem is None:
            return True

        ecosystem_lower = ecosystem.lower()

        # If ecosystem is explicitly disabled, return False
        if ecosystem_lower in self.disabled_ecosystems:
            return False

        # Handle different enable modes
        if self.ecosystem_enable_mode == "all":
            # All ecosystems are enabled by default unless explicitly disabled
            return True
        elif self.ecosystem_enable_mode == "whitelist":
            # Only explicitly enabled ecosystems are allowed
            return ecosystem_lower in self.enabled_ecosystems
        elif self.ecosystem_enable_mode == "blacklist":
            # All ecosystems are enabled except those explicitly disabled
            return ecosystem_lower not in self.disabled_ecosystems
        else:
            # Default to all enabled for unknown modes
            logger.warning(f"Unknown ecosystem enable mode: {self.ecosystem_enable_mode}")
            return True

    def is_os_enabled(self, os: Optional[str]) -> bool:
        """Check if an OS is enabled based on the current configuration.

        Args:
            os: Name of the OS to check (case-insensitive)

        Returns:
            True if the OS should be enabled, False otherwise
        """
        # If no OS is specified, treat as enabled (backward compatibility)
        if os is None:
            return True

        os_lower = os.lower()

        # If OS is explicitly disabled, return False
        if os_lower in self.disabled_os:
            return False

        # Handle different enable modes
        if self.os_enable_mode == "all":
            # All OS types are enabled by default unless explicitly disabled
            return True
        elif self.os_enable_mode == "whitelist":
            # Only explicitly enabled OS types are allowed
            return os_lower in self.enabled_os
        elif self.os_enable_mode == "blacklist":
            # All OS types are enabled except those explicitly disabled
            return os_lower not in self.disabled_os
        else:
            # Default to all enabled for unknown modes
            logger.warning(f"Unknown OS enable mode: {self.os_enable_mode}")
            return True

    def enable_plugin(self, plugin_name: str) -> None:
        """Enable a specific plugin.

        Args:
            plugin_name: Name of the plugin to enable
        """
        self.enabled_plugins.add(plugin_name)
        # Remove from disabled set if present
        self.disabled_plugins.discard(plugin_name)
        logger.info(f"Plugin '{plugin_name}' has been enabled")

    def disable_plugin(self, plugin_name: str) -> None:
        """Disable a specific plugin.

        Args:
            plugin_name: Name of the plugin to disable
        """
        self.disabled_plugins.add(plugin_name)
        # Remove from enabled set if present
        self.enabled_plugins.discard(plugin_name)
        logger.info(f"Plugin '{plugin_name}' has been disabled")

    def enable_ecosystem(self, ecosystem: str) -> None:
        """Enable a specific ecosystem.

        Args:
            ecosystem: Name of the ecosystem to enable
        """
        ecosystem_lower = ecosystem.lower()
        self.enabled_ecosystems.add(ecosystem_lower)
        # Remove from disabled set if present
        self.disabled_ecosystems.discard(ecosystem_lower)
        logger.info(f"Ecosystem '{ecosystem}' has been enabled")

    def disable_ecosystem(self, ecosystem: str) -> None:
        """Disable a specific ecosystem.

        Args:
            ecosystem: Name of the ecosystem to disable
        """
        ecosystem_lower = ecosystem.lower()
        self.disabled_ecosystems.add(ecosystem_lower)
        # Remove from enabled set if present
        self.enabled_ecosystems.discard(ecosystem_lower)
        logger.info(f"Ecosystem '{ecosystem}' has been disabled")

    def enable_os(self, os: str) -> None:
        """Enable a specific OS.

        Args:
            os: Name of the OS to enable
        """
        os_lower = os.lower()
        self.enabled_os.add(os_lower)
        # Remove from disabled set if present
        self.disabled_os.discard(os_lower)
        logger.info(f"OS '{os}' has been enabled")

    def disable_os(self, os: str) -> None:
        """Disable a specific OS.

        Args:
            os: Name of the OS to disable
        """
        os_lower = os.lower()
        self.disabled_os.add(os_lower)
        # Remove from enabled set if present
        self.enabled_os.discard(os_lower)
        logger.info(f"OS '{os}' has been disabled")

    def get_available_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata about all available plugins.

        Returns:
            Dictionary mapping plugin names to their metadata
        """
        # Try to get comprehensive plugin information from the registry
        try:
            # Import here to avoid circular imports
            from mcp_tools.plugin import registry
            return registry.get_available_plugins()
        except ImportError:
            # Fallback to basic information about configured plugins
            available_plugins = {}

            # Add information about explicitly configured plugins
            all_configured_plugins = self.enabled_plugins.union(self.disabled_plugins)

            for plugin_name in all_configured_plugins:
                available_plugins[plugin_name] = {
                    "name": plugin_name,
                    "enabled": self.is_plugin_enabled(plugin_name),
                    "source": "configuration",
                    "explicitly_configured": True,
                    "registered": False,
                    "has_instance": False
                }

            return available_plugins

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
