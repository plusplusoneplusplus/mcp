#!/usr/bin/env python3
# Test script to verify tools.yaml integration

import os
import sys
import logging
import yaml
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tools_test")

# Add parent directory to path to allow importing mcp_core
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the ToolsAdapter
from mcp_core.tools_adapter import ToolsAdapter

def main():
    print("\n=== MCP Tools YAML Integration Test ===\n")
    
    # Get the server directory
    server_dir = Path(parent_dir) / "server"
    
    # Load tools.yaml content
    yaml_path = server_dir / "tools.yaml"
    if not yaml_path.exists():
        print(f"ERROR: tools.yaml not found at {yaml_path}")
        return
    
    with open(yaml_path, 'r') as f:
        yaml_data = yaml.safe_load(f)
    
    print(f"Found {len(yaml_data.get('tools', {}))} tools and {len(yaml_data.get('tasks', {}))} tasks in tools.yaml\n")
    
    # Create the ToolsAdapter instance
    print("Initializing ToolsAdapter (this will load tools from plugins and tools.yaml)...")
    adapter = ToolsAdapter()
    
    # Get all registered tools
    tools = adapter.get_tools()
    print(f"\nRegistered tools: {len(tools)}")
    
    # Print all tools
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:60]}..." if len(tool.description) > 60 else f"  - {tool.name}: {tool.description}")
    
    # Check if specific tools from tools.yaml are registered
    yaml_tool_names = yaml_data.get('tools', {}).keys()
    registered_tool_names = [tool.name for tool in tools]
    
    print("\nVerifying tools from tools.yaml:")
    for name in yaml_tool_names:
        if name in registered_tool_names:
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name} (not registered)")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main() 