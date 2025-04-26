import importlib
import inspect
import logging
import os
import pkgutil
from typing import Dict, List, Type, Set, Optional, Any

from mcp_tools.interfaces import ToolInterface

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
    
    def register_tool(self, tool_class: Type[ToolInterface]) -> None:
        """Register a tool class.
        
        Args:
            tool_class: A class that implements ToolInterface
        
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
            return
            
        # Create a temporary instance to get the name
        try:
            temp_instance = tool_class()
            tool_name = temp_instance.name
            
            logger.info(f"Registering tool: {tool_name} ({tool_class.__name__})")
            self.tools[tool_name] = tool_class
        except Exception as e:
            logger.error(f"Error creating instance of {tool_class.__name__}: {e}")
    
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
                
                # Skip YamlToolBase which is only meant to be a base class
                if name == "YamlToolBase":
                    logger.debug(f"Skipping base class {name} from {module.__name__}")
                    continue
                
                try:
                    self.register_tool(obj)
                except Exception as e:
                    logger.warning(f"Error registering tool {name} from {module.__name__}: {e}")
    
    def get_all_tools(self) -> List[Type[ToolInterface]]:
        """Get all registered tool classes.
        
        Returns:
            List of all registered tool classes
        """
        return list(self.tools.values())
    
    def get_all_instances(self) -> List[ToolInterface]:
        """Get instances of all registered tools.
        
        This will create instances of tools that haven't been instantiated yet.
        
        Returns:
            List of tool instances
        """
        # Use the dependency injector if available
        try:
            from mcp_tools.dependency import injector
            instances = injector.resolve_all_dependencies()
            return list(instances.values())
        except ImportError:
            # Fallback to simple instantiation
            for tool_name in self.tools:
                if tool_name not in self.instances:
                    self._simple_get_tool_instance(tool_name)
                    
            return list(self.instances.values())
    
    def clear(self) -> None:
        """Clear all registered tools and instances."""
        self.tools.clear()
        self.instances.clear()
        self.discovered_paths.clear()


# Create singleton instance
registry = PluginRegistry()


# Decorator for registering tools
def register_tool(cls=None):
    """Decorator to register a tool class with the plugin registry.
    
    Example:
        @register_tool
        class MyTool(ToolInterface):
            ...
    """
    def _register(cls):
        registry.register_tool(cls)
        return cls
        
    if cls is None:
        return _register
    return _register(cls)


# Auto-discovery function
def discover_and_register_tools():
    """Discover and register all tools in the mcp_tools package."""
    # First discover code-based tools
    registry.discover_tools("mcp_tools")
    
    # Then discover YAML-based tools
    try:
        # Use a dynamic import to avoid circular imports
        yaml_tools_module = importlib.import_module("mcp_tools.yaml_tools")
        yaml_tools_function = getattr(yaml_tools_module, "discover_and_register_yaml_tools", None)
        if yaml_tools_function:
            yaml_tools_function()
    except Exception as e:
        logger.warning(f"Error loading YAML tools: {e}") 