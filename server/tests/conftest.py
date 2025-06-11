"""
Pytest fixtures for MCP server testing.

This module provides reusable fixtures for:
- Server process lifecycle management
- MCP client session setup
- Port allocation for parallel testing
- Proper cleanup and timeout handling

## MCP Client Testing Patterns

### Pattern 1: Using create_mcp_client context manager (Recommended)
This is the most flexible and reliable pattern for MCP client testing:

```python
@pytest.mark.asyncio
async def test_something(self, mcp_client_info):
    from .conftest import create_mcp_client

    server_url = mcp_client_info['url']
    worker_id = mcp_client_info['worker_id']

    async with create_mcp_client(server_url, worker_id) as session:
        # Use the session for testing
        tools_response = await session.list_tools()
        assert tools_response is not None
```

### Pattern 2: Using mcp_client_info fixture
For tests that need connection information but want to manage the client lifecycle themselves:

```python
@pytest.mark.asyncio
async def test_something(self, mcp_client_info):
    server_url = mcp_client_info['url']
    worker_id = mcp_client_info['worker_id']
    port = mcp_client_info['port']

    # Custom client setup logic here
```

### Available Fixtures:
- `mcp_server`: Running MCP server process
- `mcp_client_info`: Connection information (url, worker_id, port)
- `server_url`: HTTP server URL
- `sse_url`: SSE endpoint URL
- `server_port`: Allocated port number
- `server_process_info`: Process information

### Note on mcp_client fixture:
The `mcp_client` fixture mentioned in some error messages is intentionally not provided
due to async context manager lifecycle issues with pytest-asyncio. Use the patterns above instead.
"""

import asyncio
import subprocess
import time
import pytest
import pytest_asyncio
import logging
import requests
import socket
import os
import signal
import psutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Generator, AsyncGenerator, Optional

from mcp import ClientSession
from mcp.client.sse import sse_client


# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def pytest_configure(config):
    """Add custom markers for tests"""
    config.addinivalue_line("markers", "asyncio: mark test as an asyncio test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "server: mark test as requiring server")

    # Set asyncio mode to auto to avoid warnings
    config.option.asyncio_mode = "auto"


# Utility functions
def find_free_port() -> int:
    """Find a free port for the server to use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def get_worker_id() -> str:
    """Get the pytest-xdist worker ID if available."""
    return os.environ.get('PYTEST_XDIST_WORKER', 'master')


def kill_process_tree(pid: int) -> None:
    """Kill a process and all its children with Windows-specific handling."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)

        logger.debug(f"Killing process tree for PID {pid}, found {len(children)} children")

        # Terminate children first
        for child in children:
            try:
                logger.debug(f"Terminating child process {child.pid}")
                child.terminate()
            except psutil.NoSuchProcess:
                logger.debug(f"Child process {child.pid} already gone")
                pass
            except Exception as e:
                logger.debug(f"Error terminating child process {child.pid}: {e}")

        # Terminate parent
        try:
            logger.debug(f"Terminating parent process {pid}")
            parent.terminate()
        except psutil.NoSuchProcess:
            logger.debug(f"Parent process {pid} already gone")
            pass
        except Exception as e:
            logger.debug(f"Error terminating parent process {pid}: {e}")

        # Wait for graceful termination with platform-specific timeout
        timeout = 10 if os.name == 'nt' else 5  # Longer timeout on Windows
        gone, alive = psutil.wait_procs(children + [parent], timeout=timeout)

        logger.debug(f"Graceful termination: {len(gone)} processes terminated, {len(alive)} still alive")

        # Force kill any remaining processes
        for proc in alive:
            try:
                logger.debug(f"Force killing process {proc.pid}")
                proc.kill()
            except psutil.NoSuchProcess:
                logger.debug(f"Process {proc.pid} already gone during force kill")
                pass
            except Exception as e:
                logger.debug(f"Error force killing process {proc.pid}: {e}")

    except psutil.NoSuchProcess:
        logger.debug(f"Process {pid} not found during kill_process_tree")
        pass
    except Exception as e:
        logger.error(f"Unexpected error in kill_process_tree for PID {pid}: {e}")


def wait_for_server_ready(port: int, timeout: int = 30) -> bool:
    """Wait for server to be ready by checking HTTP endpoint."""
    start_time = time.time()
    logger.debug(f"Waiting for server on port {port} to be ready (timeout: {timeout}s)")

    while time.time() - start_time < timeout:
        elapsed = time.time() - start_time
        try:
            logger.debug(f"Attempting to connect to http://localhost:{port}/ (elapsed: {elapsed:.1f}s)")
            response = requests.get(f"http://localhost:{port}/", timeout=2)
            logger.debug(f"Got response with status code: {response.status_code}")
            if response.status_code == 200:
                logger.debug(f"Server ready on port {port} after {elapsed:.1f}s")
                return True
        except requests.exceptions.RequestException as e:
            logger.debug(f"Connection attempt failed: {e}")
        time.sleep(0.5)

    logger.error(f"Server on port {port} did not become ready within {timeout}s")
    return False


# Fixtures
@pytest.fixture(autouse=True)
def cleanup_processes():
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
def server_port() -> int:
    """Allocate a free port for server testing."""
    return find_free_port()


@pytest.fixture
def mcp_server(server_port: int) -> Generator[subprocess.Popen, None, None]:
    """
    Launch and manage MCP server process.

    This fixture:
    - Starts the server on a free port
    - Waits for server to be ready
    - Provides the process object with port attribute
    - Ensures proper cleanup on test completion
    """
    worker_id = get_worker_id()

    logger.debug(f"Worker {worker_id} starting server on port {server_port}")

    # Get the path to the server main.py
    server_path = Path(__file__).parent.parent / "main.py"
    logger.debug(f"Server path: {server_path}")

    # Set environment variables for the server
    env = os.environ.copy()
    env['SERVER_PORT'] = str(server_port)
    env['PYTEST_WORKER_ID'] = worker_id

    # Set required environment variables for tests
    env['GIT_ROOT'] = str(Path(__file__).parent.parent.parent)
    env['PROJECT_NAME'] = 'mcp_test'
    env['PRIVATE_TOOL_ROOT'] = str(Path(__file__).parent.parent.parent)
    env['MCP_YAML_TOOL_PATHS'] = str(Path(__file__).parent.parent)
    env['TOOL_HISTORY_ENABLED'] = 'true'
    env['TOOL_HISTORY_PATH'] = '.history'
    env['IMAGE_DIR'] = '.images'
    env['VECTOR_STORE_PATH'] = '.vector_store'
    env['BROWSER_TYPE'] = 'chrome'
    env['CLIENT_TYPE'] = 'playwright'
    env['BROWSER_PROFILE_PATH'] = '.browserprofile'
    env['PERIODIC_STATUS_ENABLED'] = 'false'
    env['PERIODIC_STATUS_INTERVAL'] = '30.0'
    env['PERIODIC_STATUS_MAX_COMMAND_LENGTH'] = '60'
    env['COMMAND_EXECUTOR_MAX_COMPLETED_PROCESSES'] = '100'
    env['COMMAND_EXECUTOR_COMPLETED_PROCESS_TTL'] = '3600'
    env['COMMAND_EXECUTOR_AUTO_CLEANUP_ENABLED'] = 'true'
    env['COMMAND_EXECUTOR_CLEANUP_INTERVAL'] = '300'

    logger.debug(f"Environment variables: SERVER_PORT={server_port}, PYTEST_WORKER_ID={worker_id}")

    # Start the server process
    cmd = ["uv", "run", str(server_path), "--port", str(server_port)]
    logger.debug(f"Starting server with command: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        preexec_fn=os.setsid if hasattr(os, 'setsid') else None
    )

    logger.debug(f"Server process started with PID: {process.pid}")

    # Store port and worker_id as attributes
    setattr(process, 'port', server_port)
    setattr(process, 'worker_id', worker_id)

    # Give the server time to start up
    logger.debug("Waiting 3 seconds for server to start up...")
    time.sleep(3)

    # Check if process is still running
    poll_result = process.poll()
    logger.debug(f"Process poll result after 3s: {poll_result}")
    if poll_result is not None:
        stdout, stderr = process.communicate()
        logger.error(f"Server process exited with code {poll_result}")
        logger.error(f"stdout: {stdout}")
        logger.error(f"stderr: {stderr}")
        pytest.fail(
            f"Worker {worker_id}: Server failed to start on port {server_port}. "
            f"stdout: {stdout}, stderr: {stderr}"
        )

    logger.debug("Server process is still running, checking readiness...")
    # Wait for server to be ready
    if not wait_for_server_ready(server_port, timeout=30):
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            stdout, stderr = "Process still running", "Process still running"
        logger.error(f"Server readiness check failed")
        logger.error(f"stdout: {stdout}")
        logger.error(f"stderr: {stderr}")
        pytest.fail(
            f"Worker {worker_id}: Server did not become ready within timeout on port {server_port}. "
            f"stdout: {stdout}, stderr: {stderr}"
        )

    logging.info(f"Worker {worker_id}: Server ready on port {server_port}")

    yield process

    # Cleanup
    logging.info(f"Worker {worker_id}: Starting cleanup for server on port {server_port}")

    try:
        if process.poll() is None:
            kill_process_tree(process.pid)

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
                    pass

        # Verify port is freed
        for i in range(10):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', server_port))
                    break
            except OSError:
                if i == 9:
                    logging.warning(f"Worker {worker_id}: Port {server_port} still in use after cleanup")
                time.sleep(0.1)

    except Exception as cleanup_error:
        logging.error(f"Worker {worker_id}: Error during cleanup: {cleanup_error}")

    logging.info(f"Worker {worker_id}: Cleanup completed for port {server_port}")


@asynccontextmanager
async def create_mcp_client(server_url: str, worker_id: str = "test"):
    """
    Helper function to create and initialize an MCP client session.

    This is an async context manager that can be used in tests to create client sessions.
    Enhanced with better error handling and Windows-specific debugging.
    """
    logging.info(f"Worker {worker_id}: Connecting MCP client to {server_url}")
    logging.debug(f"Worker {worker_id}: Platform: {os.name}, Python: {os.sys.version}")

    session = None
    try:
        # Create SSE client and session with enhanced error handling
        async with sse_client(server_url) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session with timeout handling
                logging.debug(f"Worker {worker_id}: Initializing MCP session...")
                await session.initialize()

                logging.info(f"Worker {worker_id}: MCP client session initialized successfully")
                logging.debug(f"Worker {worker_id}: Session capabilities: {getattr(session, 'server_capabilities', 'Unknown')}")

                yield session
    except Exception as e:
        # Enhanced error logging for debugging Windows-specific issues
        logging.error(f"Worker {worker_id}: Error in MCP client session: {type(e).__name__}: {e}")
        logging.debug(f"Worker {worker_id}: Exception details: {repr(e)}")
        logging.debug(f"Worker {worker_id}: Server URL: {server_url}")
        
        # Log additional context for debugging
        import traceback
        logging.debug(f"Worker {worker_id}: Full traceback:\n{traceback.format_exc()}")
        
        raise
    finally:
        logging.info(f"Worker {worker_id}: MCP client session cleanup completed")



@pytest.fixture
def mcp_client_info(mcp_server: subprocess.Popen):
    """
    Provide connection information for MCP client.

    This fixture provides the server URL and worker ID for creating MCP clients.
    """
    server_port = getattr(mcp_server, 'port')
    worker_id = getattr(mcp_server, 'worker_id')
    server_url = f"http://localhost:{server_port}/sse"

    return {
        'url': server_url,
        'worker_id': worker_id,
        'port': server_port
    }


@pytest.fixture
def server_url(mcp_server: subprocess.Popen) -> str:
    """Get the server URL for the running server."""
    server_port = getattr(mcp_server, 'port')
    return f"http://localhost:{server_port}"


@pytest.fixture
def sse_url(mcp_server: subprocess.Popen) -> str:
    """Get the SSE endpoint URL for the running server."""
    server_port = getattr(mcp_server, 'port')
    return f"http://localhost:{server_port}/sse"


# Utility fixtures for specific test scenarios


@pytest.fixture
def server_process_info(mcp_server: subprocess.Popen) -> dict:
    """Get information about the running server process."""
    server_port = getattr(mcp_server, 'port')
    worker_id = getattr(mcp_server, 'worker_id')
    return {
        'pid': mcp_server.pid,
        'port': server_port,
        'worker_id': worker_id,
        'is_running': mcp_server.poll() is None
    }
