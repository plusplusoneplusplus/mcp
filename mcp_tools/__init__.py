"""MCP Tools - A collection of utility tools for MCP."""

# Import interfaces
from mcp_tools.interfaces import (
    ToolInterface,
    CommandExecutorInterface,
    RepoClientInterface,
    BrowserClientInterface,
    KustoClientInterface,
)

# Import concrete implementations
from mcp_tools.command_executor import CommandExecutor
from mcp_tools.azrepo import AzureRepoClient
from mcp_tools.browser import BrowserClient
from config import env

# Import plugin system
from mcp_tools.plugin import (
    register_tool,
    registry,
    discover_and_register_tools,
    PluginRegistry,
)

# Import dependency injection system
from mcp_tools.dependency import injector, DependencyInjector

# Import YAML tools system
from mcp_tools.yaml_tools import YamlToolBase, discover_and_register_yaml_tools

# Import Kusto client
from mcp_tools.kusto import KustoClient

__version__ = "0.1.0"

__all__ = [
    # Interfaces
    "ToolInterface",
    "CommandExecutorInterface",
    "RepoClientInterface",
    "BrowserClientInterface",
    "KustoClientInterface",
    # Implementations
    "CommandExecutor",
    "AzureRepoClient",
    "BrowserClient",
    "KustoClient",
    "env",
    # Plugin system
    "register_tool",
    "registry",
    "discover_and_register_tools",
    "PluginRegistry",
    # Dependency injection
    "injector",
    "DependencyInjector",
    # YAML tools
    "YamlToolBase",
    "discover_and_register_yaml_tools",
]
