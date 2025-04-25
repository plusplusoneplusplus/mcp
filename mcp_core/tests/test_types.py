#!/usr/bin/env python3
# Test script to verify mcp_core types implementation

import os
import sys
import logging
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

def main():
    print("\n=== MCP Core Types Test ===\n")
    
    # Create a TextContent instance
    text_content = TextContent(
        type="text",
        text="This is a test message"
    )
    print(f"TextContent: {text_content}")
    
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
    print(f"Tool: {tool}")
    
    print("\nTypes work correctly!\n")

if __name__ == "__main__":
    main() 