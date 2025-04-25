"""MCP Tools - A collection of utility tools for MCP."""

# Import interfaces
from mcp_tools.interfaces import (
    ToolInterface,
    CommandExecutorInterface,
    RepoClientInterface,
    BrowserClientInterface,
    EnvironmentManagerInterface,
)

# Import concrete implementations
from mcp_tools.command_executor import CommandExecutor
from mcp_tools.azrepo import AzureRepoClient
from mcp_tools.browser import BrowserClient
from mcp_tools.environment import EnvironmentManager, env

# Import plugin system
from mcp_tools.plugin import (
    register_tool,
    registry,
    discover_and_register_tools,
    PluginRegistry
)

__version__ = "0.1.0"

__all__ = [
    # Interfaces
    "ToolInterface",
    "CommandExecutorInterface",
    "RepoClientInterface",
    "BrowserClientInterface",
    "EnvironmentManagerInterface",
    
    # Implementations
    "CommandExecutor",
    "AzureRepoClient",
    "BrowserClient",
    "EnvironmentManager",
    "env",
    
    # Plugin system
    "register_tool",
    "registry",
    "discover_and_register_tools",
    "PluginRegistry",
]
