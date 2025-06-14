"""
Tests for pull request operations.
"""

import json
import pytest
from contextlib import contextmanager
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Optional

from plugins.azrepo.tests.test_helpers import (
    mock_auth_headers,
    mock_identity_resolution,
    assert_success_response,
    create_test_cases_for_pr_statuses,
)
from plugins.azrepo.tests.workitem_helpers import mock_azure_http_client

from ..pr_tool import AzurePullRequestTool


@contextmanager
def mock_pr_azure_http_client(
    method: str = "post",
    status_code: int = 200,
    response_data: Optional[dict] = None,
    error_message: Optional[str] = None,
    raw_response_text: Optional[str] = None,
):
    """
    Helper function to mock AzureHttpClient responses for PR tool tests.
    This patches the correct import path for the PR tool.
    """
    # Prepare the response data
    json_parse_error = None
    if raw_response_text is not None:
        text_payload = raw_response_text
        try:
            json_payload = json.loads(text_payload)
        except json.JSONDecodeError as e:
            json_payload = {"error": "invalid json in mock"}
            json_parse_error = e
    else:
        if status_code < 300 and response_data is None:
            response_data = {
                "id": 12345,
                "rev": 1,
                "fields": {"System.Title": "Test Work Item"},
                "url": "https://dev.azure.com/testorg/test-project/_apis/wit/workitems/12345",
            }

        json_payload = (
            response_data if status_code < 300 else {"message": error_message}
        )
        text_payload = json.dumps(json_payload)

    # Create the standardized AzureHttpClient response format
    if status_code < 300:
        # Check for JSON parse error on successful status code
        if json_parse_error:
            mock_result = {
                "success": False,
                "error": f"Failed to parse response: {json_parse_error}",
                "status_code": status_code,
                "raw_response": text_payload
            }
        else:
            mock_result = {
                "success": True,
                "data": json_payload,
                "status_code": status_code,
                "raw_response": text_payload
            }
    else:
        # Format error message the same way as the real AzureHttpClient
        if status_code == 404:
            error_msg = "Resource not found"
        else:
            error_msg = f"HTTP {status_code}: {error_message or text_payload}"

        mock_result = {
            "success": False,
            "error": error_msg,
            "status_code": status_code,
            "raw_response": text_payload
        }

    # Create the mock AzureHttpClient
    mock_client = MagicMock()
    mock_client.request = AsyncMock(return_value=mock_result)

    # Set up the async context manager
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Patch the correct import path for PR tool and yield the mock client
    with patch("plugins.azrepo.pr_tool.AzureHttpClient", return_value=mock_client):
        yield mock_client


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
    async def test_list_pull_requests_basic(
        self, azure_pr_tool, mock_pr_list_response
    ):
        """Test basic pull request listing via REST API with new defaults."""
        from plugins.azrepo.tests.test_helpers import create_mock_identity_info

        identity = create_mock_identity_info(
            display_name="Test User", unique_name="test.user@company.com"
        )

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        azure_pr_tool.default_target_branch = "main"

        with patch(
            "plugins.azrepo.pr_tool.get_current_username", return_value="testuser"
        ), mock_auth_headers(), mock_identity_resolution(identity):
            with mock_pr_azure_http_client(
                method="get", response_data={"value": mock_pr_list_response["data"]}
            ) as mock_client:
                result = await azure_pr_tool.list_pull_requests()

                mock_client.request.assert_called_once()
                call_args, call_kwargs = mock_client.request.call_args

                assert call_args[0] == "GET"
                assert "pullrequests" in call_args[1]
                params = call_kwargs["params"]
                assert params["searchCriteria.creatorId"] == identity.id
                assert params["searchCriteria.status"] == "active"
                assert params["searchCriteria.targetRefName"] == "refs/heads/main"

                assert_success_response(result)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", [s[0] for s in create_test_cases_for_pr_statuses(["active", "completed", "abandoned"])])
    async def test_list_pull_requests_status_filter(self, azure_pr_tool, status):
        """Ensure status filter is passed correctly."""
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        with mock_auth_headers(), mock_identity_resolution():
            with mock_pr_azure_http_client(method="get", response_data={"value": []}) as mock_client:
                result = await azure_pr_tool.list_pull_requests(status=status)
                params = mock_client.request.call_args[1]["params"]
                assert params["searchCriteria.status"] == status
                assert_success_response(result)
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_list_pull_requests_with_filters(
        self, mock_auth_headers, azure_pr_tool, mock_pr_list_response
    ):
        """Test pull request listing with filters via REST API."""
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", response_data={"value": mock_pr_list_response["data"]}) as mock_client:
            await azure_pr_tool.list_pull_requests(
                status="active",
                creator="test-creator",
                reviewer="test-reviewer",
                source_branch="feature/branch",
                target_branch="main",
                top=20,
                skip=5,
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args
            params = call_kwargs["params"]

            assert params["searchCriteria.status"] == "active"
            assert params["searchCriteria.creatorId"] == "test-creator"
            assert params["searchCriteria.reviewerId"] == "test-reviewer"
            assert params["searchCriteria.sourceRefName"] == "refs/heads/feature/branch"
            assert params["searchCriteria.targetRefName"] == "refs/heads/main"
            assert params["$top"] == 20
            assert params["$skip"] == 5

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_list_pull_requests_api_failure(
        self, mock_auth_headers, azure_pr_tool
    ):
        """Test handling of API failure during pull request listing."""
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", status_code=401, error_message="Authentication failed") as mock_client:
            result = await azure_pr_tool.list_pull_requests()

            assert result["success"] is False
            assert "401" in result["error"]
            assert "Authentication failed" in result["error"]

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_list_pull_requests_exclude_drafts_default(
        self, mock_auth_headers, azure_pr_tool
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

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        azure_pr_tool.default_target_branch = "main"

        with patch(
            "plugins.azrepo.pr_tool.get_current_username", return_value="testuser"
        ):
            # Mock identity resolution to fail (no bearer token configured)
            with patch("plugins.azrepo.pr_tool.resolve_identity") as mock_resolve:
                mock_resolve.side_effect = Exception("Bearer token not configured")

                with mock_pr_azure_http_client(method="get", response_data={"value": mock_prs}) as mock_client:
                    result = await azure_pr_tool.list_pull_requests()

                    assert result["success"] is True
                    # Should only contain the non-draft PR
                    assert "123" in result["data"]
                    assert "Non-draft PR" in result["data"]
                    assert "124" not in result["data"]
                    assert "Draft PR" not in result["data"]

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_list_pull_requests_include_drafts(
        self, mock_auth_headers, azure_pr_tool
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

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        azure_pr_tool.default_target_branch = "main"

        with patch(
            "plugins.azrepo.pr_tool.get_current_username", return_value="testuser"
        ):
            # Mock identity resolution to fail (no bearer token configured)
            with patch("plugins.azrepo.pr_tool.resolve_identity") as mock_resolve:
                mock_resolve.side_effect = Exception("Bearer token not configured")

                with mock_pr_azure_http_client(method="get", response_data={"value": mock_prs}) as mock_client:
                    result = await azure_pr_tool.list_pull_requests(exclude_drafts=False)

                    assert result["success"] is True
                    # Should contain both PRs
                    assert "123" in result["data"]
                    assert "Non-draft PR" in result["data"]
                    assert "124" in result["data"]
                    assert "Draft PR" in result["data"]

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_list_pull_requests_backward_compatibility(
        self, mock_auth_headers, azure_pr_tool, mock_pr_list_response
    ):
        """Test backward compatibility - explicit None values should work as before."""
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with patch(
            "plugins.azrepo.pr_tool.get_current_username", return_value="test.user@company.com"
        ):
            with mock_pr_azure_http_client(method="get", response_data={"value": mock_pr_list_response["data"]}) as mock_client:
                # Explicitly pass None values to get old behavior
                result = await azure_pr_tool.list_pull_requests(
                    status=None,
                    target_branch=None,
                    exclude_drafts=False
                )

                # Verify the HTTP client was called
                mock_client.request.assert_called_once()
                call_args, call_kwargs = mock_client.request.call_args
                params = call_kwargs["params"]

                # Should not have status filter (old behavior)
                assert "searchCriteria.status" not in params
                # Should not have target branch filter (old behavior)
                assert "searchCriteria.targetRefName" not in params

                assert result["success"] is True

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_list_pull_requests_custom_target_branch_default(
        self, mock_auth_headers, azure_pr_tool, mock_pr_list_response
    ):
        """Test that configured default target branch is used when target_branch='default'."""
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        azure_pr_tool.default_target_branch = "develop"  # Custom default

        with patch(
            "plugins.azrepo.pr_tool.get_current_username", return_value="test.user@company.com"
        ):
            with mock_pr_azure_http_client(method="get", response_data={"value": mock_pr_list_response["data"]}) as mock_client:
                result = await azure_pr_tool.list_pull_requests()

                # Verify the HTTP client was called
                mock_client.request.assert_called_once()
                call_args, call_kwargs = mock_client.request.call_args
                params = call_kwargs["params"]

                # Should use configured default target branch
                assert params["searchCriteria.targetRefName"] == "refs/heads/develop"

                assert result["success"] is True


class TestGetPullRequest:
    """Test the get_pull_request method using REST API."""

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_pull_request_basic(
        self, mock_auth_headers, azure_pr_tool
    ):
        """Test getting a specific pull request via REST API."""
        # Setup mock response data
        mock_pr_data = {
            "pullRequestId": 123,
            "title": "Test PR",
            "sourceRefName": "refs/heads/feature/test",
            "targetRefName": "refs/heads/main",
            "status": "active",
            "createdBy": {"displayName": "John Doe", "uniqueName": "john.doe@abc.com"},
            "creationDate": "2024-01-15T10:30:00.000Z",
        }

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", response_data=mock_pr_data) as mock_client:
            result = await azure_pr_tool.get_pull_request(123)

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args
            assert call_args[0] == "GET"
            assert "pullrequests/123" in call_args[1]
            assert result["success"] is True
            assert result["data"]["pullRequestId"] == 123

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_pull_request_not_found(
        self, mock_auth_headers, azure_pr_tool
    ):
        """Test getting a non-existent pull request."""
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", status_code=404, error_message="Pull request not found") as mock_client:
            result = await azure_pr_tool.get_pull_request(999)

            assert result["success"] is False
            assert "Pull request 999 not found" in result["error"]


class TestCreatePullRequest:
    """Test the create_pull_request method using REST API."""

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_create_pull_request_basic(
        self, mock_auth_headers, azure_pr_tool
    ):
        """Test creating a basic pull request via REST API."""
        # Setup mock response data
        mock_pr_data = {
            "pullRequestId": 123,
            "title": "Test PR",
            "sourceRefName": "refs/heads/feature/test",
            "targetRefName": "refs/heads/main",
            "status": "active",
            "createdBy": {"displayName": "John Doe", "uniqueName": "john.doe@abc.com"},
            "creationDate": "2024-01-15T10:30:00.000Z",
        }

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        azure_pr_tool.default_target_branch = "main"

        with mock_pr_azure_http_client(method="post", status_code=201, response_data=mock_pr_data) as mock_client:
            result = await azure_pr_tool.create_pull_request(
                title="Test PR", source_branch="feature/test"
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args
            assert call_args[0] == "POST"
            assert "pullrequests" in call_args[1]

            # Check the request body
            request_body = call_kwargs["json"]
            assert request_body["title"] == "Test PR"
            assert request_body["sourceRefName"] == "refs/heads/feature/test"
            assert request_body["targetRefName"] == "refs/heads/main"
            assert request_body["isDraft"] is False

            assert result["success"] is True
            assert result["data"]["pullRequestId"] == 123

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_create_pull_request_with_completion_options(
        self, mock_auth_headers, azure_pr_tool
    ):
        """Test creating a pull request with auto-complete and other completion options."""
        # Setup mock response for PR creation
        mock_pr_data = {
            "pullRequestId": 123,
            "title": "Test PR",
            "sourceRefName": "refs/heads/feature/test",
            "targetRefName": "refs/heads/main",
            "status": "active",
            "createdBy": {"displayName": "John Doe", "uniqueName": "john.doe@abc.com"},
            "creationDate": "2024-01-15T10:30:00.000Z",
        }

        # Setup mock response for completion settings update
        mock_completion_data = {
            "pullRequestId": 123,
            "autoCompleteSetBy": {"id": "test-user"},
            "completionOptions": {
                "squashMerge": True,
                "deleteSourceBranch": True
            }
        }

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"
        azure_pr_tool.default_target_branch = "main"

        with patch(
            "plugins.azrepo.pr_tool.get_current_username", return_value="test-user"
        ):
            # Mock the AzureHttpClient to handle both calls
            with patch("plugins.azrepo.pr_tool.AzureHttpClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # Configure the mock to return different responses for POST and PATCH
                def side_effect(method, url, **kwargs):
                    if method == "POST":
                        return {"success": True, "status_code": 201, "data": mock_pr_data}
                    elif method == "PATCH":
                        return {"success": True, "status_code": 200, "data": mock_completion_data}
                    else:
                        return {"success": False, "error": "Unexpected method"}

                mock_client.request.side_effect = side_effect

                result = await azure_pr_tool.create_pull_request(
                    title="Test PR",
                    source_branch="feature/test",
                    auto_complete=True,
                    squash=True,
                    delete_source_branch=True
                )

                # Verify both calls were made
                assert mock_client.request.call_count == 2

                # Verify the POST call for PR creation
                post_call = mock_client.request.call_args_list[0]
                assert post_call[0][0] == "POST"
                assert "pullrequests" in post_call[0][1]

                # Verify the PATCH call for completion settings
                patch_call = mock_client.request.call_args_list[1]
                assert patch_call[0][0] == "PATCH"
                assert "pullrequests/123" in patch_call[0][1]

                assert result["success"] is True
                assert result["data"]["pullRequestId"] == 123


class TestUpdatePullRequest:
    """Test the update_pull_request method using REST API."""

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_update_pull_request_basic(
        self, mock_auth_headers, azure_pr_tool
    ):
        """Test updating a pull request via REST API."""
        # Setup mock response data
        mock_pr_data = {
            "pullRequestId": 123,
            "title": "New Title",
            "description": "New description",
            "status": "active"
        }

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="patch", response_data=mock_pr_data) as mock_client:
            result = await azure_pr_tool.update_pull_request(
                123, title="New Title", description="New description"
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args
            assert call_args[0] == "PATCH"
            assert "pullrequests/123" in call_args[1]

            # Check the request body
            request_body = call_kwargs["json"]
            assert request_body["title"] == "New Title"
            assert request_body["description"] == "New description"

            assert result["success"] is True
            assert result["data"]["pullRequestId"] == 123

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    @patch("plugins.azrepo.pr_tool.get_current_username")
    async def test_update_pull_request_with_flags(
        self, mock_username, mock_auth_headers, azure_pr_tool
    ):
        """Test updating a pull request with completion options via REST API."""
        # Setup mock response data
        mock_pr_data = {
            "pullRequestId": 123,
            "status": "active",
            "autoCompleteSetBy": {"id": "test-user"}
        }

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}
        mock_username.return_value = "test-user"

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="patch", response_data=mock_pr_data) as mock_client:
            result = await azure_pr_tool.update_pull_request(
                123, auto_complete=True, squash=False, delete_source_branch=True
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args
            assert call_args[0] == "PATCH"
            assert "pullrequests/123" in call_args[1]

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
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    @patch("plugins.azrepo.pr_tool.get_current_username")
    async def test_set_vote(self, mock_username, mock_auth_headers, azure_pr_tool):
        """Test setting a vote on a pull request via REST API."""
        # Setup mock response data
        mock_reviewer_data = {
            "id": "test-user",
            "displayName": "Test User",
            "vote": 10,
            "isRequired": False
        }

        mock_username.return_value = "test-user"
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="put", response_data=mock_reviewer_data) as mock_client:
            result = await azure_pr_tool.set_vote(123, "approve")

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "PUT"
            assert "pullrequests/123/reviewers/test-user" in call_args[1]

            # Check the request body
            request_body = call_kwargs["json"]
            assert request_body["vote"] == 10  # approve maps to 10
            assert request_body["isRequired"] is False

            assert result["success"] is True
            assert result["data"]["vote"] == 10

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_current_username")
    async def test_set_vote_invalid_value(self, mock_username, azure_pr_tool):
        """Test setting an invalid vote value."""
        mock_username.return_value = "test-user"

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        result = await azure_pr_tool.set_vote(123, "invalid-vote")

        # Should not make any HTTP calls for invalid vote
        assert result["success"] is False
        assert "Invalid vote value" in result["error"]

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_add_work_items(self, mock_auth_headers, azure_pr_tool):
        """Test adding work items to a pull request via REST API."""
        # Setup mock response data
        mock_pr_data = {
            "pullRequestId": 123,
            "workItemRefs": [
                {"id": "456"},
                {"id": "789"}
            ]
        }

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        # Configure the tool with default values
        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="patch", response_data=mock_pr_data) as mock_client:
            result = await azure_pr_tool.add_work_items(123, [456, 789])

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "PATCH"
            assert "pullrequests/123" in call_args[1]

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
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_comments_basic(self, mock_auth_headers, azure_pr_tool):
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

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", response_data={"value": mock_threads}) as mock_client:
            result = await azure_pr_tool.get_comments(pull_request_id=123)

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "GET"
            assert "pullrequests/123/threads" in call_args[1]
            params = call_kwargs["params"]
            assert params["api-version"] == "7.1"

            assert result["success"] is True
            assert len(result["data"]) == 2
            assert result["data"][0]["id"] == 1
            assert result["data"][1]["id"] == 2

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_comments_with_filters(self, mock_auth_headers, azure_pr_tool):
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

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", response_data={"value": mock_threads}) as mock_client:
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
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_resolve_comment_basic(self, mock_auth_headers, azure_pr_tool):
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

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="patch", response_data=mock_thread) as mock_client:
            result = await azure_pr_tool.resolve_comment(
                pull_request_id=123,
                thread_id=1
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "PATCH"
            assert "pullrequests/123/threads/1" in call_args[1]
            assert call_kwargs["json"]["status"] == "fixed"
            params = call_kwargs["params"]
            assert params["api-version"] == "7.1"

            assert result["success"] is True
            assert result["data"]["status"] == "fixed"

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_add_comment_new_thread(self, mock_auth_headers, azure_pr_tool):
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

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="post", response_data=mock_thread) as mock_client:
            result = await azure_pr_tool.add_comment(
                pull_request_id=123,
                comment_content="This is a new comment"
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "POST"
            assert "pullrequests/123/threads" in call_args[1]
            request_body = call_kwargs["json"]
            assert request_body["comments"][0]["content"] == "This is a new comment"
            assert request_body["status"] == "active"

            assert result["success"] is True
            assert result["data"]["id"] == 3

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_add_comment_to_existing_thread(self, mock_auth_headers, azure_pr_tool):
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

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="post", response_data=mock_comment) as mock_client:
            result = await azure_pr_tool.add_comment(
                pull_request_id=123,
                comment_content="Reply to existing thread",
                thread_id=1
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "POST"
            assert "pullrequests/123/threads/1/comments" in call_args[1]
            request_body = call_kwargs["json"]
            assert request_body["content"] == "Reply to existing thread"
            assert request_body["commentType"] == "text"

            assert result["success"] is True
            assert result["data"]["id"] == 104

    @pytest.mark.asyncio
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_update_comment(self, mock_auth_headers, azure_pr_tool):
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

        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="patch", response_data=mock_comment) as mock_client:
            result = await azure_pr_tool.update_comment(
                pull_request_id=123,
                thread_id=1,
                comment_id=101,
                comment_content="Updated comment content"
            )

            # Verify the HTTP client was called
            mock_client.request.assert_called_once()
            call_args, call_kwargs = mock_client.request.call_args

            # Check the method and URL
            assert call_args[0] == "PATCH"
            assert "pullrequests/123/threads/1/comments/101" in call_args[1]
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
    @patch("plugins.azrepo.pr_tool.get_auth_headers")
    async def test_get_comments_not_found(self, mock_auth_headers, azure_pr_tool):
        """Test handling of PR not found during comment retrieval."""
        mock_auth_headers.return_value = {"Authorization": "Bearer fake-token"}

        azure_pr_tool.default_organization = "test-org"
        azure_pr_tool.default_project = "test-project"
        azure_pr_tool.default_repository = "test-repo"

        with mock_pr_azure_http_client(method="get", status_code=404, error_message="Pull request not found") as mock_client:
            result = await azure_pr_tool.get_comments(pull_request_id=999)

            assert result["success"] is False
            assert "Pull request 999 not found" in result["error"]
