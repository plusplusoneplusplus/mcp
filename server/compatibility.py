"""
Compatibility layer for types.

This module re-exports types from mcp_core.types with the same interface as mcp.types,
allowing server code to use the local implementation without directly depending on mcp.
"""

# Import the types from mcp_core
from mcp_core.types import TextContent, Tool

# Re-export them for use in server/main.py
__all__ = ["TextContent", "Tool"]
