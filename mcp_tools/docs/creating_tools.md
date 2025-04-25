# Creating Custom MCP Tools

This guide explains how to create and register new tools for the MCP system using the plugin framework.

## Overview

The MCP Tools system uses a plugin-based architecture that allows you to create custom tools that:

1. Can be automatically discovered and registered
2. Follow a standard interface
3. Can interact with other tools through dependency injection

## Step 1: Understand the ToolInterface

All tools must implement the `ToolInterface` defined in `mcp_tools/interfaces.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class ToolInterface(ABC):
    """Base interface for all tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the tool name."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the tool description."""
        pass
        
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        pass
    
    @abstractmethod
    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the tool with the provided arguments."""
        pass
```

## Step 2: Create Your Tool Class

Create a new Python file for your tool. You can place it in a new subdirectory of `mcp_tools/` or in an existing one if it's related to an existing tool category.

Here's a template for a basic tool:

```python
import logging
from typing import Dict, Any

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

logger = logging.getLogger(__name__)

@register_tool
class MyCustomTool(ToolInterface):
    """Description of your custom tool."""
    
    @property
    def name(self) -> str:
        """Get the tool name."""
        return "my_custom_tool"  # Use a unique, descriptive name
        
    @property
    def description(self) -> str:
        """Get the tool description."""
        return "A detailed description of what your tool does"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Description of parameter 1"
                },
                "param2": {
                    "type": "integer",
                    "description": "Description of parameter 2"
                }
                # Add more parameters as needed
            },
            "required": ["param1"]  # List required parameters
        }
    
    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments.
        
        Args:
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Tool execution result
        """
        # Extract parameters from arguments
        param1 = arguments.get("param1", "")
        param2 = arguments.get("param2", 0)
        
        try:
            # Implement your tool logic here
            result = f"Processed {param1} with value {param2}"
            
            # Return success result
            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error executing tool: {str(e)}")
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }
```

## Step 3: Dependency Injection

If your tool depends on other tools, you can use dependency injection to access them:

```python
@register_tool
class ToolWithDependencies(ToolInterface):
    def __init__(self, command_executor=None):
        """Initialize with optional dependencies.
        
        Args:
            command_executor: An instance of CommandExecutor or None
        """
        # Get dependencies from registry if not provided
        if command_executor is None:
            from mcp_tools.plugin import registry
            self.command_executor = registry.get_tool_instance("command_executor")
            if not self.command_executor:
                raise ValueError("CommandExecutor not found in registry")
        else:
            self.command_executor = command_executor
```

## Step 4: Register Your Tool

The `@register_tool` decorator automatically registers your tool with the plugin system. If for some reason you want to register a tool manually, you can do so:

```python
from mcp_tools.plugin import registry
from my_package.my_tool import MyCustomTool

# Register manually
registry.register_tool(MyCustomTool)
```

## Step 5: Testing Your Tool

To test your tool, you can create a simple script:

```python
import asyncio
from mcp_tools.plugin import registry

async def test_tool():
    # Get instance of your tool
    my_tool = registry.get_tool_instance("my_custom_tool")
    
    # Test with sample arguments
    result = await my_tool.execute_tool({
        "param1": "test value",
        "param2": 42
    })
    
    print(f"Tool result: {result}")

if __name__ == "__main__":
    asyncio.run(test_tool())
```

## Step 6: Tool Discovery and Usage

When the MCP system starts, it calls `discover_and_register_tools()` to automatically find and register all tools that have the `@register_tool` decorator.

The system will find your tool if:

1. It's in a module within the `mcp_tools` package
2. The class has the `@register_tool` decorator
3. The class implements the `ToolInterface`

## Best Practices

1. **Naming**: Use clear, descriptive names for your tools and their parameters
2. **Error Handling**: Always catch exceptions and return clear error messages
3. **Documentation**: Provide detailed docstrings for your tool and its methods
4. **Input Schema**: Define a complete JSON schema with descriptions for all parameters
5. **Logging**: Use the logger to record important events and errors
6. **Testing**: Create tests to verify your tool works correctly
7. **Dependencies**: Explicitly declare and handle your tool's dependencies

## Example: A Simple Calculator Tool

Here's an example of a calculator tool that performs basic arithmetic operations:

```python
import logging
from typing import Dict, Any

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

logger = logging.getLogger(__name__)

@register_tool
class CalculatorTool(ToolInterface):
    """A simple calculator tool that performs basic arithmetic operations."""
    
    @property
    def name(self) -> str:
        return "calculator"
        
    @property
    def description(self) -> str:
        return "Performs basic arithmetic operations (add, subtract, multiply, divide)"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform",
                    "enum": ["add", "subtract", "multiply", "divide"]
                },
                "a": {
                    "type": "number",
                    "description": "First operand"
                },
                "b": {
                    "type": "number",
                    "description": "Second operand"
                }
            },
            "required": ["operation", "a", "b"]
        }
    
    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation", "")
        a = arguments.get("a", 0)
        b = arguments.get("b", 0)
        
        try:
            if operation == "add":
                result = a + b
                expression = f"{a} + {b}"
            elif operation == "subtract":
                result = a - b
                expression = f"{a} - {b}"
            elif operation == "multiply":
                result = a * b
                expression = f"{a} × {b}"
            elif operation == "divide":
                if b == 0:
                    return {
                        "success": False,
                        "error": "Division by zero is not allowed"
                    }
                result = a / b
                expression = f"{a} ÷ {b}"
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }
            
            return {
                "success": True,
                "result": result,
                "expression": expression
            }
            
        except Exception as e:
            logger.error(f"Calculator error: {str(e)}")
            return {
                "success": False,
                "error": f"Error: {str(e)}"
            }
```

## Specialized Tool Interfaces

If you're creating a specific type of tool, check if there's a more specialized interface you should implement:

- `CommandExecutorInterface`: For tools that execute commands
- `RepoClientInterface`: For tools that interact with code repositories
- `BrowserClientInterface`: For tools that interact with web browsers
- `EnvironmentManagerInterface`: For tools that manage environment information

These specialized interfaces extend the base `ToolInterface` with additional methods specific to their domain. 