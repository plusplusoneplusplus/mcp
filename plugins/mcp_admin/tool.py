from typing import Dict, Any

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool, discover_and_register_tools, registry
from mcp_tools.plugin_config import config
from mcp_tools.plugin_manager import refresh_plugins


@register_tool(os_type="all")
class McpAdminTool(ToolInterface):
    """Tool for administering the running MCP instance."""

    @property
    def name(self) -> str:
        return "mcp_admin"

    @property
    def description(self) -> str:
        return "Inspect and manage MCP plugins at runtime."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "enable_plugin",
                        "disable_plugin",
                        "refresh_plugins",
                    ],
                    "description": "Action to perform",
                },
                "plugin": {
                    "type": "string",
                    "description": "Target plugin name",
                },
                "force": {
                    "type": "boolean",
                    "description": "Force clean before reinstall when refreshing",
                },
            },
            "required": ["operation"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        plugin = arguments.get("plugin")

        if operation == "enable_plugin":
            if not plugin:
                return {"success": False, "error": "Plugin name required"}
            config.enable_plugin(plugin)
            if plugin not in registry.tools:
                discover_and_register_tools()
            return {"success": True, "plugin": plugin, "enabled": True}
        elif operation == "disable_plugin":
            if not plugin:
                return {"success": False, "error": "Plugin name required"}
            config.disable_plugin(plugin)
            registry.tools.pop(plugin, None)
            registry.instances.pop(plugin, None)
            return {"success": True, "plugin": plugin, "enabled": False}
        elif operation == "refresh_plugins":
            force = bool(arguments.get("force"))
            refresh_plugins(force_clean=force)
            discover_and_register_tools()
            return {"success": True, "refreshed": True, "force": force}

        return {"success": False, "error": f"Unknown operation: {operation}"}
