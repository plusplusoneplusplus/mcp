"""
Tests for work item assignment functionality.
"""

import pytest
from unittest.mock import patch
import plugins.azrepo.azure_rest_utils
from plugins.azrepo.tests.workitem_helpers import mock_aiohttp_response


class TestWorkItemAssignment:
    """Test work item assignment functionality."""

    @pytest.mark.asyncio
    @patch.object(plugins.azrepo.azure_rest_utils, "get_current_username")
    async def test_auto_assign_to_current_user(self, mock_get_username, azure_workitem_tool):
        """Test automatic assignment to current user."""
        mock_get_username.return_value = "testuser"

        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                description="Test description"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    @patch.object(plugins.azrepo.azure_rest_utils, "get_current_username")
    async def test_auto_assign_to_current_user_no_username(self, mock_get_username, azure_workitem_tool):
        """Test auto-assignment when current user cannot be determined."""
        mock_get_username.return_value = None

        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                description="Test description"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_explicit_assignment(self, azure_workitem_tool):
        """Test explicit user assignment."""
        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                assigned_to="specific.user@company.com"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_unassigned_work_item(self, azure_workitem_tool):
        """Test creating unassigned work items."""
        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                assigned_to="none"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_disable_auto_assignment(self, azure_workitem_tool):
        """Test disabling auto-assignment."""
        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                auto_assign_to_current_user=False
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    @patch.object(plugins.azrepo.azure_rest_utils, "get_current_username")
    async def test_auto_assignment_with_config_disabled(self, mock_get_username, azure_workitem_tool_no_auto_assign):
        """Test that auto-assignment respects configuration setting."""
        mock_get_username.return_value = "testuser"

        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool_no_auto_assign.create_work_item(
                title="Test Work Item"
            )

            assert result["success"] is True
            assert "data" in result


class TestExecuteToolAssignment:
    """Test assignment functionality through execute_tool method."""

    @pytest.mark.asyncio
    @patch.object(plugins.azrepo.azure_rest_utils, "get_current_username")
    async def test_execute_tool_create_with_auto_assignment(self, mock_get_username, azure_workitem_tool):
        """Test execute_tool create operation with auto-assignment."""
        mock_get_username.return_value = "testuser"

        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "description": "Test description"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_create_with_explicit_assignment(self, azure_workitem_tool):
        """Test execute_tool create operation with explicit assignment."""
        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "assigned_to": "specific.user@company.com"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_create_unassigned(self, azure_workitem_tool):
        """Test execute_tool create operation with unassigned work item."""
        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "assigned_to": "none"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_create_disable_auto_assignment(self, azure_workitem_tool):
        """Test execute_tool create operation with auto-assignment disabled."""
        with mock_aiohttp_response(method="post"):
            result = await azure_workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "auto_assign_to_current_user": False
            })

            assert result["success"] is True
            assert "data" in result
