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
        WorkItemCreateResponse,
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
    if spec is not None and spec.loader is not None:
        types_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(types_module)

        # Import the types
        WorkItem = types_module.WorkItem
        WorkItemResponse = types_module.WorkItemResponse
        WorkItemCreateResponse = types_module.WorkItemCreateResponse
    else:
        raise ImportError("Could not load types module")


@register_tool
class AzureWorkItemTool(ToolInterface):
    """Dedicated tool for managing Azure DevOps Work Items.

    This tool provides work item management capabilities including
    retrieving work item details, creating new work items, and managing
    work item properties. It automatically loads default configuration
    values from the environment while allowing parameter overrides for
    specific operations.

    Configuration:
        The tool automatically loads default values from environment variables
        with the AZREPO_ prefix:
        - AZREPO_ORG: Default organization URL
        - AZREPO_PROJECT: Default project name/ID
        - AZREPO_AREA_PATH: Default area path for new work items
        - AZREPO_ITERATION: Default iteration path for new work items

    Example:
        # Get work item details
        work_item = await workitem_tool.execute_tool({
            "operation": "get",
            "work_item_id": 12345
        })

        # Create a new work item
        work_item = await workitem_tool.execute_tool({
            "operation": "create",
            "title": "New feature request",
            "description": "Detailed description of the feature"
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
                        "create",
                    ],
                },
                "work_item_id": {
                    "type": ["string", "integer"],
                    "description": "ID of the work item (required for get operation)",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the work item (required for create operation)",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the work item (optional for create operation)",
                    "nullable": True,
                },
                "work_item_type": {
                    "type": "string",
                    "description": "Type of work item (Bug, Task, User Story, etc.)",
                    "default": "Task",
                    "nullable": True,
                },
                "area_path": {
                    "type": "string",
                    "description": "Area path for the work item (uses configured default if not provided)",
                    "nullable": True,
                },
                "iteration_path": {
                    "type": "string",
                    "description": "Iteration path for the work item (uses configured default if not provided)",
                    "nullable": True,
                },
                "organization": {
                    "type": "string",
                    "description": "Azure DevOps organization URL",
                    "nullable": True,
                },
                "project": {
                    "type": "string",
                    "description": "Azure DevOps project name/ID",
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
            "required": ["operation"],
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

        # Initialize default values
        self.default_organization: Optional[str] = None
        self.default_project: Optional[str] = None
        self.default_area_path: Optional[str] = None
        self.default_iteration_path: Optional[str] = None
        self.default_pat: Optional[str] = None

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
            self.default_organization = azrepo_params.get("org")
            self.default_project = azrepo_params.get("project")
            self.default_area_path = azrepo_params.get("area_path")
            self.default_iteration_path = azrepo_params.get("iteration")
            self.default_pat = azrepo_params.get("pat")

            self.logger.debug(
                f"Loaded Azure work item configuration: org={self.default_organization}, "
                f"project={self.default_project}, area_path={self.default_area_path}, "
                f"iteration={self.default_iteration_path}, pat={'***' if self.default_pat else None}"
            )

        except Exception as e:
            self.logger.warning(f"Failed to load Azure work item configuration: {e}")
            # Set defaults to None if configuration loading fails
            self.default_organization = None
            self.default_project = None
            self.default_area_path = None
            self.default_iteration_path = None
            self.default_pat = None

    def _get_param_with_default(
        self, param_value: Optional[str], default_value: Optional[str]
    ) -> Optional[str]:
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
        project: Optional[str] = None,
        as_of: Optional[str] = None,
        expand: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get details of a specific work item.

        Args:
            work_item_id: ID of the work item
            organization: Azure DevOps organization URL (uses configured default if not provided)
            project: Azure DevOps project name/ID (accepted for compatibility but not used - work item IDs are globally unique within an organization)
            as_of: Work item details as of a particular date and time
            expand: The expand parameters for work item attributes (all, fields, links, none, relations)
            fields: Comma-separated list of requested fields

        Returns:
            Dictionary with success status and work item details
        """
        command = f"boards work-item show --id {work_item_id}"

        # Use configured defaults for core parameters
        org = self._get_param_with_default(organization, self.default_organization)
        # Note: project parameter is not used for work item retrieval as work item IDs are globally unique within an organization

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

    async def create_work_item(
        self,
        title: str,
        description: Optional[str] = None,
        work_item_type: str = "Task",
        area_path: Optional[str] = None,
        iteration_path: Optional[str] = None,
        organization: Optional[str] = None,
        project: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new work item.

        Args:
            title: Title of the work item
            description: Description of the work item
            work_item_type: Type of work item (Bug, Task, User Story, etc.)
            area_path: Area path for the work item (uses configured default if not provided)
            iteration_path: Iteration path for the work item (uses configured default if not provided)
            organization: Azure DevOps organization URL (uses configured default if not provided)
            project: Azure DevOps project name/ID (uses configured default if not provided)

        Returns:
            Dictionary with success status and created work item details
        """
        command = f"boards work-item create --type '{work_item_type}' --title '{title}'"

        # Use configured defaults for core parameters
        org = self._get_param_with_default(organization, self.default_organization)
        proj = self._get_param_with_default(project, self.default_project)
        area = self._get_param_with_default(area_path, self.default_area_path)
        iteration = self._get_param_with_default(iteration_path, self.default_iteration_path)

        # Add optional parameters
        if org:
            command += f" --org {org}"
        if proj:
            command += f" --project {proj}"
        if description:
            command += f" --description '{description}'"
        if area:
            command += f" --area '{area}'"
        if iteration:
            command += f" --iteration '{iteration}'"

        return await self._run_az_command(command)

    async def create_work_item_sdk(
        self,
        title: str,
        description: Optional[str] = None,
        work_item_type: str = "Task",
        area_path: Optional[str] = None,
        iteration_path: Optional[str] = None,
        organization: Optional[str] = None,
        project: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new work item using Azure DevOps Python SDK.

        This is a proof of concept implementation that demonstrates work item creation
        using the Azure DevOps Python SDK instead of CLI commands.

        Args:
            title: Title of the work item
            description: Description of the work item
            work_item_type: Type of work item (Bug, Task, User Story, etc.)
            area_path: Area path for the work item (uses configured default if not provided)
            iteration_path: Iteration path for the work item (uses configured default if not provided)
            organization: Azure DevOps organization URL (uses configured default if not provided)
            project: Azure DevOps project name/ID (uses configured default if not provided)

        Returns:
            Dictionary with success status and created work item details
        """
        try:
            # Import Azure DevOps SDK components
            from azure.devops.connection import Connection
            from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation
            from msrest.authentication import BasicAuthentication

            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(project, self.default_project)
            area = self._get_param_with_default(area_path, self.default_area_path)
            iteration = self._get_param_with_default(iteration_path, self.default_iteration_path)

            # Validate required parameters
            if not org:
                return {
                    "success": False,
                    "error": "Organization URL is required. Set AZREPO_ORG environment variable or provide organization parameter."
                }

            if not proj:
                return {
                    "success": False,
                    "error": "Project name is required. Set AZREPO_PROJECT environment variable or provide project parameter."
                }

            # Get PAT from configuration
            azrepo_params = env_manager.get_azrepo_parameters()
            pat = azrepo_params.get("pat")

            if not pat:
                return {
                    "success": False,
                    "error": "Personal Access Token (PAT) is required for SDK authentication. Set AZREPO_PAT environment variable."
                }

            # Ensure organization URL is properly formatted
            if not org.startswith("https://"):
                org = f"https://dev.azure.com/{org}"

            self.logger.debug(f"Creating work item using SDK: org={org}, project={proj}, type={work_item_type}")

            # Create authentication and connection
            credentials = BasicAuthentication('', pat)
            connection = Connection(base_url=org, creds=credentials)

            # Get work item tracking client
            wit_client = connection.clients.get_work_item_tracking_client()

            # Prepare work item data using JsonPatchOperation
            work_item_data = [
                JsonPatchOperation(
                    op="add",
                    path="/fields/System.Title",
                    value=title
                )
            ]

            # Add description if provided
            if description:
                work_item_data.append(
                    JsonPatchOperation(
                        op="add",
                        path="/fields/System.Description",
                        value=description
                    )
                )

            # Add area path if provided
            if area:
                work_item_data.append(
                    JsonPatchOperation(
                        op="add",
                        path="/fields/System.AreaPath",
                        value=area
                    )
                )

            # Add iteration path if provided
            if iteration:
                work_item_data.append(
                    JsonPatchOperation(
                        op="add",
                        path="/fields/System.IterationPath",
                        value=iteration
                    )
                )

            # Create the work item
            work_item = wit_client.create_work_item(
                document=work_item_data,
                project=proj,
                type=work_item_type
            )

            self.logger.info(f"Successfully created work item {work_item.id} using SDK")

            # Convert work item to dictionary format similar to CLI output
            work_item_dict = {
                "id": work_item.id,
                "url": work_item.url,
                "fields": {}
            }

            # Extract fields from the work item
            if hasattr(work_item, 'fields') and work_item.fields:
                for field_name, field_value in work_item.fields.items():
                    work_item_dict["fields"][field_name] = field_value

            return {
                "success": True,
                "data": work_item_dict,
                "method": "sdk"  # Indicate this was created using SDK
            }

        except ImportError as e:
            self.logger.error(f"Azure DevOps SDK not available: {e}")
            return {
                "success": False,
                "error": f"Azure DevOps SDK not available: {e}. Please install azure-devops package."
            }

        except Exception as e:
            self.logger.error(f"Failed to create work item using SDK: {e}")
            return {
                "success": False,
                "error": f"Failed to create work item using SDK: {str(e)}"
            }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments."""
        operation = arguments.get("operation", "")

        if operation == "get":
            work_item_id = arguments.get("work_item_id")
            if work_item_id is None:
                return {"success": False, "error": "work_item_id is required for get operation"}

            return await self.get_work_item(
                work_item_id=work_item_id,
                organization=arguments.get("organization"),
                project=arguments.get("project"),
                as_of=arguments.get("as_of"),
                expand=arguments.get("expand"),
                fields=arguments.get("fields"),
            )
        elif operation == "create":
            title = arguments.get("title")
            if not title:
                return {"success": False, "error": "title is required for create operation"}

            return await self.create_work_item(
                title=title,
                description=arguments.get("description"),
                work_item_type=arguments.get("work_item_type", "Task"),
                area_path=arguments.get("area_path"),
                iteration_path=arguments.get("iteration_path"),
                organization=arguments.get("organization"),
                project=arguments.get("project"),
            )
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
