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
    def get_page_html(self, url: str, wait_time: int = 30, headless: bool = True, 
                     options: Any = None) -> Optional[str]:
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
    def take_screenshot(self, url: str, output_path: str, wait_time: int = 30, 
                       headless: bool = True, options: Any = None) -> bool:
        """Navigate to a URL and take a screenshot.
        
        Args:
            url: The URL to visit
            output_path: Path where the screenshot should be saved
            wait_time: Time to wait for page load in seconds
            headless: Whether to run browser in headless mode
            options: Browser-specific options
            
        Returns:
            True if screenshot was successful, False otherwise
        """
        pass 