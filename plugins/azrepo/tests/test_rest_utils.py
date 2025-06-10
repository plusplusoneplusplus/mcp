"""Tests for the Azure DevOps REST API utilities."""

import pytest
import json
from unittest.mock import patch, MagicMock

from plugins.azrepo.azure_rest_utils import (
    get_current_username,
    execute_bearer_token_command,
    get_auth_headers,
    build_api_url,
    process_rest_response,
)


def test_build_api_url_with_org_name():
    """Test building API URL with organization name."""
    url = build_api_url("testorg", "testproject", "testendpoint")
    assert url == "https://dev.azure.com/testorg/testproject/_apis/testendpoint"


def test_build_api_url_with_full_url():
    """Test building API URL with full organization URL."""
    url = build_api_url("https://dev.azure.com/testorg", "testproject", "testendpoint")
    assert url == "https://dev.azure.com/testorg/testproject/_apis/testendpoint"


def test_build_api_url_with_custom_host():
    """Test building API URL with custom host."""
    url = build_api_url("https://custom.example.com/testorg", "testproject", "testendpoint")
    assert url == "https://custom.example.com/testorg/testproject/_apis/testendpoint"


def test_process_rest_response_success():
    """Test processing a successful REST response."""
    response_text = json.dumps({"id": 123, "name": "Test Item"})
    result = process_rest_response(response_text, 200)

    assert result["success"] is True
    assert result["data"]["id"] == 123
    assert result["data"]["name"] == "Test Item"


def test_process_rest_response_not_found():
    """Test processing a not found REST response."""
    response_text = "Not found"
    result = process_rest_response(response_text, 404)

    assert result["success"] is False
    assert "error" in result
    assert "Resource not found" in result["error"]
    assert result["raw_output"] == response_text


def test_process_rest_response_error():
    """Test processing an error REST response."""
    response_text = "Error message"
    result = process_rest_response(response_text, 500)

    assert result["success"] is False
    assert "error" in result
    assert "HTTP 500" in result["error"]
    assert result["raw_output"] == response_text


def test_process_rest_response_invalid_json():
    """Test processing a response with invalid JSON."""
    response_text = "Not valid JSON"
    result = process_rest_response(response_text, 200)

    assert result["success"] is False
    assert "error" in result
    assert "Failed to parse" in result["error"]
    assert result["raw_output"] == response_text


@patch("plugins.azrepo.azure_rest_utils.getpass")
def test_get_current_username_from_getpass(mock_getpass):
    """Test getting username from getpass."""
    mock_getpass.getuser.return_value = "testuser"

    username = get_current_username()

    assert username == "testuser"
    mock_getpass.getuser.assert_called_once()


@patch("plugins.azrepo.azure_rest_utils.getpass")
@patch("plugins.azrepo.azure_rest_utils.os")
def test_get_current_username_from_env(mock_os, mock_getpass):
    """Test getting username from environment variables."""
    # Make getpass.getuser raise an exception
    mock_getpass.getuser.side_effect = Exception("getpass error")

    # Mock os.environ.get
    mock_os.environ.get.side_effect = lambda key, default=None: "envuser" if key in ["USER", "USERNAME"] else default

    username = get_current_username()

    assert username == "envuser"
    mock_getpass.getuser.assert_called_once()
    assert mock_os.environ.get.call_count >= 1


@patch("plugins.azrepo.azure_rest_utils.env_manager")
def test_get_auth_headers_from_static_token(mock_env_manager):
    """Test getting auth headers from static token."""
    # Mock env_manager to return a static token
    mock_env_manager.get_azrepo_parameters.return_value = {
        "bearer_token": "static-token-123"
    }

    headers = get_auth_headers()

    assert headers["Authorization"] == "Bearer static-token-123"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"
    mock_env_manager.get_azrepo_parameters.assert_called_once()


@patch("plugins.azrepo.azure_rest_utils.env_manager")
@patch("plugins.azrepo.azure_rest_utils.execute_bearer_token_command")
def test_get_auth_headers_from_command(mock_execute_command, mock_env_manager):
    """Test getting auth headers from command."""
    # Mock env_manager to return a command
    mock_env_manager.get_azrepo_parameters.return_value = {
        "bearer_token_command": "test-command"
    }

    # Mock execute_bearer_token_command to return a token
    mock_execute_command.return_value = "command-token-456"

    headers = get_auth_headers("custom/content-type")

    assert headers["Authorization"] == "Bearer command-token-456"
    assert headers["Content-Type"] == "custom/content-type"
    assert headers["Accept"] == "application/json"
    mock_env_manager.get_azrepo_parameters.assert_called_once()
    mock_execute_command.assert_called_once_with("test-command")


@patch("plugins.azrepo.azure_rest_utils.subprocess.run")
def test_execute_bearer_token_command_success(mock_run):
    """Test executing bearer token command successfully."""
    # Mock subprocess.run
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = json.dumps({"accessToken": "test-token-789"})
    mock_run.return_value = mock_process

    token = execute_bearer_token_command("test command")

    assert token == "test-token-789"
    mock_run.assert_called_once_with(
        "test command",
        shell=True,
        capture_output=True,
        text=True,
        timeout=30
    )


@patch("plugins.azrepo.azure_rest_utils.subprocess.run")
def test_execute_bearer_token_command_failure(mock_run):
    """Test executing bearer token command with failure."""
    # Mock subprocess.run with a non-zero return code
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stderr = "Command failed"
    mock_run.return_value = mock_process

    token = execute_bearer_token_command("test command")

    assert token is None
    mock_run.assert_called_once()
