#!/usr/bin/env python3
"""
Demonstration script for the new plugin enable/disable configuration system.

This script shows how to use the enhanced PluginConfig class to manage
plugin enable/disable settings through environment variables and programmatic API.
"""

import os
import sys
from pathlib import Path

# Add the mcp_tools directory to the path
sys.path.insert(0, str(Path(__file__).parent / "mcp_tools"))

from mcp_tools.plugin_config import PluginConfig
from mcp_tools.plugin import registry
from mcp_tools.interfaces import ToolInterface


class DemoTool1(ToolInterface):
    """Demo tool 1 for testing."""
    
    @property
    def name(self) -> str:
        return "demo_tool_1"
    
    @property
    def description(self) -> str:
        return "First demo tool"
    
    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}
    
    async def execute_tool(self, arguments: dict) -> any:
        return {"message": "Demo tool 1 executed"}


class DemoTool2(ToolInterface):
    """Demo tool 2 for testing."""
    
    @property
    def name(self) -> str:
        return "demo_tool_2"
    
    @property
    def description(self) -> str:
        return "Second demo tool"
    
    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}
    
    async def execute_tool(self, arguments: dict) -> any:
        return {"message": "Demo tool 2 executed"}


def demo_basic_functionality():
    """Demonstrate basic plugin enable/disable functionality."""
    print("=== Basic Plugin Enable/Disable Demo ===")
    
    # Clear registry and reset config
    registry.clear()
    config = PluginConfig()
    
    print(f"Default plugin enable mode: {config.plugin_enable_mode}")
    print(f"Enabled plugins: {config.enabled_plugins}")
    print(f"Disabled plugins: {config.disabled_plugins}")
    
    # Register some tools
    registry.register_tool(DemoTool1, source="code")
    registry.register_tool(DemoTool2, source="code")
    
    print(f"\nRegistered tools: {list(registry.tools.keys())}")
    
    # Disable one tool
    config.disable_plugin("demo_tool_1")
    print(f"\nAfter disabling demo_tool_1:")
    print(f"demo_tool_1 enabled: {config.is_plugin_enabled('demo_tool_1')}")
    print(f"demo_tool_2 enabled: {config.is_plugin_enabled('demo_tool_2')}")
    
    # Enable it back
    config.enable_plugin("demo_tool_1")
    print(f"\nAfter re-enabling demo_tool_1:")
    print(f"demo_tool_1 enabled: {config.is_plugin_enabled('demo_tool_1')}")
    
    # Get available plugins metadata
    plugins = config.get_available_plugins()
    print(f"\nAvailable plugins metadata:")
    for name, metadata in plugins.items():
        print(f"  {name}: enabled={metadata['enabled']}, source={metadata['source']}")


def demo_environment_variables():
    """Demonstrate environment variable configuration."""
    print("\n=== Environment Variable Configuration Demo ===")
    
    # Set environment variables
    os.environ["MCP_PLUGIN_MODE"] = "whitelist"
    os.environ["MCP_ENABLED_PLUGINS"] = "demo_tool_1,allowed_tool"
    os.environ["MCP_DISABLED_PLUGINS"] = "demo_tool_2"
    
    # Create new config to load from environment
    config = PluginConfig()
    
    print(f"Plugin enable mode: {config.plugin_enable_mode}")
    print(f"Enabled plugins: {config.enabled_plugins}")
    print(f"Disabled plugins: {config.disabled_plugins}")
    
    # Test plugin status
    print(f"\nPlugin status in whitelist mode:")
    print(f"demo_tool_1 enabled: {config.is_plugin_enabled('demo_tool_1')}")  # Should be True
    print(f"demo_tool_2 enabled: {config.is_plugin_enabled('demo_tool_2')}")  # Should be False
    print(f"unknown_tool enabled: {config.is_plugin_enabled('unknown_tool')}")  # Should be False
    
    # Clean up environment
    del os.environ["MCP_PLUGIN_MODE"]
    del os.environ["MCP_ENABLED_PLUGINS"]
    del os.environ["MCP_DISABLED_PLUGINS"]


def demo_plugin_modes():
    """Demonstrate different plugin enable modes."""
    print("\n=== Plugin Enable Modes Demo ===")
    
    config = PluginConfig()
    
    # Test "all" mode (default)
    config.plugin_enable_mode = "all"
    config.disabled_plugins = {"disabled_tool"}
    print(f"\nMode: {config.plugin_enable_mode}")
    print(f"random_tool enabled: {config.is_plugin_enabled('random_tool')}")  # Should be True
    print(f"disabled_tool enabled: {config.is_plugin_enabled('disabled_tool')}")  # Should be False
    
    # Test "whitelist" mode
    config.plugin_enable_mode = "whitelist"
    config.enabled_plugins = {"allowed_tool"}
    print(f"\nMode: {config.plugin_enable_mode}")
    print(f"allowed_tool enabled: {config.is_plugin_enabled('allowed_tool')}")  # Should be True
    print(f"random_tool enabled: {config.is_plugin_enabled('random_tool')}")  # Should be False
    
    # Test "blacklist" mode
    config.plugin_enable_mode = "blacklist"
    config.disabled_plugins = {"blocked_tool"}
    print(f"\nMode: {config.plugin_enable_mode}")
    print(f"random_tool enabled: {config.is_plugin_enabled('random_tool')}")  # Should be True
    print(f"blocked_tool enabled: {config.is_plugin_enabled('blocked_tool')}")  # Should be False


def demo_registry_integration():
    """Demonstrate registry integration with plugin configuration."""
    print("\n=== Registry Integration Demo ===")
    
    # Clear and setup
    registry.clear()
    
    # Set up environment for blacklist mode
    os.environ["MCP_PLUGIN_MODE"] = "blacklist"
    os.environ["MCP_DISABLED_PLUGINS"] = "demo_tool_1"
    
    # Create new config
    from mcp_tools.plugin_config import config
    config._load_from_env()
    
    # Try to register tools
    result1 = registry.register_tool(DemoTool1, source="code")
    result2 = registry.register_tool(DemoTool2, source="code")
    
    print(f"demo_tool_1 registration result: {result1}")  # Should be None (not registered)
    print(f"demo_tool_2 registration result: {result2 is not None}")  # Should be True (registered)
    print(f"Registered tools: {list(registry.tools.keys())}")
    
    # Get plugin metadata from registry
    enabled_plugins = registry.get_enabled_plugins()
    disabled_plugins = registry.get_disabled_plugins()
    
    print(f"\nEnabled plugins: {list(enabled_plugins.keys())}")
    print(f"Disabled plugins: {list(disabled_plugins.keys())}")
    
    # Clean up environment
    del os.environ["MCP_PLUGIN_MODE"]
    del os.environ["MCP_DISABLED_PLUGINS"]


def main():
    """Run all demonstrations."""
    print("Plugin Enable/Disable Configuration System Demo")
    print("=" * 50)
    
    demo_basic_functionality()
    demo_environment_variables()
    demo_plugin_modes()
    demo_registry_integration()
    
    print("\n=== Demo Complete ===")
    print("The plugin enable/disable system provides:")
    print("- Programmatic API for enabling/disabling plugins")
    print("- Environment variable configuration support")
    print("- Three modes: 'all', 'whitelist', 'blacklist'")
    print("- Integration with plugin registry")
    print("- Comprehensive metadata about plugin status")
    print("- Backward compatibility with existing functionality")


if __name__ == "__main__":
    main() 