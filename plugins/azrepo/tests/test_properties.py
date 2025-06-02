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
            == "Interact with Azure DevOps repositories with automatic configuration loading"
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
            "list_repos",
            "get_repo",
            "clone_repo",
        ]
        for op in expected_operations:
            assert op in operations

        # Check that repository-specific parameters are present
        assert "repository" in schema["properties"]
        assert "project" in schema["properties"]
        assert "organization" in schema["properties"]
        assert "clone_url" in schema["properties"]
        assert "local_path" in schema["properties"]


class TestInitialization:
    """Test initialization behavior."""

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
        assert client.executor == mock_executor

    @patch("mcp_tools.plugin.registry")
    def test_init_without_executor_failure(self, mock_registry):
        """Test initialization without executor (registry lookup failure)."""
        mock_registry.get_tool_instance.return_value = None

        with pytest.raises(ValueError, match="Command executor not found in registry"):
            AzureRepoClient()


class TestConfigurationLoading:
    """Test configuration loading behavior."""

    @patch("plugins.azrepo.tool.env_manager")
    def test_load_config_success(self, mock_env_manager):
        """Test successful configuration loading."""
        from unittest.mock import MagicMock
        mock_executor = MagicMock()

        # Mock environment manager
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            'org': 'https://dev.azure.com/testorg',
            'project': 'test-project',
            'repo': 'test-repo'
        }

        client = AzureRepoClient(command_executor=mock_executor)

        assert client.default_organization == 'https://dev.azure.com/testorg'
        assert client.default_project == 'test-project'
        assert client.default_repository == 'test-repo'

    @patch("plugins.azrepo.tool.env_manager")
    def test_load_config_failure(self, mock_env_manager):
        """Test configuration loading failure."""
        from unittest.mock import MagicMock
        mock_executor = MagicMock()

        # Mock environment manager to raise exception
        mock_env_manager.load.side_effect = Exception("Config load failed")

        client = AzureRepoClient(command_executor=mock_executor)

        # Should fall back to None values
        assert client.default_organization is None
        assert client.default_project is None
        assert client.default_repository is None


class TestParameterHandling:
    """Test parameter handling with defaults."""

    def test_get_param_with_default_explicit_value(self, azure_repo_client):
        """Test parameter handling when explicit value is provided."""
        result = azure_repo_client._get_param_with_default("explicit", "default")
        assert result == "explicit"

    def test_get_param_with_default_none_value(self, azure_repo_client):
        """Test parameter handling when None is provided."""
        result = azure_repo_client._get_param_with_default(None, "default")
        assert result == "default"

    def test_get_param_with_default_both_none(self, azure_repo_client):
        """Test parameter handling when both values are None."""
        result = azure_repo_client._get_param_with_default(None, None)
        assert result is None
