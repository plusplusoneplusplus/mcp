"""
DEPRECATED: Memory management tests - REMOVED

This test file has been deprecated and removed as part of Phase 3 of the
MCP progress notification migration.

The memory management functionality tested here has been removed:
- completed_processes cache management
- LRU eviction when limits exceeded
- TTL-based cleanup of expired processes
- Background cleanup task
- Memory statistics reporting

MIGRATION:
==========
Memory management for completed processes is no longer needed with MCP native
progress notifications. Results are returned directly without caching, eliminating
memory overhead and the need for cache management.

Benefits:
- Lower memory footprint (no indefinite result storage)
- No cache management overhead
- Simpler architecture
- Real-time updates via MCP progress notifications

For MCP progress notification testing, see:
  - server/tests/test_mcp_progress_handler.py (unit tests)
  - server/tests/test_mcp_progress_notifications_e2e.py (integration tests)

For migration details, see:
  docs/migration/progress/token-to-mcp-progress.md

REMOVED IN: Version 2.0 (Phase 3)
REMOVAL DATE: 2025-10-29
"""

# This file is intentionally left as a stub to document the removal
# All functionality has been replaced with MCP progress notifications
