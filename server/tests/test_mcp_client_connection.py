"""Tests for MCP client connection to launched server using SSE transport."""

import pytest
import logging
from mcp.types import TextContent, CallToolResult
from mcp import ClientSession
from mcp.client.sse import sse_client


class TestMCPClientConnection:
    """Test MCP client connection to launched server using SSE transport."""

    @pytest.mark.asyncio
    async def test_client_can_connect_to_server(self, mcp_client_info):
        """Test that an MCP client can successfully connect to the launched server."""
        from .conftest import create_mcp_client

        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        # Use the helper function to create a client session
        async with create_mcp_client(server_url, worker_id) as session:
            # If we get here without exceptions, the connection was successful
            assert session is not None
            logging.info("MCP client successfully connected and initialized")

    @pytest.mark.asyncio
    async def test_basic_tool_execution_via_mcp_client(self, mcp_client_info):
        """Test executing a basic tool via the MCP client."""
        from .conftest import create_mcp_client

        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            # List available tools first
            tools_response = await session.list_tools()
            available_tools = [tool.name for tool in tools_response.tools]

            logging.info(f"Available tools: {available_tools}")
            assert len(available_tools) > 0, "Server should have at least one tool available"

            # Find a simple tool to test (prefer time_tool or similar simple tools)
            test_tool = None
            preferred_tools = ["time_tool", "command_executor", "git"]

            for preferred in preferred_tools:
                if preferred in available_tools:
                    test_tool = preferred
                    break

            if test_tool is None:
                test_tool = available_tools[0]  # Use the first available tool

            logging.info(f"Testing tool: {test_tool}")

            # Execute the tool
            if test_tool == "time_tool":
                result = await session.call_tool(test_tool, {"operation": "get_time"})
            elif test_tool == "command_executor":
                result = await session.call_tool(test_tool, {"command": "echo test"})
            elif test_tool == "git":
                result = await session.call_tool(test_tool, {"operation": "status", "repo_path": "."})
            else:
                # For unknown tools, try with empty arguments first
                try:
                    result = await session.call_tool(test_tool, {})
                except Exception:
                    # If that fails, skip this test
                    pytest.skip(f"Could not determine how to call tool '{test_tool}'")

            # Verify the result
            assert isinstance(result, CallToolResult)
            assert len(result.content) > 0

            # Check that we got text content
            text_content = [c for c in result.content if isinstance(c, TextContent)]
            assert len(text_content) > 0, "Tool should return at least one TextContent item"

            logging.info(f"Tool '{test_tool}' executed successfully")

    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(self, mcp_client_info):
        """Test error handling when calling a non-existent tool."""
        from .conftest import create_mcp_client

        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            # Try to call a non-existent tool
            # The MCP protocol may handle this differently than expected
            try:
                result = await session.call_tool("non_existent_tool", {})
                # If no exception is raised, check if the result indicates an error
                if hasattr(result, 'isError') and result.isError:
                    logging.info("Non-existent tool call returned error result as expected")
                elif hasattr(result, 'content'):
                    # Check if the content indicates an error
                    error_indicators = ['error', 'not found', 'unknown', 'invalid']
                    content_text = str(result.content).lower()
                    if any(indicator in content_text for indicator in error_indicators):
                        logging.info("Non-existent tool call returned error content as expected")
                    else:
                        pytest.fail(f"Expected error for non-existent tool, but got: {result.content}")
                else:
                    pytest.fail(f"Expected error for non-existent tool, but got successful result: {result}")
            except Exception as e:
                # If an exception is raised, that's also acceptable
                logging.info(f"Non-existent tool call raised exception as expected: {type(e).__name__}: {e}")
                assert True  # Test passes if exception is raised

    @pytest.mark.asyncio
    async def test_mcp_protocol_handshake(self, mcp_client_info):
        """Test that the MCP protocol handshake was completed successfully."""
        from .conftest import create_mcp_client

        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            # The create_mcp_client helper already performs the handshake via initialize()
            # If we get here, the handshake was successful

            # We can verify by listing tools (which requires a successful handshake)
            tools_response = await session.list_tools()
            assert tools_response is not None
            assert hasattr(tools_response, 'tools')

            logging.info("MCP protocol handshake completed successfully")

    @pytest.mark.asyncio
    async def test_expected_tools_are_registered(self, mcp_client_info):
        """Test that expected tools are registered and available via MCP client."""
        from .conftest import create_mcp_client

        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            # Get list of available tools
            tools_response = await session.list_tools()
            available_tools = {tool.name: tool for tool in tools_response.tools}

            logging.info(f"Available tools: {list(available_tools.keys())}")

            # Define expected tools (these should be available in the default configuration)
            expected_tools = [
                "time_tool",
                "command_executor",
                "git"
            ]

            # Check that at least some expected tools are available
            found_tools = []
            for tool_name in expected_tools:
                if tool_name in available_tools:
                    found_tools.append(tool_name)

                    # Verify tool has required properties
                    tool = available_tools[tool_name]
                    assert hasattr(tool, 'name')
                    assert hasattr(tool, 'description')
                    assert tool.name == tool_name
                    assert tool.description and len(tool.description) > 0

            # We should find at least one expected tool
            assert len(found_tools) > 0, f"Should find at least one expected tool. Available: {list(available_tools.keys())}"

            logging.info(f"Found expected tools: {found_tools}")

    @pytest.mark.asyncio
    async def test_specific_tool_schemas_are_valid(self, mcp_client_info):
        """Test that specific tools have valid schemas."""
        from .conftest import create_mcp_client

        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            # Get list of available tools
            tools_response = await session.list_tools()
            available_tools = {tool.name: tool for tool in tools_response.tools}

            # Test schema validation for known tools
            test_cases = [
                {
                    "name": "time_tool",
                    "required_properties": ["operation"],
                    "expected_type": "object"
                },
                {
                    "name": "command_executor",
                    "required_properties": ["command"],
                    "expected_type": "object"
                }
            ]

            validated_tools = []
            for test_case in test_cases:
                tool_name = test_case["name"]
                if tool_name in available_tools:
                    tool = available_tools[tool_name]

                    # Check if tool has input schema
                    if hasattr(tool, 'inputSchema') and tool.inputSchema:
                        schema = tool.inputSchema

                        # Verify schema structure
                        assert schema.get("type") == test_case["expected_type"]

                        # Check for required properties
                        if "properties" in schema:
                            properties = schema["properties"]
                            for required_prop in test_case["required_properties"]:
                                assert required_prop in properties, f"Tool '{tool_name}' missing required property '{required_prop}'"

                        validated_tools.append(tool_name)
                        logging.info(f"Tool '{tool_name}' has valid schema")

            # We should validate at least one tool schema
            if len(validated_tools) == 0:
                pytest.skip("No tools with schemas found to validate")

            logging.info(f"Validated schemas for tools: {validated_tools}")

    @pytest.mark.asyncio
    async def test_server_info_and_capabilities(self, mcp_client_info):
        """Test that server provides proper info and capabilities."""
        from .conftest import create_mcp_client

        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            # The session should have server info after initialization
            # This is typically available through the session object

            # We can test this by ensuring tools are available (which indicates proper capabilities)
            tools_response = await session.list_tools()
            assert tools_response is not None
            assert len(tools_response.tools) > 0

            logging.info("Server capabilities verified through tool availability")

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, mcp_client_info):
        """Test that multiple tool calls can be made concurrently."""
        from .conftest import create_mcp_client
        import asyncio

        server_url = mcp_client_info['url']
        worker_id = mcp_client_info['worker_id']

        async with create_mcp_client(server_url, worker_id) as session:
            # Get available tools
            tools_response = await session.list_tools()
            available_tools = [tool.name for tool in tools_response.tools]

            if "time_tool" not in available_tools:
                pytest.skip("time_tool not available for concurrent testing")

            # Make multiple concurrent calls
            async def call_time_tool():
                return await session.call_tool("time_tool", {"operation": "get_time"})

            # Execute 3 concurrent calls
            tasks = [call_time_tool() for _ in range(3)]
            results = await asyncio.gather(*tasks)

            # Verify all calls succeeded
            assert len(results) == 3
            for result in results:
                assert isinstance(result, CallToolResult)
                assert len(result.content) > 0

            logging.info("Concurrent tool calls completed successfully")
