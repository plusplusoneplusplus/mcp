"""
Tests for work item operations.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


class TestWorkItems:
    """Test work item management methods."""

    @pytest.mark.asyncio
    async def test_get_work_item_basic(
        self, azure_workitem_tool, mock_command_success_response
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

        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "bearer_token": "test-bearer-token-123"
            }

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
                assert result["data"]["id"] == 123

                # Verify the URL was constructed correctly
                mock_session.get.assert_called_once()
                call_args = mock_session.get.call_args
                url = call_args[0][0]
                assert "wit/workitems/123" in url
                assert "api-version=7.1" in url

    @pytest.mark.asyncio
    async def test_get_work_item_with_all_options(
        self, azure_workitem_tool, mock_command_success_response
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

        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.get_azrepo_parameters.return_value = {
                "bearer_token": "test-bearer-token-123"
            }

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
                assert result["data"]["id"] == 123

                # Verify the URL contains query parameters
                mock_session.get.assert_called_once()
                call_args = mock_session.get.call_args
                url = call_args[0][0]
                assert "wit/workitems/123" in url
                assert "asOf=2023-01-01" in url
                assert "$expand=all" in url
                assert "fields=System.Id,System.Title,System.State" in url

    @pytest.mark.asyncio
    async def test_get_work_item_with_defaults(
        self, azure_workitem_tool, mock_command_success_response
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

        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "defaultorg",
                "project": "defaultproject",
                "bearer_token": "test-bearer-token-123"
            }

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
                assert result["data"]["id"] == 456

                # Verify the URL was constructed with defaults
                mock_session.get.assert_called_once()
                call_args = mock_session.get.call_args
                url = call_args[0][0]
                assert "defaultorg" in url
                assert "defaultproject" in url
                assert "wit/workitems/456" in url

    @pytest.mark.asyncio
    async def test_get_work_item_with_string_id(
        self, azure_workitem_tool, mock_command_success_response
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

        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "bearer_token": "test-bearer-token-123"
            }

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
                assert result["data"]["id"] == 123

                # Verify the URL was constructed correctly with string ID
                mock_session.get.assert_called_once()
                call_args = mock_session.get.call_args
                url = call_args[0][0]
                assert "wit/workitems/123" in url

    @pytest.mark.asyncio
    async def test_get_work_item_with_date_formats(
        self, azure_workitem_tool, mock_command_success_response
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

        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "bearer_token": "test-bearer-token-123"
            }

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

                # Verify the URL contains the date parameter
                mock_session.get.assert_called()
                call_args = mock_session.get.call_args
                url = call_args[0][0]
                assert "asOf=2023-01-01" in url

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
    async def test_get_work_item_with_expand_options(
        self, azure_workitem_tool, mock_command_success_response
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

        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "bearer_token": "test-bearer-token-123"
            }

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

                    # Verify the URL contains the expand parameter
                    mock_session.get.assert_called_once()
                    call_args = mock_session.get.call_args
                    url = call_args[0][0]
                    assert f"$expand={expand_option}" in url

    @pytest.mark.asyncio
    async def test_get_work_item_with_multiple_fields(
        self, azure_workitem_tool, mock_command_success_response
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

        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "bearer_token": "test-bearer-token-123"
            }

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
                assert result["data"]["id"] == 123

                # Verify the URL contains the fields parameter
                mock_session.get.assert_called_once()
                call_args = mock_session.get.call_args
                url = call_args[0][0]
                assert "fields=System.Id,System.Title,System.State,System.AssignedTo,System.AreaPath" in url

    @pytest.mark.asyncio
    async def test_get_work_item_error_handling(self, azure_workitem_tool):
        """Test work item retrieval error handling."""
        # Test missing organization/project (which should be caught before making HTTP request)
        result = await azure_workitem_tool.get_work_item(999)

        assert result["success"] is False
        assert "Organization is required" in result["error"]
