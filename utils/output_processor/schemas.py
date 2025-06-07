"""
Configuration schemas for output truncation system.

This module defines the data structures and validation schemas for the hierarchical
configuration system that manages output truncation settings across different levels.
"""

from enum import Enum
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
import os


class TruncationStrategy(Enum):
    """Available truncation strategies."""
    HEAD_TAIL = "head_tail"
    SMART_SUMMARY = "smart_summary"
    SIZE_LIMIT = "size_limit"
    NONE = "none"


@dataclass
class TruncationConfig:
    """
    Configuration for output truncation settings.

    This class represents the complete configuration for how output should be
    truncated, including strategy, limits, and preservation rules.
    """
    strategy: TruncationStrategy = TruncationStrategy.HEAD_TAIL
    max_chars: int = 50000  # ~50KB default
    max_lines: int = 1000   # Line-based limit
    head_lines: int = 100   # Lines to keep from start
    tail_lines: int = 100   # Lines to keep from end
    preserve_errors: bool = True    # Always include error messages
    preserve_warnings: bool = True  # Always include warnings
    content_detection: bool = True  # Detect and preserve structured data

    def __post_init__(self):
        """Validate configuration values after initialization."""
        self._validate()

    def _validate(self):
        """Validate configuration parameters."""
        if self.max_chars <= 0:
            raise ValueError("max_chars must be positive")

        if self.max_lines <= 0:
            raise ValueError("max_lines must be positive")

        if self.head_lines < 0:
            raise ValueError("head_lines must be non-negative")

        if self.tail_lines < 0:
            raise ValueError("tail_lines must be non-negative")

        if self.head_lines + self.tail_lines > self.max_lines:
            raise ValueError("head_lines + tail_lines cannot exceed max_lines")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TruncationConfig':
        """Create TruncationConfig from dictionary data."""
        if not isinstance(data, dict):
            raise TypeError("Configuration data must be a dictionary")

        # Handle strategy conversion
        strategy = data.get('strategy', TruncationStrategy.HEAD_TAIL.value)
        if isinstance(strategy, str):
            try:
                strategy = TruncationStrategy(strategy)
            except ValueError:
                raise ValueError(f"Invalid truncation strategy: {strategy}")
        elif isinstance(strategy, TruncationStrategy):
            pass  # Already correct type
        else:
            raise TypeError("Strategy must be string or TruncationStrategy enum")

        return cls(
            strategy=strategy,
            max_chars=data.get('max_chars', 50000),
            max_lines=data.get('max_lines', 1000),
            head_lines=data.get('head_lines', 100),
            tail_lines=data.get('tail_lines', 100),
            preserve_errors=data.get('preserve_errors', True),
            preserve_warnings=data.get('preserve_warnings', True),
            content_detection=data.get('content_detection', True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert TruncationConfig to dictionary."""
        return {
            'strategy': self.strategy.value,
            'max_chars': self.max_chars,
            'max_lines': self.max_lines,
            'head_lines': self.head_lines,
            'tail_lines': self.tail_lines,
            'preserve_errors': self.preserve_errors,
            'preserve_warnings': self.preserve_warnings,
            'content_detection': self.content_detection,
        }

    def merge_with(self, other: Optional['TruncationConfig']) -> 'TruncationConfig':
        """
        Merge this config with another, with the other taking precedence.

        Args:
            other: Configuration to merge with (higher priority)

        Returns:
            New TruncationConfig with merged settings
        """
        if other is None:
            return TruncationConfig(
                strategy=self.strategy,
                max_chars=self.max_chars,
                max_lines=self.max_lines,
                head_lines=self.head_lines,
                tail_lines=self.tail_lines,
                preserve_errors=self.preserve_errors,
                preserve_warnings=self.preserve_warnings,
                content_detection=self.content_detection,
            )

        return TruncationConfig(
            strategy=other.strategy,
            max_chars=other.max_chars,
            max_lines=other.max_lines,
            head_lines=other.head_lines,
            tail_lines=other.tail_lines,
            preserve_errors=other.preserve_errors,
            preserve_warnings=other.preserve_warnings,
            content_detection=other.content_detection,
        )


# Default system configuration
DEFAULT_SYSTEM_CONFIG = TruncationConfig(
    strategy=TruncationStrategy.HEAD_TAIL,
    max_chars=50000,
    max_lines=1000,
    head_lines=100,
    tail_lines=100,
    preserve_errors=True,
    preserve_warnings=True,
    content_detection=True,
)


def parse_env_config() -> Optional[TruncationConfig]:
    """
    Parse truncation configuration from environment variables.

    Environment variables:
    - MCP_TRUNCATION_STRATEGY: Truncation strategy
    - MCP_TRUNCATION_MAX_CHARS: Maximum characters
    - MCP_TRUNCATION_MAX_LINES: Maximum lines
    - MCP_TRUNCATION_HEAD_LINES: Head lines to preserve
    - MCP_TRUNCATION_TAIL_LINES: Tail lines to preserve
    - MCP_TRUNCATION_PRESERVE_ERRORS: Preserve error messages (true/false)
    - MCP_TRUNCATION_PRESERVE_WARNINGS: Preserve warning messages (true/false)
    - MCP_TRUNCATION_CONTENT_DETECTION: Enable content detection (true/false)

    Returns:
        TruncationConfig if any environment variables are set, None otherwise
    """
    env_vars = {
        'strategy': os.getenv('MCP_TRUNCATION_STRATEGY'),
        'max_chars': os.getenv('MCP_TRUNCATION_MAX_CHARS'),
        'max_lines': os.getenv('MCP_TRUNCATION_MAX_LINES'),
        'head_lines': os.getenv('MCP_TRUNCATION_HEAD_LINES'),
        'tail_lines': os.getenv('MCP_TRUNCATION_TAIL_LINES'),
        'preserve_errors': os.getenv('MCP_TRUNCATION_PRESERVE_ERRORS'),
        'preserve_warnings': os.getenv('MCP_TRUNCATION_PRESERVE_WARNINGS'),
        'content_detection': os.getenv('MCP_TRUNCATION_CONTENT_DETECTION'),
    }

    # Check if any environment variables are set
    if not any(value is not None for value in env_vars.values()):
        return None

    # Parse values with defaults from system config
    config_dict: Dict[str, Any] = {}

    if env_vars['strategy']:
        config_dict['strategy'] = env_vars['strategy']

    if env_vars['max_chars']:
        try:
            config_dict['max_chars'] = int(env_vars['max_chars'])
        except ValueError:
            raise ValueError(f"Invalid MCP_TRUNCATION_MAX_CHARS: {env_vars['max_chars']}")

    if env_vars['max_lines']:
        try:
            config_dict['max_lines'] = int(env_vars['max_lines'])
        except ValueError:
            raise ValueError(f"Invalid MCP_TRUNCATION_MAX_LINES: {env_vars['max_lines']}")

    if env_vars['head_lines']:
        try:
            config_dict['head_lines'] = int(env_vars['head_lines'])
        except ValueError:
            raise ValueError(f"Invalid MCP_TRUNCATION_HEAD_LINES: {env_vars['head_lines']}")

    if env_vars['tail_lines']:
        try:
            config_dict['tail_lines'] = int(env_vars['tail_lines'])
        except ValueError:
            raise ValueError(f"Invalid MCP_TRUNCATION_TAIL_LINES: {env_vars['tail_lines']}")

    if env_vars['preserve_errors']:
        config_dict['preserve_errors'] = env_vars['preserve_errors'].lower() in ('true', '1', 'yes', 'on')

    if env_vars['preserve_warnings']:
        config_dict['preserve_warnings'] = env_vars['preserve_warnings'].lower() in ('true', '1', 'yes', 'on')

    if env_vars['content_detection']:
        config_dict['content_detection'] = env_vars['content_detection'].lower() in ('true', '1', 'yes', 'on')

    # Start with system defaults and override with environment values
    system_dict = DEFAULT_SYSTEM_CONFIG.to_dict()
    system_dict.update(config_dict)

    return TruncationConfig.from_dict(system_dict)
