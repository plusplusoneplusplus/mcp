"""Tests for AzureWorkItemTool creation functionality."""

import pytest
from unittest.mock import patch

from plugins.azrepo.tests.test_helpers import (
    BaseTestClass,
    assert_error_response,
    assert_http_client_called_with_method,
    assert_success_response,
    create_mock_work_item_response,
    create_test_cases_for_http_errors,
    create_test_cases_for_work_item_types,
    mock_azure_http_client_context,
)


class TestCreateWorkItem(BaseTestClass):
    """Test the create_work_item method."""

    @pytest.mark.asyncio
    async def test_create_work_item_basic(self, azure_workitem_tool):
        """Test basic work item creation."""
        with mock_azure_http_client_context(
            method="post",
            response=create_mock_work_item_response(item_id=12345),
        ) as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                description="Test description"
            )

        assert_success_response(result)
        assert result["data"]["id"] == 12345
        assert_http_client_called_with_method(mock_client, "request")
    @pytest.mark.asyncio
    @pytest.mark.parametrize("work_item_type", create_test_cases_for_work_item_types(["Bug", "Task", "Feature"]))
    async def test_create_work_item_with_custom_type(
        self, work_item_type: str, azure_workitem_tool
    ) -> None:
        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Bug Report",
                work_item_type=work_item_type,
            )

        assert_success_response(result)
        assert_http_client_called_with_method(mock_client, "request")



    @pytest.mark.asyncio
    async def test_create_work_item_with_overrides(self, azure_workitem_tool):
        """Test work item creation with parameter overrides."""
        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Custom Work Item",
                area_path="CustomArea",
                iteration_path="Sprint 2",
                organization="customorg",
                project="custom-project"
            )

        assert_success_response(result)
        assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    async def test_create_work_item_minimal(self, azure_workitem_tool):
        """Test work item creation with minimal parameters."""
        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(title="Minimal Work Item")

        assert_success_response(result)
        assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    async def test_create_work_item_missing_org(self, azure_workitem_tool_no_defaults):
        """Test work item creation with missing organization."""
        # Clear the organization
        azure_workitem_tool_no_defaults.default_organization = None

        result = await azure_workitem_tool_no_defaults.create_work_item(title="Test Work Item")

        assert_error_response(result)
        assert "Organization is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_missing_project(self, azure_workitem_tool_no_defaults):
        """Test work item creation with missing project."""
        # Clear the project
        azure_workitem_tool_no_defaults.default_organization = "test_org"
        azure_workitem_tool_no_defaults.default_project = None

        result = await azure_workitem_tool_no_defaults.create_work_item(title="Test Work Item")

        assert_error_response(result)
        assert "Project is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code, message", create_test_cases_for_http_errors([401, 500]))
    async def test_create_work_item_http_error(self, status_code, message, azure_workitem_tool):
        """Test work item creation with HTTP error."""
        with mock_azure_http_client_context(method="post", status_code=status_code, error_message=message) as mock_client:
            result = await azure_workitem_tool.create_work_item(title="Test Work Item")

            assert_error_response(result)
        assert message in result["error"]
        assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    async def test_create_work_item_json_parse_error(self, azure_workitem_tool):
        """Test work item creation with JSON parsing error."""
        with mock_azure_http_client_context(
            method="post",
            status_code=200,
            error_message="Failed to parse response",
            raw_response="Invalid JSON",
        ) as mock_client:
            result = await azure_workitem_tool.create_work_item(title="Test Work Item")

        assert_error_response(result)
        assert "Failed to parse response" in result["error"]
        assert result["raw_output"] == "Invalid JSON"
        assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    async def test_create_work_item_with_special_characters(self, azure_workitem_tool):
        """Test work item creation with special characters."""
        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Fix issue with 'quotes' and \"double quotes\"",
                description="Description with special chars: @#$%^&*()_+-={}[]|\\:;\"'<>?,./",
            )

        assert_success_response(result)
        assert_http_client_called_with_method(mock_client, "request")
    @pytest.mark.asyncio
    async def test_create_work_item_with_unicode(self, azure_workitem_tool):
        """Test work item creation with Unicode characters."""
        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Unicode test: 测试 🚀 émojis",
                description="Description with Unicode: café naïve résumé 中文",
            )

        assert_success_response(result)
        assert_http_client_called_with_method(mock_client, "request")




class TestExecuteToolCreate(BaseTestClass):
    """Test the execute_tool method for create operations."""

    @pytest.mark.asyncio
    async def test_execute_tool_create_success(self, azure_workitem_tool):
        """Test successful work item creation through execute_tool."""
        with mock_azure_http_client_context(method="post") as mock_client:
            arguments = {
                "operation": "create",
                "title": "Test Work Item",
                "description": "Test description",
                "work_item_type": "User Story"
            }

            result = await azure_workitem_tool.execute_tool(arguments)

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    async def test_execute_tool_create_missing_title(self, azure_workitem_tool):
        """Test work item creation with missing title."""
        arguments = {
            "operation": "create",
            "description": "Test description"
        }

        result = await azure_workitem_tool.execute_tool(arguments)

        assert result["success"] is False
        assert "title is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_create_empty_title(self, azure_workitem_tool):
        """Test work item creation with empty title."""
        arguments = {
            "operation": "create",
            "title": "",
            "description": "Test description"
        }

        result = await azure_workitem_tool.execute_tool(arguments)

        assert result["success"] is False
        assert "title is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_create_with_all_params(self, azure_workitem_tool):
        """Test work item creation with all parameters."""
        with mock_azure_http_client_context(method="post") as mock_client:
            arguments = {
                "operation": "create",
                "title": "Complete Work Item",
                "description": "Complete description",
                "work_item_type": "Epic",
                "area_path": "MyArea",
                "iteration_path": "MyIteration",
                "organization": "myorg",
                "project": "my-project"
            }

            result = await azure_workitem_tool.execute_tool(arguments)

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    async def test_execute_tool_create_with_defaults_fallback(self, azure_workitem_tool_no_defaults):
        """Test work item creation when no defaults are configured."""
        arguments = {
            "operation": "create",
            "title": "Test Work Item",
            "organization": "customorg",
            "project": "custom-project"
        }

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool_no_defaults.execute_tool(arguments)

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    async def test_execute_tool_create_error_propagation(self, azure_workitem_tool):
        """Test error propagation through execute_tool."""
        with mock_azure_http_client_context(method="post", status_code=401, error_message="HTTP 401: Access denied") as mock_client:
            arguments = {
                "operation": "create",
                "title": "Failed Work Item"
            }

            result = await azure_workitem_tool.execute_tool(arguments)

            assert_error_response(result)
            assert "HTTP 401" in result["error"]
            assert_http_client_called_with_method(mock_client, "request")
