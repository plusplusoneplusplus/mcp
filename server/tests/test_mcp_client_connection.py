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

    @pytest.mark.asyncio
    async def test_expected_tools_are_registered(self, server_process):
        """Test that the expected set of tools are registered and available via MCP client."""
        server_url = "http://localhost:8000/sse"

        # Define expected tools based on current server configuration
        # These are the tools that should always be available
        expected_core_tools = {
            # Built-in image tool
            "get_session_image",

            # YAML-defined tools (from server/tools.yaml with enabled: true)
            "execute_task",
            "query_task_status",
            "list_tasks",
            "list_instructions",
            "get_instruction",
            "query_script_status",
            "deploy",

            # Code-based tools from mcp_tools (commonly available)
            "command_executor",
            "browser_client",
            "time_tool",
            "knowledge_indexer",
            "knowledge_query",
            "knowledge_collections",
            "git",
            "git_commit",
        }

        # Optional tools that may or may not be present depending on configuration
        optional_tools = {
            "capture_panels_client",
            "kusto_client",
            "web_summarizer",
            "url_summarizer",
            "azure_repo_client",
            "azure_pull_request",
            "azure_work_item",
        }

        try:
            async with sse_client(url=server_url) as streams:
                async with ClientSession(*streams) as session:
                    # Initialize the session
                    await session.initialize()

                    # Get the list of available tools
                    tools_response = await session.list_tools()

                    # Extract tool names from response
                    available_tools = {tool.name for tool in tools_response.tools}

                    logging.info(f"Available tools ({len(available_tools)}): {sorted(available_tools)}")

                    # Check that all expected core tools are present
                    missing_core_tools = expected_core_tools - available_tools
                    if missing_core_tools:
                        pytest.fail(f"Missing expected core tools: {sorted(missing_core_tools)}")

                    # Log which optional tools are present
                    present_optional_tools = optional_tools & available_tools
                    missing_optional_tools = optional_tools - available_tools

                    if present_optional_tools:
                        logging.info(f"Present optional tools: {sorted(present_optional_tools)}")
                    if missing_optional_tools:
                        logging.info(f"Missing optional tools (this is OK): {sorted(missing_optional_tools)}")

                    # Verify each tool has required attributes
                    for tool in tools_response.tools:
                        assert hasattr(tool, 'name'), f"Tool missing name attribute: {tool}"
                        assert hasattr(tool, 'description'), f"Tool missing description attribute: {tool.name}"
                        assert hasattr(tool, 'inputSchema'), f"Tool missing inputSchema attribute: {tool.name}"
                        assert tool.name, f"Tool has empty name: {tool}"
                        assert tool.description, f"Tool has empty description: {tool.name}"
                        assert tool.inputSchema, f"Tool has empty inputSchema: {tool.name}"

                    # Verify minimum number of tools
                    assert len(available_tools) >= len(expected_core_tools), \
                        f"Expected at least {len(expected_core_tools)} tools, got {len(available_tools)}"

                    logging.info(f"✅ Tool verification passed. Found {len(available_tools)} tools, "
                               f"including all {len(expected_core_tools)} expected core tools.")

        except Exception as e:
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                pytest.fail(f"Server crashed during tool verification test. stdout: {stdout}, stderr: {stderr}")
            else:
                pytest.fail(f"Tool verification test failed: {e}")

    @pytest.mark.asyncio
    async def test_specific_tool_schemas_are_valid(self, server_process):
        """Test that specific important tools have valid schemas."""
        server_url = "http://localhost:8000/sse"

        # Tools to specifically validate schemas for
        tools_to_validate = {
            "get_session_image": {
                "required_properties": ["session_id", "image_name"],
                "required_fields": ["session_id", "image_name"]
            },
            "execute_task": {
                "required_properties": ["task_name"],
                "required_fields": ["task_name"]
            },
            "command_executor": {
                "required_properties": ["command"],
                "required_fields": ["command"]
            },
            "git": {
                "required_properties": ["operation", "repo_path"],
                "required_fields": ["operation", "repo_path"]
            }
        }

        try:
            async with sse_client(url=server_url) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    tools_response = await session.list_tools()

                    # Create a mapping of tool names to tools
                    tools_by_name = {tool.name: tool for tool in tools_response.tools}

                    for tool_name, validation_spec in tools_to_validate.items():
                        if tool_name not in tools_by_name:
                            logging.warning(f"Tool {tool_name} not found, skipping schema validation")
                            continue

                        tool = tools_by_name[tool_name]
                        schema = tool.inputSchema

                        # Validate schema structure
                        assert isinstance(schema, dict), f"Tool {tool_name} schema is not a dict"
                        assert "type" in schema, f"Tool {tool_name} schema missing 'type'"
                        assert schema["type"] == "object", f"Tool {tool_name} schema type is not 'object'"
                        assert "properties" in schema, f"Tool {tool_name} schema missing 'properties'"

                        # Validate required properties exist
                        properties = schema["properties"]
                        for required_prop in validation_spec["required_properties"]:
                            assert required_prop in properties, \
                                f"Tool {tool_name} missing required property '{required_prop}'"

                        # Validate required fields if specified
                        if "required" in schema:
                            required_fields = set(schema["required"])
                            expected_required = set(validation_spec["required_fields"])
                            missing_required = expected_required - required_fields
                            assert not missing_required, \
                                f"Tool {tool_name} missing required fields: {missing_required}"

                        logging.info(f"✅ Tool {tool_name} schema validation passed")

        except Exception as e:
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                pytest.fail(f"Server crashed during schema validation test. stdout: {stdout}, stderr: {stderr}")
            else:
                pytest.fail(f"Schema validation test failed: {e}")
