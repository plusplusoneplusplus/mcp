"""
Tests for the execute_tool method and integration functionality.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock

from ..tool import AzureRepoClient


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
    async def test_execute_tool_update_pull_request(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool with update_pull_request operation."""
        azure_repo_client.update_pull_request = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "update_pull_request",
            "pull_request_id": 123,
            "title": "Updated Title",
            "status": "completed",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.update_pull_request.assert_called_once_with(
            pull_request_id=123,
            title="Updated Title",
            description=None,
            status="completed",
            organization=None,
            auto_complete=None,
            squash=None,
            delete_source_branch=None,
            draft=None,
        )
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_execute_tool_set_vote(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool with set_vote operation."""
        azure_repo_client.set_vote = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "set_vote",
            "pull_request_id": 123,
            "vote": "approve",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.set_vote.assert_called_once_with(
            pull_request_id=123,
            vote="approve",
            organization=None,
        )
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_execute_tool_add_work_items(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool with add_work_items operation."""
        azure_repo_client.add_work_items = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "add_work_items",
            "pull_request_id": 123,
            "work_items": [456, 789],
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.add_work_items.assert_called_once_with(
            pull_request_id=123,
            work_items=[456, 789],
            organization=None,
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

    @pytest.mark.asyncio
    async def test_execute_tool_missing_operation(self, azure_repo_client):
        """Test execute_tool with missing operation parameter."""
        arguments = {}
        result = await azure_repo_client.execute_tool(arguments)

        assert result["success"] is False
        assert "Unknown operation:" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_with_all_parameters(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool with all possible parameters."""
        azure_repo_client.create_pull_request = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "create_pull_request",
            "title": "Complete PR",
            "source_branch": "feature/complete",
            "target_branch": "main",
            "description": "Complete description",
            "repository": "test-repo",
            "project": "test-project",
            "organization": "https://dev.azure.com/test",
            "reviewers": ["user1", "user2"],
            "work_items": [123, 456],
            "draft": True,
            "auto_complete": True,
            "squash": True,
            "delete_source_branch": True,
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.create_pull_request.assert_called_once_with(
            title="Complete PR",
            source_branch="feature/complete",
            target_branch="main",
            description="Complete description",
            repository="test-repo",
            project="test-project",
            organization="https://dev.azure.com/test",
            reviewers=["user1", "user2"],
            work_items=[123, 456],
            draft=True,
            auto_complete=True,
            squash=True,
            delete_source_branch=True,
        )
        assert result == mock_command_success_response


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
