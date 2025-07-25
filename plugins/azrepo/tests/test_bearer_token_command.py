"""
Tests for AZREPO_BEARER_TOKEN_COMMAND functionality.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from plugins.azrepo.workitem_tool import AzureWorkItemTool
import plugins.azrepo.azure_rest_utils
from plugins.azrepo.tests.workitem_helpers import mock_azure_http_client


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
    # Clear bearer token cache before each test
    from plugins.azrepo.azure_rest_utils import clear_bearer_token_cache
    clear_bearer_token_cache()

    with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
        # Mock the load method
        mock_env_manager.load.return_value = None

        # Mock get_azrepo_parameters to return bearer token command (no direct token)
        mock_env_manager.get_azrepo_parameters.return_value = {
            "org": "testorg",
            "project": "test-project",
            "area_path": "TestArea\\SubArea",
            "iteration": "Sprint 1",
            "bearer_token_command": "az account get-access-token --scope \"499b84ac-1321-427f-aa17-267ca6975798/.default\""
            # No direct bearer_token - will use command
        }

        # Also patch the azure_rest_utils env_manager for the same
        with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_rest_env_manager:
            mock_rest_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "area_path": "TestArea\\SubArea",
                "iteration": "Sprint 1",
                "bearer_token_command": "az account get-access-token --scope \"499b84ac-1321-427f-aa17-267ca6975798/.default\""
                # No direct bearer_token - will use command
            }

            yield mock_env_manager


@pytest.fixture
def mock_env_manager_with_static_token():
    """Mock environment manager with static bearer token configured."""
    # Clear bearer token cache before each test
    from plugins.azrepo.azure_rest_utils import clear_bearer_token_cache
    clear_bearer_token_cache()

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

        # Also patch the azure_rest_utils env_manager for the same
        with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_rest_env_manager:
            mock_rest_env_manager.get_azrepo_parameters.return_value = {
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
    # Clear bearer token cache before each test
    from plugins.azrepo.azure_rest_utils import clear_bearer_token_cache
    clear_bearer_token_cache()

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

        # Also patch the azure_rest_utils env_manager for the same
        with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_rest_env_manager:
            mock_rest_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "area_path": "TestArea\\SubArea",
                "iteration": "Sprint 1"
                # No bearer_token or bearer_token_command
            }

            yield mock_env_manager


class TestBearerTokenCommand:
    """Test bearer token command functionality."""

    @patch("plugins.azrepo.azure_rest_utils.subprocess.run")
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
        from plugins.azrepo.azure_rest_utils import get_auth_headers
        headers = get_auth_headers(content_type="application/json-patch+json")

        # Verify the token was loaded dynamically
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer dynamic-token-from-command-123"
        assert headers["Content-Type"] == "application/json-patch+json"
        assert headers["Accept"] == "application/json"

        # Verify that subprocess.run was called with the correct command
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args
        assert "az account get-access-token --scope \"499b84ac-1321-427f-aa17-267ca6975798/.default\"" in call_args[0][0]

    def test_static_token_loading_during_auth_headers(self, mock_executor, mock_env_manager_with_static_token):
        """Test that static bearer token works correctly."""
        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)

        # Get auth headers
        from plugins.azrepo.azure_rest_utils import get_auth_headers
        headers = get_auth_headers(content_type="application/json-patch+json")

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
            from plugins.azrepo.azure_rest_utils import get_auth_headers
            get_auth_headers(content_type="application/json-patch+json")

    @patch("plugins.azrepo.azure_rest_utils.subprocess.run")
    def test_multiple_auth_header_calls_refresh_token(self, mock_subprocess_run, mock_executor, mock_env_manager_with_token_command):
        """Test that multiple calls to get auth headers use cached token within cache duration."""
        # Mock subprocess.run to simulate successful command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"accessToken": "dynamic-token-from-command-123"}'
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)

        # Call get_auth_headers multiple times
        from plugins.azrepo.azure_rest_utils import get_auth_headers
        headers1 = get_auth_headers(content_type="application/json-patch+json")
        headers2 = get_auth_headers(content_type="application/json-patch+json")
        headers3 = get_auth_headers(content_type="application/json-patch+json")

        # Verify all calls returned the same token (since our mock returns the same value)
        assert headers1["Authorization"] == "Bearer dynamic-token-from-command-123"
        assert headers2["Authorization"] == "Bearer dynamic-token-from-command-123"
        assert headers3["Authorization"] == "Bearer dynamic-token-from-command-123"

        # With caching, subprocess.run should only be called once (first call caches the token)
        assert mock_subprocess_run.call_count == 1

    @patch("plugins.azrepo.azure_rest_utils.subprocess.run")
    @patch("plugins.azrepo.azure_rest_utils.get_current_username")
    @pytest.mark.asyncio
    async def test_create_work_item_uses_dynamic_token(self, mock_get_current_username, mock_subprocess_run, mock_executor, mock_env_manager_with_token_command):
        """Test that create_work_item operation uses dynamic token loading."""
        # Mock get_current_username to avoid extra subprocess call on Windows
        mock_get_current_username.return_value = "testuser"

        # Mock subprocess.run to simulate successful command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"accessToken": "dynamic-token-from-command-123"}'
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)

        # Mock AzureHttpClient for REST API call
        response_data = {"id": 123, "fields": {"System.Title": "Test Work Item"}}
        with mock_azure_http_client(method="post", response_data=response_data) as mock_client_class:
            # Create work item
            result = await tool.create_work_item(
                title="Test Work Item",
                description="Test Description"
            )

            # Verify the operation succeeded
            assert result["success"] is True
            assert "data" in result

            # Verify that the request was made
            mock_client_class.return_value.request.assert_called_once()
            call_args = mock_client_class.return_value.request.call_args

            # Verify the method and headers
            assert call_args[0][0] == "POST"  # method
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer dynamic-token-from-command-123"

            # Verify that subprocess.run was called to get fresh token
            mock_subprocess_run.assert_called_once()


class TestBearerTokenCommandExecution:
    """Test bearer token command execution functionality in the work item tool."""

    @patch("plugins.azrepo.azure_rest_utils.subprocess.run")
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

        # Test the execute_bearer_token_command method directly
        token = plugins.azrepo.azure_rest_utils.execute_bearer_token_command("az account get-access-token --scope \"499b84ac-1321-427f-aa17-267ca6975798/.default\"")

        # Verify the token was extracted correctly
        assert token == "command-generated-token-456"

        # Verify subprocess.run was called with correct parameters
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args
        assert "az account get-access-token --scope \"499b84ac-1321-427f-aa17-267ca6975798/.default\"" in call_args[0][0]
        assert call_args[1]["shell"] is True
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["timeout"] == 30

    @patch("plugins.azrepo.azure_rest_utils.subprocess.run")
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

        # Test the execute_bearer_token_command method with failure
        token = plugins.azrepo.azure_rest_utils.execute_bearer_token_command("az account get-access-token --scope \"499b84ac-1321-427f-aa17-267ca6975798/.default\"")

        # Verify that the function returns None for a command failure
        assert token is None

        # Verify that subprocess.run was called
        mock_subprocess_run.assert_called_once()

    @patch("plugins.azrepo.azure_rest_utils.subprocess.run")
    def test_bearer_token_command_invalid_json_handling(self, mock_subprocess_run, mock_executor):
        """Test handling of invalid JSON output from bearer token command."""
        # Mock subprocess.run to simulate invalid JSON output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Not a valid JSON"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)

        # Test the execute_bearer_token_command method with invalid JSON
        token = plugins.azrepo.azure_rest_utils.execute_bearer_token_command("az account get-access-token --scope \"499b84ac-1321-427f-aa17-267ca6975798/.default\"")

        # Verify that the function returns None for invalid JSON
        assert token is None

        # Verify that subprocess.run was called
        mock_subprocess_run.assert_called_once()

    @patch("plugins.azrepo.azure_rest_utils.subprocess.run")
    def test_bearer_token_command_missing_access_token_property(self, mock_subprocess_run, mock_executor):
        """Test handling of missing accessToken property in command output."""
        # Mock subprocess.run to simulate missing accessToken property
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"token": "wrong-property-name-token-789"}'
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        # Create tool instance
        tool = AzureWorkItemTool(command_executor=mock_executor)

        # Test the execute_bearer_token_command method with missing accessToken
        token = plugins.azrepo.azure_rest_utils.execute_bearer_token_command("az account get-access-token --scope \"499b84ac-1321-427f-aa17-267ca6975798/.default\"")

        # Verify that the function returns None for missing accessToken
        assert token is None

        # Verify that subprocess.run was called
        mock_subprocess_run.assert_called_once()


class TestEndToEndBearerTokenWorkflow:
    """Test end-to-end workflow using bearer token command."""

    @patch("plugins.azrepo.azure_rest_utils.subprocess.run")
    @patch("plugins.azrepo.azure_rest_utils.get_current_username")
    @pytest.mark.asyncio
    async def test_end_to_end_create_work_item_with_token_command(self, mock_get_current_username, mock_subprocess_run, mock_executor):
        """Test complete workflow of creating a work item using bearer token command."""
        # Mock get_current_username to avoid extra subprocess call on Windows
        mock_get_current_username.return_value = "testuser"

        # Clear bearer token cache before test
        from plugins.azrepo.azure_rest_utils import clear_bearer_token_cache
        clear_bearer_token_cache()

        # Mock subprocess.run for token command
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"accessToken": "end-to-end-token-abc"}'
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        # Mock environment manager with token command
        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.load.return_value = None
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "testorg",
                "project": "test-project",
                "area_path": "TestArea\\SubArea",
                "iteration": "Sprint 1",
                "bearer_token_command": "az account get-access-token --scope \"499b84ac-1321-427f-aa17-267ca6975798/.default\""
            }

            # Also patch the azure_rest_utils env_manager
            with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_rest_env_manager:
                mock_rest_env_manager.get_azrepo_parameters.return_value = {
                    "org": "testorg",
                    "project": "test-project",
                    "area_path": "TestArea\\SubArea",
                    "iteration": "Sprint 1",
                    "bearer_token_command": "az account get-access-token --scope \"499b84ac-1321-427f-aa17-267ca6975798/.default\""
                }

                # Create tool instance
                tool = AzureWorkItemTool(command_executor=mock_executor)

                # Mock AzureHttpClient for create_work_item API call
                response_data = {"id": 456, "fields": {"System.Title": "End-to-End Test"}}
                with mock_azure_http_client(method="post", response_data=response_data) as mock_client_class:
                    # Execute the create_work_item operation
                    result = await tool.create_work_item(
                        title="End-to-End Test",
                        description="Testing end-to-end workflow with bearer token command"
                    )

                    # Verify operation success
                    assert result["success"] is True
                    assert "data" in result
                    assert result["data"]["id"] == 456

                    # Verify token command was called
                    mock_subprocess_run.assert_called_once()

                    # Verify API call with correct token
                    mock_client_class.return_value.request.assert_called_once()
                    call_args = mock_client_class.return_value.request.call_args
                    headers = call_args[1]["headers"]
                    assert headers["Authorization"] == "Bearer end-to-end-token-abc"
