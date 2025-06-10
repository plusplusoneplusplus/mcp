"""
Tests for AZREPO_BEARER_TOKEN_COMMAND functionality.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from plugins.azrepo.workitem_tool import AzureWorkItemTool


@pytest.fixture
def mock_executor():
    """Create a mock command executor."""
    executor = MagicMock()
    executor.execute_async = AsyncMock()
    executor.query_process = AsyncMock()
    return executor


@pytest.fixture
def mock_env_manager_with_token_command():
    """Mock environment manager with bearer token command configured."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock the load method
        mock_env_manager.load.return_value = None
        
        # Mock get_azrepo_parameters to return bearer token command (no direct token)
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token_command": "az account get-access-token --resource https://dev.azure.com/"
            # No direct bearer_token - will use command
        }
        
        yield mock_env_manager


@pytest.fixture
def mock_env_manager_with_static_token():
    """Mock environment manager with static bearer token configured."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock the load method
        mock_env_manager.load.return_value = None
        
        # Mock get_azrepo_parameters to return static token
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token": "static-token-123"
        }
        yield mock_env_manager


@pytest.fixture
def mock_env_manager_no_token():
    """Mock environment manager with no bearer token configured."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock the load method
        mock_env_manager.load.return_value = None
        
        # Mock get_azrepo_parameters to return no token
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1"
            # No bearer_token or bearer_token_command
        }
        yield mock_env_manager


class TestBearerTokenCommand:
    """Test bearer token command functionality."""

    @patch("plugins.azrepo.workitem_tool.subprocess.run")
    def test_dynamic_token_loading_during_auth_headers(self, mock_subprocess_run, mock_executor, mock_env_manager_with_token_command):
        """Test that bearer token is dynamically loaded when getting auth headers."""
        # Mock subprocess.run to simulate successful command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"accessToken": "dynamic-token-from-command-123"}'
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)
        
        # Get auth headers - this should trigger dynamic token loading
        headers = tool._get_auth_headers()
        
        # Verify the token was loaded dynamically
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer dynamic-token-from-command-123"
        assert headers["Content-Type"] == "application/json-patch+json"
        assert headers["Accept"] == "application/json"
        
        # Verify that subprocess.run was called with the correct command
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args
        assert "az account get-access-token --resource https://dev.azure.com/" in call_args[0][0]

    def test_static_token_loading_during_auth_headers(self, mock_executor, mock_env_manager_with_static_token):
        """Test that static bearer token works correctly."""
        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)
        
        # Get auth headers
        headers = tool._get_auth_headers()
        
        # Verify the static token was used
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer static-token-123"
        assert headers["Content-Type"] == "application/json-patch+json"
        assert headers["Accept"] == "application/json"

    def test_no_token_configured_error(self, mock_executor, mock_env_manager_no_token):
        """Test that appropriate error is raised when no token is configured."""
        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)
        
        # Getting auth headers should raise an error
        with pytest.raises(ValueError, match="Bearer token not configured"):
            tool._get_auth_headers()

    @patch("plugins.azrepo.workitem_tool.subprocess.run")
    def test_multiple_auth_header_calls_refresh_token(self, mock_subprocess_run, mock_executor, mock_env_manager_with_token_command):
        """Test that multiple calls to get auth headers refresh the token each time."""
        # Mock subprocess.run to simulate successful command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"accessToken": "dynamic-token-from-command-123"}'
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)
        
        # Call get_auth_headers multiple times
        headers1 = tool._get_auth_headers()
        headers2 = tool._get_auth_headers()
        headers3 = tool._get_auth_headers()
        
        # Verify all calls returned the same token (since our mock returns the same value)
        assert headers1["Authorization"] == "Bearer dynamic-token-from-command-123"
        assert headers2["Authorization"] == "Bearer dynamic-token-from-command-123"
        assert headers3["Authorization"] == "Bearer dynamic-token-from-command-123"
        
        # Verify that subprocess.run was called multiple times (once for each auth header request)
        assert mock_subprocess_run.call_count == 3

    @patch("plugins.azrepo.workitem_tool.subprocess.run")
    @pytest.mark.asyncio
    async def test_create_work_item_uses_dynamic_token(self, mock_subprocess_run, mock_executor, mock_env_manager_with_token_command):
        """Test that create_work_item operation uses dynamic token loading."""
        # Mock subprocess.run to simulate successful command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"accessToken": "dynamic-token-from-command-123"}'
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)
        
        # Mock aiohttp session for REST API call
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"id": 123, "fields": {"System.Title": "Test Work Item"}}')
            
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock()
            mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_class.return_value = mock_session
            
            # Create work item
            result = await tool.create_work_item(
                title="Test Work Item",
                description="Test Description"
            )
            
            # Verify the operation succeeded
            assert result["success"] is True
            assert "data" in result
            
            # Verify that the POST request was made with the correct authorization header
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer dynamic-token-from-command-123"
            
            # Verify that subprocess.run was called to get fresh token
            mock_subprocess_run.assert_called_once()


class TestBearerTokenCommandExecution:
    """Test bearer token command execution functionality in the work item tool."""

    @patch("plugins.azrepo.workitem_tool.subprocess.run")
    def test_bearer_token_command_execution_success(self, mock_subprocess_run, mock_executor):
        """Test successful bearer token command execution."""
        # Mock subprocess.run to simulate command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"accessToken": "command-generated-token-456"}'
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)
        
        # Test the _execute_bearer_token_command method directly
        token = tool._execute_bearer_token_command("az account get-access-token --resource https://dev.azure.com/")
        
        # Verify the token was extracted correctly
        assert token == "command-generated-token-456"
        
        # Verify subprocess.run was called with correct parameters
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args
        assert "az account get-access-token --resource https://dev.azure.com/" in call_args[0][0]
        assert call_args[1]["shell"] is True
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["timeout"] == 30

    @patch("plugins.azrepo.workitem_tool.subprocess.run")
    def test_bearer_token_command_failure_handling(self, mock_subprocess_run, mock_executor):
        """Test handling of bearer token command failures."""
        # Mock subprocess.run to simulate command failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Authentication failed"
        mock_subprocess_run.return_value = mock_result
        
        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)
        
        # Test the _execute_bearer_token_command method with failure
        token = tool._execute_bearer_token_command("az account get-access-token --resource https://dev.azure.com/")
        
        # Verify no token was returned
        assert token is None

    @patch("plugins.azrepo.workitem_tool.subprocess.run")
    def test_bearer_token_command_invalid_json_handling(self, mock_subprocess_run, mock_executor):
        """Test handling of invalid JSON from bearer token command."""
        # Mock subprocess.run to simulate invalid JSON output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "invalid json output"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)
        
        # Test the _execute_bearer_token_command method with invalid JSON
        token = tool._execute_bearer_token_command("az account get-access-token --resource https://dev.azure.com/")
        
        # Verify no token was returned
        assert token is None

    @patch("plugins.azrepo.workitem_tool.subprocess.run")
    def test_bearer_token_command_missing_access_token_property(self, mock_subprocess_run, mock_executor):
        """Test handling of JSON without accessToken property."""
        # Mock subprocess.run to simulate JSON without accessToken
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"someOtherProperty": "value"}'
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)
        
        # Test the _execute_bearer_token_command method
        token = tool._execute_bearer_token_command("az account get-access-token --resource https://dev.azure.com/")
        
        # Verify no token was returned
        assert token is None


class TestEndToEndBearerTokenWorkflow:
    """Test end-to-end workflow with bearer token command."""

    @patch("plugins.azrepo.workitem_tool.subprocess.run")
    @pytest.mark.asyncio
    async def test_end_to_end_create_work_item_with_token_command(self, mock_subprocess_run, mock_executor):
        """Test complete workflow of creating work item with bearer token command."""
        
        # Mock subprocess.run to simulate successful command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"accessToken": "fresh-token-from-command-789"}'
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result
        
        # Mock environment manager to simulate bearer token command configuration
        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.load.return_value = None
            
            # Simulate the environment manager providing the command configuration
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "area_path": "TestArea\\SubArea", 
                "iteration": "Sprint 1",
                "bearer_token_command": "az account get-access-token --resource https://dev.azure.com/"
                # No direct bearer_token - will use command
            }
            
            # Create tool instance
            tool = AzureWorkItemTool(command_executor=mock_executor)
            
            # Mock aiohttp for REST API call
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = MagicMock()
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(return_value='{"id": 456, "fields": {"System.Title": "Dynamic Token Test"}}')
                
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session.post = MagicMock()
                mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
                mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
                
                mock_session_class.return_value = mock_session
                
                # Execute tool via the main interface
                result = await tool.execute_tool({
                    "operation": "create",
                    "title": "Dynamic Token Test",
                    "description": "Testing dynamic token loading"
                })
                
                # Verify success
                assert result["success"] is True
                assert result["data"]["id"] == 456
                
                # Verify the correct token was used in the request
                mock_session.post.assert_called_once()
                call_args = mock_session.post.call_args
                headers = call_args[1]["headers"]
                assert headers["Authorization"] == "Bearer fresh-token-from-command-789"
                
                # Verify subprocess.run was called to execute the command
                mock_subprocess_run.assert_called_once() 