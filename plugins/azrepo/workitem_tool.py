"""Azure DevOps Work Item tool implementation."""

import logging
import json
from typing import Dict, Any, List, Optional, Union

# Import the required interfaces and decorators
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

# Import configuration manager
from config import env_manager

# Import types from the plugin
try:
    from .types import (
        WorkItem,
        WorkItemResponse,
    )
except ImportError:
    # Fallback for when module is loaded directly by plugin system
    import os
    import sys
    import importlib.util

    # Get the directory of this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    types_path = os.path.join(current_dir, "types.py")

    # Load types module directly
    spec = importlib.util.spec_from_file_location("types", types_path)
    types_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(types_module)

    # Import the types
    WorkItem = types_module.WorkItem
    WorkItemResponse = types_module.WorkItemResponse


@register_tool
class AzureWorkItemTool(ToolInterface):
    """Dedicated tool for managing Azure DevOps Work Items.

    This tool provides work item management capabilities including
    retrieving work item details and managing work item properties.
    It automatically loads default configuration values from the environment
    while allowing parameter overrides for specific operations.

    Configuration:
        The tool automatically loads default values from environment variables
        with the AZREPO_ prefix:
        - AZREPO_ORG: Default organization URL
        - AZREPO_PROJECT: Default project name/ID

    Example:
        # Get work item details
        work_item = await workitem_tool.execute_tool({
            "operation": "get",
            "work_item_id": 12345
        })

        # Get work item with specific fields
        work_item = await workitem_tool.execute_tool({
            "operation": "get",
            "work_item_id": 12345,
            "fields": "System.Id,System.Title,System.State"
        })
    """

    # Implement ToolInterface properties
    @property
    def name(self) -> str:
        """Get the tool name."""
        return "azure_work_item"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Manage Azure DevOps work items with comprehensive functionality"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The work item operation to perform",
                    "enum": [
                        "get",
                    ],
                },
                "work_item_id": {
                    "type": ["string", "integer"],
                    "description": "ID of the work item",
                },
                "organization": {
                    "type": "string",
                    "description": "Azure DevOps organization URL",
                    "nullable": True,
                },
                "as_of": {
                    "type": "string",
                    "description": "Work item details as of a particular date and time (e.g., '2019-01-20', '2019-01-20 00:20:00')",
                    "nullable": True,
                },
                "expand": {
                    "type": "string",
                    "description": "The expand parameters for work item attributes (all, fields, links, none, relations)",
                    "nullable": True,
                },
                "fields": {
                    "type": "string",
                    "description": "Comma-separated list of requested fields (e.g., System.Id,System.AreaPath)",
                    "nullable": True,
                },
            },
            "required": ["operation", "work_item_id"],
        }

    def __init__(self, command_executor=None):
        """Initialize the AzureWorkItemTool with a command executor and load configuration.

        Args:
            command_executor: An instance of CommandExecutor to use for running commands.
                              If None, it will be obtained from the registry.
        """
        if command_executor is None:
            # Get the command executor from the registry
            from mcp_tools.plugin import registry

            self.executor = registry.get_tool_instance("command_executor")
            if not self.executor:
                raise ValueError("Command executor not found in registry")
        else:
            self.executor = command_executor

        self.logger = logging.getLogger(__name__)

        # Load configuration defaults
        self._load_config()

    def _load_config(self):
        """Load default configuration from environment manager."""
        try:
            # Ensure environment is loaded
            env_manager.load()

            # Get Azure repo parameters
            azrepo_params = env_manager.get_azrepo_parameters()

            # Set default values
            self.default_organization = azrepo_params.get('org')
            self.default_project = azrepo_params.get('project')

            self.logger.debug(f"Loaded Azure work item configuration: org={self.default_organization}, "
                            f"project={self.default_project}")

        except Exception as e:
            self.logger.warning(f"Failed to load Azure work item configuration: {e}")
            # Set defaults to None if configuration loading fails
            self.default_organization = None
            self.default_project = None

    def _get_param_with_default(self, param_value: Optional[str], default_value: Optional[str]) -> Optional[str]:
        """Get parameter value with fallback to default configuration.

        Args:
            param_value: Explicitly provided parameter value
            default_value: Default value from configuration

        Returns:
            The parameter value to use (explicit value takes precedence)
        """
        return param_value if param_value is not None else default_value

    async def _run_az_command(
        self, command: str, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Run an Azure CLI command and parse the JSON output.

        Args:
            command: The az command to execute
            timeout: Optional timeout in seconds

        Returns:
            Parsed JSON response from the command
        """
        full_command = f"az {command} --output json"
        self.logger.debug(f"Executing command: {full_command}")

        result = await self.executor.execute_async(full_command, timeout)
        token = result.get("token")

        status = await self.executor.query_process(token, wait=True, timeout=timeout)

        if not status.get("success", False):
            self.logger.error(f"Command failed: {status.get('error', 'Unknown error')}")
            return {"success": False, "error": status.get("error", "Unknown error")}

        try:
            output = status.get("output", "")
            if output:
                return {"success": True, "data": json.loads(output)}
            else:
                return {"success": True, "data": {}}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON output: {e}")
            return {
                "success": False,
                "error": f"Failed to parse JSON output: {e}",
                "raw_output": status.get("output", ""),
            }

    async def get_work_item(
        self,
        work_item_id: Union[int, str],
        organization: Optional[str] = None,
        as_of: Optional[str] = None,
        expand: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get details of a specific work item.

        Args:
            work_item_id: ID of the work item
            organization: Azure DevOps organization URL (uses configured default if not provided)
            as_of: Work item details as of a particular date and time
            expand: The expand parameters for work item attributes (all, fields, links, none, relations)
            fields: Comma-separated list of requested fields

        Returns:
            Dictionary with success status and work item details
        """
        command = f"boards work-item show --id {work_item_id}"

        # Use configured defaults for core parameters
        org = self._get_param_with_default(organization, self.default_organization)

        # Add optional parameters
        if org:
            command += f" --org {org}"
        if as_of:
            command += f" --as-of '{as_of}'"
        if expand:
            command += f" --expand {expand}"
        if fields:
            command += f" --fields {fields}"

        return await self._run_az_command(command)

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments."""
        operation = arguments.get("operation", "")

        if operation == "get":
            return await self.get_work_item(
                work_item_id=arguments.get("work_item_id"),
                organization=arguments.get("organization"),
                as_of=arguments.get("as_of"),
                expand=arguments.get("expand"),
                fields=arguments.get("fields"),
            )
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
