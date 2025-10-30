"""
DEPRECATED: Background jobs API tests - REMOVED

This test file has been deprecated and removed as part of Phase 3 of the
MCP progress notification migration.

The legacy token-based polling endpoints tested here have been removed:
- GET /api/background-jobs
- GET /api/background-jobs/{token}
- POST /api/background-jobs/{token}/terminate
- GET /api/background-jobs/stats

MIGRATION:
==========
These endpoints have been replaced with MCP native progress notifications.
See test_mcp_progress_notifications_e2e.py for the new testing approach.

For more details on the migration, see:
  docs/migration/progress/token-to-mcp-progress.md

REMOVED IN: Version 2.0 (Phase 3)
REMOVAL DATE: 2025-10-29
"""

# This file is intentionally left as a stub to document the removal
# All tests have been migrated to test_mcp_progress_notifications_e2e.py
