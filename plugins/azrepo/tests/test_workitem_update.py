"""Tests for work item update REST API operations."""

import pytest
from unittest.mock import patch

from plugins.azrepo.tests.workitem_helpers import mock_aiohttp_response, mock_azure_http_client


class TestUpdateWorkItem:
    """Test the update_work_item method."""

    @pytest.mark.asyncio
    async def test_update_work_item_title_only(self, azure_workitem_tool):
        """Test updating work item title only."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Work Item Title"
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 12345

    @pytest.mark.asyncio
    async def test_update_work_item_description_only(self, azure_workitem_tool):
        """Test updating work item description only."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.update_work_item(
                work_item_id=12345,
                description="Updated test description"
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 12345

    @pytest.mark.asyncio
    async def test_update_work_item_both_fields(self, azure_workitem_tool):
        """Test updating both title and description."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title",
                description="Updated description"
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 12345

    @pytest.mark.asyncio
    async def test_update_work_item_with_markdown(self, azure_workitem_tool):
        """Test updating work item description with markdown content."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.update_work_item(
                work_item_id=12345,
                description="## Updated Description\n\nNew details with **markdown** support"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_update_work_item_string_id(self, azure_workitem_tool):
        """Test updating work item with string ID."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.update_work_item(
                work_item_id="12345",
                title="Updated Title"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_update_work_item_with_overrides(self, azure_workitem_tool):
        """Test updating work item with parameter overrides."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title",
                organization="customorg",
                project="custom-project"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_update_work_item_no_fields_provided(self, azure_workitem_tool):
        """Test updating work item with no fields provided."""
        result = await azure_workitem_tool.update_work_item(work_item_id=12345)

        assert result["success"] is False
        assert "At least one of title or description must be provided" in result["error"]

    @pytest.mark.asyncio
    async def test_update_work_item_missing_org(self, azure_workitem_tool_no_defaults):
        """Test updating work item with missing organization."""
        result = await azure_workitem_tool_no_defaults.update_work_item(
            work_item_id=12345,
            title="Updated Title"
        )

        assert result["success"] is False
        assert "Organization is required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_work_item_missing_project(self, azure_workitem_tool_no_defaults):
        """Test updating work item with missing project."""
        azure_workitem_tool_no_defaults.default_organization = "testorg"
        result = await azure_workitem_tool_no_defaults.update_work_item(
            work_item_id=12345,
            title="Updated Title"
        )

        assert result["success"] is False
        assert "Project is required" in result["error"]

    @pytest.mark.asyncio
    async def test_update_work_item_not_found(self, azure_workitem_tool):
        """Test updating work item that doesn't exist."""
        with mock_azure_http_client(method="patch", status_code=404, error_message="Work item not found"):
            result = await azure_workitem_tool.update_work_item(
                work_item_id=99999,
                title="Updated Title"
            )

            assert result["success"] is False
            assert "Work item 99999 not found" in result["error"]
            assert "raw_output" in result

    @pytest.mark.asyncio
    async def test_update_work_item_http_error(self, azure_workitem_tool):
        """Test updating work item with HTTP error."""
        with mock_azure_http_client(method="patch", status_code=401, error_message="Access denied"):
            result = await azure_workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title"
            )

            assert result["success"] is False
            assert "HTTP 401" in result["error"]
            assert "raw_output" in result

    @pytest.mark.asyncio
    async def test_update_work_item_json_parse_error(self, azure_workitem_tool):
        """Test updating work item with JSON parsing error."""
        with mock_azure_http_client(method="patch", status_code=200, raw_response_text="Invalid JSON"):
            result = await azure_workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title"
            )

            assert result["success"] is False
            assert "Failed to parse response" in result["error"]
            assert result["raw_output"] == "Invalid JSON"

    @pytest.mark.asyncio
    async def test_update_work_item_network_error(self, azure_workitem_tool):
        """Test updating work item with network error."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session_class.side_effect = Exception("Network error")

            result = await azure_workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title"
            )

            assert result["success"] is False
            assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_update_work_item_with_special_characters(self, azure_workitem_tool):
        """Test updating work item with special characters."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title with Special Characters: @#$%^&*()",
                description="Description with special chars: <>&\"'"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_update_work_item_with_unicode(self, azure_workitem_tool):
        """Test updating work item with Unicode characters."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.update_work_item(
                work_item_id=12345,
                title="Updated Title with Unicode: 测试 🚀 ñáéíóú",
                description="Unicode description: 日本語 العربية русский"
            )

            assert result["success"] is True
            assert "data" in result


class TestExecuteToolUpdate:
    """Test the execute_tool method for update operations."""

    @pytest.mark.asyncio
    async def test_execute_tool_update_success(self, azure_workitem_tool):
        """Test successful update via execute_tool."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 12345,
                "title": "Updated Title",
                "description": "Updated description"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_update_title_only(self, azure_workitem_tool):
        """Test updating title only via execute_tool."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 12345,
                "title": "Updated Title Only"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_update_description_only(self, azure_workitem_tool):
        """Test updating description only via execute_tool."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 12345,
                "description": "Updated description only"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_update_missing_work_item_id(self, azure_workitem_tool):
        """Test update operation with missing work_item_id."""
        result = await azure_workitem_tool.execute_tool({
            "operation": "update",
            "title": "Updated Title"
        })

        assert result["success"] is False
        assert "work_item_id is required for update operation" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_update_missing_fields(self, azure_workitem_tool):
        """Test update operation with missing title and description."""
        result = await azure_workitem_tool.execute_tool({
            "operation": "update",
            "work_item_id": 12345
        })

        assert result["success"] is False
        assert "At least one of title or description must be provided" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_update_with_overrides(self, azure_workitem_tool):
        """Test update operation with parameter overrides."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 12345,
                "title": "Updated Title",
                "organization": "customorg",
                "project": "custom-project"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_update_error_propagation(self, azure_workitem_tool):
        """Test that update errors are properly propagated through execute_tool."""
        with mock_azure_http_client(method="patch", status_code=404, error_message="Work item not found"):
            result = await azure_workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 99999,
                "title": "Updated Title"
            })

            assert result["success"] is False
            assert "Work item 99999 not found" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_update_with_markdown(self, azure_workitem_tool):
        """Test update operation with markdown description."""
        with mock_azure_http_client(method="patch"):
            result = await azure_workitem_tool.execute_tool({
                "operation": "update",
                "work_item_id": 12345,
                "description": "## Updated Description\n\nWith **markdown** formatting"
            })

            assert result["success"] is True
            assert "data" in result
