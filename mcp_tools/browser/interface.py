"""Browser client interface definitions.

This module defines the core interfaces for browser automation clients.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, Literal


class IBrowserClient(ABC):
    """Interface for browser automation clients.

    This abstract class defines the required methods that any browser client implementation
    must provide.
    """

    @abstractmethod
    async def get_page_html(
        self, url: str, wait_time: int = 30, headless: bool = True, options: Any = None
    ) -> Optional[str]:
        """Open a webpage and get its HTML content.

        Args:
            url: The URL to visit
            wait_time: Time to wait for page load in seconds
            headless: Whether to run browser in headless mode
            options: Browser-specific options

        Returns:
            HTML content of the page or None if an error occurred
        """
        pass

    @abstractmethod
    async def take_screenshot(
        self,
        url: str,
        output_path: str,
        wait_time: int = 30,
        headless: bool = True,
        options: Any = None,
        auto_scroll: bool = False,
        scroll_timeout: int = 30,
        scroll_step: int = 300,
        scroll_delay: float = 0.3,
    ) -> bool:
        """Navigate to a URL and take a screenshot.

        Args:
            url: The URL to visit
            output_path: Path where the screenshot should be saved
            wait_time: Time to wait for page load in seconds
            headless: Whether to run browser in headless mode
            options: Browser-specific options
            auto_scroll: Whether to automatically scroll through the page before taking the screenshot
            scroll_timeout: Maximum time to spend auto-scrolling in seconds
            scroll_step: Pixel distance to scroll in each step
            scroll_delay: Delay between scroll steps in seconds

        Returns:
            True if screenshot was successful, False otherwise
        """
        pass

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
