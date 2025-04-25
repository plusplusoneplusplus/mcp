# MCP Refactoring Project

The goal of this refactoring project is to decouple the individual tools from the MCP core. This document outlines the plan and current status of the refactoring effort.

## Project Structure

The new project structure decouples tools into their own packages:

```
/mcp_core/       # Core MCP functionality
  - mcp/         # MCP server and core components
  - tools_adapter.py  # Adapter for backwards compatibility
  - ...

/mcp_tools/      # Decoupled tool modules
  - interfaces.py  # Shared interfaces for all tools
  - plugin.py      # Plugin registration system
  - dependency.py  # Dependency injection system
  - command_executor/  # Command execution functionality
  - azrepo/       # Azure repo integration
  - browser/      # Browser automation 
  - environment/  # Environment management
  - docs/         # Documentation
  - ...
```

## Refactoring Plan

### Phase 1: Tool Isolation (Complete)

We've extracted each tool into its own package without changing functionality:

1. ✅ Create new directory structure
2. ✅ Move each tool to its own package
3. ✅ Create adapter to maintain backward compatibility

### Phase 2: Interface Definition (Complete)

We've defined clean interfaces for each tool to standardize interactions:

1. ✅ Define common interfaces for all tools
2. ✅ Adapt tools to implement these interfaces
3. ✅ Update MCP to use interface methods instead of direct calls

### Phase 3: Plugin System (Complete)

We've implemented a plugin system for tool registration and discovery:

1. ✅ Implement plugin registration system
2. ✅ Convert tools to plugins
3. ✅ Update MCP to discover and load plugins dynamically

### Phase 4: Dependency Injection (Complete)

We've implemented dependency injection to remove global instances:

1. ✅ Remove global instances
2. ✅ Implement dependency injection throughout the codebase
3. ✅ Update MCP to provide required dependencies to tools

## Using the Refactored Tools

During the transition period, you can use both the old and new approaches:

### Old Approach (via adapter)

```python
# Old code will continue to work through the adapter
from mcp_core.tools_adapter import ToolsAdapter

tools = ToolsAdapter()
tool_list = tools.get_tools()
result = await tools.call_tool("execute_command", {"command": "ls -la"})
```

### Interface-Based Approach

```python
# Using the interfaces for better extensibility
from mcp_tools import CommandExecutorInterface, CommandExecutor

# Function that accepts any command executor implementation
async def run_my_command(executor: CommandExecutorInterface):
    result = await executor.execute_command("ls -la")
    print(result)
    
# Use with the default implementation
executor = CommandExecutor()
await run_my_command(executor)

# Or create a custom implementation
class MyCustomExecutor(CommandExecutorInterface):
    # Implement the required interface methods
    ...

custom_executor = MyCustomExecutor()
await run_my_command(custom_executor)
```

### Direct Usage Approach

```python
# New code can use the decoupled modules directly
from mcp_tools.command_executor import CommandExecutor
from mcp_tools.azrepo import AzureRepoClient
from mcp_tools.browser import BrowserClient
from mcp_tools.environment import env

# Initialize environment
env.load()

# Use command executor
executor = CommandExecutor()
result = executor.execute("ls -la")

# Use Azure repo client
azure_client = AzureRepoClient(executor)
prs = await azure_client.list_pull_requests()

# Use browser client
browser = BrowserClient()
html = browser.get_page_html("https://example.com")
```

### Plugin System Approach

```python
# Using the plugin system for dynamic tool discovery
from mcp_tools.plugin import registry, discover_and_register_tools

# Discover all available tools
discover_and_register_tools()

# Get a tool instance by name
command_executor = registry.get_tool_instance("command_executor")
result = command_executor.execute("ls -la")

# Get all registered tools
all_tools = registry.get_all_instances()
```

### Dependency Injection Approach

```python
# Using the dependency injection system
from mcp_tools.dependency import injector
from mcp_tools.plugin import discover_and_register_tools

# Discover tools and register them
discover_and_register_tools()

# Register dependencies between tools
injector.register_dependency("azure_repo_client", ["command_executor"])

# Resolve all dependencies at once
tools = injector.resolve_all_dependencies()

# Or get a specific tool with dependencies resolved
azure_client = injector.get_tool_instance("azure_repo_client")
results = await azure_client.list_pull_requests()
```

### Creating Custom Tools with Dependencies

```python
# Creating a custom tool with dependencies
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

@register_tool
class MyCustomTool(ToolInterface):
    def __init__(self, command_executor=None):
        # Use dependency injection to get dependencies
        if command_executor is None:
            from mcp_tools.dependency import injector
            self.command_executor = injector.get_tool_instance("command_executor")
            if not self.command_executor:
                raise ValueError("CommandExecutor not found")
        else:
            self.command_executor = command_executor
            
    @property
    def name(self) -> str:
        return "my_custom_tool"
        
    # Implement other required methods...
```

## Installation

To install the refactored packages:

```bash
pip install -e .
```

## Status

- ✅ Phase 1: Tool Isolation (Complete)
- ✅ Phase 2: Interface Definition (Complete)
- ✅ Phase 3: Plugin System (Complete)
- ✅ Phase 4: Dependency Injection (Complete)

# MCP Tools Refactoring Integration Guide

This guide provides instructions on how to integrate the refactored MCP Tools modules into the server and remove redundant implementations.

## Overview

The MCP Tools framework has been refactored into separate modules:
- `mcp_tools`: Contains the core tool implementations
- `mcp_core`: Contains the adapter and interfaces

## Integration Steps

### 1. Install the refactored modules

```bash
pip install -e .
```

### 2. Update Server Code

The server's `main.py` file has been updated to use the new `ToolsAdapter` from `mcp_core.tools_adapter` instead of the old tools implementation. The changes include:

- Importing `ToolsAdapter` from `mcp_core.tools_adapter`
- Creating an instance of `ToolsAdapter`
- Updating `list_tools` and `call_tool_handler` functions to use the adapter
- Adjusting the environment initialization

### 3. Update Dependencies

The `server/requirements.txt` file has been updated to include the new modules:
- `mcp_tools>=0.1.0`
- `mcp_core>=0.1.0`

### 4. Clean up Redundant Files

A cleanup script has been created to remove redundant implementations:

```bash
python scripts/cleanup_server.py
```

The script will:
- Back up redundant files to `backup_before_cleanup` directory
- Remove the redundant files listed below
- Display a list of tests that might need updating

### Redundant Files

The following files are now redundant and can be removed:
- `server/command_executor.py`
- `server/command_executor_v2.py`
- `server/tools.py`
- `server/environment.py`
- `server/browser_utils.py`
- `server/azrepo_utils.py`

### Tests to Update

The following tests might need to be updated to work with the new implementation:
- `server/tests/test_command_executor_v2.py`
- `server/tests/test_command_executor_async.py`
- `server/tests/test_command_executor_integration.py`
- `server/tests/test_browser_utils.py`

## Testing

After integration, run the tests to ensure everything works as expected:

```bash
pytest
```

## Troubleshooting

If you encounter any issues:

1. Check import statements in your code that might still reference the old modules
2. Ensure the new modules are properly installed
3. Verify that the `ToolsAdapter` is correctly initialized in `server/main.py`
4. Check the test files for compatibility with the new implementation 