# Dependency Injection in MCP Tools

This guide explains how to use the dependency injection system in the MCP Tools framework.

## Overview

The MCP Tools dependency injection system allows tools to:

1. Declare their dependencies on other tools
2. Automatically get instances of those dependencies
3. Work with circular dependencies
4. Be tested in isolation with mock dependencies

## How Dependency Injection Works

Instead of directly instantiating dependencies or using global instances, tools should:

1. Accept dependencies as constructor parameters with default values of `None`
2. Use the dependency injector to obtain instances if not provided

## Basic Usage

### Declaring Dependencies in Tools

Tools should declare their dependencies in their constructors:

```python
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

@register_tool
class MyTool(ToolInterface):
    def __init__(self, command_executor=None, environment_manager=None):
        # Get command executor from injector if not provided
        if command_executor is None:
            from mcp_tools.dependency import injector
            self.command_executor = injector.get_tool_instance("command_executor")
            if not self.command_executor:
                raise ValueError("CommandExecutor not found")
        else:
            self.command_executor = command_executor
            
        # Get environment manager from injector if not provided
        if environment_manager is None:
            from mcp_tools.dependency import injector
            self.environment_manager = injector.get_tool_instance("environment_manager")
            if not self.environment_manager:
                raise ValueError("EnvironmentManager not found")
        else:
            self.environment_manager = environment_manager
            
    # Implement the required interface methods...
```

### Using the Dependency Injector

The dependency injector provides several ways to work with tool dependencies:

```python
from mcp_tools.dependency import injector
from mcp_tools.plugin import discover_and_register_tools

# Discover and register tools
discover_and_register_tools()

# Option 1: Manually register dependencies
injector.register_dependency("azure_repo_client", ["command_executor"])

# Option 2: Let the injector discover dependencies automatically
# (It analyzes constructor parameters of all registered tools)
injector.resolve_all_dependencies()

# Option 3: Get a specific tool with its dependencies resolved
my_tool = injector.get_tool_instance("my_tool")
```

## Advanced Usage

### Automatic Dependency Resolution

The dependency injector can automatically discover and resolve dependencies by analyzing tool constructors:

```python
# Automatic dependency discovery and resolution
from mcp_tools.dependency import injector
from mcp_tools.plugin import discover_and_register_tools

# Discover all tools
discover_and_register_tools()

# Analyze and resolve all dependencies
all_tools = injector.resolve_all_dependencies()
```

### Handling Circular Dependencies

The dependency injector can handle circular dependencies by:

1. Detecting circular dependency chains
2. Using registry instances to break the cycle
3. Warning about potential issues

```python
# Tools with circular dependencies
@register_tool
class ToolA(ToolInterface):
    def __init__(self, tool_b=None):
        if tool_b is None:
            from mcp_tools.dependency import injector
            self.tool_b = injector.get_tool_instance("tool_b")
        else:
            self.tool_b = tool_b
            
@register_tool
class ToolB(ToolInterface):
    def __init__(self, tool_a=None):
        if tool_a is None:
            from mcp_tools.dependency import injector
            self.tool_a = injector.get_tool_instance("tool_a")
        else:
            self.tool_a = tool_a

# The injector will detect and handle this circular dependency
from mcp_tools.dependency import injector
tool_a = injector.get_tool_instance("tool_a")  # Works despite circular dependency
```

## Testing with Dependencies

When testing tools with dependencies, you can:

1. Create mock dependencies
2. Pass them explicitly to the tool constructor
3. Test the tool in isolation

```python
import unittest
from unittest.mock import MagicMock

class TestMyTool(unittest.TestCase):
    def test_my_tool(self):
        # Create mock dependencies
        mock_executor = MagicMock()
        mock_executor.execute.return_value = {"success": True, "output": "test"}
        
        # Create the tool with mock dependencies
        from my_package.my_tool import MyTool
        tool = MyTool(command_executor=mock_executor)
        
        # Test the tool
        result = tool.do_something()
        
        # Verify interactions with dependencies
        mock_executor.execute.assert_called_once_with("test command")
```

## Best Practices

1. **Default to None**: Always use `None` as the default value for dependency parameters
2. **Check for None**: Check if dependencies are `None` and get them from the injector if needed
3. **Validate Dependencies**: Ensure that all required dependencies are available
4. **Circular Dependencies**: Avoid circular dependencies when possible
5. **Explicit Registration**: For complex dependency graphs, explicitly register dependencies
6. **Clear Error Messages**: Provide clear error messages when dependencies are missing
7. **Testing**: Use dependency injection to make testing easier with mock dependencies 