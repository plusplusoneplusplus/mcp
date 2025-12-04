"""
Model Definitions Module

Defines supported AI models organized by family (GPT, Claude, Gemini)
and maps which CLI executors support which model families.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Set, Optional

from .cli_executor import CLIType


class ModelFamily(str, Enum):
    """Model family categories"""

    GPT = "gpt"
    CLAUDE = "claude"
    GEMINI = "gemini"


@dataclass(frozen=True)
class ModelInfo:
    """Information about a specific model"""

    name: str
    """The canonical model identifier/name"""

    family: ModelFamily
    """The model family this model belongs to"""

    display_name: str
    """Human-readable display name"""

    description: str = ""
    """Optional description of the model"""

    claude_cli_name: str = ""
    """Model name/alias for Claude CLI (e.g., 'sonnet', 'opus', 'haiku')"""

    def get_cli_model_name(self, cli_type: CLIType) -> str:
        """
        Get the appropriate model name for a specific CLI type.

        Args:
            cli_type: The CLI type to get the model name for

        Returns:
            The CLI-specific model name
        """
        if cli_type == CLIType.CLAUDE and self.claude_cli_name:
            return self.claude_cli_name
        return self.name


# GPT Family Models
GPT_MODELS: List[ModelInfo] = [
    ModelInfo(
        name="gpt-5",
        family=ModelFamily.GPT,
        display_name="GPT-5",
        description="Latest GPT-5 model",
    ),
]

# Claude Family Models
CLAUDE_MODELS: List[ModelInfo] = [
    ModelInfo(
        name="claude-sonnet-4.5",
        family=ModelFamily.CLAUDE,
        display_name="Claude Sonnet 4.5",
        description="Claude Sonnet 4.5 model",
        claude_cli_name="sonnet",
    ),
    ModelInfo(
        name="claude-haiku-4.5",
        family=ModelFamily.CLAUDE,
        display_name="Claude Haiku 4.5",
        description="Fast and efficient Claude Haiku 4.5 model",
        claude_cli_name="haiku",
    ),
    ModelInfo(
        name="claude-opus-4.5",
        family=ModelFamily.CLAUDE,
        display_name="Claude Opus 4.5",
        description="Most capable Claude Opus 4.5 model",
        claude_cli_name="opus",
    ),
]

# Gemini Family Models
GEMINI_MODELS: List[ModelInfo] = [
    ModelInfo(
        name="gemini-3.0-pro",
        family=ModelFamily.GEMINI,
        display_name="Gemini 3.0 Pro",
        description="Latest Gemini 3.0 Pro model",
    ),
]

# All models combined
ALL_MODELS: List[ModelInfo] = GPT_MODELS + CLAUDE_MODELS + GEMINI_MODELS

# Model lookup by name
MODEL_BY_NAME: Dict[str, ModelInfo] = {model.name: model for model in ALL_MODELS}

# Models by family
MODELS_BY_FAMILY: Dict[ModelFamily, List[ModelInfo]] = {
    ModelFamily.GPT: GPT_MODELS,
    ModelFamily.CLAUDE: CLAUDE_MODELS,
    ModelFamily.GEMINI: GEMINI_MODELS,
}

# CLI type to supported model families mapping
# - Codex: Only supports GPT family (uses OpenAI/ChatGPT)
# - Claude Code: Only supports Claude family
# - Copilot: Supports all families (GPT, Claude, Gemini)
CLI_SUPPORTED_FAMILIES: Dict[CLIType, Set[ModelFamily]] = {
    CLIType.CODEX: {ModelFamily.GPT},
    CLIType.CLAUDE: {ModelFamily.CLAUDE},
    CLIType.COPILOT: {ModelFamily.GPT, ModelFamily.CLAUDE, ModelFamily.GEMINI},
}

# Default models for each CLI type
CLI_DEFAULT_MODELS: Dict[CLIType, str] = {
    CLIType.CODEX: "gpt-5",
    CLIType.CLAUDE: "claude-opus-4.5",
    CLIType.COPILOT: "claude-opus-4.5",
}


def get_supported_families(cli_type: CLIType) -> Set[ModelFamily]:
    """
    Get the set of model families supported by a CLI type.

    Args:
        cli_type: The CLI type to check

    Returns:
        Set of supported model families
    """
    return CLI_SUPPORTED_FAMILIES.get(cli_type, set())


def get_supported_models(cli_type: CLIType) -> List[ModelInfo]:
    """
    Get all models supported by a CLI type.

    Args:
        cli_type: The CLI type to check

    Returns:
        List of supported ModelInfo objects
    """
    supported_families = get_supported_families(cli_type)
    return [model for model in ALL_MODELS if model.family in supported_families]


def get_supported_model_names(cli_type: CLIType) -> List[str]:
    """
    Get all model names supported by a CLI type.

    Args:
        cli_type: The CLI type to check

    Returns:
        List of supported model name strings
    """
    return [model.name for model in get_supported_models(cli_type)]


def is_model_supported(cli_type: CLIType, model_name: str) -> bool:
    """
    Check if a model is supported by a CLI type.

    Args:
        cli_type: The CLI type to check
        model_name: The model name to validate

    Returns:
        True if the model is supported, False otherwise
    """
    model_info = MODEL_BY_NAME.get(model_name)
    if model_info is None:
        return False
    return model_info.family in get_supported_families(cli_type)


def get_model_info(model_name: str) -> Optional[ModelInfo]:
    """
    Get model information by name.

    Args:
        model_name: The model name to look up

    Returns:
        ModelInfo if found, None otherwise
    """
    return MODEL_BY_NAME.get(model_name)


def get_model_family(model_name: str) -> Optional[ModelFamily]:
    """
    Get the family of a model by name.

    Args:
        model_name: The model name to look up

    Returns:
        ModelFamily if found, None otherwise
    """
    model_info = get_model_info(model_name)
    return model_info.family if model_info else None


def get_default_model(cli_type: CLIType) -> str:
    """
    Get the default model for a CLI type.

    Args:
        cli_type: The CLI type

    Returns:
        Default model name string
    """
    return CLI_DEFAULT_MODELS.get(cli_type, "")


def validate_model_for_cli(cli_type: CLIType, model_name: str) -> None:
    """
    Validate that a model is supported by a CLI type.

    Args:
        cli_type: The CLI type to check
        model_name: The model name to validate

    Raises:
        ValueError: If the model is not supported
    """
    if not model_name:
        return  # Empty model means use default

    if not is_model_supported(cli_type, model_name):
        supported = get_supported_model_names(cli_type)
        model_info = get_model_info(model_name)
        if model_info:
            raise ValueError(
                f"Model '{model_name}' (family: {model_info.family.value}) "
                f"is not supported by {cli_type.value}. "
                f"Supported models: {', '.join(supported)}"
            )
        else:
            raise ValueError(
                f"Unknown model '{model_name}'. "
                f"Supported models for {cli_type.value}: {', '.join(supported)}"
            )


def get_cli_model_name(cli_type: CLIType, model_name: str) -> str:
    """
    Get the CLI-specific model name for a given model.

    Different CLIs may use different naming conventions. For example,
    Claude CLI uses 'sonnet', 'opus', 'haiku' as aliases.

    Args:
        cli_type: The CLI type to get the model name for
        model_name: The canonical model name

    Returns:
        The CLI-specific model name
    """
    model_info = get_model_info(model_name)
    if model_info:
        return model_info.get_cli_model_name(cli_type)
    return model_name
