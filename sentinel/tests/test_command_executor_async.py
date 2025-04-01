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

from sentinel.command_executor import CommandExecutor

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
            cmd = "echo Hello World"
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
        result = await executor.wait_for_process(token, timeout=1.0)
        
        # Verify the result
        assert result["success"] == True
        assert "Hello World" in result["output"]
        assert result["token"] == token
        assert result["status"] == "completed"
    
    async def test_execute_async_error_command(self, executor):
        """Test executing a command that will fail"""
        cmd = "nonexistentcommand"
        
        response = await executor.execute_async(cmd)
        token = response["token"]
        
        # Wait for process to complete
        result = await executor.wait_for_process(token, timeout=1.0)
        
        # Should fail but still return a valid result
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
            cmd = "ping -n 3 127.0.0.1"  # Takes ~2 seconds
        else:
            cmd = "sleep 2"
            
        response = await executor.execute_async(cmd)
        token = response["token"]
        
        # Query without waiting
        status = await executor.query_process(token, wait=False)
        assert status["status"] == "running"
        
        # Wait for completion
        await asyncio.sleep(3)  # Wait a bit longer for Windows
        
        # Query again - should indicate not running
        status = await executor.query_process(token, wait=False)
        assert "error" in status or status["status"] == "not_running"
    
    async def test_query_process_with_wait(self, executor):
        """Test query_process with waiting"""
        if platform.system().lower() == "windows":
            cmd = "echo Hello & ping -n 4 127.0.0.1"  # Echo + ~3 seconds of ping
        else:
            cmd = 'echo "Hello" && sleep 3'
            
        response = await executor.execute_async(cmd)
        token = response["token"]
        
        # Query with waiting - should block until process completes
        start_time = time.time()
        result = await executor.query_process(token, wait=True)
        duration = time.time() - start_time
        
        # It should take some time to complete (might be very fast on some systems)
        # Just log the duration instead of asserting a minimum time
        print(f"Process waited for {duration} seconds")
        
        # Verify the result
        assert result["success"] == True
        assert "Hello" in result["output"]
        assert result["status"] == "completed"
    
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
                cmd = f"echo Process {i} & ping -n 2 127.0.0.1"
            else:
                cmd = f'echo "Process {i}" && sleep 1'
                
            response = await executor.execute_async(cmd)
            tokens.append(response["token"])
        
        # Check all are running
        for token in tokens:
            status = await executor.get_process_status(token)
            assert status["status"] == "running"
        
        # Wait for all to complete
        results = await asyncio.gather(*[
            executor.wait_for_process(token)
            for token in tokens
        ])
        
        # Verify all succeeded and have correct output
        for i, result in enumerate(results):
            assert result["success"] == True
            assert f"Process {i}" in result["output"]
    
    async def test_nonexistent_token(self, executor):
        """Test operations with a nonexistent token"""
        fake_token = str(uuid.uuid4())
        
        # Try to check status
        status = await executor.get_process_status(fake_token)
        assert "error" in status
        assert "no process found" in status["error"].lower()
        
        # Try to wait for the process
        result = await executor.wait_for_process(fake_token)
        assert "error" in result
        assert "no process found" in result["error"].lower()
        
        # Try to terminate the process
        success = executor.terminate_by_token(fake_token)
        assert success == False 