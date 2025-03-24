import platform
import subprocess
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class CommandExecutor:
    def __init__(self):
        self.os_type = platform.system().lower()
        self._setup_allowed_commands()

    def _setup_allowed_commands(self):
        """Set up allowed commands based on OS"""
        # Common commands for both OS types
        common_commands = ["echo"]
        
        # OS-specific commands
        if self.os_type == "windows":
            self.allowed_commands = common_commands + [
                "dir",      # Windows equivalent of ls
                "cd",       # Change directory
                "type",     # Windows equivalent of cat
                "where"     # Windows equivalent of which
            ]
            self.command_mapping = {
                "ls": "dir",
                "cat": "type",
                "which": "where"
            }
        else:  # Linux/Unix
            self.allowed_commands = common_commands + [
                "ls",
                "pwd",
                "cat",
                "which"
            ]
            self.command_mapping = {}  # No mapping needed for Unix commands

    def _map_command(self, command: str) -> str:
        """Map Unix-style commands to Windows equivalents if needed"""
        if self.os_type == "windows":
            base_command = command.split()[0]
            mapped_command = self.command_mapping.get(base_command, base_command)
            if mapped_command != base_command:
                return command.replace(base_command, mapped_command, 1)
        return command

    def execute(self, command: str) -> Dict[str, Any]:
        """Execute a command and return the result"""
        # Extract the base command (first word)
        base_command = command.split()[0]
        
        # Map the command if needed
        mapped_command = self._map_command(command)
        mapped_base = mapped_command.split()[0]
        
        # Check if command is allowed
        if mapped_base not in self.allowed_commands:
            logger.warning(f"Command '{base_command}' not allowed")
            return {
                "success": False,
                "error": f"Command '{base_command}' not in allowed commands list"
            }

        try:
            logger.debug(f"Executing command: {mapped_command}")
            
            # Use shell=True on Windows for better command compatibility
            shell_needed = self.os_type == "windows"
            
            result = subprocess.run(
                mapped_command,
                shell=shell_needed,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Handle encoding for different OS
            stdout = result.stdout
            stderr = result.stderr
            
            if self.os_type == "windows":
                # Windows typically uses cp1252 or similar
                stdout = stdout.replace('\r\n', '\n')
                stderr = stderr.replace('\r\n', '\n')
            
            logger.debug(f"Command output: {stdout}")
            if stderr:
                logger.debug(f"Command stderr: {stderr}")
                
            return {
                "success": True,
                "output": stdout,
                "error": stderr
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Command execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error executing command: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    def get_allowed_commands(self) -> List[str]:
        """Return list of allowed commands for current OS"""
        return self.allowed_commands 