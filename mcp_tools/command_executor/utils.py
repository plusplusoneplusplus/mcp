import os
import platform
import shlex
from typing import Dict, Any, List, Optional

def format_command_with_parameters(command: str, parameters: Dict[str, Any]) -> str:
    """Format a command with parameters.

    Args:
        command: The command string with placeholders
        parameters: Dictionary of parameters to substitute
    """
    try:
        return command.format(**parameters)
    except KeyError as e:
        print(f"Warning: Missing parameter in command: {e}")
        return command  # Return original command if formatting fails
    except ValueError as e:
        print(f"Warning: Invalid format in command: {e}")
        return command  # Return original command if formatting fails

def get_current_os() -> str:
    """Get the current OS as a lowercase string.
    
    Returns:
        String representing the OS: 'windows', 'linux', 'darwin' (macOS), etc.
    """
    return platform.system().lower()

def is_windows() -> bool:
    """Check if the current OS is Windows.
    
    Returns:
        True if the OS is Windows, False otherwise.
    """
    return get_current_os() == "windows"

def is_wsl() -> bool:
    """Check if running in Windows Subsystem for Linux.
    
    Returns:
        True if running in WSL, False otherwise.
    """
    return (
        os.path.exists("/proc/version") and 
        "microsoft" in open("/proc/version").read().lower()
    )

def parse_command(command: str) -> List[str]:
    """Parse a command string into a list of arguments, handling OS differences.
    
    Args:
        command: The command string to parse
        
    Returns:
        List of command arguments
    """
    if is_windows():
        # On Windows, don't use shlex
        # This is a simplified approach; Windows command parsing is complex
        return command.split()
    else:
        # On Unix-like systems, use shlex for proper parsing
        return shlex.split(command)

def ensure_directory_exists(directory: str) -> None:
    """Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
    """
    os.makedirs(directory, exist_ok=True) 