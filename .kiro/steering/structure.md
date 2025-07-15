# Project Structure

## Top-Level Organization

```
├── server/           # HTTP/SSE server implementation
├── mcp_tools/        # Core plugin framework and built-in tools
├── plugins/          # Optional domain-specific plugins
├── config/           # Environment management and configuration
├── utils/            # Shared utility modules
├── scripts/          # Installation and utility scripts
├── docs/             # Project documentation
└── .kiro/            # Kiro-specific configuration and specs
```

## Core Modules

### server/
- `main.py` - Server entry point and Starlette app setup
- `api/` - REST API endpoints (tools, jobs, dataframes, etc.)
- `templates/` - Jinja2 HTML templates for web interface
- `tests/` - Server-specific test suite

### mcp_tools/
- Plugin registry and dependency injection system
- Built-in tools: command executor, browser automation, time utilities
- YAML-based tool definition system
- Core interfaces and types

### plugins/
- Domain-specific extensions (Azure DevOps, CircleCI, Git, etc.)
- Each plugin is self-contained with its own tests
- Optional dependencies managed per plugin

### config/
- Environment variable management
- Repository information handling
- Configuration templates and validation

### utils/
- Shared utilities: async jobs, dataframe management, vector storage
- Graph interface (Neo4j), memory management, OCR extraction
- HTML/Markdown conversion, log compression

## Configuration Files

- `.env` - Environment variables (create from `config/env.template`)
- `server/prompts.yaml` - AI prompts configuration
- `server/tools.yaml` - Tool definitions
- `server/.private/` - Private configuration overrides
- `pyproject.toml` - Python project configuration and dependencies

## Testing Structure

- Component-based test groups for parallel execution
- Each major module has its own `tests/` directory
- Shared test fixtures in `conftest.py` files
- Integration tests alongside unit tests

## File Naming Conventions

- Snake_case for Python files and directories
- Tool implementations end with `_tool.py`
- Test files prefixed with `test_`
- Configuration files use `.yaml` extension
- Private/local files in `.private/` or `.local/` directories
