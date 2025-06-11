"""Unit tests for AzureHttpClient class."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientError, ServerTimeoutError
from aiohttp.web import Response

# Import the class under test
from ..azure_rest_utils import AzureHttpClient


class TestAzureHttpClient:
    """Test cases for AzureHttpClient class."""

    def test_default_configuration(self):
        """Test that default configuration values are set correctly."""
        client = AzureHttpClient()

        assert client.total_connections == 100
        assert client.per_host_connections == 30
        assert client.dns_cache_ttl == 300
        assert client.request_timeout == 30
        assert client.max_retries == 3
        assert client.retry_backoff_factor == 0.5
        assert client.retry_statuses == [429, 500, 502, 503, 504]

    def test_custom_configuration(self):
        """Test that custom configuration values are applied correctly."""
        config = {
            'total_connections': 10,
            'per_host_connections': 5,
            'dns_cache_ttl': 60,
            'request_timeout': 10,
            'max_retries': 2,
            'retry_backoff_factor': 0.1,
            'retry_statuses': [429, 500]
        }

        client = AzureHttpClient(
            total_connections=config['total_connections'],
            per_host_connections=config['per_host_connections'],
            dns_cache_ttl=config['dns_cache_ttl'],
            request_timeout=config['request_timeout'],
            max_retries=config['max_retries'],
            retry_backoff_factor=config['retry_backoff_factor'],
            retry_statuses=config['retry_statuses']
        )

        assert client.total_connections == config['total_connections']
        assert client.per_host_connections == config['per_host_connections']
        assert client.dns_cache_ttl == config['dns_cache_ttl']
        assert client.request_timeout == config['request_timeout']
        assert client.max_retries == config['max_retries']
        assert client.retry_backoff_factor == config['retry_backoff_factor']
        assert client.retry_statuses == config['retry_statuses']

    @pytest.mark.asyncio
    async def test_session_not_initialized_error(self):
        """Test error when trying to make request without context manager."""
        client = AzureHttpClient()

        with pytest.raises(RuntimeError, match="AzureHttpClient session not initialized"):
            await client.get("https://api.example.com/test")

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

            # Mock connector and session
            mock_connector = AsyncMock()
            mock_session = AsyncMock()
            mock_tcp_connector.return_value = mock_connector
            mock_client_session.return_value = mock_session

            # Ensure close methods are async
            mock_connector.close = AsyncMock()
            mock_session.close = AsyncMock()

            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(test_response_data))

            # Mock the context manager for session.request
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_session.request.return_value = mock_context_manager

            client = AzureHttpClient()

            async with client:
                result = await client.get(test_url, headers=test_headers)

            # Verify response processing
            assert result['success'] is True
            assert result['data'] == test_response_data
            assert result['status_code'] == 200

    @pytest.mark.asyncio
    async def test_successful_post_request_with_json(self):
        """Test successful POST request with JSON payload."""
        test_url = "https://api.example.com/create"
        test_headers = {"Authorization": "Bearer token"}
        test_json_data = {"name": "test", "value": 123}
        test_response_data = {"id": 456, "created": True}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector'), \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session:

            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.text = AsyncMock(return_value=json.dumps(test_response_data))

            # Mock session and request
            mock_session = AsyncMock()
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session.close = AsyncMock()
            mock_client_session.return_value = mock_session

            client = AzureHttpClient()

            async with client:
                result = await client.post(test_url, headers=test_headers, json=test_json_data)

            # Verify request was made correctly
            mock_session.request.assert_called_once_with(
                'POST',
                test_url,
                headers=test_headers,
                json=test_json_data
            )

            # Verify response processing
            assert result['success'] is True
            assert result['data'] == test_response_data
            assert result['status_code'] == 201

    @pytest.mark.asyncio
    async def test_retry_logic_on_server_error(self):
        """Test retry logic when server returns 500 error."""
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector'), \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.asyncio.sleep') as mock_sleep:

            # Mock responses - first two fail, third succeeds
            mock_responses = []
            for status in [500, 500, 200]:
                mock_response = AsyncMock()
                mock_response.status = status
                if status == 200:
                    mock_response.text = AsyncMock(return_value='{"result": "success"}')
                else:
                    mock_response.text = AsyncMock(return_value='Internal Server Error')
                mock_responses.append(mock_response)

            # Mock session and request
            mock_session = AsyncMock()
            mock_session.request.return_value.__aenter__.side_effect = mock_responses
            mock_session.close = AsyncMock()
            mock_client_session.return_value = mock_session

            client = AzureHttpClient()

            async with client:
                result = await client.get(test_url, headers=test_headers)

            # Verify retries were attempted
            assert mock_session.request.call_count == 3
            assert mock_sleep.call_count == 2  # Two retry delays

            # Verify final success
            assert result['success'] is True
            assert result['data'] == {"result": "success"}
            assert result['status_code'] == 200

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test behavior when all retries are exhausted."""
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector'), \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.asyncio.sleep') as mock_sleep:

            # Mock response - always returns 500
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value='Internal Server Error')

            # Mock session and request
            mock_session = AsyncMock()
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session.close = AsyncMock()
            mock_client_session.return_value = mock_session

            client = AzureHttpClient()

            async with client:
                result = await client.get(test_url, headers=test_headers)

            # Verify all retries were attempted (max_retries + 1 = 3 total attempts)
            assert mock_session.request.call_count == 3
            assert mock_sleep.call_count == 2  # Two retry delays

            # Verify final failure
            assert result['success'] is False
            assert "HTTP 500" in result['error']
            assert result['status_code'] == 500

    @pytest.mark.asyncio
    async def test_client_error_no_retry(self):
        """Test that client errors don't trigger retries (except timeouts)."""
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector'), \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session:

            # Mock session that raises ClientError
            mock_session = AsyncMock()
            mock_session.request.side_effect = ClientError("Connection failed")
            mock_session.close = AsyncMock()
            mock_client_session.return_value = mock_session

            client = AzureHttpClient()

            async with client:
                result = await client.get(test_url, headers=test_headers)

            # Verify only one attempt was made (no retries for client errors)
            assert mock_session.request.call_count == 1

            # Verify failure response
            assert result['success'] is False
            assert "Connection failed" in result['error']
            assert result['status_code'] == 0

    @pytest.mark.asyncio
    async def test_timeout_error_with_retry(self):
        """Test that timeout errors trigger retries."""
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector'), \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.asyncio.sleep') as mock_sleep:

            # Mock session that raises timeout errors then succeeds
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"result": "success"}')

            mock_session = AsyncMock()
            mock_session.request.side_effect = [
                ServerTimeoutError("Timeout"),
                ServerTimeoutError("Timeout"),
                AsyncMock(return_value=mock_response).__aenter__.return_value
            ]
            mock_session.close = AsyncMock()
            mock_client_session.return_value = mock_session

            client = AzureHttpClient()

            async with client:
                result = await client.get(test_url, headers=test_headers)

            # Verify retries were attempted for timeout
            assert mock_session.request.call_count == 3
            assert mock_sleep.call_count == 2

            # Verify final success
            assert result['success'] is True
            assert result['data'] == {"result": "success"}

    @pytest.mark.asyncio
    async def test_convenience_methods(self):
        """Test all convenience methods (get, post, patch, put, delete)."""
        test_url = "https://api.example.com/test"
        test_headers = {"Authorization": "Bearer token"}

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector'), \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session:

            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"result": "success"}')

            # Mock session and request
            mock_session = AsyncMock()
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session.close = AsyncMock()
            mock_client_session.return_value = mock_session

            client = AzureHttpClient()

            async with client:
                # Test all convenience methods
                await client.get(test_url, headers=test_headers)
                await client.post(test_url, headers=test_headers)
                await client.patch(test_url, headers=test_headers)
                await client.put(test_url, headers=test_headers)
                await client.delete(test_url, headers=test_headers)

            # Verify all methods were called with correct HTTP methods
            expected_calls = ['GET', 'POST', 'PATCH', 'PUT', 'DELETE']
            actual_calls = [call[0][0] for call in mock_session.request.call_args_list]
            assert actual_calls == expected_calls

    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self):
        """Test that exponential backoff delays are calculated correctly."""
        test_url = "https://api.example.com/test"

        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector'), \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.asyncio.sleep') as mock_sleep:

            # Mock response - always returns 500 to trigger retries
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value='Internal Server Error')

            # Mock session and request
            mock_session = AsyncMock()
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session.close = AsyncMock()
            mock_client_session.return_value = mock_session

            client = AzureHttpClient()

            async with client:
                await client.get(test_url)

            # Verify exponential backoff delays
            # With retry_backoff_factor=0.1: delay1=0.1*2^0=0.1, delay2=0.1*2^1=0.2
            expected_delays = [0.1, 0.2]
            actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
            assert actual_delays == expected_delays

    @pytest.mark.asyncio
    async def test_azure_convenience_methods(self):
        """Test Azure DevOps convenience methods with automatic auth and URL building."""
        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector'), \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.get_auth_headers') as mock_get_auth, \
             patch('plugins.azrepo.azure_rest_utils.build_api_url') as mock_build_url:

            # Mock connector and session
            mock_connector = AsyncMock()
            mock_session = AsyncMock()
            mock_client_session.return_value = mock_session

            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"result": "success"}')

            # Mock the context manager for session.request
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_session.request.return_value = mock_context_manager

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
        with patch('plugins.azrepo.azure_rest_utils.aiohttp.TCPConnector'), \
             patch('plugins.azrepo.azure_rest_utils.aiohttp.ClientSession') as mock_client_session, \
             patch('plugins.azrepo.azure_rest_utils.get_auth_headers') as mock_get_auth, \
             patch('plugins.azrepo.azure_rest_utils.build_api_url') as mock_build_url:

            # Mock connector and session
            mock_connector = AsyncMock()
            mock_session = AsyncMock()
            mock_client_session.return_value = mock_session

            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.text = AsyncMock(return_value='{"id": 123, "created": true}')

            # Mock the context manager for session.request
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_session.request.return_value = mock_context_manager

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
