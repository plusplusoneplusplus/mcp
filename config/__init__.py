"""
MCP Configuration Package.

This package contains centralized configuration modules for the MCP project.
"""

from config.manager import EnvironmentManager, env_manager
from config.types import (
    RepositoryInfo,
    EnvironmentProvider,
    EnvironmentVariables,
)

# Re-export the singleton instance for easy access
env = env_manager

__all__ = [
    "EnvironmentManager",
    "env_manager",
    "env",
    "RepositoryInfo",
    "EnvironmentProvider",
    "EnvironmentVariables",
]
