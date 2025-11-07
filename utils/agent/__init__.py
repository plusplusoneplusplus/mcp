"""
Specialized Agent Module

Provides base classes and utilities for creating specialized agents
that use AI CLIs (Claude, Codex, or Copilot) to perform specific tasks.
"""

from .agent import SpecializedAgent, AgentConfig
from .cli_executor import CLIExecutor, CLIConfig, CLIType
from .system_prompt import SystemPromptBuilder, create_default_system_prompt

__all__ = [
    "SpecializedAgent",
    "AgentConfig",
    "CLIExecutor",
    "CLIConfig",
    "CLIType",
    "SystemPromptBuilder",
    "create_default_system_prompt",
]
