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
  - command_executor/  # Command execution functionality
  - azrepo/       # Azure repo integration
  - browser/      # Browser automation 
  - environment/  # Environment management
  - ...
```

## Refactoring Plan

### Phase 1: Tool Isolation (Complete)

We've extracted each tool into its own package without changing functionality:

1. ✅ Create new directory structure
2. ✅ Move each tool to its own package
3. ✅ Create adapter to maintain backward compatibility

### Phase 2: Interface Definition (Current Phase)

We've defined clean interfaces for each tool to standardize interactions:

1. ✅ Define common interfaces for all tools
2. ✅ Adapt tools to implement these interfaces
3. ✅ Update MCP to use interface methods instead of direct calls

### Phase 3: Plugin System

1. Implement plugin registration system
2. Convert tools to plugins
3. Update MCP to discover and load plugins

### Phase 4: Dependency Injection

1. Remove global instances
2. Implement dependency injection throughout the codebase
3. Update MCP to provide required dependencies to tools

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

## Installation

To install the refactored packages:

```bash
pip install -e .
```

## Status

- ✅ Phase 1: Tool Isolation (Complete)
- ✅ Phase 2: Interface Definition (Complete)
- ❌ Phase 3: Plugin System
- ❌ Phase 4: Dependency Injection 