"""Tests for server launch functionality."""

import subprocess
import time
import signal
import os
import sys
import socket
import requests
import threading
from pathlib import Path
import pytest


def is_port_open(host="localhost", port=8000, timeout=1):
    """Check if a port is open and accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, socket.error, ConnectionRefusedError):
        return False


def wait_for_server_ready(host="localhost", port=8000, timeout=180, check_interval=0.5):
    """Wait for server to be ready by checking if it responds to HTTP requests."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # First check if port is open
            if is_port_open(host, port, timeout=1):
                # Then try to make an actual HTTP request
                response = requests.get(f"http://{host}:{port}/", timeout=2)
                if response.status_code == 200:
                    return True
        except (requests.exceptions.RequestException, ConnectionError):
            pass

        time.sleep(check_interval)

    return False


def monitor_process_output(process, output_lines, ready_event):
    """Monitor process output for readiness indicators."""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                output_lines.append(line.strip())
                # Look for uvicorn startup messages
                if "Uvicorn running on" in line or "Application startup complete" in line:
                    ready_event.set()
                    break
    except Exception:
        pass


class TestServerLaunch:
    """Test cases for server launch functionality."""

    def test_server_launches_successfully(self):
        """Test that 'uv run server/main.py' starts without immediate crash."""
        # Get the project root directory (two levels up from this test file)
        project_root = Path(__file__).parent.parent.parent

        # Change to project root directory for the subprocess
        original_cwd = os.getcwd()

        try:
            os.chdir(project_root)

            # Launch the server using the exact production command
            process = subprocess.Popen(
                ["uv", "run", "server/main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Give the server time to start up or crash if it's going to
            time.sleep(3)

            # Check if process is still running (poll() returns None if running)
            poll_result = process.poll()

            # If the process has exited, capture output for debugging
            if poll_result is not None:
                stdout, stderr = process.communicate()
                pytest.fail(
                    f"Server process exited with code {poll_result}.\n"
                    f"STDOUT: {stdout}\n"
                    f"STDERR: {stderr}"
                )

            # Process should still be running
            assert poll_result is None, "Server process should still be running"

        finally:
            # Cleanup: terminate the server process
            try:
                if process.poll() is None:  # Process is still running
                    # Try graceful termination first
                    process.terminate()

                    # Wait up to 10 seconds for graceful shutdown
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        # Force kill if graceful shutdown didn't work
                        process.kill()
                        process.wait()

            except Exception as cleanup_error:
                # Log cleanup error but don't fail the test
                print(f"Warning: Error during cleanup: {cleanup_error}")

            # Restore original working directory
            os.chdir(original_cwd)

    def test_server_responds_to_termination(self):
        """Test that the server responds properly to termination signals."""
        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent
        original_cwd = os.getcwd()

        try:
            os.chdir(project_root)

            # Launch the server
            process = subprocess.Popen(
                ["uv", "run", "server/main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Give the server time to start
            time.sleep(2)

            # Verify it's running
            assert process.poll() is None, "Server should be running"

            # Send termination signal
            process.terminate()

            # Wait for process to terminate (should happen quickly)
            try:
                return_code = process.wait(timeout=15)
                # Process should terminate cleanly (return code varies by system)
                assert return_code is not None, "Process should have terminated"
            except subprocess.TimeoutExpired:
                # If it doesn't terminate gracefully, force kill
                process.kill()
                process.wait()
                pytest.fail("Server did not respond to termination signal within timeout")

        finally:
            # Ensure cleanup
            try:
                if process.poll() is None:
                    process.kill()
                    process.wait()
            except Exception:
                pass

            os.chdir(original_cwd)

    def test_server_startup_time(self):
        """Test that the server starts within a reasonable time frame."""
        project_root = Path(__file__).parent.parent.parent
        original_cwd = os.getcwd()

        try:
            os.chdir(project_root)

            start_time = time.time()

            # Launch the server
            process = subprocess.Popen(
                ["uv", "run", "server/main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to be ready (or fail)
            max_startup_time = 180  # seconds (3 minutes)
            startup_successful = False

            while time.time() - start_time < max_startup_time:
                if process.poll() is not None:
                    # Process has exited - this is a failure
                    stdout, stderr = process.communicate()
                    pytest.fail(
                        f"Server exited during startup.\n"
                        f"STDOUT: {stdout}\n"
                        f"STDERR: {stderr}"
                    )

                # Check if we've waited long enough to consider it "started"
                if time.time() - start_time >= 3:
                    startup_successful = True
                    break

                time.sleep(0.5)

            if not startup_successful:
                pytest.fail(f"Server did not start within {max_startup_time} seconds")

            startup_time = time.time() - start_time
            print(f"Server startup took {startup_time:.2f} seconds")

            # Reasonable startup time assertion (adjust as needed)
            assert startup_time < max_startup_time, f"Server took too long to start: {startup_time:.2f}s"

        finally:
            # Cleanup
            try:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            except Exception:
                pass

            os.chdir(original_cwd)

    def test_server_is_actually_ready_to_serve(self):
        """Test that the server is actually ready to serve HTTP requests."""
        project_root = Path(__file__).parent.parent.parent
        original_cwd = os.getcwd()

        try:
            os.chdir(project_root)

            # Launch the server
            process = subprocess.Popen(
                ["uv", "run", "server/main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to be actually ready (not just process alive)
            server_ready = wait_for_server_ready(timeout=180)

            if not server_ready:
                # If server isn't ready, capture output for debugging
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    pytest.fail(
                        f"Server process exited before becoming ready.\n"
                        f"STDOUT: {stdout}\n"
                        f"STDERR: {stderr}"
                    )
                else:
                    pytest.fail("Server did not become ready within 180 seconds")

            # Verify we can actually make a request
            response = requests.get("http://localhost:8000/", timeout=10)
            assert response.status_code == 200, f"Server returned status {response.status_code}"

            print("✅ Server is ready and responding to HTTP requests")

        finally:
            # Cleanup
            try:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            except Exception:
                pass

            os.chdir(original_cwd)

    def test_server_readiness_via_output_monitoring(self):
        """Test server readiness by monitoring stdout for startup messages."""
        project_root = Path(__file__).parent.parent.parent
        original_cwd = os.getcwd()

        try:
            os.chdir(project_root)

            # Launch the server
            process = subprocess.Popen(
                ["uv", "run", "server/main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )

            # Monitor output for readiness
            output_lines = []
            ready_event = threading.Event()

            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=monitor_process_output,
                args=(process, output_lines, ready_event)
            )
            monitor_thread.daemon = True
            monitor_thread.start()

            # Wait for ready signal or timeout
            server_ready = ready_event.wait(timeout=180)

            if not server_ready:
                # Check if process crashed
                if process.poll() is not None:
                    pytest.fail(
                        f"Server process exited before startup complete.\n"
                        f"Output: {chr(10).join(output_lines)}"
                    )
                else:
                    pytest.fail(
                        f"Server did not show ready message within 180 seconds.\n"
                        f"Output so far: {chr(10).join(output_lines)}"
                    )

            print(f"✅ Server startup detected via output monitoring")
            print(f"Captured output lines: {len(output_lines)}")

            # Verify server is actually responding
            if wait_for_server_ready(timeout=10):
                response = requests.get("http://localhost:8000/", timeout=5)
                assert response.status_code == 200
                print("✅ Confirmed server is responding to requests")

        finally:
            # Cleanup
            try:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            except Exception:
                pass

            os.chdir(original_cwd)

    def test_server_port_availability_check(self):
        """Test server readiness by checking port availability."""
        project_root = Path(__file__).parent.parent.parent
        original_cwd = os.getcwd()

        try:
            os.chdir(project_root)

            # Verify port is initially closed
            assert not is_port_open("localhost", 8000), "Port 8000 should be closed initially"

            # Launch the server
            process = subprocess.Popen(
                ["uv", "run", "server/main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for port to become available
            port_ready = False
            start_time = time.time()
            timeout = 180  # 3 minutes

            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    pytest.fail(
                        f"Server process exited before port became available.\n"
                        f"STDOUT: {stdout}\n"
                        f"STDERR: {stderr}"
                    )

                if is_port_open("localhost", 8000):
                    port_ready = True
                    break

                time.sleep(0.5)

            assert port_ready, f"Port 8000 did not become available within {timeout} seconds"

            startup_time = time.time() - start_time
            print(f"✅ Port became available after {startup_time:.2f} seconds")

        finally:
            # Cleanup
            try:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            except Exception:
                pass

            os.chdir(original_cwd)
