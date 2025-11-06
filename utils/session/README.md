# Session Management System

A comprehensive session management system for tracking conversations and tool invocations across multiple tools in the MCP framework.

## Overview

The session management system provides:

- **Cross-tool sessions**: Track activity spanning multiple tool invocations
- **Conversation history**: Maintain structured conversation logs with user, assistant, and tool messages
- **Metadata tracking**: Record session purpose, tags, statistics, and custom metadata
- **Flexible storage**: Abstract storage interface with filesystem and memory implementations
- **Parallel hierarchies**: Maintains both session-centric and tool-centric views of data
- **Rich querying**: Filter sessions by user, status, tags, and more

## Architecture

### Storage Structure

The system uses a parallel hierarchies approach (Option A from the design):

```
server/
  .sessions/                           # Session-centric storage
    {session_id}/
      metadata.json                    # Session metadata
      invocations/
        {invocation_id} -> symlink to ../../.history/...  # Link to tool history
      conversation.jsonl               # Conversation transcript
      invocations.json                 # List of invocation IDs

  .history/                            # Tool invocation storage (unchanged)
    2024-11-06_14-23-45_123456_git_tool/
      record.jsonl                     # Enhanced with session_id field
      ... (tool-specific files)
```

### Key Components

1. **Models** (`models.py`)
   - `Session`: Main session object containing metadata, invocations, and conversation
   - `SessionMetadata`: Rich metadata including status, tags, statistics, cost tracking
   - `ConversationMessage`: Individual message in the conversation
   - `SessionStatus`: Enum for session states (ACTIVE, COMPLETED, FAILED, ABANDONED)

2. **Storage** (`storage.py`)
   - `SessionStorage`: Abstract interface for session persistence
   - `FileSystemSessionStorage`: Filesystem-based implementation with symlinks
   - `MemorySessionStorage`: In-memory implementation for testing

3. **Manager** (`session_manager.py`)
   - `SessionManager`: High-level API for session operations
   - Create, retrieve, update, and delete sessions
   - Link tool invocations to sessions
   - Manage conversation history
   - Query and filter sessions

## Configuration

Add to your `.env` file or environment:

```bash
# Session storage settings
SESSION_STORAGE_ENABLED=true
SESSION_STORAGE_PATH=.sessions
SESSION_RETENTION_DAYS=30
SESSION_STORAGE_BACKEND=filesystem
```

Access via `EnvironmentManager`:

```python
from config.manager import env_manager

sessions_dir = env_manager.get_session_storage_path()
retention_days = env_manager.get_session_retention_days()
```

## Usage

### Basic Usage

```python
from pathlib import Path
from utils.session import SessionManager, FileSystemSessionStorage

# Initialize storage and manager
sessions_dir = Path(".sessions")
history_dir = Path(".history")
storage = FileSystemSessionStorage(sessions_dir, history_dir)
manager = SessionManager(storage)

# Create a session
session = manager.create_session(
    purpose="Debug authentication issue",
    user_id="user123",
    tags=["bug-fix", "authentication"]
)

# Add conversation
manager.add_conversation_message(
    session_id=session.metadata.session_id,
    role="user",
    content="What files were changed?"
)

# Link a tool invocation
manager.link_invocation(
    session_id=session.metadata.session_id,
    invocation_id="inv_001",
    tool_name="git_tool",
    invocation_dir=Path(".history/2024-11-06_14-23-45_123456_git_tool"),
    duration_ms=150.5
)

# Complete the session
manager.complete_session(session.metadata.session_id)
```

### Multi-Tool Workflow

```python
# Create session for complex task
session = manager.create_session(
    purpose="Investigate production issue",
    tags=["production", "urgent"]
)

# Use multiple tools
for tool_name in ["git_tool", "log_analysis", "knowledge_indexer"]:
    # Link tool invocation
    manager.link_invocation(
        session_id=session.metadata.session_id,
        invocation_id=f"inv_{tool_name}",
        tool_name=tool_name,
        invocation_dir=Path(f".history/invocation_{tool_name}"),
        duration_ms=100.0
    )

    # Record tool response
    manager.add_conversation_message(
        session_id=session.metadata.session_id,
        role="tool",
        content="Analysis complete",
        tool_name=tool_name
    )

# Get session statistics
stats = manager.get_session_statistics(session.metadata.session_id)
print(f"Used {len(stats['tools_used'])} tools in {stats['total_duration_ms']}ms")
```

### Querying Sessions

```python
# List all active sessions
active = manager.list_sessions(status=SessionStatus.ACTIVE)

# Find sessions by user
user_sessions = manager.list_sessions(user_id="user123")

# Filter by tags
bug_sessions = manager.list_sessions(tags=["bug-fix"])

# Combined filters
urgent_bugs = manager.list_sessions(
    tags=["bug-fix", "urgent"],
    status=SessionStatus.ACTIVE,
    limit=10
)
```

### Session Lifecycle

```python
# Create
session = manager.create_session(session_id="my_session")

# Update metadata
manager.update_session_metadata(
    session_id="my_session",
    purpose="Updated purpose",
    tags=["new-tag"],
    custom_metadata={"priority": "high"}
)

# Complete
manager.complete_session("my_session", SessionStatus.COMPLETED)

# Delete
manager.delete_session("my_session")

# Cleanup old sessions
manager.cleanup_old_sessions(max_age_days=30)
```

## API Reference

### SessionManager

#### `create_session(session_id=None, purpose=None, user_id=None, tags=None) -> Session`
Create a new session.

#### `get_session(session_id: str) -> Optional[Session]`
Retrieve a session by ID.

#### `link_invocation(session_id, invocation_id, tool_name, invocation_dir, duration_ms=None)`
Link a tool invocation to a session.

#### `add_conversation_message(session_id, role, content, tool_name=None, invocation_id=None)`
Add a message to the conversation.

#### `update_session_metadata(session_id, purpose=None, tags=None, custom_metadata=None)`
Update session metadata.

#### `complete_session(session_id, status=SessionStatus.COMPLETED)`
Mark session as completed/failed/abandoned.

#### `list_sessions(user_id=None, status=None, tags=None, limit=100) -> List[Session]`
Query sessions with filters.

#### `delete_session(session_id)`
Delete a session permanently.

#### `cleanup_old_sessions(max_age_days=30)`
Remove sessions older than specified days.

#### `get_session_statistics(session_id) -> Optional[Dict]`
Get statistics for a session.

### SessionMetadata

Tracks:
- `session_id`: Unique identifier
- `created_at`, `updated_at`: Timestamps
- `status`: Session status (ACTIVE, COMPLETED, FAILED, ABANDONED)
- `user_id`: User identifier
- `purpose`: Description of session purpose
- `tags`: List of tags for categorization
- `total_invocations`: Number of tool invocations
- `total_duration_ms`: Total duration of all invocations
- `tools_used`: List of tools used in session
- `estimated_cost`: Optional cost tracking
- `token_usage`: Optional token usage tracking
- `custom_metadata`: Dictionary for custom data

### ConversationMessage

Structure:
- `role`: "user" | "assistant" | "tool"
- `content`: Message content
- `timestamp`: When message was created
- `tool_name`: Optional tool name for tool messages
- `invocation_id`: Optional link to tool invocation

## Testing

Run all tests:
```bash
uv run pytest utils/session/tests/ -v
```

Run specific test file:
```bash
uv run pytest utils/session/tests/test_models.py -v
uv run pytest utils/session/tests/test_storage.py -v
uv run pytest utils/session/tests/test_session_manager.py -v
```

Test coverage:
- 54 tests covering all components
- Models: session, metadata, conversation messages
- Storage: memory and filesystem implementations
- Manager: CRUD operations, filtering, lifecycle management

## Examples

See `example.py` for complete working examples:

```bash
uv run python utils/session/example.py
```

Examples include:
- Basic session creation and usage
- Filesystem storage with persistence
- Multi-tool workflows
- Session filtering and querying

## Design Decisions

### Why Parallel Hierarchies?

The system maintains both `.sessions/` (session-centric) and `.history/` (tool-centric) views:

**Advantages:**
- Backward compatible with existing tool history
- Easy to find all invocations for a session
- Easy to find the session for an invocation
- No data duplication (uses symlinks)
- Tools remain unaware of sessions (optional feature)

### Why Abstract Storage?

The `SessionStorage` interface allows:
- Different backends (filesystem, database, cloud)
- Easy testing with `MemorySessionStorage`
- Future extensibility without changing API
- Separation of concerns

### Why Session-Tool Separation?

Sessions are **orthogonal** to tools:
- Tools execute independently in `.history/`
- Sessions organize invocations into logical units
- Optional: tools can work without sessions
- Flexible: one session can span multiple tools

## Future Enhancements

Potential improvements:
- Database storage backend (PostgreSQL, MongoDB)
- Cloud storage backend (S3, Azure Blob)
- Session branching/forking
- Session templates
- RAG integration for session context
- WebSocket/SSE for real-time session updates
- Session analytics and visualization
- Automatic session recovery
- Session export/import

## Integration

### With utils/agent

```python
from utils.agent import SpecializedAgent, AgentConfig
from utils.session import SessionManager, MemorySessionStorage

# Create session manager
storage = MemorySessionStorage()
session_manager = SessionManager(storage)

# Create session
session = session_manager.create_session(purpose="Code review")

# Use with agent
agent = MyAgent(config)
agent.set_session_manager(session_manager)
agent.set_session(session.metadata.session_id)

# All agent invocations now tracked in session
await agent.invoke("Review this code")
```

### With MCP Server

```python
# In server/main.py
from utils.session import SessionManager, FileSystemSessionStorage
from config.manager import env_manager

# Initialize session manager
sessions_dir = Path(env_manager.get_session_storage_path())
history_dir = Path(env_manager.get_tool_history_path())
storage = FileSystemSessionStorage(sessions_dir, history_dir)
session_manager = SessionManager(storage)

# In tool invocation handler
async def call_tool_handler(tool_name: str, arguments: dict) -> dict:
    session_id = arguments.pop('session_id', None)

    # ... execute tool ...

    # Link to session if provided
    if session_id:
        session_manager.link_invocation(
            session_id=session_id,
            invocation_id=invocation_id,
            tool_name=tool_name,
            invocation_dir=invocation_dir,
            duration_ms=duration_ms
        )
```

## License

Part of the MCP project.
