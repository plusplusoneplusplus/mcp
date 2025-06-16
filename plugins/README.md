# MCP Plugins

This directory contains example plugins that demonstrate how to extend the MCP toolset using the plugin framework.

## Plugin Directory Structure

Each plugin should be in its own directory with the following structure:

```
plugins/
└── plugin_name/
    ├── __init__.py         # Package initialization
    ├── tool.py             # Tool implementation
    └── README.md           # Plugin documentation
```

## How to Create a Plugin

1. Create a new directory for your plugin in the `plugins` directory
2. Implement a class that inherits from `mcp_tools.interfaces.ToolInterface` 
3. Register your tool using the `@register_tool` decorator
4. Make your plugin discoverable by adding it to Python's path

## Plugin Examples

- **text_summarizer**: An example plugin that summarizes text content
- **circleci**: Trigger and inspect CircleCI pipelines via the REST API
- **logcli**: Query a Grafana Loki server using the `logcli` command
- **azrepo**: Interact with Azure DevOps repositories and manage pull requests
- **git_tool**: Execute Git operations such as status, diff, and branch management
- **knowledge_indexer**: Index files into a vector store for semantic search
- **kusto**: Run queries against Azure Data Explorer (Kusto)

## Installation

To use a plugin:

1. Ensure the plugin directory is in your Python path
2. Import the plugin module in your code or use MCP's auto-discovery

## Using the Plugin Registry

The MCP tools plugin framework automatically discovers and registers tools that implement the `ToolInterface`. You can leverage this by:

1. Using the `@register_tool` decorator from `mcp_tools.plugin`
2. Making your plugin discoverable through the Python package system
3. Calling `discover_and_register_tools()` to register all available tools

For more details, see the README.md in each plugin directory. 