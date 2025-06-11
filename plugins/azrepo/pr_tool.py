"""Azure DevOps Pull Request tool implementation."""

import logging
import json
import pandas as pd
import uuid
import os
from typing import Dict, Any, List, Optional, Union

import aiohttp
import git

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
        PullRequestComment,
        PullRequestThread,
        PullRequestCommentsResponse,
        PullRequestCommentResponse,
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
    PullRequestComment = types_module.PullRequestComment
    PullRequestThread = types_module.PullRequestThread
    PullRequestCommentsResponse = types_module.PullRequestCommentsResponse
    PullRequestCommentResponse = types_module.PullRequestCommentResponse


@register_tool
class AzurePullRequestTool(ToolInterface):
    """Dedicated tool for managing Azure DevOps Pull Requests using REST API.

    This tool provides comprehensive pull request management capabilities
    including creating, updating, listing, and voting on pull requests.
    All operations use the Azure DevOps REST API for improved performance
    and reliability compared to CLI-based approaches.

    The tool automatically loads default configuration values from the environment
    while allowing parameter overrides for specific operations.

    Configuration:
        The tool automatically loads default values from environment variables
        with the AZREPO_ prefix:
        - AZREPO_ORG: Default organization URL
        - AZREPO_PROJECT: Default project name/ID
        - AZREPO_REPO: Default repository name/ID
        - AZREPO_BRANCH: Default target branch
        - AZREPO_PR_BRANCH_PREFIX: Default prefix for auto-generated PR branch names

    Authentication:
        Uses bearer token authentication with Azure DevOps REST API.
        Tokens are automatically retrieved from the environment or Azure CLI.

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
                        "get_comments",
                        "resolve_comment",
                        "add_comment",
                        "update_comment",
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
                    "description": "Name of the target branch (default: 'main' or configured default branch for list operation, use null for all branches)",
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
                    "description": "Status filter or new status for update operations (default: 'active' for list operation, use null for all statuses)",
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
                "exclude_drafts": {
                    "type": "boolean",
                    "description": "Exclude draft PRs from results (default: true)",
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
                "comment_id": {
                    "type": ["string", "integer"],
                    "description": "ID of the comment to resolve or update",
                    "nullable": True,
                },
                "thread_id": {
                    "type": ["string", "integer"],
                    "description": "ID of the comment thread",
                    "nullable": True,
                },
                "comment_content": {
                    "type": "string",
                    "description": "Content of the comment (supports markdown)",
                    "nullable": True,
                },
                "response_text": {
                    "type": "string",
                    "description": "Response text when resolving a comment",
                    "nullable": True,
                },
                "comment_status": {
                    "type": "string",
                    "description": "Filter comments by status (active, resolved, etc.)",
                    "nullable": True,
                },
                "comment_author": {
                    "type": "string",
                    "description": "Filter comments by author",
                    "nullable": True,
                },
                "parent_comment_id": {
                    "type": ["string", "integer"],
                    "description": "ID of parent comment when replying to existing comment",
                    "nullable": True,
                },
            },
            "required": ["operation"],
        }

    def __init__(self, command_executor=None):
        """Initialize the AzurePullRequestTool and load configuration.

        Args:
            command_executor: An instance of CommandExecutor to use for Git operations.
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
        status: Optional[str] = "active",
        source_branch: Optional[str] = None,
        target_branch: Optional[str] = "default",
        exclude_drafts: bool = True,
        top: Optional[int] = None,
        skip: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List pull requests in the repository using REST API."""
        try:
            # Use configured defaults for core parameters
            repo = self._get_param_with_default(repository, self.default_repository)
            proj = self._get_param_with_default(project, self.default_project)
            org = self._get_param_with_default(organization, self.default_organization)

            if not all([repo, proj, org]):
                missing = [
                    name
                    for name, value in [
                        ("repository", repo),
                        ("project", proj),
                        ("organization", org),
                    ]
                    if not value
                ]
                return {
                    "success": False,
                    "error": f"Missing required parameters: {', '.join(missing)}",
                }

            # Build URL and headers
            endpoint = f"git/repositories/{repo}/pullrequests"
            # Validate parameters before calling build_api_url
            if not org:
                raise ValueError("Organization must be provided")
            if not proj:
                raise ValueError("Project must be provided")
            url = build_api_url(org, proj, endpoint)
            headers = self._get_auth_headers()

            # Build query parameters
            params: Dict[str, Union[str, int]] = {"api-version": "7.1"}

            # Handle status parameter with new default behavior
            if status == "active":
                params["searchCriteria.status"] = "active"
            elif status:
                params["searchCriteria.status"] = status
            # If status is None, don't add status filter (backward compatibility)

            # Handle creator parameter with default behavior
            if creator == "default":
                creator_id = self._get_current_username()
                if creator_id:
                    self.logger.debug(
                        f"Using current user as creator filter: {creator_id}"
                    )
                    params["searchCriteria.creatorId"] = creator_id
            elif creator:
                params["searchCriteria.creatorId"] = creator

            if reviewer:
                params["searchCriteria.reviewerId"] = reviewer
            if source_branch:
                params["searchCriteria.sourceRefName"] = f"refs/heads/{source_branch}"

            # Handle target_branch parameter with smart default
            if target_branch == "default":
                # Use configured default target branch or "main" as fallback
                default_target = self.default_target_branch or "main"
                params["searchCriteria.targetRefName"] = f"refs/heads/{default_target}"
                self.logger.debug(f"Using default target branch: {default_target}")
            elif target_branch:
                params["searchCriteria.targetRefName"] = f"refs/heads/{target_branch}"
            # If target_branch is None, don't add target branch filter (backward compatibility)

            if top:
                params["$top"] = top
            if skip:
                params["$skip"] = skip

            self.logger.debug(
                f"Listing pull requests with URL: {url} and params: {params}"
            )

            # Make REST API call
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        prs = data.get("value", [])

                        # Filter out draft PRs if exclude_drafts is True
                        if exclude_drafts:
                            prs = [pr for pr in prs if not pr.get("isDraft", False)]
                            self.logger.debug(f"Filtered out draft PRs, {len(prs)} PRs remaining")

                        # Convert to DataFrame and return CSV
                        df = self.convert_pr_to_df(prs)
                        return {"success": True, "data": df.to_csv(index=False)}
                    else:
                        error_text = await response.text()
                        self.logger.error(
                            f"Failed to list pull requests: HTTP {response.status} - {error_text}"
                        )
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                        }
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while listing pull requests: {e}"
            )
            return {"success": False, "error": str(e)}

    async def get_pull_request(
        self, pull_request_id: Union[int, str], organization: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get details of a specific pull request using REST API."""
        try:
            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(None, self.default_project)
            repo = self._get_param_with_default(None, self.default_repository)

            if not org or not proj or not repo:
                return {"success": False, "error": "Organization, project, and repository are required"}

            # Build URL and headers
            endpoint = f"git/repositories/{repo}/pullrequests/{pull_request_id}?api-version=7.1"
            # Validate parameters before calling build_api_url
            if not org:
                raise ValueError("Organization must be provided")
            if not proj:
                raise ValueError("Project must be provided")
            url = build_api_url(org, proj, endpoint)
            headers = self._get_auth_headers()

            # Make REST API call
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            pr_data = json.loads(response_text)
                            return {"success": True, "data": pr_data}
                        except json.JSONDecodeError as e:
                            return {"success": False, "error": f"Failed to parse response: {e}"}
                    elif response.status == 404:
                        return {"success": False, "error": f"Pull request {pull_request_id} not found"}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}: {response_text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

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
        """Create a new pull request using REST API."""
        try:
            # Handle None source_branch case (preserve existing auto-branch creation logic)
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

            # Use configured defaults for core parameters
            target_br = self._get_param_with_default(
                target_branch, self.default_target_branch
            )
            repo = self._get_param_with_default(repository, self.default_repository)
            proj = self._get_param_with_default(project, self.default_project)
            org = self._get_param_with_default(organization, self.default_organization)

            if not org or not proj or not repo:
                return {"success": False, "error": "Organization, project, and repository are required"}

            # Build URL and headers
            endpoint = f"git/repositories/{repo}/pullrequests?api-version=7.1"
            # Validate parameters before calling build_api_url
            if not org:
                raise ValueError("Organization must be provided")
            if not proj:
                raise ValueError("Project must be provided")
            url = build_api_url(org, proj, endpoint)
            headers = self._get_auth_headers()

            # Build request body
            request_body = {
                "sourceRefName": f"refs/heads/{source_branch}",
                "targetRefName": f"refs/heads/{target_br or 'main'}",
                "title": title,
                "isDraft": draft
            }

            if description:
                request_body["description"] = description

            # Add reviewers if provided
            if reviewers:
                request_body["reviewers"] = [{"id": reviewer} for reviewer in reviewers]

            # Add work items if provided
            if work_items:
                request_body["workItemRefs"] = [{"id": str(item)} for item in work_items]

            self.logger.debug(f"Creating pull request with body: {request_body}")

            # Make REST API call
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=request_body) as response:
                    response_text = await response.text()

                    if response.status == 201:
                        try:
                            pr_data = json.loads(response_text)

                            # Handle auto-complete and other post-creation settings
                            if auto_complete or squash or delete_source_branch:
                                pr_id = pr_data.get("pullRequestId")
                                if pr_id:
                                    # Update PR with completion settings
                                    update_result = await self._update_pr_completion_settings(
                                        pr_id, org, proj, repo, auto_complete, squash, delete_source_branch
                                    )
                                    if not update_result.get("success", False):
                                        self.logger.warning(f"Failed to set completion settings: {update_result.get('error')}")

                            return {"success": True, "data": pr_data}
                        except json.JSONDecodeError as e:
                            return {"success": False, "error": f"Failed to parse response: {e}"}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}: {response_text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _update_pr_completion_settings(
        self,
        pr_id: Union[int, str],
        organization: str,
        project: str,
        repository: str,
        auto_complete: bool = False,
        squash: bool = False,
        delete_source_branch: bool = False,
    ) -> Dict[str, Any]:
        """Update pull request completion settings using REST API."""
        try:
            # Build URL and headers for updating PR
            endpoint = f"git/repositories/{repository}/pullrequests/{pr_id}?api-version=7.1"
            # Validate parameters before calling build_api_url
            if not organization:
                raise ValueError("Organization must be provided")
            if not project:
                raise ValueError("Project must be provided")
            url = build_api_url(organization, project, endpoint)
            headers = self._get_auth_headers()

            # Build request body for completion settings
            request_body = {}

            if auto_complete:
                # Set auto-complete with merge options
                request_body["completionOptions"] = {
                    "mergeCommitMessage": "",
                    "deleteSourceBranch": delete_source_branch,
                    "squashMerge": squash,
                    "mergeStrategy": "squash" if squash else "merge"
                }
                request_body["autoCompleteSetBy"] = {"id": self._get_current_username()}

            # Make REST API call to update PR
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, headers=headers, json=request_body) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            pr_data = json.loads(response_text)
                            return {"success": True, "data": pr_data}
                        except json.JSONDecodeError as e:
                            return {"success": False, "error": f"Failed to parse response: {e}"}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}: {response_text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

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
        """Update an existing pull request using REST API."""
        try:
            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(None, self.default_project)
            repo = self._get_param_with_default(None, self.default_repository)

            if not org or not proj or not repo:
                return {"success": False, "error": "Organization, project, and repository are required"}

            # Build URL and headers
            endpoint = f"git/repositories/{repo}/pullrequests/{pull_request_id}?api-version=7.1"
            # Validate parameters before calling build_api_url
            if not org:
                raise ValueError("Organization must be provided")
            if not proj:
                raise ValueError("Project must be provided")
            url = build_api_url(org, proj, endpoint)
            headers = self._get_auth_headers()

            # Build request body with only provided fields
            request_body = {}

            if title is not None:
                request_body["title"] = title
            if description is not None:
                request_body["description"] = description
            if status is not None:
                request_body["status"] = status
            if draft is not None:
                request_body["isDraft"] = draft

            # Handle completion options
            completion_options = {}
            if squash is not None:
                completion_options["squashMerge"] = squash
            if delete_source_branch is not None:
                completion_options["deleteSourceBranch"] = delete_source_branch

            if completion_options:
                request_body["completionOptions"] = completion_options

            # Handle auto-complete
            if auto_complete is not None:
                if auto_complete:
                    current_user = self._get_current_username()
                    if current_user:
                        request_body["autoCompleteSetBy"] = {"id": current_user}
                else:
                    request_body["autoCompleteSetBy"] = None

            self.logger.debug(f"Updating PR {pull_request_id} with body: {request_body}")

            # Make REST API call
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, json=request_body, headers=headers) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            pr_data = json.loads(response_text)
                            return {"success": True, "data": pr_data}
                        except json.JSONDecodeError as e:
                            return {"success": False, "error": f"Failed to parse response: {e}"}
                    elif response.status == 404:
                        return {"success": False, "error": f"Pull request {pull_request_id} not found"}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}: {response_text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_vote(
        self,
        pull_request_id: Union[int, str],
        vote: str,
        organization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set your vote on a pull request using REST API."""
        try:
            # Vote mapping
            VOTE_MAPPING = {
                "approve": 10,
                "approve-with-suggestions": 5,
                "reset": 0,
                "wait-for-author": -5,
                "reject": -10
            }

            if vote not in VOTE_MAPPING:
                return {"success": False, "error": f"Invalid vote value: {vote}. Must be one of: {list(VOTE_MAPPING.keys())}"}

            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(None, self.default_project)
            repo = self._get_param_with_default(None, self.default_repository)

            if not org or not proj or not repo:
                return {"success": False, "error": "Organization, project, and repository are required"}

            # Get current user ID for reviewer endpoint
            current_user = self._get_current_username()
            if not current_user:
                return {"success": False, "error": "Unable to determine current user for voting"}

            # Build URL and headers
            endpoint = f"git/repositories/{repo}/pullrequests/{pull_request_id}/reviewers/{current_user}?api-version=7.1"
            # Validate parameters before calling build_api_url
            if not org:
                raise ValueError("Organization must be provided")
            if not proj:
                raise ValueError("Project must be provided")
            url = build_api_url(org, proj, endpoint)
            headers = self._get_auth_headers()

            # Build request body
            request_body = {
                "vote": VOTE_MAPPING[vote],
                "isRequired": False
            }

            self.logger.debug(f"Setting vote {vote} ({VOTE_MAPPING[vote]}) on PR {pull_request_id} for user {current_user}")

            # Make REST API call
            async with aiohttp.ClientSession() as session:
                async with session.put(url, json=request_body, headers=headers) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            reviewer_data = json.loads(response_text)
                            return {"success": True, "data": reviewer_data}
                        except json.JSONDecodeError as e:
                            return {"success": False, "error": f"Failed to parse response: {e}"}
                    elif response.status == 404:
                        return {"success": False, "error": f"Pull request {pull_request_id} not found or user not authorized"}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}: {response_text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def add_work_items(
        self,
        pull_request_id: Union[int, str],
        work_items: List[Union[int, str]],
        organization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add work items to a pull request using REST API."""
        try:
            if not work_items:
                return {"success": False, "error": "At least one work item ID is required"}

            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(None, self.default_project)
            repo = self._get_param_with_default(None, self.default_repository)

            if not org or not proj or not repo:
                return {"success": False, "error": "Organization, project, and repository are required"}

            # Build URL and headers
            endpoint = f"git/repositories/{repo}/pullrequests/{pull_request_id}?api-version=7.1"
            # Validate parameters before calling build_api_url
            if not org:
                raise ValueError("Organization must be provided")
            if not proj:
                raise ValueError("Project must be provided")
            url = build_api_url(org, proj, endpoint)
            headers = self._get_auth_headers()

            # Build request body with work item references
            request_body = {
                "workItemRefs": [{"id": str(item)} for item in work_items]
            }

            self.logger.debug(f"Adding work items to PR {pull_request_id}: {work_items}")

            # Make REST API call
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, json=request_body, headers=headers) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            pr_data = json.loads(response_text)
                            return {"success": True, "data": pr_data}
                        except json.JSONDecodeError as e:
                            return {"success": False, "error": f"Failed to parse response: {e}"}
                    elif response.status == 404:
                        return {"success": False, "error": f"Pull request {pull_request_id} not found"}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}: {response_text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_comments(
        self,
        pull_request_id: Union[int, str],
        organization: Optional[str] = None,
        project: Optional[str] = None,
        repository: Optional[str] = None,
        comment_status: Optional[str] = None,
        comment_author: Optional[str] = None,
        top: Optional[int] = None,
        skip: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get comments for a pull request using REST API."""
        try:
            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(project, self.default_project)
            repo = self._get_param_with_default(repository, self.default_repository)

            if not org or not proj or not repo:
                return {"success": False, "error": "Organization, project, and repository are required"}

            # Build URL and headers
            endpoint = f"git/repositories/{repo}/pullrequests/{pull_request_id}/threads"
            url = build_api_url(org, proj, endpoint)
            headers = self._get_auth_headers()

            # Build query parameters
            params: Dict[str, Union[str, int]] = {"api-version": "7.1"}

            if top:
                params["$top"] = top
            if skip:
                params["$skip"] = skip

            self.logger.debug(f"Getting PR comments with URL: {url} and params: {params}")

            # Make REST API call
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            data = json.loads(response_text)
                            threads = data.get("value", [])

                            # Filter by status if specified
                            if comment_status:
                                threads = [t for t in threads if t.get("status", "").lower() == comment_status.lower()]

                            # Filter by author if specified
                            if comment_author:
                                filtered_threads = []
                                for thread in threads:
                                    comments = thread.get("comments", [])
                                    filtered_comments = [
                                        c for c in comments
                                        if c.get("author", {}).get("uniqueName", "").lower() == comment_author.lower() or
                                           c.get("author", {}).get("displayName", "").lower() == comment_author.lower()
                                    ]
                                    if filtered_comments:
                                        thread_copy = thread.copy()
                                        thread_copy["comments"] = filtered_comments
                                        filtered_threads.append(thread_copy)
                                threads = filtered_threads

                            return {"success": True, "data": threads}
                        except json.JSONDecodeError as e:
                            return {"success": False, "error": f"Failed to parse response: {e}"}
                    elif response.status == 404:
                        return {"success": False, "error": f"Pull request {pull_request_id} not found"}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}: {response_text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def resolve_comment(
        self,
        pull_request_id: Union[int, str],
        thread_id: Union[int, str],
        response_text: Optional[str] = None,
        organization: Optional[str] = None,
        project: Optional[str] = None,
        repository: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve a pull request comment thread using REST API."""
        try:
            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(project, self.default_project)
            repo = self._get_param_with_default(repository, self.default_repository)

            if not org or not proj or not repo:
                return {"success": False, "error": "Organization, project, and repository are required"}

            # Build URL and headers
            endpoint = f"git/repositories/{repo}/pullrequests/{pull_request_id}/threads/{thread_id}"
            url = build_api_url(org, proj, endpoint)
            headers = self._get_auth_headers()

            # Build request body to resolve the thread
            request_body = {
                "status": "fixed"  # Azure DevOps uses "fixed" to mark threads as resolved
            }

            # Add response comment if provided
            if response_text:
                # First, add a response comment to the thread
                comment_result = await self.add_comment(
                    pull_request_id=pull_request_id,
                    thread_id=thread_id,
                    comment_content=response_text,
                    organization=org,
                    project=proj,
                    repository=repo,
                )
                if not comment_result.get("success", False):
                    return comment_result

            self.logger.debug(f"Resolving comment thread {thread_id} on PR {pull_request_id}")

            # Make REST API call to update thread status
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, json=request_body, headers=headers, params={"api-version": "7.1"}) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            thread_data = json.loads(response_text)
                            return {"success": True, "data": thread_data}
                        except json.JSONDecodeError as e:
                            return {"success": False, "error": f"Failed to parse response: {e}"}
                    elif response.status == 404:
                        return {"success": False, "error": f"Thread {thread_id} not found on PR {pull_request_id}"}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}: {response_text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def add_comment(
        self,
        pull_request_id: Union[int, str],
        comment_content: str,
        thread_id: Optional[Union[int, str]] = None,
        parent_comment_id: Optional[Union[int, str]] = None,
        organization: Optional[str] = None,
        project: Optional[str] = None,
        repository: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a comment to a pull request using REST API."""
        try:
            if not comment_content:
                return {"success": False, "error": "Comment content is required"}

            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(project, self.default_project)
            repo = self._get_param_with_default(repository, self.default_repository)

            if not org or not proj or not repo:
                return {"success": False, "error": "Organization, project, and repository are required"}

            if thread_id:
                # Add comment to existing thread
                endpoint = f"git/repositories/{repo}/pullrequests/{pull_request_id}/threads/{thread_id}/comments"
                url = build_api_url(org, proj, endpoint)

                request_body = {
                    "content": comment_content,
                    "commentType": "text"
                }

                if parent_comment_id:
                    request_body["parentCommentId"] = int(parent_comment_id)

            else:
                # Create new thread with comment
                endpoint = f"git/repositories/{repo}/pullrequests/{pull_request_id}/threads"
                url = build_api_url(org, proj, endpoint)

                request_body = {
                    "comments": [
                        {
                            "content": comment_content,
                            "commentType": "text"
                        }
                    ],
                    "status": "active"
                }

            headers = self._get_auth_headers()

            self.logger.debug(f"Adding comment to PR {pull_request_id}, thread_id: {thread_id}")

            # Make REST API call
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=request_body, headers=headers, params={"api-version": "7.1"}) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            comment_data = json.loads(response_text)
                            return {"success": True, "data": comment_data}
                        except json.JSONDecodeError as e:
                            return {"success": False, "error": f"Failed to parse response: {e}"}
                    elif response.status == 404:
                        return {"success": False, "error": f"Pull request {pull_request_id} or thread {thread_id} not found"}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}: {response_text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_comment(
        self,
        pull_request_id: Union[int, str],
        thread_id: Union[int, str],
        comment_id: Union[int, str],
        comment_content: str,
        organization: Optional[str] = None,
        project: Optional[str] = None,
        repository: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing pull request comment using REST API."""
        try:
            if not comment_content:
                return {"success": False, "error": "Comment content is required"}

            # Use configured defaults for core parameters
            org = self._get_param_with_default(organization, self.default_organization)
            proj = self._get_param_with_default(project, self.default_project)
            repo = self._get_param_with_default(repository, self.default_repository)

            if not org or not proj or not repo:
                return {"success": False, "error": "Organization, project, and repository are required"}

            # Build URL and headers
            endpoint = f"git/repositories/{repo}/pullrequests/{pull_request_id}/threads/{thread_id}/comments/{comment_id}"
            url = build_api_url(org, proj, endpoint)
            headers = self._get_auth_headers()

            # Build request body
            request_body = {
                "content": comment_content
            }

            self.logger.debug(f"Updating comment {comment_id} in thread {thread_id} on PR {pull_request_id}")

            # Make REST API call
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, json=request_body, headers=headers, params={"api-version": "7.1"}) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        try:
                            comment_data = json.loads(response_text)
                            return {"success": True, "data": comment_data}
                        except json.JSONDecodeError as e:
                            return {"success": False, "error": f"Failed to parse response: {e}"}
                    elif response.status == 404:
                        return {"success": False, "error": f"Comment {comment_id} not found in thread {thread_id} on PR {pull_request_id}"}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}: {response_text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

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
                status=arguments.get("status", "active"),
                source_branch=arguments.get("source_branch"),
                target_branch=arguments.get("target_branch", "default"),
                exclude_drafts=arguments.get("exclude_drafts", True),
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
        elif operation == "get_comments":
            return await self.get_comments(
                pull_request_id=arguments.get("pull_request_id"),
                organization=arguments.get("organization"),
                project=arguments.get("project"),
                repository=arguments.get("repository"),
                comment_status=arguments.get("comment_status"),
                comment_author=arguments.get("comment_author"),
                top=arguments.get("top"),
                skip=arguments.get("skip"),
            )
        elif operation == "resolve_comment":
            return await self.resolve_comment(
                pull_request_id=arguments.get("pull_request_id"),
                thread_id=arguments.get("thread_id"),
                response_text=arguments.get("response_text"),
                organization=arguments.get("organization"),
                project=arguments.get("project"),
                repository=arguments.get("repository"),
            )
        elif operation == "add_comment":
            return await self.add_comment(
                pull_request_id=arguments.get("pull_request_id"),
                comment_content=arguments.get("comment_content"),
                thread_id=arguments.get("thread_id"),
                parent_comment_id=arguments.get("parent_comment_id"),
                organization=arguments.get("organization"),
                project=arguments.get("project"),
                repository=arguments.get("repository"),
            )
        elif operation == "update_comment":
            return await self.update_comment(
                pull_request_id=arguments.get("pull_request_id"),
                thread_id=arguments.get("thread_id"),
                comment_id=arguments.get("comment_id"),
                comment_content=arguments.get("comment_content"),
                organization=arguments.get("organization"),
                project=arguments.get("project"),
                repository=arguments.get("repository"),
            )
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    # Backward compatibility methods for tests
    def _get_current_username(self) -> Optional[str]:
        """Backward compatibility method for tests."""
        # Convert potential bytes to string if needed
        username = get_current_username()
        if isinstance(username, bytes):
            return username.decode("utf-8")
        return username

    def _get_auth_headers(
        self, content_type: str = "application/json"
    ) -> Dict[str, str]:
        """Backward compatibility method for tests."""
        return get_auth_headers(content_type=content_type)
