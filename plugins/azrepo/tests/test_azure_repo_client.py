"""
Tests for the AzureRepoClient class in plugins/azrepo/tool.py.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from ..tool import AzureRepoClient


@pytest.fixture
def azure_repo_client():
    """Create an AzureRepoClient instance for testing."""
    # Mock the command executor to avoid registry dependency
    mock_executor = MagicMock()
    return AzureRepoClient(command_executor=mock_executor)


@pytest.fixture
def mock_command_success_response():
    """Create a mock successful command response."""
    return {
        "success": True,
        "data": {
            "id": 123,
            "title": "Test PR",
            "sourceRefName": "refs/heads/feature/test",
            "targetRefName": "refs/heads/main",
            "status": "active",
        },
    }


@pytest.fixture
def mock_pr_list_response():
    """Create a mock PR list response."""
    return {
        "success": True,
        "data": [
            {
                "pullRequestId": 123,
                "title": "Test PR 1",
                "sourceRefName": "refs/heads/feature/test1",
                "targetRefName": "refs/heads/main",
                "status": "active",
            },
            {
                "pullRequestId": 124,
                "title": "Test PR 2",
                "sourceRefName": "refs/heads/feature/test2",
                "targetRefName": "refs/heads/main",
                "status": "completed",
            },
        ],
    }


class TestAzureRepoClientProperties:
    """Test the ToolInterface properties."""

    def test_name_property(self, azure_repo_client):
        """Test the name property returns correct value."""
        assert azure_repo_client.name == "azure_repo_client"

    def test_description_property(self, azure_repo_client):
        """Test the description property returns correct value."""
        assert (
            azure_repo_client.description
            == "Interact with Azure DevOps repositories and pull requests with automatic configuration loading"
        )

    def test_input_schema_property(self, azure_repo_client):
        """Test the input_schema property returns valid schema."""
        schema = azure_repo_client.input_schema

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "operation" in schema["properties"]
        assert "required" in schema
        assert "operation" in schema["required"]

        # Check that all expected operations are in the enum
        operations = schema["properties"]["operation"]["enum"]
        expected_operations = [
            "list_pull_requests",
            "get_pull_request",
            "create_pull_request",
            "update_pull_request",
            "set_vote",
            "add_reviewers",
            "add_work_items",
            "get_work_item",
        ]
        for op in expected_operations:
            assert op in operations

    def test_creator_parameter_description(self, azure_repo_client):
        """Test that creator parameter has the correct description."""
        schema = azure_repo_client.input_schema
        creator_desc = schema["properties"]["creator"]["description"]
        assert "defaults to current user" in creator_desc
        assert "use empty string to list all PRs" in creator_desc


class TestCurrentUsernameDetection:
    """Test the current username detection functionality."""

    @patch('getpass.getuser')
    def test_get_current_username_success(self, mock_getuser, azure_repo_client):
        """Test successful username detection using getpass.getuser()."""
        mock_getuser.return_value = "testuser"

        username = azure_repo_client._get_current_username()

        assert username == "testuser"
        mock_getuser.assert_called_once()

    @patch('getpass.getuser')
    @patch('os.environ')
    def test_get_current_username_fallback_user(self, mock_environ, mock_getuser, azure_repo_client):
        """Test username detection fallback to USER environment variable."""
        mock_getuser.side_effect = Exception("getuser failed")
        mock_environ.get.side_effect = lambda key: "envuser" if key == "USER" else None

        username = azure_repo_client._get_current_username()

        assert username == "envuser"
        mock_getuser.assert_called_once()
        mock_environ.get.assert_called()

    @patch('getpass.getuser')
    @patch('os.environ')
    def test_get_current_username_fallback_username(self, mock_environ, mock_getuser, azure_repo_client):
        """Test username detection fallback to USERNAME environment variable."""
        mock_getuser.side_effect = Exception("getuser failed")
        mock_environ.get.side_effect = lambda key: "winuser" if key == "USERNAME" else None

        username = azure_repo_client._get_current_username()

        assert username == "winuser"
        mock_getuser.assert_called_once()
        mock_environ.get.assert_called()

    @patch('getpass.getuser')
    @patch('os.environ')
    def test_get_current_username_failure(self, mock_environ, mock_getuser, azure_repo_client):
        """Test username detection failure returns None."""
        mock_getuser.side_effect = Exception("getuser failed")
        mock_environ.get.return_value = None

        username = azure_repo_client._get_current_username()

        assert username is None
        mock_getuser.assert_called_once()


class TestAzureRepoClientCommands:
    """Test the Azure CLI command execution."""

    @pytest.mark.asyncio
    async def test_run_az_command_success(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test successful Azure CLI command execution."""
        # Mock the executor methods
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={
                "success": True,
                "output": json.dumps(mock_command_success_response["data"]),
            }
        )

        result = await azure_repo_client._run_az_command("repos pr list")

        assert result["success"] is True
        assert result["data"] == mock_command_success_response["data"]
        azure_repo_client.executor.execute_async.assert_called_once_with(
            "az repos pr list --output json", None
        )

    @pytest.mark.asyncio
    async def test_run_az_command_failure(self, azure_repo_client):
        """Test Azure CLI command execution failure."""
        # Mock the executor methods to simulate failure
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={"success": False, "error": "Command failed"}
        )

        result = await azure_repo_client._run_az_command("repos pr list")

        assert result["success"] is False
        assert "Command failed" in result["error"]

    @pytest.mark.asyncio
    async def test_run_az_command_json_parse_error(self, azure_repo_client):
        """Test Azure CLI command with invalid JSON response."""
        # Mock the executor methods to return invalid JSON
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={"success": True, "output": "invalid json"}
        )

        result = await azure_repo_client._run_az_command("repos pr list")

        assert result["success"] is False
        assert "Failed to parse JSON output" in result["error"]


class TestListPullRequests:
    """Test the list_pull_requests method."""

    @pytest.mark.asyncio
    async def test_list_pull_requests_basic(
        self, azure_repo_client, mock_pr_list_response
    ):
        """Test basic pull request listing."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_pr_list_response
        )

        result = await azure_repo_client.list_pull_requests()

        azure_repo_client._run_az_command.assert_called_once_with("repos pr list")
        assert result == mock_pr_list_response

    @pytest.mark.asyncio
    async def test_list_pull_requests_with_filters(
        self, azure_repo_client, mock_pr_list_response
    ):
        """Test pull request listing with filters."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_pr_list_response
        )

        result = await azure_repo_client.list_pull_requests(
            repository="test-repo",
            project="test-project",
            status="active",
            creator="test-user",
            top=10,
        )

        expected_command = "repos pr list --repository test-repo --project test-project --creator test-user --status active --top 10"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_pr_list_response


class TestListPullRequestsCreatorBehavior:
    """Test the creator parameter behavior in list_pull_requests method."""

    @pytest.mark.asyncio
    @patch.object(AzureRepoClient, '_get_current_username')
    async def test_list_pull_requests_default_creator(
        self, mock_get_username, azure_repo_client, mock_pr_list_response
    ):
        """Test that default creator parameter uses current user."""
        mock_get_username.return_value = "currentuser"
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_pr_list_response
        )

        # Call with default creator parameter
        result = await azure_repo_client.list_pull_requests()

        expected_command = "repos pr list --creator currentuser"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_pr_list_response
        mock_get_username.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(AzureRepoClient, '_get_current_username')
    async def test_list_pull_requests_default_creator_no_username(
        self, mock_get_username, azure_repo_client, mock_pr_list_response
    ):
        """Test default creator behavior when username cannot be detected."""
        mock_get_username.return_value = None
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_pr_list_response
        )

        # Call with default creator parameter
        result = await azure_repo_client.list_pull_requests()

        # Should not include creator filter if username detection fails
        expected_command = "repos pr list"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_pr_list_response
        mock_get_username.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_pull_requests_explicit_none_creator(
        self, azure_repo_client, mock_pr_list_response
    ):
        """Test that explicit None creator lists all PRs."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_pr_list_response
        )

        result = await azure_repo_client.list_pull_requests(creator=None)

        # Should not include creator filter
        expected_command = "repos pr list"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_pr_list_response

    @pytest.mark.asyncio
    async def test_list_pull_requests_explicit_empty_creator(
        self, azure_repo_client, mock_pr_list_response
    ):
        """Test that explicit empty string creator lists all PRs."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_pr_list_response
        )

        result = await azure_repo_client.list_pull_requests(creator="")

        # Should not include creator filter
        expected_command = "repos pr list"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_pr_list_response

    @pytest.mark.asyncio
    async def test_list_pull_requests_explicit_username_creator(
        self, azure_repo_client, mock_pr_list_response
    ):
        """Test that explicit username creator filters by that user."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_pr_list_response
        )

        result = await azure_repo_client.list_pull_requests(creator="specificuser")

        expected_command = "repos pr list --creator specificuser"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_pr_list_response

    @pytest.mark.asyncio
    @patch.object(AzureRepoClient, '_get_current_username')
    async def test_list_pull_requests_default_with_other_params(
        self, mock_get_username, azure_repo_client, mock_pr_list_response
    ):
        """Test default creator behavior with other parameters."""
        mock_get_username.return_value = "currentuser"
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_pr_list_response
        )

        result = await azure_repo_client.list_pull_requests(
            repository="test-repo",
            status="active",
            top=5
        )

        expected_command = "repos pr list --repository test-repo --creator currentuser --status active --top 5"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_pr_list_response
        mock_get_username.assert_called_once()


class TestGetPullRequest:
    """Test the get_pull_request method."""

    @pytest.mark.asyncio
    async def test_get_pull_request_basic(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test getting a specific pull request."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.get_pull_request(123)

        azure_repo_client._run_az_command.assert_called_once_with(
            "repos pr show --id 123"
        )
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_get_pull_request_with_org(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test getting a pull request with organization."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.get_pull_request(
            123, organization="https://dev.azure.com/myorg"
        )

        expected_command = "repos pr show --id 123 --org https://dev.azure.com/myorg"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response


class TestCreatePullRequest:
    """Test the create_pull_request method."""

    @pytest.mark.asyncio
    async def test_create_pull_request_basic(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test creating a basic pull request."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.create_pull_request(
            title="Test PR", source_branch="feature/test"
        )

        expected_command = (
            'repos pr create --title "Test PR" --source-branch feature/test'
        )
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_create_pull_request_full_options(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test creating a pull request with all options."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.create_pull_request(
            title="Test PR",
            source_branch="feature/test",
            target_branch="main",
            description="Test description",
            repository="test-repo",
            project="test-project",
            reviewers=["user1", "user2"],
            work_items=[123, 456],
            draft=True,
            auto_complete=True,
            squash=True,
            delete_source_branch=True,
        )

        expected_command = (
            'repos pr create --title "Test PR" --source-branch feature/test '
            '--target-branch main --description "Test description" '
            "--repository test-repo --project test-project "
            "--reviewers user1 --reviewers user2 --work-items 123 --work-items 456 "
            "--draft --auto-complete --squash --delete-source-branch"
        )
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response


class TestUpdatePullRequest:
    """Test the update_pull_request method."""

    @pytest.mark.asyncio
    async def test_update_pull_request_basic(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test updating a pull request."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.update_pull_request(
            pull_request_id=123, title="Updated Title"
        )

        expected_command = 'repos pr update --id 123 --title "Updated Title"'
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_update_pull_request_with_flags(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test updating a pull request with boolean flags."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.update_pull_request(
            pull_request_id=123, auto_complete=True, squash=False, draft=True
        )

        expected_command = (
            "repos pr update --id 123 --auto-complete true --squash false --draft true"
        )
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response


class TestVotingAndReviewers:
    """Test voting and reviewer management methods."""

    @pytest.mark.asyncio
    async def test_set_vote(self, azure_repo_client, mock_command_success_response):
        """Test setting a vote on a pull request."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.set_vote(123, "approve")

        expected_command = "repos pr set-vote --id 123 --vote approve"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_add_reviewers(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test adding reviewers to a pull request."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.add_reviewers(123, ["user1", "user2"])

        expected_command = (
            "repos pr reviewer add --id 123 --reviewers user1 --reviewers user2"
        )
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_add_work_items(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test adding work items to a pull request."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.add_work_items(123, [456, 789])

        expected_command = (
            "repos pr work-item add --id 123 --work-items 456 --work-items 789"
        )
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response


class TestWorkItems:
    """Test work item management methods."""

    @pytest.mark.asyncio
    async def test_get_work_item_basic(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test getting a work item with basic parameters."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.get_work_item(123)

        expected_command = "boards work-item show --id 123"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_get_work_item_with_all_options(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test getting a work item with all optional parameters."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.get_work_item(
            work_item_id=123,
            organization="https://dev.azure.com/myorg",
            project="myproject",
            as_of="2023-01-01",
            expand="all",
            fields="System.Id,System.Title,System.State",
        )

        expected_command = (
            "boards work-item show --id 123 --org https://dev.azure.com/myorg "
            "--project myproject --as-of '2023-01-01' --expand all "
            "--fields System.Id,System.Title,System.State"
        )
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_get_work_item_with_defaults(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test getting a work item using configured defaults."""
        # Set up defaults
        azure_repo_client.default_organization = "https://dev.azure.com/defaultorg"
        azure_repo_client.default_project = "defaultproject"

        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.get_work_item(456)

        expected_command = (
            "boards work-item show --id 456 --org https://dev.azure.com/defaultorg "
            "--project defaultproject"
        )
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response


class TestExecuteTool:
    """Test the execute_tool method."""

    @pytest.mark.asyncio
    @patch.object(AzureRepoClient, '_get_current_username')
    async def test_execute_tool_list_pull_requests_default_creator(
        self, mock_get_username, azure_repo_client, mock_pr_list_response
    ):
        """Test execute_tool with list_pull_requests operation using default creator."""
        mock_get_username.return_value = "currentuser"
        azure_repo_client.list_pull_requests = AsyncMock(
            return_value=mock_pr_list_response
        )

        arguments = {
            "operation": "list_pull_requests",
            "repository": "test-repo",
            "status": "active",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.list_pull_requests.assert_called_once_with(
            repository="test-repo",
            project=None,
            organization=None,
            creator="default",  # Should use "default" when not specified
            reviewer=None,
            status="active",
            source_branch=None,
            target_branch=None,
            top=None,
            skip=None,
        )
        assert result == mock_pr_list_response

    @pytest.mark.asyncio
    async def test_execute_tool_list_pull_requests_explicit_creator(
        self, azure_repo_client, mock_pr_list_response
    ):
        """Test execute_tool with list_pull_requests operation and explicit creator."""
        azure_repo_client.list_pull_requests = AsyncMock(
            return_value=mock_pr_list_response
        )

        arguments = {
            "operation": "list_pull_requests",
            "repository": "test-repo",
            "creator": "specificuser",
            "status": "active",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.list_pull_requests.assert_called_once_with(
            repository="test-repo",
            project=None,
            organization=None,
            creator="specificuser",  # Should use the explicitly provided creator
            reviewer=None,
            status="active",
            source_branch=None,
            target_branch=None,
            top=None,
            skip=None,
        )
        assert result == mock_pr_list_response

    @pytest.mark.asyncio
    async def test_execute_tool_list_pull_requests_none_creator(
        self, azure_repo_client, mock_pr_list_response
    ):
        """Test execute_tool with list_pull_requests operation and None creator."""
        azure_repo_client.list_pull_requests = AsyncMock(
            return_value=mock_pr_list_response
        )

        arguments = {
            "operation": "list_pull_requests",
            "repository": "test-repo",
            "creator": None,
            "status": "active",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.list_pull_requests.assert_called_once_with(
            repository="test-repo",
            project=None,
            organization=None,
            creator=None,  # Should use None when explicitly provided
            reviewer=None,
            status="active",
            source_branch=None,
            target_branch=None,
            top=None,
            skip=None,
        )
        assert result == mock_pr_list_response

    @pytest.mark.asyncio
    async def test_execute_tool_get_pull_request(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool with get_pull_request operation."""
        azure_repo_client.get_pull_request = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "get_pull_request",
            "pull_request_id": 123,
            "organization": "https://dev.azure.com/myorg",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.get_pull_request.assert_called_once_with(
            pull_request_id=123, organization="https://dev.azure.com/myorg"
        )
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_execute_tool_create_pull_request(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool with create_pull_request operation."""
        azure_repo_client.create_pull_request = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "create_pull_request",
            "title": "Test PR",
            "source_branch": "feature/test",
            "target_branch": "main",
            "draft": True,
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.create_pull_request.assert_called_once_with(
            title="Test PR",
            source_branch="feature/test",
            target_branch="main",
            description=None,
            repository=None,
            project=None,
            organization=None,
            reviewers=None,
            work_items=None,
            draft=True,
            auto_complete=False,
            squash=False,
            delete_source_branch=False,
        )
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_execute_tool_get_work_item(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool with get_work_item operation."""
        azure_repo_client.get_work_item = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "get_work_item",
            "work_item_id": 123,
            "organization": "https://dev.azure.com/myorg",
            "project": "myproject",
            "expand": "all",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.get_work_item.assert_called_once_with(
            work_item_id=123,
            organization="https://dev.azure.com/myorg",
            project="myproject",
            as_of=None,
            expand="all",
            fields=None,
        )
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_operation(self, azure_repo_client):
        """Test execute_tool with unknown operation."""
        arguments = {"operation": "unknown_operation"}
        result = await azure_repo_client.execute_tool(arguments)

        assert result["success"] is False
        assert "Unknown operation: unknown_operation" in result["error"]


class TestInitialization:
    """Test client initialization."""

    def test_init_with_executor(self):
        """Test initialization with provided executor."""
        mock_executor = MagicMock()
        client = AzureRepoClient(command_executor=mock_executor)
        assert client.executor == mock_executor

    @patch("mcp_tools.plugin.registry")
    def test_init_without_executor_success(self, mock_registry):
        """Test initialization without executor (registry lookup success)."""
        mock_executor = MagicMock()
        mock_registry.get_tool_instance.return_value = mock_executor

        client = AzureRepoClient()

        mock_registry.get_tool_instance.assert_called_once_with("command_executor")
        assert client.executor == mock_executor

    @patch("mcp_tools.plugin.registry")
    def test_init_without_executor_failure(self, mock_registry):
        """Test initialization without executor (registry lookup failure)."""
        mock_registry.get_tool_instance.return_value = None

        with pytest.raises(ValueError, match="Command executor not found in registry"):
            AzureRepoClient()


class TestCreatorIntegration:
    """Integration tests for creator functionality."""

    @pytest.mark.asyncio
    @patch.object(AzureRepoClient, '_get_current_username')
    async def test_end_to_end_default_creator_workflow(
        self, mock_get_username, azure_repo_client
    ):
        """Test end-to-end workflow with default creator behavior."""
        mock_get_username.return_value = "testuser"

        # Mock the command execution
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={
                "success": True,
                "output": json.dumps([
                    {
                        "pullRequestId": 123,
                        "title": "My PR",
                        "createdBy": {"displayName": "testuser"},
                        "status": "active"
                    }
                ])
            }
        )

        # Test via execute_tool interface
        result = await azure_repo_client.execute_tool({
            "operation": "list_pull_requests",
            "status": "active"
        })

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["title"] == "My PR"

        # Verify the command included the current user as creator
        azure_repo_client.executor.execute_async.assert_called_once()
        command_call = azure_repo_client.executor.execute_async.call_args[0][0]
        assert "--creator testuser" in command_call
        assert "--status active" in command_call

    @pytest.mark.asyncio
    async def test_end_to_end_explicit_none_creator_workflow(self, azure_repo_client):
        """Test end-to-end workflow with explicit None creator."""
        # Mock the command execution
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={
                "success": True,
                "output": json.dumps([
                    {
                        "pullRequestId": 123,
                        "title": "Someone's PR",
                        "createdBy": {"displayName": "otheruser"},
                        "status": "active"
                    },
                    {
                        "pullRequestId": 124,
                        "title": "My PR",
                        "createdBy": {"displayName": "testuser"},
                        "status": "active"
                    }
                ])
            }
        )

        # Test via execute_tool interface with explicit None creator
        result = await azure_repo_client.execute_tool({
            "operation": "list_pull_requests",
            "creator": None,
            "status": "active"
        })

        assert result["success"] is True
        assert len(result["data"]) == 2  # Should get all PRs

        # Verify the command did NOT include a creator filter
        azure_repo_client.executor.execute_async.assert_called_once()
        command_call = azure_repo_client.executor.execute_async.call_args[0][0]
        assert "--creator" not in command_call
        assert "--status active" in command_call
