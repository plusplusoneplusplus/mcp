import pytest
from unittest.mock import patch, MagicMock

from plugins.github_cli.github_cli_tool import GithubCliTool


@pytest.fixture
def gh_tool():
    return GithubCliTool()


class TestGithubCliTool:
    def test_properties(self, gh_tool):
        assert gh_tool.name == "github_cli"
        assert "gh CLI" in gh_tool.description
        schema = gh_tool.input_schema
        assert schema["type"] == "object"
        assert "operation" in schema["properties"]

    @pytest.mark.asyncio
    @patch("plugins.github_cli.github_cli_tool.subprocess.run")
    async def test_auth_status_success(self, mock_run, gh_tool):
        process = MagicMock()
        process.returncode = 0
        process.stdout = "Logged in"
        mock_run.return_value = process

        result = await gh_tool.execute_tool({"operation": "auth_status"})

        assert result["success"]
        assert "Logged in" in result["result"]
        mock_run.assert_called_once()

    @pytest.mark.asyncio
    @patch("plugins.github_cli.github_cli_tool.subprocess.run")
    async def test_auth_status_failure(self, mock_run, gh_tool):
        process = MagicMock()
        process.returncode = 1
        process.stderr = "Not logged in"
        mock_run.return_value = process

        result = await gh_tool.execute_tool({"operation": "auth_status"})

        assert not result["success"]
        assert "Not logged in" in result["error"]
        mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_issue_create_missing_params(self, gh_tool):
        result = await gh_tool.execute_tool({"operation": "issue_create"})
        assert "error" in result
        assert "title" in result["error"]

    @pytest.mark.asyncio
    @patch("plugins.github_cli.github_cli_tool.subprocess.run")
    async def test_pr_create_builds_command(self, mock_run, gh_tool):
        process = MagicMock()
        process.returncode = 0
        process.stdout = "PR created"
        mock_run.return_value = process

        await gh_tool.execute_tool(
            {
                "operation": "pr_create",
                "title": "Add feature",
                "body": "details",
                "base": "main",
                "head": "feature",
            }
        )

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[:2] == ["gh", "pr"]
        assert "--base" in args and "--head" in args
