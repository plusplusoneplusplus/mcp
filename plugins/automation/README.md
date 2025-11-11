# Automation Plugin

AI-powered automation for development tasks including specialized agents for codebase exploration, code review, and pre-defined workflows for common development patterns.

This plugin provides:
1. **AI Agents**: Specialized agents for specific tasks (exploration, review, etc.)
2. **Workflows**: Pre-defined multi-step automation workflows (coming soon)
3. **MCP Tools**: Tool interfaces for invoking agents and workflows via MCP
4. **Programmatic API**: Direct Python API access to all components

## Available Agents

### ExploreAgent

A specialized agent for exploring codebases and answering questions about code structure, implementations, and patterns. The ExploreAgent provides intelligent codebase exploration capabilities to help developers understand and navigate complex codebases.

## Features

- **Code Discovery**: Find specific files, classes, functions, or patterns
- **Implementation Analysis**: Understand how features and functions are implemented
- **Structure Analysis**: Get insights into codebase architecture and organization
- **Usage Tracking**: Find all usages of symbols (functions, classes, variables)
- **Flow Explanation**: Understand execution flows and processes
- **Multi-turn Conversations**: Maintain context across multiple questions
- **Session Management**: Track exploration sessions and history

## Installation

The plugin is part of the MCP project and requires:

- Python 3.11+
- `utils.agent` module from the MCP project
- One of the following CLIs installed:
  - Claude CLI (`claude`)
  - Codex CLI (`codex`)
  - GitHub Copilot CLI (`copilot`)

## Quick Start

### Basic Usage

```python
import asyncio
from plugins.automation import explore_codebase

async def main():
    # Quick exploration
    answer = await explore_codebase(
        "Where is error handling implemented?",
        codebase_path="/path/to/project"
    )
    print(answer)

asyncio.run(main())
```

### Using the ExploreAgent Class

```python
import asyncio
from plugins.automation import ExploreAgent, ExploreAgentConfig
from utils.agent import CLIType

async def main():
    # Create configuration
    config = ExploreAgentConfig(
        cli_type=CLIType.CLAUDE,
        model="haiku",
        session_id="my-exploration-session",
        cwd="/path/to/project",
        working_directories=["/path/to/project/src"],
    )

    # Initialize agent
    agent = ExploreAgent(config)

    # Explore the codebase
    result = await agent.explore(
        "How does the authentication system work?",
        codebase_path="/path/to/project"
    )
    print(result)

    # Find implementation
    impl = await agent.find_implementation("UserLogin")
    print(impl)

    # Analyze structure
    structure = await agent.analyze_structure("auth module")
    print(structure)

asyncio.run(main())
```

## MCP Tool Interface

The automation plugin provides an MCP tool named `agent` that can be invoked through the Model Context Protocol.

### Tool Name
`agent`

### Simplified Parameters

All operations use a consistent 3-parameter structure:

1. **`operation`** (required): The operation type
2. **`prompt`** (required): The main input (question, symbol name, flow description, etc.)
3. **`context`** (optional): Configuration object with optional fields:
   - `codebase_path`: Path to the codebase root
   - `session_id`: Session ID for conversation context
   - `model`: Model to use (e.g., "haiku", "gpt-4")
   - `cli_type`: CLI to use ("claude", "codex", "copilot")
   - `working_directories`: Array of working directory paths

### Operations

#### 1. `explore`
General codebase exploration with a question.

**Example:**
```json
{
  "operation": "explore",
  "prompt": "Where is authentication implemented?",
  "context": {
    "codebase_path": "/path/to/project",
    "model": "haiku"
  }
}
```

**Minimal example:**
```json
{
  "operation": "explore",
  "prompt": "How does error handling work?"
}
```

#### 2. `find_implementation`
Find the implementation of a feature or function.

**Example:**
```json
{
  "operation": "find_implementation",
  "prompt": "UserLogin",
  "context": {
    "codebase_path": "/path/to/project"
  }
}
```

#### 3. `analyze_structure`
Analyze the structure of a component or the entire codebase.

**Example (specific component):**
```json
{
  "operation": "analyze_structure",
  "prompt": "auth module",
  "context": {
    "codebase_path": "/path/to/project"
  }
}
```

**Example (entire codebase):**
```json
{
  "operation": "analyze_structure",
  "prompt": "",
  "context": {
    "codebase_path": "/path/to/project"
  }
}
```

#### 4. `find_usage`
Find all usages of a symbol in the codebase.

**Example:**
```json
{
  "operation": "find_usage",
  "prompt": "UserModel",
  "context": {
    "codebase_path": "/path/to/project"
  }
}
```

#### 5. `explain_flow`
Explain how a specific flow or process works.

**Example:**
```json
{
  "operation": "explain_flow",
  "prompt": "user registration and email verification",
  "context": {
    "codebase_path": "/path/to/project"
  }
}
```

### Response Format

The tool returns a response with the following structure:

```json
{
  "success": true,
  "operation": "explore",
  "result": "The authentication is implemented in src/auth.py:42...",
  "session_id": "session-123"
}
```

On error:
```json
{
  "error": "Error message describing what went wrong"
}
```

### Session Management

The tool maintains session-based agents. Use the same `session_id` in the `context` object across multiple calls to maintain conversation context:

```json
// First call
{
  "operation": "explore",
  "prompt": "Where is authentication?",
  "context": {
    "session_id": "my-session"
  }
}

// Second call - agent remembers the previous context
{
  "operation": "explore",
  "prompt": "How does it handle passwords?",
  "context": {
    "session_id": "my-session"
  }
}
```

## Configuration

### ExploreAgentConfig Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cli_type` | `CLIType` | `COPILOT` | CLI to use (CLAUDE, CODEX, or COPILOT) |
| `model` | `str` | None | Model name (e.g., "haiku", "gpt-4") |
| `session_id` | `str` | None | Session ID for tracking conversations |
| `session_storage_path` | `Path` | None | Path to session storage |
| `cwd` | `str` | None | Current working directory |
| `working_directories` | `List[str]` | None | Working directories for context |
| `search_paths` | `List[str]` | `[]` | Paths to search within |
| `file_extensions` | `List[str]` | `[".py", ".js", ...]` | File extensions to focus on |
| `max_file_size` | `int` | `100000` | Max file size in bytes |
| `ignore_patterns` | `List[str]` | `["node_modules", ...]` | Patterns to ignore |

## API Reference

### ExploreAgent Methods

#### `explore(question, codebase_path=None)`
General exploration method for any codebase question.

```python
answer = await agent.explore(
    "Where is the database connection configured?"
)
```

#### `find_implementation(feature_or_function, codebase_path=None)`
Find the implementation of a specific feature or function.

```python
result = await agent.find_implementation("calculate_discount")
```

#### `analyze_structure(component_or_module=None, codebase_path=None)`
Analyze the structure of a component or the entire codebase.

```python
structure = await agent.analyze_structure("payment processing")
```

#### `find_usage(symbol, codebase_path=None)`
Find all usages of a specific symbol.

```python
usages = await agent.find_usage("UserModel")
```

#### `explain_flow(flow_description, codebase_path=None)`
Explain how a specific flow or process works.

```python
flow = await agent.explain_flow("user registration and email verification")
```

## Examples

### Example 1: Finding Implementation

```python
config = ExploreAgentConfig(
    cli_type=CLIType.CLAUDE,
    cwd="/path/to/project"
)
agent = ExploreAgent(config)

result = await agent.find_implementation("JWT token generation")
# Output: Implementation found in src/auth/jwt.py:45
# The generate_token() function creates JWT tokens using...
```

### Example 2: Multi-turn Exploration

```python
agent = ExploreAgent(ExploreAgentConfig(session_id="exploration-1"))

# Turn 1
q1 = await agent.explore("Where is user authentication implemented?")
# Found in src/auth/handlers.py

# Turn 2 - maintains context
q2 = await agent.explore("How does it validate passwords?")
# Uses bcrypt hashing in src/auth/crypto.py:23

# Turn 3
q3 = await agent.explore("Where are failed login attempts logged?")
# Logged to audit table in src/auth/handlers.py:67
```

### Example 3: Analyzing Architecture

```python
agent = ExploreAgent(ExploreAgentConfig(
    working_directories=["/project/src", "/project/lib"]
))

analysis = await agent.analyze_structure()
# Provides overview of main directories, their purposes,
# and architectural patterns
```

## Response Format

The agent provides structured responses with:

1. **Summary**: Brief answer to the question
2. **Location**: Specific file paths and line numbers (format: `file_path:line_number`)
3. **Details**: Relevant code snippets and explanations
4. **Context**: How it fits into the larger codebase
5. **Related**: Other relevant files or areas to explore

## Session Management

```python
# Create agent with session
config = ExploreAgentConfig(session_id="session-1")
agent = ExploreAgent(config)

# Explore with history
await agent.explore("Question 1")
await agent.explore("Question 2")

# Get session history
history = agent.get_session_history()

# Clear session
agent.clear_session_history()

# Switch sessions
agent.set_session("session-2")
```

## Testing

Run the tests using pytest:

```bash
# Run all tests (46 tests: 24 for ExploreAgent + 22 for AgentTool)
uv run pytest plugins/automation/tests/

# Run specific test files
uv run pytest plugins/automation/tests/test_explore_agent.py
uv run pytest plugins/automation/tests/test_agent_tool.py

# Run with coverage
uv run pytest plugins/automation/tests/ --cov=plugins.automation
```

## Architecture

### Plugin Structure

```
plugins/automation/
├── __init__.py              # Exports ExploreAgent, AgentTool
├── agents/                  # AI agent implementations
│   ├── __init__.py
│   └── explore_agent.py     # ExploreAgent implementation
├── tools/                   # MCP tool interfaces
│   ├── __init__.py
│   └── agent_tool.py        # AgentTool (MCP interface)
├── workflows/               # Future: pre-defined workflows
├── example.py               # Usage examples
├── README.md                # This file
└── tests/
    ├── __init__.py
    ├── test_explore_agent.py  # 24 tests for ExploreAgent
    └── test_agent_tool.py     # 22 tests for AgentTool
```

### Components

**ExploreAgent**:
- Extends `SpecializedAgent` from `utils/agent`
- Uses `CLIExecutor` to invoke AI CLIs
- Maintains session history for context
- Provides specialized methods for common exploration tasks
- Supports custom context preparation for each query

**AgentTool** (MCP Interface):
- Implements `ToolInterface` from `mcp_tools.interfaces`
- Registered with `@register_tool` decorator for auto-discovery
- Manages agent instances per session
- Routes MCP calls to appropriate agent methods
- Handles parameter validation and error responses

## Adding New Agents

To add a new specialized agent to this plugin:

1. Create a new file (e.g., `review_agent.py`) in `plugins/automation/agents/`
2. Extend `SpecializedAgent` from `utils/agent`
3. Implement required methods (`get_system_prompt`, optionally `prepare_context`)
4. Add the new agent to `agents/__init__.py` exports
5. Update the main `__init__.py` to export the new agent
6. Create a new MCP tool in `tools/` for the new agent
7. Add tests for the new agent
8. Update this README

## Contributing

When contributing to the Automation plugin:

1. Maintain compatibility with the base `SpecializedAgent` class
2. Add comprehensive tests for new features (both agent and tool tests)
3. Update the README with new capabilities
4. Follow the existing code style and patterns
5. Ensure MCP tool interfaces are updated for new operations
6. Place agents in `agents/` directory and MCP tools in `tools/` directory

## License

Part of the MCP project.

## See Also

- [MCP Plugins](../README.md)
- [Specialized Agent Base Class](../../utils/agent/agent.py)
- [CLI Executor](../../utils/agent/cli_executor.py)
