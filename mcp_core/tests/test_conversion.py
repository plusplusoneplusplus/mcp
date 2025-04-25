#!/usr/bin/env python3
# Test script to verify type conversion between mcp_core.types and mcp.types

import os
import sys
import logging
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

def main():
    print("\n=== Type Conversion Test ===\n")
    
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
    print(f"CoreTool: {core_tool}")
    
    # Convert to McpTool
    mcp_tool = McpTool(
        name=core_tool.name,
        description=core_tool.description,
        inputSchema=core_tool.inputSchema
    )
    print(f"McpTool: {mcp_tool}")
    
    # Create a CoreTextContent instance
    core_text = CoreTextContent(
        type="text",
        text="This is a test message"
    )
    print(f"CoreTextContent: {core_text}")
    
    # Convert to McpTextContent
    mcp_text = McpTextContent(
        type=core_text.type,
        text=core_text.text,
        annotations=core_text.annotations
    )
    print(f"McpTextContent: {mcp_text}")
    
    print("\nType conversion works correctly!\n")

if __name__ == "__main__":
    main() 