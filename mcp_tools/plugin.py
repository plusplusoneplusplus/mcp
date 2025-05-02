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
    
    def register_tool(self, tool_class: Type[ToolInterface], source: str = "code") -> Optional[Type[ToolInterface]]:
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
            raise TypeError(f"Class {tool_class.__name__} does not implement ToolInterface")
            
        # Skip abstract classes
        if inspect.isabstract(tool_class):
            logger.debug(f"Skipping registration of abstract class {tool_class.__name__}")
            return None
            
        # Create a temporary instance to get the name
        try:
            temp_instance = tool_class()
            tool_name = temp_instance.name
            
            # Check if this tool should be registered based on configuration
            if not config.should_register_tool_class(
                tool_class.__name__, 
                tool_name, 
                self.yaml_tool_names
            ):
                return None
            
            logger.info(f"Registering tool: {tool_name} ({tool_class.__name__}) from {source}")
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
                logger.debug(f"Found tool instance for '{tool_name}' with case-insensitive match: '{registered_name}'")
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
                logger.debug(f"Creating new instance for tool '{tool_name}' with case-insensitive match: '{registered_name}'")
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
        """Scan a module for classes that implement ToolInterface.
        
        Args:
            module: The module to scan
        """
        # Skip scanning if code tools registration is disabled
        if not config.register_code_tools:
            logger.info(f"Skipping code tool registration for module {module.__name__} (register_code_tools=False)")
            return
            
        for name, obj in inspect.getmembers(module):
            # Check if it's a class defined in this module (not imported)
            if (inspect.isclass(obj) and 
                obj.__module__ == module.__name__ and 
                issubclass(obj, ToolInterface) and 
                obj is not ToolInterface):
                
                # Skip abstract classes
                if inspect.isabstract(obj):
                    logger.debug(f"Skipping abstract class {name} from {module.__name__}")
                    continue
                
                try:
                    # Use direct registry method for consistency
                    self.register_tool(obj, source="code")
                except Exception as e:
                    logger.warning(f"Error registering tool {name} from {module.__name__}: {e}")
    
    def discover_plugin_directory(self, plugin_dir: Path) -> None:
        """Discover and load plugins from a directory.
        
        Args:
            plugin_dir: Path to the plugin directory
        """
        if not plugin_dir.exists() or not plugin_dir.is_dir():
            logger.warning(f"Plugin directory does not exist or is not a directory: {plugin_dir}")
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
                        logger.debug(f"Skipping already processed plugin: {plugin_name}")
                        continue
                        
                    # Add to discovered paths to avoid reprocessing
                    self.discovered_paths.add(plugin_name)
                    
                    # Look for tool.py file
                    tool_file = item / "tool.py"
                    if tool_file.exists():
                        try:
                            # Import the module directly using importlib
                            spec = importlib.util.spec_from_file_location(
                                f"{plugin_name}.tool", str(tool_file)
                            )
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                sys.modules[spec.name] = module
                                spec.loader.exec_module(module)
                                
                                # Scan for tools in the module
                                self._scan_module_for_tools(module)
                                logger.info(f"Successfully loaded plugin tool module: {plugin_name}.tool")
                            else:
                                logger.error(f"Failed to create spec for {tool_file}")
                        except Exception as e:
                            logger.error(f"Error importing tool module from {tool_file}: {e}")
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
        return [self.tools[name] for name, src in self.tool_sources.items() 
                if src == source and name in self.tools]
    
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
    """Discover and register all tools in the mcp_tools package and plugin directories."""
    # Load YAML tools first if enabled
    if config.register_yaml_tools:
        try:
            # Use a dynamic import to avoid circular imports
            yaml_tools_module = importlib.import_module("mcp_tools.yaml_tools")
            
            # Get YAML tool names before registering
            get_yaml_names = getattr(yaml_tools_module, "get_yaml_tool_names", None)
            if get_yaml_names:
                yaml_tool_names = get_yaml_names()
                registry.add_yaml_tool_names(yaml_tool_names)
            
            # Register YAML tools
            yaml_tools_function = getattr(yaml_tools_module, "discover_and_register_yaml_tools", None)
            if yaml_tools_function:
                yaml_tools_function()
            else:
                logger.warning("YAML tools function not found")
        except Exception as e:
            logger.warning(f"Error loading YAML tools: {e}")
    
    # Then discover code-based tools if enabled
    if config.register_code_tools:
        # Discover tools in the mcp_tools package
        registry.discover_tools("mcp_tools")
        
        # Discover tools in plugin root directories
        plugin_roots = config.get_plugin_roots()
        for plugin_dir in plugin_roots:
            registry.discover_plugin_directory(plugin_dir)
    
    # For debugging - Disable this logging in production
    tool_count = len(registry.tools)
    tool_sources = registry.get_tool_sources()
    yaml_count = sum(1 for source in tool_sources.values() if source == "yaml")
    code_count = sum(1 for source in tool_sources.values() if source == "code")
    
    logger.debug(f"Registered {tool_count} tools: {list(registry.tools.keys())}") 
    logger.debug(f"Tool sources: {yaml_count} from YAML, {code_count} from code")
    logger.debug(f"Tool details: {[(name, source) for name, source in tool_sources.items()]}") 