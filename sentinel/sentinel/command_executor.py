import platform
import subprocess
import asyncio
import uuid
from typing import Dict, Any, List, Optional, Union
import logging
import shlex
import time
import psutil

logger = logging.getLogger(__name__)

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

        pid = None
        try:
            logger.debug(f"Executing command: {mapped_command}")

            # Use shell=True on Windows for better command compatibility
            shell_needed = self.os_type == "windows"

            # Split command properly for non-shell execution
            if not shell_needed:
                command_parts = shlex.split(mapped_command)
            else:
                command_parts = mapped_command

            logger.debug(f"Command parts: {command_parts}.")

            # Use subprocess with timeout directly
            process = subprocess.Popen(
                command_parts,
                shell=shell_needed,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            pid = process.pid
            logger.debug(f"Process started with PID: {pid}")

            # Store process for potential later use
            self.running_processes[pid] = process

            try:
                # This will block until timeout or completion
                stdout, stderr = process.communicate(timeout=timeout)

                logger.debug(f"Process completed, returncode: {process.returncode}")

                # Process completed within timeout
                return {
                    "success": process.returncode == 0,
                    "output": stdout,
                    "error": stderr,
                    "pid": pid,
                }

            except subprocess.TimeoutExpired:
                # Process timed out, terminate it
                logger.debug(f"Process timed out after {timeout} seconds, terminating")
                process.kill()

                # Collect any output so far
                stdout, stderr = process.communicate()

                raise TimeoutError(f"Command timed out after {timeout} seconds")

        except TimeoutError as e:
            logger.error(f"Command timed out: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output": stdout if "stdout" in locals() else "",
                "pid": pid,
            }

        except Exception as e:
            logger.error(f"Unexpected error executing command: {str(e)}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

        finally:
            # Clean up process tracking if needed
            if pid in self.running_processes:
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
        
        # Extract the base command (first word)
        mapped_command = command
        pid = None
        
        try:
            logger.debug(f"Executing command asynchronously: {mapped_command}")

            # Use shell=True on Windows for better command compatibility
            shell_needed = self.os_type == "windows"

            # Split command properly for non-shell execution
            if not shell_needed:
                command_parts = shlex.split(mapped_command)
            else:
                command_parts = mapped_command

            logger.debug(f"Command parts: {command_parts}.")

            # Start the process asynchronously
            if shell_needed:
                # For Windows, use create_subprocess_shell
                process = await asyncio.create_subprocess_shell(
                    mapped_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                # For non-Windows, use create_subprocess_exec
                process = await asyncio.create_subprocess_exec(
                    *command_parts,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

            pid = process.pid
            logger.debug(f"Async process started with PID: {pid} and token: {token}")

            # Store process and map token to pid
            self.running_processes[pid] = process
            self.process_tokens[token] = pid

            # Return immediately with the token
            return {
                "token": token,
                "pid": pid,
                "status": "running"
            }
            
        except Exception as e:
            logger.error(f"Unexpected error executing async command: {str(e)}")
            return {
                "token": token,
                "success": False, 
                "error": f"Unexpected error: {str(e)}",
                "status": "failed"
            }

    async def wait_for_process(self, token: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Wait for a process to complete using its token

        Args:
            token: The token returned by execute_async
            timeout: Optional timeout in seconds

        Returns:
            Dictionary with process results
        """
        pid = self.process_tokens.get(token)
        if not pid:
            return {"success": False, "error": f"No process found for token: {token}"}
            
        process = self.running_processes.get(pid)
        if not process:
            return {"success": False, "error": f"Process not found for PID: {pid}"}
            
        try:
            # Wait for the process to complete with timeout
            if timeout is not None:
                # Wait with timeout
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
                except asyncio.TimeoutError:
                    # Process timed out, terminate it
                    logger.debug(f"Process timed out after {timeout} seconds, terminating")
                    try:
                        process.kill()
                        # Collect any output so far
                        stdout_bytes, stderr_bytes = await process.communicate()
                    except Exception as e:
                        logger.error(f"Error terminating timed out process: {str(e)}")
                        stdout_bytes, stderr_bytes = b"", b""
                    
                    raise TimeoutError(f"Command timed out after {timeout} seconds")
            else:
                # Wait indefinitely
                stdout_bytes, stderr_bytes = await process.communicate()
            
            # Decode bytes to strings
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
                
            logger.debug(f"Process completed, returncode: {process.returncode}")
            
            # Process completed
            result = {
                "token": token,
                "success": process.returncode == 0,
                "output": stdout,
                "error": stderr,
                "pid": pid,
                "status": "completed"
            }
            
            # Clean up tracking
            self.running_processes.pop(pid, None)
            self.process_tokens.pop(token, None)
            
            return result
            
        except TimeoutError as e:
            logger.error(f"Command timed out: {str(e)}")
            return {
                "token": token,
                "success": False,
                "error": str(e),
                "output": stdout if "stdout" in locals() else "",
                "pid": pid,
                "status": "timeout"
            }
        except Exception as e:
            logger.error(f"Unexpected error waiting for process: {str(e)}")
            # Try to clean up
            try:
                if pid in self.running_processes:
                    self.running_processes.pop(pid)
                if token in self.process_tokens:
                    self.process_tokens.pop(token)
            except:
                pass
                
            return {
                "token": token, 
                "success": False, 
                "error": f"Unexpected error: {str(e)}",
                "status": "error"
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
            
        process_info = self.get_process_info(pid)
        if not process_info:
            # Process may have completed or been terminated
            return {
                "token": token,
                "status": "not_running",
                "pid": pid
            }
        
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
                if hasattr(process, 'kill'):
                    process.kill()
                elif hasattr(process, 'terminate'):
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
        if hasattr(process, 'poll'):
            # This is a subprocess.Popen object
            process_running = process.poll() is None
        elif hasattr(process, 'returncode'):
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

    async def query_process(self, token: str, wait: bool = False, timeout: Optional[float] = None) -> Dict[str, Any]:
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
