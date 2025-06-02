"""
Tests for work item operations.
"""

import pytest
from unittest.mock import AsyncMock


class TestWorkItems:
    """Test work item management methods."""

    @pytest.mark.asyncio
    async def test_get_work_item_basic(
        self, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with basic parameters."""
        azure_workitem_tool._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_workitem_tool.get_work_item(123)

        expected_command = "boards work-item show --id 123"
        azure_workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_get_work_item_with_all_options(
        self, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with all optional parameters."""
        azure_workitem_tool._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_workitem_tool.get_work_item(
            work_item_id=123,
            organization="https://dev.azure.com/myorg",
            as_of="2023-01-01",
            expand="all",
            fields="System.Id,System.Title,System.State",
        )

        expected_command = (
            "boards work-item show --id 123 --org https://dev.azure.com/myorg "
            "--as-of '2023-01-01' --expand all "
            "--fields System.Id,System.Title,System.State"
        )
        azure_workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_get_work_item_with_defaults(
        self, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item using configured defaults."""
        # Set up defaults
        azure_workitem_tool.default_organization = "https://dev.azure.com/defaultorg"

        azure_workitem_tool._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_workitem_tool.get_work_item(456)

        expected_command = (
            "boards work-item show --id 456 --org https://dev.azure.com/defaultorg"
        )
        azure_workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_get_work_item_with_string_id(
        self, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with string ID."""
        azure_workitem_tool._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_workitem_tool.get_work_item("123")

        expected_command = "boards work-item show --id 123"
        azure_workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_get_work_item_with_date_formats(
        self, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with different date formats."""
        azure_workitem_tool._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        # Test with date only
        result = await azure_workitem_tool.get_work_item(
            work_item_id=123, as_of="2023-01-01"
        )

        expected_command = "boards work-item show --id 123 --as-of '2023-01-01'"
        azure_workitem_tool._run_az_command.assert_called_with(expected_command)

        # Test with date and time
        azure_workitem_tool._run_az_command.reset_mock()
        result = await azure_workitem_tool.get_work_item(
            work_item_id=123, as_of="2023-01-01 12:30:00"
        )

        expected_command = (
            "boards work-item show --id 123 --as-of '2023-01-01 12:30:00'"
        )
        azure_workitem_tool._run_az_command.assert_called_with(expected_command)

    @pytest.mark.asyncio
    async def test_get_work_item_with_expand_options(
        self, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with different expand options."""
        azure_workitem_tool._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        expand_options = ["all", "fields", "links", "none", "relations"]

        for expand_option in expand_options:
            azure_workitem_tool._run_az_command.reset_mock()
            result = await azure_workitem_tool.get_work_item(
                work_item_id=123, expand=expand_option
            )

            expected_command = (
                f"boards work-item show --id 123 --expand {expand_option}"
            )
            azure_workitem_tool._run_az_command.assert_called_with(expected_command)
            assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_get_work_item_with_multiple_fields(
        self, azure_workitem_tool, mock_command_success_response
    ):
        """Test getting a work item with multiple field specifications."""
        azure_workitem_tool._run_az_command = AsyncMock(
            return_value=mock_command_success_response
        )

        result = await azure_workitem_tool.get_work_item(
            work_item_id=123,
            fields="System.Id,System.Title,System.State,System.AssignedTo,System.AreaPath",
        )

        expected_command = (
            "boards work-item show --id 123 "
            "--fields System.Id,System.Title,System.State,System.AssignedTo,System.AreaPath"
        )
        azure_workitem_tool._run_az_command.assert_called_once_with(expected_command)
        assert result == mock_command_success_response

    @pytest.mark.asyncio
    async def test_get_work_item_error_handling(self, azure_workitem_tool):
        """Test work item retrieval error handling."""
        error_response = {"success": False, "error": "Work item not found"}
        azure_workitem_tool._run_az_command = AsyncMock(return_value=error_response)

        result = await azure_workitem_tool.get_work_item(999)

        assert result["success"] is False
        assert "Work item not found" in result["error"]
