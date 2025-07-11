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
import asyncio
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

# Bearer token cache to avoid repeated command executions
_bearer_token_cache: Optional[str] = None
_bearer_token_cache_expiry: Optional[datetime] = None
BEARER_TOKEN_CACHE_DURATION_SECONDS = 300  # 5 minutes


class AzureHttpClient:
    """Centralized HTTP client for Azure DevOps REST API operations.

    This class provides a reusable HTTP client with connection pooling, retry logic,
    and standardized error handling for Azure DevOps REST API calls. It implements
    the async context manager protocol for proper resource management.

    Features:
    - Connection pooling with configurable limits
    - Retry logic with exponential backoff
    - Standardized error handling and response processing
    - Integration with existing authentication system
    - Proper async context manager for resource cleanup

    Example:
        async with AzureHttpClient() as client:
            response = await client.request('GET', url, headers=headers)
            data = response.get('data')
    """

    def __init__(
        self,
        total_connections: int = 100,
        per_host_connections: int = 30,
        dns_cache_ttl: int = 300,
        request_timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.5,
        retry_statuses: Optional[List[int]] = None
    ):
        """Initialize the AzureHttpClient.

        Args:
            total_connections: Total connection pool limit
            per_host_connections: Per-host connection limit
            dns_cache_ttl: DNS cache TTL in seconds
            request_timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff_factor: Exponential backoff factor for retries
            retry_statuses: HTTP status codes that should trigger retries
        """
        self.total_connections = total_connections
        self.per_host_connections = per_host_connections
        self.dns_cache_ttl = dns_cache_ttl
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.retry_statuses = retry_statuses or [429, 500, 502, 503, 504]

        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None

    async def __aenter__(self) -> 'AzureHttpClient':
        """Async context manager entry."""
        await self._initialize_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with proper cleanup."""
        await self._cleanup_session()

    async def _initialize_session(self) -> None:
        """Initialize the HTTP session with connection pooling."""
        if self._session is not None:
            return

        # Create TCP connector with connection pooling
        self._connector = aiohttp.TCPConnector(
            limit=self.total_connections,
            limit_per_host=self.per_host_connections,
            ttl_dns_cache=self.dns_cache_ttl,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )

        # Create timeout configuration
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)

        # Create session with connector and timeout
        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            raise_for_status=False  # We handle status codes manually
        )

        logger.debug(
            f"Initialized AzureHttpClient session with {self.total_connections} total connections, "
            f"{self.per_host_connections} per-host connections"
        )

    async def _cleanup_session(self) -> None:
        """Clean up the HTTP session and connector."""
        if self._session:
            await self._session.close()
            self._session = None

        if self._connector:
            await self._connector.close()
            self._connector = None

        logger.debug("Cleaned up AzureHttpClient session")

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Union[Dict[str, Any], List[Any]]] = None,
        data: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic and standardized error handling.

        Args:
            method: HTTP method (GET, POST, PATCH, PUT, DELETE)
            url: Request URL
            headers: Optional request headers
            params: Optional query parameters
            json: Optional JSON payload
            data: Optional request data
            **kwargs: Additional arguments passed to aiohttp

        Returns:
            Dictionary with standardized response format:
            {
                "success": bool,
                "data": Optional[Dict[str, Any]],  # Present on success
                "error": Optional[str],            # Present on failure
                "status_code": int,                # HTTP status code
                "raw_response": Optional[str]      # Raw response text
            }
        """
        if not self._session:
            raise RuntimeError("AzureHttpClient session not initialized. Use 'async with' context manager.")

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Calculate delay for exponential backoff
                if attempt > 0:
                    delay = self.retry_backoff_factor * (2 ** (attempt - 1))
                    logger.debug(f"Retrying request after {delay:.2f}s delay (attempt {attempt + 1}/{self.max_retries + 1})")
                    await asyncio.sleep(delay)

                # Prepare request arguments - only include non-None values
                request_kwargs: Dict[str, Any] = {}

                if headers is not None:
                    request_kwargs['headers'] = headers
                if params is not None:
                    request_kwargs['params'] = params
                if json is not None:
                    request_kwargs['json'] = json
                elif data is not None:
                    request_kwargs['data'] = data

                # Add any additional kwargs
                request_kwargs.update(kwargs)

                # Make the HTTP request
                session = self._session
                if session is None:
                    raise RuntimeError("Session is None")

                async with session.request(
                    method=method.upper(),
                    url=url,
                    **request_kwargs
                ) as response:
                    response_text = await response.text()
                    status_code = response.status

                    logger.debug(f"{method.upper()} {url} -> {status_code}")

                    # Check if we should retry based on status code
                    if attempt < self.max_retries and status_code in self.retry_statuses:
                        logger.warning(f"Request failed with status {status_code}, will retry")
                        continue

                    # Process the response using existing utility function
                    result = process_rest_response(response_text, status_code)
                    result["status_code"] = status_code
                    result["raw_response"] = response_text

                    return result

            except aiohttp.ClientError as e:
                last_exception = e
                logger.warning(f"HTTP client error on attempt {attempt + 1}: {e}")

                # Don't retry on client errors unless it's a timeout
                if not isinstance(e, (aiohttp.ServerTimeoutError, asyncio.TimeoutError)):
                    break

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                break

        # If we get here, all retries failed
        error_msg = f"Request failed after {self.max_retries + 1} attempts"
        if last_exception:
            error_msg += f": {str(last_exception)}"

        return {
            "success": False,
            "error": error_msg,
            "status_code": 0,
            "raw_response": None
        }

    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """Convenience method for GET requests."""
        return await self.request('GET', url, **kwargs)

    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """Convenience method for POST requests."""
        return await self.request('POST', url, **kwargs)

    async def patch(self, url: str, **kwargs) -> Dict[str, Any]:
        """Convenience method for PATCH requests."""
        return await self.request('PATCH', url, **kwargs)

    async def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """Convenience method for PUT requests."""
        return await self.request('PUT', url, **kwargs)

    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """Convenience method for DELETE requests."""
        return await self.request('DELETE', url, **kwargs)

    # Integration methods with existing utilities
    async def azure_request(
        self,
        method: str,
        organization: str,
        project: str,
        endpoint: str,
        content_type: str = "application/json",
        **kwargs
    ) -> Dict[str, Any]:
        """Make an Azure DevOps REST API request with automatic authentication and URL building.

        This method integrates with existing utility functions to provide a seamless
        experience for Azure DevOps API calls.

        Args:
            method: HTTP method (GET, POST, PATCH, PUT, DELETE)
            organization: Azure DevOps organization name or URL
            project: Azure DevOps project name
            endpoint: API endpoint path without leading slash
            content_type: Content-Type header value
            **kwargs: Additional arguments passed to the request

        Returns:
            Dictionary with standardized response format from process_rest_response()
        """
        # Build URL using existing utility
        url = build_api_url(organization, project, endpoint)

        # Get authentication headers using existing utility
        headers = get_auth_headers(content_type)

        # Merge with any additional headers provided
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        # Make the request
        return await self.request(method, url, headers=headers, **kwargs)

    async def azure_get(
        self,
        organization: str,
        project: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Convenience method for Azure DevOps GET requests."""
        return await self.azure_request(
            'GET', organization, project, endpoint,
            params=params, **kwargs
        )

    async def azure_post(
        self,
        organization: str,
        project: str,
        endpoint: str,
        json: Optional[Union[Dict[str, Any], List[Any]]] = None,
        data: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Convenience method for Azure DevOps POST requests."""
        return await self.azure_request(
            'POST', organization, project, endpoint,
            json=json, data=data, **kwargs
        )

    async def azure_patch(
        self,
        organization: str,
        project: str,
        endpoint: str,
        json: Optional[Union[Dict[str, Any], List[Any]]] = None,
        data: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Convenience method for Azure DevOps PATCH requests."""
        return await self.azure_request(
            'PATCH', organization, project, endpoint,
            json=json, data=data, **kwargs
        )

    async def azure_put(
        self,
        organization: str,
        project: str,
        endpoint: str,
        json: Optional[Union[Dict[str, Any], List[Any]]] = None,
        data: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Convenience method for Azure DevOps PUT requests."""
        return await self.azure_request(
            'PUT', organization, project, endpoint,
            json=json, data=data, **kwargs
        )

    async def azure_delete(
        self,
        organization: str,
        project: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Convenience method for Azure DevOps DELETE requests."""
        return await self.azure_request(
            'DELETE', organization, project, endpoint, **kwargs
        )


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

    # Try to get current user's email first (more reliable for Azure DevOps)if
    current_user_email = get_current_user_email()
    if current_user_email:
        return current_user_email

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


def get_current_user_email() -> Optional[str]:
    """Get the current user's email address in a cross-platform way.
    
    On Windows, this uses 'whoami /upn' to get the User Principal Name (UPN),
    which is typically the user's email address in domain environments.
    On other platforms, it falls back to environment variables.

    Returns:
        The current user's email address, or None if unable to determine
    """
    try:
        # On Windows, try whoami /upn first to get the UPN (usually email)
        if os.name == 'nt':  # Windows
            try:
                logger.debug("Attempting to get current user email using 'whoami /upn' on Windows")
                result = subprocess.run(
                    ["whoami", "/upn"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    upn = result.stdout.strip()
                    if upn and is_valid_email(upn):
                        logger.debug(f"Successfully retrieved user email from whoami /upn: {upn}")
                        return upn
                    else:
                        logger.debug(f"whoami /upn returned '{upn}' which is not a valid email format")
                else:
                    logger.debug(f"whoami /upn failed with return code {result.returncode}: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.warning("whoami /upn command timed out")
            except Exception as e:
                logger.debug(f"Error executing whoami /upn: {e}")
        
        # Fallback to environment variables that might contain email
        email_env_vars = [
            "USERPRINCIPALNAME",  # Windows domain environments
            "USER_EMAIL",         # Custom environment variable
            "EMAIL",              # Generic email environment variable
            "MAIL",               # Unix mail environment variable
        ]
        
        for env_var in email_env_vars:
            email = os.environ.get(env_var)
            if email and is_valid_email(email):
                logger.debug(f"Found user email in environment variable {env_var}: {email}")
                return email
        
        # If no email found, return None
        logger.debug("Unable to determine current user email from any source")
        return None
        
    except Exception as e:
        logger.warning(f"Error getting current user email: {e}")
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


def clear_bearer_token_cache() -> None:
    """Clear the bearer token cache.

    This is primarily used for testing to ensure clean state between tests.
    """
    global _bearer_token_cache, _bearer_token_cache_expiry
    _bearer_token_cache = None
    _bearer_token_cache_expiry = None


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
        # Handle different organization URL formats
        if organization.startswith(("http://", "https://")):
            base_url = organization.rstrip("/")
            
            # For Visual Studio Team Services URLs, use the correct identity service endpoint
            if "visualstudio.com" in base_url:
                # Extract organization name from URL like https://msazure.visualstudio.com
                org_name = base_url.split("//")[1].split(".")[0]
                vssps_base_url = f"https://vssps.dev.azure.com/{org_name}"
            else:
                # For dev.azure.com URLs, extract organization name
                if "dev.azure.com" in base_url:
                    org_name = base_url.split("/")[-1]
                    vssps_base_url = f"https://vssps.dev.azure.com/{org_name}"
                else:
                    # For other custom URLs, try to use them directly
                    vssps_base_url = base_url
        else:
            # Plain organization name
            base_url = f"https://dev.azure.com/{organization}"
            vssps_base_url = f"https://vssps.dev.azure.com/{organization}"

        # Try multiple API endpoints for identity resolution
        endpoints_to_try = [
            # Try the VSSPS identity service first (most reliable)
            f"{vssps_base_url}/_apis/identities?searchFilter=General&filterValue={identity}&api-version=7.1",
            # Try the graph API as fallback
            f"{vssps_base_url}/_apis/graph/users?subjectTypes=aad,msa&api-version=7.1-preview.1",
            # Try the main organization URL as additional fallback
            f"{base_url}/_apis/identities?searchFilter=General&filterValue={identity}&api-version=7.1",
        ]

        headers = get_auth_headers()
        
        logger.debug(f"Attempting to resolve identity '{identity}' using endpoints: {endpoints_to_try}")

        # Use AzureHttpClient for better error handling and retry logic
        async with AzureHttpClient() as client:
            # Try each endpoint
            for endpoint in endpoints_to_try:
                try:
                    logger.debug(f"Trying identity resolution endpoint: {endpoint}")
                    
                    # Make request with built-in retry logic and error handling
                    result = await client.get(endpoint, headers=headers)
                    
                    logger.debug(f"Identity API response status: {result.get('status_code')}")
                    
                    if result.get("success") and result.get("data"):
                        data = result["data"]
                        logger.debug(f"Identity API response data: {data}")

                        # Process identities API response
                        if "value" in data and data["value"]:
                            for identity_item in data["value"]:
                                # Check if this identity matches our search
                                if _identity_matches(identity_item, identity):
                                    logger.debug(f"Found matching identity: {identity_item}")
                                    return _create_identity_info_from_api_response(identity_item)

                            # If we found results but no matches, log for debugging
                            if "value" in data and data["value"]:
                                logger.debug(f"Found {len(data['value'])} identities but none matched '{identity}'")
                                for item in data["value"]:
                                    logger.debug(f"Available identity: {item.get('displayName', 'N/A')} ({item.get('uniqueName', 'N/A')})")
                    else:
                        # Handle error cases
                        status_code = result.get("status_code", 0)
                        error_msg = result.get("error", "Unknown error")
                        
                        if status_code == 401:
                            logger.warning(f"Authentication failed for endpoint {endpoint}")
                        elif status_code == 403:
                            logger.warning(f"Access denied for endpoint {endpoint}")
                        else:
                            logger.debug(f"Identity API returned error: {error_msg}")

                except Exception as e:
                    logger.debug(f"Failed to resolve identity via endpoint {endpoint}: {e}")
                    continue

        # Enhanced fallback strategies
        logger.debug(f"API resolution failed, trying fallback strategies for '{identity}'")
        
        # Strategy 1: If it looks like an email, accept it directly
        if is_valid_email(identity):
            logger.debug(f"Identity '{identity}' is a valid email format, accepting directly")
            return IdentityInfo(
                display_name=identity,
                unique_name=identity,
                id="",
                descriptor="",
                is_valid=True,
                error_message=""
            )
        
        # Strategy 2: Try common email domain patterns for the username
        # This is useful for corporate environments where username might be part of email
        common_domains = []
        
        # Extract potential domain from organization URL
        if "visualstudio.com" in organization or "dev.azure.com" in organization:
            # For Azure DevOps organizations, try to infer domain
            if "dev.azure.com" in organization:
                # For dev.azure.com URLs, extract the organization name from the path
                org_name = organization.split("/")[-1] if "/" in organization else organization
            else:
                # For visualstudio.com URLs, extract from subdomain
                org_name = organization.split("//")[1].split(".")[0] if "//" in organization else organization
            logger.debug(f"Extracted organization name: {org_name}")
            
            # Generic patterns for Azure DevOps organizations
            common_domains = [
                f"{org_name}.com",
                f"{org_name}.onmicrosoft.com"
            ]
            
            logger.debug(f"Will try common domains: {common_domains}")
        
        # Try common domain patterns
        for domain in common_domains:
            potential_email = f"{identity}@{domain}"
            logger.debug(f"Trying potential email format: {potential_email}")
            
            # Validate email format and return directly if valid
            if is_valid_email(potential_email):
                logger.debug(f"Accepting constructed email format: {potential_email}")
                return IdentityInfo(
                    display_name=potential_email,
                    unique_name=potential_email,
                    id="",
                    descriptor="",
                    is_valid=True,
                    error_message=""
                )

        # If all resolution attempts fail
        error_msg = f"Unable to resolve identity '{identity}' in organization '{organization}'"
        logger.warning(error_msg)
        return IdentityInfo(
            display_name="",
            unique_name="",
            id="",
            descriptor="",
            is_valid=False,
            error_message=error_msg
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

    # First try exact matches
    for field in fields_to_check:
        if field and field.lower() == search_lower:
            return True

    # Then try partial matches (contains)
    for field in fields_to_check:
        if field and search_lower in field.lower():
            return True
    
    # Special handling for username patterns
    # If search term looks like a username (no @ symbol), try matching against email prefixes
    if "@" not in search_term:
        for field in fields_to_check:
            if field and "@" in field:
                # Extract username part from email
                email_prefix = field.split("@")[0].lower()
                if email_prefix == search_lower:
                    return True
                # Also try partial match on email prefix
                if search_lower in email_prefix:
                    return True
    
    # Try reverse matching - if the field contains the search term as a substring
    # This helps with cases where display names might contain the username
    for field in fields_to_check:
        if field and len(search_term) >= 3:  # Only for reasonably long search terms
            field_words = field.lower().split()
            for word in field_words:
                if search_lower in word or word in search_lower:
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
    global _bearer_token_cache, _bearer_token_cache_expiry

    bearer_token = None

    # Always get fresh Azure repo parameters from environment manager
    # This ensures we get the latest configuration, including any mocked values in tests
    azrepo_params = env_manager.get_azrepo_parameters()

    # Try bearer token command first (takes precedence over static token)
    bearer_token_command = azrepo_params.get("bearer_token_command")
    if bearer_token_command:
        # Check if we have a cached token that's still valid
        if (_bearer_token_cache and _bearer_token_cache_expiry and
            datetime.now() < _bearer_token_cache_expiry):
            bearer_token = _bearer_token_cache
            logger.debug("Using cached bearer token")
        else:
            # Execute command to get fresh token
            bearer_token = execute_bearer_token_command(bearer_token_command)
            if bearer_token:
                # Cache the token for a short period
                _bearer_token_cache = bearer_token
                _bearer_token_cache_expiry = datetime.now() + timedelta(seconds=BEARER_TOKEN_CACHE_DURATION_SECONDS)
                logger.debug("Cached new bearer token")

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
