"""Git Commit Tool for MCP.

This module provides a dedicated Git commit tool that handles commit operations
and pull rebase functionality through the Model Context Protocol.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

import git

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool


class GitCommitOperationType(str, Enum):
    """Enumeration of supported Git commit operations."""

    COMMIT = "git_commit"
    PULL_REBASE = "git_pull_rebase"


@register_tool(ecosystem="general", os_type="all")
class GitCommitTool(ToolInterface):
    """Git commit tool for commit and pull rebase operations through MCP."""

    def __init__(self):
        """Initialize the Git commit tool."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """Return the tool name."""
        return "git_commit"

    @property
    def description(self) -> str:
        """Return the tool description."""
        return "Git commit operations including committing changes and pull rebase"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The Git commit operation to perform",
                    "enum": [op.value for op in GitCommitOperationType],
                },
                "repo_path": {
                    "type": "string",
                    "description": "Path to the Git repository",
                },
                "message": {
                    "type": "string",
                    "description": "Commit message (for commit operation)",
                },
                "remote": {
                    "type": "string",
                    "description": "Remote name for pull rebase operation (defaults to 'origin')",
                },
            },
            "required": ["operation", "repo_path"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"error": "Missing required parameter: operation"}

        return await self.execute_function(operation, arguments)

    async def execute_function(
        self, function_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Git commit function."""
        try:
            operation = GitCommitOperationType(function_name)

            # Validate repo_path for all operations
            repo_path = parameters.get("repo_path")
            if not repo_path:
                return {"error": "Missing required parameter: repo_path"}

            # Validate operation-specific parameters BEFORE accessing the repository
            match operation:
                case GitCommitOperationType.COMMIT:
                    message = parameters.get("message")
                    if not message:
                        return {"error": "Missing required parameter: message"}

            # Validate the repository exists
            repo = git.Repo(repo_path)

            match operation:
                case GitCommitOperationType.COMMIT:
                    message = parameters.get("message")  # Already validated above
                    result = self._git_commit(repo, message)
                    return {"success": True, "result": result}

                case GitCommitOperationType.PULL_REBASE:
                    remote = parameters.get("remote", "origin")
                    result = self._git_pull_rebase(repo, remote)
                    return {"success": True, "result": result}

                case _:
                    return {"error": f"Unknown Git commit operation: {operation}"}

        except git.InvalidGitRepositoryError:
            return {
                "success": False,
                "error": f"Invalid Git repository: {parameters.get('repo_path', 'unknown')}",
            }
        except git.GitCommandError as e:
            return {"success": False, "error": f"Git command failed: {str(e)}"}
        except Exception as e:
            self.logger.error(
                f"Error executing Git commit operation {function_name}: {str(e)}"
            )
            return {"success": False, "error": f"Git commit operation failed: {str(e)}"}

    def _git_commit(self, repo: git.Repo, message: str) -> str:
        """Commit changes."""
        commit = repo.index.commit(message)
        return f"Changes committed successfully with hash {commit.hexsha}"

    def _git_pull_rebase(self, repo: git.Repo, remote: str = "origin") -> str:
        """Pull changes from remote with rebase (no merge allowed)."""
        try:
            # Get the current branch name
            current_branch = repo.active_branch.name

            # Perform git pull --rebase
            # This will fetch from remote and rebase current branch on top of remote branch
            repo.git.pull("--rebase", remote, current_branch)

            return f"Successfully pulled and rebased '{current_branch}' from '{remote}/{current_branch}'"

        except git.GitCommandError as e:
            # Handle common rebase conflicts or issues
            if "conflict" in str(e).lower():
                return f"Pull rebase failed due to conflicts. Please resolve conflicts manually and run 'git rebase --continue' or 'git rebase --abort'"
            elif "no such remote" in str(e).lower():
                return (
                    f"Remote '{remote}' does not exist. Please check the remote name."
                )
            elif "no tracking information" in str(e).lower():
                return f"No tracking information for current branch. Please set up tracking or specify the remote branch explicitly."
            else:
                return f"Pull rebase failed: {str(e)}"
        except Exception as e:
            return f"Error during pull rebase: {str(e)}"
