"""Type definitions and data structures for log compression."""

import re
from typing import Dict, List, Tuple, Any, Optional, Union, TextIO
from dataclasses import dataclass
from datetime import datetime


# Timestamp extraction regex
TIMESTAMP_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})")

# Define log format (required for logparser)
LOG_FORMAT = "<Content>"  # Simple format treating the whole line as content


@dataclass
class LogEntry:
    """Represents a single log entry with timestamp and content."""
    timestamp: float
    content: str


@dataclass
class StructuredLog:
    """Represents a structured log entry with template ID, timestamp, and parameters."""
    template_id: int
    timestamp: float
    parameters: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "t": self.template_id,
            "ts": self.timestamp,
            "p": self.parameters
        }


@dataclass
class CompressionResult:
    """Result of log compression operation."""
    structured_logs: List[StructuredLog]
    template_registry: Dict[str, int]
    total_lines: int
    unique_templates: int


# Type aliases
LogParserClass = Any  # Type for logparser classes
TemplateRegistry = Dict[str, int]
