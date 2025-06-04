"""Git Tool for MCP.

This module provides a comprehensive Git tool that implements various Git operations
through the Model Context Protocol, including repository status, diff viewing,
committing changes, branch management, and more.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum

import git

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool


class GitOperationType(str, Enum):
    """Enumeration of supported Git operations."""
    STATUS = "git_status"
    DIFF_UNSTAGED = "git_diff_unstaged"
    DIFF_STAGED = "git_diff_staged"
    DIFF = "git_diff"
    COMMIT = "git_commit"
    ADD = "git_add"
    RESET = "git_reset"
    LOG = "git_log"
    CREATE_BRANCH = "git_create_branch"
    CHECKOUT = "git_checkout"
    SHOW = "git_show"
    INIT = "git_init"


@register_tool
class GitTool(ToolInterface):
    """Git tool for repository operations through MCP."""

    def __init__(self):
        """Initialize the Git tool."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """Return the tool name."""
        return "git"

    @property
    def description(self) -> str:
        """Return the tool description."""
        return "Git repository operations including status, diff, commit, branch management, and more"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The Git operation to perform",
                    "enum": [op.value for op in GitOperationType],
                },
                "repo_path": {
                    "type": "string",
                    "description": "Path to the Git repository",
                },
                "message": {
                    "type": "string",
                    "description": "Commit message (for commit operation)",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths (for add operation)",
                },
                "target": {
                    "type": "string",
                    "description": "Target branch or commit (for diff operation)",
                },
                "branch_name": {
                    "type": "string",
                    "description": "Name of the branch (for branch operations)",
                },
                "base_branch": {
                    "type": "string",
                    "description": "Base branch for new branch (optional)",
                },
                "revision": {
                    "type": "string",
                    "description": "Revision to show (for show operation)",
                },
                "max_count": {
                    "type": "integer",
                    "description": "Maximum number of commits to show (for log operation)",
                    "default": 10,
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

    async def execute_function(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Git function."""
        try:
            operation = GitOperationType(function_name)
            
            # Validate repo_path for all operations
            repo_path = parameters.get("repo_path")
            if not repo_path:
                return {"error": "Missing required parameter: repo_path"}
            
            # Validate operation-specific parameters BEFORE accessing the repository
            match operation:
                case GitOperationType.DIFF:
                    target = parameters.get("target")
                    if not target:
                        return {"error": "Missing required parameter: target"}
                
                case GitOperationType.COMMIT:
                    message = parameters.get("message")
                    if not message:
                        return {"error": "Missing required parameter: message"}
                
                case GitOperationType.ADD:
                    files = parameters.get("files")
                    if not files:
                        return {"error": "Missing required parameter: files"}
                
                case GitOperationType.CREATE_BRANCH:
                    branch_name = parameters.get("branch_name")
                    if not branch_name:
                        return {"error": "Missing required parameter: branch_name"}
                
                case GitOperationType.CHECKOUT:
                    branch_name = parameters.get("branch_name")
                    if not branch_name:
                        return {"error": "Missing required parameter: branch_name"}
                
                case GitOperationType.SHOW:
                    revision = parameters.get("revision")
                    if not revision:
                        return {"error": "Missing required parameter: revision"}
            
            # Handle git init separately since it doesn't require an existing repo
            if operation == GitOperationType.INIT:
                result = self._git_init(repo_path)
                return {"success": True, "result": result}
            
            # For all other operations, validate the repository exists
            repo = git.Repo(repo_path)
            
            match operation:
                case GitOperationType.STATUS:
                    result = self._git_status(repo)
                    return {"success": True, "result": f"Repository status:\n{result}"}
                
                case GitOperationType.DIFF_UNSTAGED:
                    result = self._git_diff_unstaged(repo)
                    return {"success": True, "result": f"Unstaged changes:\n{result}"}
                
                case GitOperationType.DIFF_STAGED:
                    result = self._git_diff_staged(repo)
                    return {"success": True, "result": f"Staged changes:\n{result}"}
                
                case GitOperationType.DIFF:
                    target = parameters.get("target")  # Already validated above
                    result = self._git_diff(repo, target)
                    return {"success": True, "result": f"Diff with {target}:\n{result}"}
                
                case GitOperationType.COMMIT:
                    message = parameters.get("message")  # Already validated above
                    result = self._git_commit(repo, message)
                    return {"success": True, "result": result}
                
                case GitOperationType.ADD:
                    files = parameters.get("files")  # Already validated above
                    result = self._git_add(repo, files)
                    return {"success": True, "result": result}
                
                case GitOperationType.RESET:
                    result = self._git_reset(repo)
                    return {"success": True, "result": result}
                
                case GitOperationType.LOG:
                    max_count = parameters.get("max_count", 10)
                    result = self._git_log(repo, max_count)
                    return {"success": True, "result": f"Commit history:\n{result}"}
                
                case GitOperationType.CREATE_BRANCH:
                    branch_name = parameters.get("branch_name")  # Already validated above
                    base_branch = parameters.get("base_branch")
                    result = self._git_create_branch(repo, branch_name, base_branch)
                    return {"success": True, "result": result}
                
                case GitOperationType.CHECKOUT:
                    branch_name = parameters.get("branch_name")  # Already validated above
                    result = self._git_checkout(repo, branch_name)
                    return {"success": True, "result": result}
                
                case GitOperationType.SHOW:
                    revision = parameters.get("revision")  # Already validated above
                    result = self._git_show(repo, revision)
                    return {"success": True, "result": result}
                
                case _:
                    return {"error": f"Unknown Git operation: {operation}"}
        
        except git.InvalidGitRepositoryError:
            return {"success": False, "error": f"Invalid Git repository: {parameters.get('repo_path', 'unknown')}"}
        except git.GitCommandError as e:
            return {"success": False, "error": f"Git command failed: {str(e)}"}
        except Exception as e:
            self.logger.error(f"Error executing Git operation {function_name}: {str(e)}")
            return {"success": False, "error": f"Git operation failed: {str(e)}"}

    def _git_status(self, repo: git.Repo) -> str:
        """Get repository status."""
        return repo.git.status()

    def _git_diff_unstaged(self, repo: git.Repo) -> str:
        """Get unstaged changes."""
        return repo.git.diff()

    def _git_diff_staged(self, repo: git.Repo) -> str:
        """Get staged changes."""
        return repo.git.diff("--cached")

    def _git_diff(self, repo: git.Repo, target: str) -> str:
        """Get diff with target branch or commit."""
        return repo.git.diff(target)

    def _git_commit(self, repo: git.Repo, message: str) -> str:
        """Commit changes."""
        commit = repo.index.commit(message)
        return f"Changes committed successfully with hash {commit.hexsha}"

    def _git_add(self, repo: git.Repo, files: List[str]) -> str:
        """Add files to staging area."""
        repo.index.add(files)
        return f"Files staged successfully: {', '.join(files)}"

    def _git_reset(self, repo: git.Repo) -> str:
        """Reset staged changes."""
        repo.index.reset()
        return "All staged changes reset"

    def _git_log(self, repo: git.Repo, max_count: int = 10) -> str:
        """Get commit log."""
        commits = list(repo.iter_commits(max_count=max_count))
        log_entries = []
        for commit in commits:
            log_entries.append(
                f"Commit: {commit.hexsha}\n"
                f"Author: {commit.author}\n"
                f"Date: {commit.authored_datetime}\n"
                f"Message: {commit.message}\n"
            )
        return "\n".join(log_entries)

    def _git_create_branch(self, repo: git.Repo, branch_name: str, base_branch: Optional[str] = None) -> str:
        """Create a new branch."""
        if base_branch:
            base = repo.refs[base_branch]
        else:
            base = repo.active_branch

        repo.create_head(branch_name, base)
        return f"Created branch '{branch_name}' from '{base.name}'"

    def _git_checkout(self, repo: git.Repo, branch_name: str) -> str:
        """Checkout a branch."""
        repo.git.checkout(branch_name)
        return f"Switched to branch '{branch_name}'"

    def _git_show(self, repo: git.Repo, revision: str) -> str:
        """Show commit contents."""
        commit = repo.commit(revision)
        output = [
            f"Commit: {commit.hexsha}\n"
            f"Author: {commit.author}\n"
            f"Date: {commit.authored_datetime}\n"
            f"Message: {commit.message}\n"
        ]
        
        if commit.parents:
            parent = commit.parents[0]
            diff = parent.diff(commit, create_patch=True)
        else:
            diff = commit.diff(git.NULL_TREE, create_patch=True)
        
        for d in diff:
            output.append(f"\n--- {d.a_path}\n+++ {d.b_path}\n")
            if d.diff:
                output.append(d.diff.decode('utf-8'))
        
        return "".join(output)

    def _git_init(self, repo_path: str) -> str:
        """Initialize a Git repository."""
        try:
            repo = git.Repo.init(path=repo_path, mkdir=True)
            return f"Initialized empty Git repository in {repo.git_dir}"
        except Exception as e:
            return f"Error initializing repository: {str(e)}" 