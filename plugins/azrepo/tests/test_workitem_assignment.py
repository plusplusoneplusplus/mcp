"""
Tests for work item assignment functionality.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from plugins.azrepo.workitem_tool import AzureWorkItemTool
import plugins.azrepo.azure_rest_utils


def mock_aiohttp_for_success(work_item_data=None):
    """Helper function to mock successful aiohttp calls."""
    if work_item_data is None:
        work_item_data = {
            "id": 12345,
            "fields": {
                "System.Title": "Test Work Item",
                "System.WorkItemType": "Task",
                "System.State": "New",
                "System.AreaPath": "TestArea\\SubArea",
                "System.IterationPath": "Sprint 1",
                "System.Description": "Test description",
                "System.AssignedTo": {
                    "displayName": "Test User",
                    "uniqueName": "testuser@company.com"
                }
            }
        }

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=json.dumps(work_item_data))

    mock_session = MagicMock()
    mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    return patch("aiohttp.ClientSession", return_value=mock_session)


@pytest.fixture
def mock_executor():
    """Mock command executor."""
    executor = MagicMock()
    executor.execute_async = AsyncMock()
    executor.query_process = AsyncMock()
    return executor


@pytest.fixture
def workitem_tool(mock_executor):
    """Create AzureWorkItemTool instance with mocked executor."""
    # Use a persistent patch that lasts for the entire test
    patcher = patch("plugins.azrepo.workitem_tool.env_manager")
    mock_env_manager = patcher.start()

    # Mock environment manager
    mock_env_manager.load.return_value = None
    mock_env_manager.get_azrepo_parameters.return_value = {
        "org": "testorg",
        "project": "test-project",
        "area_path": "TestArea\\SubArea",
        "iteration": "Sprint 1",
        "bearer_token": "test-bearer-token-123",
        "auto_assign_to_current_user": True,
        "default_assignee": None
    }

    # Also patch the azure_rest_utils env_manager to avoid bearer token error
    auth_patcher = patch("plugins.azrepo.azure_rest_utils.env_manager")
    mock_rest_env_manager = auth_patcher.start()
    mock_rest_env_manager.get_azrepo_parameters.return_value = {
        "org": "testorg",
        "project": "test-project",
        "area_path": "TestArea\\SubArea",
        "iteration": "Sprint 1",
        "bearer_token": "test-bearer-token-123",
        "auto_assign_to_current_user": True,
        "default_assignee": None
    }

    tool = AzureWorkItemTool(command_executor=mock_executor)

    yield tool

    # Clean up the patches
    patcher.stop()
    auth_patcher.stop()


@pytest.fixture
def workitem_tool_no_auto_assign(mock_executor):
    """Create AzureWorkItemTool instance with auto-assignment disabled."""
    # Use a persistent patch that lasts for the entire test
    patcher = patch("plugins.azrepo.workitem_tool.env_manager")
    mock_env_manager = patcher.start()

    # Mock environment manager with auto-assignment disabled
    mock_env_manager.load.return_value = None
    mock_env_manager.get_azrepo_parameters.return_value = {
        "org": "testorg",
        "project": "test-project",
        "area_path": "TestArea\\SubArea",
        "iteration": "Sprint 1",
        "bearer_token": "test-bearer-token-123",
        "auto_assign_to_current_user": False,
        "default_assignee": None
    }

    # Also patch the azure_rest_utils env_manager to avoid bearer token error
    auth_patcher = patch("plugins.azrepo.azure_rest_utils.env_manager")
    mock_rest_env_manager = auth_patcher.start()
    mock_rest_env_manager.get_azrepo_parameters.return_value = {
        "org": "testorg",
        "project": "test-project",
        "area_path": "TestArea\\SubArea",
        "iteration": "Sprint 1",
        "bearer_token": "test-bearer-token-123",
        "auto_assign_to_current_user": False,
        "default_assignee": None
    }

    tool = AzureWorkItemTool(command_executor=mock_executor)

    yield tool

    # Clean up the patches
    patcher.stop()
    auth_patcher.stop()


class TestWorkItemAssignment:
    """Test work item assignment functionality."""

    @pytest.mark.asyncio
    @patch.object(plugins.azrepo.azure_rest_utils, "get_current_username")
    async def test_auto_assign_to_current_user(self, mock_get_username, workitem_tool):
        """Test automatic assignment to current user."""
        mock_get_username.return_value = "testuser"

        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Test Work Item",
                description="Test description"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    @patch.object(plugins.azrepo.azure_rest_utils, "get_current_username")
    async def test_auto_assign_to_current_user_no_username(self, mock_get_username, workitem_tool):
        """Test auto-assignment when current user cannot be determined."""
        mock_get_username.return_value = None

        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Test Work Item",
                description="Test description"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_explicit_assignment(self, workitem_tool):
        """Test explicit user assignment."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Test Work Item",
                assigned_to="specific.user@company.com"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_unassigned_work_item(self, workitem_tool):
        """Test creating unassigned work items."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Test Work Item",
                assigned_to="none"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_disable_auto_assignment(self, workitem_tool):
        """Test disabling auto-assignment."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Test Work Item",
                auto_assign_to_current_user=False
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    @patch.object(plugins.azrepo.azure_rest_utils, "get_current_username")
    async def test_auto_assignment_with_config_disabled(self, mock_get_username, workitem_tool_no_auto_assign):
        """Test that auto-assignment respects configuration setting."""
        mock_get_username.return_value = "testuser"

        with mock_aiohttp_for_success():
            result = await workitem_tool_no_auto_assign.create_work_item(
                title="Test Work Item"
            )

            assert result["success"] is True
            assert "data" in result


class TestExecuteToolAssignment:
    """Test assignment functionality through execute_tool method."""

    @pytest.mark.asyncio
    @patch.object(plugins.azrepo.azure_rest_utils, "get_current_username")
    async def test_execute_tool_create_with_auto_assignment(self, mock_get_username, workitem_tool):
        """Test execute_tool create operation with auto-assignment."""
        mock_get_username.return_value = "testuser"

        with mock_aiohttp_for_success():
            result = await workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "description": "Test description"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_create_with_explicit_assignment(self, workitem_tool):
        """Test execute_tool create operation with explicit assignment."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "assigned_to": "specific.user@company.com"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_create_unassigned(self, workitem_tool):
        """Test execute_tool create operation with unassigned work item."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "assigned_to": "none"
            })

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_create_disable_auto_assignment(self, workitem_tool):
        """Test execute_tool create operation with auto-assignment disabled."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.execute_tool({
                "operation": "create",
                "title": "Test Work Item",
                "auto_assign_to_current_user": False
            })

            assert result["success"] is True
            assert "data" in result


class TestCurrentUsernameDetection:
    """Test current username detection functionality."""

    @patch("plugins.azrepo.azure_rest_utils.getpass.getuser")
    def test_get_current_username_success(self, mock_getuser, workitem_tool):
        """Test successful username detection."""
        mock_getuser.return_value = "testuser"

        username = workitem_tool._get_current_username()

        assert username == "testuser"
        mock_getuser.assert_called_once()

    @patch("plugins.azrepo.azure_rest_utils.os.environ")
    @patch("plugins.azrepo.azure_rest_utils.getpass.getuser")
    def test_get_current_username_fallback_to_env(self, mock_getuser, mock_environ, workitem_tool):
        """Test username detection fallback to environment variables."""
        mock_getuser.side_effect = Exception("getuser failed")
        mock_environ.get.side_effect = lambda key: "envuser" if key == "USER" else None

        username = workitem_tool._get_current_username()

        assert username == "envuser"
        mock_getuser.assert_called_once()

    @patch("plugins.azrepo.azure_rest_utils.os.environ")
    @patch("plugins.azrepo.azure_rest_utils.getpass.getuser")
    def test_get_current_username_failure(self, mock_getuser, mock_environ, workitem_tool):
        """Test username detection failure."""
        mock_getuser.side_effect = Exception("getuser failed")
        mock_environ.get.return_value = None

        username = workitem_tool._get_current_username()

        assert username is None
        mock_getuser.assert_called_once()


class TestConfigurationLoading:
    """Test configuration loading for assignment preferences."""

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_with_assignment_defaults(self, mock_env_manager, mock_executor):
        """Test configuration loading with assignment defaults."""
        # Mock environment manager
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "bearer_token": "test-token",
            "auto_assign_to_current_user": False,
            "default_assignee": "default.user@company.com"
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)

        assert tool.auto_assign_to_current_user is False
        assert tool.default_assignee == "default.user@company.com"

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_without_assignment_config(self, mock_env_manager, mock_executor):
        """Test configuration loading without assignment configuration."""
        # Mock environment manager without assignment config
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "bearer_token": "test-token"
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)

        # Should use defaults
        assert tool.auto_assign_to_current_user is True
        assert tool.default_assignee is None
