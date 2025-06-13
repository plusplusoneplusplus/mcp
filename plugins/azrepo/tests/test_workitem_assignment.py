"""
Tests for work item assignment functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch
import plugins.azrepo.azure_rest_utils
from plugins.azrepo.azure_rest_utils import IdentityInfo

from plugins.azrepo.tests.test_helpers import (
    BaseTestClass,
    assert_http_client_called_with_method,
    assert_success_response,
    mock_azure_http_client_context,
)


class TestWorkItemAssignment(BaseTestClass):
    """Test work item assignment functionality."""

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_auto_assign_to_current_user(self, mock_validate_assignee, azure_workitem_tool):
        """Test automatic assignment to current user."""
        mock_validate_assignee.return_value = ("testuser@company.com", "")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                description="Test description"
            )

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")
            mock_validate_assignee.assert_called_once()

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_auto_assign_to_current_user_no_username(self, mock_validate_assignee, azure_workitem_tool):
        """Test auto-assignment when current user cannot be determined."""
        mock_validate_assignee.return_value = (None, "Unable to determine current user for assignment")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                description="Test description"
            )

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_explicit_assignment(self, mock_validate_assignee, azure_workitem_tool):
        """Test explicit user assignment."""
        mock_validate_assignee.return_value = ("specific.user@company.com", "")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                assigned_to="specific.user@company.com"
            )

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")
            mock_validate_assignee.assert_called_once_with(
                "specific.user@company.com", "testorg", "test-project", fallback_to_current_user=False
            )

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_unassigned_work_item(self, mock_validate_assignee, azure_workitem_tool):
        """Test creating unassigned work items."""
        mock_validate_assignee.return_value = (None, "")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                assigned_to="none"
            )

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_disable_auto_assignment(self, mock_validate_assignee, azure_workitem_tool):
        """Test disabling auto-assignment."""
        # When auto-assignment is disabled, no assignee should be resolved
        mock_validate_assignee.return_value = (None, "")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                auto_assign_to_current_user=False
            )

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_auto_assignment_with_config_disabled(self, mock_validate_assignee, azure_workitem_tool_no_auto_assign):
        """Test that auto-assignment respects configuration setting."""
        # When auto-assignment is disabled in config, no assignee should be resolved
        mock_validate_assignee.return_value = (None, "")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool_no_auto_assign.create_work_item(
                title="Test Work Item"
            )

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")


class TestExecuteToolAssignment:
    """Test assignment functionality through execute_tool method."""

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_execute_tool_create_with_auto_assignment(self, mock_validate_assignee, azure_workitem_tool):
        """Test execute_tool create operation with auto-assignment."""
        mock_validate_assignee.return_value = ("testuser@company.com", "")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "description": "Test description"
            })

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_execute_tool_create_with_explicit_assignment(self, mock_validate_assignee, azure_workitem_tool):
        """Test execute_tool create operation with explicit assignment."""
        mock_validate_assignee.return_value = ("specific.user@company.com", "")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "assigned_to": "specific.user@company.com"
            })

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_execute_tool_create_unassigned(self, mock_validate_assignee, azure_workitem_tool):
        """Test execute_tool create operation with unassigned work item."""
        mock_validate_assignee.return_value = (None, "")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "assigned_to": "none"
            })

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_execute_tool_create_disable_auto_assignment(self, mock_validate_assignee, azure_workitem_tool):
        """Test execute_tool create operation with auto-assignment disabled."""
        mock_validate_assignee.return_value = (None, "")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "auto_assign_to_current_user": False
            })

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")


class TestWorkItemAssignmentWithIdentityResolution(BaseTestClass):
    """Test work item assignment with identity resolution scenarios."""

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_assignment_with_identity_resolution_failure(self, mock_validate_assignee, azure_workitem_tool):
        """Test work item creation when identity resolution fails."""
        mock_validate_assignee.return_value = (None, "Unable to resolve identity 'invalid@user.com': Identity not found")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                assigned_to="invalid@user.com"
            )

            # Work item should still be created successfully, just unassigned
            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_assignment_with_combo_format_identity(self, mock_validate_assignee, azure_workitem_tool):
        """Test work item creation with combo format identity."""
        mock_validate_assignee.return_value = ("john.doe@company.com", "")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                assigned_to="John Doe <john.doe@company.com>"
            )

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")
            mock_validate_assignee.assert_called_once_with(
                "John Doe <john.doe@company.com>", "testorg", "test-project", fallback_to_current_user=False
            )

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_assignment_with_display_name_resolution(self, mock_validate_assignee, azure_workitem_tool):
        """Test work item creation with display name that gets resolved to email."""
        mock_validate_assignee.return_value = ("john.doe@company.com", "")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                assigned_to="John Doe"
            )

            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")
            mock_validate_assignee.assert_called_once_with(
                "John Doe", "testorg", "test-project", fallback_to_current_user=False
            )

    @pytest.mark.asyncio
    @patch("plugins.azrepo.workitem_tool.validate_and_format_assignee")
    async def test_assignment_exception_handling(self, mock_validate_assignee, azure_workitem_tool):
        """Test work item creation when identity validation raises an exception."""
        mock_validate_assignee.side_effect = Exception("API connection error")

        with mock_azure_http_client_context(method="post") as mock_client:
            result = await azure_workitem_tool.create_work_item(
                title="Test Work Item",
                assigned_to="test@user.com"
            )

            # Work item should still be created successfully, just unassigned
            assert_success_response(result)
            assert_http_client_called_with_method(mock_client, "request")
