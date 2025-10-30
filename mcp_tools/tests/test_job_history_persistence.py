"""
DEPRECATED: Job history persistence tests - REMOVED

This test file has been deprecated and removed as part of Phase 3 of the
MCP progress notification migration.

The job history persistence functionality tested here has been removed:
- completed_processes cache
- Job history JSON persistence
- Persistence load/save operations

MIGRATION:
==========
Job history persistence is no longer needed with MCP native progress notifications.
Progress updates are sent in real-time via MCP session, eliminating the need
for result caching and persistence.

For MCP progress notification testing, see:
  - server/tests/test_mcp_progress_handler.py (unit tests)
  - server/tests/test_mcp_progress_notifications_e2e.py (integration tests)

For migration details, see:
  docs/migration/progress/token-to-mcp-progress.md

REMOVED IN: Version 2.0 (Phase 3)
REMOVAL DATE: 2025-10-29
"""

# This file is intentionally left as a stub to document the removal
# All functionality has been migrated to MCP progress notifications
