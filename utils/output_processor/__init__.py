"""
Output processor module for MCP framework.

This module provides hierarchical configuration management for output truncation
and processing functionality.
"""

from .schemas import (
    TruncationConfig,
    TruncationStrategy,
    ConfigLevel,
    ConfigSource,
    DEFAULT_SYSTEM_CONFIG,
    parse_env_config
)

from .config import (
    ConfigurationManager,
    get_config_manager,
    reset_config_manager,
    resolve_truncation_config
)

__all__ = [
    # Schemas
    'TruncationConfig',
    'TruncationStrategy',
    'ConfigLevel',
    'ConfigSource',
    'DEFAULT_SYSTEM_CONFIG',
    'parse_env_config',
    
    # Configuration Manager
    'ConfigurationManager',
    'get_config_manager',
    'reset_config_manager',
    'resolve_truncation_config',
] 