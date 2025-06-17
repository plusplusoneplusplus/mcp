"""Azure DevOps Repository tool implementation."""

import logging
import json
from typing import Dict, Any, List, Optional, Union

# Import the required interfaces and decorators
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

# Import configuration manager
from config import env_manager


@register_tool(ecosystem="microsoft", os_type="all")
class AzureRepoClient(ToolInterface):
    """Client for interacting with Azure DevOps Repositories using Azure CLI commands.

    This class provides methods for repository-level operations by executing
    az cli commands through the CommandExecutor. It automatically loads default
    configuration values from the environment while allowing parameter overrides
    for specific operations.

    Note: Pull request and work item functionality has been moved to dedicated tools:
    - AzurePullRequestTool for PR operations
    - AzureWorkItemTool for work item operations

    Configuration:
        The client automatically loads default values from environment variables
        with the AZREPO_ prefix:
        - AZREPO_ORG: Default organization URL
        - AZREPO_PROJECT: Default project name/ID
        - AZREPO_REPO: Default repository name/ID

    Example:
        # Initialize the client with a command executor
        from mcp_tools.command_executor import CommandExecutor
        executor = CommandExecutor()
        az_client = AzureRepoClient(executor)

        # Repository operations would go here
        # (Currently focused on PR/WI operations which are now in separate tools)
    """

    # Implement ToolInterface properties
    @property
    def name(self) -> str:
        """Get the tool name."""
        return "azure_repo_client"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Interact with Azure DevOps repositories with automatic configuration loading"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The repository operation to perform",
                    "enum": [
                        "list_repos",
                        "get_repo",
                        "clone_repo",
                    ],
                },
                "repository": {
                    "type": "string",
                    "description": "Name or ID of the repository",
                    "nullable": True,
                },
                "project": {
                    "type": "string",
                    "description": "Name or ID of the project",
                    "nullable": True,
                },
                "organization": {
                    "type": "string",
                    "description": "Azure DevOps organization URL",
                    "nullable": True,
                },
                "clone_url": {
                    "type": "string",
                    "description": "URL to clone the repository",
                    "nullable": True,
                },
                "local_path": {
                    "type": "string",
                    "description": "Local path where to clone the repository",
                    "nullable": True,
                },
            },
            "required": ["operation"],
        }

    def __init__(self, command_executor=None):
        """Initialize the AzureRepoClient with a command executor and load configuration.

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
            self.default_organization = azrepo_params.get("org")
            self.default_project = azrepo_params.get("project")
            self.default_repository = azrepo_params.get("repo")

            self.logger.debug(
                f"Loaded Azure repo configuration: org={self.default_organization}, "
                f"project={self.default_project}, repo={self.default_repository}"
            )

        except Exception as e:
            self.logger.warning(f"Failed to load Azure repo configuration: {e}")
            # Set defaults to None if configuration loading fails
            self.default_organization = None
            self.default_project = None
            self.default_repository = None

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

    async def list_repositories(
        self,
        project: Optional[str] = None,
        organization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List repositories in the project.

        Args:
            project: Name or ID of the project (uses configured default if not provided)
            organization: Azure DevOps organization URL (uses configured default if not provided)

        Returns:
            Dictionary with success status and list of repositories
        """
        command = "repos list"

        # Use configured defaults for core parameters
        proj = self._get_param_with_default(project, self.default_project)
        org = self._get_param_with_default(organization, self.default_organization)

        # Add optional parameters
        if proj:
            command += f" --project {proj}"
        if org:
            command += f" --org {org}"

        return await self._run_az_command(command)

    async def get_repository(
        self,
        repository: Optional[str] = None,
        project: Optional[str] = None,
        organization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get details of a specific repository.

        Args:
            repository: Name or ID of the repository (uses configured default if not provided)
            project: Name or ID of the project (uses configured default if not provided)
            organization: Azure DevOps organization URL (uses configured default if not provided)

        Returns:
            Dictionary with success status and repository details
        """
        command = "repos show"

        # Use configured defaults for core parameters
        repo = self._get_param_with_default(repository, self.default_repository)
        proj = self._get_param_with_default(project, self.default_project)
        org = self._get_param_with_default(organization, self.default_organization)

        # Add optional parameters
        if repo:
            command += f" --repository {repo}"
        if proj:
            command += f" --project {proj}"
        if org:
            command += f" --org {org}"

        return await self._run_az_command(command)

    async def clone_repository(
        self,
        clone_url: Optional[str] = None,
        local_path: Optional[str] = None,
        repository: Optional[str] = None,
        project: Optional[str] = None,
        organization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Clone a repository to a local path.

        Args:
            clone_url: URL to clone the repository (if not provided, will be constructed from other params)
            local_path: Local path where to clone the repository
            repository: Name or ID of the repository (uses configured default if not provided)
            project: Name or ID of the project (uses configured default if not provided)
            organization: Azure DevOps organization URL (uses configured default if not provided)

        Returns:
            Dictionary with success status and clone details
        """
        if clone_url:
            # Use provided clone URL directly
            command = f"git clone {clone_url}"
            if local_path:
                command += f" {local_path}"
        else:
            # Construct clone URL from Azure DevOps parameters
            repo = self._get_param_with_default(repository, self.default_repository)
            proj = self._get_param_with_default(project, self.default_project)
            org = self._get_param_with_default(organization, self.default_organization)

            if not all([repo, proj, org]):
                return {
                    "success": False,
                    "error": "Repository, project, and organization must be specified for Azure DevOps clone",
                }

            # Construct Azure DevOps clone URL
            clone_url = f"{org}/{proj}/_git/{repo}"
            command = f"git clone {clone_url}"
            if local_path:
                command += f" {local_path}"

        # Execute git clone command directly (not through az cli)
        result = await self.executor.execute_async(command)
        token = result.get("token")

        status = await self.executor.query_process(token, wait=True)

        if status.get("success", False):
            return {
                "success": True,
                "message": f"Repository cloned successfully to {local_path or 'current directory'}",
            }
        else:
            return {"success": False, "error": status.get("error", "Clone failed")}

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments.

        Args:
            arguments: Dictionary of arguments for the tool

        Returns:
            Tool execution result
        """
        operation = arguments.get("operation", "")

        if operation == "list_repos":
            return await self.list_repositories(
                project=arguments.get("project"),
                organization=arguments.get("organization"),
            )
        elif operation == "get_repo":
            return await self.get_repository(
                repository=arguments.get("repository"),
                project=arguments.get("project"),
                organization=arguments.get("organization"),
            )
        elif operation == "clone_repo":
            return await self.clone_repository(
                clone_url=arguments.get("clone_url"),
                local_path=arguments.get("local_path"),
                repository=arguments.get("repository"),
                project=arguments.get("project"),
                organization=arguments.get("organization"),
            )
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
