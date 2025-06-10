"""
Tests for work item creation operations using REST API.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from plugins.azrepo.workitem_tool import AzureWorkItemTool


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
                "System.Description": "Test description"
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


def mock_aiohttp_for_error(status_code=401, error_message="Access denied"):
    """Helper function to mock error aiohttp calls."""
    mock_response = MagicMock()
    mock_response.status = status_code
    mock_response.text = AsyncMock(return_value=json.dumps({
        "message": error_message,
        "typeKey": "UnauthorizedRequestException"
    }))
    
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
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock environment manager
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-bearer-token-123"
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)
        return tool


@pytest.fixture
def workitem_tool_no_defaults(mock_executor):
    """Create AzureWorkItemTool instance with no defaults."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock environment manager with no defaults
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "bearer_token": "test-bearer-token-123"  # Still need bearer token
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)
        return tool


class TestCreateWorkItem:
    """Test the create_work_item method."""

    @pytest.mark.asyncio
    async def test_create_work_item_basic(self, workitem_tool):
        """Test basic work item creation."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Test Work Item",
                description="Test description"
            )

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["id"] == 12345

    @pytest.mark.asyncio
    async def test_create_work_item_with_custom_type(self, workitem_tool):
        """Test work item creation with custom type."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Bug Report",
                work_item_type="Bug"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_with_overrides(self, workitem_tool):
        """Test work item creation with parameter overrides."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Custom Work Item",
                area_path="CustomArea",
                iteration_path="Sprint 2",
                organization="customorg",
                project="custom-project"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_minimal(self, workitem_tool):
        """Test work item creation with minimal parameters."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(title="Minimal Work Item")

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_missing_org(self, workitem_tool):
        """Test work item creation with missing organization."""
        # Clear the organization
        workitem_tool.default_organization = None
        
        result = await workitem_tool.create_work_item(title="Test Work Item")

        assert result["success"] is False
        assert "Organization is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_missing_project(self, workitem_tool):
        """Test work item creation with missing project."""
        # Clear the project
        workitem_tool.default_project = None
        
        result = await workitem_tool.create_work_item(title="Test Work Item")

        assert result["success"] is False
        assert "Project is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_http_error(self, workitem_tool):
        """Test work item creation with HTTP error."""
        with mock_aiohttp_for_error(401, "Access denied"):
            result = await workitem_tool.create_work_item(title="Test Work Item")

            assert result["success"] is False
            assert "HTTP 401" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_json_parse_error(self, workitem_tool):
        """Test work item creation with JSON parsing error."""
        # Mock invalid JSON response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="Invalid JSON response")
        
        mock_session = MagicMock()
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await workitem_tool.create_work_item(title="Test Work Item")

            assert result["success"] is False
            assert "Failed to parse response" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_with_special_characters(self, workitem_tool):
        """Test work item creation with special characters."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Fix issue with 'quotes' and \"double quotes\"",
                description="Description with special chars: @#$%^&*()_+-={}[]|\\:;\"'<>?,./"
            )

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_with_unicode(self, workitem_tool):
        """Test work item creation with Unicode characters."""
        with mock_aiohttp_for_success():
            result = await workitem_tool.create_work_item(
                title="Unicode test: 测试 🚀 émojis",
                description="Description with Unicode: café naïve résumé 中文"
            )

            assert result["success"] is True
            assert "data" in result


class TestExecuteToolCreate:
    """Test the execute_tool method for create operations."""

    @pytest.mark.asyncio
    async def test_execute_tool_create_success(self, workitem_tool):
        """Test successful work item creation through execute_tool."""
        with mock_aiohttp_for_success():
            arguments = {
                "operation": "create",
                "title": "Test Work Item",
                "description": "Test description",
                "work_item_type": "User Story"
            }

            result = await workitem_tool.execute_tool(arguments)

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_create_missing_title(self, workitem_tool):
        """Test work item creation with missing title."""
        arguments = {
            "operation": "create",
            "description": "Test description"
        }

        result = await workitem_tool.execute_tool(arguments)

        assert result["success"] is False
        assert "title is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_create_empty_title(self, workitem_tool):
        """Test work item creation with empty title."""
        arguments = {
            "operation": "create",
            "title": "",
            "description": "Test description"
        }

        result = await workitem_tool.execute_tool(arguments)

        assert result["success"] is False
        assert "title is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_create_with_all_params(self, workitem_tool):
        """Test work item creation with all parameters."""
        with mock_aiohttp_for_success():
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

            result = await workitem_tool.execute_tool(arguments)

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_create_with_defaults_fallback(self, workitem_tool_no_defaults):
        """Test work item creation when no defaults are configured."""
        arguments = {
            "operation": "create",
            "title": "Work Item No Defaults",
            "organization": "testorg",
            "project": "test-project"
        }

        with mock_aiohttp_for_success():
            result = await workitem_tool_no_defaults.execute_tool(arguments)

            assert result["success"] is True
            assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_tool_create_error_propagation(self, workitem_tool):
        """Test error propagation through execute_tool."""
        with mock_aiohttp_for_error(401, "Access denied"):
            arguments = {
                "operation": "create",
                "title": "Failed Work Item"
            }

            result = await workitem_tool.execute_tool(arguments)

            assert result["success"] is False
            assert "HTTP 401" in result["error"]


class TestConfigurationLoading:
    """Test configuration loading functionality."""

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_with_work_item_defaults(self, mock_env_manager, mock_executor):
        """Test loading configuration with work item defaults."""
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "test-token"
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)

        assert tool.default_organization == "testorg"
        assert tool.default_project == "test-project"
        assert tool.default_area_path == "TestArea\\SubArea"
        assert tool.default_iteration_path == "Sprint 1"
        assert tool.bearer_token == "test-token"

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_missing_bearer_token(self, mock_env_manager, mock_executor):
        """Test loading configuration without bearer token."""
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project"
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)

        assert tool.bearer_token is None

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_exception_handling(self, mock_env_manager, mock_executor):
        """Test configuration loading with exception."""
        mock_env_manager.load.side_effect = Exception("Config error")

        tool = AzureWorkItemTool(command_executor=mock_executor)

        # Should handle exception gracefully
        assert tool.default_organization is None
        assert tool.default_project is None
        assert tool.bearer_token is None


class TestParameterHandling:
    """Test parameter handling functionality."""

    def test_get_param_with_default_explicit_value(self, workitem_tool):
        """Test parameter handling with explicit value."""
        result = workitem_tool._get_param_with_default("explicit", "default")
        assert result == "explicit"

    def test_get_param_with_default_none_value(self, workitem_tool):
        """Test parameter handling with None value."""
        result = workitem_tool._get_param_with_default(None, "default")
        assert result == "default"

    def test_get_param_with_default_both_none(self, workitem_tool):
        """Test parameter handling with both None."""
        result = workitem_tool._get_param_with_default(None, None)
        assert result is None


class TestAuthenticationHeaders:
    """Test authentication header generation."""

    def test_get_auth_headers_with_token(self, workitem_tool):
        """Test authentication headers with bearer token."""
        headers = workitem_tool._get_auth_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert headers["Content-Type"] == "application/json-patch+json"
        assert headers["Accept"] == "application/json"

    def test_get_auth_headers_without_token(self, workitem_tool):
        """Test authentication headers without bearer token."""
        workitem_tool.bearer_token = None
        
        with pytest.raises(ValueError, match="Bearer token not configured"):
            workitem_tool._get_auth_headers() 