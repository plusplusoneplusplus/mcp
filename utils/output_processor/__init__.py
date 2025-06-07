"""
Output processor module for MCP framework.

This module provides hierarchical configuration management for output truncation
and processing functionality using the existing EnvironmentManager.
"""

from typing import Optional
from .schemas import (
    TruncationConfig,
    TruncationStrategy,
    DEFAULT_SYSTEM_CONFIG,
    parse_env_config
)

# Import the existing environment manager
from config import env_manager

# Convenience functions that delegate to the existing EnvironmentManager
def get_config_manager():
    """Get the global environment manager instance (for compatibility)."""
    return env_manager

def reset_config_manager():
    """Reset the global environment manager (mainly for testing)."""
    # The existing EnvironmentManager is a singleton, so we can't easily reset it
    # This is mainly for compatibility with the original API
    pass

def resolve_truncation_config(tool_name: Optional[str] = None, task_id: Optional[str] = None) -> TruncationConfig:
    """
    Convenience function to resolve truncation configuration.

    Args:
        tool_name: Name of the tool (for tool-specific config)
        task_id: Task identifier (for task-specific config)

    Returns:
        Resolved TruncationConfig
    """
    config = env_manager.resolve_truncation_config(tool_name, task_id)
    return config if config is not None else DEFAULT_SYSTEM_CONFIG

# For backward compatibility, create aliases
ConfigurationManager = type(env_manager)
ConfigLevel = dict  # Simplified - just use dict for config levels
ConfigSource = str  # Simplified - just use string for sources

__all__ = [
    # Schemas
    'TruncationConfig',
    'TruncationStrategy',
    'DEFAULT_SYSTEM_CONFIG',
    'parse_env_config',

    # Configuration Manager (delegated to existing EnvironmentManager)
    'ConfigurationManager',
    'get_config_manager',
    'reset_config_manager',
    'resolve_truncation_config',

    # Compatibility
    'ConfigLevel',
    'ConfigSource',
]
