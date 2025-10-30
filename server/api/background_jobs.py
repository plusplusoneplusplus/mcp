"""
Background job management API endpoints - REMOVED.

This module has been removed as part of Phase 3 of the MCP progress notification
migration. Legacy token-based polling endpoints have been replaced with MCP native
progress notifications.

MIGRATION GUIDE:
================

Instead of polling endpoints like:
  GET /api/background-jobs
  GET /api/background-jobs/{token}
  POST /api/background-jobs/{token}/terminate

Use MCP progress notifications:
  1. Include `progressToken` in your tool call request metadata
  2. Listen for progress notifications from the MCP server
  3. Receive real-time updates without polling

Example (MCP Client):
```python
# Include progress token in request
result = await client.call_tool(
    "command_executor",
    {"command": "long_running_command"},
    _meta={"progressToken": "my-token-123"}
)

# Listen for progress notifications
@client.on_progress
async def handle_progress(token, progress, total):
    print(f"Progress: {progress}/{total}")
```

For more details, see:
  docs/migration/progress/token-to-mcp-progress.md

REMOVED IN: Version 2.0 (Phase 3)
REMOVAL DATE: 2025-10-29
"""

# This file intentionally left as a stub to document the migration
