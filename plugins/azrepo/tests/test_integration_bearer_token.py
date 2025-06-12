"""
Integration test for AZREPO_BEARER_TOKEN_COMMAND functionality.
This test demonstrates the complete workflow from environment configuration to work item creation.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from plugins.azrepo.workitem_tool import AzureWorkItemTool
import plugins.azrepo.azure_rest_utils
from plugins.azrepo.tests.workitem_helpers import mock_azure_http_client


class TestBearerTokenCommandIntegration:
    """Integration tests for bearer token command functionality."""

    @patch("plugins.azrepo.azure_rest_utils.subprocess.run")
    @pytest.mark.asyncio
    async def test_complete_workflow_with_bearer_token_command(self, mock_subprocess_run):
        """Test the complete workflow: environment config -> command execution -> work item creation."""

        # Clear bearer token cache before test
        from plugins.azrepo.azure_rest_utils import clear_bearer_token_cache
        clear_bearer_token_cache()

        # Step 1: Mock the bearer token command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6...",  # Simulated JWT token
            "expiresOn": "2024-01-20 12:00:00.000000",
            "subscription": "12345678-1234-1234-1234-123456789012",
            "tenant": "87654321-4321-4321-4321-210987654321",
            "tokenType": "Bearer"
        })
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        # Step 2: Mock environment manager to provide bearer token command configuration
        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.load.return_value = None
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "mycompany",
                "project": "MyProject",
                "area_path": "MyProject\\Development\\Backend",
                "iteration": "MyProject\\Sprint 1",
                "bearer_token_command": "az account get-access-token --resource https://dev.azure.com/"
            }

            # Also patch the azure_rest_utils env_manager
            with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_rest_env_manager:
                mock_rest_env_manager.get_azrepo_parameters.return_value = {
                    "org": "mycompany",
                    "project": "MyProject",
                    "area_path": "MyProject\\Development\\Backend",
                    "iteration": "MyProject\\Sprint 1",
                    "bearer_token_command": "az account get-access-token --resource https://dev.azure.com/"
                }

                # Step 3: Create tool instance (simulates user creating the tool)
                mock_executor = MagicMock()
                tool = AzureWorkItemTool(command_executor=mock_executor)

                # Step 4: Mock the REST API response for work item creation
                response_data = {
                    "id": 12345,
                    "rev": 1,
                    "fields": {
                        "System.Id": 12345,
                        "System.Title": "Implement user authentication",
                        "System.Description": "Add OAuth2 authentication to the application",
                        "System.WorkItemType": "Task",
                        "System.State": "New",
                        "System.AreaPath": "MyProject\\Development\\Backend",
                        "System.IterationPath": "MyProject\\Sprint 1",
                        "System.CreatedDate": "2024-01-20T10:00:00.000Z",
                        "System.CreatedBy": {
                            "displayName": "John Doe",
                            "uniqueName": "john.doe@company.com"
                        }
                    },
                    "url": "https://dev.azure.com/mycompany/_apis/wit/workItems/12345"
                }
                with mock_azure_http_client(method="post", response_data=response_data) as mock_client_class:

                    # Step 5: Execute the tool (simulates user calling the tool)
                    result = await tool.execute_tool({
                        "operation": "create",
                        "title": "Implement user authentication",
                        "description": "Add OAuth2 authentication to the application",
                        "work_item_type": "Task"
                    })

                    # Step 6: Verify the complete workflow worked

                    # Verify the result is successful
                    assert result["success"] is True
                    assert result["data"]["id"] == 12345
                    assert result["data"]["fields"]["System.Title"] == "Implement user authentication"

                    # Verify the bearer token command was executed
                    mock_subprocess_run.assert_called_once()
                    call_args = mock_subprocess_run.call_args
                    assert "az account get-access-token --resource https://dev.azure.com/" in call_args[0][0]
                    assert call_args[1]["shell"] is True
                    assert call_args[1]["capture_output"] is True
                    assert call_args[1]["text"] is True
                    assert call_args[1]["timeout"] == 30

                    # Verify the REST API was called with the correct token
                    mock_client_class.return_value.request.assert_called_once()
                    post_call_args = mock_client_class.return_value.request.call_args

                    # Check the method and URL
                    assert post_call_args[0][0] == "POST"  # method
                    expected_url = "https://dev.azure.com/mycompany/MyProject/_apis/wit/workitems/$Task?api-version=7.1"
                    assert post_call_args[0][1] == expected_url  # url

                    # Check the headers contain the bearer token
                    headers = post_call_args[1]["headers"]
                    assert headers["Authorization"] == "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6..."
                    assert headers["Content-Type"] == "application/json-patch+json"
                    assert headers["Accept"] == "application/json"

                    # Check the patch document
                    patch_document = post_call_args[1]["json"]
                    # With identity resolution, if the current user cannot be resolved,
                    # the work item will be left unassigned (4 fields instead of 5)
                    assert len(patch_document) == 4  # title, description, area_path, iteration (no assigned_to due to resolution failure)

                    # Verify patch document contents
                    title_patch = next(p for p in patch_document if p["path"] == "/fields/System.Title")
                    assert title_patch["op"] == "add"
                    assert title_patch["value"] == "Implement user authentication"

                    description_patch = next(p for p in patch_document if p["path"] == "/fields/System.Description")
                    assert description_patch["op"] == "add"
                    assert description_patch["value"] == "Add OAuth2 authentication to the application"

                    # Verify that no assignment field is included due to identity resolution failure
                    assigned_to_patches = [p for p in patch_document if p["path"] == "/fields/System.AssignedTo"]
                    assert len(assigned_to_patches) == 0  # No assignment due to identity resolution failure

    @patch("plugins.azrepo.azure_rest_utils.subprocess.run")
    def test_bearer_token_command_failure_graceful_handling(self, mock_subprocess_run):
        """Test that bearer token command failures are handled gracefully."""

        # Clear bearer token cache before test
        from plugins.azrepo.azure_rest_utils import clear_bearer_token_cache
        clear_bearer_token_cache()

        # Mock command failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: Please run 'az login' to setup account."
        mock_subprocess_run.return_value = mock_result

        # Mock environment manager
        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.load.return_value = None
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "mycompany",
                "project": "MyProject",
                "bearer_token_command": "az account get-access-token --resource https://dev.azure.com/"
            }

            # Also patch the azure_rest_utils env_manager
            with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_rest_env_manager:
                mock_rest_env_manager.get_azrepo_parameters.return_value = {
                    "org": "mycompany",
                    "project": "MyProject",
                    "bearer_token_command": "az account get-access-token --resource https://dev.azure.com/"
                }

                # Create tool instance
                mock_executor = MagicMock()
                tool = AzureWorkItemTool(command_executor=mock_executor)

                # Attempting to get auth headers should raise a clear error
                with pytest.raises(ValueError, match="Bearer token not configured"):
                    from plugins.azrepo.azure_rest_utils import get_auth_headers
                    get_auth_headers(content_type="application/json-patch+json")

                # Verify the command was attempted
                mock_subprocess_run.assert_called_once()

    def test_fallback_to_static_token_when_command_not_configured(self):
        """Test that static token is used when no command is configured."""

        # Mock environment manager with static token
        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.load.return_value = None
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "mycompany",
                "project": "MyProject",
                "bearer_token": "static-token-12345"
                # No bearer_token_command configured
            }

            # Also patch the azure_rest_utils env_manager
            with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_rest_env_manager:
                mock_rest_env_manager.get_azrepo_parameters.return_value = {
                    "org": "mycompany",
                    "project": "MyProject",
                    "bearer_token": "static-token-12345"
                    # No bearer_token_command configured
                }

                # Create tool instance
                mock_executor = MagicMock()
                tool = AzureWorkItemTool(command_executor=mock_executor)

                # Get auth headers should use static token
                from plugins.azrepo.azure_rest_utils import get_auth_headers
                headers = get_auth_headers(content_type="application/json-patch+json")

                assert headers["Authorization"] == "Bearer static-token-12345"
                assert headers["Content-Type"] == "application/json-patch+json"
                assert headers["Accept"] == "application/json"

    @patch("plugins.azrepo.azure_rest_utils.subprocess.run")
    def test_command_takes_precedence_when_both_configured(self, mock_subprocess_run):
        """Test that bearer token command takes precedence over static token when both are configured."""

        # Clear bearer token cache before test
        from plugins.azrepo.azure_rest_utils import clear_bearer_token_cache
        clear_bearer_token_cache()

        # Mock successful command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"accessToken": "dynamic-token-from-command"}'
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        # Mock environment manager with both static token and command
        with patch("plugins.azrepo.workitem_tool.env_manager") as mock_env_manager:
            mock_env_manager.load.return_value = None
            mock_env_manager.get_azrepo_parameters.return_value = {
                "org": "mycompany",
                "project": "MyProject",
                "bearer_token": "static-token-12345",  # This should be ignored
                "bearer_token_command": "az account get-access-token --resource https://dev.azure.com/"
            }

            # Also patch the azure_rest_utils env_manager
            with patch("plugins.azrepo.azure_rest_utils.env_manager") as mock_rest_env_manager:
                mock_rest_env_manager.get_azrepo_parameters.return_value = {
                    "org": "mycompany",
                    "project": "MyProject",
                    "bearer_token": "static-token-12345",  # This should be ignored
                    "bearer_token_command": "az account get-access-token --resource https://dev.azure.com/"
                }

                # Create tool instance
                mock_executor = MagicMock()
                tool = AzureWorkItemTool(command_executor=mock_executor)

                # Get auth headers should use dynamic token from command
                from plugins.azrepo.azure_rest_utils import get_auth_headers
                headers = get_auth_headers(content_type="application/json-patch+json")

                assert headers["Authorization"] == "Bearer dynamic-token-from-command"

                # Verify command was executed
                mock_subprocess_run.assert_called_once()
