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
        """Test basic pull request listing via REST API with new defaults."""
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
        azure_pr_tool.default_target_branch = "main"

        with patch.object(
            azure_pr_tool, "_get_current_username", return_value="test.user@company.com"
        ):
            result = await azure_pr_tool.list_pull_requests()

            mock_get.assert_called_once()
            call_args, call_kwargs = mock_get.call_args
            assert "pullrequests" in call_args[0]
            params = call_kwargs["params"]
            assert params["searchCriteria.creatorId"] == "test.user@company.com"
            # New default behavior: status should be "active"
            assert params["searchCriteria.status"] == "active"
            # New default behavior: target branch should be "main"
            assert params["searchCriteria.targetRefName"] == "refs/heads/main"

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

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_list_pull_requests_exclude_drafts_default(
        self, mock_auth_headers, mock_get, azure_pr_tool
    ):
        """Test that draft PRs are excluded by default."""
        # Setup mock response with both draft and non-draft PRs
        mock_prs = [
            {
                "pullRequestId": 123,
                "title": "Non-draft PR",
                "sourceRefName": "refs/heads/feature/test1",
                "targetRefName": "refs/heads/main",
                "status": "active",
                "isDraft": False,
                "createdBy": {"displayName": "John Doe", "uniqueName": "john.doe@abc.com"},
                "creationDate": "2024-01-15T10:30:00.000Z",
            },
            {
                "pullRequestId": 124,
                "title": "Draft PR",
                "sourceRefName": "refs/heads/feature/test2",
                "targetRefName": "refs/heads/main",
                "status": "active",
                "isDraft": True,
                "createdBy": {"displayName": "Jane Doe", "uniqueName": "jane.doe@abc.com"},
                "creationDate": "2024-01-15T11:30:00.000Z",
            }
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"value": mock_prs}
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        azure_pr_tool.default_target_branch = "main"

        with patch.object(
            azure_pr_tool, "_get_current_username", return_value="test.user@company.com"
        ):
            result = await azure_pr_tool.list_pull_requests()

            assert result["success"] is True
            # Should only contain the non-draft PR
            assert "123" in result["data"]
            assert "Non-draft PR" in result["data"]
            assert "124" not in result["data"]
            assert "Draft PR" not in result["data"]

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_list_pull_requests_include_drafts(
        self, mock_auth_headers, mock_get, azure_pr_tool
    ):
        """Test that draft PRs are included when exclude_drafts=False."""
        # Setup mock response with both draft and non-draft PRs
        mock_prs = [
            {
                "pullRequestId": 123,
                "title": "Non-draft PR",
                "sourceRefName": "refs/heads/feature/test1",
                "targetRefName": "refs/heads/main",
                "status": "active",
                "isDraft": False,
                "createdBy": {"displayName": "John Doe", "uniqueName": "john.doe@abc.com"},
                "creationDate": "2024-01-15T10:30:00.000Z",
            },
            {
                "pullRequestId": 124,
                "title": "Draft PR",
                "sourceRefName": "refs/heads/feature/test2",
                "targetRefName": "refs/heads/main",
                "status": "active",
                "isDraft": True,
                "createdBy": {"displayName": "Jane Doe", "uniqueName": "jane.doe@abc.com"},
                "creationDate": "2024-01-15T11:30:00.000Z",
            }
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"value": mock_prs}
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        azure_pr_tool.default_target_branch = "main"

        with patch.object(
            azure_pr_tool, "_get_current_username", return_value="test.user@company.com"
        ):
            result = await azure_pr_tool.list_pull_requests(exclude_drafts=False)

            assert result["success"] is True
            # Should contain both PRs
            assert "123" in result["data"]
            assert "Non-draft PR" in result["data"]
            assert "124" in result["data"]
            assert "Draft PR" in result["data"]

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_list_pull_requests_backward_compatibility(
        self, mock_auth_headers, mock_get, azure_pr_tool, mock_pr_list_response
    ):
        """Test backward compatibility - explicit None values should work as before."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"value": mock_pr_list_response["data"]}
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with patch.object(
            azure_pr_tool, "_get_current_username", return_value="test.user@company.com"
        ):
            # Explicitly pass None values to get old behavior
            result = await azure_pr_tool.list_pull_requests(
                status=None,
                target_branch=None,
                exclude_drafts=False
            )

            mock_get.assert_called_once()
            call_args, call_kwargs = mock_get.call_args
            params = call_kwargs["params"]

            # Should not have status filter (old behavior)
            assert "searchCriteria.status" not in params
            # Should not have target branch filter (old behavior)
            assert "searchCriteria.targetRefName" not in params

            assert result["success"] is True

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_list_pull_requests_custom_target_branch_default(
        self, mock_auth_headers, mock_get, azure_pr_tool, mock_pr_list_response
    ):
        """Test that configured default target branch is used when target_branch='default'."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"value": mock_pr_list_response["data"]}
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        azure_pr_tool.default_target_branch = "develop"  # Custom default

        with patch.object(
            azure_pr_tool, "_get_current_username", return_value="test.user@company.com"
        ):
            result = await azure_pr_tool.list_pull_requests()

            mock_get.assert_called_once()
            call_args, call_kwargs = mock_get.call_args
            params = call_kwargs["params"]

            # Should use configured default target branch
            assert params["searchCriteria.targetRefName"] == "refs/heads/develop"

            assert result["success"] is True


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
    """Test the update_pull_request method using REST API."""

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.patch")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_update_pull_request_basic(
        self, mock_auth_headers, mock_patch, azure_pr_tool
    ):
        """Test updating a pull request via REST API."""
        # Setup mock response for aiohttp
        mock_pr_data = {
            "pullRequestId": 123,
            "title": "New Title",
            "description": "New description",
            "status": "active"
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = json.dumps(mock_pr_data)
        mock_patch.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.update_pull_request(
            123, title="New Title", description="New description"
        )

        mock_patch.assert_called_once()
        call_args, call_kwargs = mock_patch.call_args
        assert "pullrequests/123" in call_args[0]

        # Check the request body
        request_body = call_kwargs["json"]
        assert request_body["title"] == "New Title"
        assert request_body["description"] == "New description"

        assert result["success"] is True
        assert result["data"]["pullRequestId"] == 123

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.patch")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_current_username")
    async def test_update_pull_request_with_flags(
        self, mock_username, mock_auth_headers, mock_patch, azure_pr_tool
    ):
        """Test updating a pull request with completion options via REST API."""
        # Setup mock response for aiohttp
        mock_pr_data = {
            "pullRequestId": 123,
            "status": "active",
            "autoCompleteSetBy": {"id": "test-user"}
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = json.dumps(mock_pr_data)
        mock_patch.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}
        mock_username.return_value = "test-user"

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.update_pull_request(
            123, auto_complete=True, squash=False, delete_source_branch=True
        )

        mock_patch.assert_called_once()
        call_args, call_kwargs = mock_patch.call_args
        assert "pullrequests/123" in call_args[0]

        # Check the request body
        request_body = call_kwargs["json"]
        assert request_body["autoCompleteSetBy"]["id"] == "test-user"
        assert request_body["completionOptions"]["squashMerge"] is False
        assert request_body["completionOptions"]["deleteSourceBranch"] is True

        assert result["success"] is True
        assert result["data"]["pullRequestId"] == 123


class TestVotingAndReviewers:
    """Test voting and reviewer operations using REST API."""

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.put")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_current_username")
    async def test_set_vote(self, mock_username, mock_auth_headers, mock_put, azure_pr_tool):
        """Test setting a vote on a pull request via REST API."""
        # Setup mock response for aiohttp
        mock_reviewer_data = {
            "id": "test-user",
            "displayName": "Test User",
            "vote": 10,
            "isRequired": False
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = json.dumps(mock_reviewer_data)
        mock_put.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}
        mock_username.return_value = "test-user"

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.set_vote(123, "approve")

        mock_put.assert_called_once()
        call_args, call_kwargs = mock_put.call_args
        assert "pullrequests/123/reviewers/test-user" in call_args[0]

        # Check the request body
        request_body = call_kwargs["json"]
        assert request_body["vote"] == 10  # approve maps to 10
        assert request_body["isRequired"] is False

        assert result["success"] is True
        assert result["data"]["vote"] == 10

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.put")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_current_username")
    async def test_set_vote_invalid_value(self, mock_username, mock_auth_headers, mock_put, azure_pr_tool):
        """Test setting an invalid vote value."""
        mock_username.return_value = "test-user"

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.set_vote(123, "invalid-vote")

        # Should not make any HTTP calls for invalid vote
        mock_put.assert_not_called()
        assert result["success"] is False
        assert "Invalid vote value" in result["error"]

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.patch")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_add_work_items(self, mock_auth_headers, mock_patch, azure_pr_tool):
        """Test adding work items to a pull request via REST API."""
        # Setup mock response for aiohttp
        mock_pr_data = {
            "pullRequestId": 123,
            "workItemRefs": [
                {"id": "456"},
                {"id": "789"}
            ]
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = json.dumps(mock_pr_data)
        mock_patch.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.add_work_items(123, [456, 789])

        mock_patch.assert_called_once()
        call_args, call_kwargs = mock_patch.call_args
        assert "pullrequests/123" in call_args[0]

        # Check the request body
        request_body = call_kwargs["json"]
        assert len(request_body["workItemRefs"]) == 2
        assert request_body["workItemRefs"][0]["id"] == "456"
        assert request_body["workItemRefs"][1]["id"] == "789"

        assert result["success"] is True
        assert result["data"]["pullRequestId"] == 123

    @pytest.mark.asyncio
    async def test_add_work_items_empty_list(self, azure_pr_tool):
        """Test adding empty work items list."""
        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.add_work_items(123, [])

        assert result["success"] is False
        assert "At least one work item ID is required" in result["error"]


class TestCommentManagement:
    """Test comment management operations."""

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_get_comments_basic(self, mock_auth_headers, mock_get, azure_pr_tool):
        """Test basic comment retrieval via REST API."""
        # Setup mock response for comment threads
        mock_threads = [
            {
                "id": 1,
                "status": "active",
                "comments": [
                    {
                        "id": 101,
                        "content": "This looks good!",
                        "author": {
                            "displayName": "John Doe",
                            "uniqueName": "john.doe@company.com",
                            "id": "user-123"
                        },
                        "publishedDate": "2024-01-15T10:30:00.000Z",
                        "commentType": "text"
                    }
                ]
            },
            {
                "id": 2,
                "status": "resolved",
                "comments": [
                    {
                        "id": 102,
                        "content": "Please fix this issue",
                        "author": {
                            "displayName": "Jane Smith",
                            "uniqueName": "jane.smith@company.com",
                            "id": "user-456"
                        },
                        "publishedDate": "2024-01-15T11:30:00.000Z",
                        "commentType": "text"
                    }
                ]
            }
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"value": mock_threads}
        mock_response.text.return_value = json.dumps({"value": mock_threads})
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.get_comments(pull_request_id=123)

        mock_get.assert_called_once()
        call_args, call_kwargs = mock_get.call_args
        assert "pullrequests/123/threads" in call_args[0]
        params = call_kwargs["params"]
        assert params["api-version"] == "7.1"

        assert result["success"] is True
        assert len(result["data"]) == 2
        assert result["data"][0]["id"] == 1
        assert result["data"][1]["id"] == 2

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_get_comments_with_filters(self, mock_auth_headers, mock_get, azure_pr_tool):
        """Test comment retrieval with status and author filters."""
        mock_threads = [
            {
                "id": 1,
                "status": "active",
                "comments": [
                    {
                        "id": 101,
                        "content": "Active comment",
                        "author": {
                            "displayName": "John Doe",
                            "uniqueName": "john.doe@company.com",
                            "id": "user-123"
                        },
                        "publishedDate": "2024-01-15T10:30:00.000Z",
                        "commentType": "text"
                    }
                ]
            },
            {
                "id": 2,
                "status": "resolved",
                "comments": [
                    {
                        "id": 102,
                        "content": "Resolved comment",
                        "author": {
                            "displayName": "Jane Smith",
                            "uniqueName": "jane.smith@company.com",
                            "id": "user-456"
                        },
                        "publishedDate": "2024-01-15T11:30:00.000Z",
                        "commentType": "text"
                    }
                ]
            }
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"value": mock_threads}
        mock_response.text.return_value = json.dumps({"value": mock_threads})
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        # Test status filter
        result = await azure_pr_tool.get_comments(
            pull_request_id=123,
            comment_status="active"
        )

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["status"] == "active"

        # Test author filter
        result = await azure_pr_tool.get_comments(
            pull_request_id=123,
            comment_author="john.doe@company.com"
        )

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["comments"][0]["author"]["uniqueName"] == "john.doe@company.com"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.patch")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_resolve_comment_basic(self, mock_auth_headers, mock_patch, azure_pr_tool):
        """Test basic comment resolution via REST API."""
        mock_thread = {
            "id": 1,
            "status": "fixed",
            "comments": [
                {
                    "id": 101,
                    "content": "This has been resolved",
                    "author": {
                        "displayName": "John Doe",
                        "uniqueName": "john.doe@company.com",
                        "id": "user-123"
                    },
                    "publishedDate": "2024-01-15T10:30:00.000Z",
                    "commentType": "text"
                }
            ]
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_thread
        mock_response.text.return_value = json.dumps(mock_thread)
        mock_patch.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.resolve_comment(
            pull_request_id=123,
            thread_id=1
        )

        mock_patch.assert_called_once()
        call_args, call_kwargs = mock_patch.call_args
        assert "pullrequests/123/threads/1" in call_args[0]
        assert call_kwargs["json"]["status"] == "fixed"
        params = call_kwargs["params"]
        assert params["api-version"] == "7.1"

        assert result["success"] is True
        assert result["data"]["status"] == "fixed"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_add_comment_new_thread(self, mock_auth_headers, mock_post, azure_pr_tool):
        """Test adding a comment to create a new thread."""
        mock_thread = {
            "id": 3,
            "status": "active",
            "comments": [
                {
                    "id": 103,
                    "content": "This is a new comment",
                    "author": {
                        "displayName": "John Doe",
                        "uniqueName": "john.doe@company.com",
                        "id": "user-123"
                    },
                    "publishedDate": "2024-01-15T12:30:00.000Z",
                    "commentType": "text"
                }
            ]
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_thread
        mock_response.text.return_value = json.dumps(mock_thread)
        mock_post.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.add_comment(
            pull_request_id=123,
            comment_content="This is a new comment"
        )

        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args
        assert "pullrequests/123/threads" in call_args[0]
        request_body = call_kwargs["json"]
        assert request_body["comments"][0]["content"] == "This is a new comment"
        assert request_body["status"] == "active"

        assert result["success"] is True
        assert result["data"]["id"] == 3

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_add_comment_to_existing_thread(self, mock_auth_headers, mock_post, azure_pr_tool):
        """Test adding a comment to an existing thread."""
        mock_comment = {
            "id": 104,
            "content": "Reply to existing thread",
            "author": {
                "displayName": "John Doe",
                "uniqueName": "john.doe@company.com",
                "id": "user-123"
            },
            "publishedDate": "2024-01-15T12:30:00.000Z",
            "commentType": "text"
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_comment
        mock_response.text.return_value = json.dumps(mock_comment)
        mock_post.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.add_comment(
            pull_request_id=123,
            comment_content="Reply to existing thread",
            thread_id=1
        )

        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args
        assert "pullrequests/123/threads/1/comments" in call_args[0]
        request_body = call_kwargs["json"]
        assert request_body["content"] == "Reply to existing thread"
        assert request_body["commentType"] == "text"

        assert result["success"] is True
        assert result["data"]["id"] == 104

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.patch")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_update_comment(self, mock_auth_headers, mock_patch, azure_pr_tool):
        """Test updating an existing comment."""
        mock_comment = {
            "id": 101,
            "content": "Updated comment content",
            "author": {
                "displayName": "John Doe",
                "uniqueName": "john.doe@company.com",
                "id": "user-123"
            },
            "publishedDate": "2024-01-15T10:30:00.000Z",
            "lastUpdatedDate": "2024-01-15T13:30:00.000Z",
            "commentType": "text"
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_comment
        mock_response.text.return_value = json.dumps(mock_comment)
        mock_patch.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.update_comment(
            pull_request_id=123,
            thread_id=1,
            comment_id=101,
            comment_content="Updated comment content"
        )

        mock_patch.assert_called_once()
        call_args, call_kwargs = mock_patch.call_args
        assert "pullrequests/123/threads/1/comments/101" in call_args[0]
        request_body = call_kwargs["json"]
        assert request_body["content"] == "Updated comment content"

        assert result["success"] is True
        assert result["data"]["content"] == "Updated comment content"

    @pytest.mark.asyncio
    async def test_add_comment_empty_content(self, azure_pr_tool):
        """Test that empty comment content returns error."""
        result = await azure_pr_tool.add_comment(
            pull_request_id=123,
            comment_content=""
        )

        assert result["success"] is False
        assert "Comment content is required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_comment_empty_content(self, azure_pr_tool):
        """Test that empty comment content returns error for update."""
        result = await azure_pr_tool.update_comment(
            pull_request_id=123,
            thread_id=1,
            comment_id=101,
            comment_content=""
        )

        assert result["success"] is False
        assert "Comment content is required" in result["error"]

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.get")
    @patch("plugins.azrepo.pr_tool.AzurePullRequestTool._get_auth_headers")
    async def test_get_comments_not_found(self, mock_auth_headers, mock_get, azure_pr_tool):
        """Test handling of PR not found during comment retrieval."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text.return_value = "Pull request not found"
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.get_comments(pull_request_id=999)

        assert result["success"] is False
        assert "Pull request 999 not found" in result["error"]
