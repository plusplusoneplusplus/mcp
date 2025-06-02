"""Azure DevOps Repository tool implementation."""

import logging
import json
import getpass
import os
from typing import Dict, Any, List, Optional, Union

# Import the required interfaces and decorators
from mcp_tools.interfaces import ToolInterface, RepoClientInterface
from mcp_tools.plugin import register_tool

# Import configuration manager
from config import env_manager

# Import types from the plugin
try:
    from .types import (
        PullRequestIdentity,
        PullRequestWorkItem,
        PullRequestRef,
        PullRequest,
        PullRequestListResponse,
        PullRequestDetailResponse,
        PullRequestCreateResponse,
        PullRequestUpdateResponse,
        PullRequestVoteEnum,
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
    PullRequestIdentity = types_module.PullRequestIdentity
    PullRequestWorkItem = types_module.PullRequestWorkItem
    PullRequestRef = types_module.PullRequestRef
    PullRequest = types_module.PullRequest
    PullRequestListResponse = types_module.PullRequestListResponse
    PullRequestDetailResponse = types_module.PullRequestDetailResponse
    PullRequestCreateResponse = types_module.PullRequestCreateResponse
    PullRequestUpdateResponse = types_module.PullRequestUpdateResponse
    PullRequestVoteEnum = types_module.PullRequestVoteEnum
    WorkItem = types_module.WorkItem
    WorkItemResponse = types_module.WorkItemResponse


@register_tool
class AzureRepoClient(RepoClientInterface):
    """Client for interacting with Azure DevOps Repositories using Azure CLI commands.

    This class provides methods to manage pull requests and other repo operations
    by executing az cli commands through the CommandExecutor. It automatically
    loads default configuration values from the environment while allowing
    parameter overrides for specific operations.

    Configuration:
        The client automatically loads default values from environment variables
        with the AZREPO_ prefix:
        - AZREPO_ORG: Default organization URL
        - AZREPO_PROJECT: Default project name/ID
        - AZREPO_REPO: Default repository name/ID
        - AZREPO_BRANCH: Default target branch

    Example:
        # Initialize the client with a command executor
        from mcp_tools.command_executor import CommandExecutor
        executor = CommandExecutor()
        az_client = AzureRepoClient(executor)

        # List pull requests (uses configured defaults)
        prs = await az_client.list_pull_requests()

        # List current user's pull requests (creator defaults to current user)
        my_prs = await az_client.list_pull_requests()

        # List all pull requests (explicitly set creator to None)
        all_prs = await az_client.list_pull_requests(creator=None)

        # Create a pull request with override parameters
        pr = await az_client.create_pull_request(
            title="My PR Title",
            source_branch="feature/my-feature",
            organization="different-org"  # Override default
        )

        # Get PR details
        pr_details = await az_client.get_pull_request(123)
    """

    # Implement ToolInterface properties
    @property
    def name(self) -> str:
        """Get the tool name."""
        return "azure_repo_client"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Interact with Azure DevOps repositories and pull requests with automatic configuration loading"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform (list_pull_requests, get_pull_request, create_pull_request, etc.)",
                    "enum": [
                        "list_pull_requests",
                        "get_pull_request",
                        "create_pull_request",
                        "update_pull_request",
                        "set_vote",
                        "add_reviewers",
                        "add_work_items",
                        "get_work_item",
                    ],
                },
                "pull_request_id": {
                    "type": ["string", "integer"],
                    "description": "ID of the pull request",
                    "nullable": True,
                },
                "work_item_id": {
                    "type": ["string", "integer"],
                    "description": "ID of the work item",
                    "nullable": True,
                },
                "title": {
                    "type": "string",
                    "description": "Title for the pull request",
                    "nullable": True,
                },
                "source_branch": {
                    "type": "string",
                    "description": "Name of the source branch",
                    "nullable": True,
                },
                "target_branch": {
                    "type": "string",
                    "description": "Name of the target branch",
                    "nullable": True,
                },
                "description": {
                    "type": "string",
                    "description": "Description for the pull request (can include markdown)",
                    "nullable": True,
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
                "vote": {
                    "type": "string",
                    "description": "Vote value (approve, approve-with-suggestions, reset, reject, wait-for-author)",
                    "nullable": True,
                },
                "reviewers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of reviewers to add (users or groups)",
                    "nullable": True,
                },
                "work_items": {
                    "type": "array",
                    "items": {"type": ["string", "integer"]},
                    "description": "List of work item IDs to link to the PR",
                    "nullable": True,
                },
                "status": {
                    "type": "string",
                    "description": "Status filter or new status for update operations",
                    "nullable": True,
                },
                "creator": {
                    "type": "string",
                    "description": "Filter PRs by creator (defaults to current user if not specified, use empty string to list all PRs)",
                    "nullable": True,
                },
                "reviewer": {
                    "type": "string",
                    "description": "Filter PRs by reviewer",
                    "nullable": True,
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of PRs to list",
                    "nullable": True,
                },
                "skip": {
                    "type": "integer",
                    "description": "Number of PRs to skip",
                    "nullable": True,
                },
                "draft": {
                    "type": "boolean",
                    "description": "Whether to create the PR in draft mode",
                    "nullable": True,
                },
                "auto_complete": {
                    "type": "boolean",
                    "description": "Set the PR to complete automatically when policies pass",
                    "nullable": True,
                },
                "squash": {
                    "type": "boolean",
                    "description": "Squash the commits when merging",
                    "nullable": True,
                },
                "delete_source_branch": {
                    "type": "boolean",
                    "description": "Delete the source branch after PR completion",
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
            self.default_organization = azrepo_params.get('org')
            self.default_project = azrepo_params.get('project')
            self.default_repository = azrepo_params.get('repo')
            self.default_target_branch = azrepo_params.get('branch')

            self.logger.debug(f"Loaded Azure repo configuration: org={self.default_organization}, "
                            f"project={self.default_project}, repo={self.default_repository}, "
                            f"branch={self.default_target_branch}")

        except Exception as e:
            self.logger.warning(f"Failed to load Azure repo configuration: {e}")
            # Set defaults to None if configuration loading fails
            self.default_organization = None
            self.default_project = None
            self.default_repository = None
            self.default_target_branch = None

    def _get_param_with_default(self, param_value: Optional[str], default_value: Optional[str]) -> Optional[str]:
        """Get parameter value with fallback to default configuration.

        Args:
            param_value: Explicitly provided parameter value
            default_value: Default value from configuration

        Returns:
            The parameter value to use (explicit value takes precedence)
        """
        return param_value if param_value is not None else default_value

    def _get_current_username(self) -> Optional[str]:
        """Get the current username in a cross-platform way.

        Returns:
            The current username, or None if unable to determine

        Note:
            This method returns None instead of raising an exception to allow
            graceful fallback when username cannot be determined.
        """
        try:
            # Try getpass.getuser() first (works on most platforms)
            return getpass.getuser()
        except Exception:
            try:
                # Fallback to environment variables
                username = os.environ.get('USER') or os.environ.get('USERNAME')
                if username:
                    return username
            except Exception:
                pass

            # Return None if unable to determine username
            self.logger.warning("Unable to determine current username")
            return None

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

    async def list_pull_requests(
        self,
        repository: Optional[str] = None,
        project: Optional[str] = None,
        organization: Optional[str] = None,
        creator: Optional[str] = "default",
        reviewer: Optional[str] = None,
        status: Optional[str] = None,
        source_branch: Optional[str] = None,
        target_branch: Optional[str] = None,
        top: Optional[int] = None,
        skip: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List pull requests in the repository.

        Args:
            repository: Name or ID of the repository (uses configured default if not provided)
            project: Name or ID of the project (uses configured default if not provided)
            organization: Azure DevOps organization URL (uses configured default if not provided)
            creator: Limit results to PRs created by this user.
                    - If "default" (default value), uses current user
                    - If None or empty string, lists all PRs regardless of creator
                    - If a username, filters by that specific user
            reviewer: Limit results to PRs where this user is a reviewer
            status: Limit results to PRs with this status (abandoned, active, all, completed)
            source_branch: Limit results to PRs that originate from this branch
            target_branch: Limit results to PRs that target this branch
            top: Maximum number of PRs to list
            skip: Number of PRs to skip

        Returns:
            Dictionary with success status and list of pull requests
        """
        command = "repos pr list"

        # Use configured defaults for core parameters
        repo = self._get_param_with_default(repository, self.default_repository)
        proj = self._get_param_with_default(project, self.default_project)
        org = self._get_param_with_default(organization, self.default_organization)

        # Handle creator parameter with default behavior
        if creator == "default":
            # Use current user as default
            creator = self._get_current_username()
            if creator:
                self.logger.debug(f"Using current user as creator filter: {creator}")

        # Add optional parameters
        if repo:
            command += f" --repository {repo}"
        if proj:
            command += f" --project {proj}"
        if org:
            command += f" --org {org}"
        if creator:
            command += f" --creator {creator}"
        if reviewer:
            command += f" --reviewer {reviewer}"
        if status:
            command += f" --status {status}"
        if source_branch:
            command += f" --source-branch {source_branch}"
        if target_branch:
            command += f" --target-branch {target_branch}"
        if top:
            command += f" --top {top}"
        if skip:
            command += f" --skip {skip}"

        return await self._run_az_command(command)

    async def get_pull_request(
        self, pull_request_id: Union[int, str], organization: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get details of a specific pull request.

        Args:
            pull_request_id: ID of the pull request
            organization: Azure DevOps organization URL (uses configured default if not provided)

        Returns:
            Dictionary with success status and pull request details
        """
        command = f"repos pr show --id {pull_request_id}"

        # Use configured default for organization
        org = self._get_param_with_default(organization, self.default_organization)
        if org:
            command += f" --org {org}"

        return await self._run_az_command(command)

    async def create_pull_request(
        self,
        title: str,
        source_branch: str,
        target_branch: Optional[str] = None,
        description: Optional[str] = None,
        repository: Optional[str] = None,
        project: Optional[str] = None,
        organization: Optional[str] = None,
        reviewers: Optional[List[str]] = None,
        work_items: Optional[List[Union[int, str]]] = None,
        draft: bool = False,
        auto_complete: bool = False,
        squash: bool = False,
        delete_source_branch: bool = False,
    ) -> Dict[str, Any]:
        """Create a new pull request.

        Args:
            title: Title for the pull request
            source_branch: Name of the source branch
            target_branch: Name of the target branch (uses configured default if not specified)
            description: Description for the pull request (can include markdown)
            repository: Name or ID of the repository (uses configured default if not provided)
            project: Name or ID of the project (uses configured default if not provided)
            organization: Azure DevOps organization URL (uses configured default if not provided)
            reviewers: List of reviewers to add (users or groups)
            work_items: List of work item IDs to link to the PR
            draft: Whether to create the PR in draft mode
            auto_complete: Set the PR to complete automatically when policies pass
            squash: Squash the commits when merging
            delete_source_branch: Delete the source branch after PR completion

        Returns:
            Dictionary with success status and created pull request details
        """
        command = "repos pr create"

        # Required parameters
        command += f' --title "{title}"'
        command += f" --source-branch {source_branch}"

        # Use configured defaults for core parameters
        target_br = self._get_param_with_default(target_branch, self.default_target_branch)
        repo = self._get_param_with_default(repository, self.default_repository)
        proj = self._get_param_with_default(project, self.default_project)
        org = self._get_param_with_default(organization, self.default_organization)

        # Add optional parameters
        if target_br:
            command += f" --target-branch {target_br}"
        if description:
            # Escape quotes in description and wrap each line
            desc_lines = description.replace('"', '\\"').split("\n")
            for line in desc_lines:
                command += f' --description "{line}"'
        if repo:
            command += f" --repository {repo}"
        if proj:
            command += f" --project {proj}"
        if org:
            command += f" --org {org}"

        # Add reviewers if provided
        if reviewers:
            for reviewer in reviewers:
                command += f" --reviewers {reviewer}"

        # Add work items if provided
        if work_items:
            for item in work_items:
                command += f" --work-items {item}"

        # Add flags
        if draft:
            command += " --draft"
        if auto_complete:
            command += " --auto-complete"
        if squash:
            command += " --squash"
        if delete_source_branch:
            command += " --delete-source-branch"

        return await self._run_az_command(command)

    async def update_pull_request(
        self,
        pull_request_id: Union[int, str],
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        organization: Optional[str] = None,
        auto_complete: Optional[bool] = None,
        squash: Optional[bool] = None,
        delete_source_branch: Optional[bool] = None,
        draft: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update an existing pull request.

        Args:
            pull_request_id: ID of the pull request to update
            title: New title for the pull request
            description: New description for the pull request
            status: New status (active, abandoned, completed)
            organization: Azure DevOps organization URL (uses configured default if not provided)
            auto_complete: Set the PR to complete automatically when policies pass
            squash: Squash the commits when merging
            delete_source_branch: Delete the source branch after PR completion
            draft: Whether the PR should be in draft mode

        Returns:
            Dictionary with success status and updated pull request details
        """
        command = f"repos pr update --id {pull_request_id}"

        # Use configured default for organization
        org = self._get_param_with_default(organization, self.default_organization)

        # Add optional parameters
        if title:
            command += f' --title "{title}"'
        if description:
            # Escape quotes in description and wrap each line
            desc_lines = description.replace('"', '\\"').split("\n")
            for line in desc_lines:
                command += f' --description "{line}"'
        if status:
            command += f" --status {status}"
        if org:
            command += f" --org {org}"

        # Add flags
        if auto_complete is not None:
            command += f" --auto-complete {'true' if auto_complete else 'false'}"
        if squash is not None:
            command += f" --squash {'true' if squash else 'false'}"
        if delete_source_branch is not None:
            command += (
                f" --delete-source-branch {'true' if delete_source_branch else 'false'}"
            )
        if draft is not None:
            command += f" --draft {'true' if draft else 'false'}"

        return await self._run_az_command(command)

    async def set_vote(
        self,
        pull_request_id: Union[int, str],
        vote: str,
        organization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set your vote on a pull request.

        Args:
            pull_request_id: ID of the pull request
            vote: Vote value (approve, approve-with-suggestions, reset, reject, wait-for-author)
            organization: Azure DevOps organization URL (uses configured default if not provided)

        Returns:
            Dictionary with success status and result details
        """
        command = f"repos pr set-vote --id {pull_request_id} --vote {vote}"

        # Use configured default for organization
        org = self._get_param_with_default(organization, self.default_organization)
        if org:
            command += f" --org {org}"

        return await self._run_az_command(command)

    async def add_reviewers(
        self,
        pull_request_id: Union[int, str],
        reviewers: List[str],
        organization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add reviewers to a pull request.

        Args:
            pull_request_id: ID of the pull request
            reviewers: List of reviewers to add (users or groups)
            organization: Azure DevOps organization URL (uses configured default if not provided)

        Returns:
            Dictionary with success status and result details
        """
        command = f"repos pr reviewer add --id {pull_request_id}"

        # Add reviewers
        for reviewer in reviewers:
            command += f" --reviewers {reviewer}"

        # Use configured default for organization
        org = self._get_param_with_default(organization, self.default_organization)
        if org:
            command += f" --org {org}"

        return await self._run_az_command(command)

    async def add_work_items(
        self,
        pull_request_id: Union[int, str],
        work_items: List[Union[int, str]],
        organization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add work items to a pull request.

        Args:
            pull_request_id: ID of the pull request
            work_items: List of work item IDs to add
            organization: Azure DevOps organization URL (uses configured default if not provided)

        Returns:
            Dictionary with success status and result details
        """
        command = f"repos pr work-item add --id {pull_request_id}"

        # Add work items
        for item in work_items:
            command += f" --work-items {item}"

        # Use configured default for organization
        org = self._get_param_with_default(organization, self.default_organization)
        if org:
            command += f" --org {org}"

        return await self._run_az_command(command)

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
            project: Name or ID of the project (uses configured default if not provided)
            as_of: Work item details as of a particular date and time
            expand: The expand parameters for work item attributes (all, fields, links, none, relations)
            fields: Comma-separated list of requested fields

        Returns:
            Dictionary with success status and work item details
        """
        command = f"boards work-item show --id {work_item_id}"

        # Use configured defaults for core parameters
        org = self._get_param_with_default(organization, self.default_organization)
        proj = self._get_param_with_default(project, self.default_project)

        # Add optional parameters
        if org:
            command += f" --org {org}"
        if proj:
            command += f" --project {proj}"
        if as_of:
            command += f" --as-of '{as_of}'"
        if expand:
            command += f" --expand {expand}"
        if fields:
            command += f" --fields {fields}"

        return await self._run_az_command(command)

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments.

        Args:
            arguments: Dictionary of arguments for the tool

        Returns:
            Tool execution result
        """
        operation = arguments.get("operation", "")

        if operation == "list_pull_requests":
            return await self.list_pull_requests(
                repository=arguments.get("repository"),
                project=arguments.get("project"),
                organization=arguments.get("organization"),
                creator=arguments.get("creator", "default"),  # Use "default" if not specified
                reviewer=arguments.get("reviewer"),
                status=arguments.get("status"),
                source_branch=arguments.get("source_branch"),
                target_branch=arguments.get("target_branch"),
                top=arguments.get("top"),
                skip=arguments.get("skip"),
            )
        elif operation == "get_pull_request":
            return await self.get_pull_request(
                pull_request_id=arguments.get("pull_request_id"),
                organization=arguments.get("organization"),
            )
        elif operation == "create_pull_request":
            return await self.create_pull_request(
                title=arguments.get("title"),
                source_branch=arguments.get("source_branch"),
                target_branch=arguments.get("target_branch"),
                description=arguments.get("description"),
                repository=arguments.get("repository"),
                project=arguments.get("project"),
                organization=arguments.get("organization"),
                reviewers=arguments.get("reviewers"),
                work_items=arguments.get("work_items"),
                draft=arguments.get("draft", False),
                auto_complete=arguments.get("auto_complete", False),
                squash=arguments.get("squash", False),
                delete_source_branch=arguments.get("delete_source_branch", False),
            )
        elif operation == "update_pull_request":
            return await self.update_pull_request(
                pull_request_id=arguments.get("pull_request_id"),
                title=arguments.get("title"),
                description=arguments.get("description"),
                status=arguments.get("status"),
                organization=arguments.get("organization"),
                auto_complete=arguments.get("auto_complete"),
                squash=arguments.get("squash"),
                delete_source_branch=arguments.get("delete_source_branch"),
                draft=arguments.get("draft"),
            )
        elif operation == "set_vote":
            return await self.set_vote(
                pull_request_id=arguments.get("pull_request_id"),
                vote=arguments.get("vote"),
                organization=arguments.get("organization"),
            )
        elif operation == "add_reviewers":
            return await self.add_reviewers(
                pull_request_id=arguments.get("pull_request_id"),
                reviewers=arguments.get("reviewers", []),
                organization=arguments.get("organization"),
            )
        elif operation == "add_work_items":
            return await self.add_work_items(
                pull_request_id=arguments.get("pull_request_id"),
                work_items=arguments.get("work_items", []),
                organization=arguments.get("organization"),
            )
        elif operation == "get_work_item":
            return await self.get_work_item(
                work_item_id=arguments.get("work_item_id"),
                organization=arguments.get("organization"),
                project=arguments.get("project"),
                as_of=arguments.get("as_of"),
                expand=arguments.get("expand"),
                fields=arguments.get("fields"),
            )
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
