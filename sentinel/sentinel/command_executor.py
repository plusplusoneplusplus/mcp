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
    context['timestamp'] = datetime.now(UTC).isoformat()
    
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
                    "start_time": start_time
                }
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
                {
                    "shell_needed": shell_needed,
                    "command_parts": command_parts
                }
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
                    {"error": str(e), "pid": pid}
                )

            _log_with_context(
                logging.INFO,
                "Process started",
                {
                    "pid": pid,
                    "memory_info": memory_info,
                    "cpu_percent": cpu_percent,
                    "command": mapped_command
                }
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
                        "stderr_length": len(stderr)
                    }
                )

                # Process completed within timeout
                return {
                    "success": process.returncode == 0,
                    "output": stdout,
                    "error": stderr,
                    "pid": pid,
                    "duration": duration
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
                        "elapsed_time": time.time() - start_time
                    }
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
                    "command": mapped_command
                }
            )
            return {
                "success": False,
                "error": str(e),
                "output": stdout if "stdout" in locals() else "",
                "pid": pid,
                "duration": end_time - start_time
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
                    "command": mapped_command
                }
            )
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "duration": end_time - start_time
            }

        finally:
            # Clean up process tracking if needed
            if pid in self.running_processes:
                _log_with_context(
                    logging.DEBUG,
                    "Cleaning up process tracking",
                    {"pid": pid}
                )
                self.running_processes.pop(pid, None)

    async def execute_async(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Execute a command asynchronously and return a token for tracking

        Args:
            command: The command to execute
            timeout: Optional timeout in seconds

        Returns:
            Dictionary with token for tracking and initial process info
        """
        # Generate a unique token for this process
        token = str(uuid.uuid4())
        start_time = time.time()
        pid = None

        try:
            _log_with_context(
                logging.INFO,
                "Starting async command execution",
                {
                    "command": command,
                    "token": token,
                    "timeout": timeout,
                    "start_time": start_time
                }
            )

            # Start the process asynchronously
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            pid = process.pid
            
            # Collect process metrics if possible
            try:
                process_info = psutil.Process(pid)
                memory_info = process_info.memory_info()._asdict()
                cpu_percent = process_info.cpu_percent()
                create_time = process_info.create_time()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                memory_info = {}
                cpu_percent = None
                create_time = None
                _log_with_context(
                    logging.WARNING,
                    "Could not get async process metrics",
                    {"error": str(e), "pid": pid, "token": token}
                )

            _log_with_context(
                logging.INFO,
                "Async process started",
                {
                    "pid": pid,
                    "token": token,
                    "memory_info": memory_info,
                    "cpu_percent": cpu_percent,
                    "create_time": create_time,
                    "command": command,
                    "elapsed_time": time.time() - start_time
                }
            )

            # Store process and map token to pid
            self.running_processes[pid] = process
            self.process_tokens[token] = pid

            _log_with_context(
                logging.DEBUG,
                "Process tracking initialized",
                {
                    "pid": pid,
                    "token": token,
                    "total_running_processes": len(self.running_processes)
                }
            )

            # Return immediately with the token
            return {"token": token, "pid": pid, "status": "running"}

        except Exception as e:
            end_time = time.time()
            _log_with_context(
                logging.ERROR,
                "Error in async command execution",
                {
                    "token": token,
                    "pid": pid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration": end_time - start_time,
                    "command": command
                }
            )
            return {
                "token": token,
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "status": "failed",
                "duration": end_time - start_time
            }

    async def wait_for_process(self, token: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Wait for a process to complete using its token

        Args:
            token: The token returned by execute_async
            timeout: Optional timeout in seconds

        Returns:
            Dictionary with process results
        """
        start_time = time.time()
        
        pid = self.process_tokens.get(token)
        if not pid:
            _log_with_context(
                logging.ERROR,
                "Process token not found",
                {"token": token}
            )
            return {"success": False, "error": f"No process found for token: {token}"}

        process = self.running_processes.get(pid)
        if not process:
            _log_with_context(
                logging.ERROR,
                "Process not found",
                {"token": token, "pid": pid}
            )
            return {"success": False, "error": f"Process not found for PID: {pid}"}

        try:
            _log_with_context(
                logging.INFO,
                "Waiting for process completion",
                {
                    "token": token,
                    "pid": pid,
                    "timeout": timeout
                }
            )

            # Wait for the process to complete with timeout
            if timeout is not None:
                # Wait with timeout
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(), timeout=timeout
                    )
                except asyncio.TimeoutError:
                    # Process timed out, terminate it
                    elapsed_time = time.time() - start_time
                    _log_with_context(
                        logging.ERROR,
                        "Process wait timeout",
                        {
                            "token": token,
                            "pid": pid,
                            "timeout": timeout,
                            "elapsed_time": elapsed_time
                        }
                    )
                    
                    try:
                        process.kill()
                        _log_with_context(
                            logging.INFO,
                            "Process terminated after timeout",
                            {"token": token, "pid": pid}
                        )
                        # Collect any output so far
                        stdout_bytes, stderr_bytes = await process.communicate()
                    except Exception as kill_error:
                        _log_with_context(
                            logging.ERROR,
                            "Error terminating process after timeout",
                            {
                                "token": token,
                                "pid": pid,
                                "error": str(kill_error)
                            }
                        )
                        stdout_bytes, stderr_bytes = b"", b""

                    raise TimeoutError(f"Command timed out after {timeout} seconds")
            else:
                # Wait indefinitely
                stdout_bytes, stderr_bytes = await process.communicate()

            # Decode bytes to strings
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            end_time = time.time()
            duration = end_time - start_time

            # Try to get final process metrics
            try:
                ps_process = psutil.Process(pid)
                final_cpu = ps_process.cpu_percent()
                final_memory = ps_process.memory_info()._asdict()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                final_cpu = None
                final_memory = {}

            _log_with_context(
                logging.INFO,
                "Process completed",
                {
                    "token": token,
                    "pid": pid,
                    "returncode": process.returncode,
                    "duration": duration,
                    "stdout_length": len(stdout),
                    "stderr_length": len(stderr),
                    "final_cpu_percent": final_cpu,
                    "final_memory": final_memory
                }
            )

            # Process completed
            result = {
                "token": token,
                "success": process.returncode == 0,
                "output": stdout,
                "error": stderr,
                "pid": pid,
                "status": "completed",
                "duration": duration
            }

            # Clean up tracking
            self.running_processes.pop(pid, None)
            self.process_tokens.pop(token, None)

            _log_with_context(
                logging.DEBUG,
                "Process tracking cleaned up",
                {
                    "token": token,
                    "pid": pid,
                    "remaining_processes": len(self.running_processes)
                }
            )

            return result

        except TimeoutError as e:
            _log_with_context(
                logging.ERROR,
                "Process wait timed out",
                {
                    "token": token,
                    "pid": pid,
                    "error": str(e),
                    "duration": time.time() - start_time
                }
            )
            return {
                "token": token,
                "success": False,
                "error": str(e),
                "output": stdout if "stdout" in locals() else "",
                "pid": pid,
                "status": "timeout",
                "duration": time.time() - start_time
            }
        except Exception as e:
            _log_with_context(
                logging.ERROR,
                "Unexpected error waiting for process",
                {
                    "token": token,
                    "pid": pid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration": time.time() - start_time
                }
            )
            # Try to clean up
            try:
                if pid in self.running_processes:
                    self.running_processes.pop(pid)
                if token in self.process_tokens:
                    self.process_tokens.pop(token)
                _log_with_context(
                    logging.INFO,
                    "Process tracking cleaned up after error",
                    {"token": token, "pid": pid}
                )
            except Exception as cleanup_error:
                _log_with_context(
                    logging.ERROR,
                    "Error during cleanup after process error",
                    {
                        "token": token,
                        "pid": pid,
                        "cleanup_error": str(cleanup_error)
                    }
                )

            return {
                "token": token,
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "status": "error",
                "duration": time.time() - start_time
            }

    async def get_process_status(self, token: str) -> Dict[str, Any]:
        """Get the status of a process using its token

        Args:
            token: The token returned by execute_async

        Returns:
            Dictionary with process status information
        """
        pid = self.process_tokens.get(token)
        if not pid:
            return {"success": False, "error": f"No process found for token: {token}"}

        print("Getting process info for pid: ", pid)
        process_info = self.get_process_info(pid)
        if not process_info:
            # Process may have completed or been terminated
            return {"token": token, "status": "not_running", "pid": pid}

        # Add token to process info
        process_info["token"] = token
        process_info["status"] = "running"
        return process_info

    def get_allowed_commands(self) -> List[str]:
        """Return list of allowed commands for current OS"""
        return self.allowed_commands

    def terminate_process(self, pid: int) -> bool:
        """Terminate a running process by PID"""
        process = self.running_processes.get(pid)
        if process:
            try:
                # Handle both regular subprocess and asyncio processes
                if hasattr(process, "kill"):
                    process.kill()
                elif hasattr(process, "terminate"):
                    process.terminate()
                # Remove from tracking
                self.running_processes.pop(pid, None)
                return True
            except Exception as e:
                logger.error(f"Error terminating process {pid}: {str(e)}")
        return False

    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Get information about a running process"""
        process = self.running_processes.get(pid)
        if not process:
            return None

        # Handle different process types (asyncio Process vs subprocess.Popen)
        process_running = False
        if hasattr(process, "poll"):
            # This is a subprocess.Popen object
            process_running = process.poll() is None
        elif hasattr(process, "returncode"):
            # This is an asyncio Process object
            process_running = process.returncode is None

        if process_running:
            try:
                # Use psutil to get additional process info
                ps_process = psutil.Process(pid)
                return {
                    "pid": pid,
                    "status": ps_process.status(),
                    "cpu_percent": ps_process.cpu_percent(),
                    "memory_info": ps_process.memory_info()._asdict(),
                    "create_time": ps_process.create_time(),
                    "cmdline": ps_process.cmdline(),
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return None

    def terminate_by_token(self, token: str) -> bool:
        """Terminate a running process by token

        Args:
            token: The token returned by execute_async

        Returns:
            Boolean indicating success
        """
        pid = self.process_tokens.get(token)
        if not pid:
            logger.warning(f"No process found for token: {token}")
            return False

        result = self.terminate_process(pid)
        if result:
            # Clean up tracking if termination was successful
            self.process_tokens.pop(token, None)

        return result

    async def query_process(
        self, token: str, wait: bool = False, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Query a process status and optionally wait for completion

        Args:
            token: The token returned by execute_async
            wait: If True, wait for the process to complete
            timeout: Optional timeout in seconds for waiting

        Returns:
            Dictionary with process status or results
        """
        # If not waiting, just return current status
        if not wait:
            return await self.get_process_status(token)

        # Otherwise, wait for process to complete
        return await self.wait_for_process(token, timeout)
