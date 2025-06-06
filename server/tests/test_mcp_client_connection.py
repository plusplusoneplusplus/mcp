import asyncio
import subprocess
import time
import pytest
import logging
import requests
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client


class TestMCPClientConnection:
    """Test MCP client connection to launched server using SSE transport."""

    @pytest.fixture
    def server_process(self):
        """Launch the MCP server as a subprocess and clean up after test."""
        # Get the path to the server main.py
        server_path = Path(__file__).parent.parent / "main.py"

        # Start the server process
        process = subprocess.Popen(
            ["uv", "run", str(server_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Give the server more time to start up
        time.sleep(5)

        # Check if process is still running (didn't crash immediately)
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(f"Server failed to start. stdout: {stdout}, stderr: {stderr}")

        # Additional check: try to connect to the HTTP endpoint to ensure server is ready
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:8000/", timeout=2)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                if i == max_retries - 1:
                    pytest.fail("Server did not become ready within timeout period")
                time.sleep(1)

        yield process

        # Cleanup: terminate the server process
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    @pytest.mark.asyncio
    async def test_client_can_connect_to_server(self, server_process):
        """Test that an MCP client can successfully connect to the launched server."""
        server_url = "http://localhost:8000/sse"

        try:
            # Connect to the server using SSE transport
            async with sse_client(url=server_url) as streams:
                async with ClientSession(*streams) as session:
                    # Initialize the MCP session
                    await session.initialize()

                    # Verify we can list tools (basic handshake verification)
                    tools_response = await session.list_tools()

                    # Assert that we got a valid response
                    assert tools_response is not None
                    assert hasattr(tools_response, 'tools')
                    assert isinstance(tools_response.tools, list)

                    # Log the available tools for debugging
                    tool_names = [tool.name for tool in tools_response.tools]
                    logging.info(f"Successfully connected to server. Available tools: {tool_names}")

                    # Verify we have at least some tools available
                    assert len(tools_response.tools) > 0, "Server should have at least one tool available"

        except Exception as e:
            # Check if server is still running to help with debugging
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                pytest.fail(f"Server crashed during test. stdout: {stdout}, stderr: {stderr}")
            else:
                pytest.fail(f"Failed to connect to server: {e}")

    @pytest.mark.asyncio
    async def test_client_can_call_tool(self, server_process):
        """Test that an MCP client can successfully call a tool on the server."""
        server_url = "http://localhost:8000/sse"

        try:
            async with sse_client(url=server_url) as streams:
                async with ClientSession(*streams) as session:
                    # Initialize the session
                    await session.initialize()

                    # List available tools
                    tools_response = await session.list_tools()

                    if len(tools_response.tools) > 0:
                        # Try to call the first available tool
                        first_tool = tools_response.tools[0]
                        tool_name = first_tool.name

                        logging.info(f"Attempting to call tool: {tool_name}")

                        # For this test, we'll try to call with empty arguments
                        # In a real scenario, you'd provide proper arguments based on the tool's schema
                        try:
                            result = await session.call_tool(tool_name, {})

                            # Verify we got some kind of response
                            assert result is not None
                            logging.info(f"Tool call successful. Result type: {type(result)}")

                        except Exception as tool_error:
                            # It's okay if the tool call fails due to missing arguments
                            # The important thing is that we can communicate with the server
                            logging.info(f"Tool call failed (expected for empty args): {tool_error}")
                            # As long as we get a proper error response, the connection is working
                            assert "Error" in str(tool_error) or "error" in str(tool_error).lower()

        except Exception as e:
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                pytest.fail(f"Server crashed during test. stdout: {stdout}, stderr: {stderr}")
            else:
                pytest.fail(f"Failed during tool call test: {e}")

    @pytest.mark.asyncio
    async def test_mcp_protocol_handshake(self, server_process):
        """Test that the MCP protocol handshake works correctly."""
        server_url = "http://localhost:8000/sse"

        try:
            async with sse_client(url=server_url) as streams:
                async with ClientSession(*streams) as session:
                    # The initialize() call performs the MCP handshake
                    init_result = await session.initialize()

                    # Verify initialization was successful
                    assert init_result is not None
                    logging.info("MCP protocol handshake completed successfully")

                    # Test that we can perform basic MCP operations
                    tools_response = await session.list_tools()
                    assert tools_response is not None

                    # If the server supports other capabilities, test them too
                    try:
                        resources_response = await session.list_resources()
                        logging.info("Server supports resources")
                    except Exception:
                        logging.info("Server does not support resources (this is fine)")

                    try:
                        prompts_response = await session.list_prompts()
                        logging.info("Server supports prompts")
                    except Exception:
                        logging.info("Server does not support prompts (this is fine)")

        except Exception as e:
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                pytest.fail(f"Server crashed during handshake test. stdout: {stdout}, stderr: {stderr}")
            else:
                pytest.fail(f"MCP handshake failed: {e}")
