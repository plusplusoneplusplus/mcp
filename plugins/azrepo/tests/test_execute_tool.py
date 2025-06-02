"""
Tests for the execute_tool method and integration functionality for repository operations.
"""

import pytest
from unittest.mock import AsyncMock

from ..repo_tool import AzureRepoClient


class TestExecuteTool:
    """Test the execute_tool method for repository operations."""

    @pytest.mark.asyncio
    async def test_execute_tool_list_repos(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool with list_repos operation."""
        azure_repo_client.list_repositories = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "list_repos",
            "project": "test-project",
            "organization": "https://dev.azure.com/myorg",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.list_repositories.assert_called_once_with(
            project="test-project",
            organization="https://dev.azure.com/myorg",
        )
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_execute_tool_get_repo(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool with get_repo operation."""
        azure_repo_client.get_repository = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "get_repo",
            "repository": "test-repo",
            "project": "test-project",
            "organization": "https://dev.azure.com/myorg",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.get_repository.assert_called_once_with(
            repository="test-repo",
            project="test-project",
            organization="https://dev.azure.com/myorg",
        )
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_execute_tool_clone_repo_with_url(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool with clone_repo operation using clone URL."""
        azure_repo_client.clone_repository = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "clone_repo",
            "clone_url": "https://github.com/user/repo.git",
            "local_path": "/path/to/local",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.clone_repository.assert_called_once_with(
            clone_url="https://github.com/user/repo.git",
            local_path="/path/to/local",
            repository=None,
            project=None,
            organization=None,
        )
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_execute_tool_clone_repo_azure_devops(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool with clone_repo operation using Azure DevOps parameters."""
        azure_repo_client.clone_repository = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "clone_repo",
            "repository": "test-repo",
            "project": "test-project",
            "organization": "https://dev.azure.com/myorg",
            "local_path": "/path/to/local",
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.clone_repository.assert_called_once_with(
            clone_url=None,
            local_path="/path/to/local",
            repository="test-repo",
            project="test-project",
            organization="https://dev.azure.com/myorg",
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
        """Test execute_tool with missing operation."""
        arguments = {}
        result = await azure_repo_client.execute_tool(arguments)

        assert result["success"] is False
        assert "Unknown operation:" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_with_defaults(
        self, azure_repo_client, mock_command_success_response
    ):
        """Test execute_tool using configured defaults."""
        # Set up defaults
        azure_repo_client.default_organization = "https://dev.azure.com/defaultorg"
        azure_repo_client.default_project = "default-project"
        azure_repo_client.default_repository = "default-repo"

        azure_repo_client.get_repository = AsyncMock(
            return_value=mock_command_success_response
        )

        arguments = {
            "operation": "get_repo",
            # No explicit parameters - should use defaults
        }
        result = await azure_repo_client.execute_tool(arguments)

        azure_repo_client.get_repository.assert_called_once_with(
            repository=None,  # Will use default in the method
            project=None,     # Will use default in the method
            organization=None, # Will use default in the method
        )
        assert result == mock_command_success_response


class TestRepositoryIntegration:
    """Test end-to-end repository workflows."""

    @pytest.mark.asyncio
    async def test_end_to_end_list_repositories_workflow(self, azure_repo_client):
        """Test end-to-end workflow for listing repositories."""
        # Mock the command execution
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={
                "success": True,
                "output": '{"value": [{"id": "repo1", "name": "Repository 1"}, {"id": "repo2", "name": "Repository 2"}]}'
            }
        )

        # Test via execute_tool interface
        result = await azure_repo_client.execute_tool({
            "operation": "list_repos",
            "project": "test-project"
        })

        assert result["success"] is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_end_to_end_get_repository_workflow(self, azure_repo_client):
        """Test end-to-end workflow for getting repository details."""
        # Mock the command execution
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={
                "success": True,
                "output": '{"id": "repo1", "name": "Repository 1", "defaultBranch": "refs/heads/main"}'
            }
        )

        # Test via execute_tool interface
        result = await azure_repo_client.execute_tool({
            "operation": "get_repo",
            "repository": "test-repo",
            "project": "test-project"
        })

        assert result["success"] is True
        assert "data" in result
