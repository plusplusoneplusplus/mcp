"""
Types used throughout the mcp_core package.

This module contains type definitions that were previously imported from mcp.types,
making mcp_core self-contained and not dependent on the mcp package.
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, ConfigDict


class Annotations(BaseModel):
    """Annotations for content."""

    audience: List[Literal["user", "assistant"]] = None
    priority: float = None

    model_config = ConfigDict(extra="allow")


class TextContent(BaseModel):
    """Text content for a message."""

    type: Literal["text"]
    text: str
    """The text content of the message."""
    annotations: Optional[Annotations] = None

    model_config = ConfigDict(extra="allow")


class Tool(BaseModel):
    """Definition for a tool the client can call."""

    name: str
    """The name of the tool."""
    description: Optional[str] = None
    """A human-readable description of the tool."""
    inputSchema: Dict[str, Any]
    """A JSON Schema object defining the expected parameters for the tool."""

    model_config = ConfigDict(extra="allow")


# Additional types that might be needed
class ToolResult(BaseModel):
    """Result of a tool call."""

    content: List[TextContent]
    isError: bool = False

    model_config = ConfigDict(extra="allow")
