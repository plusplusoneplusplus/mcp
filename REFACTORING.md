# MCP Refactoring Project

The goal of this refactoring project is to decouple the individual tools from the MCP core. This document outlines the plan and current status of the refactoring effort.

## Project Structure

The new project structure decouples tools into their own packages:

```
/mcp_core/       # Core MCP functionality
  - mcp/         # MCP server and core components
  - ...

/mcp_tools/      # Decoupled tool modules
  - command_executor/  # Command execution functionality
  - azrepo/       # Azure repo integration
  - browser/      # Browser automation 
  - environment/  # Environment management
  - ...
```

## Refactoring Plan

### Phase 1: Tool Isolation (Current Phase)

We're extracting each tool into its own package without changing functionality:

1. ✅ Create new directory structure
2. ✅ Move each tool to its own package
3. ✅ Create adapter to maintain backward compatibility

### Phase 2: Interface Definition

1. Define clean interfaces for each tool
2. Adapt tools to implement these interfaces
3. Update MCP to use interface methods instead of direct calls

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

### New Approach (direct usage)

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

- ✅ Phase 1: Tool Isolation (In progress)
- ❌ Phase 2: Interface Definition
- ❌ Phase 3: Plugin System
- ❌ Phase 4: Dependency Injection 