# MCP Server

## Overview

The MCP Server is a Starlette-based web application that provides a comprehensive interface for managing MCP (Model Context Protocol) tools, knowledge management, and data processing. It serves as both an SSE-based MCP server and a web-based management interface.

## Architecture

### Core Components

```
server/
├── main.py                 # Server entry point and MCP server setup
├── api/                    # REST API endpoints
│   ├── background_jobs.py  # Background job management
│   ├── base.py            # Base API functionality
│   ├── configuration.py   # Configuration management
│   ├── dataframes.py      # DataFrame operations
│   ├── knowledge.py       # Knowledge management
│   ├── pyeval.py          # Python evaluation
│   ├── tool_history.py    # Tool execution history
│   ├── tools.py           # Tool management
│   └── visualizations.py  # Data visualization
├── templates/              # Jinja2 HTML templates
├── static/                # Static assets (CSS, JS, images)
└── tests/                 # Test suite
```

### Technology Stack

- **Backend**: Python 3.11+, Starlette ASGI framework
- **Frontend**: HTML5, CSS3, JavaScript, Jinja2 templates
- **MCP Protocol**: Server-Sent Events (SSE) transport
- **APIs**: RESTful APIs with JSON responses
- **Data**: In-memory DataFrames, ChromaDB for vector storage
- **Tools**: Plugin-based tool system with YAML and Python support

## Starting the Server

Run the server using:

```bash
uv run server/main.py
```

The server will start on `http://0.0.0.0:8000` by default. You can specify a different port:

```bash
uv run server/main.py --port 8080
```

Or set the `SERVER_PORT` environment variable:

```bash
SERVER_PORT=8080 uv run server/main.py
```

## MCP Integration

The server implements the Model Context Protocol with SSE transport:

- **SSE Endpoint**: `http://0.0.0.0:8000/sse`
- **Tool Registration**: Automatic discovery from `mcp_tools` and `plugins`
- **Tool Execution**: Safe execution with history recording

### Connecting MCP Clients

To connect from Claude Desktop or other MCP clients:

```json
{
  "mcpServers": {
    "mymcp-sse": { "url": "http://0.0.0.0:8000/sse" }
  }
}
```

## Web Interface

The server provides several web interfaces:

### Main Pages

- `/` - Redirects to knowledge page
- `/knowledge` - Knowledge management and document import
- `/jobs` - Background job monitoring
- `/tools` - Tool browser and execution
- `/tool-history` - Tool execution history
- `/dataframes` - DataFrame management and visualization
- `/config` - Configuration management
- `/pyeval` - Python code evaluation
- `/visualizations` - Task visualization
- `/knowledge-sync` - Knowledge synchronization

### Key Features

1. **Knowledge Management**: Document import, semantic search, collection management
2. **Tool Execution**: Browse and execute available tools with parameter validation
3. **Data Processing**: Upload, process, and visualize DataFrames
4. **Background Jobs**: Monitor and manage long-running tasks
5. **Configuration**: Manage server settings and environment variables
6. **Python Evaluation**: Safe Python code execution with RestrictedPython

## API Endpoints

The server provides REST API endpoints under `/api`:

### Core APIs

- **Tools API** (`/api/tools`): Tool listing, execution, and management
- **Knowledge API** (`/api/knowledge`): Document import and semantic search
- **DataFrames API** (`/api/dataframes`): Data upload and processing
- **Background Jobs API** (`/api/background-jobs`): Job management
- **Configuration API** (`/api/config`): Settings management
- **Tool History API** (`/api/tool-history`): Execution history
- **PyEval API** (`/api/pyeval`): Python code execution
- **Visualizations API** (`/api/visualizations`): Chart and graph generation

### Response Format

All APIs return JSON responses in this format:

```json
{
    "success": true,
    "data": { /* response data */ },
    "error": null
}
```

## Tool System

The server automatically discovers and registers tools from:

1. **mcp_tools package**: Built-in tools (browser automation, command execution, etc.)
2. **plugins directory**: Custom plugins
3. **YAML definitions**: Declarative tool definitions

### Tool History

When `TOOL_HISTORY_ENABLED=true`, all tool executions are logged to timestamped directories containing:
- `record.jsonl`: Execution details, arguments, results, and timing
- Additional diagnostic files based on tool type

## Configuration

The server uses environment variables for configuration:

```bash
# Server settings
SERVER_PORT=8000

# Tool history
TOOL_HISTORY_ENABLED=true
TOOL_HISTORY_PATH=.tool_history

# Knowledge management
CHROMA_DB_PATH=./data/chroma

# Private tool configuration (optional)
PRIVATE_TOOL_ROOT=/path/to/private/tools
```

Configuration files are resolved in this order:
1. `PRIVATE_TOOL_ROOT` directory
2. `server/.private/` directory
3. Default `server/` directory

## Development

### Running Tests

Execute the test suite:

```bash
# Run all server tests
pytest server/tests/

# Run specific test file
pytest server/tests/test_server_launch.py
```

### Project Structure

The server integrates with the broader MCP project:

- **mcp_tools/**: Core tool framework and built-in tools
- **plugins/**: Extended functionality (Azure DevOps, Git, Kusto, etc.)
- **config/**: Environment and configuration management
- **utils/**: Shared utilities (async jobs, vector store, etc.)

### Startup Process

The server performs these operations on startup:

1. **Environment Loading**: Load configuration from `.env` files
2. **Tool Discovery**: Scan for available tools in mcp_tools and plugins
3. **Dependency Resolution**: Set up dependency injection container
4. **Route Registration**: Configure web and API routes
5. **Knowledge Sync**: Initialize knowledge synchronization service
6. **SSE Transport**: Set up MCP protocol transport

Startup timing is tracked and logged for performance monitoring.

## Troubleshooting

### Common Issues

1. **Port in use**: Change the port with `--port` or `SERVER_PORT`
2. **Missing dependencies**: Run `uv sync` to install all dependencies
3. **Tool not found**: Check tool registration logs and plugin configuration
4. **SSE connection failed**: Verify firewall settings and URL format

### Logging

Logs are written to:
- **Console**: INFO level and above
- **File**: `server/.logs/server.log` with DEBUG level

Increase logging detail by setting `MCP_LOG_LEVEL=DEBUG`.

## Integration

The server can be integrated with:

- **MCP Clients**: Any client supporting SSE transport
- **Web Browsers**: Direct access to the web interface
- **REST APIs**: Programmatic access to all functionality
- **External Tools**: Plugin system for custom integrations

This server serves as a comprehensive platform for MCP tool management, knowledge processing, and data analysis workflows.
