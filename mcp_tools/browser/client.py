"""Browser client for web automation.

This module provides a client for browser automation operations.
"""

import time
from typing import Dict, Any, Optional, Literal

from mcp_tools.browser.factory import BrowserClientFactory
from mcp_tools.plugin import register_tool
from mcp_tools.interfaces import BrowserClientInterface

# Global configuration
DEFAULT_BROWSER_TYPE: Literal["chrome", "edge"] = "chrome"
DEFAULT_CLIENT_TYPE: str = "selenium"


@register_tool
class BrowserClient(BrowserClientInterface):
    """Client for browser automation operations.
    
    This class provides a simplified interface for browser operations like opening pages,
    capturing screenshots, etc. using Selenium with Chrome or Microsoft Edge.
    
    This class is a wrapper around the browser client implementation provided by the factory.
    
    Example:
        # Create a browser client
        browser = BrowserClient()
        
        # Get HTML content of a page
        html = browser.get_page_html("https://example.com")
    """
    
    def __init__(self, browser_type: Literal["chrome", "edge"] = None, client_type: str = None):
        """Initialize the browser client.
        
        Args:
            browser_type: Type of browser to use ('chrome' or 'edge').
                         If None, uses DEFAULT_BROWSER_TYPE.
            client_type: Type of client implementation to use.
                        If None, uses DEFAULT_CLIENT_TYPE.
        """
        self.browser_type = browser_type or DEFAULT_BROWSER_TYPE
        self.client_type = client_type or DEFAULT_CLIENT_TYPE
    
    # Implement ToolInterface properties
    @property
    def name(self) -> str:
        """Get the tool name."""
        return "browser_client"
        
    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Browser automation for web scraping and testing"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform (get_page_html, take_screenshot)",
                    "enum": ["get_page_html", "take_screenshot"]
                },
                "url": {
                    "type": "string",
                    "description": "The URL to visit"
                },
                "wait_time": {
                    "type": "integer",
                    "description": "Time to wait for page load in seconds",
                    "default": 30
                },
                "output_path": {
                    "type": "string",
                    "description": "Path where the screenshot should be saved (for take_screenshot)",
                    "nullable": True
                }
            },
            "required": ["operation", "url"]
        }
        
    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments.
        
        Args:
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Tool execution result
        """
        operation = arguments.get("operation", "")
        url = arguments.get("url", "")
        wait_time = arguments.get("wait_time", 30)
        headless = arguments.get("headless", True)
        browser_options = arguments.get("browser_options", None)
        browser_type = arguments.get("browser_type", self.browser_type)
        client_type = arguments.get("client_type", self.client_type)
        
        # Use the BrowserClientFactory to create the client
        client = BrowserClientFactory.create_client(client_type, browser_type)
        
        if operation == "get_page_html":
            html = client.get_page_html(url, wait_time, headless, browser_options)
            if html:
                return {
                    "success": True,
                    "html": html[:10000] + ("..." if len(html) > 10000 else ""),
                    "html_length": len(html)
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to retrieve HTML from {url}"
                }
        elif operation == "take_screenshot":
            output_path = arguments.get("output_path", f"screenshot_{int(time.time())}.png")
            success = client.take_screenshot(url, output_path, wait_time, headless, browser_options)
            return {
                "success": success,
                "output_path": output_path
            }
        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}"
            }
    
    @classmethod
    def set_default_browser_type(cls, browser_type: Literal["chrome", "edge"]):
        """Set the default browser type to use globally.
        
        Args:
            browser_type: Type of browser ('chrome' or 'edge')
        """
        global DEFAULT_BROWSER_TYPE
        DEFAULT_BROWSER_TYPE = browser_type
    
    @classmethod
    def get_default_browser_type(cls) -> str:
        """Get the current default browser type.
        
        Returns:
            Current default browser type
        """
        return DEFAULT_BROWSER_TYPE
    
    @classmethod
    def set_default_client_type(cls, client_type: str):
        """Set the default client type to use globally.
        
        Args:
            client_type: Type of client implementation
        """
        global DEFAULT_CLIENT_TYPE
        DEFAULT_CLIENT_TYPE = client_type
    
    @classmethod
    def get_default_client_type(cls) -> str:
        """Get the current default client type.
        
        Returns:
            Current default client type
        """
        return DEFAULT_CLIENT_TYPE
    
    @staticmethod
    def get_page_html(url: str, wait_time: int = 30, options = None, headless: bool = True) -> Optional[str]:
        """Open a webpage and get its HTML content.
        
        Args:
            url: The URL to visit
            wait_time: Time to wait for page load in seconds
            options: Browser options to use
            headless: Whether to run browser in headless mode
            
        Returns:
            HTML content of the page or None if an error occurred
        """
        client = BrowserClientFactory.create_client(DEFAULT_CLIENT_TYPE, DEFAULT_BROWSER_TYPE)
        return client.get_page_html(url, wait_time, headless, options)
            
    @staticmethod
    def take_screenshot(url: str, output_path: str, wait_time: int = 30, options = None, headless: bool = True) -> bool:
        """Navigate to a URL and take a screenshot.
        
        Args:
            url: The URL to visit
            output_path: Path where the screenshot should be saved
            wait_time: Time to wait for page load in seconds
            options: Browser options to use
            headless: Whether to run browser in headless mode
            
        Returns:
            True if screenshot was successful, False otherwise
        """
        client = BrowserClientFactory.create_client(DEFAULT_CLIENT_TYPE, DEFAULT_BROWSER_TYPE)
        return client.take_screenshot(url, output_path, wait_time, headless, options)
