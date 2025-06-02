"""
Tests for pull request operations.
"""

import pytest
from unittest.mock import patch, AsyncMock

from ..tool import AzureRepoClient


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
