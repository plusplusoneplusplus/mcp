"""
Tests for Azure DevOps SDK work item creation operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from plugins.azrepo.workitem_tool import AzureWorkItemTool


@pytest.fixture
def mock_executor():
    """Mock command executor."""
    executor = MagicMock()
    executor.execute_async = AsyncMock()
    executor.query_process = AsyncMock()
    return executor


@pytest.fixture
def workitem_tool_with_pat(mock_executor):
    """Create AzureWorkItemTool instance with PAT configuration."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock environment manager with PAT
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "pat": "test-pat-token-12345"
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)
        return tool


@pytest.fixture
def workitem_tool_no_pat(mock_executor):
    """Create AzureWorkItemTool instance without PAT configuration."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock environment manager without PAT
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1"
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)
        return tool


@pytest.fixture
def workitem_tool_no_config(mock_executor):
    """Create AzureWorkItemTool instance with no configuration."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock environment manager with no configuration
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {}

        tool = AzureWorkItemTool(command_executor=mock_executor)
        return tool


@pytest.fixture
def mock_work_item():
    """Mock Azure DevOps work item response."""
    work_item = Mock()
    work_item.id = 12345
    work_item.url = "https://dev.azure.com/testorg/test-project/_workitems/edit/12345"
    work_item.fields = {
        "System.Id": 12345,
        "System.Title": "Test Work Item",
        "System.WorkItemType": "Task",
        "System.State": "New",
        "System.AreaPath": "TestArea\\SubArea",
        "System.IterationPath": "Sprint 1",
        "System.Description": "Test description"
    }
    return work_item


@pytest.fixture
def mock_azure_devops_sdk():
    """Mock Azure DevOps SDK components."""
    with patch("plugins.azrepo.workitem_tool.Connection") as mock_connection, \
         patch("plugins.azrepo.workitem_tool.JsonPatchOperation") as mock_json_patch, \
         patch("plugins.azrepo.workitem_tool.BasicAuthentication") as mock_auth:
        
        # Mock authentication
        mock_credentials = Mock()
        mock_auth.return_value = mock_credentials
        
        # Mock connection
        mock_conn_instance = Mock()
        mock_connection.return_value = mock_conn_instance
        
        # Mock work item tracking client
        mock_wit_client = Mock()
        mock_conn_instance.clients.get_work_item_tracking_client.return_value = mock_wit_client
        
        # Mock JsonPatchOperation
        mock_patch_op = Mock()
        mock_json_patch.return_value = mock_patch_op
        
        yield {
            "connection": mock_connection,
            "connection_instance": mock_conn_instance,
            "wit_client": mock_wit_client,
            "auth": mock_auth,
            "credentials": mock_credentials,
            "json_patch": mock_json_patch,
            "patch_op": mock_patch_op
        }


class TestCreateWorkItemSDK:
    """Test the create_work_item_sdk method."""

    @pytest.mark.asyncio
    async def test_create_work_item_sdk_missing_pat(self, workitem_tool_no_pat):
        """Test error handling when PAT is missing."""
        result = await workitem_tool_no_pat.create_work_item_sdk(
            title="Test Work Item"
        )

        # Verify error response
        assert result["success"] is False
        assert "Personal Access Token (PAT) is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_sdk_missing_organization(self, workitem_tool_no_config):
        """Test error handling when organization is missing."""
        result = await workitem_tool_no_config.create_work_item_sdk(
            title="Test Work Item"
        )

        # Verify error response
        assert result["success"] is False
        assert "Organization URL is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_sdk_missing_project(self, workitem_tool_no_config):
        """Test error handling when project is missing."""
        # Add organization but no project
        workitem_tool_no_config.default_organization = "testorg"
        
        result = await workitem_tool_no_config.create_work_item_sdk(
            title="Test Work Item"
        )

        # Verify error response
        assert result["success"] is False
        assert "Project name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_sdk_import_error(self, workitem_tool_with_pat):
        """Test error handling when Azure DevOps SDK is not available."""
        # Mock the import to fail
        with patch('builtins.__import__', side_effect=ImportError("No module named 'azure.devops'")):
            result = await workitem_tool_with_pat.create_work_item_sdk(
                title="Test Work Item"
            )

        # Verify error response
        assert result["success"] is False
        assert "Azure DevOps SDK not available" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_sdk_basic_success(self, workitem_tool_with_pat):
        """Test basic successful work item creation using SDK."""
        # Mock the Azure DevOps SDK components
        mock_work_item = Mock()
        mock_work_item.id = 12345
        mock_work_item.url = "https://dev.azure.com/testorg/test-project/_workitems/edit/12345"
        mock_work_item.fields = {
            "System.Id": 12345,
            "System.Title": "Test Work Item",
            "System.WorkItemType": "Task",
            "System.State": "New"
        }

        mock_wit_client = Mock()
        mock_wit_client.create_work_item.return_value = mock_work_item

        mock_connection = Mock()
        mock_connection.clients.get_work_item_tracking_client.return_value = mock_wit_client

        # Patch the imports and classes, and also patch the env_manager call
        with patch('azure.devops.connection.Connection', return_value=mock_connection), \
             patch('azure.devops.v7_1.work_item_tracking.models.JsonPatchOperation') as mock_patch, \
             patch('msrest.authentication.BasicAuthentication') as mock_auth, \
             patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            
            # Mock the environment manager call within the SDK method
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "pat": "test-pat-token-12345"
            }
            
            result = await workitem_tool_with_pat.create_work_item_sdk(
                title="Test Work Item",
                description="Test description"
            )

            # Verify result structure
            assert result["success"] is True
            assert result["method"] == "sdk"
            assert result["data"]["id"] == 12345
            assert result["data"]["url"] == "https://dev.azure.com/testorg/test-project/_workitems/edit/12345"

    @pytest.mark.asyncio
    async def test_create_work_item_sdk_api_error(self, workitem_tool_with_pat):
        """Test error handling for API failures."""
        # Mock the Azure DevOps SDK to raise an exception
        mock_wit_client = Mock()
        mock_wit_client.create_work_item.side_effect = Exception("API Error: Project not found")

        mock_connection = Mock()
        mock_connection.clients.get_work_item_tracking_client.return_value = mock_wit_client

        with patch('azure.devops.connection.Connection', return_value=mock_connection), \
             patch('azure.devops.v7_1.work_item_tracking.models.JsonPatchOperation'), \
             patch('msrest.authentication.BasicAuthentication'), \
             patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            
            # Mock the environment manager call within the SDK method
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "pat": "test-pat-token-12345"
            }
            
            result = await workitem_tool_with_pat.create_work_item_sdk(
                title="Test Work Item"
            )

            # Verify error response
            assert result["success"] is False
            assert "Failed to create work item using SDK" in result["error"]
            assert "API Error: Project not found" in result["error"]

    @pytest.mark.asyncio
    async def test_create_work_item_sdk_url_formatting(self, workitem_tool_with_pat):
        """Test that organization URLs are properly formatted."""
        mock_work_item = Mock()
        mock_work_item.id = 12345
        mock_work_item.url = "https://dev.azure.com/customorg/test-project/_workitems/edit/12345"
        mock_work_item.fields = {}

        mock_wit_client = Mock()
        mock_wit_client.create_work_item.return_value = mock_work_item

        mock_connection = Mock()
        mock_connection.clients.get_work_item_tracking_client.return_value = mock_wit_client

        with patch('azure.devops.connection.Connection', return_value=mock_connection) as mock_conn_class, \
             patch('azure.devops.v7_1.work_item_tracking.models.JsonPatchOperation'), \
             patch('msrest.authentication.BasicAuthentication'), \
             patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            
            # Mock the environment manager call within the SDK method
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "pat": "test-pat-token-12345"
            }
            
            # Test with organization name only (should be formatted to full URL)
            result = await workitem_tool_with_pat.create_work_item_sdk(
                title="Test Work Item",
                organization="customorg"
            )

            # Verify the connection was created with properly formatted URL
            mock_conn_class.assert_called_once()
            call_args = mock_conn_class.call_args
            assert call_args[1]["base_url"] == "https://dev.azure.com/customorg"
            
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_work_item_sdk_https_url_preserved(self, workitem_tool_with_pat):
        """Test that HTTPS URLs are preserved as-is."""
        mock_work_item = Mock()
        mock_work_item.id = 12345
        mock_work_item.url = "https://dev.azure.com/customorg/test-project/_workitems/edit/12345"
        mock_work_item.fields = {}

        mock_wit_client = Mock()
        mock_wit_client.create_work_item.return_value = mock_work_item

        mock_connection = Mock()
        mock_connection.clients.get_work_item_tracking_client.return_value = mock_wit_client

        with patch('azure.devops.connection.Connection', return_value=mock_connection) as mock_conn_class, \
             patch('azure.devops.v7_1.work_item_tracking.models.JsonPatchOperation'), \
             patch('msrest.authentication.BasicAuthentication'), \
             patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            
            # Mock the environment manager call within the SDK method
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "pat": "test-pat-token-12345"
            }
            
            # Test with full HTTPS URL (should be preserved)
            result = await workitem_tool_with_pat.create_work_item_sdk(
                title="Test Work Item",
                organization="https://dev.azure.com/customorg"
            )

            # Verify the connection was created with the URL as-is
            mock_conn_class.assert_called_once()
            call_args = mock_conn_class.call_args
            assert call_args[1]["base_url"] == "https://dev.azure.com/customorg"
            
            assert result["success"] is True


class TestSDKConfigurationLoading:
    """Test configuration loading for SDK functionality."""

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_with_pat(self, mock_env_manager, mock_executor):
        """Test configuration loading with PAT."""
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "pat": "test-pat-token"
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)

        assert tool.default_organization == "testorg"
        assert tool.default_project == "test-project"
        assert tool.default_pat == "test-pat-token"

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_without_pat(self, mock_env_manager, mock_executor):
        """Test configuration loading without PAT."""
        mock_env_manager.load.return_value = None
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project"
        }

        tool = AzureWorkItemTool(command_executor=mock_executor)

        assert tool.default_organization == "testorg"
        assert tool.default_project == "test-project"
        assert tool.default_pat is None

    @patch("plugins.azrepo.workitem_tool.env_manager")
    def test_load_config_exception_handling_with_pat(self, mock_env_manager, mock_executor):
        """Test configuration loading exception handling includes PAT reset."""
        mock_env_manager.load.side_effect = Exception("Configuration error")

        tool = AzureWorkItemTool(command_executor=mock_executor)

        # Verify all defaults are None when configuration fails
        assert tool.default_organization is None
        assert tool.default_project is None
        assert tool.default_area_path is None
        assert tool.default_iteration_path is None
        assert tool.default_pat is None


class TestSDKIntegration:
    """Test SDK integration scenarios."""

    @pytest.mark.asyncio
    async def test_sdk_method_error_format_compatibility(self, workitem_tool_no_pat):
        """Test that SDK method error format is compatible with CLI method."""
        result = await workitem_tool_no_pat.create_work_item_sdk(
            title="Test Work Item"
        )

        # Verify error format matches CLI method format
        assert result["success"] is False
        assert "error" in result
        assert isinstance(result["error"], str)

    @pytest.mark.asyncio
    async def test_sdk_method_parameter_compatibility(self, workitem_tool_with_pat):
        """Test that SDK method accepts the same parameters as CLI method."""
        # This test verifies the method signature is compatible
        # We expect it to fail due to missing PAT, but it should accept all parameters
        
        # Test with all parameters that the CLI method accepts
        result = await workitem_tool_with_pat.create_work_item_sdk(
            title="Test Work Item",
            description="Test description",
            work_item_type="Bug",
            area_path="TestArea",
            iteration_path="Sprint 1",
            organization="testorg",
            project="test-project"
        )

        # The method should handle all parameters without throwing a TypeError
        # The actual result depends on whether the SDK is available
        assert "success" in result
        assert isinstance(result["success"], bool) 