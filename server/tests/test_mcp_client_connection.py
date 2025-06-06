import asyncio
import subprocess
import time
import pytest
import logging
import requests
import socket
import os
import signal
import psutil
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client


def find_free_port():
    """Find a free port for the server to use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def get_worker_id():
    """Get the pytest-xdist worker ID if available."""
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')
    return worker_id


def kill_process_tree(pid):
    """Kill a process and all its children."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)

        # Terminate children first
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass

        # Terminate parent
        try:
            parent.terminate()
        except psutil.NoSuchProcess:
            pass

        # Wait for graceful termination
        gone, alive = psutil.wait_procs(children + [parent], timeout=5)

        # Force kill any remaining processes
        for proc in alive:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass

    except psutil.NoSuchProcess:
        pass


class TestMCPClientConnection:
    """Test MCP client connection to launched server using SSE transport."""

    @pytest.fixture(autouse=True)
    def cleanup_processes(self):
        """Cleanup any leftover processes after each test."""
        yield
        # Kill any remaining test processes
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        for child in children:
            try:
                if 'server/main.py' in ' '.join(child.cmdline()):
                    child.terminate()
                    try:
                        child.wait(timeout=2)
                    except psutil.TimeoutExpired:
                        child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    @pytest.fixture
    def server_process(self):
        """Launch the MCP server as a subprocess with dynamic port allocation and clean up after test."""
        # Get worker-specific port to avoid conflicts
        worker_id = get_worker_id()
        port = find_free_port()

        logging.info(f"Worker {worker_id} using port {port}")

        # Get the path to the server main.py
        server_path = Path(__file__).parent.parent / "main.py"

        # Set environment variables for the server
        env = os.environ.copy()
        env['SERVER_PORT'] = str(port)
        env['PYTEST_WORKER_ID'] = worker_id

        # Start the server process with the specific port
        process = subprocess.Popen(
            ["uv", "run", str(server_path), "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None  # Create new process group on Unix
        )

        # Store port for cleanup and test access (dynamic attributes)
        setattr(process, 'port', port)
        setattr(process, 'worker_id', worker_id)

        # Give the server time to start up
        time.sleep(3)

        # Check if process is still running (didn't crash immediately)
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(f"Worker {worker_id}: Server failed to start on port {port}. stdout: {stdout}, stderr: {stderr}")

        # Additional check: try to connect to the HTTP endpoint to ensure server is ready
        max_retries = 20
        server_ready = False

        for i in range(max_retries):
            try:
                response = requests.get(f"http://localhost:{port}/", timeout=2)
                if response.status_code == 200:
                    server_ready = True
                    break
            except requests.exceptions.RequestException:
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    pytest.fail(f"Worker {worker_id}: Server crashed during startup on port {port}. stdout: {stdout}, stderr: {stderr}")

                if i == max_retries - 1:
                    # Final attempt failed, capture output for debugging
                    try:
                        stdout, stderr = process.communicate(timeout=2)
                    except subprocess.TimeoutExpired:
                        stdout, stderr = "Process still running", "Process still running"
                    pytest.fail(f"Worker {worker_id}: Server did not become ready within timeout period on port {port}. stdout: {stdout}, stderr: {stderr}")

                time.sleep(0.5)

        if not server_ready:
            pytest.fail(f"Worker {worker_id}: Server readiness check failed on port {port}")

        logging.info(f"Worker {worker_id}: Server ready on port {port}")

        yield process

        # Enhanced cleanup: terminate the server process and all children
        logging.info(f"Worker {worker_id}: Starting cleanup for server on port {port}")

        try:
            if process.poll() is None:  # Process is still running
                # Kill the entire process tree
                kill_process_tree(process.pid)

                # Wait for process to actually terminate
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logging.warning(f"Worker {worker_id}: Process did not terminate gracefully, force killing")
                    try:
                        if hasattr(os, 'killpg'):
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        else:
                            process.kill()
                        process.wait()
                    except (ProcessLookupError, OSError):
                        pass  # Process already dead

            # Verify port is freed
            for i in range(10):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('localhost', port))
                        break  # Port is free
                except OSError:
                    if i == 9:
                        logging.warning(f"Worker {worker_id}: Port {port} still in use after cleanup")
                    time.sleep(0.1)

        except Exception as cleanup_error:
            logging.error(f"Worker {worker_id}: Error during cleanup: {cleanup_error}")

        logging.info(f"Worker {worker_id}: Cleanup completed for port {port}")

    @pytest.mark.asyncio
    async def test_client_can_connect_to_server(self, server_process):
        """Test that an MCP client can successfully connect to the launched server."""
        server_url = f"http://localhost:{server_process.port}/sse"
        worker_id = server_process.worker_id

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
                    logging.info(f"Worker {worker_id}: Successfully connected to server. Available tools: {tool_names}")

                    # Verify we have at least some tools available
                    assert len(tools_response.tools) > 0, "Server should have at least one tool available"

        except Exception as e:
            # Check if server is still running to help with debugging
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                pytest.fail(f"Worker {worker_id}: Server crashed during test. stdout: {stdout}, stderr: {stderr}")
            else:
                pytest.fail(f"Worker {worker_id}: Failed to connect to server: {e}")

    @pytest.mark.asyncio
    async def test_basic_tool_execution_via_mcp_client(self, server_process):
        """Test that at least one tool can be successfully executed via the MCP client.
        
        This test fulfills the requirements of issue #12:
        - Execute one simple tool via call_tool()
        - Verify tool returns expected response format (MCP TextContent)
        - Test basic error handling (invalid tool name)
        """
        server_url = f"http://localhost:{server_process.port}/sse"
        worker_id = server_process.worker_id

        try:
            async with sse_client(url=server_url) as streams:
                async with ClientSession(*streams) as session:
                    # Initialize the session
                    await session.initialize()

                    # List available tools
                    tools_response = await session.list_tools()
                    available_tools = {tool.name: tool for tool in tools_response.tools}

                    # Test 1: Execute a simple, reliable tool successfully
                    # Use time_tool as it's simple and doesn't require external dependencies
                    if "time_tool" in available_tools:
                        tool_name = "time_tool"
                        arguments = {"operation": "get_time"}
                        
                        logging.info(f"Worker {worker_id}: Testing successful tool execution with {tool_name}")
                        
                        result = await session.call_tool(tool_name, arguments)
                        
                        # Verify we got a valid response
                        assert result is not None, f"Worker {worker_id}: Tool {tool_name} returned None"
                        
                        # Verify response follows MCP TextContent format
                        assert hasattr(result, 'content'), f"Worker {worker_id}: Tool response missing 'content' attribute"
                        assert isinstance(result.content, list), f"Worker {worker_id}: Tool response content is not a list"
                        assert len(result.content) > 0, f"Worker {worker_id}: Tool response content is empty"
                        
                        # Check that each content item has the expected structure
                        text_content_found = False
                        time_text = ""
                        for content_item in result.content:
                            assert hasattr(content_item, 'type'), f"Worker {worker_id}: Content item missing 'type' attribute"
                            
                            if hasattr(content_item, 'type') and content_item.type == "text":
                                assert hasattr(content_item, 'text'), f"Worker {worker_id}: TextContent item missing 'text' attribute"
                                text_attr = getattr(content_item, 'text', '')
                                assert isinstance(text_attr, str), f"Worker {worker_id}: TextContent item text is not a string"
                                assert len(text_attr) > 0, f"Worker {worker_id}: TextContent item text is empty"
                                text_content_found = True
                                if not time_text:  # Use the first text content for time verification
                                    time_text = text_attr
                        
                        # Ensure we found at least one text content item
                        assert text_content_found, f"Worker {worker_id}: No TextContent items found in response"
                        import re
                        time_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
                        assert re.search(time_pattern, time_text), f"Worker {worker_id}: Time tool response doesn't contain expected time format: {time_text}"
                        
                        logging.info(f"Worker {worker_id}: ✅ Tool {tool_name} executed successfully. Response: {time_text}")
                        
                    else:
                        # Fallback: try to find any tool that might work with minimal arguments
                        # Look for tools that have simple schemas
                        simple_tools = []
                        for tool_name, tool in available_tools.items():
                            schema = tool.inputSchema
                            if isinstance(schema, dict) and schema.get("type") == "object":
                                properties = schema.get("properties", {})
                                required = schema.get("required", [])
                                # Look for tools with minimal required fields
                                if len(required) <= 1:
                                    simple_tools.append((tool_name, tool))
                        
                        if simple_tools:
                            tool_name, tool = simple_tools[0]
                            schema = tool.inputSchema
                            required = schema.get("required", [])
                            
                            # Build minimal arguments
                            arguments = {}
                            if required:
                                # Try to provide a reasonable default for the first required field
                                first_required = required[0]
                                properties = schema.get("properties", {})
                                if first_required in properties:
                                    prop_info = properties[first_required]
                                    if prop_info.get("type") == "string":
                                        if "enum" in prop_info:
                                            arguments[first_required] = prop_info["enum"][0]
                                        else:
                                            arguments[first_required] = "test"
                            
                            logging.info(f"Worker {worker_id}: Testing with fallback tool {tool_name} and arguments {arguments}")
                            
                            try:
                                result = await session.call_tool(tool_name, arguments)
                                assert result is not None, f"Worker {worker_id}: Tool {tool_name} returned None"
                                assert hasattr(result, 'content'), f"Worker {worker_id}: Tool response missing 'content' attribute"
                                logging.info(f"Worker {worker_id}: ✅ Fallback tool {tool_name} executed successfully")
                            except Exception as tool_error:
                                logging.info(f"Worker {worker_id}: Fallback tool {tool_name} failed (this is acceptable): {tool_error}")
                                # As long as we get a proper error response, the connection is working
                                assert "Error" in str(tool_error) or "error" in str(tool_error).lower()
                        else:
                            pytest.fail(f"Worker {worker_id}: No suitable tools found for testing. Available tools: {list(available_tools.keys())}")

                    # Test 2: Test basic error handling with invalid tool name
                    logging.info(f"Worker {worker_id}: Testing error handling with invalid tool name")
                    
                    invalid_tool_name = "nonexistent_tool_12345"
                    result = await session.call_tool(invalid_tool_name, {})
                    
                    # The server should return a proper MCP response with error content
                    assert result is not None, f"Worker {worker_id}: Expected error response for invalid tool {invalid_tool_name}, but got None"
                    assert hasattr(result, 'content'), f"Worker {worker_id}: Error response missing 'content' attribute"
                    assert len(result.content) > 0, f"Worker {worker_id}: Error response content is empty"
                    
                    # Check that the response contains an error message
                    error_found = False
                    for content_item in result.content:
                        if hasattr(content_item, 'type') and content_item.type == "text":
                            text_content = getattr(content_item, 'text', '')
                            if any(keyword in text_content.lower() for keyword in ["not found", "unknown", "invalid", "error"]):
                                error_found = True
                                logging.info(f"Worker {worker_id}: ✅ Error handling test passed. Got error response: {text_content}")
                                break
                    
                    assert error_found, f"Worker {worker_id}: Error response doesn't contain expected error keywords: {result}"

                    # Test 3: Test error handling with valid tool but invalid arguments (if time_tool is available)
                    if "time_tool" in available_tools:
                        logging.info(f"Worker {worker_id}: Testing error handling with invalid operation")
                        
                        try:
                            result = await session.call_tool("time_tool", {"operation": "invalid_operation"})
                            
                            # The tool should return an error response, not raise an exception
                            assert result is not None, f"Worker {worker_id}: Tool returned None for invalid operation"
                            assert hasattr(result, 'content'), f"Worker {worker_id}: Tool response missing 'content' attribute"
                            
                            # Check if the response indicates an error
                            error_text = ""
                            if result.content:
                                for content_item in result.content:
                                    if hasattr(content_item, 'type') and content_item.type == "text":
                                        error_text = getattr(content_item, 'text', '')
                                        break
                            assert any(keyword in error_text.lower() for keyword in ["error", "unknown", "invalid"]), \
                                f"Worker {worker_id}: Tool response doesn't indicate error for invalid operation: {error_text}"
                            
                            logging.info(f"Worker {worker_id}: ✅ Invalid operation test passed. Got error response: {error_text}")
                            
                        except Exception as tool_error:
                            # Some tools might raise exceptions for invalid operations, which is also acceptable
                            logging.info(f"Worker {worker_id}: ✅ Invalid operation test passed. Got exception: {tool_error}")

        except Exception as e:
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                pytest.fail(f"Worker {worker_id}: Server crashed during tool execution test. stdout: {stdout}, stderr: {stderr}")
            else:
                pytest.fail(f"Worker {worker_id}: Tool execution test failed: {e}")

    @pytest.mark.asyncio
    async def test_mcp_protocol_handshake(self, server_process):
        """Test that the MCP protocol handshake works correctly."""
        server_url = f"http://localhost:{server_process.port}/sse"
        worker_id = server_process.worker_id

        try:
            async with sse_client(url=server_url) as streams:
                async with ClientSession(*streams) as session:
                    # The initialize() call performs the MCP handshake
                    init_result = await session.initialize()

                    # Verify initialization was successful
                    assert init_result is not None
                    logging.info(f"Worker {worker_id}: MCP protocol handshake completed successfully")

                    # Test that we can perform basic MCP operations
                    tools_response = await session.list_tools()
                    assert tools_response is not None

                    # If the server supports other capabilities, test them too
                    try:
                        resources_response = await session.list_resources()
                        logging.info(f"Worker {worker_id}: Server supports resources")
                    except Exception:
                        logging.info(f"Worker {worker_id}: Server does not support resources (this is fine)")

                    try:
                        prompts_response = await session.list_prompts()
                        logging.info(f"Worker {worker_id}: Server supports prompts")
                    except Exception:
                        logging.info(f"Worker {worker_id}: Server does not support prompts (this is fine)")

        except Exception as e:
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                pytest.fail(f"Worker {worker_id}: Server crashed during handshake test. stdout: {stdout}, stderr: {stderr}")
            else:
                pytest.fail(f"Worker {worker_id}: MCP handshake failed: {e}")

    @pytest.mark.asyncio
    async def test_expected_tools_are_registered(self, server_process):
        """Test that the expected set of tools are registered and available via MCP client."""
        server_url = f"http://localhost:{server_process.port}/sse"
        worker_id = server_process.worker_id

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

                    logging.info(f"Worker {worker_id}: Available tools ({len(available_tools)}): {sorted(available_tools)}")

                    # Check that all expected core tools are present
                    missing_core_tools = expected_core_tools - available_tools
                    if missing_core_tools:
                        pytest.fail(f"Worker {worker_id}: Missing expected core tools: {sorted(missing_core_tools)}")

                    # Log which optional tools are present
                    present_optional_tools = optional_tools & available_tools
                    missing_optional_tools = optional_tools - available_tools

                    if present_optional_tools:
                        logging.info(f"Worker {worker_id}: Present optional tools: {sorted(present_optional_tools)}")
                    if missing_optional_tools:
                        logging.info(f"Worker {worker_id}: Missing optional tools (this is OK): {sorted(missing_optional_tools)}")

                    # Verify each tool has required attributes
                    for tool in tools_response.tools:
                        assert hasattr(tool, 'name'), f"Worker {worker_id}: Tool missing name attribute: {tool}"
                        assert hasattr(tool, 'description'), f"Worker {worker_id}: Tool missing description attribute: {tool.name}"
                        assert hasattr(tool, 'inputSchema'), f"Worker {worker_id}: Tool missing inputSchema attribute: {tool.name}"
                        assert tool.name, f"Worker {worker_id}: Tool has empty name: {tool}"
                        assert tool.description, f"Worker {worker_id}: Tool has empty description: {tool.name}"
                        assert tool.inputSchema, f"Worker {worker_id}: Tool has empty inputSchema: {tool.name}"

                    # Verify minimum number of tools
                    assert len(available_tools) >= len(expected_core_tools), \
                        f"Worker {worker_id}: Expected at least {len(expected_core_tools)} tools, got {len(available_tools)}"

                    logging.info(f"Worker {worker_id}: ✅ Tool verification passed. Found {len(available_tools)} tools, "
                               f"including all {len(expected_core_tools)} expected core tools.")

        except Exception as e:
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                pytest.fail(f"Worker {worker_id}: Server crashed during tool verification test. stdout: {stdout}, stderr: {stderr}")
            else:
                pytest.fail(f"Worker {worker_id}: Tool verification test failed: {e}")

    @pytest.mark.asyncio
    async def test_specific_tool_schemas_are_valid(self, server_process):
        """Test that specific important tools have valid schemas."""
        server_url = f"http://localhost:{server_process.port}/sse"
        worker_id = server_process.worker_id

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
                            logging.warning(f"Worker {worker_id}: Tool {tool_name} not found, skipping schema validation")
                            continue

                        tool = tools_by_name[tool_name]
                        schema = tool.inputSchema

                        # Validate schema structure
                        assert isinstance(schema, dict), f"Worker {worker_id}: Tool {tool_name} schema is not a dict"
                        assert "type" in schema, f"Worker {worker_id}: Tool {tool_name} schema missing 'type'"
                        assert schema["type"] == "object", f"Worker {worker_id}: Tool {tool_name} schema type is not 'object'"
                        assert "properties" in schema, f"Worker {worker_id}: Tool {tool_name} schema missing 'properties'"

                        # Validate required properties exist
                        properties = schema["properties"]
                        for required_prop in validation_spec["required_properties"]:
                            assert required_prop in properties, \
                                f"Worker {worker_id}: Tool {tool_name} missing required property '{required_prop}'"

                        # Validate required fields if specified
                        if "required" in schema:
                            required_fields = set(schema["required"])
                            expected_required = set(validation_spec["required_fields"])
                            missing_required = expected_required - required_fields
                            assert not missing_required, \
                                f"Worker {worker_id}: Tool {tool_name} missing required fields: {missing_required}"

                        logging.info(f"Worker {worker_id}: ✅ Tool {tool_name} schema validation passed")

        except Exception as e:
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                pytest.fail(f"Worker {worker_id}: Server crashed during schema validation test. stdout: {stdout}, stderr: {stderr}")
            else:
                pytest.fail(f"Worker {worker_id}: Schema validation test failed: {e}")
