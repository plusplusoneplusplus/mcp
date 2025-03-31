import platform
import subprocess
from typing import Dict, Any, List, Optional
import logging
import shlex
import time
import psutil

logger = logging.getLogger(__name__)

class CommandExecutor:
    def __init__(self):
        self.os_type = platform.system().lower()
        self.running_processes = {}

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

    def get_allowed_commands(self) -> List[str]:
        """Return list of allowed commands for current OS"""
        return self.allowed_commands

    def terminate_process(self, pid: int) -> bool:
        """Terminate a running process by PID"""
        process = self.running_processes.get(pid)
        if process:
            try:
                process.kill()
                return True
            except:
                pass
        return False

    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Get information about a running process"""
        process = self.running_processes.get(pid)
        if process and process.poll() is None:
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
