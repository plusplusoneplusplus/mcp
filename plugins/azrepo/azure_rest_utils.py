"""Azure DevOps REST API utilities.

This module provides shared utilities for interacting with the Azure DevOps REST API.
It includes authentication, URL building, and common error handling functions.
"""

import os
import json
import logging
import getpass
import subprocess
from typing import Dict, Any, Optional, Union

# Import configuration manager
from config import env_manager

logger = logging.getLogger(__name__)


def get_current_username() -> Optional[str]:
    """Get the current username in a cross-platform way.

    Returns:
        The current username, or None if unable to determine
    """
    try:
        # Try getpass.getuser() first (works on most platforms)
        return getpass.getuser()
    except Exception:
        try:
            # Fallback to environment variables
            username = os.environ.get("USER") or os.environ.get("USERNAME")
            if username:
                return username
        except Exception:
            pass

        # Return None if unable to determine username
        logger.warning("Unable to determine current username")
        return None


def execute_bearer_token_command(command: str) -> Optional[str]:
    """Execute a command and extract the accessToken from JSON output.

    Args:
        command: The command to execute

    Returns:
        The access token if found, None otherwise
    """
    try:
        logger.debug(f"Executing bearer token command: {command}")

        # Execute the command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )

        if result.returncode != 0:
            logger.error(f"Bearer token command failed with return code {result.returncode}: {result.stderr}")
            return None

        # Parse JSON output
        try:
            json_output = json.loads(result.stdout)
            access_token = json_output.get("accessToken")

            if access_token:
                logger.debug("Successfully extracted access token from command output")
                return access_token
            else:
                logger.warning("No 'accessToken' property found in command output JSON")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse command output as JSON: {e}")
            logger.debug(f"Command output was: {result.stdout}")
            return None

    except subprocess.TimeoutExpired:
        logger.error(f"Bearer token command timed out after 30 seconds: {command}")
        return None
    except Exception as e:
        logger.error(f"Error executing bearer token command: {e}")
        return None


def get_auth_headers(content_type: str = "application/json") -> Dict[str, str]:
    """Get authentication headers for REST API calls.

    Args:
        content_type: Content-Type header value (defaults to application/json for GET operations)

    Returns:
        Dictionary with authorization headers
    """
    bearer_token = None

    # Always get fresh Azure repo parameters from environment manager
    # This ensures we get the latest configuration, including any mocked values in tests
    azrepo_params = env_manager.get_azrepo_parameters()

    # Try bearer token command first (takes precedence over static token)
    bearer_token_command = azrepo_params.get("bearer_token_command")
    if bearer_token_command:
        bearer_token = execute_bearer_token_command(bearer_token_command)

    # If no token from command, fall back to static token from environment
    if not bearer_token:
        bearer_token = azrepo_params.get("bearer_token")

    if not bearer_token:
        raise ValueError("Bearer token not configured. Please set AZREPO_BEARER_TOKEN or AZREPO_BEARER_TOKEN_COMMAND environment variable.")

    # For Azure DevOps REST API, use the bearer token directly
    return {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": content_type,
        "Accept": "application/json"
    }


def build_api_url(organization: str, project: str, endpoint: str) -> str:
    """Build complete Azure DevOps REST API URL.

    This helper handles organization parameters that may be supplied either
    as a plain organization name (e.g. ``mycompany``) or a full URL
    (e.g. ``https://dev.azure.com/mycompany`` or a custom host).

    Args:
        organization: Azure DevOps organization name or URL
        project: Azure DevOps project name
        endpoint: API endpoint path without leading slash

    Returns:
        Complete REST API URL
    """
    if organization.startswith(("http://", "https://")):
        base_url = organization.rstrip("/")
    else:
        base_url = f"https://dev.azure.com/{organization}"

    return f"{base_url}/{project}/_apis/{endpoint}"


def process_rest_response(response_text: str, status_code: int) -> Dict[str, Any]:
    """Process REST API response and standardize error handling.

    Args:
        response_text: Raw response text from the API
        status_code: HTTP status code

    Returns:
        Dictionary with standardized response format:
        {
            "success": bool,
            "data": Optional[Dict[str, Any]],  # Present on success
            "error": Optional[str],            # Present on failure
            "raw_output": Optional[str]        # Present on failure or parse error
        }
    """
    try:
        if 200 <= status_code < 300:
            # Success response
            try:
                response_data = json.loads(response_text)
                return {"success": True, "data": response_data}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse successful response as JSON: {e}")
                return {
                    "success": False,
                    "error": f"Failed to parse response: {e}",
                    "raw_output": response_text
                }
        elif status_code == 404:
            # Not found
            return {
                "success": False,
                "error": "Resource not found",
                "raw_output": response_text
            }
        else:
            # Other errors
            return {
                "success": False,
                "error": f"HTTP {status_code}: {response_text}",
                "raw_output": response_text
            }
    except Exception as e:
        logger.error(f"Error processing REST response: {e}")
        return {
            "success": False,
            "error": f"Error processing response: {str(e)}",
            "raw_output": response_text
        }
