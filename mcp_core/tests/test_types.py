#!/usr/bin/env python3
# Test script to verify mcp_core types implementation

import os
import sys
import logging
import pytest
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("types_test")

# Add parent directory to path to allow importing mcp_core
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from the new types module
from mcp_core.types import TextContent, Tool

def test_text_content():
    """Test the TextContent class"""
    # Create a TextContent instance
    text_content = TextContent(
        type="text",
        text="This is a test message"
    )
    
    # Verify properties
    assert text_content.type == "text"
    assert text_content.text == "This is a test message"
    
    # Test string representation
    str_repr = str(text_content)
    assert "text" in str_repr
    assert "This is a test message" in str_repr

def test_tool():
    """Test the Tool class"""
    # Create a Tool instance
    tool = Tool(
        name="test_tool",
        description="A test tool",
        inputSchema={
            "type": "object",
            "properties": {
                "parameter": {"type": "string"}
            }
        }
    )
    
    # Verify properties
    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert "parameter" in tool.inputSchema["properties"]
    
    # Test string representation
    str_repr = str(tool)
    assert "test_tool" in str_repr
    assert "A test tool" in str_repr 