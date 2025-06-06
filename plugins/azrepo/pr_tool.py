"""Azure DevOps Pull Request tool implementation."""

import logging
import json
import getpass
import os
import pandas as pd
import uuid
from typing import Dict, Any, List, Optional, Union

import git

# Import the required interfaces and decorators
from mcp_tools.interfaces import ToolInterface
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


@register_tool
class AzurePullRequestTool(ToolInterface):
    """Dedicated tool for managing Azure DevOps Pull Requests.

    This tool provides comprehensive pull request management capabilities
    including creating, updating, listing, and voting on pull requests.
    It automatically loads default configuration values from the environment
    while allowing parameter overrides for specific operations.

    Configuration:
        The tool automatically loads default values from environment variables
        with the AZREPO_ prefix:
        - AZREPO_ORG: Default organization URL
        - AZREPO_PROJECT: Default project name/ID
        - AZREPO_REPO: Default repository name/ID
        - AZREPO_BRANCH: Default target branch
        - AZREPO_PR_BRANCH_PREFIX: Default prefix for auto-generated PR branch names

    Example:
        # List pull requests (uses configured defaults)
        prs = await pr_tool.execute_tool({"operation": "list"})

        # Create a pull request with auto-generated branch and title
        pr = await pr_tool.execute_tool({
            "operation": "create",
            "title": "My Feature",
            "description": "Feature description"
        })

        # Get PR details
        pr_details = await pr_tool.execute_tool({
            "operation": "get",
            "pull_request_id": 123
        })
    """

    # Implement ToolInterface properties
    @property
    def name(self) -> str:
        """Get the tool name."""
        return "azure_pull_request"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Manage Azure DevOps pull requests with comprehensive functionality"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The pull request operation to perform",
                    "enum": [
                        "list",
                        "get",
                        "create",
                        "update",
                        "vote",
                        "add_work_items",
                    ],
                },
                "pull_request_id": {
                    "type": ["string", "integer"],
                    "description": "ID of the pull request",
                    "nullable": True,
                },
                "title": {
                    "type": "string",
                    "description": "Title for the pull request (if None and source_branch is None, uses last commit message)",
                    "nullable": True,
                },
                "source_branch": {
                    "type": "string",
                    "description": "Name of the source branch (if None, creates a branch from current HEAD using commit ID)",
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
                "reviewers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of reviewers to add (users or groups)",
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
            },
            "required": ["operation"],
        }

    def __init__(self, command_executor=None):
        """Initialize the AzurePullRequestTool with a command executor and load configuration.

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
            self.default_target_branch = azrepo_params.get("branch")
            # Get default prefix with username
            default_prefix = self._get_default_pr_branch_prefix()
            self.default_pr_branch_prefix = azrepo_params.get(
                "pr_branch_prefix", default_prefix
            )

            self.logger.debug(
                f"Loaded Azure repo configuration: org={self.default_organization}, "
                f"project={self.default_project}, repo={self.default_repository}, "
                f"branch={self.default_target_branch}, pr_branch_prefix={self.default_pr_branch_prefix}"
            )

        except Exception as e:
            self.logger.warning(f"Failed to load Azure repo configuration: {e}")
            # Set defaults to None if configuration loading fails
            self.default_organization = None
            self.default_project = None
            self.default_repository = None
            self.default_target_branch = None
            self.default_pr_branch_prefix = self._get_default_pr_branch_prefix()

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

    def _get_current_username(self) -> Optional[str]:
        """Get the current username in a cross-platform way.

        Returns:
            The current username, or None if unable to determine
        """
        try:
            # Try getpass.getuser() first (works on most platforms)
            return getpass.getuser()
        except Exception:
            try:
                # Fallback to environment variables
                username = os.environ.get("USER") or os.environ.get("USERNAME")
                if username:
                    return username
            except Exception:
                pass

            # Return None if unable to determine username
            self.logger.warning("Unable to determine current username")
            return None

    def _get_default_pr_branch_prefix(self) -> str:
        """Get the default PR branch prefix including username.

        Returns:
            Default prefix in format 'auto-pr/<username>/' or 'auto-pr' if username unavailable
        """
        username = self._get_current_username()
        if username:
            return f"auto-pr/{username}/"
        else:
            return "auto-pr"

    def _get_last_commit_message(self) -> Optional[str]:
        """Get the first line of the last commit message using GitPython.

        Returns:
            The first line of the last commit message, or None if unable to determine
        """
        try:
            # Use GitPython to get the last commit message
            repo = git.Repo(search_parent_directories=True)

            # Get the latest commit
            latest_commit = repo.head.commit

            # Get the first line of the commit message
            commit_message = latest_commit.message.strip()
            if commit_message:
                # Return only the first line (subject)
                first_line = commit_message.split("\n")[0].strip()
                if first_line:
                    return first_line

            self.logger.warning("Unable to get last commit message")
            return None

        except git.exc.InvalidGitRepositoryError:
            self.logger.warning("Not in a git repository")
            return None
        except Exception as e:
            self.logger.warning(
                f"Failed to get last commit message with GitPython: {e}"
            )
            return None

    def _generate_branch_name_from_commit(self) -> str:
        """Generate a branch name using the last commit ID and configurable prefix.

        Returns:
            A branch name in the format '{prefix}{commit_id}' where prefix
            is configurable via AZREPO_PR_BRANCH_PREFIX environment variable
            and commit_id is the first 12 characters of the last commit hash
        """
        try:
            # Use GitPython to get the last commit ID
            repo = git.Repo(search_parent_directories=True)
            latest_commit = repo.head.commit
            commit_id = str(latest_commit.hexsha)[
                :12
            ]  # Use first 12 characters of commit hash

            prefix = (
                self.default_pr_branch_prefix or self._get_default_pr_branch_prefix()
            )
            if prefix.endswith("/"):
                return f"{prefix}{commit_id}"
            else:
                return f"{prefix}/{commit_id}"

        except git.exc.InvalidGitRepositoryError:
            self.logger.warning("Not in a git repository, falling back to UUID")
            # Fallback to UUID if not in a git repository
            random_id = str(uuid.uuid4())[:8]
            prefix = (
                self.default_pr_branch_prefix or self._get_default_pr_branch_prefix()
            )
            return f"{prefix}{random_id}"
        except Exception as e:
            self.logger.warning(f"Failed to get commit ID: {e}, falling back to UUID")
            # Fallback to UUID if commit ID retrieval fails
            random_id = str(uuid.uuid4())[:8]
            prefix = (
                self.default_pr_branch_prefix or self._get_default_pr_branch_prefix()
            )
            return f"{prefix}{random_id}"

    def _create_and_push_branch(self, branch_name: str) -> Dict[str, Any]:
        """Create a new branch from current HEAD and push it to remote using GitPython.

        Args:
            branch_name: Name of the branch to create

        Returns:
            Dictionary with success status and any error information
        """
        try:
            # Use GitPython to create and push the branch
            repo = git.Repo(search_parent_directories=True)

            # Create the new branch from current HEAD
            new_branch = repo.create_head(branch_name)

            # Checkout the new branch
            new_branch.checkout()

            # Push the branch to remote origin
            origin = repo.remote("origin")
            origin.push(new_branch, set_upstream=True)

            self.logger.info(f"Successfully created and pushed branch: {branch_name}")
            return {"success": True, "branch_name": branch_name}

        except git.exc.InvalidGitRepositoryError:
            return {"success": False, "error": "Not in a git repository"}
        except git.exc.GitCommandError as e:
            return {"success": False, "error": f"Git command failed: {str(e)}"}
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create/push branch with GitPython: {str(e)}",
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

    def convert_pr_to_df(self, prs_in_json):
        """Convert pull request JSON data to a pandas DataFrame."""
        l = []
        for o in prs_in_json:
            l.append(
                {
                    "id": o["pullRequestId"],
                    "creator": o["createdBy"]["uniqueName"],
                    "date": pd.to_datetime(o["creationDate"]).strftime(
                        "%m/%d/%y %H:%M:%S"
                    ),
                    "title": o["title"],
                    "source_ref": o["sourceRefName"].replace("refs/heads/", ""),
                    "target_ref": o["targetRefName"].replace("refs/heads/", ""),
                }
            )

        # Create DataFrame with proper columns even if empty
        if not l:
            return pd.DataFrame(
                columns=["id", "creator", "date", "title", "source_ref", "target_ref"]
            )

        return pd.DataFrame().from_dict(l)

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
        """List pull requests in the repository."""
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

        result = await self._run_az_command(command)

        # If successful, convert to DataFrame and return as CSV
        if result.get("success", False) and "data" in result:
            try:
                df = self.convert_pr_to_df(result["data"])
                csv_data = df.to_csv(index=False)
                return {"success": True, "data": csv_data}
            except Exception as e:
                self.logger.warning(f"Failed to convert PRs to DataFrame: {e}")
                # Return error if conversion fails
                return {
                    "success": False,
                    "error": f"Failed to convert PRs to CSV: {str(e)}",
                }

        return result

    async def get_pull_request(
        self, pull_request_id: Union[int, str], organization: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get details of a specific pull request."""
        command = f"repos pr show --id {pull_request_id}"

        # Use configured default for organization
        org = self._get_param_with_default(organization, self.default_organization)
        if org:
            command += f" --org {org}"

        return await self._run_az_command(command)

    async def create_pull_request(
        self,
        title: Optional[str] = None,
        source_branch: Optional[str] = None,
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
        """Create a new pull request."""
        # Handle None source_branch case
        if source_branch is None:
            # Generate branch name from commit ID and create/push it
            commit_branch = self._generate_branch_name_from_commit()
            self.logger.info(f"Creating branch from commit: {commit_branch}")

            branch_result = self._create_and_push_branch(commit_branch)
            if not branch_result.get("success", False):
                return branch_result

            source_branch = commit_branch

            # If title is also None, get it from last commit message
            if title is None:
                commit_title = self._get_last_commit_message()
                if commit_title:
                    title = commit_title
                    self.logger.info(f"Using commit message as title: {title}")
                else:
                    title = f"Auto PR from {source_branch}"
                    self.logger.warning(
                        f"Could not get commit message, using default title: {title}"
                    )

        # Ensure we have a title
        if title is None:
            return {
                "success": False,
                "error": "Title is required when source_branch is provided",
            }

        command = "repos pr create"

        # Required parameters
        command += f' --title "{title}"'
        command += f" --source-branch {source_branch}"

        # Use configured defaults for core parameters
        target_br = self._get_param_with_default(
            target_branch, self.default_target_branch
        )
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
        """Update an existing pull request."""
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
        """Set your vote on a pull request."""
        command = f"repos pr set-vote --id {pull_request_id} --vote {vote}"

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
        """Add work items to a pull request."""
        command = f"repos pr work-item add --id {pull_request_id}"

        # Add work items
        for item in work_items:
            command += f" --work-items {item}"

        # Use configured default for organization
        org = self._get_param_with_default(organization, self.default_organization)
        if org:
            command += f" --org {org}"

        return await self._run_az_command(command)

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments."""
        operation = arguments.get("operation", "")

        if operation == "list":
            return await self.list_pull_requests(
                repository=arguments.get("repository"),
                project=arguments.get("project"),
                organization=arguments.get("organization"),
                creator=arguments.get("creator", "default"),
                reviewer=arguments.get("reviewer"),
                status=arguments.get("status"),
                source_branch=arguments.get("source_branch"),
                target_branch=arguments.get("target_branch"),
                top=arguments.get("top"),
                skip=arguments.get("skip"),
            )
        elif operation == "get":
            return await self.get_pull_request(
                pull_request_id=arguments.get("pull_request_id"),
                organization=arguments.get("organization"),
            )
        elif operation == "create":
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
        elif operation == "update":
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
        elif operation == "vote":
            return await self.set_vote(
                pull_request_id=arguments.get("pull_request_id"),
                vote=arguments.get("vote"),
                organization=arguments.get("organization"),
            )
        elif operation == "add_work_items":
            return await self.add_work_items(
                pull_request_id=arguments.get("pull_request_id"),
                work_items=arguments.get("work_items", []),
                organization=arguments.get("organization"),
            )
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
