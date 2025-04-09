import pytest
import platform
import os
import time
from pathlib import Path
import sys
import signal
import psutil
import logging

# Update import to use local command_executor
import sys
from pathlib import Path

# Add the parent directory to the path so we can import server modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from server.command_executor import CommandExecutor

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


@pytest.mark.integration
@pytest.mark.skipif(platform.system().lower() != "linux", reason="Linux-specific tests")
class TestLinuxCommands:
    """Integration tests for Linux commands"""

    def test_echo_command(self, executor):
        """Test echo command on Linux"""
        result = executor.execute('echo "Hello World"')  # Using double quotes instead of single
        assert result[
            "success"
        ], f"Command failed with error: {result.get('error', 'Unknown error')}"
        assert "Hello World" in result["output"]
        assert not result["error"]

    def test_ls_command(self, executor, test_file):
        """Test ls command on Linux"""
        # Change to the temporary directory
        test_dir = os.path.dirname(test_file)
        os.chdir(test_dir)

        result = executor.execute("ls")
        assert result[
            "success"
        ], f"Command failed with error: {result.get('error', 'Unknown error')}"
        assert os.path.basename(test_file) in result["output"]
        assert not result["error"]

    def test_cat_command(self, executor, test_file):
        """Test cat command on Linux"""
        result = executor.execute(f"cat {test_file}")
        assert result[
            "success"
        ], f"Command failed with error: {result.get('error', 'Unknown error')}"
        assert "test content" in result["output"]
        assert not result["error"]

    def test_which_command(self, executor):
        """Test which command on Linux"""
        result = executor.execute("which ls")
        assert result[
            "success"
        ], f"Command failed with error: {result.get('error', 'Unknown error')}"
        assert "/bin/ls" in result["output"] or "/usr/bin/ls" in result["output"]
        assert not result["error"]

    def test_timeout(self, executor):
        """Test timeout functionality"""
        logging.info("Starting timeout test")
        # Sleep command should timeout
        result = executor.execute("sleep 2", timeout=0.5)
        logging.info(f"Result: {result}")
        assert not result["success"], "Command should have failed due to timeout"
        assert (
            "timed out" in result["error"]
        ), f"Error should contain 'timed out', got: {result['error']}"
        logging.info("Timeout test completed")


@pytest.mark.integration
@pytest.mark.skipif(platform.system().lower() != "windows", reason="Windows-specific tests")
class TestWindowsCommands:
    """Integration tests for Windows commands"""

    def test_echo_command(self, executor):
        """Test echo command on Windows"""
        result = executor.execute("echo Hello World")
        assert result[
            "success"
        ], f"Command failed with error: {result.get('error', 'Unknown error')}"
        assert "Hello World" in result["output"]
        assert not result["error"]

    def test_dir_command(self, executor, test_file):
        """Test dir command on Windows"""
        # Change to the temporary directory
        test_dir = os.path.dirname(test_file)
        os.chdir(test_dir)

        result = executor.execute("dir")
        assert result[
            "success"
        ], f"Command failed with error: {result.get('error', 'Unknown error')}"
        assert os.path.basename(test_file) in result["output"]
        assert not result["error"]

    def test_type_command(self, executor, test_file):
        """Test type command on Windows"""
        result = executor.execute(f'type "{test_file}"')
        assert result[
            "success"
        ], f"Command failed with error: {result.get('error', 'Unknown error')}"
        assert "test content" in result["output"]
        assert not result["error"]

    def test_where_command(self, executor):
        """Test where command on Windows"""
        result = executor.execute("where cmd.exe")
        assert result[
            "success"
        ], f"Command failed with error: {result.get('error', 'Unknown error')}"
        assert "cmd.exe" in result["output"].lower()
        assert not result["error"]

    def test_timeout(self, executor):
        """Test timeout functionality"""
        # why cmd /c?  see https://stackoverflow.com/questions/74842935/powershell-batch-script-timeout-error-input-redirection-is-not-supported-exiti
        result = executor.execute("cmd /c start /min timeout.exe 2", timeout=0.5)
        assert not result["success"]
        assert "timed out" in result["error"]


@pytest.mark.integration
class TestCrossPlatformFeatures:
    """Integration tests for features that should work on both platforms"""

    def test_process_info(self, executor):
        """Test process information retrieval"""
        # Start a long-running command
        if platform.system().lower() == "windows":
            cmd = "cmd /c start /min timeout.exe 2"
        else:
            cmd = "sleep 5"

        result = executor.execute(cmd, timeout=0.5)
        assert not result["success"]
        assert "timed out" in result["error"]

        # Get process info before termination
        pid = result.get("pid")
        if pid:
            info = executor.get_process_info(pid)
            if info:  # Info might be None if process ended quickly
                assert isinstance(info["cpu_percent"], (int, float))
                assert isinstance(info["memory_info"], dict)

    def test_multiple_commands(self, executor):
        """Test running multiple commands in sequence"""
        for i in range(3):
            result = executor.execute('echo "test"')  # Using double quotes
            assert result[
                "success"
            ], f"Command {i} failed with error: {result.get('error', 'Unknown error')}"
            assert "test" in result["output"]
            time.sleep(0.1)  # Small delay between commands

    def test_invalid_command(self, executor):
        """Test handling of invalid commands"""
        result = executor.execute("thiscommanddoesnotexist")
        assert not result["success"]
        assert result["error"] != ""

    def test_stdout_capture(self, executor):
        """Test capturing stdout output correctly"""
        # Generate multi-line output
        if platform.system().lower() == "windows":
            # Windows echo with multiple lines
            result = executor.execute("echo Line 1 & echo Line 2 & echo Line 3")
        else:
            # Linux/Unix multi-line echo
            result = executor.execute('echo -e "Line 1\nLine 2\nLine 3"')

        assert result["success"], f"Command failed with error: {result.get('error')}"

        # Verify stdout contains all expected lines
        output = result["output"]
        assert "Line 1" in output, f"Expected 'Line 1' in output, got: {output}"
        assert "Line 2" in output, f"Expected 'Line 2' in output, got: {output}"
        assert "Line 3" in output, f"Expected 'Line 3' in output, got: {output}"

        # Verify lines appear in correct order
        line1_pos = output.find("Line 1")
        line2_pos = output.find("Line 2")
        line3_pos = output.find("Line 3")

        assert line1_pos < line2_pos < line3_pos, "Lines are not in the expected order"


if __name__ == "__main__":
    pytest.main(["-v", __file__])