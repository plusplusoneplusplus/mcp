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
        result = await git_tool.execute_tool(
            {"operation": "invalid_op", "repo_path": "/test"}
        )
        assert not result["success"]
        assert "Git operation failed" in result["error"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_status_success(self, mock_repo_class, git_tool, mock_repo):
        """Test git status operation."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.status.return_value = (
            "On branch main\nnothing to commit, working tree clean"
        )

        result = await git_tool.execute_tool(
            {"operation": "git_status", "repo_path": "/test"}
        )

        assert result["success"]
        assert "On branch main" in result["result"]
        mock_repo.git.status.assert_called_once()

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_status_invalid_repo(self, mock_repo_class, git_tool):
        """Test git status with invalid repository."""
        mock_repo_class.side_effect = InvalidGitRepositoryError("Not a git repo")

        result = await git_tool.execute_tool(
            {"operation": "git_status", "repo_path": "/test"}
        )

        assert not result["success"]
        assert "Invalid Git repository" in result["error"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_diff_unstaged(self, mock_repo_class, git_tool, mock_repo):
        """Test git diff unstaged operation."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.diff.return_value = "diff --git a/file.txt b/file.txt\n+new line"

        result = await git_tool.execute_tool(
            {"operation": "git_diff_unstaged", "repo_path": "/test"}
        )

        assert result["success"]
        assert "diff --git" in result["result"]
        mock_repo.git.diff.assert_called_once()

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_diff_staged(self, mock_repo_class, git_tool, mock_repo):
        """Test git diff staged operation."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.diff.return_value = (
            "diff --git a/staged.txt b/staged.txt\n+staged change"
        )

        result = await git_tool.execute_tool(
            {"operation": "git_diff_staged", "repo_path": "/test"}
        )

        assert result["success"]
        assert "staged change" in result["result"]
        mock_repo.git.diff.assert_called_once_with("--cached")

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_add_files(self, mock_repo_class, git_tool, mock_repo):
        """Test git add operation with specific files."""
        mock_repo_class.return_value = mock_repo
        mock_repo.index = Mock()
        mock_repo.index.add.return_value = None

        result = await git_tool.execute_tool(
            {
                "operation": "git_add",
                "repo_path": "/test",
                "files": ["file1.txt", "file2.txt"],
            }
        )

        assert result["success"]
        assert "Files staged successfully" in result["result"]
        mock_repo.index.add.assert_called_once_with(["file1.txt", "file2.txt"])

    @pytest.mark.asyncio
    async def test_add_missing_files(self, git_tool):
        """Test git add without files parameter."""
        result = await git_tool.execute_tool(
            {"operation": "git_add", "repo_path": "/test"}
        )

        assert "error" in result
        assert "Missing required parameter: files" in result["error"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_reset(self, mock_repo_class, git_tool, mock_repo):
        """Test git reset operation."""
        mock_repo_class.return_value = mock_repo
        mock_repo.index = Mock()
        mock_repo.index.reset.return_value = None

        result = await git_tool.execute_tool(
            {"operation": "git_reset", "repo_path": "/test"}
        )

        assert result["success"]
        assert "All staged changes reset" in result["result"]
        mock_repo.index.reset.assert_called_once()

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_log(self, mock_repo_class, git_tool, mock_repo):
        """Test git log operation."""
        mock_repo_class.return_value = mock_repo
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_commit.author = "Test Author"
        mock_commit.authored_datetime = "2023-01-01"
        mock_commit.message = "Test commit"
        mock_repo.iter_commits.return_value = [mock_commit]

        result = await git_tool.execute_tool(
            {"operation": "git_log", "repo_path": "/test", "max_count": 5}
        )

        assert result["success"]
        assert "abc123" in result["result"]
        assert "Test commit" in result["result"]
        mock_repo.iter_commits.assert_called_once_with(max_count=5)

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_create_branch(self, mock_repo_class, git_tool, mock_repo):
        """Test create branch operation."""
        mock_repo_class.return_value = mock_repo
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        mock_repo.create_head.return_value = mock_branch

        result = await git_tool.execute_tool(
            {
                "operation": "git_create_branch",
                "repo_path": "/test",
                "branch_name": "feature-branch",
            }
        )

        assert result["success"]
        assert "Created branch 'feature-branch'" in result["result"]
        mock_repo.create_head.assert_called_once_with("feature-branch", mock_branch)

    @pytest.mark.asyncio
    async def test_create_branch_missing_name(self, git_tool):
        """Test create branch without name."""
        result = await git_tool.execute_tool(
            {"operation": "git_create_branch", "repo_path": "/test"}
        )

        assert "error" in result
        assert "Missing required parameter: branch_name" in result["error"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_checkout_branch(self, mock_repo_class, git_tool, mock_repo):
        """Test checkout branch operation."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.checkout.return_value = ""

        result = await git_tool.execute_tool(
            {"operation": "git_checkout", "repo_path": "/test", "branch_name": "main"}
        )

        assert result["success"]
        assert "Switched to branch 'main'" in result["result"]
        mock_repo.git.checkout.assert_called_once_with("main")

    @pytest.mark.asyncio
    async def test_checkout_missing_branch(self, git_tool):
        """Test checkout without branch name."""
        result = await git_tool.execute_tool(
            {"operation": "git_checkout", "repo_path": "/test"}
        )

        assert "error" in result
        assert "Missing required parameter: branch_name" in result["error"]

    @pytest.mark.asyncio
    @patch("git.Repo")
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

        result = await git_tool.execute_tool(
            {"operation": "git_show", "repo_path": "/test", "revision": "abc123"}
        )

        assert result["success"]
        assert "abc123" in result["result"]
        assert "Test commit" in result["result"]
        mock_repo.commit.assert_called_once_with("abc123")

    @pytest.mark.asyncio
    async def test_show_missing_revision(self, git_tool):
        """Test show without revision."""
        result = await git_tool.execute_tool(
            {"operation": "git_show", "repo_path": "/test"}
        )

        assert "error" in result
        assert "Missing required parameter: revision" in result["error"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_init_repository(self, mock_repo_class, git_tool):
        """Test git init operation."""
        mock_repo = Mock()
        mock_repo.git_dir = "/test/.git"
        mock_repo_class.init.return_value = mock_repo

        result = await git_tool.execute_tool(
            {"operation": "git_init", "repo_path": "/test/path"}
        )

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
    @patch("git.Repo")
    async def test_git_command_error(self, mock_repo_class, git_tool, mock_repo):
        """Test handling of GitCommandError."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.status.side_effect = GitCommandError(
            "git status", 1, "error message"
        )

        result = await git_tool.execute_tool(
            {"operation": "git_status", "repo_path": "/test"}
        )

        assert not result["success"]
        assert "Git command failed" in result["error"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_diff_with_target(self, mock_repo_class, git_tool, mock_repo):
        """Test git diff with target."""
        mock_repo_class.return_value = mock_repo
        mock_repo.git.diff.return_value = "diff between commits"

        result = await git_tool.execute_tool(
            {"operation": "git_diff", "repo_path": "/test", "target": "HEAD~1"}
        )

        assert result["success"]
        assert "diff between commits" in result["result"]
        mock_repo.git.diff.assert_called_once_with("HEAD~1")

    @pytest.mark.asyncio
    async def test_diff_missing_target(self, git_tool):
        """Test git diff without target."""
        result = await git_tool.execute_tool(
            {"operation": "git_diff", "repo_path": "/test"}
        )

        assert "error" in result
        assert "Missing required parameter: target" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_repo_path(self, git_tool):
        """Test operation without repo_path."""
        result = await git_tool.execute_tool({"operation": "git_status"})

        assert "error" in result
        assert "Missing required parameter: repo_path" in result["error"]

    # Tests for git_query_commits functionality
    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_query_commits_basic(self, mock_repo_class, git_tool, mock_repo):
        """Test basic git query commits operation."""
        mock_repo_class.return_value = mock_repo

        # Create mock commits
        mock_commit1 = Mock()
        mock_commit1.hexsha = "abc123def456"
        mock_commit1.author.name = "John Doe"
        mock_commit1.author.email = "john@example.com"
        mock_commit1.authored_datetime.strftime.return_value = "2023-12-01 10:30:00"
        mock_commit1.message = "Add new feature\n"

        mock_commit2 = Mock()
        mock_commit2.hexsha = "def456ghi789"
        mock_commit2.author.name = "Jane Smith"
        mock_commit2.author.email = "jane@example.com"
        mock_commit2.authored_datetime.strftime.return_value = "2023-11-30 15:45:00"
        mock_commit2.message = "Fix bug in authentication\n"

        mock_repo.iter_commits.return_value = [mock_commit1, mock_commit2]

        result = await git_tool.execute_tool(
            {"operation": "git_query_commits", "repo_path": "/test"}
        )

        assert result["success"]
        assert "Found 2 commit(s)" in result["result"]
        assert "abc123de" in result["result"]  # Short hash
        assert "John Doe <john@example.com>" in result["result"]
        assert "Add new feature" in result["result"]
        assert "def456gh" in result["result"]  # Short hash
        assert "Jane Smith <jane@example.com>" in result["result"]
        assert "Fix bug in authentication" in result["result"]

        # Verify iter_commits was called with default parameters
        mock_repo.iter_commits.assert_called_once_with(
            max_count=100, since=None, until=None, author=None
        )

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_query_commits_with_date_range(
        self, mock_repo_class, git_tool, mock_repo
    ):
        """Test git query commits with date range filtering."""
        mock_repo_class.return_value = mock_repo

        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_commit.author.name = "John Doe"
        mock_commit.author.email = "john@example.com"
        mock_commit.authored_datetime.strftime.return_value = "2023-12-01 10:30:00"
        mock_commit.message = "Recent commit\n"

        mock_repo.iter_commits.return_value = [mock_commit]

        result = await git_tool.execute_tool(
            {
                "operation": "git_query_commits",
                "repo_path": "/test",
                "since_date": "2023-12-01",
                "until_date": "2023-12-31",
            }
        )

        assert result["success"]
        assert "Found 1 commit(s) since 2023-12-01 until 2023-12-31" in result["result"]
        assert "Recent commit" in result["result"]

        mock_repo.iter_commits.assert_called_once_with(
            max_count=100, since="2023-12-01", until="2023-12-31", author=None
        )

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_query_commits_with_author_filter(
        self, mock_repo_class, git_tool, mock_repo
    ):
        """Test git query commits with author filtering."""
        mock_repo_class.return_value = mock_repo

        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_commit.author.name = "John Doe"
        mock_commit.author.email = "john@example.com"
        mock_commit.authored_datetime.strftime.return_value = "2023-12-01 10:30:00"
        mock_commit.message = "John's commit\n"

        mock_repo.iter_commits.return_value = [mock_commit]

        result = await git_tool.execute_tool(
            {
                "operation": "git_query_commits",
                "repo_path": "/test",
                "author": "John Doe",
            }
        )

        assert result["success"]
        assert "Found 1 commit(s) by author 'John Doe'" in result["result"]
        assert "John's commit" in result["result"]

        mock_repo.iter_commits.assert_called_once_with(
            max_count=100, since=None, until=None, author="John Doe"
        )

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_query_commits_with_max_count(
        self, mock_repo_class, git_tool, mock_repo
    ):
        """Test git query commits with custom max count."""
        mock_repo_class.return_value = mock_repo

        # Create 3 mock commits but limit to 2
        mock_commits = []
        for i in range(2):  # Only return 2 commits due to max_count=2
            mock_commit = Mock()
            mock_commit.hexsha = f"commit{i}hash"
            mock_commit.author.name = f"Author {i}"
            mock_commit.author.email = f"author{i}@example.com"
            mock_commit.authored_datetime.strftime.return_value = (
                f"2023-12-0{i+1} 10:30:00"
            )
            mock_commit.message = f"Commit {i}\n"
            mock_commits.append(mock_commit)

        mock_repo.iter_commits.return_value = mock_commits

        result = await git_tool.execute_tool(
            {"operation": "git_query_commits", "repo_path": "/test", "max_count": 2}
        )

        assert result["success"]
        assert "Found 2 commit(s) (max 2 results)" in result["result"]
        assert "Commit 0" in result["result"]
        assert "Commit 1" in result["result"]

        mock_repo.iter_commits.assert_called_once_with(
            max_count=2, since=None, until=None, author=None
        )

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_query_commits_all_filters(
        self, mock_repo_class, git_tool, mock_repo
    ):
        """Test git query commits with all filters applied."""
        mock_repo_class.return_value = mock_repo

        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_commit.author.name = "John Doe"
        mock_commit.author.email = "john@example.com"
        mock_commit.authored_datetime.strftime.return_value = "2023-12-01 10:30:00"
        mock_commit.message = "Filtered commit\n"

        mock_repo.iter_commits.return_value = [mock_commit]

        result = await git_tool.execute_tool(
            {
                "operation": "git_query_commits",
                "repo_path": "/test",
                "since_date": "2023-12-01",
                "until_date": "2023-12-31",
                "author": "John Doe",
                "max_count": 50,
            }
        )

        assert result["success"]
        assert (
            "Found 1 commit(s) since 2023-12-01 until 2023-12-31 by author 'John Doe' (max 50 results)"
            in result["result"]
        )
        assert "Filtered commit" in result["result"]

        mock_repo.iter_commits.assert_called_once_with(
            max_count=50, since="2023-12-01", until="2023-12-31", author="John Doe"
        )

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_query_commits_no_results(self, mock_repo_class, git_tool, mock_repo):
        """Test git query commits when no commits match criteria."""
        mock_repo_class.return_value = mock_repo
        mock_repo.iter_commits.return_value = []

        result = await git_tool.execute_tool(
            {
                "operation": "git_query_commits",
                "repo_path": "/test",
                "author": "NonExistentAuthor",
            }
        )

        assert result["success"]
        assert "No commits found matching the specified criteria" in result["result"]

        mock_repo.iter_commits.assert_called_once_with(
            max_count=100, since=None, until=None, author="NonExistentAuthor"
        )

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_query_commits_only_since_date(
        self, mock_repo_class, git_tool, mock_repo
    ):
        """Test git query commits with only since_date filter."""
        mock_repo_class.return_value = mock_repo

        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_commit.author.name = "John Doe"
        mock_commit.author.email = "john@example.com"
        mock_commit.authored_datetime.strftime.return_value = "2023-12-01 10:30:00"
        mock_commit.message = "Recent commit\n"

        mock_repo.iter_commits.return_value = [mock_commit]

        result = await git_tool.execute_tool(
            {
                "operation": "git_query_commits",
                "repo_path": "/test",
                "since_date": "2023-12-01",
            }
        )

        assert result["success"]
        assert "Found 1 commit(s) since 2023-12-01" in result["result"]
        assert "Recent commit" in result["result"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_query_commits_only_until_date(
        self, mock_repo_class, git_tool, mock_repo
    ):
        """Test git query commits with only until_date filter."""
        mock_repo_class.return_value = mock_repo

        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_commit.author.name = "John Doe"
        mock_commit.author.email = "john@example.com"
        mock_commit.authored_datetime.strftime.return_value = "2023-11-30 10:30:00"
        mock_commit.message = "Old commit\n"

        mock_repo.iter_commits.return_value = [mock_commit]

        result = await git_tool.execute_tool(
            {
                "operation": "git_query_commits",
                "repo_path": "/test",
                "until_date": "2023-11-30",
            }
        )

        assert result["success"]
        assert "Found 1 commit(s) until 2023-11-30" in result["result"]
        assert "Old commit" in result["result"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_query_commits_git_error(self, mock_repo_class, git_tool, mock_repo):
        """Test git query commits with git command error."""
        mock_repo_class.return_value = mock_repo
        mock_repo.iter_commits.side_effect = GitCommandError(
            "git log", 1, "fatal: bad revision"
        )

        result = await git_tool.execute_tool(
            {"operation": "git_query_commits", "repo_path": "/test"}
        )

        assert result["success"]
        assert "Error querying commits" in result["result"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_query_commits_invalid_repo(self, mock_repo_class, git_tool):
        """Test git query commits with invalid repository."""
        mock_repo_class.side_effect = InvalidGitRepositoryError("Not a git repo")

        result = await git_tool.execute_tool(
            {"operation": "git_query_commits", "repo_path": "/invalid"}
        )

        assert not result["success"]
        assert "Invalid Git repository" in result["error"]

    @pytest.mark.asyncio
    async def test_query_commits_missing_repo_path(self, git_tool):
        """Test git query commits without repo_path."""
        result = await git_tool.execute_tool({"operation": "git_query_commits"})

        assert "error" in result
        assert "Missing required parameter: repo_path" in result["error"]

    @pytest.mark.asyncio
    @patch("git.Repo")
    async def test_query_commits_message_formatting(
        self, mock_repo_class, git_tool, mock_repo
    ):
        """Test git query commits message formatting with multiline commit messages."""
        mock_repo_class.return_value = mock_repo

        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_commit.author.name = "John Doe"
        mock_commit.author.email = "john@example.com"
        mock_commit.authored_datetime.strftime.return_value = "2023-12-01 10:30:00"
        mock_commit.message = "Add new feature\n\nThis commit adds a new feature\nwith multiple lines of description\n\n"

        mock_repo.iter_commits.return_value = [mock_commit]

        result = await git_tool.execute_tool(
            {"operation": "git_query_commits", "repo_path": "/test"}
        )

        assert result["success"]
        # Check that the message is properly stripped
        assert (
            "Add new feature\n\nThis commit adds a new feature\nwith multiple lines of description"
            in result["result"]
        )
        # Ensure the formatting separators are present
        assert "=" * 50 in result["result"]
