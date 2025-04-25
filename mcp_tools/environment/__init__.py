from mcp_tools.environment.manager import EnvironmentManager, env_manager
from mcp_tools.environment.types import (
    RepositoryInfo,
    EnvironmentProvider,
    EnvironmentVariables,
)

# Re-export the singleton instance for easy access
env = env_manager

__all__ = [
    "EnvironmentManager",
    "env_manager",
    "env",  # Alias for env_manager for backward compatibility
    "RepositoryInfo",
    "EnvironmentProvider",
    "EnvironmentVariables",
]
