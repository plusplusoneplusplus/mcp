import platform
import subprocess
import asyncio
import uuid
from typing import Dict, Any, List, Optional, Union, Callable, Awaitable
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
from collections import OrderedDict

# Import the interface
from mcp_tools.interfaces import CommandExecutorInterface
from mcp_tools.plugin import register_tool

# Import config manager
from config import env_manager

# Type alias for progress callback
ProgressCallback = Callable[[float, Optional[float], Optional[str]], Awaitable[None]]

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


@register_tool()
class CommandExecutor(CommandExecutorInterface):
    """Command executor that can run processes synchronously or asynchronously,
    using temporary files for stdout/stderr capture.

    Example:
        # Synchronous execution
        executor = CommandExecutor()
        result = executor.execute("ls -la")

        # Asynchronous execution
        async def run_command():
            executor = CommandExecutor()

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

    # Implement ToolInterface properties
    @property
    def name(self) -> str:
        """Get the tool name."""
        return "command_executor"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Execute shell commands synchronously or asynchronously"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to execute"},
                "timeout": {
                    "type": "number",
                    "description": "Optional timeout in seconds",
                    "nullable": True,
                },
            },
            "required": ["command"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments.

        Args:
            arguments: Dictionary of arguments for the tool

        Returns:
            Tool execution result
        """
        command = arguments.get("command", "")
        timeout = arguments.get("timeout")

        return self.execute(command, timeout)

    def __init__(self, temp_dir: Optional[str] = None):
        self.os_type = platform.system().lower()
        self.running_processes = {}
        self.process_tokens = {}  # Maps tokens to process IDs
        self.temp_files = {}  # Maps PIDs to (stdout_file, stderr_file) tuples
        self.cleanup_lock = asyncio.Lock()  # Lock to protect temp file operations

        # Note: completed_processes cache removed in Phase 3 migration
        # MCP progress notifications eliminate need for result caching

        # Periodic status reporting attributes
        self.status_reporter_task: Optional[asyncio.Task] = None

        # Load configuration from config manager
        env_manager.load()
        self.status_reporter_enabled = env_manager.get_setting(
            "periodic_status_enabled", False
        )
        self.status_reporter_interval = env_manager.get_setting(
            "periodic_status_interval", 30.0
        )
        self.status_reporter_max_command_length = env_manager.get_setting(
            "periodic_status_max_command_length", 60
        )

        # Note: Job history persistence removed in Phase 3 migration
        # MCP progress notifications provide real-time updates without caching

        # Use specified temp dir or system default
        self.temp_dir = temp_dir if temp_dir else tempfile.gettempdir()

        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)

        _log_with_context(
            logging.INFO,
            "Initialized CommandExecutor",
            {
                "temp_dir": self.temp_dir,
                "os_type": self.os_type,
            },
        )

        # Note: Auto-cleanup and persistence removed in Phase 3

    def _enforce_completed_process_limit(self) -> None:
        """No-op: completed_processes cache removed in Phase 3."""
        pass

    def _cleanup_expired_processes(self) -> int:
        """No-op: completed_processes cache removed in Phase 3."""
        return 0

    async def _periodic_cleanup_task(self) -> None:
        """Background task that periodically cleans up expired completed processes."""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)

                try:
                    cleanup_count = self._cleanup_expired_processes()

                    if cleanup_count > 0:
                        _log_with_context(
                            logging.INFO,
                            "Periodic cleanup completed",
                            {
                                "cleaned_processes": cleanup_count,
                                "remaining_processes": 0  # Cache removed
                            }
                        )
                        # _persist_completed_processes() - removed

                except Exception as e:
                    _log_with_context(
                        logging.ERROR,
                        "Error during periodic cleanup",
                        {"error": str(e), "traceback": traceback.format_exc()}
                    )

        except asyncio.CancelledError:
            _log_with_context(
                logging.INFO,
                "Periodic cleanup task cancelled",
                {"cleanup_interval": self.cleanup_interval}
            )
            raise
        except Exception as e:
            _log_with_context(
                logging.ERROR,
                "Error in periodic cleanup task",
                {"error": str(e), "traceback": traceback.format_exc()}
            )

    def start_cleanup_task(self) -> None:
        """No-op: cleanup task removed in Phase 3."""
        pass

    def stop_cleanup_task(self) -> None:
        """No-op: cleanup task removed in Phase 3."""
        pass

    def _ensure_cleanup_task_running(self) -> None:
        """No-op: auto cleanup removed in Phase 3."""
        pass

    def cleanup_completed_processes(self, force_all: bool = False) -> Dict[str, Any]:
        """No-op: completed_processes cache removed in Phase 3."""
        return {
            "initial_count": 0,
            "cleaned_count": 0,
            "remaining_count": 0,
            "force_all": force_all
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """No-op: completed_processes cache removed in Phase 3."""
        return {
            "completed_processes_count": 0,
            "note": "Completed processes cache removed in Phase 3 migration"
        }

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

    def _persist_completed_processes(self) -> None:
        """No-op: job history persistence removed in Phase 3."""
        pass

    def _load_persisted_history(self) -> None:
        """No-op: job history persistence removed in Phase 3."""
        pass

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

                # Remove the temp files entry
                del self.temp_files[pid]

    def _prepare_redirected_command(
        self, command: str, stdout_path: str, stderr_path: str
    ) -> str:
        """Prepare a command with output redirection

        Args:
            command: The command to execute
            stdout_path: Path to redirect stdout to
            stderr_path: Path to redirect stderr to

        Returns:
            Modified command with redirection
        """
        if self.os_type == "windows":
            # Windows - using cmd.exe
            return f'cmd.exe /c "{command} > "{stdout_path}" 2> "{stderr_path}""'
        else:
            # Unix/Linux/macOS
            return f'{command} > "{stdout_path}" 2> "{stderr_path}"'

    def execute(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Execute a command synchronously

        Args:
            command: The command to execute
            timeout: Optional timeout in seconds

        Returns:
            Dictionary with execution results
        """
        # Create temporary files for output capture
        stdout_path, stderr_path, stdout_file, stderr_file = self._create_temp_files()
        start_time = time.time()

        try:
            _log_with_context(
                logging.INFO,
                f"Executing command synchronously",
                {"command": command, "timeout": timeout},
            )

            # Prepare the command with output redirection
            redirected_command = self._prepare_redirected_command(
                command, stdout_path, stderr_path
            )

            # Close the files - they'll be written to by the subprocess
            stdout_file.close()
            stderr_file.close()

            # Execute the command
            if self.os_type == "windows":
                # On Windows, use shell=True to interpret the redirections
                process = subprocess.run(
                    redirected_command, shell=True, timeout=timeout, check=False
                )
            else:
                # On Unix, use a list of arguments and shell=True
                process = subprocess.run(
                    redirected_command, shell=True, timeout=timeout, check=False
                )

            # Read output from temp files
            stdout_content = self._read_temp_file(stdout_path)
            stderr_content = self._read_temp_file(stderr_path)

            _log_with_context(
                logging.INFO,
                f"Command completed synchronously",
                {
                    "command": command,
                    "return_code": process.returncode,
                    "stdout_length": len(stdout_content),
                    "stderr_length": len(stderr_content),
                },
            )

            # Return the result
            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "output": stdout_content,
                "error": stderr_content,
                "pid": os.getpid(),  # Adding the current process PID
                "duration": time.time() - start_time,
            }

        except subprocess.TimeoutExpired:
            _log_with_context(
                logging.WARNING,
                f"Command timed out after {timeout} seconds",
                {"command": command},
            )

            # Read any partial output
            stdout_content = self._read_temp_file(stdout_path)
            stderr_content = self._read_temp_file(stderr_path)

            return {
                "success": False,
                "return_code": -1,
                "output": stdout_content,
                "error": f"Command timed out after {timeout} seconds\n{stderr_content}",
                "pid": os.getpid(),  # Adding the current process PID
                "duration": time.time() - start_time,
            }

        except Exception as e:
            _log_with_context(
                logging.ERROR,
                f"Error executing command",
                {
                    "command": command,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )

            return {
                "success": False,
                "return_code": -1,
                "output": "",
                "error": f"Error executing command: {str(e)}",
                "pid": os.getpid(),  # Adding the current process PID
                "duration": time.time() - start_time,
            }

        finally:
            # Clean up temp files
            try:
                if os.path.exists(stdout_path):
                    os.remove(stdout_path)
                if os.path.exists(stderr_path):
                    os.remove(stderr_path)
            except Exception as e:
                _log_with_context(
                    logging.WARNING, f"Error cleaning up temp files", {"error": str(e)}
                )

    async def _monitor_async_process(
        self, token: str, timeout: Optional[float] = None
    ) -> None:
        """Monitor an asynchronous process until completion

        Args:
            token: Process token to monitor
            timeout: Optional timeout in seconds
        """
        if token not in self.process_tokens:
            _log_with_context(
                logging.WARNING,
                f"Monitor task: Process token not found: {token}",
                {"token": token},
            )
            return

        pid = self.process_tokens[token]
        if pid not in self.running_processes:
            _log_with_context(
                logging.WARNING,
                f"Monitor task: Process PID not found: {pid}",
                {"token": token, "pid": pid},
            )
            return

        process = self.running_processes[pid]["process"]

        _log_with_context(
            logging.INFO,
            f"Monitor task: Started monitoring process",
            {"token": token, "pid": pid},
        )

        # Wait for the process to complete
        start_time = time.time()
        try:
            await asyncio.wait_for(process.wait(), timeout)

            _log_with_context(
                logging.INFO,
                f"Monitor task: Process completed normally",
                {"token": token, "pid": pid, "returncode": process.returncode},
            )

        except asyncio.TimeoutError:
            # Process didn't complete within timeout
            _log_with_context(
                logging.WARNING,
                f"Monitor task: Process timeout after {timeout} seconds",
                {"token": token, "pid": pid},
            )

            # Try to terminate the process
            self.terminate_process(pid)

            # Update status
            await self.wait_for_process(
                token, timeout=5, from_monitor=True
            )  # Short additional wait

        except Exception as e:
            _log_with_context(
                logging.ERROR,
                f"Monitor task: Error monitoring process",
                {"token": token, "pid": pid, "error": str(e)},
            )

            # Try to clean up
            await self.wait_for_process(token, timeout=5, from_monitor=True)

    async def _monitor_process_with_progress(self, pid: int) -> None:
        """Monitor process and send periodic MCP progress notifications.

        Args:
            pid: Process ID to monitor
        """
        try:
            process_data = self.running_processes.get(pid)
            if not process_data:
                return

            callback = process_data.get("progress_callback")
            if not callback:
                return  # No MCP progress requested

            start_time = process_data["start_time"]
            command = process_data["command"]
            update_interval = 5  # Send update every 5 seconds

            while pid in self.running_processes:
                runtime = time.time() - start_time

                # Get process metrics if available
                try:
                    proc = psutil.Process(pid)
                    cpu_percent = proc.cpu_percent(interval=0.1)
                    memory_mb = proc.memory_info().rss / 1024 / 1024
                    message = f"Running for {runtime:.1f}s | CPU: {cpu_percent:.1f}% | Memory: {memory_mb:.1f}MB"
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    message = f"Running for {runtime:.1f}s"

                # Send progress (use runtime as progress indicator)
                try:
                    await callback(
                        progress=runtime,
                        total=None,  # Unknown total for command execution
                        message=message
                    )
                except Exception as e:
                    _log_with_context(
                        logging.ERROR,
                        "Error sending progress notification",
                        {"pid": pid, "error": str(e)}
                    )

                await asyncio.sleep(update_interval)

        except Exception as e:
            _log_with_context(
                logging.ERROR,
                f"Error monitoring process {pid}",
                {"pid": pid, "error": str(e)}
            )

    async def execute_async(
        self,
        command: str,
        timeout: Optional[float] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Dict[str, Any]:
        """Execute a command asynchronously with optional progress notifications.

        Args:
            command: The command to execute
            timeout: Optional timeout in seconds (for process completion)
            progress_callback: Optional callback for MCP progress notifications
                Signature: async def callback(progress: float, total: Optional[float], message: Optional[str])

        Returns:
            Dictionary with process token and initial status
        """
        # Ensure cleanup task is running
        self._ensure_cleanup_task_running()

        # Create temporary files for output capture
        stdout_path, stderr_path, stdout_file, stderr_file = self._create_temp_files()

        try:
            # Generate a unique token for this process
            token = str(uuid.uuid4())

            _log_with_context(
                logging.INFO,
                f"Starting async command",
                {"command": command, "token": token},
            )

            # Prepare the command with output redirection
            redirected_command = self._prepare_redirected_command(
                command, stdout_path, stderr_path
            )

            # Close the files - they'll be written to by the subprocess
            stdout_file.close()
            stderr_file.close()

            # Start the process
            if self.os_type == "windows":
                # On Windows, use shell=True to interpret the redirections
                process = await asyncio.create_subprocess_shell(
                    redirected_command,
                    stdout=None,  # Already redirected in the command
                    stderr=None,  # Already redirected in the command
                )
            else:
                # On Unix, use a list of arguments
                process = await asyncio.create_subprocess_shell(
                    redirected_command,
                    stdout=None,  # Already redirected in the command
                    stderr=None,  # Already redirected in the command
                )

            # Store the process and associate it with the token
            pid = process.pid
            self.process_tokens[token] = pid
            self.running_processes[pid] = {
                "process": process,
                "command": command,
                "stdout_path": stdout_path,
                "stderr_path": stderr_path,
                "token": token,
                "start_time": time.time(),
                "terminated": False,  # Initialize terminated flag
                "progress_callback": progress_callback,  # Store progress callback
            }

            # Store temp file locations for cleanup
            self.temp_files[pid] = (stdout_path, stderr_path)

            _log_with_context(
                logging.INFO,
                f"Started async command",
                {"command": command, "token": token, "pid": pid},
            )

            # Send initial progress if callback provided
            if progress_callback:
                try:
                    await progress_callback(0, None, f"Started: {command}")
                except Exception as e:
                    _log_with_context(
                        logging.ERROR,
                        "Failed to send initial progress notification",
                        {"error": str(e), "token": token}
                    )

                # Start progress monitoring task
                asyncio.create_task(self._monitor_process_with_progress(pid))

            # Start a task to monitor the process if timeout is specified
            if timeout:
                asyncio.create_task(self._monitor_async_process(token, timeout))

            # Return the token and initial status
            return {"token": token, "status": "running", "pid": pid}

        except Exception as e:
            _log_with_context(
                logging.ERROR,
                f"Error starting async command",
                {
                    "command": command,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )

            # Clean up temp files
            try:
                if os.path.exists(stdout_path):
                    os.remove(stdout_path)
                if os.path.exists(stderr_path):
                    os.remove(stderr_path)
            except Exception as cleanup_error:
                _log_with_context(
                    logging.WARNING,
                    f"Error cleaning up temp files after failed start",
                    {"error": str(cleanup_error)},
                )

            return {
                "token": "error",
                "status": "error",
                "error": f"Error starting command: {str(e)}",
            }

    def _merge_psutil_info(self, status_info: Dict[str, Any], process_info: Optional[Dict[str, Any]]) -> None:
        """Merge psutil process info while preserving logical status.

        Args:
            status_info: The status dictionary to update
            process_info: Optional psutil process information
        """
        # Add psutil info if available, but preserve logical status
        if process_info:
            # Extract OS status before updating to avoid overwriting logical status
            os_status = process_info.pop("status", None)
            status_info.update(process_info)
            # Add OS status as separate field
            if os_status:
                status_info["os_status"] = os_status

    async def get_process_status(self, token: str) -> Dict[str, Any]:
        """DEPRECATED: Use MCP progress notifications instead of polling.

        Args:
            token: Process token to check

        Returns:
            Dictionary with process status information (running processes only)
        """
        # Only check running processes - completed process cache removed
        if token not in self.process_tokens:
            return {
                "status": "not_found",
                "error": f"Process with token {token} not found or already completed",
                "_deprecated": "Use MCP progress notifications instead of polling"
            }

        pid = self.process_tokens[token]
        if pid not in self.running_processes:
            return {
                "status": "not_found",
                "error": "Process not found in running processes",
                "_deprecated": "Use MCP progress notifications instead of polling"
            }

        process_data = self.running_processes[pid]
        process = process_data["process"]

        # If completed, wait for final result
        if process.returncode is not None:
            return await self.wait_for_process(token)

        # Still running
        process_info = self.get_process_info(pid)
        status_info = {
            "status": "running",
            "pid": pid,
            "token": token,
            "command": process_data["command"],
            "runtime": time.time() - process_data["start_time"],
            "_deprecated": "Use MCP progress notifications instead of polling"
        }

        self._merge_psutil_info(status_info, process_info)
        return status_info

    def get_allowed_commands(self) -> List[str]:
        """Get list of allowed commands (for security/filtering)"""
        # Implement command allowlisting if needed
        return []

    def terminate_process(self, pid: int) -> bool:
        """Terminate a running process by PID

        Args:
            pid: Process ID to terminate

        Returns:
            True if termination was successful, False otherwise
        """
        if pid not in self.running_processes:
            _log_with_context(
                logging.WARNING,
                f"Cannot terminate: Process PID not found: {pid}",
                {"pid": pid},
            )
            return False

        process_data = self.running_processes[pid]
        process = process_data["process"]

        # Process already exited
        if process.returncode is not None:
            _log_with_context(
                logging.INFO,
                f"Process already completed, no need to terminate",
                {"pid": pid, "returncode": process.returncode},
            )
            return True

        _log_with_context(
            logging.INFO,
            f"Terminating process",
            {"pid": pid, "command": process_data["command"]},
        )

        try:
            # Add terminated flag to process data
            process_data["terminated"] = True

            # Try to terminate gracefully first
            process.terminate()

            # For Windows, no additional steps needed
            # For Unix, we need to create a process group if we want to kill child processes too
            # This requires changes at process creation time

            _log_with_context(
                logging.INFO, f"Sent termination signal to process", {"pid": pid}
            )

            return True

        except Exception as e:
            _log_with_context(
                logging.ERROR,
                f"Error terminating process",
                {"pid": pid, "error": str(e)},
            )
            return False

    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Get detailed process information using psutil

        Args:
            pid: Process ID to get information for

        Returns:
            Dictionary with process information or None if not available
        """
        try:
            # Attempt to get process via psutil
            p = psutil.Process(pid)

            # Basic process info
            info = {
                "create_time": p.create_time(),
                "username": p.username(),
                "status": p.status(),
                "pid": pid,  # Add the pid to the returned info dictionary
            }

            # Add CPU and memory usage if possible
            try:
                info["cpu_percent"] = p.cpu_percent(interval=0.1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            try:
                mem = p.memory_info()
                info["memory_info"] = {
                    "rss": mem.rss,  # Resident Set Size
                    "vms": mem.vms,  # Virtual Memory Size
                    "rss_mb": mem.rss / (1024 * 1024),  # RSS in MB
                    "vms_mb": mem.vms / (1024 * 1024),  # VMS in MB
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # Add io counters if possible
            try:
                io = p.io_counters()
                info["io_counters"] = {
                    "read_count": io.read_count,
                    "write_count": io.write_count,
                    "read_bytes": io.read_bytes,
                    "write_bytes": io.write_bytes,
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                pass

            # Add children count if possible
            try:
                info["num_children"] = len(p.children())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            return info

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Process no longer exists or can't be accessed
            return None
        except Exception as e:
            _log_with_context(
                logging.ERROR,
                f"Error getting process info",
                {"pid": pid, "error": str(e)},
            )
            return None

    def terminate_by_token(self, token: str) -> bool:
        """Terminate a running process by token

        Args:
            token: Process token to terminate

        Returns:
            True if termination was successful, False otherwise
        """
        # Check if the token exists
        if token not in self.process_tokens:
            # Note: completed_processes cache removed - token not found
            _log_with_context(
                logging.WARNING,
                f"Process token not found, may be already completed",
                {"token": token},
            )
            return False

        # Get the process ID and terminate
        pid = self.process_tokens[token]
        result = self.terminate_process(pid)

        if result:
            _log_with_context(
                logging.INFO,
                f"Successfully terminated process by token",
                {"token": token, "pid": pid},
            )
        else:
            _log_with_context(
                logging.WARNING,
                f"Failed to terminate process by token",
                {"token": token, "pid": pid},
            )

        return result

    async def query_process(
        self, token: str, wait: bool = False, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Query a process status or wait for completion

        Args:
            token: Process token to query
            wait: Whether to wait for process completion
            timeout: Optional timeout in seconds if waiting

        Returns:
            Dictionary with process status or final result
        """
        if not wait:
            # Just return current status without waiting
            return await self.get_process_status(token)

        # Wait for the process to complete with timeout
        return await self.wait_for_process(token, timeout)

    async def wait_for_process(
        self, token: str, timeout: Optional[float] = None, from_monitor: bool = False
    ) -> Dict[str, Any]:
        """Wait for a process to complete

        Args:
            token: Process token to wait for
            timeout: Optional timeout in seconds
            from_monitor: Whether this is called from the monitor task

        Returns:
            Dictionary with final process result
        """
        # Note: completed_processes cache removed in Phase 3
        # Results are now returned directly without caching

        # Check if the token exists
        if token not in self.process_tokens:
            _log_with_context(
                logging.WARNING,
                f"Wait process: Process token not found: {token}",
                {"token": token},
            )
            return {
                "status": "not_found",
                "error": f"Process with token {token} not found",
            }

        # Get the process ID
        pid = self.process_tokens[token]

        # Check if the process exists in running processes
        if pid not in self.running_processes:
            _log_with_context(
                logging.WARNING,
                f"Wait process: Process PID not found in running processes: {pid}",
                {"token": token, "pid": pid},
            )
            return {
                "status": "unknown",
                "error": f"Process with PID {pid} not found in running processes",
            }

        process_data = self.running_processes[pid]
        process = process_data["process"]
        stdout_path = process_data["stdout_path"]
        stderr_path = process_data["stderr_path"]

        # Check if already completed
        if process.returncode is not None:
            # Already completed
            _log_with_context(
                logging.INFO,
                f"Wait process: Process already completed",
                {"token": token, "pid": pid, "returncode": process.returncode},
            )
        else:
            # Not completed yet, wait with timeout
            try:
                _log_with_context(
                    logging.INFO,
                    f"Wait process: Waiting for process to complete",
                    {"token": token, "pid": pid, "timeout": timeout},
                )

                # Wait for the process to complete
                await asyncio.wait_for(process.wait(), timeout)

                _log_with_context(
                    logging.INFO,
                    f"Wait process: Process completed after waiting",
                    {"token": token, "pid": pid, "returncode": process.returncode},
                )

            except asyncio.TimeoutError:
                # Process didn't complete within timeout
                _log_with_context(
                    logging.WARNING,
                    f"Wait process: Timeout waiting for process after {timeout} seconds",
                    {"token": token, "pid": pid},
                )

                return {
                    "status": "timeout",
                    "pid": pid,
                    "error": f"Timeout waiting for process after {timeout} seconds",
                }

            except Exception as e:
                # Error waiting for process
                _log_with_context(
                    logging.ERROR,
                    f"Wait process: Error waiting for process",
                    {"token": token, "pid": pid, "error": str(e)},
                )

                return {
                    "status": "error",
                    "pid": pid,
                    "error": f"Error waiting for process: {str(e)}",
                }

        # Process completed, read output
        returncode = process.returncode
        stdout_content = self._read_temp_file(stdout_path)
        stderr_content = self._read_temp_file(stderr_path)

        # Send final progress notification if callback exists
        callback = process_data.get("progress_callback")
        if callback:
            duration = time.time() - process_data.get("start_time", time.time())
            status = "completed successfully" if returncode == 0 else f"failed with code {returncode}"
            try:
                await callback(
                    progress=duration,
                    total=duration,
                    message=f"Process {status} in {duration:.1f}s"
                )
            except Exception as e:
                _log_with_context(
                    logging.ERROR,
                    "Failed to send final progress notification",
                    {"token": token, "error": str(e)}
                )

        # Clean up process and temp files
        del self.running_processes[pid]
        del self.process_tokens[token]

        # Clean up temp files if not called from monitor
        if not from_monitor:
            await self._cleanup_temp_files(pid)

        # Prepare result
        result = {
            "status": "completed",
            "success": returncode == 0,
            "return_code": returncode,
            "output": stdout_content,
            "error": stderr_content,
            "pid": pid,
            "start_time": process_data.get("start_time"),  # Preserve start time for completed jobs
            "duration": time.time() - process_data.get("start_time", time.time()),
        }

        # If process was terminated, update status
        if "terminated" in process_data and process_data["terminated"]:
            result["status"] = "terminated"

        # Note: Caching and persistence removed in Phase 3
        # Results are returned directly without caching

        _log_with_context(
            logging.INFO,
            f"Wait process: Returning final result",
            {
                "token": token,
                "pid": pid,
                "returncode": returncode,
                "stdout_length": len(stdout_content),
                "stderr_length": len(stderr_content),
            },
        )

        return result

    def list_running_processes(self) -> List[Dict[str, Any]]:
        """List all currently running background processes.

        Returns:
            List of dictionaries containing process information
        """
        running_processes = []

        for pid, process_data in self.running_processes.items():
            process = process_data["process"]

            # Skip completed processes
            if process.returncode is not None:
                continue

            # Get basic process info
            process_info = {
                "token": process_data["token"][:8],  # First 8 characters
                "pid": pid,
                "command": process_data["command"],
                "runtime": time.time() - process_data["start_time"],
                "status": "running",
            }

            # Get additional process info if available
            detailed_info = self.get_process_info(pid)
            if detailed_info:
                process_info.update(
                    {
                        "cpu_percent": detailed_info.get("cpu_percent", 0.0),
                        "memory_mb": detailed_info.get("memory_info", {}).get(
                            "rss_mb", 0.0
                        ),
                        "status": detailed_info.get("status", "running"),
                    }
                )

            running_processes.append(process_info)

        return running_processes

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _truncate_command(self, command: str, max_length: int = None) -> str:
        """Truncate command string if it's too long.

        Args:
            command: Command string to truncate
            max_length: Maximum length (uses instance setting if None)

        Returns:
            Truncated command string
        """
        if max_length is None:
            max_length = self.status_reporter_max_command_length

        if len(command) <= max_length:
            return command
        return command[: max_length - 3] + "..."

    def _print_status_report(self) -> None:
        """Print a status report of running processes to stdout."""
        running_processes = self.list_running_processes()

        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Print header
        print(
            f"[{timestamp}] Background Jobs Status ({len(running_processes)} running):"
        )

        if not running_processes:
            print("  No background processes currently running.")
            return

        # Print each process
        for process_info in running_processes:
            token = process_info["token"]
            pid = process_info["pid"]
            runtime = self._format_duration(process_info["runtime"])
            status = process_info["status"]
            command = self._truncate_command(process_info["command"])
            cpu_percent = process_info.get("cpu_percent", 0.0)
            memory_mb = process_info.get("memory_mb", 0.0)

            print(
                f"  Token: {token} | PID: {pid} | Runtime: {runtime} | Status: {status}"
            )
            print(f"    Command: {command}")
            print(f"    CPU: {cpu_percent:.1f}% | Memory: {memory_mb:.1f}MB")
            print()

    async def _periodic_status_reporter(self) -> None:
        """Background task that periodically prints status reports."""
        try:
            while True:
                await asyncio.sleep(self.status_reporter_interval)

                # Only print if there are running processes
                if self.running_processes:
                    self._print_status_report()

        except asyncio.CancelledError:
            _log_with_context(
                logging.INFO,
                "Periodic status reporter task cancelled",
                {"interval": self.status_reporter_interval},
            )
            raise
        except Exception as e:
            _log_with_context(
                logging.ERROR,
                "Error in periodic status reporter",
                {"error": str(e), "traceback": traceback.format_exc()},
            )

    async def start_periodic_status_reporter(
        self, interval: float = 30.0, enabled: bool = True
    ) -> None:
        """Start periodic status reporting for running processes.

        Args:
            interval: Time interval between status reports in seconds
            enabled: Whether to enable periodic reporting
        """
        if not enabled:
            _log_with_context(
                logging.INFO, "Periodic status reporter disabled", {"enabled": enabled}
            )
            return

        # Stop existing reporter if running
        await self.stop_periodic_status_reporter()

        # Update settings
        self.status_reporter_interval = interval
        self.status_reporter_enabled = enabled

        # Start new reporter task
        self.status_reporter_task = asyncio.create_task(
            self._periodic_status_reporter()
        )

        _log_with_context(
            logging.INFO,
            "Started periodic status reporter",
            {"interval": interval, "enabled": enabled},
        )

    async def stop_periodic_status_reporter(self) -> None:
        """Stop periodic status reporting."""
        if self.status_reporter_task and not self.status_reporter_task.done():
            self.status_reporter_task.cancel()
            try:
                await self.status_reporter_task
            except asyncio.CancelledError:
                pass

        self.status_reporter_task = None
        self.status_reporter_enabled = False

        _log_with_context(logging.INFO, "Stopped periodic status reporter", {})
