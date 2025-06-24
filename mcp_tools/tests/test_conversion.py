#!/usr/bin/env python3
# Test script to verify type conversion between mcp_tools.types and mcp.types

import os
import sys
import logging
import pytest
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("conversion_test")

# Add parent directory to path to allow importing mcp_tools
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from mcp_tools.mcp_types (formerly mcp_core.types)
from mcp_tools.mcp_types import TextContent as ToolsTextContent
from mcp_tools.mcp_types import Tool as ToolsTool

# Import from mcp.types
from mcp.types import TextContent as McpTextContent
from mcp.types import Tool as McpTool


def test_tool_conversion():
    """Test conversion between ToolsTool and McpTool"""
    # Create a ToolsTool instance
    tools_tool = ToolsTool(
        name="test_tool",
        description="A test tool",
        inputSchema={"type": "object", "properties": {"parameter": {"type": "string"}}},
    )

    # Convert to McpTool
    mcp_tool = McpTool(
        name=tools_tool.name,
        description=tools_tool.description,
        inputSchema=tools_tool.inputSchema,
    )

    # Verify conversion preserves properties
    assert mcp_tool.name == tools_tool.name
    assert mcp_tool.description == tools_tool.description
    assert mcp_tool.inputSchema == tools_tool.inputSchema


def test_text_content_conversion():
    """Test conversion between ToolsTextContent and McpTextContent"""
    # Create a ToolsTextContent instance
    tools_text = ToolsTextContent(type="text", text="This is a test message")

    # Convert to McpTextContent
    mcp_text = McpTextContent(
        type=tools_text.type, text=tools_text.text, annotations=tools_text.annotations
    )

    # Verify conversion preserves properties
    assert mcp_text.type == tools_text.type
    assert mcp_text.text == tools_text.text
    assert mcp_text.annotations == tools_text.annotations
