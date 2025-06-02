"""
Tests for the AzureRepoClient class in plugins/azrepo/tool.py.
"""

import pytest
import json
import pandas as pd
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
                "createdBy": {
                    "displayName": "John Doe",
                    "uniqueName": "john.doe@abc.com"
                },
                "creationDate": "2024-01-15T10:30:00.000Z"
            },
            {
                "pullRequestId": 124,
                "title": "Test PR 2",
                "sourceRefName": "refs/heads/feature/test2",
                "targetRefName": "refs/heads/main",
                "status": "completed",
                "createdBy": {
                    "displayName": "Jane Smith",
                    "uniqueName": "jane.smith@abc.com"
                },
                "creationDate": "2024-01-14T15:45:00.000Z"
            },
        ],
    }


@pytest.fixture
def mock_pr_list_response_with_csv_fields():
    """Create a mock PR list response with all fields needed for CSV conversion."""
    return {
        "success": True,
        "data": [
            {
                "pullRequestId": 123,
                "title": "Test PR 1",
                "sourceRefName": "refs/heads/feature/test1",
                "targetRefName": "refs/heads/main",
                "status": "active",
                "createdBy": {
                    "displayName": "John Doe",
                    "uniqueName": "john.doe@abc.com"
                },
                "creationDate": "2024-01-15T10:30:00.000Z"
            },
            {
                "pullRequestId": 124,
                "title": "Test PR 2",
                "sourceRefName": "refs/heads/feature/test2",
                "targetRefName": "refs/heads/main",
                "status": "completed",
                "createdBy": {
                    "displayName": "Jane Smith",
                    "uniqueName": "jane.smith@abc.com"
                },
                "creationDate": "2024-01-14T15:45:00.000Z"
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

        # Should include current user as creator by default
        azure_repo_client._run_az_command.assert_called_once()
        command_called = azure_repo_client._run_az_command.call_args[0][0]
        assert "repos pr list" in command_called
        assert "--creator" in command_called

        # Should return CSV data
        assert result["success"] is True
        assert isinstance(result["data"], str)
        assert "id,creator,date,title,source_ref,target_ref" in result["data"]

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

        # Should return CSV data
        assert result["success"] is True
        assert isinstance(result["data"], str)
        assert "id,creator,date,title,source_ref,target_ref" in result["data"]


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

        # Should return CSV data
        assert result["success"] is True
        assert isinstance(result["data"], str)
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

        # Should return CSV data
        assert result["success"] is True
        assert isinstance(result["data"], str)
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

        # Should return CSV data
        assert result["success"] is True
        assert isinstance(result["data"], str)

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

        # Should return CSV data
        assert result["success"] is True
        assert isinstance(result["data"], str)

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

        # Should return CSV data
        assert result["success"] is True
        assert isinstance(result["data"], str)

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

        # Should return CSV data
        assert result["success"] is True
        assert isinstance(result["data"], str)
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
            as_of="2023-01-01",
            expand="all",
            fields="System.Id,System.Title,System.State",
        )

        expected_command = (
            "boards work-item show --id 123 --org https://dev.azure.com/myorg "
            "--as-of '2023-01-01' --expand all "
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

        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_repo_client.get_work_item(456)

        expected_command = (
            "boards work-item show --id 456 --org https://dev.azure.com/defaultorg"
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
            "expand": "all",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.get_work_item.assert_called_once_with(
            work_item_id=123,
            organization="https://dev.azure.com/myorg",
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
                        "createdBy": {"displayName": "testuser", "uniqueName": "testuser@abc.com"},
                        "status": "active",
                        "sourceRefName": "refs/heads/feature/test",
                        "targetRefName": "refs/heads/main",
                        "creationDate": "2024-01-15T10:30:00.000Z"
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
        assert isinstance(result["data"], str)
        assert "My PR" in result["data"]

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
                        "createdBy": {"displayName": "otheruser", "uniqueName": "otheruser@abc.com"},
                        "status": "active",
                        "sourceRefName": "refs/heads/feature/other",
                        "targetRefName": "refs/heads/main",
                        "creationDate": "2024-01-15T10:30:00.000Z"
                    },
                    {
                        "pullRequestId": 124,
                        "title": "My PR",
                        "createdBy": {"displayName": "testuser", "uniqueName": "testuser@abc.com"},
                        "status": "active",
                        "sourceRefName": "refs/heads/feature/test",
                        "targetRefName": "refs/heads/main",
                        "creationDate": "2024-01-14T15:45:00.000Z"
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
        assert isinstance(result["data"], str)
        assert "Someone's PR" in result["data"] and "My PR" in result["data"]

        # Verify the command did NOT include a creator filter
        azure_repo_client.executor.execute_async.assert_called_once()
        command_call = azure_repo_client.executor.execute_async.call_args[0][0]
        assert "--creator" not in command_call
        assert "--status active" in command_call


class TestConvertPrToDf:
    """Test the convert_pr_to_df method."""

    def test_convert_pr_to_df_basic(self, azure_repo_client):
        """Test basic PR to DataFrame conversion."""
        prs_data = [
            {
                "pullRequestId": 123,
                "title": "Test PR 1",
                "sourceRefName": "refs/heads/feature/test1",
                "targetRefName": "refs/heads/main",
                "createdBy": {
                    "displayName": "John Doe",
                    "uniqueName": "john.doe@abc.com"
                },
                "creationDate": "2024-01-15T10:30:00.000Z"
            },
            {
                "pullRequestId": 124,
                "title": "Test PR 2",
                "sourceRefName": "refs/heads/feature/test2",
                "targetRefName": "refs/heads/main",
                "createdBy": {
                    "displayName": "Jane Smith",
                    "uniqueName": "jane.smith@abc.com"
                },
                "creationDate": "2024-01-14T15:45:00.000Z"
            }
        ]

        df = azure_repo_client.convert_pr_to_df(prs_data)

        # Check DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ['id', 'creator', 'date', 'title', 'source_ref', 'target_ref']

        # Check first row data
        assert df.iloc[0]['id'] == 123
        assert df.iloc[0]['creator'] == 'john.doe@abc.com'
        assert df.iloc[0]['title'] == 'Test PR 1'
        assert df.iloc[0]['source_ref'] == 'feature/test1'
        assert df.iloc[0]['target_ref'] == 'main'

        # Check second row data
        assert df.iloc[1]['id'] == 124
        assert df.iloc[1]['creator'] == 'jane.smith@abc.com'
        assert df.iloc[1]['title'] == 'Test PR 2'
        assert df.iloc[1]['source_ref'] == 'feature/test2'
        assert df.iloc[1]['target_ref'] == 'main'

    def test_convert_pr_to_df_empty_list(self, azure_repo_client):
        """Test conversion with empty PR list."""
        df = azure_repo_client.convert_pr_to_df([])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == ['id', 'creator', 'date', 'title', 'source_ref', 'target_ref']

    def test_convert_pr_to_df_removes_refs_prefix(self, azure_repo_client):
        """Test that refs/heads/ prefix is properly removed from branch names."""
        prs_data = [
            {
                "pullRequestId": 123,
                "title": "Test PR",
                "sourceRefName": "refs/heads/feature/complex-branch-name",
                "targetRefName": "refs/heads/develop",
                "createdBy": {
                    "uniqueName": "test.user@abc.com"
                },
                "creationDate": "2024-01-15T10:30:00.000Z"
            }
        ]

        df = azure_repo_client.convert_pr_to_df(prs_data)

        assert df.iloc[0]['source_ref'] == 'feature/complex-branch-name'
        assert df.iloc[0]['target_ref'] == 'develop'

    def test_convert_pr_to_df_preserves_full_email(self, azure_repo_client):
        """Test that full email addresses are preserved in creator names."""
        prs_data = [
            {
                "pullRequestId": 123,
                "title": "Test PR",
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "createdBy": {
                    "uniqueName": "test.user@abc.com"
                },
                "creationDate": "2024-01-15T10:30:00.000Z"
            }
        ]

        df = azure_repo_client.convert_pr_to_df(prs_data)

        assert df.iloc[0]['creator'] == 'test.user@abc.com'

    def test_convert_pr_to_df_date_formatting(self, azure_repo_client):
        """Test that dates are properly formatted."""
        prs_data = [
            {
                "pullRequestId": 123,
                "title": "Test PR",
                "sourceRefName": "refs/heads/feature/test",
                "targetRefName": "refs/heads/main",
                "createdBy": {
                    "uniqueName": "test.user@abc.com"
                },
                "creationDate": "2024-01-15T10:30:45.123Z"
            }
        ]

        df = azure_repo_client.convert_pr_to_df(prs_data)

        # Check that date is formatted as expected (MM/dd/yy HH:MM:SS)
        date_str = df.iloc[0]['date']
        assert isinstance(date_str, str)
        # The exact format depends on timezone, but should be in MM/dd/yy HH:MM:SS format
        assert len(date_str.split(' ')) == 2  # Should have date and time parts
        assert '/' in date_str  # Should have date separators
        assert ':' in date_str  # Should have time separators


class TestListPullRequestsWithCsv:
    """Test the updated list_pull_requests method that returns CSV data."""

    @pytest.mark.asyncio
    async def test_list_pull_requests_returns_csv(
        self, azure_repo_client, mock_pr_list_response_with_csv_fields
    ):
        """Test that list_pull_requests returns CSV data when successful."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_pr_list_response_with_csv_fields
        )

        result = await azure_repo_client.list_pull_requests()

        assert result["success"] is True
        assert "data" in result

        # Check that data is CSV string
        csv_data = result["data"]
        assert isinstance(csv_data, str)

        # Check CSV headers
        lines = csv_data.strip().split('\n')
        headers = lines[0]
        assert headers == "id,creator,date,title,source_ref,target_ref"

        # Check that we have data rows
        assert len(lines) == 3  # Header + 2 data rows

        # Check first data row
        first_row = lines[1].split(',')
        assert first_row[0] == '123'  # id
        assert first_row[1] == 'john.doe@abc.com'  # creator
        assert 'Test PR 1' in first_row[3]  # title
        assert first_row[4] == 'feature/test1'  # source_ref
        assert first_row[5] == 'main'  # target_ref

    @pytest.mark.asyncio
    async def test_list_pull_requests_csv_conversion_failure(self, azure_repo_client):
        """Test list_pull_requests when CSV conversion fails."""
        # Mock _run_az_command to return data that will cause conversion to fail
        mock_response = {
            "success": True,
            "data": [
                {
                    # Missing required fields for conversion
                    "pullRequestId": 123,
                    "title": "Test PR"
                    # Missing pullRequestId, createdBy, etc.
                }
            ]
        }
        azure_repo_client._run_az_command = AsyncMock(return_value=mock_response)

        result = await azure_repo_client.list_pull_requests()

        assert result["success"] is False
        assert "Failed to convert PRs to CSV" in result["error"]

    @pytest.mark.asyncio
    async def test_list_pull_requests_empty_data_returns_empty_csv(self, azure_repo_client):
        """Test list_pull_requests with empty data returns empty CSV."""
        mock_response = {
            "success": True,
            "data": []
        }
        azure_repo_client._run_az_command = AsyncMock(return_value=mock_response)

        result = await azure_repo_client.list_pull_requests()

        assert result["success"] is True
        csv_data = result["data"]

        # Should have headers but no data rows
        lines = csv_data.strip().split('\n')
        assert len(lines) == 1  # Only header row
        assert lines[0] == "id,creator,date,title,source_ref,target_ref"

    @pytest.mark.asyncio
    async def test_list_pull_requests_command_failure_returns_original_error(self, azure_repo_client):
        """Test that command failures are passed through unchanged."""
        mock_response = {
            "success": False,
            "error": "Azure CLI command failed"
        }
        azure_repo_client._run_az_command = AsyncMock(return_value=mock_response)

        result = await azure_repo_client.list_pull_requests()

        assert result["success"] is False
        assert result["error"] == "Azure CLI command failed"

    @pytest.mark.asyncio
    async def test_list_pull_requests_no_data_field_returns_original(self, azure_repo_client):
        """Test that responses without data field are returned unchanged."""
        mock_response = {
            "success": True,
            "message": "No pull requests found"
        }
        azure_repo_client._run_az_command = AsyncMock(return_value=mock_response)

        result = await azure_repo_client.list_pull_requests()

        assert result == mock_response


class TestExecuteToolWithCsv:
    """Test the execute_tool method with CSV functionality."""

    @pytest.mark.asyncio
    async def test_execute_tool_list_pull_requests_returns_csv(
        self, azure_repo_client, mock_pr_list_response_with_csv_fields
    ):
        """Test execute_tool with list_pull_requests returns CSV data."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_pr_list_response_with_csv_fields
        )

        arguments = {
            "operation": "list_pull_requests",
            "repository": "test-repo",
            "status": "active",
        }
        result = await azure_repo_client.execute_tool(arguments)

        assert result["success"] is True
        assert isinstance(result["data"], str)

        # Verify it's CSV format
        csv_lines = result["data"].strip().split('\n')
        assert csv_lines[0] == "id,creator,date,title,source_ref,target_ref"
        assert len(csv_lines) == 3  # Header + 2 data rows

    @pytest.mark.asyncio
    async def test_execute_tool_list_pull_requests_csv_error(self, azure_repo_client):
        """Test execute_tool when CSV conversion fails."""
        # Mock response with invalid data for CSV conversion
        mock_response = {
            "success": True,
            "data": [{"invalid": "data"}]
        }
        azure_repo_client._run_az_command = AsyncMock(return_value=mock_response)

        arguments = {"operation": "list_pull_requests"}
        result = await azure_repo_client.execute_tool(arguments)

        assert result["success"] is False
        assert "Failed to convert PRs to CSV" in result["error"]


class TestCsvIntegration:
    """Integration tests for CSV functionality."""

    @pytest.mark.asyncio
    async def test_end_to_end_csv_workflow(self, azure_repo_client):
        """Test complete end-to-end CSV workflow."""
        # Mock the Azure CLI command execution
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={
                "success": True,
                "output": json.dumps([
                    {
                        "pullRequestId": 123,
                        "title": "Fix authentication bug",
                        "sourceRefName": "refs/heads/feature/auth-fix",
                        "targetRefName": "refs/heads/main",
                        "createdBy": {
                            "uniqueName": "john.doe@abc.com"
                        },
                        "creationDate": "2024-01-15T10:30:00.000Z"
                    },
                    {
                        "pullRequestId": 124,
                        "title": "Add new feature",
                        "sourceRefName": "refs/heads/feature/new-feature",
                        "targetRefName": "refs/heads/develop",
                        "createdBy": {
                            "uniqueName": "jane.smith@abc.com"
                        },
                        "creationDate": "2024-01-14T15:45:00.000Z"
                    }
                ])
            }
        )

        # Execute via the tool interface
        result = await azure_repo_client.execute_tool({
            "operation": "list_pull_requests",
            "status": "active"
        })

        # Verify successful CSV response
        assert result["success"] is True
        csv_data = result["data"]

        # Parse and verify CSV content
        lines = csv_data.strip().split('\n')
        assert len(lines) == 3  # Header + 2 data rows

        # Verify header
        assert lines[0] == "id,creator,date,title,source_ref,target_ref"

        # Verify data content (basic checks)
        assert "123" in lines[1]
        assert "john.doe@abc.com" in lines[1]
        assert "Fix authentication bug" in lines[1]
        assert "feature/auth-fix" in lines[1]
        assert "main" in lines[1]

        assert "124" in lines[2]
        assert "jane.smith@abc.com" in lines[2]
        assert "Add new feature" in lines[2]
        assert "feature/new-feature" in lines[2]
        assert "develop" in lines[2]

    @pytest.mark.asyncio
    async def test_csv_with_special_characters_in_title(self, azure_repo_client):
        """Test CSV handling with special characters in PR titles."""
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={
                "success": True,
                "output": json.dumps([
                    {
                        "pullRequestId": 123,
                        "title": "Fix bug with \"quotes\" and, commas",
                        "sourceRefName": "refs/heads/feature/bug-fix",
                        "targetRefName": "refs/heads/main",
                        "createdBy": {
                            "uniqueName": "test.user@abc.com"
                        },
                        "creationDate": "2024-01-15T10:30:00.000Z"
                    }
                ])
            }
        )

        result = await azure_repo_client.execute_tool({
            "operation": "list_pull_requests"
        })

        assert result["success"] is True
        csv_data = result["data"]

        # Verify that CSV properly handles special characters
        # pandas.to_csv() should properly escape quotes and commas
        assert "Fix bug with \"quotes\" and, commas" in csv_data or \
               "\"Fix bug with \"\"quotes\"\" and, commas\"" in csv_data
