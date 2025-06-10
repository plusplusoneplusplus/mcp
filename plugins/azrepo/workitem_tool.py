"""Azure DevOps Work Item tool implementation."""

import logging
import json
import aiohttp
from typing import Dict, Any, List, Optional, Union

# Import the required interfaces and decorators
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

# Import configuration manager
from config import env_manager

# Import shared Azure REST API utilities
from .azure_rest_utils import (
    get_current_username,
    get_auth_headers,
    build_api_url,
    process_rest_response,
)

# Import markdown to HTML conversion utility
from utils.markdown_to_html import detect_and_convert_markdown

# Import types from the plugin
try:
    from .types import (
        WorkItem,
        WorkItemResponse,
        WorkItemCreateResponse,
        WorkItemUpdateResponse,
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
        WorkItemUpdateResponse = types_module.WorkItemUpdateResponse
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

    Features:
    - Automatic markdown to HTML conversion for work item descriptions
    - Support for all standard Azure DevOps work item types

    Configuration:
        The tool automatically loads default values from environment variables
        with the AZREPO_ prefix:
        - AZREPO_ORG: Default organization URL
        - AZREPO_PROJECT: Default project name/ID
        - AZREPO_AREA_PATH: Default area path for new work items
        - AZREPO_ITERATION: Default iteration path for new work items
        - AZREPO_BEARER_TOKEN: Bearer token for REST API authentication (static)
        - AZREPO_BEARER_TOKEN_COMMAND: Command to get bearer token dynamically
          (should output JSON with "accessToken" property)

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

        # Update an existing work item
        work_item = await workitem_tool.execute_tool({
            "operation": "update",
            "work_item_id": 12345,
            "title": "Updated feature request",
            "description": "Updated description with **markdown** support"
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
                        "update",
                    ],
                },
                "work_item_id": {
                    "type": ["string", "integer"],
                    "description": "ID of the work item (required for get and update operations)",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the work item (required for create operation, optional for update operation)",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the work item (optional for create and update operations). Supports markdown format - will be automatically converted to HTML for Azure DevOps.",
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
                "assigned_to": {
                    "type": "string",
                    "description": "User to assign the work item to. Use 'current' to assign to current user, 'none' for unassigned, or specify a username/email. Defaults to current user if not specified.",
                    "default": "current",
                    "nullable": True,
                },
                "auto_assign_to_current_user": {
                    "type": "boolean",
                    "description": "Whether to automatically assign work items to the current user by default. Defaults to true.",
                    "default": True,
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
        self.bearer_token: Optional[str] = None
        self.auto_assign_to_current_user: bool = True
        self.default_assignee: Optional[str] = None

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
            self.bearer_token = azrepo_params.get("bearer_token")

            # Load assignment preferences
            self.auto_assign_to_current_user = azrepo_params.get("auto_assign_to_current_user", True)
            self.default_assignee = azrepo_params.get("default_assignee")

            self.logger.debug(
                f"Loaded Azure work item configuration: org={self.default_organization}, "
                f"project={self.default_project}, area_path={self.default_area_path}, "
                f"iteration={self.default_iteration_path}, bearer_token={'***' if self.bearer_token else None}, "
                f"auto_assign_to_current_user={self.auto_assign_to_current_user}, "
                f"default_assignee={self.default_assignee}"
            )

        except Exception as e:
            self.logger.warning(f"Failed to load Azure work item configuration: {e}")
            # Set defaults to None if configuration loading fails
            self.default_organization = None
            self.default_project = None
            self.default_area_path = None
            self.default_iteration_path = None
            self.bearer_token = None

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

    # Moved to azure_rest_utils.py

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
        """Get details of a specific work item using Azure DevOps REST API.

        Args:
            work_item_id: ID of the work item
            organization: Azure DevOps organization URL (uses configured default if not provided)
            project: Azure DevOps project name/ID (uses configured default if not provided)
            as_of: Work item details as of a particular date and time
            expand: The expand parameters for work item attributes (all, fields, links, none, relations)
            fields: Comma-separated list of requested fields

        Returns:
            Dictionary with success status and work item details
        """
        try:
            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(project, self.default_project)

            if not org:
                return {"success": False, "error": "Organization is required"}
            if not proj:
                return {"success": False, "error": "Project is required"}

            # Construct the REST API URL
            endpoint = f"wit/workitems/{work_item_id}"

            # Build query parameters
            query_params = ["api-version=7.1"]

            if as_of:
                query_params.append(f"asOf={as_of}")
            if expand:
                query_params.append(f"$expand={expand}")
            if fields:
                query_params.append(f"fields={fields}")

            # Add query parameters to endpoint
            if query_params:
                endpoint += "?" + "&".join(query_params)

            url = build_api_url(org, proj, endpoint)

            # Get authentication headers (use application/json for GET requests)
            headers = get_auth_headers(content_type="application/json")

            self.logger.debug(f"Getting work item via REST API: {url}")

            # Make the REST API call
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            work_item_data = json.loads(response_text)
                            return {"success": True, "data": work_item_data}
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Failed to parse work item response: {e}")
                            return {
                                "success": False,
                                "error": f"Failed to parse response: {e}",
                                "raw_output": response_text
                            }
                    elif response.status == 404:
                        self.logger.error(f"Work item {work_item_id} not found")
                        return {
                            "success": False,
                            "error": f"Work item {work_item_id} not found",
                            "raw_output": response_text
                        }
                    else:
                        self.logger.error(f"Work item retrieval failed with status {response.status}: {response_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {response_text}",
                            "raw_output": response_text
                        }

        except Exception as e:
            self.logger.error(f"Error retrieving work item: {e}")
            return {"success": False, "error": str(e)}

    async def create_work_item(
        self,
        title: str,
        description: Optional[str] = None,
        work_item_type: str = "Task",
        area_path: Optional[str] = None,
        iteration_path: Optional[str] = None,
        assigned_to: Optional[str] = "current",
        auto_assign_to_current_user: bool = True,
        organization: Optional[str] = None,
        project: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new work item using Azure DevOps REST API.

        Args:
            title: Title of the work item
            description: Description of the work item (supports markdown - will be automatically converted to HTML)
            work_item_type: Type of work item (Bug, Task, User Story, etc.)
            area_path: Area path for the work item (uses configured default if not provided)
            iteration_path: Iteration path for the work item (uses configured default if not provided)
            assigned_to: User to assign work item to. Special values:
                - "current": Assign to current user (default)
                - "none" or None: Leave unassigned
                - Any other string: Assign to specified user
            auto_assign_to_current_user: Whether to auto-assign to current user by default
            organization: Azure DevOps organization URL (uses configured default if not provided)
            project: Azure DevOps project name/ID (uses configured default if not provided)

        Returns:
            Dictionary with success status and created work item details
        """
        try:
            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(project, self.default_project)
            area = self._get_param_with_default(area_path, self.default_area_path)
            iteration = self._get_param_with_default(iteration_path, self.default_iteration_path)

            if not org:
                return {"success": False, "error": "Organization is required"}
            if not proj:
                return {"success": False, "error": "Project is required"}

            # Construct the REST API URL using organization name or URL
            url = build_api_url(
                org,
                proj,
                f"wit/workitems/${work_item_type}?api-version=7.1",
            )

            # Build the JSON patch document for work item creation
            patch_document = [
                {
                    "op": "add",
                    "path": "/fields/System.Title",
                    "value": title
                }
            ]

            # Add description if provided (convert markdown to HTML if needed)
            if description:
                # Detect if description is markdown and convert to HTML
                html_description = detect_and_convert_markdown(description)
                patch_document.append({
                    "op": "add",
                    "path": "/fields/System.Description",
                    "value": html_description
                })

            # Add area path if provided
            if area:
                patch_document.append({
                    "op": "add",
                    "path": "/fields/System.AreaPath",
                    "value": area
                })

            # Add iteration path if provided
            if iteration:
                patch_document.append({
                    "op": "add",
                    "path": "/fields/System.IterationPath",
                    "value": iteration
                })

            # Handle assignment logic
            assignee = None
            # Check both parameter and instance configuration for auto-assignment
            should_auto_assign = auto_assign_to_current_user and self.auto_assign_to_current_user
            if should_auto_assign and assigned_to == "current":
                current_user = get_current_username()
                if current_user:
                    assignee = current_user
                    self.logger.debug(f"Auto-assigning work item to current user: {current_user}")
                else:
                    self.logger.warning("Could not determine current user for auto-assignment")
            elif assigned_to and assigned_to not in ["current", "none"]:
                assignee = assigned_to

            # Add assignment to patch document if assignee is determined
            if assignee:
                patch_document.append({
                    "op": "add",
                    "path": "/fields/System.AssignedTo",
                    "value": assignee
                })

            # Get authentication headers
            headers = get_auth_headers(content_type="application/json-patch+json")

            self.logger.debug(f"Creating work item via REST API: {url}")
            self.logger.debug(f"Patch document: {json.dumps(patch_document, indent=2)}")

            # Make the REST API call
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=patch_document, headers=headers) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            work_item_data = json.loads(response_text)
                            return {"success": True, "data": work_item_data}
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Failed to parse work item response: {e}")
                            return {
                                "success": False,
                                "error": f"Failed to parse response: {e}",
                                "raw_output": response_text
                            }
                    else:
                        self.logger.error(f"Work item creation failed with status {response.status}: {response_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {response_text}",
                            "raw_output": response_text
                        }

        except Exception as e:
            self.logger.error(f"Error creating work item: {e}")
            return {"success": False, "error": str(e)}

    async def update_work_item(
        self,
        work_item_id: Union[int, str],
        title: Optional[str] = None,
        description: Optional[str] = None,
        organization: Optional[str] = None,
        project: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing work item using Azure DevOps REST API.

        Args:
            work_item_id: ID of the work item to update
            title: New title of the work item (optional)
            description: New description of the work item (optional, supports markdown - will be automatically converted to HTML)
            organization: Azure DevOps organization URL (uses configured default if not provided)
            project: Azure DevOps project name/ID (uses configured default if not provided)

        Returns:
            Dictionary with success status and updated work item details
        """
        try:
            # Validate that at least one field is provided for update
            if title is None and description is None:
                return {"success": False, "error": "At least one of title or description must be provided for update operation"}

            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(project, self.default_project)

            if not org:
                return {"success": False, "error": "Organization is required"}
            if not proj:
                return {"success": False, "error": "Project is required"}

            # Construct the REST API URL for updating work item
            url = build_api_url(
                org,
                proj,
                f"wit/workitems/{work_item_id}?api-version=7.1",
            )

            # Build the JSON patch document for work item update
            patch_document = []

            # Add title update if provided
            if title is not None:
                patch_document.append({
                    "op": "replace",
                    "path": "/fields/System.Title",
                    "value": title
                })

            # Add description update if provided (convert markdown to HTML if needed)
            if description is not None:
                # Detect if description is markdown and convert to HTML
                html_description = detect_and_convert_markdown(description)
                patch_document.append({
                    "op": "replace",
                    "path": "/fields/System.Description",
                    "value": html_description
                })

            # Get authentication headers (use PATCH method)
            headers = get_auth_headers(content_type="application/json-patch+json")

            self.logger.debug(f"Updating work item via REST API: {url}")
            self.logger.debug(f"Patch document: {json.dumps(patch_document, indent=2)}")

            # Make the REST API call using PATCH method
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, json=patch_document, headers=headers) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            work_item_data = json.loads(response_text)
                            return {"success": True, "data": work_item_data}
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Failed to parse work item response: {e}")
                            return {
                                "success": False,
                                "error": f"Failed to parse response: {e}",
                                "raw_output": response_text
                            }
                    elif response.status == 404:
                        self.logger.error(f"Work item {work_item_id} not found")
                        return {
                            "success": False,
                            "error": f"Work item {work_item_id} not found",
                            "raw_output": response_text
                        }
                    else:
                        self.logger.error(f"Work item update failed with status {response.status}: {response_text}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {response_text}",
                            "raw_output": response_text
                        }

        except Exception as e:
            self.logger.error(f"Error updating work item: {e}")
            return {"success": False, "error": str(e)}

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
                assigned_to=arguments.get("assigned_to", "current"),
                auto_assign_to_current_user=arguments.get("auto_assign_to_current_user", True),
                organization=arguments.get("organization"),
                project=arguments.get("project"),
            )
        elif operation == "update":
            work_item_id = arguments.get("work_item_id")
            if work_item_id is None:
                return {"success": False, "error": "work_item_id is required for update operation"}

            title = arguments.get("title")
            description = arguments.get("description")
            if title is None and description is None:
                return {"success": False, "error": "At least one of title or description must be provided for update operation"}

            return await self.update_work_item(
                work_item_id=work_item_id,
                title=title,
                description=description,
                organization=arguments.get("organization"),
                project=arguments.get("project"),
            )
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
