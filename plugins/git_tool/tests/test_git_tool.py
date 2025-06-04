"""Tests for the Git tool."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import asyncio
import git
from git.exc import InvalidGitRepositoryError, GitCommandError

from plugins.git_tool.git_tool import GitTool, GitOperationType


@pytest.fixture
def git_tool():
    """Create a GitTool instance for testing."""
    return GitTool()


@pytest.fixture
def mock_repo():
    """Create a mock git repository."""
    repo = Mock(spec=git.Repo)
    repo.git = Mock()
    repo.heads = []
    repo.remotes = Mock()
    repo.remotes.origin = Mock()
    return repo


class TestGitTool:
    """Test cases for GitTool."""

    def test_name_property(self, git_tool):
        """Test the name property."""
        assert git_tool.name == "git"

    def test_description_property(self, git_tool):
        """Test the description property."""
        assert "Git repository operations" in git_tool.description

    def test_input_schema_structure(self, git_tool):
        """Test the input schema structure."""
        schema = git_tool.input_schema
        assert schema["type"] == "object"
        assert "operation" in schema["properties"]
        assert schema["properties"]["operation"]["type"] == "string"
        assert "enum" in schema["properties"]["operation"]
        
        # Check that all operations are in the enum
        operations = schema["properties"]["operation"]["enum"]
        expected_operations = [op.value for op in GitOperationType]
        assert set(operations) == set(expected_operations)

    @pytest.mark.asyncio
    async def test_invalid_operation(self, git_tool):
        """Test handling of invalid operation."""
        result = await git_tool.execute_tool({"operation": "invalid_op", "repo_path": "/test"})
        assert not result["success"]
        assert "Git operation failed" in result["error"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_status_success(self, mock_repo_class, git_tool, mock_repo):
        """Test git status operation."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.status.return_value = "On branch main\nnothing to commit, working tree clean"
        
        result = await git_tool.execute_tool({"operation": "git_status", "repo_path": "/test"})
        
        assert result["success"]
        assert "On branch main" in result["result"]
        mock_repo.git.status.assert_called_once()

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_status_invalid_repo(self, mock_repo_class, git_tool):
        """Test git status with invalid repository."""
        mock_repo_class.side_effect = InvalidGitRepositoryError("Not a git repo")
        
        result = await git_tool.execute_tool({"operation": "git_status", "repo_path": "/test"})
        
        assert not result["success"]
        assert "Invalid Git repository" in result["error"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_diff_unstaged(self, mock_repo_class, git_tool, mock_repo):
        """Test git diff unstaged operation."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.diff.return_value = "diff --git a/file.txt b/file.txt\n+new line"
        
        result = await git_tool.execute_tool({"operation": "git_diff_unstaged", "repo_path": "/test"})
        
        assert result["success"]
        assert "diff --git" in result["result"]
        mock_repo.git.diff.assert_called_once()

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_diff_staged(self, mock_repo_class, git_tool, mock_repo):
        """Test git diff staged operation."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.diff.return_value = "diff --git a/staged.txt b/staged.txt\n+staged change"
        
        result = await git_tool.execute_tool({"operation": "git_diff_staged", "repo_path": "/test"})
        
        assert result["success"]
        assert "staged change" in result["result"]
        mock_repo.git.diff.assert_called_once_with("--cached")

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_add_files(self, mock_repo_class, git_tool, mock_repo):
        """Test git add operation with specific files."""
        mock_repo_class.return_value = mock_repo
        mock_repo.index = Mock()
        mock_repo.index.add.return_value = None
        
        result = await git_tool.execute_tool({
            "operation": "git_add",
            "repo_path": "/test",
            "files": ["file1.txt", "file2.txt"]
        })
        
        assert result["success"]
        assert "Files staged successfully" in result["result"]
        mock_repo.index.add.assert_called_once_with(["file1.txt", "file2.txt"])

    @pytest.mark.asyncio
    async def test_add_missing_files(self, git_tool):
        """Test git add without files parameter."""
        result = await git_tool.execute_tool({"operation": "git_add", "repo_path": "/test"})
        
        assert "error" in result
        assert "Missing required parameter: files" in result["error"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_commit(self, mock_repo_class, git_tool, mock_repo):
        """Test git commit operation."""
        mock_repo_class.return_value = mock_repo
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_repo.index = Mock()
        mock_repo.index.commit.return_value = mock_commit
        
        result = await git_tool.execute_tool({
            "operation": "git_commit",
            "repo_path": "/test",
            "message": "Test commit"
        })
        
        assert result["success"]
        assert "abc123" in result["result"]
        mock_repo.index.commit.assert_called_once_with("Test commit")

    @pytest.mark.asyncio
    async def test_commit_missing_message(self, git_tool):
        """Test git commit without message."""
        result = await git_tool.execute_tool({"operation": "git_commit", "repo_path": "/test"})
        
        assert "error" in result
        assert "Missing required parameter: message" in result["error"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_reset(self, mock_repo_class, git_tool, mock_repo):
        """Test git reset operation."""
        mock_repo_class.return_value = mock_repo
        mock_repo.index = Mock()
        mock_repo.index.reset.return_value = None
        
        result = await git_tool.execute_tool({
            "operation": "git_reset",
            "repo_path": "/test"
        })
        
        assert result["success"]
        assert "All staged changes reset" in result["result"]
        mock_repo.index.reset.assert_called_once()

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_log(self, mock_repo_class, git_tool, mock_repo):
        """Test git log operation."""
        mock_repo_class.return_value = mock_repo
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_commit.author = "Test Author"
        mock_commit.authored_datetime = "2023-01-01"
        mock_commit.message = "Test commit"
        mock_repo.iter_commits.return_value = [mock_commit]
        
        result = await git_tool.execute_tool({
            "operation": "git_log",
            "repo_path": "/test",
            "max_count": 5
        })
        
        assert result["success"]
        assert "abc123" in result["result"]
        assert "Test commit" in result["result"]
        mock_repo.iter_commits.assert_called_once_with(max_count=5)

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_create_branch(self, mock_repo_class, git_tool, mock_repo):
        """Test create branch operation."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        mock_repo.create_head.return_value = mock_branch
        
        result = await git_tool.execute_tool({
            "operation": "git_create_branch",
            "repo_path": "/test",
            "branch_name": "feature-branch"
        })
        
        assert result["success"]
        assert "Created branch 'feature-branch'" in result["result"]
        mock_repo.create_head.assert_called_once_with("feature-branch", mock_branch)

    @pytest.mark.asyncio
    async def test_create_branch_missing_name(self, git_tool):
        """Test create branch without name."""
        result = await git_tool.execute_tool({"operation": "git_create_branch", "repo_path": "/test"})
        
        assert "error" in result
        assert "Missing required parameter: branch_name" in result["error"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_checkout_branch(self, mock_repo_class, git_tool, mock_repo):
        """Test checkout branch operation."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.checkout.return_value = ""
        
        result = await git_tool.execute_tool({
            "operation": "git_checkout",
            "repo_path": "/test",
            "branch_name": "main"
        })
        
        assert result["success"]
        assert "Switched to branch 'main'" in result["result"]
        mock_repo.git.checkout.assert_called_once_with("main")

    @pytest.mark.asyncio
    async def test_checkout_missing_branch(self, git_tool):
        """Test checkout without branch name."""
        result = await git_tool.execute_tool({"operation": "git_checkout", "repo_path": "/test"})
        
        assert "error" in result
        assert "Missing required parameter: branch_name" in result["error"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_show_commit(self, mock_repo_class, git_tool, mock_repo):
        """Test show commit operation."""
        mock_repo_class.return_value = mock_repo
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_commit.author = "Test Author"
        mock_commit.authored_datetime = "2023-01-01"
        mock_commit.message = "Test commit"
        mock_commit.parents = []
        mock_commit.diff.return_value = []
        mock_repo.commit.return_value = mock_commit
        
        result = await git_tool.execute_tool({
            "operation": "git_show",
            "repo_path": "/test",
            "revision": "abc123"
        })
        
        assert result["success"]
        assert "abc123" in result["result"]
        assert "Test commit" in result["result"]
        mock_repo.commit.assert_called_once_with("abc123")

    @pytest.mark.asyncio
    async def test_show_missing_revision(self, git_tool):
        """Test show without revision."""
        result = await git_tool.execute_tool({"operation": "git_show", "repo_path": "/test"})
        
        assert "error" in result
        assert "Missing required parameter: revision" in result["error"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_init_repository(self, mock_repo_class, git_tool):
        """Test git init operation."""
        mock_repo = Mock()
        mock_repo.git_dir = "/test/.git"
        mock_repo_class.init.return_value = mock_repo
        
        result = await git_tool.execute_tool({
            "operation": "git_init",
            "repo_path": "/test/path"
        })
        
        assert result["success"]
        assert "Initialized empty Git repository" in result["result"]
        mock_repo_class.init.assert_called_once_with(path="/test/path", mkdir=True)

    @pytest.mark.asyncio
    async def test_init_missing_path(self, git_tool):
        """Test git init without path."""
        result = await git_tool.execute_tool({"operation": "git_init"})
        
        assert "error" in result
        assert "Missing required parameter: repo_path" in result["error"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_git_command_error(self, mock_repo_class, git_tool, mock_repo):
        """Test handling of GitCommandError."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.status.side_effect = GitCommandError("git status", 1, "error message")
        
        result = await git_tool.execute_tool({"operation": "git_status", "repo_path": "/test"})
        
        assert not result["success"]
        assert "Git command failed" in result["error"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_diff_with_target(self, mock_repo_class, git_tool, mock_repo):
        """Test git diff with target."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.diff.return_value = "diff between commits"
        
        result = await git_tool.execute_tool({
            "operation": "git_diff",
            "repo_path": "/test",
            "target": "HEAD~1"
        })
        
        assert result["success"]
        assert "diff between commits" in result["result"]
        mock_repo.git.diff.assert_called_once_with("HEAD~1")

    @pytest.mark.asyncio
    async def test_diff_missing_target(self, git_tool):
        """Test git diff without target."""
        result = await git_tool.execute_tool({"operation": "git_diff", "repo_path": "/test"})
        
        assert "error" in result
        assert "Missing required parameter: target" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_repo_path(self, git_tool):
        """Test operation without repo_path."""
        result = await git_tool.execute_tool({"operation": "git_status"})
        
        assert "error" in result
        assert "Missing required parameter: repo_path" in result["error"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_pull_rebase_success(self, mock_repo_class, git_tool, mock_repo):
        """Test git pull rebase operation."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        mock_repo.git.pull.return_value = ""
        
        result = await git_tool.execute_tool({
            "operation": "git_pull_rebase",
            "repo_path": "/test"
        })
        
        assert result["success"]
        assert "Successfully pulled and rebased 'main' from 'origin/main'" in result["result"]
        mock_repo.git.pull.assert_called_once_with("--rebase", "origin", "main")

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_pull_rebase_with_custom_remote(self, mock_repo_class, git_tool, mock_repo):
        """Test git pull rebase with custom remote."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "feature"
        mock_repo.active_branch = mock_branch
        mock_repo.git.pull.return_value = ""
        
        result = await git_tool.execute_tool({
            "operation": "git_pull_rebase",
            "repo_path": "/test",
            "remote": "upstream"
        })
        
        assert result["success"]
        assert "Successfully pulled and rebased 'feature' from 'upstream/feature'" in result["result"]
        mock_repo.git.pull.assert_called_once_with("--rebase", "upstream", "feature")

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_pull_rebase_conflict(self, mock_repo_class, git_tool, mock_repo):
        """Test git pull rebase with conflicts."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        mock_repo.git.pull.side_effect = GitCommandError("git pull", 1, "conflict detected")
        
        result = await git_tool.execute_tool({
            "operation": "git_pull_rebase",
            "repo_path": "/test"
        })
        
        assert result["success"]
        assert "Pull rebase failed due to conflicts" in result["result"]
        assert "git rebase --continue" in result["result"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_pull_rebase_no_remote(self, mock_repo_class, git_tool, mock_repo):
        """Test git pull rebase with non-existent remote."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        mock_repo.git.pull.side_effect = GitCommandError("git pull", 1, "no such remote 'nonexistent'")
        
        result = await git_tool.execute_tool({
            "operation": "git_pull_rebase",
            "repo_path": "/test",
            "remote": "nonexistent"
        })
        
        assert result["success"]
        assert "Remote 'nonexistent' does not exist" in result["result"]

    @pytest.mark.asyncio
    @patch('git.Repo')
    async def test_pull_rebase_no_tracking(self, mock_repo_class, git_tool, mock_repo):
        """Test git pull rebase with no tracking information."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        mock_repo.git.pull.side_effect = GitCommandError("git pull", 1, "no tracking information for the current branch")
        
        result = await git_tool.execute_tool({
            "operation": "git_pull_rebase",
            "repo_path": "/test"
        })
        
        assert result["success"]
        assert "No tracking information for current branch" in result["result"] 