"""
Tests for Azure DevOps identity resolution functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import aiohttp
from datetime import datetime, timedelta

from plugins.azrepo.azure_rest_utils import (
    IdentityInfo,
    is_valid_email,
    normalize_identity_input,
    resolve_identity,
    validate_and_format_assignee,
    _identity_cache,
    _cache_expiry,
    _is_cache_valid,
    _cache_identity,
    _identity_matches,
    _create_identity_info_from_api_response,
)


class TestEmailValidation:
    """Test email validation functionality."""

    def test_valid_emails(self):
        """Test valid email formats."""
        valid_emails = [
            "user@domain.com",
            "test.user@company.org",
            "user+tag@domain.co.uk",
            "user123@test-domain.com",
            "a@b.co",
        ]

        for email in valid_emails:
            assert is_valid_email(email), f"Email '{email}' should be valid"

    def test_invalid_emails(self):
        """Test invalid email formats."""
        invalid_emails = [
            "not-an-email",
            "@domain.com",
            "user@",
            "user@domain",
            "user.domain.com",
            "",
            "user@domain.",
            "user name@domain.com",
        ]

        for email in invalid_emails:
            assert not is_valid_email(email), f"Email '{email}' should be invalid"


class TestIdentityNormalization:
    """Test identity input normalization."""

    def test_normalize_basic_inputs(self):
        """Test normalization of basic identity inputs."""
        test_cases = [
            ("user@domain.com", "user@domain.com"),
            ("  user@domain.com  ", "user@domain.com"),
            ("John Doe", "John Doe"),
            ("", ""),
        ]

        for input_val, expected in test_cases:
            assert normalize_identity_input(input_val) == expected

    def test_normalize_combo_format(self):
        """Test normalization of combo format identities."""
        test_cases = [
            ("John Doe <user@domain.com>", "user@domain.com"),
            ("Jane Smith<jane@company.org>", "jane@company.org"),
            ("  Test User  <  test@domain.com  >  ", "test@domain.com"),
            ("Display Name <email@domain.co.uk>", "email@domain.co.uk"),
        ]

        for input_val, expected in test_cases:
            assert normalize_identity_input(input_val) == expected


class TestIdentityCache:
    """Test identity caching functionality."""

    def setup_method(self):
        """Clear cache before each test."""
        _identity_cache.clear()
        _cache_expiry.clear()

    def test_cache_validity(self):
        """Test cache validity checking."""
        cache_key = "test_key"

        # Initially invalid (not in cache)
        assert not _is_cache_valid(cache_key)

        # Add to cache with future expiry
        _cache_expiry[cache_key] = datetime.now() + timedelta(minutes=10)
        assert _is_cache_valid(cache_key)

        # Expired cache
        _cache_expiry[cache_key] = datetime.now() - timedelta(minutes=1)
        assert not _is_cache_valid(cache_key)

    def test_cache_identity(self):
        """Test identity caching."""
        cache_key = "test_org:test_proj:user@domain.com"
        identity_data = {
            "display_name": "Test User",
            "unique_name": "user@domain.com",
            "id": "123",
            "descriptor": "desc123",
            "is_valid": True,
            "error_message": ""
        }

        _cache_identity(cache_key, identity_data)

        assert cache_key in _identity_cache
        assert _identity_cache[cache_key] == identity_data
        assert _is_cache_valid(cache_key)


class TestIdentityMatching:
    """Test identity matching logic."""

    def test_identity_matches_basic_fields(self):
        """Test identity matching against basic fields."""
        identity_item = {
            "displayName": "John Doe",
            "uniqueName": "john.doe@company.com",
            "mailAddress": "john.doe@company.com",
            "providerDisplayName": "John Doe"
        }

        # Should match various search terms
        assert _identity_matches(identity_item, "john.doe@company.com")
        assert _identity_matches(identity_item, "John Doe")
        assert _identity_matches(identity_item, "john")
        assert _identity_matches(identity_item, "doe")
        assert _identity_matches(identity_item, "company.com")

        # Should not match unrelated terms
        assert not _identity_matches(identity_item, "jane")
        assert not _identity_matches(identity_item, "smith")

    def test_identity_matches_properties(self):
        """Test identity matching against properties."""
        identity_item = {
            "displayName": "Test User",
            "properties": {
                "Account": {"$value": "testuser"},
                "Mail": {"$value": "test@domain.com"}
            }
        }

        assert _identity_matches(identity_item, "testuser")
        assert _identity_matches(identity_item, "test@domain.com")
        assert _identity_matches(identity_item, "domain.com")


class TestIdentityInfoCreation:
    """Test IdentityInfo creation from API responses."""

    def test_create_identity_info_basic(self):
        """Test creating IdentityInfo from basic API response."""
        api_response = {
            "displayName": "John Doe",
            "uniqueName": "john.doe@company.com",
            "id": "user123",
            "descriptor": "desc123"
        }

        identity_info = _create_identity_info_from_api_response(api_response)

        assert identity_info.display_name == "John Doe"
        assert identity_info.unique_name == "john.doe@company.com"
        assert identity_info.id == "user123"
        assert identity_info.descriptor == "desc123"
        assert identity_info.is_valid is True
        assert identity_info.error_message == ""

    def test_create_identity_info_with_properties(self):
        """Test creating IdentityInfo with properties fallback."""
        api_response = {
            "displayName": "Test User",
            "properties": {
                "Mail": {"$value": "test@domain.com"},
                "Account": {"$value": "testaccount"}
            },
            "id": "user456"
        }

        identity_info = _create_identity_info_from_api_response(api_response)

        assert identity_info.display_name == "Test User"
        assert identity_info.unique_name == "test@domain.com"
        assert identity_info.id == "user456"

    def test_create_identity_info_provider_display_name(self):
        """Test creating IdentityInfo with providerDisplayName priority."""
        api_response = {
            "providerDisplayName": "Provider Name",
            "displayName": "Display Name",
            "uniqueName": "user@domain.com",
            "id": "user789"
        }

        identity_info = _create_identity_info_from_api_response(api_response)

        assert identity_info.display_name == "Provider Name"  # Should prefer providerDisplayName


class TestResolveIdentity:
    """Test identity resolution functionality."""

    def setup_method(self):
        """Clear cache before each test."""
        _identity_cache.clear()
        _cache_expiry.clear()

    @pytest.mark.asyncio
    async def test_resolve_identity_empty(self):
        """Test resolving empty or None identity."""
        result = await resolve_identity("", "test_org")
        assert not result.is_valid
        assert "empty" in result.error_message.lower()

        result = await resolve_identity("none", "test_org")
        assert not result.is_valid
        assert "unassigned" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_resolve_identity_cached(self):
        """Test resolving identity from cache."""
        cache_key = "test_org:global:user@domain.com"
        cached_data = {
            "display_name": "Cached User",
            "unique_name": "user@domain.com",
            "id": "cached123",
            "descriptor": "cached_desc",
            "is_valid": True,
            "error_message": ""
        }
        _cache_identity(cache_key, cached_data)

        result = await resolve_identity("user@domain.com", "test_org")

        assert result.is_valid
        assert result.display_name == "Cached User"
        assert result.unique_name == "user@domain.com"

    @pytest.mark.asyncio
    @patch('plugins.azrepo.azure_rest_utils.get_auth_headers')
    async def test_resolve_identity_api_success(self, mock_auth_headers):
        """Test successful identity resolution via API."""
        # Mock authentication headers
        mock_auth_headers.return_value = {"Authorization": "Bearer token"}

        # Mock API response
        mock_response_data = {
            "value": [
                {
                    "displayName": "API User",
                    "uniqueName": "api.user@company.com",
                    "id": "api123",
                    "descriptor": "api_desc"
                }
            ]
        }

        # Mock the entire API resolution function to return our expected result
        with patch('plugins.azrepo.azure_rest_utils._resolve_identity_via_api') as mock_api_resolve:
            mock_api_resolve.return_value = IdentityInfo(
                display_name="API User",
                unique_name="api.user@company.com",
                id="api123",
                descriptor="api_desc",
                is_valid=True,
                error_message=""
            )

            result = await resolve_identity("api.user@company.com", "test_org")

        assert result.is_valid
        assert result.display_name == "API User"
        assert result.unique_name == "api.user@company.com"
        assert result.id == "api123"

    @pytest.mark.asyncio
    @patch('plugins.azrepo.azure_rest_utils.get_auth_headers')
    @patch('plugins.azrepo.azure_rest_utils.AzureHttpClient')
    async def test_resolve_identity_api_no_match(self, mock_azure_client, mock_auth_headers):
        """Test identity resolution when API returns no matches."""
        # Mock authentication headers
        mock_auth_headers.return_value = {"Authorization": "Bearer token"}

        # Mock API response with no matching identities
        mock_response_data = {"value": []}

        # Mock AzureHttpClient
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = {
            "success": True,
            "data": mock_response_data,
            "status_code": 200
        }
        mock_azure_client.return_value.__aenter__.return_value = mock_client_instance

        # Test with valid email (should create basic identity)
        result = await resolve_identity("valid@email.com", "test_org")

        assert result.is_valid
        assert result.display_name == "valid@email.com"
        assert result.unique_name == "valid@email.com"

    @pytest.mark.asyncio
    @patch('plugins.azrepo.azure_rest_utils.get_auth_headers')
    @patch('plugins.azrepo.azure_rest_utils.AzureHttpClient')
    async def test_resolve_identity_api_error(self, mock_azure_client, mock_auth_headers):
        """Test identity resolution when API returns error."""
        # Mock authentication headers
        mock_auth_headers.return_value = {"Authorization": "Bearer token"}

        # Mock AzureHttpClient to return error
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = {
            "success": False,
            "error": "Internal server error",
            "status_code": 500
        }
        mock_azure_client.return_value.__aenter__.return_value = mock_client_instance

        # Test with invalid identity (not email format)
        result = await resolve_identity("invalid_identity", "test_org")

        assert not result.is_valid
        assert "Unable to resolve identity" in result.error_message


class TestValidateAndFormatAssignee:
    """Test assignee validation and formatting."""

    def setup_method(self):
        """Clear cache before each test."""
        _identity_cache.clear()
        _cache_expiry.clear()

    @pytest.mark.asyncio
    async def test_validate_assignee_none(self):
        """Test validating None or 'none' assignee."""
        result, error = await validate_and_format_assignee(None, "test_org")
        assert result is None
        assert error == ""

        result, error = await validate_and_format_assignee("none", "test_org")
        assert result is None
        assert error == ""

        result, error = await validate_and_format_assignee("unassigned", "test_org")
        assert result is None
        assert error == ""

    @pytest.mark.asyncio
    @patch('plugins.azrepo.azure_rest_utils.get_current_username')
    @patch('plugins.azrepo.azure_rest_utils.resolve_identity')
    async def test_validate_assignee_current_success(self, mock_resolve, mock_get_username):
        """Test validating 'current' assignee successfully."""
        mock_get_username.return_value = "currentuser"
        mock_resolve.return_value = IdentityInfo(
            display_name="Current User",
            unique_name="current@company.com",
            id="current123",
            descriptor="current_desc",
            is_valid=True
        )

        result, error = await validate_and_format_assignee("current", "test_org")

        assert result == "current@company.com"
        assert error == ""
        mock_resolve.assert_called_once_with("currentuser", "test_org", None)

    @pytest.mark.asyncio
    @patch('plugins.azrepo.azure_rest_utils.get_current_username')
    async def test_validate_assignee_current_no_username(self, mock_get_username):
        """Test validating 'current' assignee when username cannot be determined."""
        mock_get_username.return_value = None

        result, error = await validate_and_format_assignee("current", "test_org")

        assert result is None
        assert "Unable to determine current user" in error

    @pytest.mark.asyncio
    @patch('plugins.azrepo.azure_rest_utils.resolve_identity')
    async def test_validate_assignee_explicit_success(self, mock_resolve):
        """Test validating explicit assignee successfully."""
        mock_resolve.return_value = IdentityInfo(
            display_name="Test User",
            unique_name="test@company.com",
            id="test123",
            descriptor="test_desc",
            is_valid=True
        )

        result, error = await validate_and_format_assignee("test@company.com", "test_org")

        assert result == "test@company.com"
        assert error == ""

    @pytest.mark.asyncio
    @patch('plugins.azrepo.azure_rest_utils.resolve_identity')
    async def test_validate_assignee_explicit_failure(self, mock_resolve):
        """Test validating explicit assignee that fails resolution."""
        mock_resolve.return_value = IdentityInfo(
            display_name="",
            unique_name="",
            id="",
            descriptor="",
            is_valid=False,
            error_message="Identity not found"
        )

        result, error = await validate_and_format_assignee("invalid@company.com", "test_org", fallback_to_current_user=False)

        assert result is None
        assert "Unable to resolve identity" in error
        assert "Identity not found" in error

    @pytest.mark.asyncio
    @patch('plugins.azrepo.azure_rest_utils.resolve_identity')
    async def test_validate_assignee_with_fallback(self, mock_resolve):
        """Test validating assignee with fallback to current user."""
        # First call fails, second call (fallback) succeeds
        mock_resolve.side_effect = [
            IdentityInfo(
                display_name="",
                unique_name="",
                id="",
                descriptor="",
                is_valid=False,
                error_message="Identity not found"
            ),
            IdentityInfo(
                display_name="Current User",
                unique_name="current@company.com",
                id="current123",
                descriptor="current_desc",
                is_valid=True
            )
        ]

        with patch('plugins.azrepo.azure_rest_utils.get_current_username', return_value="currentuser"):
            result, error = await validate_and_format_assignee(
                "invalid@company.com", "test_org", fallback_to_current_user=True
            )

        assert result == "current@company.com"
        assert error == ""
        assert mock_resolve.call_count == 2

    @pytest.mark.asyncio
    @patch('plugins.azrepo.azure_rest_utils.resolve_identity')
    async def test_validate_assignee_exception_handling(self, mock_resolve):
        """Test exception handling in assignee validation."""
        mock_resolve.side_effect = Exception("API Error")

        result, error = await validate_and_format_assignee("test@company.com", "test_org", fallback_to_current_user=False)

        assert result is None
        assert "Unable to resolve identity" in error
        assert "API Error" in error


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple components."""

    def setup_method(self):
        """Clear cache before each test."""
        _identity_cache.clear()
        _cache_expiry.clear()

    @pytest.mark.asyncio
    async def test_full_resolution_workflow(self):
        """Test complete identity resolution workflow."""
        # Mock the API resolution to return a specific result
        with patch('plugins.azrepo.azure_rest_utils._resolve_identity_via_api') as mock_api_resolve:
            mock_api_resolve.return_value = IdentityInfo(
                display_name="John Doe",
                unique_name="john.doe@company.com",
                id="user123",
                descriptor="desc123",
                is_valid=True,
                error_message=""
            )

            # First resolution should hit API
            result, error = await validate_and_format_assignee("john.doe@company.com", "test_org")

            assert result == "john.doe@company.com"
            assert error == ""

            # Second resolution should use cache
            result2, error2 = await validate_and_format_assignee("john.doe@company.com", "test_org")

            assert result2 == "john.doe@company.com"
            assert error2 == ""

            # Verify API was only called once (second call used cache)
            assert mock_api_resolve.call_count == 1

    @pytest.mark.asyncio
    async def test_combo_format_resolution(self):
        """Test resolution of combo format identities."""
        # Cache a resolved identity
        cache_key = "test_org:global:user@domain.com"
        cached_data = {
            "display_name": "John Doe",
            "unique_name": "user@domain.com",
            "id": "user123",
            "descriptor": "desc123",
            "is_valid": True,
            "error_message": None
        }
        _cache_identity(cache_key, cached_data)

        # Test combo format resolution
        result, error = await validate_and_format_assignee("John Doe <user@domain.com>", "test_org")

        assert result == "user@domain.com"
        assert error == ""
