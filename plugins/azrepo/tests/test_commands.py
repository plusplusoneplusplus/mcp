"""
Tests for Azure CLI command execution functionality.
"""

import pytest
import json
from unittest.mock import AsyncMock


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

    @pytest.mark.asyncio
    async def test_run_az_command_with_timeout(self, azure_repo_client):
        """Test Azure CLI command execution with timeout."""
        # Mock the executor methods
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={
                "success": True,
                "output": json.dumps({"test": "data"}),
            }
        )

        result = await azure_repo_client._run_az_command("repos pr list", timeout=30.0)

        assert result["success"] is True
        azure_repo_client.executor.execute_async.assert_called_once_with(
            "az repos pr list --output json", 30.0
        )
        azure_repo_client.executor.query_process.assert_called_once_with(
            "test_token", wait=True, timeout=30.0
        )

    @pytest.mark.asyncio
    async def test_run_az_command_empty_output(self, azure_repo_client):
        """Test Azure CLI command with empty output."""
        # Mock the executor methods to return empty output
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={"success": True, "output": ""}
        )

        result = await azure_repo_client._run_az_command("repos pr list")

        assert result["success"] is True
        assert result["data"] == {}

    @pytest.mark.asyncio
    async def test_run_az_command_no_output_key(self, azure_repo_client):
        """Test Azure CLI command when output key is missing."""
        # Mock the executor methods to return response without output key
        azure_repo_client.executor.execute_async = AsyncMock(
            return_value={"token": "test_token"}
        )
        azure_repo_client.executor.query_process = AsyncMock(
            return_value={"success": True}  # No output key
        )

        result = await azure_repo_client._run_az_command("repos pr list")

        assert result["success"] is True
        assert result["data"] == {}
