"""Dependency injection system for MCP tools."""

import logging
import inspect
from typing import Dict, Any, Type, Optional, List, Set, Callable, Tuple

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import registry

logger = logging.getLogger(__name__)

class DependencyInjector:
    """A dependency injector for MCP tools.
    
    This class helps manage dependencies between tools by:
    1. Tracking dependencies between tools
    2. Creating and initializing tools with their dependencies
    3. Resolving circular dependencies when possible
    
    Example:
        injector = DependencyInjector()
        
        # Register a tool with its dependencies
        injector.register_dependency("azure_repo_client", ["command_executor"])
        
        # Get a tool with all its dependencies resolved
        azure_client = injector.get_tool_instance("azure_repo_client")
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DependencyInjector, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the dependency injector."""
        # Dictionary of tool dependencies: {tool_name: [dependency_names]}
        self.dependencies: Dict[str, List[str]] = {}
        
        # Dictionary of tool constructors with parameter information
        self.tool_constructors: Dict[str, Dict[str, Any]] = {}
        
        # Dictionary of tool instances
        self.instances: Dict[str, ToolInterface] = {}
    
    def register_dependency(self, tool_name: str, dependency_names: List[str]) -> None:
        """Register dependencies for a tool.
        
        Args:
            tool_name: Name of the tool
            dependency_names: List of dependency tool names
        """
        logger.debug(f"Registering dependencies for {tool_name}: {dependency_names}")
        self.dependencies[tool_name] = dependency_names
    
    def analyze_tool_constructor(self, tool_class: Type[ToolInterface]) -> Dict[str, Any]:
        """Analyze a tool's constructor to extract parameter information.
        
        Args:
            tool_class: The tool class to analyze
            
        Returns:
            Dictionary with constructor parameter information
        """
        sig = inspect.signature(tool_class.__init__)
        parameters = {}
        
        for param_name, param in sig.parameters.items():
            # Skip 'self' parameter
            if param_name == "self":
                continue
                
            # Get parameter type hint if available
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else None
            
            # Get default value if available
            default_value = param.default if param.default != inspect.Parameter.empty else None
            
            # Store parameter information
            parameters[param_name] = {
                "name": param_name,
                "type": param_type,
                "default": default_value,
                "required": param.default == inspect.Parameter.empty
            }
        
        return {
            "parameters": parameters,
            "has_var_kwargs": any(param.kind == inspect.Parameter.VAR_KEYWORD 
                                for param in sig.parameters.values())
        }
    
    def register_tool_constructor(self, tool_name: str, constructor_info: Dict[str, Any]) -> None:
        """Register constructor information for a tool.
        
        Args:
            tool_name: Name of the tool
            constructor_info: Dictionary with constructor parameter information
        """
        self.tool_constructors[tool_name] = constructor_info
    
    def _detect_circular_dependencies(self, tool_name: str, visited: Set[str] = None) -> Set[str]:
        """Detect circular dependencies for a tool.
        
        Args:
            tool_name: Name of the tool to check
            visited: Set of already visited tool names
            
        Returns:
            Set of tools that form a circular dependency
        """
        if visited is None:
            visited = set()
            
        if tool_name in visited:
            return {tool_name}
            
        visited.add(tool_name)
        
        circular = set()
        for dep_name in self.dependencies.get(tool_name, []):
            if dep_name in visited:
                circular.add(dep_name)
            else:
                circular.update(self._detect_circular_dependencies(dep_name, visited.copy()))
                
        return circular
    
    def get_tool_instance(self, tool_name: str, context: Dict[str, Any] = None) -> Optional[ToolInterface]:
        """Get or create an instance of a tool with its dependencies resolved.
        
        Args:
            tool_name: Name of the tool to get
            context: Optional context with already resolved instances
            
        Returns:
            The tool instance or None if it can't be created
        """
        # Return existing instance if available
        if tool_name in self.instances:
            return self.instances[tool_name]
            
        if context is None:
            context = {}
            
        # Check if tool is registered
        tool_class = registry.tools.get(tool_name)
        if not tool_class:
            logger.error(f"Tool {tool_name} not registered")
            return None
            
        # Analyze constructor if not already done
        if tool_name not in self.tool_constructors:
            constructor_info = self.analyze_tool_constructor(tool_class)
            self.register_tool_constructor(tool_name, constructor_info)
            
        # Resolve dependencies
        dependencies = {}
        for dep_name in self.dependencies.get(tool_name, []):
            # Skip if already in context
            if dep_name in context:
                dependencies[dep_name] = context[dep_name]
                continue
                
            # Detect circular dependencies
            circular = self._detect_circular_dependencies(dep_name, {tool_name})
            if circular:
                logger.warning(f"Circular dependency detected for {tool_name} -> {dep_name}: {circular}")
                
                # For circular dependencies, use the registry's instance
                dep_instance = registry.get_tool_instance(dep_name)
                if dep_instance:
                    dependencies[dep_name] = dep_instance
                    context[dep_name] = dep_instance
                continue
                
            # Recursively resolve dependency
            dep_instance = self.get_tool_instance(dep_name, context.copy())
            if dep_instance:
                dependencies[dep_name] = dep_instance
                context[dep_name] = dep_instance
                
        # Create tool instance with resolved dependencies
        try:
            # Map dependencies to constructor parameters
            kwargs = {}
            constructor_info = self.tool_constructors[tool_name]
            parameters = constructor_info["parameters"]
            
            for param_name, param_info in parameters.items():
                # Try to find matching dependency
                for dep_name, dep_instance in dependencies.items():
                    if dep_name == param_name or dep_name.endswith("_" + param_name):
                        kwargs[param_name] = dep_instance
                        break
                        
            # Create instance
            instance = tool_class(**kwargs)
            self.instances[tool_name] = instance
            return instance
            
        except Exception as e:
            logger.error(f"Error creating instance of {tool_name}: {e}")
            return None
    
    def resolve_all_dependencies(self) -> Dict[str, ToolInterface]:
        """Resolve dependencies for all registered tools.
        
        Returns:
            Dictionary of tool instances filtered by tool source based on config
        """
        # Discover all dependencies from constructor parameters
        for tool_name, tool_class in registry.tools.items():
            if tool_name not in self.tool_constructors:
                constructor_info = self.analyze_tool_constructor(tool_class)
                self.register_tool_constructor(tool_name, constructor_info)
                
                # Infer dependencies from parameter names
                dependencies = []
                for param_name in constructor_info["parameters"]:
                    # Look for registered tools that match parameter names
                    for registered_tool in registry.tools:
                        if registered_tool == param_name or registered_tool.endswith("_" + param_name):
                            dependencies.append(registered_tool)
                            break
                
                # Register inferred dependencies
                if dependencies:
                    self.register_dependency(tool_name, dependencies)
        
        # Create instances for all tools
        for tool_name in registry.tools:
            self.get_tool_instance(tool_name)
            
        # Return filtered instances based on configuration
        return self.get_filtered_instances()
    
    def get_all_instances(self) -> Dict[str, ToolInterface]:
        """Get all tool instances without filtering.
        
        Returns:
            Dictionary of all tool instances regardless of source
        """
        return self.instances.copy()
    
    def get_filtered_instances(self) -> Dict[str, ToolInterface]:
        """Get tool instances filtered by configuration settings.
        
        Returns:
            Dictionary of tool instances filtered by tool source based on config
        """
        from mcp_tools.plugin_config import config
        
        # If both sources are enabled, return all instances
        if config.register_code_tools and config.register_yaml_tools:
            return self.instances.copy()
        
        # Get tool sources
        tool_sources = registry.get_tool_sources()
        
        # Filter instances based on config
        filtered_instances = {}
        for tool_name, instance in self.instances.items():
            source = tool_sources.get(tool_name, "unknown")
            
            # Use the plugin_config to check if source is enabled
            if config.is_source_enabled(source):
                filtered_instances[tool_name] = instance
                
        return filtered_instances
    
    def clear(self) -> None:
        """Clear all registered dependencies and instances."""
        self.dependencies.clear()
        self.tool_constructors.clear()
        self.instances.clear()


# Create singleton instance
injector = DependencyInjector() 