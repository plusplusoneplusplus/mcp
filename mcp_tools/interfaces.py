"""Interfaces for MCP tools.

This module defines the core interfaces that tools must implement
to be compatible with the MCP system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Generic, TypeVar

T = TypeVar('T')
InputType = TypeVar('InputType')
OutputType = TypeVar('OutputType')

class ToolInterface(ABC):
    """Base interface for all tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the tool name."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the tool description."""
        pass
        
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        pass
    
    @abstractmethod
    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the tool with the provided arguments.
        
        Args:
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Tool execution result
        """
        pass

class CommandExecutorInterface(ToolInterface):
    """Interface for command execution tools."""
    
    @abstractmethod
    def execute(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Execute a command synchronously.
        
        Args:
            command: The command to execute
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary with execution results
        """
        pass
    
    @abstractmethod
    async def execute_async(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Execute a command asynchronously.
        
        Args:
            command: The command to execute
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary with process token and initial status
        """
        pass
    
    @abstractmethod
    async def query_process(self, token: str, wait: bool = False, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Query a process status or wait for completion.
        
        Args:
            token: Process token to query
            wait: Whether to wait for process completion
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary with process status or result
        """
        pass
    
    @abstractmethod
    def terminate_by_token(self, token: str) -> bool:
        """Terminate a running process by token.
        
        Args:
            token: Process token to terminate
            
        Returns:
            True if termination was successful, False otherwise
        """
        pass

class RepoClientInterface(ToolInterface):
    """Interface for repository client tools."""
    
    @abstractmethod
    async def list_pull_requests(self, **kwargs) -> Dict[str, Any]:
        """List pull requests in the repository.
        
        Args:
            **kwargs: Repository-specific arguments
            
        Returns:
            Dictionary with pull request information
        """
        pass
    
    @abstractmethod
    async def get_pull_request(self, pull_request_id: Union[int, str], **kwargs) -> Dict[str, Any]:
        """Get details of a specific pull request.
        
        Args:
            pull_request_id: ID of the pull request
            **kwargs: Repository-specific arguments
            
        Returns:
            Dictionary with pull request details
        """
        pass
    
    @abstractmethod
    async def create_pull_request(self, title: str, source_branch: str, **kwargs) -> Dict[str, Any]:
        """Create a new pull request.
        
        Args:
            title: Title for the pull request
            source_branch: Name of the source branch
            **kwargs: Repository-specific arguments
            
        Returns:
            Dictionary with created pull request details
        """
        pass

class BrowserClientInterface(ToolInterface):
    """Interface for browser client tools."""
    
    @abstractmethod
    def get_page_html(self, url: str, wait_time: int = 30) -> Optional[str]:
        """Open a webpage and get its HTML content.
        
        Args:
            url: The URL to visit
            wait_time: Time to wait for page load in seconds
            
        Returns:
            HTML content of the page or None if an error occurred
        """
        pass
    
    @abstractmethod
    def take_screenshot(self, url: str, output_path: str, wait_time: int = 30) -> bool:
        """Navigate to a URL and take a screenshot.
        
        Args:
            url: The URL to visit
            output_path: Path where the screenshot should be saved
            wait_time: Time to wait for page load in seconds
            
        Returns:
            True if screenshot was successful, False otherwise
        """
        pass

class EnvironmentManagerInterface(ToolInterface):
    """Interface for environment management tools."""
    
    @abstractmethod
    def load(self) -> 'EnvironmentManagerInterface':
        """Load all environment information.
        
        Returns:
            Self for method chaining
        """
        pass
    
    @abstractmethod
    def get_parameter_dict(self) -> Dict[str, Any]:
        """Return environment as a dictionary for command substitution.
        
        Returns:
            Dictionary of environment parameters
        """
        pass
    
    @abstractmethod
    def get_git_root(self) -> Optional[str]:
        """Get git root directory.
        
        Returns:
            Path to the git root or None if not available
        """
        pass
    
    @abstractmethod
    def get_workspace_folder(self) -> Optional[str]:
        """Get workspace folder.
        
        Returns:
            Path to the workspace folder or None if not available
        """
        pass 