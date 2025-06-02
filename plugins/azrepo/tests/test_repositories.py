"""
Tests for repository operations.
"""

import pytest
from unittest.mock import AsyncMock


class TestListRepositories:
    """Test the list_repositories method."""

    @pytest.mark.asyncio
    async def test_list_repositories_basic(
        self, azure_repo_client, mock_repo_list_response
    ):
        """Test basic repository listing."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_repo_list_response
        )

        result = await azure_repo_client.list_repositories()

        azure_repo_client._run_az_command.assert_called_once_with("repos list")
        assert result == mock_repo_list_response

    @pytest.mark.asyncio
    async def test_list_repositories_with_params(
        self, azure_repo_client, mock_repo_list_response
    ):
        """Test repository listing with parameters."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_repo_list_response
        )

        result = await azure_repo_client.list_repositories(
            project="test-project", organization="https://dev.azure.com/myorg"
        )

        expected_command = (
            "repos list --project test-project --org https://dev.azure.com/myorg"
        )
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_repo_list_response

    @pytest.mark.asyncio
    async def test_list_repositories_with_defaults(
        self, azure_repo_client, mock_repo_list_response
    ):
        """Test repository listing using configured defaults."""
        # Set up defaults
        azure_repo_client.default_project = "default-project"
        azure_repo_client.default_organization = "https://dev.azure.com/defaultorg"

        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_repo_list_response
        )

        result = await azure_repo_client.list_repositories()

        expected_command = "repos list --project default-project --org https://dev.azure.com/defaultorg"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_repo_list_response


class TestGetRepository:
    """Test the get_repository method."""

    @pytest.mark.asyncio
    async def test_get_repository_basic(
        self, azure_repo_client, mock_repo_details_response
    ):
        """Test getting repository details."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_repo_details_response
        )

        result = await azure_repo_client.get_repository(repository="test-repo")

        expected_command = "repos show --repository test-repo"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_repo_details_response

    @pytest.mark.asyncio
    async def test_get_repository_with_all_params(
        self, azure_repo_client, mock_repo_details_response
    ):
        """Test getting repository details with all parameters."""
        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_repo_details_response
        )

        result = await azure_repo_client.get_repository(
            repository="test-repo",
            project="test-project",
            organization="https://dev.azure.com/myorg",
        )

        expected_command = "repos show --repository test-repo --project test-project --org https://dev.azure.com/myorg"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_repo_details_response

    @pytest.mark.asyncio
    async def test_get_repository_with_defaults(
        self, azure_repo_client, mock_repo_details_response
    ):
        """Test getting repository details using configured defaults."""
        # Set up defaults
        azure_repo_client.default_repository = "default-repo"
        azure_repo_client.default_project = "default-project"
        azure_repo_client.default_organization = "https://dev.azure.com/defaultorg"

        azure_repo_client._run_az_command = AsyncMock(
            return_value=mock_repo_details_response
        )

        result = await azure_repo_client.get_repository()

        expected_command = "repos show --repository default-repo --project default-project --org https://dev.azure.com/defaultorg"
        azure_repo_client._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_repo_details_response


class TestCloneRepository:
    """Test the clone_repository method."""

    @pytest.mark.asyncio
    async def test_clone_repository_with_url(self, azure_repo_client):
        """Test cloning repository with direct URL."""
        # Mock the executor directly since clone uses git command, not az command
        mock_result = {"token": "test-token"}
        mock_status = {"success": True, "output": "Cloning into 'repo'..."}

        azure_repo_client.executor.execute_async = AsyncMock(return_value=mock_result)
        azure_repo_client.executor.query_process = AsyncMock(return_value=mock_status)

        result = await azure_repo_client.clone_repository(
            clone_url="https://github.com/user/repo.git", local_path="/path/to/local"
        )

        azure_repo_client.executor.execute_async.assert_called_once_with(
            "git clone https://github.com/user/repo.git /path/to/local"
        )
        assert result["success"] is True
        assert "Repository cloned successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_clone_repository_azure_devops(self, azure_repo_client):
        """Test cloning Azure DevOps repository."""
        mock_result = {"token": "test-token"}
        mock_status = {"success": True, "output": "Cloning into 'repo'..."}

        azure_repo_client.executor.execute_async = AsyncMock(return_value=mock_result)
        azure_repo_client.executor.query_process = AsyncMock(return_value=mock_status)

        result = await azure_repo_client.clone_repository(
            repository="test-repo",
            project="test-project",
            organization="https://dev.azure.com/myorg",
            local_path="/path/to/local",
        )

        expected_command = "git clone https://dev.azure.com/myorg/test-project/_git/test-repo /path/to/local"
        azure_repo_client.executor.execute_async.assert_called_once_with(
            expected_command
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_clone_repository_missing_params(self, azure_repo_client):
        """Test cloning with missing required parameters."""
        result = await azure_repo_client.clone_repository(
            repository="test-repo"
            # Missing project and organization
        )

        assert result["success"] is False
        assert (
            "Repository, project, and organization must be specified" in result["error"]
        )

    @pytest.mark.asyncio
    async def test_clone_repository_with_defaults(self, azure_repo_client):
        """Test cloning using configured defaults."""
        # Set up defaults
        azure_repo_client.default_repository = "default-repo"
        azure_repo_client.default_project = "default-project"
        azure_repo_client.default_organization = "https://dev.azure.com/defaultorg"

        mock_result = {"token": "test-token"}
        mock_status = {"success": True, "output": "Cloning into 'repo'..."}

        azure_repo_client.executor.execute_async = AsyncMock(return_value=mock_result)
        azure_repo_client.executor.query_process = AsyncMock(return_value=mock_status)

        result = await azure_repo_client.clone_repository(local_path="/path/to/local")

        expected_command = "git clone https://dev.azure.com/defaultorg/default-project/_git/default-repo /path/to/local"
        azure_repo_client.executor.execute_async.assert_called_once_with(
            expected_command
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_clone_repository_error(self, azure_repo_client):
        """Test clone repository error handling."""
        mock_result = {"token": "test-token"}
        mock_status = {"success": False, "error": "Repository not found"}

        azure_repo_client.executor.execute_async = AsyncMock(return_value=mock_result)
        azure_repo_client.executor.query_process = AsyncMock(return_value=mock_status)

        result = await azure_repo_client.clone_repository(
            clone_url="https://github.com/user/nonexistent.git"
        )

        assert result["success"] is False
        assert "Repository not found" in result["error"]
