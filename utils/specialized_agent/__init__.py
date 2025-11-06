"""
Specialized Agent Module

Provides base classes and utilities for creating specialized agents
that use AI CLIs (Claude, Codex, or Copilot) to perform specific tasks.
"""

from .agent import SpecializedAgent, AgentConfig
from .cli_executor import CLIExecutor, CLIConfig, CLIType

__all__ = ["SpecializedAgent", "AgentConfig", "CLIExecutor", "CLIConfig", "CLIType"]
