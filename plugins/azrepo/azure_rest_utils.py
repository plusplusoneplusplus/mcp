"""Azure DevOps REST API utilities.

This module provides shared utilities for interacting with the Azure DevOps REST API.
It includes authentication, URL building, common error handling functions, and identity resolution.
"""

import os
import json
import logging
import getpass
import subprocess
import re
import aiohttp
from typing import Dict, Any, Optional, Union, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

# Import configuration manager
from config import env_manager

logger = logging.getLogger(__name__)

# Identity cache to avoid repeated API calls
_identity_cache: Dict[str, Dict[str, Any]] = {}
_cache_expiry: Dict[str, datetime] = {}
CACHE_DURATION_MINUTES = 30


@dataclass
class IdentityInfo:
    """Represents a resolved Azure DevOps identity."""
    display_name: str
    unique_name: str  # Usually email
    id: str
    descriptor: str
    is_valid: bool = True
    error_message: str = ""


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


def is_valid_email(email: str) -> bool:
    """Check if a string is a valid email format.

    Args:
        email: String to validate

    Returns:
        True if valid email format, False otherwise
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def normalize_identity_input(identity: str) -> str:
    """Normalize identity input for consistent processing.

    Args:
        identity: Raw identity string

    Returns:
        Normalized identity string
    """
    if not identity:
        return ""

    # Strip whitespace
    identity = identity.strip()

    # Handle combo format "Display Name <email@domain.com>"
    combo_match = re.match(r'^(.+?)\s*<(.+?)>$', identity)
    if combo_match:
        return combo_match.group(2).strip()  # Extract email

    return identity


def _is_cache_valid(cache_key: str) -> bool:
    """Check if cached identity data is still valid.

    Args:
        cache_key: Cache key to check

    Returns:
        True if cache is valid, False otherwise
    """
    if cache_key not in _cache_expiry:
        return False

    return datetime.now() < _cache_expiry[cache_key]


def _cache_identity(cache_key: str, identity_data: Dict[str, Any]) -> None:
    """Cache identity data with expiration.

    Args:
        cache_key: Key for caching
        identity_data: Identity data to cache
    """
    _identity_cache[cache_key] = identity_data
    _cache_expiry[cache_key] = datetime.now() + timedelta(minutes=CACHE_DURATION_MINUTES)


async def resolve_identity(
    identity: str,
    organization: str,
    project: Optional[str] = None
) -> IdentityInfo:
    """Resolve an identity string to a valid Azure DevOps identity.

    This function attempts to resolve various identity formats:
    - Email addresses (e.g., "user@domain.com")
    - Display names (e.g., "John Doe")
    - Combo format (e.g., "John Doe <user@domain.com>")
    - Identity descriptors

    Args:
        identity: Identity string to resolve
        organization: Azure DevOps organization
        project: Optional project context for resolution

    Returns:
        IdentityInfo object with resolution results
    """
    if not identity or identity.lower() in ["none", "unassigned"]:
        return IdentityInfo(
            display_name="",
            unique_name="",
            id="",
            descriptor="",
            is_valid=False,
            error_message="Identity is empty or explicitly unassigned"
        )

    # Normalize the input
    normalized_identity = normalize_identity_input(identity)

    # Create cache key
    cache_key = f"{organization}:{project or 'global'}:{normalized_identity}"

    # Check cache first
    if _is_cache_valid(cache_key):
        cached_data = _identity_cache[cache_key]
        return IdentityInfo(**cached_data)

    try:
        # Try to resolve using Azure DevOps Identity API
        identity_info = await _resolve_identity_via_api(normalized_identity, organization, project)

        # Cache the result
        _cache_identity(cache_key, {
            "display_name": identity_info.display_name,
            "unique_name": identity_info.unique_name,
            "id": identity_info.id,
            "descriptor": identity_info.descriptor,
            "is_valid": identity_info.is_valid,
            "error_message": identity_info.error_message
        })

        return identity_info

    except Exception as e:
        logger.error(f"Error resolving identity '{identity}': {e}")
        return IdentityInfo(
            display_name="",
            unique_name="",
            id="",
            descriptor="",
            is_valid=False,
            error_message=f"Failed to resolve identity: {str(e)}"
        )


async def _resolve_identity_via_api(
    identity: str,
    organization: str,
    project: Optional[str] = None
) -> IdentityInfo:
    """Resolve identity using Azure DevOps REST API.

    Args:
        identity: Normalized identity string
        organization: Azure DevOps organization
        project: Optional project context

    Returns:
        IdentityInfo with resolution results
    """
    try:
        # Build API URL for identity resolution
        # Use the Identity API to resolve the identity
        if organization.startswith(("http://", "https://")):
            base_url = organization.rstrip("/")
        else:
            base_url = f"https://vssps.dev.azure.com/{organization}"

        # Try multiple API endpoints for identity resolution
        endpoints_to_try = [
            f"{base_url}/_apis/identities?searchFilter=General&filterValue={identity}&api-version=7.1",
            f"{base_url}/_apis/graph/users?subjectTypes=aad,msa&api-version=7.1-preview.1"
        ]

        headers = get_auth_headers()

        async with aiohttp.ClientSession() as session:
            # Try the identities API first
            for endpoint in endpoints_to_try:
                try:
                    async with session.get(endpoint, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()

                            # Process identities API response
                            if "value" in data and data["value"]:
                                for identity_item in data["value"]:
                                    # Check if this identity matches our search
                                    if _identity_matches(identity_item, identity):
                                        return _create_identity_info_from_api_response(identity_item)

                            # If we found results but no matches, continue to next endpoint
                            continue

                except Exception as e:
                    logger.debug(f"Failed to resolve identity via endpoint {endpoint}: {e}")
                    continue

        # If API resolution fails, try to validate the format and create a basic identity
        if is_valid_email(identity):
            # For valid email formats, create a basic identity info
            # Azure DevOps often accepts email addresses directly
            return IdentityInfo(
                display_name=identity,
                unique_name=identity,
                id="",
                descriptor="",
                is_valid=True,
                error_message=""
            )

        # If all resolution attempts fail
        return IdentityInfo(
            display_name="",
            unique_name="",
            id="",
            descriptor="",
            is_valid=False,
            error_message=f"Unable to resolve identity '{identity}' in organization '{organization}'"
        )

    except Exception as e:
        logger.error(f"API identity resolution failed: {e}")
        return IdentityInfo(
            display_name="",
            unique_name="",
            id="",
            descriptor="",
            is_valid=False,
            error_message=f"API resolution error: {str(e)}"
        )


def _identity_matches(identity_item: Dict[str, Any], search_term: str) -> bool:
    """Check if an identity item matches the search term.

    Args:
        identity_item: Identity data from API
        search_term: Original search term

    Returns:
        True if identity matches, False otherwise
    """
    search_lower = search_term.lower()

    # Check various fields for matches
    fields_to_check = [
        identity_item.get("providerDisplayName", ""),
        identity_item.get("displayName", ""),
        identity_item.get("uniqueName", ""),
        identity_item.get("mailAddress", ""),
    ]

    # Also check properties if available
    properties = identity_item.get("properties", {})
    if properties:
        fields_to_check.extend([
            properties.get("Account", {}).get("$value", ""),
            properties.get("Mail", {}).get("$value", ""),
        ])

    for field in fields_to_check:
        if field and search_lower in field.lower():
            return True

    return False


def _create_identity_info_from_api_response(identity_item: Dict[str, Any]) -> IdentityInfo:
    """Create IdentityInfo from API response data.

    Args:
        identity_item: Identity data from API

    Returns:
        IdentityInfo object
    """
    display_name = (
        identity_item.get("providerDisplayName") or
        identity_item.get("displayName") or
        identity_item.get("uniqueName", "")
    )

    unique_name = (
        identity_item.get("uniqueName") or
        identity_item.get("mailAddress") or
        ""
    )

    # Extract from properties if main fields are empty
    properties = identity_item.get("properties", {})
    if not unique_name and properties:
        unique_name = (
            properties.get("Mail", {}).get("$value") or
            properties.get("Account", {}).get("$value") or
            ""
        )

    return IdentityInfo(
        display_name=display_name,
        unique_name=unique_name,
        id=identity_item.get("id", ""),
        descriptor=identity_item.get("descriptor", ""),
        is_valid=True,
        error_message=""
    )


async def validate_and_format_assignee(
    assignee: Optional[str],
    organization: str,
    project: Optional[str] = None,
    fallback_to_current_user: bool = True
) -> Tuple[Optional[str], str]:
    """Validate and format an assignee for Azure DevOps work item assignment.

    Args:
        assignee: Raw assignee string (can be "current", "none", email, display name, etc.)
        organization: Azure DevOps organization
        project: Optional project context
        fallback_to_current_user: Whether to fallback to current user if resolution fails

    Returns:
        Tuple of (formatted_assignee, error_message)
        - formatted_assignee: Properly formatted assignee string for Azure DevOps, or None if unassigned
        - error_message: Error message if validation failed, None if successful
    """
    if not assignee or assignee.lower() in ["none", "unassigned"]:
        return None, ""

    if assignee.lower() == "current":
        # Try to get current user's identity
        current_username = get_current_username()
        if not current_username:
            return None, "Unable to determine current user for assignment"

        # Try to resolve current username to a valid identity
        identity_info = await resolve_identity(current_username, organization, project)
        if identity_info.is_valid and identity_info.unique_name:
            return identity_info.unique_name, ""
        else:
            # If current username resolution fails, return error
            error_msg = f"Unable to resolve current user '{current_username}' to a valid Azure DevOps identity"
            if identity_info.error_message:
                error_msg += f": {identity_info.error_message}"
            return None, error_msg

    # Resolve the provided identity
    try:
        identity_info = await resolve_identity(assignee, organization, project)

        if identity_info.is_valid:
            # Use unique_name (usually email) for assignment if available, otherwise display_name
            formatted_assignee = identity_info.unique_name or identity_info.display_name
            if formatted_assignee:
                return formatted_assignee, ""
            else:
                return None, f"Resolved identity for '{assignee}' but no usable identifier found"
        else:
            error_msg = f"Unable to resolve identity '{assignee}'"
            if identity_info.error_message:
                error_msg += f": {identity_info.error_message}"

            if fallback_to_current_user:
                logger.warning(f"{error_msg}. Attempting fallback to current user.")
                return await validate_and_format_assignee("current", organization, project, False)

            return None, error_msg
    except Exception as e:
        error_msg = f"Unable to resolve identity '{assignee}': {str(e)}"

        if fallback_to_current_user:
            logger.warning(f"{error_msg}. Attempting fallback to current user.")
            return await validate_and_format_assignee("current", organization, project, False)

        return None, error_msg


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
