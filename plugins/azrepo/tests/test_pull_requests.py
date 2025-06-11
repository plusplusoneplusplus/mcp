"""
Tests for pull request operations.
"""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from ..pr_tool import AzurePullRequestTool


@pytest.fixture
def mock_aiohttp_get():
    """Fixture to mock aiohttp.ClientSession.get."""

    async def _mock_json():
        return {
            "value": [
                {
                    "pullRequestId": 123,
                    "title": "Test PR 1",
                    "sourceRefName": "refs/heads/feature/test1",
                    "targetRefName": "refs/heads/main",
                    "status": "active",
                    "createdBy": {
                        "displayName": "John Doe",
                        "uniqueName": "john.doe@abc.com",
                    },
                    "creationDate": "2024-01-15T10:30:00.000Z",
                }
            ]
        }

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(side_effect=_mock_json)
    mock_response.text = AsyncMock(return_value="Success")

    # This is the async context manager
    async_get_mock = AsyncMock()
    async_get_mock.__aenter__.return_value = mock_response
    async_get_mock.__aexit__.return_value = None
    return async_get_mock


class TestListPullRequestsAPI:
    """Test the list_pull_requests method using the REST API."""

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_list_pull_requests_basic(
        self, mock_auth_headers, mock_get, azure_pr_tool, mock_pr_list_response
    ):
        """Test basic pull request listing via REST API."""
        # Setup mock response for aiohttp
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"value": mock_pr_list_response["data"]}
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with patch.object(
            azure_pr_tool, "_get_current_username", return_value="test.user@company.com"
        ):
            result = await azure_pr_tool.list_pull_requests()

            mock_get.assert_called_once()
            call_args, call_kwargs = mock_get.call_args
            assert "pullrequests" in call_args[0]
            params = call_kwargs["params"]
            assert params["searchCriteria.creatorId"] == "test.user@company.com"
            assert "searchCriteria.status" not in params

            assert result["success"] is True
            assert "id,creator,date,title,source_ref,target_ref" in result["data"]

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_list_pull_requests_with_filters(
        self, mock_auth_headers, mock_get, azure_pr_tool, mock_pr_list_response
    ):
        """Test pull request listing with filters via REST API."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"value": mock_pr_list_response["data"]}
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        await azure_pr_tool.list_pull_requests(
            status="active",
            creator="test-creator",
            reviewer="test-reviewer",
            source_branch="feature/branch",
            target_branch="main",
            top=20,
            skip=5,
        )

        mock_get.assert_called_once()
        call_args, call_kwargs = mock_get.call_args
        params = call_kwargs["params"]

        assert params["searchCriteria.status"] == "active"
        assert params["searchCriteria.creatorId"] == "test-creator"
        assert params["searchCriteria.reviewerId"] == "test-reviewer"
        assert params["searchCriteria.sourceRefName"] == "refs/heads/feature/branch"
        assert params["searchCriteria.targetRefName"] == "refs/heads/main"
        assert params["$top"] == 20
        assert params["$skip"] == 5

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_list_pull_requests_api_failure(
        self, mock_auth_headers, mock_get, azure_pr_tool
    ):
        """Test handling of API failure during pull request listing."""
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text.return_value = "Authentication failed"
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.list_pull_requests()

        assert result["success"] is False
        assert "401" in result["error"]
        assert "Authentication failed" in result["error"]


class TestGetPullRequest:
    """Test the get_pull_request method using REST API."""

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_get_pull_request_basic(
        self, mock_auth_headers, mock_get, azure_pr_tool
    ):
        """Test getting a specific pull request via REST API."""
        # Setup mock response for aiohttp
        mock_pr_data = {
            "pullRequestId": 123,
            "title": "Test PR",
            "sourceRefName": "refs/heads/feature/test",
            "targetRefName": "refs/heads/main",
            "status": "active",
            "createdBy": {"displayName": "John Doe", "uniqueName": "john.doe@abc.com"},
            "creationDate": "2024-01-15T10:30:00.000Z",
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = json.dumps(mock_pr_data)
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.get_pull_request(123)

        mock_get.assert_called_once()
        call_args, call_kwargs = mock_get.call_args
        assert "pullrequests/123" in call_args[0]
        assert result["success"] is True
        assert result["data"]["pullRequestId"] == 123

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_get_pull_request_not_found(
        self, mock_auth_headers, mock_get, azure_pr_tool
    ):
        """Test getting a non-existent pull request."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text.return_value = "Pull request not found"
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.get_pull_request(999)

        assert result["success"] is False
        assert "Pull request 999 not found" in result["error"]


class TestCreatePullRequest:
    """Test the create_pull_request method using REST API."""

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_create_pull_request_basic(
        self, mock_auth_headers, mock_post, azure_pr_tool
    ):
        """Test creating a basic pull request via REST API."""
        # Setup mock response for aiohttp
        mock_pr_data = {
            "pullRequestId": 123,
            "title": "Test PR",
            "sourceRefName": "refs/heads/feature/test",
            "targetRefName": "refs/heads/main",
            "status": "active",
            "createdBy": {"displayName": "John Doe", "uniqueName": "john.doe@abc.com"},
            "creationDate": "2024-01-15T10:30:00.000Z",
        }

        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.text.return_value = json.dumps(mock_pr_data)
        mock_post.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        azure_pr_tool.default_target_branch = "main"

        result = await azure_pr_tool.create_pull_request(
            title="Test PR", source_branch="feature/test"
        )

        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args
        assert "pullrequests" in call_args[0]

        # Check the request body
        request_body = call_kwargs["json"]
        assert request_body["title"] == "Test PR"
        assert request_body["sourceRefName"] == "refs/heads/feature/test"
        assert request_body["targetRefName"] == "refs/heads/main"
        assert request_body["isDraft"] is False

        assert result["success"] is True
        assert result["data"]["pullRequestId"] == 123

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    @patch("aiohttp.ClientSession.patch")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_create_pull_request_with_completion_options(
        self, mock_auth_headers, mock_patch, mock_post, azure_pr_tool
    ):
        """Test creating a pull request with auto-complete and other completion options."""
        # Setup mock response for PR creation
        mock_pr_data = {
            "pullRequestId": 123,
            "title": "Test PR",
            "sourceRefName": "refs/heads/feature/test",
            "targetRefName": "refs/heads/main",
            "status": "active",
        }

        mock_create_response = AsyncMock()
        mock_create_response.status = 201
        mock_create_response.text.return_value = json.dumps(mock_pr_data)
        mock_post.return_value.__aenter__.return_value = mock_create_response

        # Setup mock response for completion settings update
        mock_update_response = AsyncMock()
        mock_update_response.status = 200
        mock_update_response.text.return_value = json.dumps(mock_pr_data)
        mock_patch.return_value.__aenter__.return_value = mock_update_response

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        azure_pr_tool.default_target_branch = "main"

        result = await azure_pr_tool.create_pull_request(
            title="Test PR",
            source_branch="feature/test",
            description="Test description",
            reviewers=["user1", "user2"],
            work_items=[123, 456],
            draft=True,
            auto_complete=True,
            squash=True,
            delete_source_branch=True,
        )

        # Verify PR creation call
        mock_post.assert_called_once()
        create_call_args, create_call_kwargs = mock_post.call_args
        request_body = create_call_kwargs["json"]

        assert request_body["title"] == "Test PR"
        assert request_body["description"] == "Test description"
        assert request_body["isDraft"] is True
        assert len(request_body["reviewers"]) == 2
        assert len(request_body["workItemRefs"]) == 2

        # Verify completion settings update call
        mock_patch.assert_called_once()

        assert result["success"] is True
        assert result["data"]["pullRequestId"] == 123


class TestUpdatePullRequest:
    """Test the update_pull_request method."""

    @pytest.mark.asyncio
    async def test_update_pull_request_basic(
        self, azure_pr_tool, mock_command_success_response
    ):
        """Test updating a pull request."""
        azure_pr_tool._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_pr_tool.update_pull_request(
            123, title="New Title", description="New description"
        )

        expected_command = (
            'repos pr update --id 123 --title "New Title" '
            '--description "New description"'
        )
        azure_pr_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_update_pull_request_with_flags(
        self, azure_pr_tool, mock_command_success_response
    ):
        """Test updating a pull request with flags."""
        azure_pr_tool._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_pr_tool.update_pull_request(
            123, auto_complete=True, squash=False, delete_source_branch=True
        )

        expected_command = (
            "repos pr update --id 123 --auto-complete true "
            "--squash false --delete-source-branch true"
        )
        azure_pr_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response


class TestVotingAndReviewers:
    """Test voting and reviewer operations."""

    @pytest.mark.asyncio
    async def test_set_vote(self, azure_pr_tool, mock_command_success_response):
        """Test setting a vote on a pull request."""
        azure_pr_tool._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_pr_tool.set_vote(123, "approve")

        azure_pr_tool._run_az_command.assert_called_once_with(
            "repos pr set-vote --id 123 --vote approve"
        )
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_add_work_items(self, azure_pr_tool, mock_command_success_response):
        """Test adding work items to a pull request."""
        azure_pr_tool._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_pr_tool.add_work_items(123, [456, 789])

        azure_pr_tool._run_az_command.assert_called_once_with(
            "repos pr work-item add --id 123 --work-items 456 --work-items 789"
        )
        assert result == mock_command_success_response
