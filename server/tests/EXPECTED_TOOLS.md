# Expected Tools Documentation

This document lists the tools that should be available via the MCP server and verified by the test suite.

## Core Tools (Always Expected)

These tools should always be present and the tests will fail if any are missing:

### Built-in Tools
- **get_session_image**: Get an image for a given session_id and image_name

### YAML-defined Tools (from server/tools.yaml)
- **execute_task**: Execute a predefined task by name and start it asynchronously
- **query_task_status**: Query the status of an asynchronously executed task
- **list_tasks**: List all available predefined tasks
- **list_instructions**: List all available instructions
- **get_instruction**: Get a specific instruction with its details
- **query_script_status**: Query the status of an asynchronously executed script
- **deploy**: Deploy the application asynchronously and return a token for tracking

### Code-based Tools (from mcp_tools)
- **command_executor**: Execute shell commands synchronously or asynchronously
- **browser_client**: Browser automation for web scraping and testing
- **time_tool**: Returns time strings with optional delta calculations
- **knowledge_indexer**: Upload and index new knowledge from files into a vector store
- **knowledge_query**: Search and retrieve relevant knowledge from indexed documents
- **knowledge_collections**: Manage knowledge collections (list, delete, get info)
- **git**: Git repository operations including status, diff, add, branch management
- **git_commit**: Git commit operations including committing changes and pull rebase

## Optional Tools

These tools may or may not be present depending on configuration and environment:

- **capture_panels_client**: Capture dashboard panels as PNG images via browser automation
- **kusto_client**: Execute queries against Azure Data Explorer (Kusto) databases
- **web_summarizer**: Extracts and summarizes content from HTML into markdown format
- **url_summarizer**: Fetches a URL and extracts its content into markdown format
- **azure_repo_client**: Interact with Azure DevOps repositories
- **azure_pull_request**: Manage Azure DevOps pull requests
- **azure_work_item**: Manage Azure DevOps work items

## Tool Schema Requirements

Key tools must have valid schemas with required properties:

### get_session_image
- Required properties: `session_id`, `image_name`
- Required fields: `session_id`, `image_name`

### execute_task
- Required properties: `task_name`
- Required fields: `task_name`

### command_executor
- Required properties: `command`
- Required fields: `command`

### git
- Required properties: `operation`, `repo_path`
- Required fields: `operation`, `repo_path`

## Test Coverage

The test suite verifies:

1. **Tool Presence**: All core tools are registered and available
2. **Tool Attributes**: Each tool has name, description, and inputSchema
3. **Schema Validation**: Key tools have properly structured schemas
4. **Minimum Count**: At least the expected number of core tools are present

## Maintenance

When adding new tools to the server:

1. Update the expected tools list in `test_mcp_client_connection.py`
2. Add schema validation if the tool is critical
3. Update this documentation
4. Consider whether the tool should be core (always expected) or optional

## Tool Sources

Tools come from three sources:

1. **Built-in**: Hardcoded in server code (e.g., image_tool)
2. **YAML**: Defined in `server/tools.yaml` with `enabled: true`
3. **Code**: Discovered from `mcp_tools` package via `discover_and_register_tools()`

The tool discovery process:
1. Calls `discover_and_register_tools()` to find code-based tools
2. Loads YAML-defined tools from configuration
3. Filters tools based on configuration settings
4. Adds built-in tools like `get_session_image`
