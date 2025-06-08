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
import platform

from mcp import ClientSession
from mcp.client.sse import sse_client


# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]


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


def get_platform_timeout() -> int:
    """Get platform-appropriate timeout for server startup.

    Windows environments typically need more time for server startup due to:
    - Slower process initialization
    - Different process management overhead
    - CI environment performance characteristics

    This addresses issue #109 where Windows CI tests were failing due to
    insufficient startup timeout (30s -> 60s for Windows).

    Returns:
        int: Timeout in seconds (60 for Windows, 30 for other platforms)
    """
    system = platform.system().lower()
    if system == "windows":
        return 60  # Longer timeout for Windows
    return 30  # Default timeout for Unix-like systems


def wait_for_server_ready(port: int, timeout: Optional[int] = None) -> bool:
    """Wait for server to be ready by checking HTTP endpoint.

    Args:
        port: Port number to check
        timeout: Timeout in seconds (uses platform-specific default if None)
    """
    if timeout is None:
        timeout = get_platform_timeout()

    start_time = time.time()
    last_error = None
    attempt_count = 0

    logging.info(f"Waiting for server on port {port} (timeout: {timeout}s, platform: {platform.system()})")

    while time.time() - start_time < timeout:
        attempt_count += 1
        try:
            response = requests.get(f"http://localhost:{port}/", timeout=2)
            if response.status_code == 200:
                elapsed = time.time() - start_time
                logging.info(f"Server ready on port {port} after {elapsed:.2f}s ({attempt_count} attempts)")
                return True
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            # Log every 10th attempt to avoid spam but provide progress indication
            if attempt_count % 10 == 0:
                elapsed = time.time() - start_time
                logging.debug(f"Server not ready on port {port} after {elapsed:.2f}s (attempt {attempt_count}): {last_error}")

        time.sleep(0.5)

    elapsed = time.time() - start_time
    logging.error(f"Server failed to become ready on port {port} after {elapsed:.2f}s ({attempt_count} attempts). Last error: {last_error}")
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

    logging.info(f"Worker {worker_id} starting server on port {server_port}")

    # Get the path to the server main.py
    server_path = Path(__file__).parent.parent / "main.py"

    # Set environment variables for the server
    env = os.environ.copy()
    env['SERVER_PORT'] = str(server_port)
    env['PYTEST_WORKER_ID'] = worker_id

    # Start the server process
    process = subprocess.Popen(
        ["uv", "run", str(server_path), "--port", str(server_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        preexec_fn=os.setsid if hasattr(os, 'setsid') else None
    )

    # Store port and worker_id as attributes
    setattr(process, 'port', server_port)
    setattr(process, 'worker_id', worker_id)

    # Give the server time to start up
    time.sleep(3)

    # Check if process is still running
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        pytest.fail(
            f"Worker {worker_id}: Server failed to start on port {server_port}. "
            f"stdout: {stdout}, stderr: {stderr}"
        )

    # Wait for server to be ready with platform-specific timeout
    platform_timeout = get_platform_timeout()
    logging.info(f"Worker {worker_id}: Using {platform_timeout}s timeout for {platform.system()} platform")

    if not wait_for_server_ready(server_port):
        # Collect detailed diagnostics on failure
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            stdout, stderr = "Process still running", "Process still running"

        # Additional diagnostic information
        process_info = f"PID: {process.pid}, Poll: {process.poll()}"
        platform_info = f"Platform: {platform.system()} {platform.release()}"

        # Check if port is actually bound
        port_status = "unknown"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('localhost', server_port))
                port_status = "bound" if result == 0 else "not bound"
        except Exception as e:
            port_status = f"check failed: {e}"

        pytest.fail(
            f"Worker {worker_id}: Server did not become ready within {platform_timeout}s timeout on port {server_port}.\n"
            f"Process info: {process_info}\n"
            f"Platform info: {platform_info}\n"
            f"Port status: {port_status}\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}"
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
    """
    logging.info(f"Worker {worker_id}: Connecting MCP client to {server_url}")

    session = None
    try:
        # Create SSE client and session
        async with sse_client(server_url) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()

                logging.info(f"Worker {worker_id}: MCP client session initialized")

                yield session
    except Exception as e:
        logging.error(f"Worker {worker_id}: Error in MCP client session: {e}")
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
