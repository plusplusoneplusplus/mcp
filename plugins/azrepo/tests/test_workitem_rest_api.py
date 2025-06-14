"""
Tests for work item REST API operations.
"""

import pytest
from unittest.mock import patch

from plugins.azrepo.tests.test_helpers import (
    assert_error_response,
    assert_http_client_called_with_method,
    assert_success_response,
    mock_azure_http_client_context,
)


@pytest.fixture
def mock_create_response():
    """Mock successful REST API response for work item creation."""
    return {
        "id": 12345, "rev": 1, "fields": {"System.Title": "Test Work Item"}
    }


@pytest.fixture
def mock_get_response():
    """Mock successful REST API response for work item retrieval."""
    return {
        "id": 12345, "rev": 2, "fields": {"System.Title": "Test Work Item - Updated"}
    }


class TestWorkItemCreation:
    """Test REST API work item creation functionality."""

    @pytest.mark.asyncio
    async def test_create_work_item_rest_api_success(self, azure_workitem_tool, mock_create_response):
        """Test successful work item creation via REST API."""
        with mock_azure_http_client_context(method="post", response=mock_create_response) as mock_client:
            result = await azure_workitem_tool.create_work_item(title="Test Work Item")

            assert_success_response(result)
            assert "data" in result
            assert result["data"]["id"] == 12345

            assert_http_client_called_with_method(mock_client, "request")


    @pytest.mark.asyncio
    async def test_create_work_item_rest_api_http_error(self, azure_workitem_tool):
        """Test work item creation with HTTP error response."""
        with mock_azure_http_client_context(method="post", status_code=401, error_message="HTTP 401: Access denied"):
            result = await azure_workitem_tool.create_work_item(title="Test Work Item")

            assert_error_response(result)
            assert "error" in result
            assert "HTTP 401" in result["error"]


class TestWorkItemRetrieval:
    """Test REST API work item retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_work_item_rest_api_success(self, azure_workitem_tool, mock_get_response):
        """Test successful work item retrieval via REST API."""
        with mock_azure_http_client_context(method="get", response=mock_get_response):
            result = await azure_workitem_tool.get_work_item(work_item_id=12345)

            assert_success_response(result)
            assert "data" in result
            assert result["data"]["id"] == 12345
            assert result["data"]["fields"]["System.Title"] == "Test Work Item - Updated"

    @pytest.mark.asyncio
    async def test_get_work_item_with_query_parameters(self, azure_workitem_tool, mock_get_response):
        """Test work item retrieval with query parameters."""
        with mock_azure_http_client_context(method="get", response=mock_get_response) as mock_client:
            result = await azure_workitem_tool.get_work_item(
                work_item_id=12345,
                as_of="2024-01-15",
                expand="all",
                fields="System.Id,System.Title"
            )

            assert_success_response(result)
            assert "data" in result
            assert result["data"]["id"] == 12345

            # Verify the request was made
            assert_http_client_called_with_method(mock_client, "request")
            # Note: URL parameter verification would require examining the request call args

    @pytest.mark.asyncio
    async def test_get_work_item_not_found(self, azure_workitem_tool):
        """Test work item retrieval with 404 not found response."""
        with mock_azure_http_client_context(method="get", status_code=404, error_message="Work item not found"):
            result = await azure_workitem_tool.get_work_item(work_item_id=99999)

            assert_error_response(result)
            assert "Work item 99999 not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_work_item_with_string_id(self, azure_workitem_tool, mock_get_response):
        """Test work item retrieval with a string ID."""
        with mock_azure_http_client_context(method="get", response=mock_get_response):
            result = await azure_workitem_tool.get_work_item(work_item_id="12345")

            assert_success_response(result)
            assert result["data"]["id"] == 12345

    @pytest.mark.asyncio
    @pytest.mark.parametrize("date_str", ["2024-01-15", "2024-01-15 12:30:00"])
    async def test_get_work_item_with_date_formats(self, azure_workitem_tool, mock_get_response, date_str):
        """Test work item retrieval with different date formats for as_of."""
        with mock_azure_http_client_context(method="get", response=mock_get_response) as mock_client:
            await azure_workitem_tool.get_work_item(work_item_id=12345, as_of=date_str)

            assert_http_client_called_with_method(mock_client, "request")
            # Note: URL parameter verification would require examining the request call args


class TestExecuteTool:
    """Test execute_tool method for REST API operations."""

    @pytest.mark.asyncio
    async def test_execute_tool_create_rest_api(self, azure_workitem_tool, mock_create_response):
        """Test execute_tool create operation via REST API."""
        with mock_azure_http_client_context(method="post", response=mock_create_response):
            result = await azure_workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "description": "Test description",
                "work_item_type": "User Story"
            })
            assert_success_response(result)
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_get_rest_api(self, azure_workitem_tool, mock_get_response):
        """Test execute_tool get operation via REST API."""
        with mock_azure_http_client_context(method="get", response=mock_get_response):
            result = await azure_workitem_tool.execute_tool({
                "operation": "get",
                "work_item_id": 12345,
                "expand": "all",
                "fields": "System.Id,System.Title"
            })
            assert_success_response(result)
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_get_missing_work_item_id(self, azure_workitem_tool):
        """Test execute_tool get operation with missing work_item_id."""
        result = await azure_workitem_tool.execute_tool({"operation": "get"})
        assert_error_response(result)
        assert "work_item_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_operation(self, azure_workitem_tool):
        """Test execute_tool with unknown operation."""
        result = await azure_workitem_tool.execute_tool({"operation": "unknown"})
        assert_error_response(result)
        assert "Unknown operation" in result["error"]
