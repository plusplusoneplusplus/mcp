"""Azure DevOps Work Item tool implementation."""

import logging
import json
import aiohttp
import base64
import subprocess
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
        self.bearer_token: Optional[str] = None

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

            self.logger.debug(
                f"Loaded Azure work item configuration: org={self.default_organization}, "
                f"project={self.default_project}, area_path={self.default_area_path}, "
                f"iteration={self.default_iteration_path}, bearer_token={'***' if self.bearer_token else None}"
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

    def _execute_bearer_token_command(self, command: str) -> Optional[str]:
        """Execute a command and extract the accessToken from JSON output.
        
        Args:
            command: The command to execute
            
        Returns:
            The access token if found, None otherwise
        """
        try:
            self.logger.debug(f"Executing bearer token command: {command}")
            
            # Execute the command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"Bearer token command failed with return code {result.returncode}: {result.stderr}")
                return None
                
            # Parse JSON output
            try:
                json_output = json.loads(result.stdout)
                access_token = json_output.get("accessToken")
                
                if access_token:
                    self.logger.debug("Successfully extracted access token from command output")
                    return access_token
                else:
                    self.logger.warning("No 'accessToken' property found in command output JSON")
                    return None
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse command output as JSON: {e}")
                self.logger.debug(f"Command output was: {result.stdout}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Bearer token command timed out after 30 seconds: {command}")
            return None
        except Exception as e:
            self.logger.error(f"Error executing bearer token command: {e}")
            return None

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for REST API calls.

        Returns:
            Dictionary with authorization headers
        """
        # Get Azure repo parameters from environment manager
        azrepo_params = env_manager.get_azrepo_parameters()
        bearer_token = None
        
        # Try bearer token command first (takes precedence over static token)
        bearer_token_command = azrepo_params.get("bearer_token_command")
        if bearer_token_command:
            bearer_token = self._execute_bearer_token_command(bearer_token_command)
        
        # If no token from command, fall back to static token
        if not bearer_token:
            bearer_token = azrepo_params.get("bearer_token")
        
        if not bearer_token:
            raise ValueError("Bearer token not configured. Please set AZREPO_BEARER_TOKEN or AZREPO_BEARER_TOKEN_COMMAND environment variable.")
        
        # For Azure DevOps REST API, use the bearer token directly
        return {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }

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
        """Create a new work item using Azure DevOps REST API.

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
            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(project, self.default_project)
            area = self._get_param_with_default(area_path, self.default_area_path)
            iteration = self._get_param_with_default(iteration_path, self.default_iteration_path)

            if not org:
                return {"success": False, "error": "Organization is required"}
            if not proj:
                return {"success": False, "error": "Project is required"}

            # Construct the REST API URL
            url = f"{org}/{proj}/_apis/wit/workitems/${work_item_type}?api-version=7.1"

            # Build the JSON patch document for work item creation
            patch_document = [
                {
                    "op": "add",
                    "path": "/fields/System.Title",
                    "value": title
                }
            ]

            # Add description if provided
            if description:
                patch_document.append({
                    "op": "add",
                    "path": "/fields/System.Description",
                    "value": description
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

            # Get authentication headers
            headers = self._get_auth_headers()

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
