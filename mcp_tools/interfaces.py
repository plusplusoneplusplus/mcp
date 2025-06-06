"""Interfaces for MCP tools.

This module defines the core interfaces that tools must implement
to be compatible with the MCP system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Generic, TypeVar

T = TypeVar("T")
InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")


class ToolInterface(ABC):
    """Base interface for all tools."""

    def __init__(self):
        self._diagnostic_dir: Optional[str] = None

    @property
    def diagnostic_dir(self) -> Optional[str]:
        """Get the diagnostic directory path for this tool instance."""
        return self._diagnostic_dir

    @diagnostic_dir.setter
    def diagnostic_dir(self, value: Optional[str]):
        self._diagnostic_dir = value

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
    async def execute_async(
        self, command: str, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute a command asynchronously.

        Args:
            command: The command to execute
            timeout: Optional timeout in seconds

        Returns:
            Dictionary with process token and initial status
        """
        pass

    @abstractmethod
    async def query_process(
        self, token: str, wait: bool = False, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
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

    @abstractmethod
    def list_running_processes(self) -> List[Dict[str, Any]]:
        """List all currently running background processes.
        
        Returns:
            List of dictionaries containing process information
        """
        pass

    @abstractmethod
    async def start_periodic_status_reporter(self, interval: float = 30.0, enabled: bool = True) -> None:
        """Start periodic status reporting for running processes.
        
        Args:
            interval: Time interval between status reports in seconds
            enabled: Whether to enable periodic reporting
        """
        pass

    @abstractmethod
    async def stop_periodic_status_reporter(self) -> None:
        """Stop periodic status reporting."""
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
    async def get_pull_request(
        self, pull_request_id: Union[int, str], **kwargs
    ) -> Dict[str, Any]:
        """Get details of a specific pull request.

        Args:
            pull_request_id: ID of the pull request
            **kwargs: Repository-specific arguments

        Returns:
            Dictionary with pull request details
        """
        pass

    @abstractmethod
    async def create_pull_request(
        self, title: str, source_branch: str, **kwargs
    ) -> Dict[str, Any]:
        """Create a new pull request.

        Args:
            title: Title for the pull request
            source_branch: Name of the source branch
            **kwargs: Repository-specific arguments

        Returns:
            Dictionary with created pull request details
        """
        pass


class KustoClientInterface(ToolInterface):
    """Interface for Azure Data Explorer (Kusto) client tools."""

    @abstractmethod
    def get_kusto_client(self, cluster_url: Optional[str] = None) -> Any:
        """Initialize and return a Kusto client for Azure Data Explorer.

        Args:
            cluster_url: Optional URL of the Kusto cluster

        Returns:
            A configured Kusto client
        """
        pass

    @abstractmethod
    async def execute_query(
        self,
        database: str,
        query: str,
        client: Optional[Any] = None,
        cluster_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a Kusto query and return the results.

        Args:
            database: The name of the database to query
            query: The KQL query to execute
            client: Optional existing Kusto client to use
            cluster_url: Optional URL of the Kusto cluster

        Returns:
            Dictionary with query results
        """
        pass


class BrowserClientInterface(ToolInterface):
    """Interface for browser client tools."""

    @abstractmethod
    async def get_page_html(self, url: str, wait_time: int = 30) -> Optional[str]:
        """Open a webpage and get its HTML content.

        Args:
            url: The URL to visit
            wait_time: Time to wait for page load in seconds

        Returns:
            HTML content of the page or None if an error occurred
        """
        pass

    @abstractmethod
    async def take_screenshot(
        self, url: str, output_path: str, wait_time: int = 30
    ) -> bool:
        """Navigate to a URL and take a screenshot.

        Args:
            url: The URL to visit
            output_path: Path where the screenshot should be saved
            wait_time: Time to wait for page load in seconds

        Returns:
            True if screenshot was successful, False otherwise
        """
        pass


class CapturePanelsClientInterface(ToolInterface):
    """Interface for dashboard panel capture tools."""

    @abstractmethod
    async def capture_panels(
        self,
        url: str,
        selector: str = ".react-grid-item",
        out_dir: str = "charts",
        width: int = 1600,
        height: int = 900,
        token: Optional[str] = None,
        wait_time: int = 30,
        headless: bool = True,
        options: Any = None,
    ) -> int:
        """
        Capture each matching element as an image and save to the output directory.
        Args:
            url: The dashboard URL to visit
            selector: CSS selector for chart/panel containers
            out_dir: Directory to write PNGs
            width: Browser viewport width
            height: Browser viewport height
            token: Bearer token for Authorization header (optional)
            wait_time: Time to wait for page load in seconds
            headless: Whether to run browser in headless mode
            options: Browser-specific options
        Returns:
            The number of panels captured (saved as PNGs)
        """
        pass


class EnvironmentManagerInterface(ToolInterface):
    """Interface for environment management tools."""

    @abstractmethod
    def load(self) -> "EnvironmentManagerInterface":
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
