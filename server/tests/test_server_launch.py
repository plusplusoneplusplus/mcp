"""Tests for server launch functionality."""

import pytest
import requests
import logging


class TestServerLaunch:
    """Test cases for server launch functionality."""

    def test_server_launches_successfully(self, mcp_server):
        """Test that the server starts successfully and is accessible."""
        # The mcp_server fixture already launches the server and verifies it's ready
        # If we get here without exceptions, the server launched successfully
        assert mcp_server is not None
        assert mcp_server.poll() is None, "Server process should still be running"

        server_port = getattr(mcp_server, 'port')
        worker_id = getattr(mcp_server, 'worker_id')

        logging.info(f"Worker {worker_id}: Server launched successfully on port {server_port}")

    def test_server_responds_to_http_requests(self, server_url):
        """Test that the server responds to HTTP requests."""
        # Test the root endpoint
        response = requests.get(server_url, timeout=5)
        assert response.status_code == 200

        logging.info(f"Server responds to HTTP requests at {server_url}")

    def test_server_sse_endpoint_accessible(self, sse_url):
        """Test that the SSE endpoint is accessible."""
        # We don't need to establish a full SSE connection here,
        # just verify the endpoint is reachable
        response = requests.get(sse_url, timeout=5, stream=True)
        # SSE endpoints typically return 200 and keep the connection open
        assert response.status_code == 200

        logging.info(f"SSE endpoint accessible at {sse_url}")

    def test_server_process_info(self, server_process_info):
        """Test that we can get information about the running server process."""
        assert server_process_info['pid'] > 0
        assert server_process_info['port'] > 0
        assert server_process_info['worker_id'] is not None
        assert server_process_info['is_running'] is True

        logging.info(f"Server process info: {server_process_info}")

    @pytest.mark.asyncio
    async def test_server_supports_mcp_protocol(self, mcp_client):
        """Test that the server properly supports the MCP protocol."""
        # The mcp_client fixture already establishes an MCP connection
        # If we get here, the server supports MCP protocol

        # Verify we can perform basic MCP operations
        tools_response = await mcp_client.list_tools()
        assert tools_response is not None
        assert hasattr(tools_response, 'tools')
        assert isinstance(tools_response.tools, list)

        logging.info("Server properly supports MCP protocol")

    def test_server_startup_time_reasonable(self, mcp_server):
        """Test that server startup time was reasonable."""
        # The mcp_server fixture includes startup time verification
        # If we get here, the server started within the timeout period

        server_port = getattr(mcp_server, 'port')
        worker_id = getattr(mcp_server, 'worker_id')

        logging.info(f"Worker {worker_id}: Server startup time was reasonable on port {server_port}")

    def test_multiple_http_requests(self, server_url):
        """Test that the server can handle multiple HTTP requests."""
        # Make several requests to ensure the server is stable
        for i in range(5):
            response = requests.get(server_url, timeout=5)
            assert response.status_code == 200

        logging.info("Server handled multiple HTTP requests successfully")

    @pytest.mark.asyncio
    async def test_server_handles_concurrent_mcp_operations(self, mcp_client):
        """Test that the server can handle concurrent MCP operations."""
        import asyncio

        # Make multiple concurrent list_tools calls
        async def list_tools():
            return await mcp_client.list_tools()

        # Execute 3 concurrent operations
        tasks = [list_tools() for _ in range(3)]
        results = await asyncio.gather(*tasks)

        # Verify all operations succeeded
        assert len(results) == 3
        for result in results:
            assert result is not None
            assert hasattr(result, 'tools')

        logging.info("Server handled concurrent MCP operations successfully")
