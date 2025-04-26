#!/usr/bin/env python3
# Test script to verify type conversion between mcp_core.types and mcp.types

import os
import sys
import logging
import pytest
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("conversion_test")

# Add parent directory to path to allow importing mcp_core
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from mcp_core.types
from mcp_core.types import TextContent as CoreTextContent
from mcp_core.types import Tool as CoreTool

# Import from mcp.types
from mcp.types import TextContent as McpTextContent
from mcp.types import Tool as McpTool

def test_tool_conversion():
    """Test conversion between CoreTool and McpTool"""
    # Create a CoreTool instance
    core_tool = CoreTool(
        name="test_tool",
        description="A test tool",
        inputSchema={
            "type": "object",
            "properties": {
                "parameter": {"type": "string"}
            }
        }
    )
    
    # Convert to McpTool
    mcp_tool = McpTool(
        name=core_tool.name,
        description=core_tool.description,
        inputSchema=core_tool.inputSchema
    )
    
    # Verify conversion preserves properties
    assert mcp_tool.name == core_tool.name
    assert mcp_tool.description == core_tool.description
    assert mcp_tool.inputSchema == core_tool.inputSchema

def test_text_content_conversion():
    """Test conversion between CoreTextContent and McpTextContent"""
    # Create a CoreTextContent instance
    core_text = CoreTextContent(
        type="text",
        text="This is a test message"
    )
    
    # Convert to McpTextContent
    mcp_text = McpTextContent(
        type=core_text.type,
        text=core_text.text,
        annotations=core_text.annotations
    )
    
    # Verify conversion preserves properties
    assert mcp_text.type == core_text.type
    assert mcp_text.text == core_text.text
    assert mcp_text.annotations == core_text.annotations 