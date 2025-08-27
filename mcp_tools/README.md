# MCP Tools

## Overview

The `mcp_tools` package provides a comprehensive framework for creating, managing, and executing MCP (Model Context Protocol) tools. It includes built-in tools, a plugin system, dependency injection, and utilities for tool development and testing.

## Architecture

### Core Components

```
mcp_tools/
├── interfaces.py           # Core tool interfaces and contracts
├── plugin.py              # Tool discovery and registration system
├── plugin_config.py       # Configuration management for plugins
├── dependency.py          # Dependency injection system
├── tools.py              # Tool execution engine
├── yaml_tools.py         # YAML-based tool definitions
├── mcp_types.py          # Common type definitions
├── built-in tools/       # Core tool implementations
│   ├── browser/          # Browser automation tools
│   ├── command_executor/ # Command execution tools
│   ├── dataframe_service/ # Data processing tools
│   ├── kv_store/         # Key-value storage tools
│   ├── time/             # Time and scheduling utilities
│   └── image_tool.py     # Image processing tool
└── tests/               # Comprehensive test suite
```

## Core Interfaces

### ToolInterface

The base interface that all tools must implement:

```python
from mcp_tools.interfaces import ToolInterface

class MyTool(ToolInterface):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Description of what my tool does"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "Parameter description"}
            }
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        # Tool implementation
        return {"result": "success"}
```

## Built-in Tools

### Browser Automation (`browser/`)

Provides browser automation capabilities using Playwright:

- **Web scraping**: Extract content from web pages
- **Screenshot capture**: Take screenshots of web pages
- **Form interaction**: Fill forms and click buttons
- **Cookie management**: Handle authentication cookies
- **Multi-browser support**: Chrome, Firefox, Safari support

### Command Executor (`command_executor/`)

Executes shell commands with advanced features:

- **Synchronous execution**: Run commands and wait for completion
- **Asynchronous execution**: Non-blocking command execution
- **Output streaming**: Real-time command output
- **Run-to-completion**: Execute scripts until finished
- **TMUX integration**: Session management and multiplexing

### DataFrame Service (`dataframe_service/`)

Data processing and analysis tools:

- **DataFrame management**: Create, manipulate, and query data
- **File upload**: Import CSV, JSON, Excel files
- **Data visualization**: Generate charts and graphs
- **Statistical analysis**: Compute statistics and summaries
- **Export capabilities**: Save data in multiple formats

### Key-Value Store (`kv_store/`)

Simple persistent storage:

- **Key-value operations**: Set, get, delete operations
- **Persistence**: Data survives server restarts
- **JSON serialization**: Store complex data structures
- **Namespace support**: Organize data by prefixes

### Time Utilities (`time/`)

Time-related functionality:

- **Current time**: Get current timestamp in various formats
- **Time parsing**: Parse time strings and convert formats
- **Scheduling**: Schedule tasks and reminders
- **Timezone handling**: Work with different timezones

### Image Tool (`image_tool.py`)

Image processing capabilities:

- **OCR**: Extract text from images using EasyOCR
- **Image analysis**: Analyze image properties and content
- **Format conversion**: Convert between image formats
- **Chart extraction**: Extract data from charts and graphs

## Tool Discovery and Registration

The plugin system automatically discovers tools from multiple sources:

### 1. Code-based Tools

Python classes that implement `ToolInterface`:

```python
# In a Python module
from mcp_tools.interfaces import ToolInterface

class MyCodeTool(ToolInterface):
    # Implementation here...
```

### 2. YAML-based Tools

Declarative tool definitions:

```yaml
# tool.example.yaml
tools:
  my_yaml_tool:
    description: "A tool defined in YAML"
    input_schema:
      type: object
      properties:
        message:
          type: string
          description: "Message to process"
    implementation:
      type: "shell"
      command: "echo 'Processing: {{ message }}'"
```

### 3. Plugin Directories

Tools in the `plugins/` directory are automatically discovered and registered.

## Dependency Injection

The dependency injection system manages tool instances and their dependencies:

```python
from mcp_tools.dependency import injector

# Get all tool instances
all_tools = injector.get_all_instances()

# Get filtered (active) tools
active_tools = injector.get_filtered_instances()

# Get specific tool
tool = injector.get_tool_instance("tool_name")
```

## Configuration

Tools are configured using environment variables and YAML files:

### Plugin Configuration

Create a `plugin_config.yaml` file:

```yaml
sources:
  code:
    enabled: true  # Enable code-based tools
  yaml:
    enabled: true  # Enable YAML-based tools

plugins:
  - plugin_repo: "owner/repo"
    sub_dir: "path/to/plugin"
    type: "python"
```

### Environment Variables

```bash
# Tool filtering
ENABLED_TOOLS=tool1,tool2,tool3

# Plugin management
PRIVATE_TOOL_ROOT=/path/to/private/tools

# Tool execution
TOOL_TIMEOUT=300
MAX_CONCURRENT_JOBS=10
```

## Development

### Creating New Tools

1. **Implement the ToolInterface**:

```python
from mcp_tools.interfaces import ToolInterface

class MyNewTool(ToolInterface):
    # Required properties and methods
```

2. **Place in discoverable location**:
   - Add to `mcp_tools/` package
   - Add to `plugins/` directory
   - Create YAML definition

3. **Test your tool**:

```python
import pytest
from mcp_tools.dependency import injector

def test_my_tool():
    tool = injector.get_tool_instance("my_new_tool")
    result = await tool.execute_tool({"param": "value"})
    assert result["success"] is True
```

### YAML Tool Development

Create tools using YAML definitions for simple use cases:

```yaml
tools:
  file_reader:
    description: "Read file contents"
    input_schema:
      type: object
      properties:
        file_path:
          type: string
          description: "Path to file to read"
      required: ["file_path"]
    implementation:
      type: "python"
      code: |
        with open(arguments["file_path"], "r") as f:
            return {"content": f.read()}
```

## Testing

The framework includes comprehensive testing utilities:

### Test Runner

```bash
# Run all mcp_tools tests
pytest mcp_tools/tests/

# Run specific test categories
pytest mcp_tools/tests/test_browser_*.py
pytest mcp_tools/tests/test_command_executor*.py
pytest mcp_tools/tests/test_yaml_*.py
```

### Test Utilities

```python
from mcp_tools.tests.conftest import temp_tool_registry

def test_tool_registration():
    with temp_tool_registry():
        # Test tool registration and execution
        pass
```

### Fixtures and Mocks

The test suite includes fixtures for:

- Temporary tool registries
- Mock browser sessions
- Sample YAML configurations
- Test data files

## Advanced Features

### Security Filtering

Tools can be filtered for security:

```python
from mcp_tools.plugin_config import config

# Check if a tool source is enabled
if config.is_source_enabled("yaml"):
    # Execute YAML-based tools
```

### Output Processing

Built-in output processing and formatting:

- **Truncation**: Limit output length
- **Compression**: Compress large outputs
- **Formatting**: Format structured data
- **Security**: Filter sensitive information

### Concurrency Management

Control concurrent tool execution:

```python
from utils.concurrency import manager

# Limit concurrent executions
async with manager.acquire_semaphore("tool_category"):
    result = await tool.execute_tool(arguments)
```

### Memory Management

Automatic memory monitoring and cleanup:

- **Memory tracking**: Monitor tool memory usage
- **Cleanup**: Automatic resource cleanup
- **Limits**: Enforce memory limits per tool
- **Monitoring**: Real-time memory usage reporting

## Integration

### MCP Server Integration

Tools are automatically registered with the MCP server:

```python
# In server/main.py
from mcp_tools.plugin import discover_and_register_tools
from mcp_tools.dependency import injector

# Discover and register all tools
discover_and_register_tools()
injector.resolve_all_dependencies()

# Get active tools for MCP
active_tools = list(injector.get_filtered_instances().values())
```

### External Plugin Integration

Load external plugins from Git repositories:

```yaml
plugins:
  - plugin_repo: "organization/custom-mcp-tools"
    sub_dir: "src/tools"
    type: "python"
```

## Performance

### Startup Optimization

- **Lazy loading**: Tools are loaded on-demand
- **Caching**: Tool schemas and metadata are cached
- **Parallel discovery**: Multi-threaded tool discovery

### Runtime Optimization

- **Connection pooling**: Reuse browser connections
- **Result caching**: Cache tool results when appropriate
- **Resource monitoring**: Track and optimize resource usage

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **Creating Tools** (`creating_tools.md`): Guide for developing new tools
- **Dependency Injection** (`dependency_injection.md`): DI system documentation
- **Async Job Framework** (`async_job_framework.md`): Background job system

For more detailed information about specific tools or features, see their individual README files and the documentation in the `docs/` directory.
