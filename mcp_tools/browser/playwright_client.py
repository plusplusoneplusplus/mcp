"""Playwright-based browser client implementation.

This module provides a browser client implementation using Playwright.
"""

import time
import os
from typing import Optional, Dict, Any, Union, Literal

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from mcp_tools.browser.interface import IBrowserClient


class PlaywrightBrowserClient(IBrowserClient):
    """Playwright-based browser client implementation.
    
    This class provides a browser automation implementation using Playwright.
    It supports Chromium, Firefox, and WebKit browsers.
    """
    
    # Default browser type to use
    DEFAULT_BROWSER_TYPE: Literal["chromium", "firefox", "webkit"] = "chromium"
    
    def __init__(self, browser_type: Literal["chromium", "firefox", "webkit"] = None):
        """Initialize the Playwright browser client.
        
        Args:
            browser_type: Type of browser to use ('chromium', 'firefox', or 'webkit').
                         If None, uses DEFAULT_BROWSER_TYPE.
        """
        self.browser_type = browser_type or self.DEFAULT_BROWSER_TYPE
        self._playwright = None
        self._browser = None
        self._context = None
        self._user_data_dir = None
    
    def setup_google_auth(self, user_data_dir: str = None) -> bool:
        """Set up Google authentication with persistent context.
        
        Args:
            user_data_dir: Path to user data directory for persistent storage.
                          If None, a temporary directory will be used.
        
        Returns:
            True if setup was successful, False otherwise
        """
        try:
            # Create user data directory if not provided
            if not user_data_dir:
                import tempfile
                user_data_dir = tempfile.mkdtemp(prefix="playwright_")
            
            self._user_data_dir = user_data_dir
            
            # Set up browser with persistent context
            if not self._browser:
                self._setup_browser(headless=False, options={
                    "user_data_dir": user_data_dir
                })
            
            # Create a new context with persistent storage
            self._context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_data_dir=user_data_dir
            )
            
            # Open a new page
            page = self._context.new_page()
            
            # Navigate to Google login
            page.goto("https://accounts.google.com")
            
            # Wait for manual login
            print("Please log in to your Google account in the browser window.")
            print("The browser will close automatically after successful login.")
            
            # Wait for URL change to indicate successful login
            page.wait_for_url("https://myaccount.google.com/**", timeout=0)
            
            # Close the page but keep the context
            page.close()
            
            return True
            
        except Exception as e:
            print(f"Error setting up Google authentication: {e}")
            return False
    
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
        try:
            # Set up browser if not already done
            if not self._browser:
                self._setup_browser(headless=headless, options=options)
            
            # Use existing context if available, otherwise create new one
            if self._context:
                page = self._context.new_page()
            else:
                context = self._browser.new_context()
                page = context.new_page()
            
            # Navigate to the page
            print(f"Opening {url} with {self.browser_type.capitalize()}...")
            page.goto(url)
            
            # Wait for the page to load
            time.sleep(wait_time)
            
            # Get the page content
            html_content = page.content()
            
            # Clean up
            if not self._context:  # Only close context if we created it
                context.close()
            page.close()
            
            return html_content
            
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
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
        try:
            # Set up browser if not already done
            if not self._browser:
                self._setup_browser(headless=headless, options=options)
            
            # Create a new context and page
            context = self._browser.new_context()
            page = context.new_page()
            
            # Navigate to the page
            print(f"Opening {url} with {self.browser_type.capitalize()} for screenshot...")
            page.goto(url)
            
            # Wait for the page to load
            time.sleep(wait_time)
            
            # Take screenshot
            page.screenshot(path=output_path)
            print(f"Screenshot saved to {output_path}")
            
            # Clean up
            context.close()
            
            return True
            
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return False
            
        finally:
            # Clean up browser if needed
            if self._browser:
                self._cleanup_browser()
    
    def _setup_browser(self, headless: bool = False, options: Any = None):
        """Set up and return a Playwright browser instance.
        
        Args:
            headless: Whether to run browser in headless mode
            options: Browser-specific options
            
        Raises:
            Exception: If browser cannot be set up properly
        """
        try:
            # Launch Playwright
            self._playwright = sync_playwright().start()
            
            # Get the browser type
            browser_type = getattr(self._playwright, self.browser_type)
            
            # Launch browser with options
            launch_options = {
                "headless": headless,
            }
            
            # Merge additional options if provided
            if options:
                launch_options.update(options)
            
            print(f"Setting up {self.browser_type.capitalize()} browser...")
            self._browser = browser_type.launch(**launch_options)
            print(f"{self.browser_type.capitalize()} browser successfully created")
            
        except Exception as e:
            print(f"Error setting up {self.browser_type.capitalize()}: {e}")
            self._print_troubleshooting_info()
            raise
    
    def _cleanup_browser(self):
        """Clean up resources associated with the browser."""
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
    
    def _print_troubleshooting_info(self):
        """Print troubleshooting information for browser setup issues."""
        print("\nTroubleshooting steps:")
        print(f"1. Make sure {self.browser_type.capitalize()} is installed")
        print("2. Run 'playwright install' to install browsers")
        print("3. Ensure you have the latest version of Playwright installed")
        print("4. Check system requirements at https://playwright.dev/docs/intro#system-requirements")
        print("5. Try killing any existing browser processes:")
        if self.browser_type == "chromium":
            print("   Windows: taskkill /F /IM chrome.exe")
            print("   macOS/Linux: pkill chrome")
        elif self.browser_type == "firefox":
            print("   Windows: taskkill /F /IM firefox.exe")
            print("   macOS/Linux: pkill firefox")
        elif self.browser_type == "webkit":
            print("   Windows: taskkill /F /IM safari.exe")
            print("   macOS/Linux: pkill safari") 