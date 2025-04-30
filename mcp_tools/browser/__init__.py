"""Browser automation module.

This module provides browser automation capabilities for web scraping and testing.
"""

from mcp_tools.browser.client import BrowserClient
from mcp_tools.browser.selenium_client import SeleniumBrowserClient
from mcp_tools.browser.interface import IBrowserClient
from mcp_tools.browser.factory import BrowserClientFactory
from mcp_tools.browser.types import (
    PageContent,
    ScreenshotResult,
    BrowserOptions,
)

__all__ = [
    "BrowserClient",  # For backward compatibility
    "SeleniumBrowserClient",
    "IBrowserClient",
    "BrowserClientFactory",
    "PageContent",
    "ScreenshotResult",
    "BrowserOptions",
]
