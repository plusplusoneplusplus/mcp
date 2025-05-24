"""Azure DevOps Repository Plugin for MCP Tools.

This plugin provides tools for interacting with Azure DevOps repositories,
including pull request management and other repository operations.
"""

from .tool import AzureRepoClient

__all__ = ["AzureRepoClient"] 