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
from collections import OrderedDict

# Import the interface
from mcp_tools.interfaces import CommandExecutorInterface
from mcp_tools.plugin import register_tool

# Import config manager
from config import env_manager

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


@register_tool(os="all")
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

        # Memory management for completed processes - using OrderedDict for LRU behavior
        self.completed_processes = OrderedDict()  # Store results of completed processes
        self.completed_process_timestamps = {}  # Track completion timestamps for TTL

        # Periodic status reporting attributes
        self.status_reporter_task: Optional[asyncio.Task] = None

        # Background cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None

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

        # Job history persistence settings
        self.job_history_persistence_enabled = env_manager.get_setting(
            "job_history_persistence_enabled", False
        )
        self.job_history_storage_backend = env_manager.get_setting(
            "job_history_storage_backend", "json"
        )
        self.job_history_storage_path = Path(
            env_manager.get_setting("job_history_storage_path", ".job_history.json")
        )
        self.job_history_max_entries = env_manager.get_setting(
            "job_history_max_entries", 1000
        )
        self.job_history_max_age_days = env_manager.get_setting(
            "job_history_max_age_days", 30
        )

        # Memory management settings with defaults
        self.max_completed_processes = env_manager.get_setting(
            "command_executor_max_completed_processes", 100
        )
        self.completed_process_ttl = env_manager.get_setting(
            "command_executor_completed_process_ttl", 3600  # 1 hour default
        )
        self.auto_cleanup_enabled = env_manager.get_setting(
            "command_executor_auto_cleanup_enabled", True
        )
        self.cleanup_interval = env_manager.get_setting(
            "command_executor_cleanup_interval", 300  # 5 minutes default
        )

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
                "max_completed_processes": self.max_completed_processes,
                "completed_process_ttl": self.completed_process_ttl,
                "auto_cleanup_enabled": self.auto_cleanup_enabled,
                "cleanup_interval": self.cleanup_interval
            },
        )

        if self.job_history_persistence_enabled:
            self._load_persisted_history()

        # Start cleanup task if enabled
        if self.auto_cleanup_enabled:
            self.start_cleanup_task()

    def __del__(self):
        """Cleanup when the CommandExecutor is destroyed."""
        try:
            self.stop_cleanup_task()
        except Exception:
            # Ignore errors during cleanup
            pass

    def _enforce_completed_process_limit(self) -> None:
        """Enforce the maximum number of completed processes using LRU eviction.

        This method removes the oldest completed processes when the limit would be exceeded.
        """
        # Remove processes if we exceed the limit
        while len(self.completed_processes) > self.max_completed_processes:
            # Remove the oldest item (FIFO/LRU behavior with OrderedDict)
            oldest_token, oldest_result = self.completed_processes.popitem(last=False)

            # Also remove from timestamps
            if oldest_token in self.completed_process_timestamps:
                del self.completed_process_timestamps[oldest_token]

            _log_with_context(
                logging.DEBUG,
                "Evicted oldest completed process due to limit",
                {
                    "evicted_token": oldest_token[:8],
                    "current_count": len(self.completed_processes),
                    "max_limit": self.max_completed_processes
                }
            )

    def _cleanup_expired_processes(self) -> int:
        """Clean up completed processes that have exceeded their TTL.

        Returns:
            Number of processes cleaned up
        """
        if self.completed_process_ttl <= 0:
            return 0

        current_time = time.time()
        expired_tokens = []

        # Find expired processes
        for token, timestamp in self.completed_process_timestamps.items():
            if current_time - timestamp > self.completed_process_ttl:
                expired_tokens.append(token)

        # Remove expired processes
        cleanup_count = 0
        for token in expired_tokens:
            if token in self.completed_processes:
                del self.completed_processes[token]
                cleanup_count += 1
            if token in self.completed_process_timestamps:
                del self.completed_process_timestamps[token]

        if cleanup_count > 0:
            _log_with_context(
                logging.DEBUG,
                "Cleaned up expired completed processes",
                {
                    "cleanup_count": cleanup_count,
                    "ttl_seconds": self.completed_process_ttl,
                    "remaining_count": len(self.completed_processes)
                }
            )
            self._persist_completed_processes()

        return cleanup_count

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
                                "remaining_processes": len(self.completed_processes)
                            }
                        )
                        self._persist_completed_processes()

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
        """Start the background cleanup task."""
        if not self.auto_cleanup_enabled:
            return

        # Stop existing task if running
        self.stop_cleanup_task()

        # Only start task if there's a running event loop
        try:
            loop = asyncio.get_running_loop()
            # Start new cleanup task
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup_task())

            _log_with_context(
                logging.INFO,
                "Started background cleanup task",
                {
                    "cleanup_interval": self.cleanup_interval,
                    "ttl_seconds": self.completed_process_ttl,
                    "max_processes": self.max_completed_processes
                }
            )
        except RuntimeError:
            # No event loop running, defer task creation
            _log_with_context(
                logging.DEBUG,
                "No event loop running, deferring cleanup task creation",
                {"auto_cleanup_enabled": self.auto_cleanup_enabled}
            )

    def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self.cleanup_task and not self.cleanup_task.done():
            try:
                self.cleanup_task.cancel()
            except RuntimeError:
                # Event loop might be closed, ignore the error
                pass
            self.cleanup_task = None

        _log_with_context(
            logging.INFO,
            "Stopped background cleanup task",
            {}
        )

    def _ensure_cleanup_task_running(self) -> None:
        """Ensure the cleanup task is running if auto cleanup is enabled."""
        if (self.auto_cleanup_enabled and
            (self.cleanup_task is None or self.cleanup_task.done())):
            try:
                loop = asyncio.get_running_loop()
                self.start_cleanup_task()
            except RuntimeError:
                # No event loop running, can't start task
                pass

    def cleanup_completed_processes(self, force_all: bool = False) -> Dict[str, Any]:
        """Manually clean up completed processes.

        Args:
            force_all: If True, remove all completed processes regardless of TTL

        Returns:
            Dictionary with cleanup statistics
        """
        initial_count = len(self.completed_processes)

        if force_all:
            # Clear all completed processes
            self.completed_processes.clear()
            self.completed_process_timestamps.clear()
            cleanup_count = initial_count

            _log_with_context(
                logging.INFO,
                "Force cleaned all completed processes",
                {"cleaned_count": cleanup_count}
            )
        else:
            # Clean up expired processes only
            cleanup_count = self._cleanup_expired_processes()

            # Also enforce the limit
            self._enforce_completed_process_limit()

        if cleanup_count > 0:
            self._persist_completed_processes()

        return {
            "initial_count": initial_count,
            "cleaned_count": cleanup_count,
            "remaining_count": len(self.completed_processes),
            "force_all": force_all
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory usage statistics for completed processes.

        Returns:
            Dictionary with memory statistics
        """
        current_time = time.time()

        # Calculate age statistics
        ages = []
        for timestamp in self.completed_process_timestamps.values():
            ages.append(current_time - timestamp)

        stats = {
            "completed_processes_count": len(self.completed_processes),
            "max_completed_processes": self.max_completed_processes,
            "completed_process_ttl": self.completed_process_ttl,
            "auto_cleanup_enabled": self.auto_cleanup_enabled,
            "cleanup_interval": self.cleanup_interval,
        }

        if ages:
            stats.update({
                "oldest_process_age": max(ages),
                "newest_process_age": min(ages),
                "average_process_age": sum(ages) / len(ages)
            })

        return stats

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
        """Persist completed processes to storage if enabled."""
        if not self.job_history_persistence_enabled:
            return

        try:
            self.job_history_storage_path.parent.mkdir(parents=True, exist_ok=True)
            entries = []
            now = time.time()
            max_age = self.job_history_max_age_days * 86400
            for token, result in self.completed_processes.items():
                ts = self.completed_process_timestamps.get(token, now)
                if self.job_history_max_age_days > 0 and now - ts > max_age:
                    continue
                entries.append({"token": token, "result": result, "timestamp": ts})

            if self.job_history_max_entries > 0:
                entries = entries[-self.job_history_max_entries :]
            with open(self.job_history_storage_path, "w", encoding="utf-8") as f:
                json.dump(entries, f)
        except Exception as e:
            _log_with_context(
                logging.WARNING,
                "Failed to persist job history",
                {"error": str(e), "path": str(self.job_history_storage_path)},
            )

    def _load_persisted_history(self) -> None:
        """Load persisted job history from storage."""
        if not self.job_history_persistence_enabled:
            return

        try:
            if self.job_history_storage_path.exists():
                with open(self.job_history_storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                now = time.time()
                max_age = self.job_history_max_age_days * 86400
                for entry in data:
                    token = entry.get("token")
                    result = entry.get("result")
                    timestamp = entry.get("timestamp", now)
                    if not token or not result:
                        continue
                    if self.job_history_max_age_days > 0 and now - timestamp > max_age:
                        continue
                    self.completed_processes[token] = result
                    self.completed_process_timestamps[token] = timestamp

                self._enforce_completed_process_limit()
                self._cleanup_expired_processes()
        except Exception as e:
            _log_with_context(
                logging.WARNING,
                "Failed to load persisted job history",
                {"error": str(e), "path": str(self.job_history_storage_path)},
            )

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

    async def execute_async(
        self, command: str, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute a command asynchronously

        Args:
            command: The command to execute
            timeout: Optional timeout in seconds (for process completion)

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
            }

            # Store temp file locations for cleanup
            self.temp_files[pid] = (stdout_path, stderr_path)

            _log_with_context(
                logging.INFO,
                f"Started async command",
                {"command": command, "token": token, "pid": pid},
            )

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
        """Get the status of an asynchronous process

        Args:
            token: Process token to check

        Returns:
            Dictionary with process status information
        """
        # Check if the token exists
        if token not in self.process_tokens:
            # Check if it's in completed processes
            if token in self.completed_processes:
                # Move to end to mark as recently accessed (LRU behavior)
                result = self.completed_processes[token]
                self.completed_processes.move_to_end(token)
                return result

            _log_with_context(
                logging.WARNING, f"Process token not found: {token}", {"token": token}
            )
            return {
                "status": "not_found",
                "error": f"Process with token {token} not found",
            }

        # Get the process ID
        pid = self.process_tokens[token]

        # Check if the process is still running
        if pid not in self.running_processes:
            _log_with_context(
                logging.WARNING,
                f"Process PID not found in running processes: {pid}",
                {"token": token, "pid": pid},
            )
            return {
                "status": "unknown",
                "error": f"Process with PID {pid} not found in running processes",
            }

        process_data = self.running_processes[pid]
        process = process_data["process"]

        # Check if the process has exited
        if process.returncode is not None:
            # Process has completed
            _log_with_context(
                logging.INFO,
                f"Process status check found completed process",
                {"token": token, "pid": pid, "returncode": process.returncode},
            )

            # Get final result
            result = await self.wait_for_process(token)
            return result

        # Check if the process has been marked as terminated
        if "terminated" in process_data and process_data["terminated"]:
            # Get additional process info if psutil is available
            process_info = self.get_process_info(pid)

            status_info = {
                "status": "terminated",
                "pid": pid,
                "token": token,
                "command": process_data["command"],
                "runtime": time.time() - process_data["start_time"],
            }

            self._merge_psutil_info(status_info, process_info)

            return status_info

        # Process is still running
        # Get additional process info if psutil is available
        process_info = self.get_process_info(pid)

        status_info = {
            "status": "running",
            "pid": pid,
            "token": token,
            "command": process_data["command"],
            "runtime": time.time() - process_data["start_time"],
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
            # Check if it's already in completed processes
            if token in self.completed_processes:
                _log_with_context(
                    logging.INFO,
                    f"Process already completed, no need to terminate",
                    {"token": token},
                )
                return True

            _log_with_context(
                logging.WARNING,
                f"Cannot terminate: Process token not found: {token}",
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
        # Check if already in completed processes
        if token in self.completed_processes:
            return self.completed_processes[token]

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

        # Enforce memory limits before adding new process
        self._enforce_completed_process_limit()

        # Store in completed processes with timestamp
        current_time = time.time()
        self.completed_processes[token] = result
        self.completed_process_timestamps[token] = current_time

        # Persist job history
        self._persist_completed_processes()

        _log_with_context(
            logging.INFO,
            f"Wait process: Returning final result",
            {
                "token": token,
                "pid": pid,
                "returncode": returncode,
                "stdout_length": len(stdout_content),
                "stderr_length": len(stderr_content),
                "completed_processes_count": len(self.completed_processes),
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
