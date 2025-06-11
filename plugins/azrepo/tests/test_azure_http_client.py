"""Unit tests for AzureHttpClient class."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientError, ServerTimeoutError
from aiohttp.web import Response

# Import the class under test
from ..azure_rest_utils import AzureHttpClient


class AsyncContextManagerMock:
    """Helper class to properly mock async context managers."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


class TestAzureHttpClient:
    """Test cases for AzureHttpClient class."""

    def test_default_configuration(self):
        """Test client initialization with default configuration."""
        client = AzureHttpClient()

        assert client.total_connections == 100
        assert client.per_host_connections == 30
        assert client.dns_cache_ttl == 300
        assert client.request_timeout == 30
        assert client.max_retries == 3
        assert client.retry_backoff_factor == 0.5
        assert client.retry_statuses == [429, 500, 502, 503, 504]

    def test_custom_configuration(self):
        """Test client initialization with custom configuration."""
        client = AzureHttpClient(
            total_connections=50,
            per_host_connections=15,
            dns_cache_ttl=600,
            request_timeout=60,
            max_retries=5,
            retry_backoff_factor=2.0,
            retry_statuses=[429, 500]
        )

        assert client.total_connections == 50
        assert client.per_host_connections == 15
        assert client.dns_cache_ttl == 600
        assert client.request_timeout == 60
        assert client.max_retries == 5
        assert client.retry_backoff_factor == 2.0
        assert client.retry_statuses == [429, 500]

    @pytest.mark.asyncio
    async def test_session_not_initialized_error(self):
        """Test error when trying to make request without initializing session."""
        client = AzureHttpClient()

        with pytest.raises(RuntimeError, match="AzureHttpClient session not initialized"):
            await client.get("https://example.com")

    @pytest.mark.asyncio
    async def test_context_manager_basic(self):
        """Test basic context manager functionality."""
        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector') as mock_tcp_connector, \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session:

            # Mock connector and session with proper async methods
            mock_connector = AsyncMock()
            mock_session = AsyncMock()
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            client = AzureHttpClient()

            async with client:
                # Verify session was initialized
                mock_tcp_connector.assert_called_once()
                mock_client_session.assert_called_once()

            # Verify cleanup was called
            mock_session.close.assert_called_once()
            mock_connector.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_get_request(self):
        """Test successful GET request."""
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}
        test_response_data = {"result": "success"}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector') as mock_tcp_connector, \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session:

            # Mock connector and session with proper async methods
            mock_connector = AsyncMock()
            mock_session = MagicMock()  # Use MagicMock for session to avoid coroutine issues
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            # Mock response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(test_response_data))

            # Mock the async context manager for session.request
            mock_session.request.return_value = AsyncContextManagerMock(mock_response)
            mock_session.close = AsyncMock()  # Ensure close is async

            client = AzureHttpClient()

            async with client:
                result = await client.get(test_url, headers=test_headers)

            # Verify response processing
            assert result['success'] is True
            assert result['data'] == test_response_data

            # Verify request was made correctly
            mock_session.request.assert_called_once_with(
                method='GET', url=test_url, headers=test_headers
            )

    @pytest.mark.asyncio
    async def test_successful_post_request_with_json(self):
        """Test successful POST request with JSON payload."""
        test_url = "https://api.example.com/create"
        test_headers = {"Authorization": "Bearer token"}
        test_json_data = {"name": "test", "value": 123}
        test_response_data = {"id": 456, "created": True}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector') as mock_tcp_connector, \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session:

            # Mock connector and session with proper async methods
            mock_connector = AsyncMock()
            mock_session = MagicMock()  # Use MagicMock for session to avoid coroutine issues
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            # Mock response
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.text = AsyncMock(return_value=json.dumps(test_response_data))

            # Mock the async context manager for session.request
            mock_session.request.return_value = AsyncContextManagerMock(mock_response)
            mock_session.close = AsyncMock()  # Ensure close is async

            client = AzureHttpClient()

            async with client:
                result = await client.post(test_url, headers=test_headers, json=test_json_data)

            # Verify response processing
            assert result['success'] is True
            assert result['data'] == test_response_data

            # Verify request was made correctly
            mock_session.request.assert_called_once_with(
                method='POST', url=test_url, headers=test_headers, json=test_json_data
            )

    @pytest.mark.asyncio
    async def test_retry_logic_on_server_error(self):
        """Test retry logic when server returns 500 error."""
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector') as mock_tcp_connector, \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.asyncio.sleep') as mock_sleep:

            # Mock connector and session with proper async methods
            mock_connector = AsyncMock()
            mock_session = MagicMock()  # Use MagicMock for session to avoid coroutine issues
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            # Mock responses - first two fail, third succeeds
            mock_responses = []
            for status in [500, 500, 200]:
                mock_response = MagicMock()
                mock_response.status = status
                if status == 200:
                    mock_response.text = AsyncMock(return_value='{"result": "success"}')
                else:
                    mock_response.text = AsyncMock(return_value='Internal Server Error')
                mock_responses.append(mock_response)

            # Mock the async context manager to return different responses
            mock_session.request.side_effect = [
                AsyncContextManagerMock(mock_responses[0]),
                AsyncContextManagerMock(mock_responses[1]),
                AsyncContextManagerMock(mock_responses[2])
            ]
            mock_session.close = AsyncMock()  # Ensure close is async

            client = AzureHttpClient()

            async with client:
                result = await client.get(test_url, headers=test_headers)

            # Verify final success
            assert result['success'] is True
            assert result['data'] == {"result": "success"}

            # Verify retries occurred
            assert mock_session.request.call_count == 3
            assert mock_sleep.call_count == 2  # 2 retries = 2 sleep calls

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test behavior when all retries are exhausted."""
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector') as mock_tcp_connector, \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.asyncio.sleep') as mock_sleep:

            # Mock connector and session with proper async methods
            mock_connector = AsyncMock()
            mock_session = MagicMock()  # Use MagicMock for session to avoid coroutine issues
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            # Mock response - always returns 500
            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value='Internal Server Error')

            # Mock the async context manager to always return the failing response
            mock_session.request.return_value = AsyncContextManagerMock(mock_response)
            mock_session.close = AsyncMock()  # Ensure close is async

            client = AzureHttpClient()

            async with client:
                result = await client.get(test_url, headers=test_headers)

            # Verify final failure
            assert result['success'] is False
            assert "HTTP 500" in result['error']

            # Verify all retries were attempted (1 initial + 3 retries = 4 total)
            assert mock_session.request.call_count == 4
            assert mock_sleep.call_count == 3  # 3 retries = 3 sleep calls

    @pytest.mark.asyncio
    async def test_client_error_no_retry(self):
        """Test that client errors don't trigger retries (except timeouts)."""
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector') as mock_tcp_connector, \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session:

            # Mock connector and session with proper async methods
            mock_connector = AsyncMock()
            mock_session = MagicMock()  # Use MagicMock for session to avoid coroutine issues
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            # Mock session that raises ClientError
            mock_session.request.side_effect = ClientError("Connection failed")
            mock_session.close = AsyncMock()  # Ensure close is async

            client = AzureHttpClient()

            async with client:
                result = await client.get(test_url, headers=test_headers)

            # Verify failure without retries
            assert result['success'] is False
            assert "Connection failed" in result['error']

            # Verify no retries occurred (only 1 attempt)
            assert mock_session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_timeout_error_with_retry(self):
        """Test that timeout errors trigger retries."""
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector') as mock_tcp_connector, \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.asyncio.sleep') as mock_sleep:

            # Mock connector and session with proper async methods
            mock_connector = AsyncMock()
            mock_session = MagicMock()  # Use MagicMock for session to avoid coroutine issues
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            # Mock response for successful attempt
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"result": "success"}')

            # Mock session that raises timeout errors then succeeds
            mock_session.request.side_effect = [
                ServerTimeoutError("Timeout"),
                ServerTimeoutError("Timeout"),
                AsyncContextManagerMock(mock_response)
            ]
            mock_session.close = AsyncMock()  # Ensure close is async

            client = AzureHttpClient()

            async with client:
                result = await client.get(test_url, headers=test_headers)

            # Verify final success
            assert result['success'] is True
            assert result['data'] == {"result": "success"}

            # Verify retries occurred (2 timeouts + 1 success = 3 attempts)
            assert mock_session.request.call_count == 3
            assert mock_sleep.call_count == 2  # 2 retries = 2 sleep calls

    @pytest.mark.asyncio
    async def test_convenience_methods(self):
        """Test all convenience methods (get, post, patch, put, delete)."""
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector') as mock_tcp_connector, \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session:

            # Mock connector and session with proper async methods
            mock_connector = AsyncMock()
            mock_session = MagicMock()  # Use MagicMock for session to avoid coroutine issues
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            # Mock response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"result": "success"}')

            # Mock the async context manager
            mock_session.request.return_value = AsyncContextManagerMock(mock_response)
            mock_session.close = AsyncMock()  # Ensure close is async

            client = AzureHttpClient()

            async with client:
                # Test all HTTP methods
                methods = ['get', 'post', 'patch', 'put', 'delete']
                for method in methods:
                    method_func = getattr(client, method)
                    result = await method_func(test_url, headers=test_headers)

                    assert result['success'] is True
                    assert result['data'] == {"result": "success"}

            # Verify all methods were called
            assert mock_session.request.call_count == len(methods)

    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self):
        """Test that exponential backoff delays are calculated correctly."""
        test_url = "https://api.example.com/test"

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector') as mock_tcp_connector, \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.asyncio.sleep') as mock_sleep:

            # Mock connector and session with proper async methods
            mock_connector = AsyncMock()
            mock_session = MagicMock()  # Use MagicMock for session to avoid coroutine issues
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            # Mock response - always returns 500 to trigger retries
            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value='Internal Server Error')

            # Mock the async context manager
            mock_session.request.return_value = AsyncContextManagerMock(mock_response)
            mock_session.close = AsyncMock()  # Ensure close is async

            client = AzureHttpClient()

            async with client:
                await client.get(test_url)

            # Verify exponential backoff with default factor 0.5: 0.5, 1.0, 2.0 seconds
            expected_delays = [0.5, 1.0, 2.0]
            actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
            assert actual_delays == expected_delays

    @pytest.mark.asyncio
    async def test_azure_convenience_methods(self):
        """Test Azure DevOps convenience methods with automatic auth and URL building."""
        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector') as mock_tcp_connector, \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.get_auth_headers') as mock_get_auth, \
             patch('plugins.azrepo.azure_rest_utils.build_api_url') as mock_build_url:

            # Mock connector and session with proper async methods
            mock_connector = AsyncMock()
            mock_session = MagicMock()  # Use MagicMock for session to avoid coroutine issues
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            # Mock response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"result": "success"}')

            # Mock the async context manager for session.request
            mock_session.request.return_value = AsyncContextManagerMock(mock_response)
            mock_session.close = AsyncMock()  # Ensure close is async

            # Mock utility functions
            mock_get_auth.return_value = {"Authorization": "Bearer token", "Content-Type": "application/json"}
            mock_build_url.return_value = "https://dev.azure.com/org/project/_apis/test"

            client = AzureHttpClient()

            async with client:
                # Test azure_get method
                result = await client.azure_get("org", "project", "test", params={"api-version": "7.1"})

                # Verify utility functions were called
                mock_build_url.assert_called_with("org", "project", "test")
                mock_get_auth.assert_called_with("application/json")

                # Verify response
                assert result['success'] is True
                assert result['data'] == {"result": "success"}

    @pytest.mark.asyncio
    async def test_azure_post_with_json(self):
        """Test Azure DevOps POST method with JSON payload."""
        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector') as mock_tcp_connector, \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.get_auth_headers') as mock_get_auth, \
             patch('plugins.azrepo.azure_rest_utils.build_api_url') as mock_build_url:

            # Mock connector and session with proper async methods
            mock_connector = AsyncMock()
            mock_session = MagicMock()  # Use MagicMock for session to avoid coroutine issues
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            # Mock response
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.text = AsyncMock(return_value='{"id": 123, "created": true}')

            # Mock the async context manager for session.request
            mock_session.request.return_value = AsyncContextManagerMock(mock_response)
            mock_session.close = AsyncMock()  # Ensure close is async

            # Mock utility functions
            mock_get_auth.return_value = {"Authorization": "Bearer token", "Content-Type": "application/json"}
            mock_build_url.return_value = "https://dev.azure.com/org/project/_apis/test"

            client = AzureHttpClient()

            async with client:
                # Test azure_post method
                test_data = {"name": "test", "value": 123}
                result = await client.azure_post("org", "project", "test", json=test_data)

                # Verify utility functions were called
                mock_build_url.assert_called_with("org", "project", "test")
                mock_get_auth.assert_called_with("application/json")

                # Verify response
                assert result['success'] is True
                assert result['data'] == {"id": 123, "created": True}
