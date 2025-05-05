"""Browser client for web automation.

This module provides a client for browser automation operations.
"""

import time
from typing import Dict, Any, Optional, Literal

from mcp_tools.browser.factory import BrowserClientFactory
from mcp_tools.plugin import register_tool
from mcp_tools.interfaces import BrowserClientInterface
import trafilatura

# Global configuration
DEFAULT_BROWSER_TYPE: Literal["chrome", "edge"] = "chrome"
DEFAULT_CLIENT_TYPE: str = "playwright"
MAX_RETURN_CHARS: int = 100000

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
                    "description": "The operation to perform (get_page_html, take_screenshot, get_page_markdown)",
                    "enum": ["get_page_html", "take_screenshot", "get_page_markdown"],
                    "default": "get_page_markdown"
                },
                "url": {
                    "type": "string",
                    "description": "The URL to visit"
                },
                "wait_time": {
                    "type": "integer",
                    "description": "Time to wait for page load in seconds",
                    "default": 7 
                },
                "output_path": {
                    "type": "string",
                    "description": "Path where the screenshot should be saved (for take_screenshot)",
                    "nullable": True
                },
                "include_links": {
                    "type": "boolean",
                    "description": "Whether to include links in the extracted markdown (for get_page_markdown)",
                    "default": True
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Whether to include image references in the extracted markdown (for get_page_markdown)",
                    "default": False
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
        wait_time = arguments.get("wait_time", 7)
        headless = arguments.get("headless", False)
        browser_options = arguments.get("browser_options", None)
        browser_type = arguments.get("browser_type", self.browser_type)
        client_type = arguments.get("client_type", self.client_type)
        
        # Use the BrowserClientFactory to create the client
        client = BrowserClientFactory.create_client(client_type, user_data_dir=None, browser_type=browser_type)
        
        if operation == "get_page_html":
            html = await client.get_page_html(url, wait_time, headless, browser_options)
            if html:
                return {
                    "success": True,
                    "html": html[:MAX_RETURN_CHARS] + ("..." if len(html) > MAX_RETURN_CHARS else ""),
                    "html_length": len(html)
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to retrieve HTML from {url}"
                }
        elif operation == "take_screenshot":
            output_path = arguments.get("output_path", f"screenshot_{int(time.time())}.png")
            success = await client.take_screenshot(url, output_path, wait_time, headless, browser_options)
            return {
                "success": success,
                "output_path": output_path
            }
        elif operation == "get_page_markdown":
            include_links = arguments.get("include_links", True)
            include_images = arguments.get("include_images", True)
            
            html = await client.get_page_html(url, wait_time, headless, browser_options)
            if not html:
                return {
                    "success": False,
                    "error": f"Failed to retrieve HTML from {url}"
                }
            
            extracted_text = trafilatura.extract(
                html,
                output_format="markdown",
                include_links=include_links,
                include_images=include_images
            )
            
            # If extraction failed, return an empty string
            if not extracted_text:
                extracted_text = ""
                
            return {
                "success": True,
                "markdown": extracted_text[:MAX_RETURN_CHARS] + ("..." if len(extracted_text) > MAX_RETURN_CHARS else ""),
                "markdown_length": len(extracted_text),
                "url": url
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

    async def get_page_html(self, url: str, wait_time: int = 30) -> Optional[str]:
        raise NotImplementedError("get_page_html should be implemented by the real client")
    
    async def take_screenshot(self, url: str, output_path: str, wait_time: int = 30) -> bool:
        raise NotImplementedError("take_screenshot should be implemented by the real client")