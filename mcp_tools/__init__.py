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

# BrowserClient requires optional selenium/playwright dependencies. Avoid failing
# on import if those packages are not installed by lazily importing the class.
try:  # pragma: no cover - optional dependency
    from mcp_tools.browser import BrowserClient
except Exception:  # pragma: no cover - missing optional deps
    BrowserClient = None  # type: ignore

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

# Import tools
from mcp_tools.kv_store import KVStoreTool

# Import types (formerly from mcp_core)
from mcp_tools.mcp_types import TextContent, Tool, ToolResult, Annotations

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
    "BrowserClient",
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
    # Tools
    "KVStoreTool",
    # Types (formerly from mcp_core)
    "TextContent",
    "Tool",
    "ToolResult",
    "Annotations",
]
