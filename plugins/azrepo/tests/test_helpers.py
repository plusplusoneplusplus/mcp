"""Utility helpers for azrepo plugin tests."""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict, Generator, Iterable, Optional, Tuple

from unittest.mock import AsyncMock, MagicMock, patch

from plugins.azrepo.azure_rest_utils import (
    IdentityInfo,
    clear_bearer_token_cache,
    _identity_cache,
    _cache_expiry,
)

# Prevent pytest from collecting this module as tests
__test__ = False


# ---------------------------------------------------------------------------
# Test data factories
# ---------------------------------------------------------------------------

def create_mock_work_item_response(
    item_id: int = 1,
    state: str = "Active",
    title: str = "Test Work Item",
) -> Dict[str, Any]:
    """Create a minimal mock work item response."""
    return {
        "id": item_id,
        "fields": {
            "System.Title": title,
            "System.State": state,
        },
        "url": f"https://dev.azure.com/org/project/_apis/wit/workitems/{item_id}",
    }


def create_mock_pr_response(
    pr_id: int = 1,
    status: str = "active",
    title: str = "Test PR",
) -> Dict[str, Any]:
    """Create a minimal mock pull request response."""
    return {
        "pullRequestId": pr_id,
        "status": status,
        "title": title,
    }


def create_mock_identity_info(
    display_name: str = "User",
    unique_name: str = "user@example.com",
) -> IdentityInfo:
    """Create a mock :class:`IdentityInfo` instance."""
    return IdentityInfo(
        display_name=display_name,
        unique_name=unique_name,
        id="00000000-0000-0000-0000-000000000000",
        descriptor="mock",
        is_valid=True,
        error_message="",
    )


def create_default_config() -> Dict[str, Any]:
    """Return a default configuration dictionary used in tests."""
    return {
        "org": "test-org",
        "project": "test-project",
        "repository": "test-repo",
        "token": "fake-token",
    }


# ---------------------------------------------------------------------------
# Context manager utilities
# ---------------------------------------------------------------------------

@contextmanager
def mock_azure_http_client_context(
    method: str = "get",
    response: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    error_message: Optional[str] = None,
    raw_response: str = "",
) -> Generator:
    """Context manager to mock ``AzureHttpClient`` requests."""
    response = response or {"success": status_code < 300, "data": {}}
    mock_client = MagicMock()
    success = status_code < 300 and error_message is None
    mock_client.request = AsyncMock(
        return_value={
            "success": success,
            "data": response,
            "error": error_message,
            "status_code": status_code,
            "raw_response": raw_response,
        }
    )
    with patch("plugins.azrepo.workitem_tool.AzureHttpClient", return_value=mock_client) as p:
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        yield p


@contextmanager
def mock_env_managers() -> Generator:
    """Patch env_manager usage in both tool modules."""
    with patch("plugins.azrepo.workitem_tool.env_manager") as w, patch(
        "plugins.azrepo.azure_rest_utils.env_manager"
    ) as r:
        yield w, r


@contextmanager
def mock_auth_headers(headers: Optional[Dict[str, str]] = None) -> Generator:
    """Patch ``get_auth_headers`` to return predefined headers."""
    if headers is None:
        headers = {"Authorization": "Bearer fake"}
    with patch("plugins.azrepo.azure_rest_utils.get_auth_headers", return_value=headers), \
        patch("plugins.azrepo.pr_tool.get_auth_headers", return_value=headers):
        yield


@contextmanager
def mock_current_username(name: str = "testuser") -> Generator:
    """Patch ``get_current_username`` helper."""
    with patch("plugins.azrepo.azure_rest_utils.get_current_username", return_value=name):
        yield


@contextmanager
def mock_identity_resolution(identity: Optional[IdentityInfo] = None) -> Generator:
    """Patch ``resolve_identity`` to return a pre-defined identity."""
    identity = identity or create_mock_identity_info()
    with patch("plugins.azrepo.azure_rest_utils.resolve_identity", return_value=identity), \
        patch("plugins.azrepo.pr_tool.resolve_identity", return_value=identity):
        yield


@contextmanager
def mock_full_azure_environment() -> Generator:
    """Mock env managers, auth headers and identity resolution."""
    with mock_env_managers() as managers, mock_auth_headers(), mock_identity_resolution():
        yield managers


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------

def assert_success_response(result: Dict[str, Any]) -> None:
    """Assert that a result dictionary represents a successful response."""
    assert result.get("success") is True
    assert "error" not in result


def assert_error_response(result: Dict[str, Any]) -> None:
    """Assert that a result dictionary represents a failed response."""
    assert result.get("success") is False
    assert "error" in result


def assert_http_client_called_with_method(mock_client: MagicMock, method: str) -> None:
    """Assert that the HTTP client was called with the expected method."""
    getattr(mock_client.return_value, method).assert_called()


# ---------------------------------------------------------------------------
# Cache helpers and base class
# ---------------------------------------------------------------------------

def clear_identity_cache() -> None:
    """Clear in-memory identity caches used in tests."""
    _identity_cache.clear()
    _cache_expiry.clear()


def clear_identity_cache_decorator(func):
    """Decorator to clear identity cache after a test function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            clear_identity_cache()
    return wrapper


def clear_bearer_token_cache_decorator(func):
    """Decorator to clear bearer token cache after a test function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            clear_bearer_token_cache()
    return wrapper


class BaseTestClass:
    """Base class providing automatic cache clearing in ``setup_method``."""

    def setup_method(self) -> None:  # pragma: no cover - simple cache clearing
        clear_identity_cache()
        clear_bearer_token_cache()


# ---------------------------------------------------------------------------
# Parameterised test data
# ---------------------------------------------------------------------------

def create_test_cases_for_http_errors(codes: Iterable[int]) -> Iterable[Tuple[int, str]]:
    """Create parameterized data for HTTP error tests."""
    return [(code, f"HTTP {code}") for code in codes]


def create_test_cases_for_work_item_types(types: Iterable[str]) -> Iterable[Tuple[str]]:
    """Create parameterized data for work item type tests."""
    return [(t,) for t in types]


def create_test_cases_for_pr_statuses(statuses: Iterable[str]) -> Iterable[Tuple[str]]:
    """Create parameterized data for pull request status tests."""
    return [(s,) for s in statuses]

