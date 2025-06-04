"""Tests for the Git Commit tool."""

import pytest
from unittest.mock import Mock, patch
import git
from git.exc import InvalidGitRepositoryError, GitCommandError

from plugins.git_tool.git_commit_tool import GitCommitTool, GitCommitOperationType


@pytest.fixture
def git_commit_tool():
    """Create a GitCommitTool instance for testing."""
    return GitCommitTool()


@pytest.fixture
def mock_repo():
    """Create a mock git repository."""
    repo = Mock(spec=git.Repo)
    repo.git = Mock()
    repo.index = Mock()
    repo.active_branch = Mock()
    return repo


class TestGitCommitTool:
    """Test cases for GitCommitTool."""

    def test_name_property(self, git_commit_tool):
        """Test the name property."""
        assert git_commit_tool.name == "git_commit"

    def test_description_property(self, git_commit_tool):
        """Test the description property."""
        assert "Git commit operations" in git_commit_tool.description

    def test_input_schema_structure(self, git_commit_tool):
        """Test the input schema structure."""
        schema = git_commit_tool.input_schema
        assert schema["type"] == "object"
        assert "operation" in schema["properties"]
        assert schema["properties"]["operation"]["type"] == "string"
        assert schema["properties"]["operation"]["enum"]

        # Check that all operations are in the enum
        operations = schema["properties"]["operation"]["enum"]
        expected_operations = [op.value for op in GitCommitOperationType]
        assert set(operations) == set(expected_operations)

    @pytest.mark.asyncio
    async def test_invalid_operation(self, git_commit_tool):
        """Test handling of invalid operation."""
        result = await git_commit_tool.execute_tool(
            {"operation": "invalid_op", "repo_path": "/test"}
        )
        assert not result["success"]
        assert "Git commit operation failed" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_repo_path(self, git_commit_tool):
        """Test handling of missing repo_path."""
        result = await git_commit_tool.execute_tool({"operation": "git_commit"})
        assert "error" in result
        assert "Missing required parameter: repo_path" in result["error"]

    # Commit operation tests
    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_commit_success(self, mock_repo_class, git_commit_tool, mock_repo):
        """Test successful git commit operation."""
        mock_repo_class.return_value = mock_repo
        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_repo.index.commit.return_value = mock_commit

        result = await git_commit_tool.execute_tool(
            {
                "operation": "git_commit",
                "repo_path": "/test",
                "message": "Test commit message",
            }
        )

        assert result["success"]
        assert (
            "Changes committed successfully with hash abc123def456" in result["result"]
        )
        mock_repo.index.commit.assert_called_once_with("Test commit message")

    @pytest.mark.asyncio
    async def test_commit_missing_message(self, git_commit_tool):
        """Test git commit without message."""
        result = await git_commit_tool.execute_tool(
            {"operation": "git_commit", "repo_path": "/test"}
        )

        assert "error" in result
        assert "Missing required parameter: message" in result["error"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_commit_invalid_repo(self, mock_repo_class, git_commit_tool):
        """Test git commit with invalid repository."""
        mock_repo_class.side_effect = InvalidGitRepositoryError("Not a git repo")

        result = await git_commit_tool.execute_tool(
            {"operation": "git_commit", "repo_path": "/test", "message": "Test commit"}
        )

        assert not result["success"]
        assert "Invalid Git repository" in result["error"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_commit_git_error(self, mock_repo_class, git_commit_tool, mock_repo):
        """Test git commit with Git command error."""
        mock_repo_class.return_value = mock_repo
        mock_repo.index.commit.side_effect = GitCommandError(
            "commit", 1, "nothing to commit"
        )

        result = await git_commit_tool.execute_tool(
            {"operation": "git_commit", "repo_path": "/test", "message": "Test commit"}
        )

        assert not result["success"]
        assert "Git command failed" in result["error"]

    # Pull rebase operation tests
    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_pull_rebase_success(
        self, mock_repo_class, git_commit_tool, mock_repo
    ):
        """Test successful git pull rebase operation."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        mock_repo.git.pull.return_value = ""

        result = await git_commit_tool.execute_tool(
            {"operation": "git_pull_rebase", "repo_path": "/test"}
        )

        assert result["success"]
        assert (
            "Successfully pulled and rebased 'main' from 'origin/main'"
            in result["result"]
        )
        mock_repo.git.pull.assert_called_once_with("--rebase", "origin", "main")

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_pull_rebase_with_custom_remote(
        self, mock_repo_class, git_commit_tool, mock_repo
    ):
        """Test git pull rebase with custom remote."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "feature"
        mock_repo.active_branch = mock_branch
        mock_repo.git.pull.return_value = ""

        result = await git_commit_tool.execute_tool(
            {"operation": "git_pull_rebase", "repo_path": "/test", "remote": "upstream"}
        )

        assert result["success"]
        assert (
            "Successfully pulled and rebased 'feature' from 'upstream/feature'"
            in result["result"]
        )
        mock_repo.git.pull.assert_called_once_with("--rebase", "upstream", "feature")

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_pull_rebase_conflict(
        self, mock_repo_class, git_commit_tool, mock_repo
    ):
        """Test git pull rebase with conflicts."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        mock_repo.git.pull.side_effect = GitCommandError(
            "git pull", 1, "conflict detected"
        )

        result = await git_commit_tool.execute_tool(
            {"operation": "git_pull_rebase", "repo_path": "/test"}
        )

        assert result["success"]
        assert "Pull rebase failed due to conflicts" in result["result"]
        assert "git rebase --continue" in result["result"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_pull_rebase_no_remote(
        self, mock_repo_class, git_commit_tool, mock_repo
    ):
        """Test git pull rebase with non-existent remote."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        mock_repo.git.pull.side_effect = GitCommandError(
            "git pull", 1, "no such remote 'nonexistent'"
        )

        result = await git_commit_tool.execute_tool(
            {
                "operation": "git_pull_rebase",
                "repo_path": "/test",
                "remote": "nonexistent",
            }
        )

        assert result["success"]
        assert "Remote 'nonexistent' does not exist" in result["result"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_pull_rebase_no_tracking(
        self, mock_repo_class, git_commit_tool, mock_repo
    ):
        """Test git pull rebase with no tracking information."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        mock_repo.git.pull.side_effect = GitCommandError(
            "git pull", 1, "no tracking information for the current branch"
        )

        result = await git_commit_tool.execute_tool(
            {"operation": "git_pull_rebase", "repo_path": "/test"}
        )

        assert result["success"]
        assert "No tracking information for current branch" in result["result"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_pull_rebase_invalid_repo(self, mock_repo_class, git_commit_tool):
        """Test git pull rebase with invalid repository."""
        mock_repo_class.side_effect = InvalidGitRepositoryError("Not a git repo")

        result = await git_commit_tool.execute_tool(
            {"operation": "git_pull_rebase", "repo_path": "/test"}
        )

        assert not result["success"]
        assert "Invalid Git repository" in result["error"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_pull_rebase_generic_error(
        self, mock_repo_class, git_commit_tool, mock_repo
    ):
        """Test git pull rebase with generic error."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        mock_repo.git.pull.side_effect = Exception("Generic error")

        result = await git_commit_tool.execute_tool(
            {"operation": "git_pull_rebase", "repo_path": "/test"}
        )

        assert result["success"]
        assert "Error during pull rebase: Generic error" in result["result"]
