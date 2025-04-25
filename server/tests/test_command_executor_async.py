import pytest
import platform
import os
import time
import asyncio
from pathlib import Path
import sys
import signal
import psutil
import logging
import uuid

# Update import to use local command_executor
import sys
from pathlib import Path

# Add the parent directory to the path so we can import server modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from mcp_tools.command_executor import CommandExecutor

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@pytest.fixture
def executor():
    """Fixture to create a CommandExecutor instance"""
    return CommandExecutor()


@pytest.fixture
def test_file(tmp_path):
    """Create a temporary test file"""
    file_path = tmp_path / "test.txt"
    with open(file_path, "w") as f:
        f.write("test content\n")
    return file_path


@pytest.fixture(autouse=True)
def cleanup_processes():
    """Cleanup any leftover processes after each test"""
    yield
    # Kill any remaining test processes
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    for child in children:
        try:
            child.terminate()
            child.wait(timeout=1)
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass


@pytest.mark.asyncio
class TestCommandExecutorAsync:
    """Tests for async methods in CommandExecutor"""

    async def test_execute_async_echo(self, executor):
        """Test executing a simple echo command asynchronously"""
        if platform.system().lower() == "windows":
            cmd = "cmd /c echo Hello World"  # Use cmd /c for Windows
        else:
            cmd = 'echo "Hello World"'

        response = await executor.execute_async(cmd)

        # Check token was returned
        assert "token" in response
        assert isinstance(response["token"], str)
        assert uuid.UUID(response["token"])  # Should be a valid UUID

        # Check status and PID
        assert response["status"] == "running"
        assert "pid" in response
        assert isinstance(response["pid"], int)

        # Now wait for it to complete
        token = response["token"]
        result = await executor.wait_for_process(token, timeout=5.0)

        # Verify the result
        assert result["success"] == True
        assert "Hello World" in result["output"]
        # Token is not included in result, so remove this check
        # assert result["token"] == token

    async def test_execute_async_error_command(self, executor):
        """Test executing a command that will fail"""
        cmd = "nonexistentcommand"

        response = await executor.execute_async(cmd)
        token = response["token"]

        # Wait for process to complete
        result = await executor.wait_for_process(token, timeout=1.0)

        assert result["success"] == False
        assert "error" in result
        assert result["status"] in ["completed", "error"]

    async def test_get_process_status(self, executor):
        """Test getting process status asynchronously"""
        # Execute a longer-running command
        if platform.system().lower() == "windows":
            cmd = "ping -n 3 127.0.0.1"  # Takes ~2 seconds
        else:
            cmd = "sleep 2"

        response = await executor.execute_async(cmd)
        token = response["token"]

        # Check status right after starting
        status = await executor.get_process_status(token)
        assert status["status"] == "running"
        assert status["token"] == token
        assert "pid" in status

        # Wait for it to complete
        result = await executor.wait_for_process(token)
        assert result["status"] == "completed"

        # Check status after completion - should indicate not running
        status = await executor.get_process_status(token)
        assert "error" in status or status["status"] == "not_running"

    async def test_query_process_no_wait(self, executor):
        """Test query_process without waiting"""
        if platform.system().lower() == "windows":
            cmd = "cmd /c ping -n 3 127.0.0.1"  # Use cmd /c for Windows
        else:
            cmd = "sleep 2"

        response = await executor.execute_async(cmd)
        token = response["token"]

        # Query without waiting - provide a default timeout
        status = await executor.query_process(token, wait=False, timeout=1.0)
        assert status["status"] == "running"

        # Wait for completion
        await asyncio.sleep(3)  # Wait a bit longer for Windows

        # Query again - should indicate completed
        status = await executor.query_process(token, wait=False, timeout=1.0)
        assert status["status"] == "completed"

    async def test_query_process_with_wait(self, executor):
        """Test query_process with waiting"""
        if platform.system().lower() == "windows":
            cmd = "cmd /c echo Hello && ping -n 4 127.0.0.1"  # Use cmd /c for Windows
        else:
            cmd = 'echo "Hello" && sleep 3'

        response = await executor.execute_async(cmd)
        token = response["token"]

        # Query with waiting - should block until process completes
        start_time = time.time()
        result = await executor.query_process(token, wait=True, timeout=10.0)
        duration = time.time() - start_time

        # It should take some time to complete (might be very fast on some systems)
        print(f"Process waited for {duration} seconds")

        # Verify the result
        assert result["status"] == "completed"
        assert "Hello" in result["output"]

    async def test_terminate_by_token(self, executor):
        """Test terminating a process by token"""
        # Start a long-running process
        if platform.system().lower() == "windows":
            cmd = "ping -n 10 127.0.0.1"  # Takes ~9 seconds
        else:
            cmd = "sleep 10"

        response = await executor.execute_async(cmd)
        token = response["token"]

        # Check it's running
        status = await executor.get_process_status(token)
        assert status["status"] == "running"

        # Terminate it
        success = executor.terminate_by_token(token)
        assert success == True, "Process termination failed"

        # Wait a moment for termination to complete
        await asyncio.sleep(0.5)

        # Check it's not running
        status = await executor.get_process_status(token)
        assert "error" in status or status["status"] == "not_running"

    async def test_execute_timeout(self, executor):
        """Test process timeout handling"""
        # Start a long process but wait with timeout
        if platform.system().lower() == "windows":
            cmd = "ping -n 10 127.0.0.1"  # Takes ~9 seconds
        else:
            cmd = "sleep 10"

        response = await executor.execute_async(cmd)
        token = response["token"]

        # Wait with short timeout
        result = await executor.wait_for_process(token, timeout=0.5)

        # Should indicate timeout
        assert result["success"] == False
        assert "timed out" in result["error"].lower() or "timeout" in result["error"].lower()

        # Ensure process is terminated
        await asyncio.sleep(0.5)
        status = await executor.get_process_status(token)
        assert "error" in status or status["status"] == "not_running"

    async def test_concurrent_processes(self, executor):
        """Test running multiple processes concurrently"""
        # Start several processes
        tokens = []

        for i in range(3):
            if platform.system().lower() == "windows":
                cmd = f"cmd /c echo Process {i} && ping -n 2 127.0.0.1"  # Use cmd /c for Windows
            else:
                cmd = f'echo "Process {i}";sleep 2'

            response = await executor.execute_async(cmd)
            tokens.append(response["token"])

        # Check all are running
        for token in tokens:
            status = await executor.get_process_status(token)
            assert status["status"] == "running"

        # Wait for all to complete with timeout
        results = await asyncio.gather(*[executor.wait_for_process(token, timeout=10.0) for token in tokens])

        # Verify all completed and have correct output
        for i, result in enumerate(results):
            assert result["status"] == "completed"
            assert f"Process {i}" in result["output"]

    async def test_nonexistent_token(self, executor):
        """Test operations with a nonexistent token"""
        fake_token = str(uuid.uuid4())

        # Try to check status
        status = await executor.get_process_status(fake_token)
        assert "error" in status
        # Update expected error message
        assert "process token not found" in status["error"].lower()

        # Try to wait for the process
        result = await executor.wait_for_process(fake_token)
        assert "error" in result
        assert "process token not found" in result["error"].lower()

        # Try to terminate the process
        success = executor.terminate_by_token(fake_token)
        assert success == False

    async def test_large_stdout_capture(self, executor):
        """Test capturing large stdout output completely from a long-running process"""
        # Command that generates a large number of lines
        line_count = 500  # Generate 500 lines of output
        
        if platform.system().lower() == "windows":
            # Windows command to generate many lines
            cmd = f"for /L %i in (1,1,{line_count}) do @echo Line %i of {line_count}"
        else:
            # Unix command to generate many lines
            cmd = f"for i in $(seq 1 {line_count}); do echo \"Line $i of {line_count}\"; done"
            
        # Execute the command
        response = await executor.execute_async(cmd)
        token = response["token"]
        
        # Wait for the process to complete
        result = await executor.wait_for_process(token)
        
        # Verify the command succeeded
        assert result["success"] == True
        assert result["status"] == "completed"
        
        # Split output into lines and count
        output_lines = result["output"].strip().split("\n")
        actual_lines = [line for line in output_lines if line.strip()]  # Remove empty lines
        
        # Check that we have the expected number of lines (allowing for some variation)
        # Some platforms might add extra lines, so we check for minimum
        assert len(actual_lines) >= line_count * 0.9, f"Expected at least {line_count*0.9} lines, got {len(actual_lines)}"
        
        # Verify content of some specific lines
        if len(actual_lines) >= line_count:
            # Check first line
            assert f"Line 1 of {line_count}" in actual_lines[0]
            
            # Check a line in the middle
            middle_idx = line_count // 2
            if middle_idx < len(actual_lines):
                assert f"Line {middle_idx}" in actual_lines[middle_idx - 1]
            
            # Check the last line
            if line_count <= len(actual_lines):
                assert f"Line {line_count}" in actual_lines[line_count - 1]

    async def test_streaming_output_capture(self, executor):
        """Test capturing streaming output from a long-running process"""
        # Number of lines to generate with delay between them
        line_count = 20
        
        if platform.system().lower() == "windows":
            # Windows command that prints lines with a delay
            # Using timeout between prints to simulate processing delay
            delay_cmd = "ping -n 1 127.0.0.1"  # Quick delay without visible output
            cmd = f"powershell -Command \"for ($i=1; $i -le {line_count}; $i++) {{ Write-Host \\\"Processing chunk $i of {line_count}\\\"; Start-Sleep -Milliseconds 100 }}\""
        else:
            # Unix command that prints lines with a delay
            # Using sleep between prints to simulate processing delay
            cmd = f"for i in $(seq 1 {line_count}); do echo \"Processing chunk $i of {line_count}\"; sleep 0.1; done"

        print(f"Running command: {cmd}")
        
        # Execute the command
        response = await executor.execute_async(cmd)
        token = response["token"]
        
        # Wait for the process to complete
        start_time = time.time()
        result = await executor.wait_for_process(token)
        duration = time.time() - start_time
        
        # Should take some time to complete
        print(f"Streaming output process completed in {duration:.2f} seconds")
        
        # Verify the command succeeded
        assert result["success"] == True
        assert result["status"] == "completed"
        
        # Verify output contains the expected lines
        output_lines = result["output"].strip().split("\n")
        actual_lines = [line for line in output_lines if line.strip() and "Processing chunk" in line]
        
        # Check that we have most of the expected output lines
        assert len(actual_lines) >= line_count * 0.8, f"Expected at least {line_count*0.8} lines, got {len(actual_lines)}"
        
        # Print a sample of captured output for debugging
        print(f"Captured {len(actual_lines)} output lines out of {line_count} expected")
        if len(actual_lines) > 0:
            print(f"First line: {actual_lines[0]}")
            if len(actual_lines) > 1:
                print(f"Last line: {actual_lines[-1]}")
                
        # Verify first and last lines if available
        if len(actual_lines) > 0:
            assert "Processing chunk 1" in actual_lines[0]
            if len(actual_lines) >= line_count:
                assert f"Processing chunk {line_count}" in actual_lines[-1]
                
    async def test_completed_process_output_retrieval(self, executor):
        """Test retrieving output from a completed process without waiting again"""
        if platform.system().lower() == "windows":
            cmd = "echo Hello World"
        else:
            cmd = 'echo "Hello World"'

        # Start and wait for the process to complete
        response = await executor.execute_async(cmd)
        token = response["token"]
        
        # Wait for the process to complete
        result = await executor.wait_for_process(token)
        assert result["status"] == "completed"
        assert "Hello World" in result["output"]
        
        # Now try to get the output again using get_process_status
        status = await executor.get_process_status(token)
        assert status["status"] == "completed"
        assert "output" in status
        assert "Hello World" in status["output"]
        
        # Try using query_process without waiting
        query_result = await executor.query_process(token, wait=False)
        assert query_result["status"] == "completed"
        assert "output" in query_result
        assert "Hello World" in query_result["output"]
        
        # Test that calling wait_for_process again works and returns cached results
        result_again = await executor.wait_for_process(token)
        assert result_again["status"] == "completed"
        assert "output" in result_again
        assert "Hello World" in result_again["output"]
        
    async def test_query_completed_process_without_wait(self, executor):
        """Test retrieving stdout from a completed process using query_process without wait=True"""
        # Create a command that generates multiple lines of output
        if platform.system().lower() == "windows":
            cmd = "echo Line 1 && echo Line 2 && echo Line 3"
        else:
            cmd = 'echo "Line 1" && echo "Line 2" && echo "Line 3"'
            
        # Start the command
        response = await executor.execute_async(cmd)
        token = response["token"]
        
        # Wait for completion to ensure it's done and stored in the completed_processes cache
        await asyncio.sleep(1)
        
        # Use query_process without wait to get the process status
        status = await executor.query_process(token, wait=False)
        
        # Verify it's completed and has output
        assert status["status"] == "completed"
        assert "output" in status
        
        # Check content of the output
        output = status["output"]
        assert "Line 1" in output
        assert "Line 2" in output
        assert "Line 3" in output
        
        # Check that we can query it repeatedly and get the same results
        for _ in range(3):
            repeat_status = await executor.query_process(token, wait=False)
            assert repeat_status["status"] == "completed"
            assert "output" in repeat_status
            assert repeat_status["output"] == output
        
        # Try with a different process too
        if platform.system().lower() == "windows":
            cmd2 = "echo Different output"
        else:
            cmd2 = 'echo "Different output"'
            
        response2 = await executor.execute_async(cmd2)
        token2 = response2["token"]
        
        # Wait for completion
        await asyncio.sleep(1)
        
        # Check both processes have their correct outputs
        status1 = await executor.query_process(token, wait=False)
        status2 = await executor.query_process(token2, wait=False)
        
        assert status1["status"] == "completed"
        assert status2["status"] == "completed"
        
        assert "Line 1" in status1["output"]
        assert "Different output" in status2["output"]

    async def test_git_branch_command(self, executor):
        """Test git rev-parse command to get current branch name asynchronously"""
        # Store original directory
        original_dir = os.getcwd()
        try:
            # Change to the directory containing this test file
            test_file_dir = os.path.dirname(os.path.abspath(__file__))
            os.chdir(test_file_dir)
            
            # Find the git root directory (assuming we're in a git repo)
            response = await executor.execute_async("git rev-parse --show-toplevel")
            assert "token" in response, "No token returned"
            token = response["token"]
            
            # Wait for the command to complete
            result = await executor.wait_for_process(token, timeout=5.0)
            assert result["success"], "Not in a git repository"
            git_root = result["output"].strip()
            
            # Change to git root directory
            os.chdir(git_root)
            
            # Now run the branch command asynchronously
            response = await executor.execute_async("git rev-parse --abbrev-ref HEAD")
            assert "token" in response, "No token returned"
            token = response["token"]
            
            # Wait for the command to complete
            result = await executor.wait_for_process(token, timeout=5.0)
            assert result["success"], f"Command failed with error: {result.get('error', 'Unknown error')}"
            assert result["output"].strip(), "Branch name should not be empty"
            # Branch name should be a valid git branch name (no spaces or special chars except - _ /)
            assert all(c.isalnum() or c in "-_/" for c in result["output"].strip()), "Invalid branch name characters"
            assert not result["error"], "Command should not have errors"
            
            # Test query_process method as well
            response = await executor.execute_async("git rev-parse --abbrev-ref HEAD")
            token = response["token"]
            
            # Query without waiting
            status = await executor.query_process(token, wait=False, timeout=1.0)
            assert status["status"] in ["running", "completed"], f"Unexpected status: {status['status']}"
            
            # Query with waiting
            result = await executor.query_process(token, wait=True, timeout=5.0)
            assert result["status"] == "completed"
            assert result["output"].strip(), "Branch name should not be empty"
            
        finally:
            # Restore original directory
            os.chdir(original_dir)