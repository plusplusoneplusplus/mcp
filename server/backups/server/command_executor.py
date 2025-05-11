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
from datetime import datetime, UTC

g_config_sleep_when_running = True

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


class CommandExecutor:
    """Command executor that can run processes synchronously or asynchronously

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

    def __init__(self):
        self.os_type = platform.system().lower()
        self.running_processes = {}
        self.process_tokens = {}  # Maps tokens to process IDs
        self.completed_processes = {}  # Store results of completed processes

    def execute(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Execute a command and return the result with process monitoring

        Args:
            command: The command to execute
            timeout: Optional timeout in seconds
        """
        # Extract the base command (first word)
        mapped_command = command
        start_time = time.time()
        pid = None

        try:
            _log_with_context(
                logging.INFO,
                "Starting command execution",
                {
                    "command": mapped_command,
                    "timeout": timeout,
                    "os_type": self.os_type,
                    "start_time": start_time,
                },
            )

            # Use shell=True on Windows for better command compatibility
            shell_needed = self.os_type == "windows"

            # Split command properly for non-shell execution
            if not shell_needed:
                command_parts = shlex.split(mapped_command)
            else:
                command_parts = mapped_command

            _log_with_context(
                logging.DEBUG,
                "Prepared command for execution",
                {"shell_needed": shell_needed, "command_parts": command_parts},
            )

            # Use subprocess with timeout directly
            process = subprocess.Popen(
                command_parts,
                shell=shell_needed,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            pid = process.pid
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
                },
            )

            # Store process for potential later use
            self.running_processes[pid] = process

            try:
                # This will block until timeout or completion
                stdout, stderr = process.communicate(timeout=timeout)
                end_time = time.time()
                duration = end_time - start_time

                _log_with_context(
                    logging.INFO,
                    "Process completed",
                    {
                        "pid": pid,
                        "returncode": process.returncode,
                        "duration": duration,
                        "success": process.returncode == 0,
                        "stdout_length": len(stdout),
                        "stderr_length": len(stderr),
                    },
                )

                # Process completed within timeout
                return {
                    "success": process.returncode == 0,
                    "output": stdout,
                    "error": stderr,
                    "pid": pid,
                    "duration": duration,
                }

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

                # Collect any output so far
                stdout, stderr = process.communicate()

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
                },
            )
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "duration": end_time - start_time,
            }

        finally:
            # Clean up process tracking if needed
            if pid in self.running_processes:
                _log_with_context(
                    logging.DEBUG, "Cleaning up process tracking", {"pid": pid}
                )
                self.running_processes.pop(pid, None)

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

        _log_with_context(
            logging.INFO,
            "Starting async command execution",
            {
                "command": mapped_command,
                "timeout": timeout,
                "os_type": self.os_type,
                "token": token,
            },
        )

        # Use shell=True on Windows for better command compatibility
        shell_needed = self.os_type == "windows"

        # Split command properly for non-shell execution
        if not shell_needed:
            command_parts = shlex.split(mapped_command)
        else:
            command_parts = mapped_command

        _log_with_context(
            logging.DEBUG,
            "Prepared async command for execution",
            {
                "shell_needed": shell_needed,
                "command_parts": command_parts,
                "token": token,
            },
        )

        # Launch the process
        try:
            # Use subprocess with timeout directly
            process = subprocess.Popen(
                command_parts,
                shell=shell_needed,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            pid = process.pid

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
                    "token": token,
                },
            )

            # Store the process and mapping
            self.running_processes[pid] = process
            self.process_tokens[token] = pid

            # Create a task to monitor and eventually collect output
            asyncio.create_task(self.wait_for_process(token, timeout))

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
                },
            )
            # Store the error in completed processes
            self.completed_processes[token] = {
                "status": "error",
                "error": f"Failed to start process: {str(e)}",
                "success": False,
            }
            return {
                "token": token,
                "status": "error",
                "error": f"Failed to start process: {str(e)}",
            }

    async def wait_for_process(
        self, token: str, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Wait for a process to complete and collect its output

        Args:
            token: The token returned from execute_async
            timeout: Optional timeout in seconds

        Returns:
            Dictionary with success, output, and error information
        """
        if token in self.completed_processes:
            # Process has already completed or errored
            _log_with_context(
                logging.INFO,
                "Fetching already completed process results",
                {"token": token},
            )
            return self.completed_processes[token]

        if token not in self.process_tokens:
            # Process token not found
            error_msg = f"Process token not found: {token}"
            _log_with_context(logging.ERROR, error_msg, {"token": token})
            return {"status": "error", "error": error_msg, "success": False}

        # Get the process ID
        pid = self.process_tokens[token]
        if pid not in self.running_processes:
            # Process no longer running
            error_msg = f"Process not found (token: {token}, pid: {pid})"
            _log_with_context(logging.ERROR, error_msg, {"token": token, "pid": pid})
            return {"status": "error", "error": error_msg, "success": False}

        # Get the process object
        process = self.running_processes[pid]
        start_time = time.time()

        _log_with_context(
            logging.INFO,
            "Waiting for process completion",
            {"token": token, "pid": pid, "timeout": timeout},
        )

        try:
            # This will block until timeout or completion
            stdout, stderr = await asyncio.get_event_loop().run_in_executor(
                None, lambda: process.communicate(timeout=timeout)
            )
            end_time = time.time()
            duration = end_time - start_time

            success = process.returncode == 0

            _log_with_context(
                logging.INFO,
                "Process wait completed",
                {
                    "token": token,
                    "pid": pid,
                    "returncode": process.returncode,
                    "duration": duration,
                    "success": success,
                    "stdout_length": len(stdout),
                    "stderr_length": len(stderr),
                },
            )

            result = {
                "status": "completed",
                "success": success,
                "output": stdout,
                "error": stderr,
                "pid": pid,
                "returncode": process.returncode,
                "duration": duration,
            }

            # Store the result for later retrieval
            self.completed_processes[token] = result

            # Clean up tracking
            self.running_processes.pop(pid, None)

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
                },
            )

            # Terminate the process
            self.terminate_process(pid)

            # Try to collect any output so far
            try:
                stdout, stderr = process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", "Unable to collect output after timeout"

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

            # Clean up tracking
            self.running_processes.pop(pid, None)

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
                },
            )

            # Try to collect any output so far
            try:
                stdout, stderr = process.communicate(timeout=1)
            except:
                stdout, stderr = "", "Unable to collect output after error"

            # Ensure the process is terminated
            self.terminate_process(pid)

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

            # Clean up tracking
            self.running_processes.pop(pid, None)

            return result

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
        except psutil.NoSuchProcess:
            # Process no longer exists, but we don't have completion info
            memory_info = {}
            cpu_percent = None
            status = "unknown"
        except Exception as e:
            memory_info = {}
            cpu_percent = None
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
            return {
                "pid": pid,
                "status": process.status(),
                "cpu_percent": process.cpu_percent(),
                "memory_info": process.memory_info()._asdict(),
                "create_time": process.create_time(),
                "cmdline": process.cmdline(),
                "username": process.username(),
                "name": process.name(),
            }
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
