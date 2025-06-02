import importlib
import importlib.util
import inspect
import logging
import os
import pkgutil
import sys
from typing import Dict, List, Type, Set, Optional, Any
from pathlib import Path

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin_config import config

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Registry for MCP tool plugins.

    This class handles the registration, discovery, and management of tool plugins
    that implement the ToolInterface.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginRegistry, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the plugin registry"""
        self.tools: Dict[str, Type[ToolInterface]] = {}
        self.instances: Dict[str, ToolInterface] = {}
        self.discovered_paths: Set[str] = set()
        self.yaml_tool_names: Set[str] = set()
        self.tool_sources: Dict[str, str] = {}  # Track tool source: "code" or "yaml"

    def register_tool(
        self, tool_class: Type[ToolInterface], source: str = "code"
    ) -> Optional[Type[ToolInterface]]:
        """Register a tool class.

        Args:
            tool_class: A class that implements ToolInterface
            source: Source of the tool ("code" or "yaml")

        Returns:
            The registered tool class or None if it wasn't registered

        Raises:
            TypeError: If the provided class doesn't implement ToolInterface
        """
        if not inspect.isclass(tool_class):
            raise TypeError(f"Expected a class, got {type(tool_class)}")

        if not issubclass(tool_class, ToolInterface):
            raise TypeError(
                f"Class {tool_class.__name__} does not implement ToolInterface"
            )

        # Skip abstract classes
        if inspect.isabstract(tool_class):
            logger.debug(
                f"Skipping registration of abstract class {tool_class.__name__}"
            )
            return None

        # Create a temporary instance to get the name
        try:
            temp_instance = tool_class()
            tool_name = temp_instance.name

            # Check if this tool should be registered based on configuration
            if not config.should_register_tool_class(
                tool_class.__name__, tool_name, self.yaml_tool_names
            ):
                return None

            logger.info(
                f"Registering tool: {tool_name} ({tool_class.__name__}) from {source}"
            )
            self.tools[tool_name] = tool_class
            self.tool_sources[tool_name] = source
            return tool_class
        except Exception as e:
            logger.error(f"Error creating instance of {tool_class.__name__}: {e}")
            return None

    def get_tool_instance(self, tool_name: str) -> Optional[ToolInterface]:
        """Get or create an instance of a registered tool.

        Args:
            tool_name: Name of the tool to get

        Returns:
            Instance of the tool, or None if not found
        """
        # Try case-sensitive lookup first
        if tool_name in self.instances:
            logger.debug(f"Found existing tool instance for '{tool_name}'")
            return self.instances[tool_name]

        # If not found, try case-insensitive lookup
        for registered_name in self.instances:
            if registered_name.lower() == tool_name.lower():
                logger.debug(
                    f"Found tool instance for '{tool_name}' with case-insensitive match: '{registered_name}'"
                )
                return self.instances[registered_name]

        # Check if tool class is registered (case-sensitive)
        if tool_name in self.tools:
            logger.debug(f"Creating new instance for tool '{tool_name}'")
            # Use the dependency injector if available
            try:
                from mcp_tools.dependency import injector

                return injector.get_tool_instance(tool_name)
            except ImportError:
                # Fallback to simple instantiation
                return self._simple_get_tool_instance(tool_name)

        # Try case-insensitive lookup for tool class
        for registered_name in self.tools:
            if registered_name.lower() == tool_name.lower():
                logger.debug(
                    f"Creating new instance for tool '{tool_name}' with case-insensitive match: '{registered_name}'"
                )
                try:
                    from mcp_tools.dependency import injector

                    return injector.get_tool_instance(registered_name)
                except ImportError:
                    return self._simple_get_tool_instance(registered_name)

        logger.warning(f"Tool '{tool_name}' not found")
        return None

    def _simple_get_tool_instance(self, tool_name: str) -> Optional[ToolInterface]:
        """Simple tool instantiation without dependency injection.

        Args:
            tool_name: Name of the tool to get

        Returns:
            Instance of the tool, or None if not found
        """
        # Return existing instance if available
        if tool_name in self.instances:
            return self.instances[tool_name]

        # Create a new instance if the tool is registered
        if tool_name in self.tools:
            try:
                instance = self.tools[tool_name]()
                self.instances[tool_name] = instance
                return instance
            except Exception as e:
                logger.error(f"Error creating instance of tool {tool_name}: {e}")
                return None

        return None

    def discover_tools(self, package_name: str = "mcp_tools") -> None:
        """Discover tools by recursively scanning a package.

        Args:
            package_name: Name of the package to scan for tools
        """
        # Skip if code tools are disabled
        if not config.register_code_tools:
            logger.info("Code tool registration is disabled, skipping discovery")
            return

        logger.info(f"Discovering tools in package: {package_name}")

        # Skip setup-related modules
        if package_name in ["mcp_tools.setup", "setuptools", "setup"]:
            logger.debug(f"Skipping setup module: {package_name}")
            return

        try:
            package = importlib.import_module(package_name)
            package_path = getattr(package, "__path__", [])

            for _, module_name, is_pkg in pkgutil.walk_packages(package_path):
                # Skip setup-related modules
                if module_name in ["setup", "setuptools"]:
                    continue

                full_name = f"{package_name}.{module_name}"

                # Skip if already processed
                if full_name in self.discovered_paths:
                    continue

                try:
                    # Mark as discovered to avoid loops
                    self.discovered_paths.add(full_name)

                    if is_pkg:
                        # Recursively discover tools in subpackages
                        self.discover_tools(full_name)
                    else:
                        # Import the module and look for tool classes
                        module = importlib.import_module(full_name)
                        self._scan_module_for_tools(module)
                except Exception as e:
                    logger.warning(f"Error processing module {full_name}: {e}")
        except Exception as e:
            logger.error(f"Error discovering tools in {package_name}: {e}")

    def _scan_module_for_tools(self, module) -> None:
        """Scan a module for classes that implement ToolInterface with comprehensive error handling.

        Args:
            module: The module to scan
        """
        # Skip scanning if code tools registration is disabled
        if not config.register_code_tools:
            logger.info(
                f"Skipping code tool registration for module {module.__name__} (register_code_tools=False)"
            )
            return

        module_name = getattr(module, "__name__", "Unknown")
        logger.debug(f"Scanning module {module_name} for tool classes")

        successful_registrations = []
        failed_registrations = []

        try:
            # Get all members of the module with error handling
            try:
                module_members = inspect.getmembers(module)
            except Exception as e:
                logger.error(f"Error getting members from module {module_name}: {e}")
                return

            for name, obj in module_members:
                try:
                    # Check if it's a class defined in this module (not imported)
                    if not (
                        inspect.isclass(obj)
                        and obj.__module__ == module.__name__
                        and issubclass(obj, ToolInterface)
                        and obj is not ToolInterface
                    ):
                        continue

                    # Skip abstract classes
                    if inspect.isabstract(obj):
                        logger.debug(
                            f"Skipping abstract class {name} from {module_name}"
                        )
                        continue

                    # Attempt to register this individual tool with comprehensive error handling
                    try:
                        logger.debug(
                            f"Attempting to register tool class {name} from {module_name}"
                        )

                        # Check exclusion before validation to avoid unnecessary instantiation
                        # Create a temporary instance to get the tool name for exclusion check
                        try:
                            temp_instance = obj()
                            tool_name = temp_instance.name
                        except Exception as e:
                            logger.warning(
                                f"Tool {name} failed to instantiate for exclusion check: {e}"
                            )
                            failed_registrations.append(
                                f"{name}: Instantiation failed - {str(e)}"
                            )
                            continue

                        # Check if this tool should be registered based on configuration
                        if not config.should_register_tool_class(
                            name, tool_name, self.yaml_tool_names
                        ):
                            logger.debug(
                                f"Skipping registration of {name} (tool: {tool_name}) due to configuration"
                            )
                            continue

                        # Validate the tool class before registration
                        try:
                            # We already have temp_instance from above, get remaining properties
                            description = temp_instance.description
                            input_schema = temp_instance.input_schema

                            # Basic validation
                            if not tool_name or not isinstance(tool_name, str):
                                raise ValueError(
                                    f"Tool {name} has invalid name: {tool_name}"
                                )
                            if not description or not isinstance(description, str):
                                raise ValueError(
                                    f"Tool {name} has invalid description: {description}"
                                )
                            if not isinstance(input_schema, dict):
                                raise ValueError(
                                    f"Tool {name} has invalid input_schema: {type(input_schema)}"
                                )

                            logger.debug(
                                f"Tool {name} validation successful: name='{tool_name}', description='{description[:50]}...'"
                            )
                        except Exception as validation_error:
                            logger.warning(
                                f"Tool {name} failed validation: {validation_error}"
                            )
                            failed_registrations.append(
                                f"{name}: Validation failed - {str(validation_error)}"
                            )
                            continue

                        # Use direct registry method for consistency
                        result = self.register_tool(obj, source="code")
                        if result is not None:
                            successful_registrations.append(
                                f"{name} (as '{tool_name}')"
                            )
                            logger.debug(
                                f"Successfully registered tool {name} as '{tool_name}' from {module_name}"
                            )
                        else:
                            logger.debug(
                                f"Tool {name} was not registered (likely due to configuration)"
                            )
                            failed_registrations.append(
                                f"{name}: Not registered due to configuration"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Error registering tool {name} from {module_name}: {e}"
                        )
                        failed_registrations.append(
                            f"{name}: Registration error - {str(e)}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Error processing class {name} from {module_name}: {e}"
                    )
                    failed_registrations.append(f"{name}: Processing error - {str(e)}")

            # Log summary for this module
            if successful_registrations or failed_registrations:
                logger.info(f"Module {module_name} scan results:")
                logger.info(
                    f"  - Successfully registered: {len(successful_registrations)} tools"
                )
                if successful_registrations:
                    for tool in successful_registrations:
                        logger.info(f"    + {tool}")

                if failed_registrations:
                    logger.warning(
                        f"  - Failed registrations: {len(failed_registrations)} tools"
                    )
                    for failure in failed_registrations:
                        logger.warning(f"    - {failure}")
            else:
                logger.debug(f"No tool classes found in module {module_name}")

        except Exception as e:
            logger.error(f"Critical error scanning module {module_name}: {e}")
            logger.exception("Full traceback for module scanning error:")

    def discover_plugin_directory(self, plugin_dir: Path) -> None:
        """Discover and load plugins from a directory.

        Args:
            plugin_dir: Path to the plugin directory
        """
        if not plugin_dir.exists() or not plugin_dir.is_dir():
            logger.warning(
                f"Plugin directory does not exist or is not a directory: {plugin_dir}"
            )
            return

        logger.info(f"Discovering plugins in directory: {plugin_dir}")

        # Check if the directory contains Python files or subdirectories
        plugin_items = list(plugin_dir.iterdir())

        for item in plugin_items:
            # Handle plugin subdirectories
            if item.is_dir() and (item / "__init__.py").exists():
                try:
                    plugin_name = item.name

                    # Add parent directory to sys.path if not already there
                    parent_dir = str(plugin_dir.resolve())
                    if parent_dir not in sys.path:
                        sys.path.insert(0, parent_dir)
                        logger.debug(f"Added to sys.path: {parent_dir}")

                    # Skip if already processed
                    if plugin_name in self.discovered_paths:
                        logger.debug(
                            f"Skipping already processed plugin: {plugin_name}"
                        )
                        continue

                    # Add to discovered paths to avoid reprocessing
                    self.discovered_paths.add(plugin_name)

                    # Look for all files ending with tool.py
                    tool_files = list(item.glob("*tool.py"))
                    if tool_files:
                        for tool_file in tool_files:
                            try:
                                # Extract module name from filename (e.g., "repo_tool.py" -> "repo_tool")
                                module_name = tool_file.stem

                                # Import the module directly using importlib
                                spec = importlib.util.spec_from_file_location(
                                    f"{plugin_name}.{module_name}", str(tool_file)
                                )
                                if spec and spec.loader:
                                    module = importlib.util.module_from_spec(spec)
                                    sys.modules[spec.name] = module
                                    spec.loader.exec_module(module)

                                    # Scan for tools in the module
                                    self._scan_module_for_tools(module)
                                    logger.info(
                                        f"Successfully loaded plugin tool module: {plugin_name}.{module_name}"
                                    )
                                else:
                                    logger.error(f"Failed to create spec for {tool_file}")
                            except Exception as e:
                                logger.error(
                                    f"Error importing tool module from {tool_file}: {e}"
                                )
                except Exception as e:
                    logger.error(f"Error loading plugin {item.name}: {e}")

    def get_all_tools(self) -> List[Type[ToolInterface]]:
        """Get all registered tool classes.

        Returns:
            List of all registered tool classes
        """
        return list(self.tools.values())

    def get_tool_sources(self) -> Dict[str, str]:
        """Get the source of all registered tools.

        Returns:
            Dictionary mapping tool names to their sources ("code" or "yaml")
        """
        return self.tool_sources.copy()

    def get_tools_by_source(self, source: str) -> List[Type[ToolInterface]]:
        """Get all registered tool classes from a specific source.

        Args:
            source: Source of the tools to get ("code" or "yaml")

        Returns:
            List of tool classes from the specified source
        """
        return [
            self.tools[name]
            for name, src in self.tool_sources.items()
            if src == source and name in self.tools
        ]

    def get_all_instances(self) -> List[ToolInterface]:
        """Get instances of all registered tools.

        This will create instances of tools that haven't been instantiated yet.

        Returns:
            List of tool instances filtered according to configuration settings
        """
        # Use the dependency injector if available
        try:
            from mcp_tools.dependency import injector

            instances = injector.get_filtered_instances()
            return list(instances.values())
        except ImportError:
            # Fallback to simple instantiation
            for tool_name in self.tools:
                if tool_name not in self.instances:
                    self._simple_get_tool_instance(tool_name)

            # Filter instances based on configuration
            from mcp_tools.plugin_config import config

            if config.register_code_tools and config.register_yaml_tools:
                return list(self.instances.values())

            filtered_instances = []
            for tool_name, instance in self.instances.items():
                source = self.tool_sources.get(tool_name, "unknown")

                # Use the plugin_config to check if source is enabled
                if config.is_source_enabled(source):
                    filtered_instances.append(instance)

            return filtered_instances

    def clear(self) -> None:
        """Clear all registered tools and instances."""
        self.tools.clear()
        self.instances.clear()
        self.discovered_paths.clear()
        self.yaml_tool_names.clear()
        self.tool_sources.clear()

    def add_yaml_tool_names(self, tool_names: Set[str]) -> None:
        """Add YAML tool names to the registry.

        Args:
            tool_names: Set of tool names defined in YAML
        """
        self.yaml_tool_names.update(tool_names)
        logger.debug(f"Added YAML tool names: {tool_names}")


# Create singleton instance
registry = PluginRegistry()


# Decorator for registering tools
def register_tool(cls=None, *, source="code"):
    """Decorator to register a tool class with the plugin registry.

    Args:
        cls: The class to register
        source: Source of the tool ("code" or "yaml")

    Example:
        @register_tool
        class MyTool(ToolInterface):
            ...

        # Or with source specified:
        @register_tool(source="yaml")
        class YamlTool(ToolInterface):
            ...
    """

    def _register(cls):
        result = registry.register_tool(cls, source=source)
        return cls if result is None else result

    if cls is None:
        return _register
    return _register(cls)


# Auto-discovery function
def discover_and_register_tools():
    """Discover and register all tools in the mcp_tools package and plugin directories with comprehensive error handling."""
    successful_tools = []
    failed_tools = []

    logger.info("Starting comprehensive tool discovery and registration")

    # Load YAML tools first if enabled
    if config.register_yaml_tools:
        logger.info("Attempting to discover YAML tools...")
        try:
            # Use a dynamic import to avoid circular imports
            yaml_tools_module = importlib.import_module("mcp_tools.yaml_tools")

            # Get YAML tool names before registering with error handling
            try:
                get_yaml_names = getattr(yaml_tools_module, "get_yaml_tool_names", None)
                if get_yaml_names:
                    yaml_tool_names = get_yaml_names()
                    registry.add_yaml_tool_names(yaml_tool_names)
                    logger.info(f"Found {len(yaml_tool_names)} YAML tool names")
                else:
                    logger.warning(
                        "get_yaml_tool_names function not found in yaml_tools module"
                    )
            except Exception as e:
                logger.error(f"Error getting YAML tool names: {e}")
                failed_tools.append(f"YAML tool names discovery: {str(e)}")

            # Register YAML tools with error handling
            try:
                yaml_tools_function = getattr(
                    yaml_tools_module, "discover_and_register_yaml_tools", None
                )
                if yaml_tools_function:
                    yaml_tool_classes = yaml_tools_function()
                    if yaml_tool_classes:
                        successful_tools.extend(
                            [f"YAML:{cls.__name__}" for cls in yaml_tool_classes]
                        )
                        logger.info(
                            f"Successfully registered {len(yaml_tool_classes)} YAML tools"
                        )
                    else:
                        logger.info("No YAML tools were registered")
                else:
                    logger.warning(
                        "discover_and_register_yaml_tools function not found"
                    )
            except Exception as e:
                logger.error(f"Error registering YAML tools: {e}")
                failed_tools.append(f"YAML tools registration: {str(e)}")
        except ImportError as e:
            logger.error(f"Could not import YAML tools module: {e}")
            failed_tools.append(f"YAML tools module import: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error loading YAML tools: {e}")
            failed_tools.append(f"YAML tools general error: {str(e)}")
    else:
        logger.info("YAML tool registration is disabled")

    # Then discover code-based tools if enabled
    if config.register_code_tools:
        logger.info("Attempting to discover code-based tools...")

        # Discover tools in the mcp_tools package with error handling
        try:
            registry.discover_tools("mcp_tools")
            logger.info("Successfully completed mcp_tools package discovery")
        except Exception as e:
            logger.error(f"Error discovering tools in mcp_tools package: {e}")
            failed_tools.append(f"mcp_tools package discovery: {str(e)}")

        # Discover tools in plugin root directories with error handling
        try:
            plugin_roots = config.get_plugin_roots()
            logger.info(f"Discovering tools in {len(plugin_roots)} plugin directories")

            for plugin_dir in plugin_roots:
                try:
                    registry.discover_plugin_directory(plugin_dir)
                    logger.debug(
                        f"Successfully processed plugin directory: {plugin_dir}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error discovering tools in plugin directory {plugin_dir}: {e}"
                    )
                    failed_tools.append(f"Plugin directory {plugin_dir}: {str(e)}")
        except Exception as e:
            logger.error(
                f"Error getting plugin roots or processing plugin directories: {e}"
            )
            failed_tools.append(f"Plugin directories discovery: {str(e)}")
    else:
        logger.info("Code tool registration is disabled")

    # Collect summary information with error handling
    try:
        tool_count = len(registry.tools)
        tool_sources = registry.get_tool_sources()
        yaml_count = sum(1 for source in tool_sources.values() if source == "yaml")
        code_count = sum(1 for source in tool_sources.values() if source == "code")

        logger.info(f"Tool discovery summary:")
        logger.info(f"  - Total tools registered: {tool_count}")
        logger.info(f"  - YAML tools: {yaml_count}")
        logger.info(f"  - Code tools: {code_count}")
        logger.info(f"  - Successfully processed: {len(successful_tools)}")
        logger.info(f"  - Failed components: {len(failed_tools)}")

        if failed_tools:
            logger.warning("Failed tool discovery components:")
            for failed_item in failed_tools:
                logger.warning(f"  - {failed_item}")

        logger.debug(f"Registered tool names: {list(registry.tools.keys())}")
        logger.debug(
            f"Tool sources breakdown: {yaml_count} from YAML, {code_count} from code"
        )
        logger.debug(
            f"Tool details: {[(name, source) for name, source in tool_sources.items()]}"
        )
    except Exception as e:
        logger.error(f"Error generating tool discovery summary: {e}")

    logger.info("Tool discovery and registration completed")
