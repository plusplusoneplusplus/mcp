"""Tests for AzureWorkItemTool creation functionality."""

import pytest
from unittest.mock import patch

from plugins.azrepo.tests.workitem_helpers import mock_aiohttp_response, mock_azure_http_client


class TestCreateWorkItem:
    """Test the create_work_item method."""

    @pytest.mark.asyncio
    async def test_create_work_item_basic(self, azure_workitem_tool):
        """Test basic work item creation."""
        with mock_azure_http_client(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                description="Test description"
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 12345

    @pytest.mark.asyncio
    async def test_create_work_item_with_custom_type(self, azure_workitem_tool):
        """Test work item creation with custom type."""
        with mock_azure_http_client(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Bug Report",
                work_item_type="Bug"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_with_overrides(self, azure_workitem_tool):
        """Test work item creation with parameter overrides."""
        with mock_azure_http_client(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Custom Work Item",
                area_path="CustomArea",
                iteration_path="Sprint 2",
                organization="customorg",
                project="custom-project"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_minimal(self, azure_workitem_tool):
        """Test work item creation with minimal parameters."""
        with mock_azure_http_client(method="post"):
            result = await azure_workitem_tool.create_work_item(title="Minimal Work Item")

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_missing_org(self, azure_workitem_tool_no_defaults):
        """Test work item creation with missing organization."""
        # Clear the organization
        azure_workitem_tool_no_defaults.default_organization = None

        result = await azure_workitem_tool_no_defaults.create_work_item(title="Test Work Item")

        assert result["success"] is False
        assert "Organization is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_missing_project(self, azure_workitem_tool_no_defaults):
        """Test work item creation with missing project."""
        # Clear the project
        azure_workitem_tool_no_defaults.default_organization = "test_org"
        azure_workitem_tool_no_defaults.default_project = None

        result = await azure_workitem_tool_no_defaults.create_work_item(title="Test Work Item")

        assert result["success"] is False
        assert "Project is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_http_error(self, azure_workitem_tool):
        """Test work item creation with HTTP error."""
        with mock_azure_http_client(method="post", status_code=401, error_message="Access denied"):
            result = await azure_workitem_tool.create_work_item(title="Test Work Item")

            assert result["success"] is False
            assert "HTTP 401" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_json_parse_error(self, azure_workitem_tool):
        """Test work item creation with JSON parsing error."""
        with mock_azure_http_client(method="post", status_code=200, raw_response_text="Invalid JSON"):
            result = await azure_workitem_tool.create_work_item(title="Test Work Item")
            assert result["success"] is False
            assert "Failed to parse response" in result["error"]
            assert result["raw_output"] == "Invalid JSON"

    @pytest.mark.asyncio
    async def test_create_work_item_with_special_characters(self, azure_workitem_tool):
        """Test work item creation with special characters."""
        with mock_azure_http_client(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Fix issue with 'quotes' and \"double quotes\"",
                description="Description with special chars: @#$%^&*()_+-={}[]|\\:;\"'<>?,./"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_with_unicode(self, azure_workitem_tool):
        """Test work item creation with Unicode characters."""
        with mock_azure_http_client(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Unicode test: 测试 🚀 émojis",
                description="Description with Unicode: café naïve résumé 中文"
            )

            assert result["success"] is True
            assert "data" in result


class TestExecuteToolCreate:
    """Test the execute_tool method for create operations."""

    @pytest.mark.asyncio
    async def test_execute_tool_create_success(self, azure_workitem_tool):
        """Test successful work item creation through execute_tool."""
        with mock_azure_http_client(method="post"):
            arguments = {
                "operation": "create",
                "title": "Test Work Item",
                "description": "Test description",
                "work_item_type": "User Story"
            }

            result = await azure_workitem_tool.execute_tool(arguments)

            assert result["success"] is True
            assert "data" in result

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
        with mock_azure_http_client(method="post"):
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

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_create_with_defaults_fallback(self, azure_workitem_tool_no_defaults):
        """Test work item creation when no defaults are configured."""
        arguments = {
            "operation": "create",
            "title": "Test Work Item",
            "organization": "customorg",
            "project": "custom-project"
        }

        with mock_azure_http_client(method="post"):
            result = await azure_workitem_tool_no_defaults.execute_tool(arguments)

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_create_error_propagation(self, azure_workitem_tool):
        """Test error propagation through execute_tool."""
        with mock_azure_http_client(method="post", status_code=401, error_message="Access denied"):
            arguments = {
                "operation": "create",
                "title": "Failed Work Item"
            }

            result = await azure_workitem_tool.execute_tool(arguments)

            assert result["success"] is False
            assert "HTTP 401" in result["error"]
