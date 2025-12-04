"""
Specialized Agent Module

Provides base classes and utilities for creating specialized agents
that use AI CLIs (Claude, Codex, or Copilot) to perform specific tasks.
"""

from .agent import SpecializedAgent, AgentConfig
from .cli_executor import CLIExecutor, CLIConfig, CLIType
from .system_prompt import SystemPromptBuilder, create_default_system_prompt
from .models import (
    ModelFamily,
    ModelInfo,
    GPT_MODELS,
    CLAUDE_MODELS,
    GEMINI_MODELS,
    ALL_MODELS,
    MODEL_BY_NAME,
    MODELS_BY_FAMILY,
    CLI_SUPPORTED_FAMILIES,
    CLI_DEFAULT_MODELS,
    get_supported_families,
    get_supported_models,
    get_supported_model_names,
    is_model_supported,
    get_model_info,
    get_model_family,
    get_default_model,
    validate_model_for_cli,
    get_cli_model_name,
)

__all__ = [
    # Agent classes
    "SpecializedAgent",
    "AgentConfig",
    # CLI executor
    "CLIExecutor",
    "CLIConfig",
    "CLIType",
    # System prompt
    "SystemPromptBuilder",
    "create_default_system_prompt",
    # Model definitions
    "ModelFamily",
    "ModelInfo",
    "GPT_MODELS",
    "CLAUDE_MODELS",
    "GEMINI_MODELS",
    "ALL_MODELS",
    "MODEL_BY_NAME",
    "MODELS_BY_FAMILY",
    "CLI_SUPPORTED_FAMILIES",
    "CLI_DEFAULT_MODELS",
    # Model helper functions
    "get_supported_families",
    "get_supported_models",
    "get_supported_model_names",
    "is_model_supported",
    "get_model_info",
    "get_model_family",
    "get_default_model",
    "validate_model_for_cli",
    "get_cli_model_name",
]
