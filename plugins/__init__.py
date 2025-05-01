"""MCP Plugins Package.

This package contains plugins that extend the MCP toolset.
Each subdirectory contains a separate plugin implementation.
"""

# Import plugin modules
from plugins import text_summarizer

# List of all plugin modules for easy importing
__all__ = ["text_summarizer"] 