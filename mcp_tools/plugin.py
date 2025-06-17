import importlib
import importlib.util
import inspect
import logging
import os
import pkgutil
import sys
import time
from typing import Dict, List, Type, Set, Optional, Any, Union
from pathlib import Path

from mcp_tools.interfaces import ToolInterface
from mcp_tools.constants import Ecosystem, OSType
from mcp_tools.plugin_config import config

logger = logging.getLogger(__name__)

# Simple timing utility for plugin discovery
from contextlib import contextmanager

@contextmanager
def time_plugin_operation(name: str):
    start_time = time.time()
    logger.info(f"🚀 Starting {name}...")
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"✅ {name} completed in {duration:.2f}s")


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
        self.tool_ecosystems: Dict[str, Optional[str]] = {}  # Track tool ecosystem
        self.tool_os: Dict[str, Optional[str]] = {}  # Track tool OS compatibility


    def register_tool(
        self,
        tool_class: Type[ToolInterface],
        source: str = "code",
        ecosystem: Optional[Union[str, Ecosystem]] = None,
        os_type: Optional[Union[str, OSType]] = None,
    ) -> Optional[Type[ToolInterface]]:
        """Register a tool class.

        Args:
            tool_class: A class that implements ToolInterface
            source: Source of the tool ("code" or "yaml")
            ecosystem: Ecosystem the tool belongs to (e.g., "microsoft", "general")
            os_type: OS compatibility ("windows", "non-windows", "all")

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
                tool_class.__name__, tool_name, self.yaml_tool_names,
                ecosystem=ecosystem, os_type=os_type
            ):
                return None

            logger.info(
                f"Registering tool: {tool_name} ({tool_class.__name__}) from {source}"
                f"{f' [ecosystem: {ecosystem}]' if ecosystem else ''}"
                f"{f' [os: {os_type}]' if os_type else ''}"
            )
            self.tools[tool_name] = tool_class
            self.tool_sources[tool_name] = source
            self.tool_ecosystems[tool_name] = (
                str(ecosystem) if ecosystem is not None else None
            )
            self.tool_os[tool_name] = str(os_type) if os_type is not None else None
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

                        # Get ecosystem from the class metadata (set by decorator) or instance if available
                        ecosystem = getattr(obj, '_mcp_ecosystem', getattr(temp_instance, 'ecosystem', None))

                        # Get OS type from the class metadata (set by decorator) or instance if available
                        os_type = getattr(obj, '_mcp_os', getattr(temp_instance, 'os_type', None))

                        # Check if this tool should be registered based on configuration
                        if not config.should_register_tool_class(
                            name, tool_name, self.yaml_tool_names,
                            ecosystem=ecosystem, os_type=os_type
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
                        result = self.register_tool(obj, source="code", ecosystem=ecosystem, os_type=os_type)
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

        # Plugin Directory Discovery Logging
        logger.info(f"🔍 Scanning plugin directory: {plugin_dir}")

        # Check if the directory contains Python files or subdirectories
        plugin_items = list(plugin_dir.iterdir())

        # Find plugin directories (subdirectories with __init__.py)
        plugin_subdirs = [
            item for item in plugin_items
            if item.is_dir() and (item / "__init__.py").exists()
        ]

        if plugin_subdirs:
            plugin_names = [item.name for item in plugin_subdirs]
            logger.info(f"📁 Found plugin directories: {', '.join(plugin_names)}")
        else:
            logger.info(f"📁 No plugin directories found in: {plugin_dir}")
            return

        # Track plugin loading statistics
        plugins_discovered = 0
        plugins_loaded = 0
        plugins_failed = 0
        plugin_details = []

        for item in plugin_subdirs:
            plugins_discovered += 1
            plugin_start_time = time.time()

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

                # Individual Plugin Loading Logs
                logger.info(f"🔌 Loading plugin: {plugin_name}")

                if tool_files:
                    logger.info(f"  📄 Found tool modules: {', '.join([f.name for f in tool_files])}")

                    loaded_tools = []
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
                                tools_before = len(self.tools)
                                self._scan_module_for_tools(module)
                                tools_after = len(self.tools)
                                tools_added = tools_after - tools_before

                                if tools_added > 0:
                                    loaded_tools.append(module_name)
                                    logger.info(f"  ✅ Successfully loaded: {module_name} ({tools_added} tools)")
                                else:
                                    logger.info(f"  ⚠️  No tools found in: {module_name}")
                            else:
                                logger.error(f"  ❌ Failed to create spec for {tool_file}")
                        except Exception as e:
                            logger.error(f"  ❌ Error importing tool module from {tool_file}: {e}")

                    if loaded_tools:
                        plugins_loaded += 1
                        plugin_duration = time.time() - plugin_start_time
                        logger.info(f"  ⏱️  Plugin loaded in {plugin_duration:.3f}s")
                        plugin_details.append({
                            "name": plugin_name,
                            "status": "success",
                            "duration": plugin_duration,
                            "tool_modules": loaded_tools,
                            "source_path": str(item)
                        })
                    else:
                        plugins_failed += 1
                        plugin_details.append({
                            "name": plugin_name,
                            "status": "failed",
                            "duration": time.time() - plugin_start_time,
                            "error": "No tools successfully loaded",
                            "source_path": str(item)
                        })
                else:
                    logger.info(f"  📄 No tool modules found (*tool.py)")
                    plugins_failed += 1
                    plugin_details.append({
                        "name": plugin_name,
                        "status": "failed",
                        "duration": time.time() - plugin_start_time,
                        "error": "No tool modules found",
                        "source_path": str(item)
                    })

            except Exception as e:
                plugins_failed += 1
                plugin_duration = time.time() - plugin_start_time
                logger.error(f"🔌 Error loading plugin {item.name}: {e}")
                plugin_details.append({
                    "name": item.name,
                    "status": "failed",
                    "duration": plugin_duration,
                    "error": str(e),
                    "source_path": str(item)
                })

        # Plugin Loading Summary for this directory
        logger.info(f"📊 Plugin directory summary for {plugin_dir}:")
        logger.info(f"  • Total plugins discovered: {plugins_discovered}")
        logger.info(f"  • Successfully loaded: {plugins_loaded}")
        logger.info(f"  • Failed to load: {plugins_failed}")

        if plugin_details:
            logger.info(f"  • Plugin details:")
            for detail in plugin_details:
                status_icon = "✅" if detail["status"] == "success" else "❌"
                logger.info(f"    {status_icon} {detail['name']}: {detail['status']} ({detail['duration']:.3f}s)")
                if detail["status"] == "success" and "tool_modules" in detail:
                    logger.info(f"      └─ Modules: {', '.join(detail['tool_modules'])}")
                elif detail["status"] == "failed" and "error" in detail:
                    logger.info(f"      └─ Error: {detail['error']}")

    def _log_plugin_discovery_start(self, plugin_dir: Path):
        """Log the start of plugin discovery for a directory.

        Args:
            plugin_dir: Path to the plugin directory being scanned
        """
        logger.info(f"🔍 Scanning plugin directory: {plugin_dir}")

    def _log_plugin_loaded(self, plugin_name: str, tool_files: List[Path], duration: float):
        """Log successful plugin loading with timing information.

        Args:
            plugin_name: Name of the loaded plugin
            tool_files: List of tool files that were processed
            duration: Time taken to load the plugin in seconds
        """
        logger.info(f"🔌 Loading plugin: {plugin_name} ({duration:.2f}s)")
        for tool_file in tool_files:
            logger.info(f"  📄 Found tool module: {tool_file.name}")

    def _log_plugin_failed(self, plugin_name: str, error: str, duration: float):
        """Log failed plugin loading with error details.

        Args:
            plugin_name: Name of the plugin that failed to load
            error: Error message describing the failure
            duration: Time taken before failure in seconds
        """
        logger.error(f"🔌 Failed to load plugin: {plugin_name} ({duration:.2f}s)")
        logger.error(f"  ❌ Error: {error}")

    def get_plugin_loading_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of plugin loading results.

        Returns:
            Dictionary containing plugin loading statistics and details
        """
        tool_sources = self.get_tool_sources()

        # Group tools by source directory (approximate)
        plugin_groups = {}
        for tool_name, source in tool_sources.items():
            if source == "code":
                # Try to determine plugin source from discovered paths
                plugin_source = "mcp_tools"  # Default for built-in tools
                for discovered_path in self.discovered_paths:
                    if discovered_path in tool_name.lower():
                        plugin_source = discovered_path
                        break

                if plugin_source not in plugin_groups:
                    plugin_groups[plugin_source] = []
                plugin_groups[plugin_source].append(tool_name)

        return {
            "total_tools_registered": len(self.tools),
            "code_tools": len([s for s in tool_sources.values() if s == "code"]),
            "yaml_tools": len([s for s in tool_sources.values() if s == "yaml"]),
            "plugin_groups": plugin_groups,
            "discovered_plugin_paths": list(self.discovered_paths),
            "tool_sources": tool_sources
        }

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
        """Get all tools from a specific source.

        Args:
            source: The source to filter by ("code" or "yaml")

        Returns:
            List of tool classes from the specified source
        """
        return [
            tool_class
            for tool_name, tool_class in self.tools.items()
            if self.tool_sources.get(tool_name) == source
        ]

    def get_tools_by_ecosystem(self, ecosystem: str) -> List[Type[ToolInterface]]:
        """Get all tools from a specific ecosystem.

        Args:
            ecosystem: The ecosystem to filter by (case-insensitive)

        Returns:
            List of tool classes from the specified ecosystem
        """
        ecosystem_lower = ecosystem.lower()
        return [
            tool_class
            for tool_name, tool_class in self.tools.items()
            if (self.tool_ecosystems.get(tool_name) or "").lower() == ecosystem_lower
        ]



    def get_available_ecosystems(self) -> Set[str]:
        """Get all available ecosystems from registered tools.

        Returns:
            Set of ecosystem names
        """
        ecosystems = set()
        for ecosystem in self.tool_ecosystems.values():
            if ecosystem:
                ecosystems.add(ecosystem)
        return ecosystems



    def get_tool_ecosystems(self) -> Dict[str, Optional[str]]:
        """Get the ecosystem mapping for all tools.

        Returns:
            Dictionary mapping tool names to their ecosystems
        """
        return self.tool_ecosystems.copy()

    def get_tools_by_os(self, os_type: str) -> List[Type[ToolInterface]]:
        """Get all tools compatible with a specific OS.

        Args:
            os_type: The OS to filter by (case-insensitive)

        Returns:
            List of tool classes compatible with the specified OS
        """
        os_lower = os_type.lower()
        return [
            tool_class
            for tool_name, tool_class in self.tools.items()
            if (self.tool_os.get(tool_name) or "").lower() == os_lower
        ]

    def get_available_os(self) -> Set[str]:
        """Get all available OS types from registered tools.

        Returns:
            Set of OS types
        """
        os_types = set()
        for os_type in self.tool_os.values():
            if os_type:
                os_types.add(os_type)
        return os_types

    def get_tool_os(self) -> Dict[str, Optional[str]]:
        """Get the OS mapping for all tools.

        Returns:
            Dictionary mapping tool names to their OS compatibility
        """
        return self.tool_os.copy()



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
        self.tool_ecosystems.clear()
        self.tool_os.clear()

    def add_yaml_tool_names(self, tool_names: Set[str]) -> None:
        """Add YAML tool names to the registry.

        Args:
            tool_names: Set of tool names defined in YAML
        """
        self.yaml_tool_names.update(tool_names)
        logger.debug(f"Added YAML tool names: {tool_names}")

    def get_available_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata about all available plugins.

        Returns:
            Dictionary mapping plugin names to their metadata including
            registration status, source, and enable/disable state
        """
        from mcp_tools.plugin_config import config

        available_plugins = {}

        # Add registered tools
        for tool_name, tool_class in self.tools.items():
            source = self.tool_sources.get(tool_name, "unknown")
            available_plugins[tool_name] = {
                "name": tool_name,
                "class_name": tool_class.__name__,
                "source": source,
                "registered": True,
                "enabled": config.is_plugin_enabled(tool_name),
                "explicitly_configured": (
                    tool_name in config.enabled_plugins or
                    tool_name in config.disabled_plugins
                ),
                "has_instance": tool_name in self.instances,
                "ecosystem": self.tool_ecosystems.get(tool_name, None),
                "os": self.tool_os.get(tool_name, None)
            }

        # Add YAML tool names that might not be registered yet
        for tool_name in self.yaml_tool_names:
            if tool_name not in available_plugins:
                available_plugins[tool_name] = {
                    "name": tool_name,
                    "class_name": f"YamlTool_{tool_name}",
                    "source": "yaml",
                    "registered": False,
                    "enabled": config.is_plugin_enabled(tool_name),
                    "explicitly_configured": (
                        tool_name in config.enabled_plugins or
                        tool_name in config.disabled_plugins
                    ),
                    "has_instance": False,
                    "ecosystem": None
                }

        # Add explicitly configured plugins that might not be discovered yet
        config_plugins = config.enabled_plugins.union(config.disabled_plugins)
        for plugin_name in config_plugins:
            if plugin_name not in available_plugins:
                available_plugins[plugin_name] = {
                    "name": plugin_name,
                    "class_name": "Unknown",
                    "source": "configuration",
                    "registered": False,
                    "enabled": config.is_plugin_enabled(plugin_name),
                    "explicitly_configured": True,
                    "has_instance": False,
                    "ecosystem": None
                }

        return available_plugins

    def get_enabled_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata about all enabled plugins.

        Returns:
            Dictionary mapping enabled plugin names to their metadata
        """
        all_plugins = self.get_available_plugins()
        return {
            name: metadata
            for name, metadata in all_plugins.items()
            if metadata["enabled"]
        }

    def get_disabled_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata about all disabled plugins.

        Returns:
            Dictionary mapping disabled plugin names to their metadata
        """
        all_plugins = self.get_available_plugins()
        return {
            name: metadata
            for name, metadata in all_plugins.items()
            if not metadata["enabled"]
        }


# Create singleton instance
registry = PluginRegistry()


# Decorator for registering tools
def register_tool(
    cls=None,
    *,
    source: str = "code",
    ecosystem: Optional[Union[str, Ecosystem]] = None,
    os_type: Optional[Union[str, OSType]] = None,
):
    """Decorator to register a tool class with the plugin registry.

    Args:
        cls: The class to register
        source: Source of the tool ("code" or "yaml")
        ecosystem: Ecosystem the tool belongs to (e.g., "microsoft", "general")
        os_type: OS compatibility ("windows", "non-windows", "all")

    Example:
        @register_tool
        class MyTool(ToolInterface):
            ...

        # Or with metadata specified:
        @register_tool(source="yaml", ecosystem="microsoft", os_type="windows")
        class AzureTool(ToolInterface):
            ...
    """

    def _register(cls):
        # Store metadata on the class for discovery
        cls._mcp_ecosystem = str(ecosystem) if ecosystem is not None else None
        cls._mcp_source = source
        cls._mcp_os = str(os_type) if os_type is not None else None

        result = registry.register_tool(
            cls,
            source=source,
            ecosystem=ecosystem,
            os_type=os_type,
        )
        return cls if result is None else result

    if cls is None:
        return _register
    return _register(cls)


# Auto-discovery function
def discover_and_register_tools():
    """Discover and register all tools in the mcp_tools package and plugin directories with comprehensive error handling."""
    successful_tools = []
    failed_tools = []

    logger.info("🚀 Starting comprehensive tool discovery and registration")

    # Load YAML tools first if enabled
    if config.register_yaml_tools:
        try:
            with time_plugin_operation("YAML Tools Discovery"):
                logger.info("🔍 Attempting to discover YAML tools...")
                # Use a dynamic import to avoid circular imports
                yaml_tools_module = importlib.import_module("mcp_tools.yaml_tools")

                # Get YAML tool names before registering with error handling
                try:
                    get_yaml_names = getattr(yaml_tools_module, "get_yaml_tool_names", None)
                    if get_yaml_names:
                        yaml_tool_names = get_yaml_names()
                        registry.add_yaml_tool_names(yaml_tool_names)
                        logger.info(f"📄 Found {len(yaml_tool_names)} YAML tool names")
                    else:
                        logger.warning(
                            "⚠️  get_yaml_tool_names function not found in yaml_tools module"
                        )
                except Exception as e:
                    logger.error(f"❌ Error getting YAML tool names: {e}")
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
                                f"✅ Successfully registered {len(yaml_tool_classes)} YAML tools"
                            )
                        else:
                            logger.info("📄 No YAML tools were registered")
                    else:
                        logger.warning(
                            "⚠️  discover_and_register_yaml_tools function not found"
                        )
                except Exception as e:
                    logger.error(f"❌ Error registering YAML tools: {e}")
                    failed_tools.append(f"YAML tools registration: {str(e)}")
        except ImportError as e:
            logger.error(f"❌ Could not import YAML tools module: {e}")
            failed_tools.append(f"YAML tools module import: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Unexpected error loading YAML tools: {e}")
            failed_tools.append(f"YAML tools general error: {str(e)}")
    else:
        logger.info("📄 YAML tool registration is disabled")

    # Then discover code-based tools if enabled
    if config.register_code_tools:
        with time_plugin_operation("Code-based Tools Discovery"):
            logger.info("🔍 Attempting to discover code-based tools...")

            # Discover tools in the mcp_tools package with error handling
            try:
                with time_plugin_operation("mcp_tools Package Discovery"):
                    logger.info("🔍 Scanning mcp_tools package...")
                    registry.discover_tools("mcp_tools")
                    logger.info("✅ Successfully completed mcp_tools package discovery")
            except Exception as e:
                logger.error(f"❌ Error discovering tools in mcp_tools package: {e}")
                failed_tools.append(f"mcp_tools package discovery: {str(e)}")

            # Discover tools in plugin root directories with error handling
            try:
                plugin_roots = config.get_plugin_roots()
                logger.info(f"🔍 Discovering tools in {len(plugin_roots)} plugin root directories")

                # Log plugin root directories being scanned
                for i, plugin_root in enumerate(plugin_roots, 1):
                    logger.info(f"  📁 Plugin root {i}: {plugin_root}")

                with time_plugin_operation("Plugin Directories Discovery"):
                    for plugin_dir in plugin_roots:
                        try:
                            registry.discover_plugin_directory(plugin_dir)
                            logger.debug(
                                f"✅ Successfully processed plugin directory: {plugin_dir}"
                            )
                        except Exception as e:
                            logger.error(
                                f"❌ Error discovering tools in plugin directory {plugin_dir}: {e}"
                            )
                            failed_tools.append(f"Plugin directory {plugin_dir}: {str(e)}")
            except Exception as e:
                logger.error(
                    f"❌ Error getting plugin roots or processing plugin directories: {e}"
                )
                failed_tools.append(f"Plugin directories discovery: {str(e)}")
    else:
        logger.info("🔧 Code tool registration is disabled")

    # Generate comprehensive plugin loading summary
    try:
        tool_count = len(registry.tools)
        tool_sources = registry.get_tool_sources()
        yaml_count = sum(1 for source in tool_sources.values() if source == "yaml")
        code_count = sum(1 for source in tool_sources.values() if source == "code")

        # Get plugin loading summary
        plugin_summary = registry.get_plugin_loading_summary()

        # Comprehensive Plugin Loading Summary
        logger.info("=" * 60)
        logger.info("📊 COMPREHENSIVE PLUGIN LOADING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"🔧 Total tools registered: {tool_count}")
        logger.info(f"📄 YAML tools: {yaml_count}")
        logger.info(f"🔧 Code tools: {code_count}")
        logger.info(f"✅ Successfully processed components: {len(successful_tools)}")
        logger.info(f"❌ Failed components: {len(failed_tools)}")

        # Plugin source breakdown
        if plugin_summary.get("plugin_groups"):
            logger.info(f"📁 Plugin sources:")
            for plugin_source, tools in plugin_summary["plugin_groups"].items():
                logger.info(f"  • {plugin_source}: {', '.join(tools) if tools else 'None'}")

        # Plugin root directories
        plugin_roots = config.get_plugin_roots()
        if plugin_roots:
            logger.info(f"📂 Plugin root directories scanned:")
            for plugin_root in plugin_roots:
                logger.info(f"  • {plugin_root}")

        # Discovered plugin paths
        if plugin_summary.get("discovered_plugin_paths"):
            logger.info(f"🔌 Discovered plugin directories:")
            for plugin_path in plugin_summary["discovered_plugin_paths"]:
                logger.info(f"  • {plugin_path}")

        if failed_tools:
            logger.warning("⚠️  Failed tool discovery components:")
            for failed_item in failed_tools:
                logger.warning(f"  ❌ {failed_item}")

        logger.debug(f"Registered tool names: {list(registry.tools.keys())}")
        logger.debug(
            f"Tool sources breakdown: {yaml_count} from YAML, {code_count} from code"
        )
        logger.debug(
            f"Tool details: {[(name, source) for name, source in tool_sources.items()]}"
        )

        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Error generating tool discovery summary: {e}")

    logger.info("🎉 Tool discovery and registration completed")
