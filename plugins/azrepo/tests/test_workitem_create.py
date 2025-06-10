"""Tests for AzureWorkItemTool creation functionality."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import aiohttp

from plugins.azrepo.workitem_tool import AzureWorkItemTool
from plugins.azrepo.azure_rest_utils import get_auth_headers, build_api_url

# Shared mock context managers
def mock_aiohttp_for_success():
    """Mock aiohttp to return a successful response."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=json.dumps({
        "id": 12345,
        "fields": {
            "System.Title": "Test Work Item",
            "System.Description": "Test Description",
            "System.CreatedBy": {
                "displayName": "Test User",
                "id": "test-user-id",
                "uniqueName": "test@example.com"
            },
            "System.CreatedDate": "2023-01-01T00:00:00Z",
            "System.State": "New",
            "System.WorkItemType": "Task"
        },
        "url": "https://dev.azure.com/testorg/test-project/_apis/wit/workitems/12345"
    }))

    mock_session = MagicMock()
    mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    return patch("aiohttp.ClientSession", return_value=mock_session)

def mock_aiohttp_for_error(status_code=500, error_message="Internal Server Error"):
    """Mock aiohttp to return an error response."""
    error_response = {
        "message": error_message,
        "typeKey": "Error"
    }

    mock_response = MagicMock()
    mock_response.status = status_code
    mock_response.text = AsyncMock(return_value=json.dumps(error_response))

    mock_session = MagicMock()
    mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    return patch("aiohttp.ClientSession", return_value=mock_session)

# Common fixtures
@pytest.fixture
def mock_executor():
    """Create a mock CommandExecutor instance."""
    executor = MagicMock()
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
        "bearer_token": "test-bearer-token-123"
    }
    
    # Also patch the azure_rest_utils env_manager
    rest_patcher = patch("plugins.azrepo.azure_rest_utils.env_manager")
    mock_rest_env_manager = rest_patcher.start()
    mock_rest_env_manager.get_azrepo_parameters.return_value = {
        "org": "testorg",
        "project": "test-project", 
        "area_path": "TestArea\\SubArea",
        "iteration": "Sprint 1",
        "bearer_token": "test-bearer-token-123"
    }

    tool = AzureWorkItemTool(command_executor=mock_executor)

    yield tool

    # Clean up the patches
    patcher.stop()
    rest_patcher.stop()

@pytest.fixture
def workitem_tool_no_defaults(mock_executor):
    """Create AzureWorkItemTool instance with no defaults."""
    # Use a persistent patch that lasts for the entire test
    patcher = patch("plugins.azrepo.workitem_tool.env_manager")
    mock_env_manager = patcher.start()

    # Mock environment manager with no defaults
    mock_env_manager.load.return_value = None
    mock_env_manager.get_azrepo_parameters.return_value = {
        "bearer_token": "test-bearer-token-123"  # Still need bearer token
    }
    
    # Also patch the azure_rest_utils env_manager
    rest_patcher = patch("plugins.azrepo.azure_rest_utils.env_manager")
    mock_rest_env_manager = rest_patcher.start()
    mock_rest_env_manager.get_azrepo_parameters.return_value = {
        "bearer_token": "test-bearer-token-123"  # Still need bearer token
    }

    tool = AzureWorkItemTool(command_executor=mock_executor)

    yield tool

    # Clean up the patches
    patcher.stop()
    rest_patcher.stop()

class TestCreateWorkItem:
    """Test the create_work_item method."""

    @pytest.mark.asyncio
    async def test_create_work_item_basic(self, workitem_tool):
        """Test basic work item creation."""
        # Patch the utility functions
        with patch("plugins.azrepo.workitem_tool.get_auth_headers", return_value={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }):
            with patch("plugins.azrepo.workitem_tool.build_api_url", 
                      return_value="https://dev.azure.com/testorg/testproject/_apis/wit/workitems/$Task?api-version=7.1"):
                with mock_aiohttp_for_success():
                    result = await workitem_tool.create_work_item(
                        title="Test Work Item",
                        description="Test description"
                    )

                    assert result["success"] is True
                    assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_with_custom_type(self, workitem_tool):
        """Test work item creation with custom type."""
        # Patch the utility functions
        with patch("plugins.azrepo.workitem_tool.get_auth_headers", return_value={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }):
            with patch("plugins.azrepo.workitem_tool.build_api_url", 
                      return_value="https://dev.azure.com/testorg/testproject/_apis/wit/workitems/$Bug?api-version=7.1"):
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
        # Patch the utility functions
        with patch("plugins.azrepo.workitem_tool.get_auth_headers", return_value={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }):
            with patch("plugins.azrepo.workitem_tool.build_api_url", 
                      return_value="https://dev.azure.com/customorg/custom-project/_apis/wit/workitems/$Task?api-version=7.1"):
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
        # Patch the utility functions
        with patch("plugins.azrepo.workitem_tool.get_auth_headers", return_value={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }):
            with patch("plugins.azrepo.workitem_tool.build_api_url", 
                      return_value="https://dev.azure.com/testorg/testproject/_apis/wit/workitems/$Task?api-version=7.1"):
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
        # Patch the utility functions
        with patch("plugins.azrepo.workitem_tool.get_auth_headers", return_value={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }):
            with patch("plugins.azrepo.workitem_tool.build_api_url", 
                      return_value="https://dev.azure.com/testorg/testproject/_apis/wit/workitems/$Task?api-version=7.1"):
                with mock_aiohttp_for_error(401, "Access denied"):
                    result = await workitem_tool.create_work_item(title="Test Work Item")

                    assert result["success"] is False
                    assert "HTTP 401" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_json_parse_error(self, workitem_tool):
        """Test work item creation with JSON parsing error."""
        # Patch the utility functions
        with patch("plugins.azrepo.workitem_tool.get_auth_headers", return_value={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }):
            with patch("plugins.azrepo.workitem_tool.build_api_url", 
                      return_value="https://dev.azure.com/testorg/testproject/_apis/wit/workitems/$Task?api-version=7.1"):
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
        # Patch the utility functions
        with patch("plugins.azrepo.workitem_tool.get_auth_headers", return_value={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }):
            with patch("plugins.azrepo.workitem_tool.build_api_url", 
                      return_value="https://dev.azure.com/testorg/testproject/_apis/wit/workitems/$Task?api-version=7.1"):
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
        # Patch the utility functions
        with patch("plugins.azrepo.workitem_tool.get_auth_headers", return_value={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }):
            with patch("plugins.azrepo.workitem_tool.build_api_url", 
                      return_value="https://dev.azure.com/testorg/testproject/_apis/wit/workitems/$Task?api-version=7.1"):
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
            "title": "Test Work Item",
            "organization": "customorg",
            "project": "custom-project"
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
        with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_env_manager:
            mock_env_manager.get_azrepo_parameters.return_value = {
                "bearer_token": "test-bearer-token-123"
            }
            
            headers = get_auth_headers("application/json-patch+json")

            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Bearer ")
            assert headers["Content-Type"] == "application/json-patch+json"
            assert headers["Accept"] == "application/json"

    def test_get_auth_headers_without_token(self, workitem_tool):
        """Test authentication headers without bearer token."""
        # Mock the environment manager to return no bearer token
        with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_env_manager:
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project"
                # No bearer_token or bearer_token_command
            }

            # Test that a ValueError is raised when no token is available
            with pytest.raises(ValueError, match="Bearer token not configured"):
                get_auth_headers()


class TestCreateWorkItemNoDefaults:
    """Tests for work item creation with no default values."""

    @pytest.mark.asyncio
    async def test_create_work_item_no_defaults(self, workitem_tool_no_defaults):
        """Test work item creation with all required parameters."""
        # Patch the utility functions
        with patch("plugins.azrepo.workitem_tool.get_auth_headers", return_value={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }):
            with patch("plugins.azrepo.workitem_tool.build_api_url", 
                      return_value="https://dev.azure.com/customorg/custom-project/_apis/wit/workitems/$Task?api-version=7.1"):
                with mock_aiohttp_for_success():
                    result = await workitem_tool_no_defaults.create_work_item(
                        title="Test Work Item",
                        area_path="CustomArea",
                        iteration_path="Sprint 2",
                        organization="customorg",
                        project="custom-project"
                    )

                    assert result["success"] is True
                    assert "data" in result

    @pytest.mark.asyncio
    async def test_create_work_item_missing_org(self, workitem_tool_no_defaults):
        """Test work item creation with missing org."""
        # We need to patch the check inside create_work_item, which happens before API calls
        # Ensure workitem_tool_no_defaults has empty defaults
        workitem_tool_no_defaults.default_organization = None
        workitem_tool_no_defaults.default_project = "custom-project"
        
        result = await workitem_tool_no_defaults.create_work_item(
            title="Test Work Item",
            project="custom-project"
        )
        
        assert result["success"] is False
        assert "Organization is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_missing_project(self, workitem_tool_no_defaults):
        """Test work item creation with missing project."""
        # We need to patch the check inside create_work_item, which happens before API calls
        # Ensure workitem_tool_no_defaults has empty defaults
        workitem_tool_no_defaults.default_organization = "customorg"
        workitem_tool_no_defaults.default_project = None
        
        result = await workitem_tool_no_defaults.create_work_item(
            title="Test Work Item",
            organization="customorg"
        )
        
        assert result["success"] is False
        assert "Project is required" in result["error"]
