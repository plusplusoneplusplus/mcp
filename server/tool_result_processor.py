"""Tool result processing utilities.

This module provides utilities for processing tool execution results and converting
them into the appropriate MCP content types (TextContent, ImageContent).
"""

from typing import Any, List, Union
from mcp.types import TextContent, ImageContent


def process_tool_result(result: Any) -> List[Union[TextContent, ImageContent]]:
    """Process a tool execution result into MCP content types.

    This function handles various result types and converts them into a list of
    TextContent and/or ImageContent objects that can be returned by the MCP server.

    Args:
        result: The result from a tool execution. Can be:
            - List of ImageContent/TextContent objects (returned as-is)
            - List of dicts with text properties (converted to TextContent)
            - List of objects with type/text attributes (converted to TextContent)
            - Single ImageContent/TextContent object (wrapped in list)
            - Dictionary (formatted and wrapped in TextContent)
            - Any other type (converted to string and wrapped in TextContent)

    Returns:
        List of TextContent and/or ImageContent objects
    """
    if isinstance(result, list):
        # Check if the list contains ImageContent or TextContent objects
        if all(isinstance(item, (ImageContent, TextContent)) for item in result):
            return result
        elif all(isinstance(item, dict) for item in result):
            return [TextContent(**item) for item in result]
        elif all(hasattr(item, "type") and hasattr(item, "text") for item in result):
            return [
                TextContent(
                    type=item.type,
                    text=item.text,
                    annotations=getattr(item, "annotations", None),
                )
                for item in result
            ]
        else:
            # Mixed or unknown list contents - convert to text
            return [TextContent(type="text", text=str(result))]
    elif isinstance(result, (ImageContent, TextContent)):
        # Single ImageContent or TextContent object
        return [result]
    elif isinstance(result, dict):
        text = format_result_as_text(result)
        return [TextContent(type="text", text=text)]
    else:
        return [TextContent(type="text", text=str(result))]


def format_result_as_text(result: dict) -> str:
    """Format a result dictionary as text.

    Args:
        result: Dictionary containing tool execution results

    Returns:
        Formatted text representation of the result
    """
    if not result.get("success", True):
        return f"Error: {result.get('error', 'Unknown error')}"

    # Different formatting based on the type of result
    if "output" in result:
        return result.get("output", "")
    elif "html" in result:
        return f"HTML content (length: {result.get('html_length', 0)}):\n{result.get('html', '')}"
    else:
        # Generic formatting
        return "\n".join(f"{k}: {v}" for k, v in result.items() if k != "success")
