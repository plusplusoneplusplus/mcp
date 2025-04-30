"""Browser client factory.

This module provides a factory for creating browser clients.
"""

from typing import Optional, Literal

from mcp_tools.browser.interface import IBrowserClient
from mcp_tools.browser.selenium_client import SeleniumBrowserClient


class BrowserClientFactory:
    """Factory for creating browser clients.
    
    This class provides methods for creating different types of browser clients.
    """
    
    @staticmethod
    def create_client(client_type: str = "selenium", 
                     browser_type: Optional[Literal["chrome", "edge"]] = None) -> IBrowserClient:
        """Create a browser client of the specified type.
        
        Args:
            client_type: Type of client to create ('selenium' for now)
            browser_type: Type of browser to use ('chrome' or 'edge')
            
        Returns:
            Browser client instance
            
        Raises:
            ValueError: If an unsupported client type is specified
        """
        if client_type.lower() == "selenium":
            return SeleniumBrowserClient(browser_type)
        else:
            raise ValueError(f"Unsupported client type: {client_type}") 