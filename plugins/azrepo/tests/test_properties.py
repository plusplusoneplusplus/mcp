"""
Tests for AzureRepoClient properties and interface compliance.
"""

import pytest
from unittest.mock import patch

from ..tool import AzureRepoClient


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


class TestInitialization:
    """Test client initialization."""

    def test_init_with_executor(self):
        """Test initialization with provided executor."""
        from unittest.mock import MagicMock
        mock_executor = MagicMock()
        client = AzureRepoClient(command_executor=mock_executor)
        assert client.executor == mock_executor

    @patch("mcp_tools.plugin.registry")
    def test_init_without_executor_success(self, mock_registry):
        """Test initialization without executor (registry lookup success)."""
        from unittest.mock import MagicMock
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
