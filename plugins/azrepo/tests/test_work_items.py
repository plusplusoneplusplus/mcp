"""
Tests for Azure DevOps work item integration.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from plugins.azrepo.workitem_tool import AzureWorkItemTool
import plugins.azrepo.azure_rest_utils
from plugins.azrepo.tests.helpers import patch_azure_utils_env_manager


@pytest.fixture
def mock_executor():
    """Mock command executor."""
    executor = MagicMock()
    executor.execute_async = AsyncMock()
    executor.query_process = AsyncMock()
    return executor


@pytest.fixture
def workitem_tool(mock_executor):
    """Create AzureWorkItemTool instance with bearer token configured."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock environment settings
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "bearer_token": "test-bearer-token-123"
        }

        # Also patch the azure_rest_utils env_manager
        with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_rest_env_manager:
            mock_rest_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "bearer_token": "test-bearer-token-123"
            }

            tool = AzureWorkItemTool(command_executor=mock_executor)
            yield tool


@pytest.fixture
def mock_command_success_response():
    """Mock a successful response from the command executor."""
    return {
        "success": True,
        "data": {
            "id": 123,
            "sourceRefName": "refs/heads/feature/test",
            "status": "active",
            "targetRefName": "refs/heads/main",
            "title": "Test PR",
            "description": "Test PR description",
            "createdBy": {
                "displayName": "Test User",
                "id": "12345"
            },
            "reviewers": []
        }
    }


@pytest.fixture
def mock_command_error_response():
    """Mock an error response from the command executor."""
    return {
        "success": False,
        "error": "Test error message"
    }


class TestWorkItems:
    """Test work item management methods."""

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_get_work_item_basic(
        self, mock_env_manager, mock_rest_env_manager, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with basic parameters."""
        # Mock the REST API response
        mock_work_item_data = {
            "id": 123,
            "fields": {
                "System.Title": "Test Work Item",
                "System.State": "New"
            }
        }

        # Set the default values directly on the tool instance
        azure_workitem_tool.default_organization = "testorg"
        azure_workitem_tool.default_project = "test-project"

        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_work_item_data))

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await azure_workitem_tool.get_work_item(123)

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 123

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_get_work_item_with_all_options(
        self, mock_env_manager, mock_rest_env_manager, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with all optional parameters."""
        mock_work_item_data = {
            "id": 123,
            "fields": {
                "System.Id": 123,
                "System.Title": "Test Work Item",
                "System.State": "New"
            }
        }

        # Set the default values directly on the tool instance
        azure_workitem_tool.default_organization = "testorg"
        azure_workitem_tool.default_project = "test-project"

        # Configure both mocks to return the same values
        config = {
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_work_item_data))

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await azure_workitem_tool.get_work_item(
                work_item_id=123,
                organization="https://dev.azure.com/myorg",
                project="myproject",
                as_of="2023-01-01",
                expand="all",
                fields="System.Id,System.Title,System.State",
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 123

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_get_work_item_with_defaults(
        self, mock_env_manager, mock_rest_env_manager, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item using configured defaults."""
        mock_work_item_data = {
            "id": 456,
            "fields": {
                "System.Title": "Test Work Item",
                "System.State": "New"
            }
        }

        # Set the default values directly on the tool instance
        azure_workitem_tool.default_organization = "defaultorg"
        azure_workitem_tool.default_project = "defaultproject"

        # Configure both mocks to return the same values
        config = {
            "org": "defaultorg",
            "project": "defaultproject",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_work_item_data))

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await azure_workitem_tool.get_work_item(456)

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 456

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_get_work_item_with_string_id(
        self, mock_env_manager, mock_rest_env_manager, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with string ID."""
        mock_work_item_data = {
            "id": 123,
            "fields": {
                "System.Title": "Test Work Item",
                "System.State": "New"
            }
        }

        # Set the default values directly on the tool instance
        azure_workitem_tool.default_organization = "testorg"
        azure_workitem_tool.default_project = "test-project"

        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_work_item_data))

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await azure_workitem_tool.get_work_item("123")

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 123

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_get_work_item_with_date_formats(
        self, mock_env_manager, mock_rest_env_manager, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with different date formats."""
        mock_work_item_data = {
            "id": 123,
            "fields": {
                "System.Title": "Test Work Item",
                "System.State": "New"
            }
        }

        # Set the default values directly on the tool instance
        azure_workitem_tool.default_organization = "testorg"
        azure_workitem_tool.default_project = "test-project"

        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_work_item_data))

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Test with date only
            result = await azure_workitem_tool.get_work_item(
                work_item_id=123, as_of="2023-01-01"
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 123

            # Test with date and time
            mock_session.reset_mock()
            mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await azure_workitem_tool.get_work_item(
                work_item_id=123, as_of="2023-01-01 12:30:00"
            )

            assert result["success"] is True

            # Verify the URL contains the date and time parameter
            call_args = mock_session.get.call_args
            url = call_args[0][0]
            assert "asOf=2023-01-01 12:30:00" in url

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_get_work_item_with_expand_options(
        self, mock_env_manager, mock_rest_env_manager, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with different expand options."""
        mock_work_item_data = {
            "id": 123,
            "fields": {
                "System.Title": "Test Work Item",
                "System.State": "New"
            }
        }

        # Set the default values directly on the tool instance
        azure_workitem_tool.default_organization = "testorg"
        azure_workitem_tool.default_project = "test-project"

        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        expand_options = ["all", "fields", "links", "none", "relations"]

        for expand_option in expand_options:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_work_item_data))

            mock_session = MagicMock()
            mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            with patch("aiohttp.ClientSession", return_value=mock_session):
                result = await azure_workitem_tool.get_work_item(
                    work_item_id=123, expand=expand_option
                )

                assert result["success"] is True
                assert "data" in result
                assert result["data"]["id"] == 123

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_get_work_item_with_multiple_fields(
        self, mock_env_manager, mock_rest_env_manager, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with multiple field specifications."""
        mock_work_item_data = {
            "id": 123,
            "fields": {
                "System.Id": 123,
                "System.Title": "Test Work Item",
                "System.State": "New",
                "System.AssignedTo": "test@example.com",
                "System.AreaPath": "TestArea"
            }
        }

        # Set the default values directly on the tool instance
        azure_workitem_tool.default_organization = "testorg"
        azure_workitem_tool.default_project = "test-project"

        # Configure both mocks to return the same values
        config = {
            "org": "testorg",
            "project": "test-project",
            "bearer_token": "test-bearer-token-123"
        }
        mock_env_manager.get_azrepo_parameters.return_value = config
        mock_rest_env_manager.get_azrepo_parameters.return_value = config

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(mock_work_item_data))

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await azure_workitem_tool.get_work_item(
                work_item_id=123,
                fields="System.Id,System.Title,System.State,System.AssignedTo,System.AreaPath",
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 123

    @pytest.mark.asyncio
    @patch_azure_utils_env_manager
    async def test_get_work_item_error_handling(
        self, mock_env_manager, mock_rest_env_manager, azure_workitem_tool, mock_command_error_response
    ):
        """Test error handling when getting a work item."""
        result = await azure_workitem_tool.get_work_item(999)

        assert result["success"] is False
        assert "error" in result
