import platform
import subprocess
import asyncio
import uuid
from typing import Dict, Any, List, Optional, Union
import logging
import shlex
import time
import psutil
import json
import os
import tempfile
from datetime import datetime, UTC
from pathlib import Path
import traceback

g_config_sleep_when_running = True

# Create logger with the module name
logger = logging.getLogger(__name__)


def _log_with_context(log_level: int, msg: str, context: Dict[str, Any] = None) -> None:
    """Helper function for structured logging with context

    Args:
        log_level: The logging level to use
        msg: The message to log
        context: Optional dictionary of contextual information
    """
    if context is None:
        context = {}

    # Add timestamp in ISO format using timezone-aware UTC
    context["timestamp"] = datetime.now(UTC).isoformat()

    # Format the log message with context
    structured_msg = f"{msg} | Context: {json.dumps(context, default=str)}"
    logger.log(log_level, structured_msg)


class CommandExecutorV2:
    """Command executor that can run processes synchronously or asynchronously,
    using temporary files for stdout/stderr capture.

    Example:
        # Synchronous execution
        executor = CommandExecutorV2()
        result = executor.execute("ls -la")

        # Asynchronous execution
        async def run_command():
            executor = CommandExecutorV2()

            # Start the command
            response = await executor.execute_async("long-running-command")
            token = response["token"]

            # Later, check status
            status = await executor.get_process_status(token)

            # Wait for completion
            result = await executor.wait_for_process(token)

            # Or combined query and wait
            result = await executor.query_process(token, wait=True, timeout=30)

            # To terminate early
            executor.terminate_by_token(token)
    """

    def __init__(self, temp_dir: Optional[str] = None):
        self.os_type = platform.system().lower()
        self.running_processes = {}
        self.process_tokens = {}  # Maps tokens to process IDs
        self.completed_processes = {}  # Store results of completed processes
        self.temp_files = {}  # Maps PIDs to (stdout_file, stderr_file) tuples
        self.cleanup_lock = asyncio.Lock()  # Lock to protect temp file operations

        # Use specified temp dir or system default
        self.temp_dir = temp_dir if temp_dir else tempfile.gettempdir()

        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)

        _log_with_context(
            logging.INFO,
            "Initialized CommandExecutorV2",
            {"temp_dir": self.temp_dir, "os_type": self.os_type},
        )

    def _create_temp_files(self, prefix: str = "cmd_") -> tuple:
        """Create temporary files for stdout and stderr

        Args:
            prefix: Prefix for the temporary files

        Returns:
            Tuple of (stdout_path, stderr_path, stdout_file, stderr_file)
        """
        stdout_fd, stdout_path = tempfile.mkstemp(
            prefix=f"{prefix}out_", dir=self.temp_dir, text=True
        )
        stderr_fd, stderr_path = tempfile.mkstemp(
            prefix=f"{prefix}err_", dir=self.temp_dir, text=True
        )

        # Convert file descriptors to file objects
        stdout_file = os.fdopen(stdout_fd, "w")
        stderr_file = os.fdopen(stderr_fd, "w")

        _log_with_context(
            logging.DEBUG,
            "Created temp files",
            {"stdout_path": stdout_path, "stderr_path": stderr_path},
        )

        return stdout_path, stderr_path, stdout_file, stderr_file

    def _read_temp_file(self, file_path: str) -> str:
        """Read the contents of a temporary file

        Args:
            file_path: Path to the file to read

        Returns:
            Contents of the file as a string
        """
        try:
            if not os.path.exists(file_path):
                _log_with_context(
                    logging.WARNING,
                    f"Temp file does not exist: {file_path}",
                    {"path": file_path},
                )
                return ""

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                _log_with_context(
                    logging.DEBUG,
                    f"Read temp file: {file_path}",
                    {
                        "path": file_path,
                        "content_length": len(content),
                        "content_sample": content[:100] if content else "",
                    },
                )
                return content
        except Exception as e:
            _log_with_context(
                logging.ERROR,
                f"Error reading temp file: {file_path}",
                {"error": str(e), "path": file_path},
            )
            return f"[Error reading output: {str(e)}]"

    async def _cleanup_temp_files(self, pid: int, from_monitor: bool = False) -> None:
        """Clean up temporary files associated with a process

        Args:
            pid: Process ID
            from_monitor: Whether this is called from the monitor task
        """
        # Skip the lock acquisition if called from monitor to avoid deadlocks
        if from_monitor:
            _log_with_context(
                logging.DEBUG,
                f"Monitor skipping cleanup for PID {pid}",
                {"pid": pid, "from_monitor": from_monitor},
            )
            return

        # Use a lock to prevent race conditions when cleaning up files
        async with self.cleanup_lock:
            if pid in self.temp_files:
                stdout_path, stderr_path = self.temp_files[pid]

                _log_with_context(
                    logging.DEBUG,
                    f"Cleaning up temp files for PID {pid}",
                    {
                        "pid": pid,
                        "stdout_path": stdout_path,
                        "stderr_path": stderr_path,
                        "from_monitor": from_monitor,
                    },
                )

                # Remove stdout file
                try:
                    if os.path.exists(stdout_path):
                        os.remove(stdout_path)
                        _log_with_context(
                            logging.DEBUG,
                            f"Removed stdout temp file: {stdout_path}",
                            {"pid": pid, "path": stdout_path},
                        )
                except Exception as e:
                    _log_with_context(
                        logging.WARNING,
                        f"Error removing stdout temp file",
                        {"pid": pid, "path": stdout_path, "error": str(e)},
                    )

                # Remove stderr file
                try:
                    if os.path.exists(stderr_path):
                        os.remove(stderr_path)
                        _log_with_context(
                            logging.DEBUG,
                            f"Removed stderr temp file: {stderr_path}",
                            {"pid": pid, "path": stderr_path},
                        )
                except Exception as e:
                    _log_with_context(
                        logging.WARNING,
                        f"Error removing stderr temp file",
                        {"pid": pid, "path": stderr_path, "error": str(e)},
                    )

                # Remove from tracking
                del self.temp_files[pid]
                _log_with_context(
                    logging.DEBUG,
                    f"Removed PID {pid} from temp_files tracking",
                    {"pid": pid},
                )

    def _prepare_redirected_command(
        self, command: str, stdout_path: str, stderr_path: str
    ) -> str:
        """Prepare a command with output redirection

        Args:
            command: Original command
            stdout_path: Path to stdout file
            stderr_path: Path to stderr file

        Returns:
            Modified command with redirection
        """
        if self.os_type == "windows":
            # For Windows, use standard redirection
            return f'{command} >> "{stdout_path}" 2>> "{stderr_path}"'
        else:
            # Unix redirection
            return f"{command} >> '{stdout_path}' 2>> '{stderr_path}'"

    def execute(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Execute a command and return the result with process monitoring

        Args:
            command: The command to execute
            timeout: Optional timeout in seconds
        """
        mapped_command = command
        start_time = time.time()
        pid = None

        # Create temporary files for stdout/stderr
        stdout_path, stderr_path, stdout_file, stderr_file = self._create_temp_files()

        try:
            _log_with_context(
                logging.INFO,
                "Starting command execution with file redirection",
                {
                    "command": mapped_command,
                    "timeout": timeout,
                    "os_type": self.os_type,
                    "stdout_path": stdout_path,
                    "stderr_path": stderr_path,
                },
            )

            # Close file handles - we'll use redirection instead
            stdout_file.close()
            stderr_file.close()

            # Prepare redirected command
            redirected_command = self._prepare_redirected_command(
                mapped_command, stdout_path, stderr_path
            )

            _log_with_context(
                logging.DEBUG,
                "Using command with redirection",
                {"redirected_command": redirected_command},
            )

            # Use subprocess with shell=True to enable redirection
            process = subprocess.Popen(redirected_command, shell=True, text=True)

            pid = process.pid
            self.temp_files[pid] = (stdout_path, stderr_path)

            try:
                process_info = psutil.Process(pid)
                memory_info = process_info.memory_info()._asdict()
                cpu_percent = process_info.cpu_percent()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                memory_info = {}
                cpu_percent = None
                _log_with_context(
                    logging.WARNING,
                    "Could not get process metrics",
                    {"error": str(e), "pid": pid},
                )

            _log_with_context(
                logging.INFO,
                "Process started",
                {
                    "pid": pid,
                    "memory_info": memory_info,
                    "cpu_percent": cpu_percent,
                    "command": mapped_command,
                    "redirected_command": redirected_command,
                },
            )

            # Store process for potential later use
            self.running_processes[pid] = process

            try:
                # Wait for process to complete with timeout
                exit_code = process.wait(timeout=timeout)
                end_time = time.time()
                duration = end_time - start_time

                # Read output from temporary files
                stdout = self._read_temp_file(stdout_path)
                stderr = self._read_temp_file(stderr_path)

                _log_with_context(
                    logging.INFO,
                    "Process completed",
                    {
                        "pid": pid,
                        "returncode": exit_code,
                        "duration": duration,
                        "success": exit_code == 0,
                        "stdout_length": len(stdout),
                        "stderr_length": len(stderr),
                        "stdout_sample": stdout[:100] if stdout else "",
                        "stderr_sample": stderr[:100] if stderr else "",
                    },
                )

                # Process completed within timeout
                result = {
                    "success": exit_code == 0,
                    "output": stdout,
                    "error": stderr,
                    "pid": pid,
                    "duration": duration,
                }

                # Clean up temp files synchronously for this synchronous method
                if pid in self.temp_files:
                    stdout_path, stderr_path = self.temp_files[pid]

                    # Clean up - synchronous version
                    for path in [stdout_path, stderr_path]:
                        try:
                            if os.path.exists(path):
                                os.remove(path)
                                _log_with_context(
                                    logging.DEBUG,
                                    f"Removed temp file: {path}",
                                    {"pid": pid, "path": path},
                                )
                        except Exception as e:
                            _log_with_context(
                                logging.WARNING,
                                f"Error removing temp file",
                                {"pid": pid, "path": path, "error": str(e)},
                            )

                    # Remove tracking
                    del self.temp_files[pid]

                return result

            except subprocess.TimeoutExpired:
                # Process timed out, terminate it
                _log_with_context(
                    logging.ERROR,
                    "Process timeout",
                    {
                        "pid": pid,
                        "timeout": timeout,
                        "command": mapped_command,
                        "elapsed_time": time.time() - start_time,
                    },
                )
                process.kill()

                # Read whatever output we have so far
                stdout = self._read_temp_file(stdout_path)
                stderr = self._read_temp_file(stderr_path)

                raise TimeoutError(f"Command timed out after {timeout} seconds")

        except TimeoutError as e:
            end_time = time.time()
            _log_with_context(
                logging.ERROR,
                "Command execution timed out",
                {
                    "pid": pid,
                    "error": str(e),
                    "duration": end_time - start_time,
                    "command": mapped_command,
                },
            )
            return {
                "success": False,
                "error": str(e),
                "output": stdout if "stdout" in locals() else "",
                "pid": pid,
                "duration": end_time - start_time,
            }

        except Exception as e:
            end_time = time.time()
            _log_with_context(
                logging.ERROR,
                "Unexpected error during command execution",
                {
                    "pid": pid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration": end_time - start_time,
                    "command": mapped_command,
                    "traceback": traceback.format_exc(),
                },
            )

            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "duration": end_time - start_time,
            }

        finally:
            # Clean up process tracking and temp files
            if pid in self.running_processes:
                _log_with_context(
                    logging.DEBUG,
                    "Cleaning up process tracking and temp files",
                    {"pid": pid},
                )
                self.running_processes.pop(pid, None)

                # Clean up temp files synchronously
                if pid in self.temp_files:
                    stdout_path, stderr_path = self.temp_files[pid]

                    # Clean up - synchronous version
                    for path in [stdout_path, stderr_path]:
                        try:
                            if os.path.exists(path):
                                os.remove(path)
                                _log_with_context(
                                    logging.DEBUG,
                                    f"Removed temp file from finally: {path}",
                                    {"pid": pid, "path": path},
                                )
                        except Exception as e:
                            _log_with_context(
                                logging.WARNING,
                                f"Error removing temp file from finally",
                                {"pid": pid, "path": path, "error": str(e)},
                            )

                    # Remove tracking
                    del self.temp_files[pid]

    async def _monitor_async_process(
        self, token: str, timeout: Optional[float] = None
    ) -> None:
        """Monitor an async process and collect its output when it completes

        This is an internal method called as a task to avoid blocking
        """
        try:
            # Log that monitoring has started
            _log_with_context(
                logging.DEBUG,
                "Starting async process monitor",
                {"token": token, "timeout": timeout},
            )

            # We no longer need to call cleanup with from_monitor=True
            # The wait_for_process method will handle reading files with the correct lock handling

            # Now wait for the process
            result = await self.wait_for_process(token, timeout, from_monitor=True)
            _log_with_context(
                logging.DEBUG,
                "Async process monitor completed",
                {"token": token, "status": result.get("status", "unknown")},
            )
        except Exception as e:
            _log_with_context(
                logging.ERROR,
                "Error in async process monitor",
                {
                    "token": token,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                },
            )

    async def execute_async(
        self, command: str, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute a command asynchronously and return a token for tracking

        Args:
            command: The command to execute
            timeout: Optional timeout in seconds

        Returns:
            Dictionary with the token and initial status information
        """
        # Generate a unique token for this execution
        token = str(uuid.uuid4())
        mapped_command = command

        # Create temporary files for stdout/stderr
        stdout_path, stderr_path, stdout_file, stderr_file = self._create_temp_files(
            f"{token[:8]}_"
        )

        _log_with_context(
            logging.INFO,
            "Starting async command execution with file redirection",
            {
                "command": mapped_command,
                "timeout": timeout,
                "os_type": self.os_type,
                "token": token,
                "stdout_path": stdout_path,
                "stderr_path": stderr_path,
            },
        )

        # Launch the process
        try:
            # Close file handles - we'll use redirection instead
            stdout_file.close()
            stderr_file.close()

            # Prepare redirected command
            redirected_command = self._prepare_redirected_command(
                mapped_command, stdout_path, stderr_path
            )

            _log_with_context(
                logging.DEBUG,
                "Using async command with redirection",
                {"redirected_command": redirected_command, "token": token},
            )

            # Use subprocess with shell=True to enable redirection
            process = subprocess.Popen(redirected_command, shell=True, text=True)

            pid = process.pid
            self.temp_files[pid] = (stdout_path, stderr_path)

            try:
                # Get initial process metrics
                process_info = psutil.Process(pid)
                memory_info = process_info.memory_info()._asdict()
                cpu_percent = process_info.cpu_percent()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                memory_info = {}
                cpu_percent = None
                _log_with_context(
                    logging.WARNING,
                    "Could not get async process metrics",
                    {"error": str(e), "pid": pid, "token": token},
                )

            _log_with_context(
                logging.INFO,
                "Async process started",
                {
                    "pid": pid,
                    "memory_info": memory_info,
                    "cpu_percent": cpu_percent,
                    "command": mapped_command,
                    "redirected_command": redirected_command,
                    "token": token,
                },
            )

            # Store the process and mapping
            self.running_processes[pid] = process
            self.process_tokens[token] = pid

            # Create a task to monitor the process
            asyncio.create_task(self._monitor_async_process(token, timeout))

            # Return initial information
            return {
                "token": token,
                "status": "running",
                "pid": pid,
                "memory_info": memory_info,
                "cpu_percent": cpu_percent,
            }

        except Exception as e:
            _log_with_context(
                logging.ERROR,
                "Error starting async process",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "command": mapped_command,
                    "token": token,
                    "traceback": traceback.format_exc(),
                },
            )

            # Store the error in completed processes
            self.completed_processes[token] = {
                "status": "error",
                "error": f"Failed to start process: {str(e)}",
                "success": False,
            }

            # Clean up temp files if they were created
            for path in [stdout_path, stderr_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as cleanup_error:
                        _log_with_context(
                            logging.WARNING,
                            "Error cleaning up temp file",
                            {"error": str(cleanup_error), "path": path},
                        )

            return {
                "token": token,
                "status": "error",
                "error": f"Failed to start process: {str(e)}",
            }

    async def get_process_status(self, token: str) -> Dict[str, Any]:
        """Get the current status of a process by token without waiting for completion

        Args:
            token: The token returned from execute_async

        Returns:
            Dictionary with current status information
        """
        if token in self.completed_processes:
            # Process has already completed
            completed_result = self.completed_processes[token]
            _log_with_context(
                logging.INFO,
                "Fetching status for completed process",
                {"token": token, "status": completed_result.get("status", "completed")},
            )
            return completed_result

        if token not in self.process_tokens:
            # Process token not found
            error_msg = f"Process token not found: {token}"
            _log_with_context(logging.ERROR, error_msg, {"token": token})
            return {"status": "error", "error": error_msg}

        # Get the process ID
        pid = self.process_tokens[token]

        # Get process metrics via psutil
        try:
            process_info = psutil.Process(pid)
            memory_info = process_info.memory_info()._asdict()
            cpu_percent = process_info.cpu_percent()
            status = "running"

            # Check if output is available in temp files
            if pid in self.temp_files:
                try:
                    stdout_path, stderr_path = self.temp_files[pid]
                    current_stdout = self._read_temp_file(stdout_path)
                    current_stderr = self._read_temp_file(stderr_path)
                except Exception as e:
                    _log_with_context(
                        logging.WARNING,
                        "Error reading temp files for status",
                        {"token": token, "pid": pid, "error": str(e)},
                    )
                    current_stdout = ""
                    current_stderr = f"Error reading output: {str(e)}"
            else:
                current_stdout = ""
                current_stderr = ""

        except psutil.NoSuchProcess:
            # Process no longer exists, but we don't have completion info
            memory_info = {}
            cpu_percent = None
            status = "unknown"
            current_stdout = ""
            current_stderr = ""
        except Exception as e:
            memory_info = {}
            cpu_percent = None
            current_stdout = ""
            current_stderr = ""
            _log_with_context(
                logging.WARNING,
                "Error getting process status",
                {"token": token, "pid": pid, "error": str(e)},
            )
            status = "error_monitoring"

        return {
            "status": status,
            "pid": pid,
            "memory_info": memory_info,
            "cpu_percent": cpu_percent,
            "token": token,
            "current_stdout": current_stdout,
            "current_stderr": current_stderr,
        }

    def get_allowed_commands(self) -> List[str]:
        """Get the list of allowed commands based on the OS type"""
        return []

    def terminate_process(self, pid: int) -> bool:
        """Terminate a process by PID

        Args:
            pid: The process ID to terminate

        Returns:
            True if the process was terminated successfully, False otherwise
        """
        try:
            process = psutil.Process(pid)
            process.terminate()

            # Give it a moment to terminate
            gone, still_alive = psutil.wait_procs([process], timeout=3)
            if still_alive:
                # Force kill if still alive
                for p in still_alive:
                    p.kill()

            # Clean up temp files
            self._cleanup_temp_files(pid)

            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
            _log_with_context(
                logging.ERROR,
                "Error terminating process",
                {"pid": pid, "error": str(e)},
            )
            return False

    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a process

        Args:
            pid: The process ID to get information for

        Returns:
            Dictionary with process information or None if the process cannot be found
        """
        try:
            process = psutil.Process(pid)
            info = {
                "pid": pid,
                "status": process.status(),
                "cpu_percent": process.cpu_percent(),
                "memory_info": process.memory_info()._asdict(),
                "create_time": process.create_time(),
                "cmdline": process.cmdline(),
                "username": process.username(),
                "name": process.name(),
            }

            # Add output info if available
            if pid in self.temp_files:
                try:
                    stdout_path, stderr_path = self.temp_files[pid]
                    info["current_stdout"] = self._read_temp_file(stdout_path)
                    info["current_stderr"] = self._read_temp_file(stderr_path)
                except Exception as e:
                    _log_with_context(
                        logging.ERROR,
                        "Error reading temp files for process info",
                        {"pid": pid, "error": str(e)},
                    )
                    info["current_stdout"] = ""
                    info["current_stderr"] = f"Error reading output: {str(e)}"

            return info
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            _log_with_context(
                logging.WARNING,
                "Could not get process info",
                {"pid": pid, "error": str(e)},
            )
            return None
        except Exception as e:
            _log_with_context(
                logging.ERROR,
                "Unexpected error getting process info",
                {"pid": pid, "error": str(e)},
            )
            return None

    def terminate_by_token(self, token: str) -> bool:
        """Terminate a process by its token

        Args:
            token: The token for the process to terminate

        Returns:
            True if the process was terminated successfully, False otherwise
        """
        if token not in self.process_tokens:
            _log_with_context(
                logging.WARNING,
                "Process token not found for termination",
                {"token": token},
            )
            return False

        pid = self.process_tokens[token]
        result = self.terminate_process(pid)

        if result:
            # Mark as completed with termination status
            self.completed_processes[token] = {
                "status": "terminated",
                "success": False,
                "error": "Process was terminated by request",
                "output": "",
                "pid": pid,
            }

            # Clean up tracking
            self.running_processes.pop(pid, None)

        return result

    async def query_process(
        self, token: str, wait: bool = False, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Query the status of a process and optionally wait for completion

        Args:
            token: The token for the process to query
            wait: Whether to wait for the process to complete
            timeout: Optional timeout in seconds for the wait (if wait is True)

        Returns:
            Dictionary with process status or completion information
        """
        if wait:
            _log_with_context(
                logging.INFO,
                "Querying process with wait",
                {"token": token, "timeout": timeout},
            )
            return await self.wait_for_process(token, timeout)
        else:
            _log_with_context(
                logging.INFO,
                "Querying process status without wait",
                {"token": token, "timeout": timeout},
            )
            status = await self.get_process_status(token)
            if status["status"] == "running" and g_config_sleep_when_running:
                await asyncio.sleep(timeout)
                return await self.get_process_status(token)
            else:
                return status

    async def wait_for_process(
        self, token: str, timeout: Optional[float] = None, from_monitor: bool = False
    ) -> Dict[str, Any]:
        """Wait for a process to complete and collect its output

        Args:
            token: The token returned from execute_async
            timeout: Optional timeout in seconds
            from_monitor: Whether this is called from the monitor task

        Returns:
            Dictionary with success, output, and error information
        """
        if token in self.completed_processes:
            # Process has already completed or errored
            _log_with_context(
                logging.INFO,
                "Fetching already completed process results",
                {"token": token, "from_monitor": from_monitor},
            )
            return self.completed_processes[token]

        if token not in self.process_tokens:
            # Process token not found
            error_msg = f"Process token not found: {token}"
            _log_with_context(
                logging.ERROR, error_msg, {"token": token, "from_monitor": from_monitor}
            )
            return {"status": "error", "error": error_msg, "success": False}

        # Get the process ID
        pid = self.process_tokens[token]
        if pid not in self.running_processes:
            # Process no longer running
            error_msg = f"Process not found (token: {token}, pid: {pid})"
            _log_with_context(
                logging.ERROR,
                error_msg,
                {"token": token, "pid": pid, "from_monitor": from_monitor},
            )
            return {"status": "error", "error": error_msg, "success": False}

        # Get the process object
        process = self.running_processes[pid]
        start_time = time.time()

        _log_with_context(
            logging.INFO,
            "Waiting for process completion",
            {
                "token": token,
                "pid": pid,
                "timeout": timeout,
                "from_monitor": from_monitor,
            },
        )

        try:
            # This will block until timeout or completion
            exit_code = await asyncio.get_event_loop().run_in_executor(
                None, lambda: process.wait(timeout=timeout)
            )
            end_time = time.time()
            duration = end_time - start_time

            success = exit_code == 0

            # Get output from temp files - without using the lock in the monitor function
            # to avoid deadlock where monitor is waiting for lock that's already held
            if pid in self.temp_files:
                stdout_path, stderr_path = self.temp_files[pid]

                # We don't need the lock if we're monitoring since it's a separate task
                if from_monitor:
                    stdout = self._read_temp_file(stdout_path)
                    stderr = self._read_temp_file(stderr_path)
                else:
                    # Use a lock only for the direct wait_for_process call
                    async with self.cleanup_lock:
                        stdout = self._read_temp_file(stdout_path)
                        stderr = self._read_temp_file(stderr_path)
            else:
                stdout = ""
                stderr = "Error: Output files not found"

            _log_with_context(
                logging.INFO,
                "Process wait completed",
                {
                    "token": token,
                    "pid": pid,
                    "returncode": exit_code,
                    "duration": duration,
                    "success": success,
                    "stdout_length": len(stdout),
                    "stderr_length": len(stderr),
                    "stdout_sample": stdout[:100] if stdout else "",
                    "stderr_sample": stderr[:100] if stderr else "",
                    "from_monitor": from_monitor,
                },
            )

            result = {
                "status": "completed",
                "success": success,
                "output": stdout,
                "error": stderr,
                "pid": pid,
                "returncode": exit_code,
                "duration": duration,
            }

            # Store the result for later retrieval
            self.completed_processes[token] = result

            # If this is a direct call (not from monitor), clean up
            if not from_monitor:
                # Clean up tracking
                self.running_processes.pop(pid, None)
                await self._cleanup_temp_files(pid)
            else:
                # Just signal that the monitoring task is complete
                _log_with_context(
                    logging.DEBUG,
                    "Monitor task completed without cleaning up files",
                    {"token": token, "pid": pid},
                )

            return result

        except asyncio.TimeoutError:
            # Process timed out, terminate it
            _log_with_context(
                logging.ERROR,
                "Process wait timeout",
                {
                    "token": token,
                    "pid": pid,
                    "timeout": timeout,
                    "elapsed_time": time.time() - start_time,
                    "from_monitor": from_monitor,
                },
            )

            # Terminate the process
            self.terminate_process(pid)

            # Try to collect any output so far
            try:
                if pid in self.temp_files:
                    stdout_path, stderr_path = self.temp_files[pid]
                    stdout = self._read_temp_file(stdout_path)
                    stderr = self._read_temp_file(stderr_path)
                else:
                    stdout = ""
                    stderr = "Error: Output files not found"
            except Exception as e:
                stdout, stderr = "", f"Unable to collect output after timeout: {str(e)}"

            error_message = f"Process timed out after {timeout} seconds"
            result = {
                "status": "timeout",
                "success": False,
                "error": error_message,
                "output": stdout,
                "pid": pid,
                "duration": time.time() - start_time,
            }

            # Store the result for later retrieval
            self.completed_processes[token] = result

            # If this is a direct call (not from monitor), clean up
            if not from_monitor:
                # Clean up tracking
                if pid in self.running_processes:
                    self.running_processes.pop(pid, None)
                await self._cleanup_temp_files(pid)

            return result

        except Exception as e:
            # Other error occurred
            end_time = time.time()
            _log_with_context(
                logging.ERROR,
                "Error during process wait",
                {
                    "token": token,
                    "pid": pid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration": end_time - start_time,
                    "traceback": traceback.format_exc(),
                    "from_monitor": from_monitor,
                },
            )

            # Try to collect any output so far
            try:
                if pid in self.temp_files:
                    stdout_path, stderr_path = self.temp_files[pid]
                    stdout = self._read_temp_file(stdout_path)
                    stderr = self._read_temp_file(stderr_path)
                else:
                    stdout = ""
                    stderr = "Error: Output files not found"
            except Exception as output_error:
                stdout, stderr = (
                    "",
                    f"Unable to collect output after error: {str(output_error)}",
                )

            # Ensure the process is terminated
            try:
                self.terminate_process(pid)
            except Exception as term_error:
                _log_with_context(
                    logging.WARNING,
                    "Error during termination after error",
                    {"token": token, "pid": pid, "error": str(term_error)},
                )

            error_message = f"Error waiting for process: {str(e)}"
            result = {
                "status": "error",
                "success": False,
                "error": error_message,
                "output": stdout,
                "pid": pid,
                "duration": end_time - start_time,
            }

            # Store the result for later retrieval
            self.completed_processes[token] = result

            # If this is a direct call (not from monitor), clean up
            if not from_monitor:
                # Clean up tracking
                if pid in self.running_processes:
                    self.running_processes.pop(pid, None)
                await self._cleanup_temp_files(pid)

            return result
