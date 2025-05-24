"""Azure Data Explorer (Kusto) Plugin for MCP Tools.

This plugin provides tools for executing queries against Azure Data Explorer (Kusto) databases.
"""

from .tool import KustoClient

__all__ = ["KustoClient"]
