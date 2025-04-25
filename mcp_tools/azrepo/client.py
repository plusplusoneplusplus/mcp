import logging
import json
from typing import Dict, Any, List, Optional, Union

# Import interface
from mcp_tools.interfaces import RepoClientInterface

# Now we'll accept the CommandExecutor as a dependency rather than importing it directly
class AzureRepoClient(RepoClientInterface):
    """Client for interacting with Azure DevOps Repositories using Azure CLI commands.

    This class provides methods to manage pull requests and other repo operations
    by executing az cli commands through the CommandExecutor.

    Example:
        # Initialize the client with a command executor
        from mcp_tools.command_executor import CommandExecutor
        executor = CommandExecutor()
        az_client = AzureRepoClient(executor)

        # List pull requests
        prs = await az_client.list_pull_requests()

        # Create a pull request
        pr = await az_client.create_pull_request(
            title="My PR Title",
            source_branch="feature/my-feature",
            target_branch="main"
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
        return "Interact with Azure DevOps repositories and pull requests"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform (list_pull_requests, get_pull_request, create_pull_request, etc.)",
                    "enum": ["list_pull_requests", "get_pull_request", "create_pull_request", "update_pull_request"]
                },
                "pull_request_id": {
                    "type": ["string", "integer"],
                    "description": "ID of the pull request",
                    "nullable": True
                },
                "title": {
                    "type": "string",
                    "description": "Title for the pull request",
                    "nullable": True
                },
                "source_branch": {
                    "type": "string",
                    "description": "Name of the source branch",
                    "nullable": True
                },
                "target_branch": {
                    "type": "string",
                    "description": "Name of the target branch",
                    "nullable": True
                },
                "repository": {
                    "type": "string",
                    "description": "Name or ID of the repository",
                    "nullable": True
                },
                "project": {
                    "type": "string",
                    "description": "Name or ID of the project",
                    "nullable": True
                },
                "organization": {
                    "type": "string",
                    "description": "Azure DevOps organization URL",
                    "nullable": True
                }
            },
            "required": ["operation"]
        }

    def __init__(self, command_executor):
        """Initialize the AzureRepoClient with a command executor.
        
        Args:
            command_executor: An instance of CommandExecutor to use for running commands
        """
        self.executor = command_executor
        self.logger = logging.getLogger(__name__)

    async def _run_az_command(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
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
                "raw_output": status.get("output", "")
            }

    async def list_pull_requests(
        self,
        repository: Optional[str] = None,
        project: Optional[str] = None,
        organization: Optional[str] = None,
        creator: Optional[str] = None,
        reviewer: Optional[str] = None,
        status: Optional[str] = None,
        source_branch: Optional[str] = None,
        target_branch: Optional[str] = None,
        top: Optional[int] = None,
        skip: Optional[int] = None
    ) -> Dict[str, Any]:
        """List pull requests in the repository.

        Args:
            repository: Name or ID of the repository
            project: Name or ID of the project
            organization: Azure DevOps organization URL
            creator: Limit results to PRs created by this user
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

        # Add optional parameters
        if repository:
            command += f" --repository {repository}"
        if project:
            command += f" --project {project}"
        if organization:
            command += f" --org {organization}"
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
        self,
        pull_request_id: Union[int, str],
        organization: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get details of a specific pull request.

        Args:
            pull_request_id: ID of the pull request
            organization: Azure DevOps organization URL

        Returns:
            Dictionary with success status and pull request details
        """
        command = f"repos pr show --id {pull_request_id}"

        if organization:
            command += f" --org {organization}"

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
        delete_source_branch: bool = False
    ) -> Dict[str, Any]:
        """Create a new pull request.

        Args:
            title: Title for the pull request
            source_branch: Name of the source branch
            target_branch: Name of the target branch (defaults to default branch if not specified)
            description: Description for the pull request (can include markdown)
            repository: Name or ID of the repository
            project: Name or ID of the project
            organization: Azure DevOps organization URL
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
        command += f" --title \"{title}\""
        command += f" --source-branch {source_branch}"

        # Add optional parameters
        if target_branch:
            command += f" --target-branch {target_branch}"
        if description:
            # Escape quotes in description and wrap each line
            desc_lines = description.replace('"', '\\"').split('\n')
            for line in desc_lines:
                command += f" --description \"{line}\""
        if repository:
            command += f" --repository {repository}"
        if project:
            command += f" --project {project}"
        if organization:
            command += f" --org {organization}"

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
        draft: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update an existing pull request.

        Args:
            pull_request_id: ID of the pull request to update
            title: New title for the pull request
            description: New description for the pull request
            status: New status (active, abandoned, completed)
            organization: Azure DevOps organization URL
            auto_complete: Set the PR to complete automatically when policies pass
            squash: Squash the commits when merging
            delete_source_branch: Delete the source branch after PR completion
            draft: Whether the PR should be in draft mode

        Returns:
            Dictionary with success status and updated pull request details
        """
        command = f"repos pr update --id {pull_request_id}"

        # Add optional parameters
        if title:
            command += f" --title \"{title}\""
        if description:
            # Escape quotes in description and wrap each line
            desc_lines = description.replace('"', '\\"').split('\n')
            for line in desc_lines:
                command += f" --description \"{line}\""
        if status:
            command += f" --status {status}"
        if organization:
            command += f" --org {organization}"

        # Add flags
        if auto_complete is not None:
            command += f" --auto-complete {'true' if auto_complete else 'false'}"
        if squash is not None:
            command += f" --squash {'true' if squash else 'false'}"
        if delete_source_branch is not None:
            command += f" --delete-source-branch {'true' if delete_source_branch else 'false'}"
        if draft is not None:
            command += f" --draft {'true' if draft else 'false'}"

        return await self._run_az_command(command)

    async def set_vote(
        self,
        pull_request_id: Union[int, str],
        vote: str,
        organization: Optional[str] = None
    ) -> Dict[str, Any]:
        """Set your vote on a pull request.

        Args:
            pull_request_id: ID of the pull request
            vote: Vote value (approve, approve-with-suggestions, reset, reject, wait-for-author)
            organization: Azure DevOps organization URL

        Returns:
            Dictionary with success status and result details
        """
        command = f"repos pr set-vote --id {pull_request_id} --vote {vote}"

        if organization:
            command += f" --org {organization}"

        return await self._run_az_command(command)

    async def add_reviewers(
        self,
        pull_request_id: Union[int, str],
        reviewers: List[str],
        organization: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add reviewers to a pull request.

        Args:
            pull_request_id: ID of the pull request
            reviewers: List of reviewers to add (users or groups)
            organization: Azure DevOps organization URL

        Returns:
            Dictionary with success status and result details
        """
        command = f"repos pr reviewer add --id {pull_request_id}"

        # Add reviewers
        for reviewer in reviewers:
            command += f" --reviewers {reviewer}"

        if organization:
            command += f" --org {organization}"

        return await self._run_az_command(command)

    async def add_work_items(
        self,
        pull_request_id: Union[int, str],
        work_items: List[Union[int, str]],
        organization: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add work items to a pull request.

        Args:
            pull_request_id: ID of the pull request
            work_items: List of work item IDs to add
            organization: Azure DevOps organization URL

        Returns:
            Dictionary with success status and result details
        """
        command = f"repos pr work-item add --id {pull_request_id}"

        # Add work items
        for item in work_items:
            command += f" --work-items {item}"

        if organization:
            command += f" --org {organization}"

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
                creator=arguments.get("creator"),
                reviewer=arguments.get("reviewer"),
                status=arguments.get("status"),
                source_branch=arguments.get("source_branch"),
                target_branch=arguments.get("target_branch")
            )
        elif operation == "get_pull_request":
            return await self.get_pull_request(
                pull_request_id=arguments.get("pull_request_id"),
                organization=arguments.get("organization")
            )
        elif operation == "create_pull_request":
            return await self.create_pull_request(
                title=arguments.get("title"),
                source_branch=arguments.get("source_branch"),
                target_branch=arguments.get("target_branch"),
                description=arguments.get("description"),
                repository=arguments.get("repository"),
                project=arguments.get("project"),
                organization=arguments.get("organization")
            )
        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}"
            } 