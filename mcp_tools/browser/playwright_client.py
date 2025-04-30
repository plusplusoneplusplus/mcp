"""Playwright-based browser client implementation.

This module provides a browser client implementation using Playwright.
"""

import time
import os
import asyncio
import json
import platform
from typing import Optional, Dict, Any, Union, Literal

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
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
    
    async def setup_google_auth(self, user_data_dir: str = None) -> bool:
        """Set up Google authentication with persistent context.
        
        This method implements several techniques to bypass Google's automated browser detection:
        
        1. Browser fingerprinting resistance:
           - Uses a real-looking user agent string based on the user's OS
           - Sets realistic viewport and screen dimensions
           - Configures proper locale and timezone settings
           - Disables automation-specific flags and properties
        
        2. WebDriver detection avoidance:
           - Overrides navigator.webdriver property to return false
           - Adds fake browser plugins that regular browsers would have
           - Uses Chrome-specific flags to disable automation detection
        
        3. Persistent authentication:
           - Stores and reuses authentication state between sessions
           - Uses storage_state to maintain cookies and localStorage
        
        4. Human-like behavior:
           - Runs in non-headless mode to appear like a regular browser
           - Uses longer timeouts for more realistic page loading times
           - Handles different authentication completion patterns
        
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
            
            # Ensure the directory exists
            os.makedirs(user_data_dir, exist_ok=True)
            
            # Path to storage state file
            storage_state_file = os.path.join(user_data_dir, "storage_state.json")
            
            # Load existing storage state if available
            storage_state = None
            if os.path.exists(storage_state_file):
                try:
                    with open(storage_state_file, 'r') as f:
                        storage_state = json.load(f)
                    print(f"Loaded existing authentication state from {storage_state_file}")
                except Exception as e:
                    print(f"Error loading storage state: {e}")
            
            # Set up browser with persistent context - using non-headless mode for Google auth
            if not self._browser:
                await self._setup_browser(headless=False, for_auth=True)
            
            # Determine OS for platform-specific settings
            system = platform.system()
            
            # Create a new context with realistic settings
            context_options = {
                "viewport": {"width": 1280, "height": 800},
                "storage_state": storage_state,
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36" if system == "Darwin" else 
                             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36" if system == "Windows" else
                             "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "screen": {"width": 1920, "height": 1080},
                "has_touch": False,
                "is_mobile": False,
                "color_scheme": "light",
                "locale": "en-US",
                "timezone_id": "America/Los_Angeles",
            }
            
            self._context = await self._browser.new_context(**context_options)
            
            # Open a new page
            page = await self._context.new_page()
            
            # Add additional page properties
            await page.add_init_script("""
                // Override the webdriver property to avoid detection
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                
                // Add fake plugins to mimic a real browser
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            name: "Chrome PDF Plugin"
                        }
                    ]
                });
            """)
            
            # Navigate to Google login
            print("Opening Google login page...")
            await page.goto("https://accounts.google.com", {"timeout": 60000})
            print("Google login page loaded")
            
            # Wait for manual login
            print("\n" + "="*50)
            print("Please log in to your Google account in the browser window.")
            print("Follow these steps:")
            print("1. Enter your email and click 'Next'")
            print("2. Enter your password and click 'Next'")
            print("3. Complete any additional verification steps if required")
            print("The browser will close automatically after successful login.")
            print("="*50 + "\n")
            
            # Wait for URL change to indicate successful login
            try:
                await page.wait_for_url("https://myaccount.google.com/**", timeout=0)
                print("Successfully logged in to Google account!")
            except Exception as e:
                print(f"Waiting for alternative success URL patterns...")
                # Alternative success patterns
                await page.wait_for_url("**/u/0/**", timeout=0)
                print("Successfully logged in to Google account!")
            
            # Save the storage state for future use
            await self._context.storage_state(path=storage_state_file)
            print(f"Saved authentication state to {storage_state_file}")
            
            # Close the page but keep the context
            await page.close()
            
            return True
            
        except Exception as e:
            print(f"Error setting up Google authentication: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_page_html(self, url: str, wait_time: int = 30, headless: bool = True, 
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
                await self._setup_browser(headless=headless, options=options)
            
            # Use existing context if available, otherwise create new one
            if self._context:
                page = await self._context.new_page()
            else:
                context = await self._browser.new_context()
                page = await context.new_page()
            
            # Navigate to the page
            print(f"Opening {url} with {self.browser_type.capitalize()}...")
            await page.goto(url)
            
            # Wait for the page to load
            await asyncio.sleep(wait_time)
            
            # Get the page content
            html_content = await page.content()
            
            # Clean up
            if not self._context:  # Only close context if we created it
                await context.close()
            await page.close()
            
            return html_content
            
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
    async def take_screenshot(self, url: str, output_path: str, wait_time: int = 30, 
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
                await self._setup_browser(headless=headless, options=options)
            
            # Create a new context and page
            context = await self._browser.new_context()
            page = await context.new_page()
            
            # Navigate to the page
            print(f"Opening {url} with {self.browser_type.capitalize()} for screenshot...")
            await page.goto(url)
            
            # Wait for the page to load
            await asyncio.sleep(wait_time)
            
            # Take screenshot
            await page.screenshot(path=output_path)
            print(f"Screenshot saved to {output_path}")
            
            # Clean up
            await context.close()
            
            return True
            
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return False
            
        finally:
            # Clean up browser if needed
            if self._browser:
                await self._cleanup_browser()
    
    async def _setup_browser(self, headless: bool = False, options: Any = None, for_auth: bool = False):
        """Set up and return a Playwright browser instance.
        
        Args:
            headless: Whether to run browser in headless mode
            options: Browser-specific options
            for_auth: Whether the browser is being set up for authentication
            
        Raises:
            Exception: If browser cannot be set up properly
        """
        try:
            # Launch Playwright
            self._playwright = await async_playwright().start()
            
            # Get the browser type
            browser_type = getattr(self._playwright, self.browser_type)
            
            # Launch browser with options
            launch_options = {
                "headless": headless,
            }
            
            # Add special args to avoid detection
            if for_auth:
                if self.browser_type == "chromium":
                    launch_options["args"] = [
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-features=AutomationControlled",
                        "--disable-dev-shm-usage"
                    ]
                elif self.browser_type == "firefox":
                    launch_options["firefox_user_prefs"] = {
                        "dom.webdriver.enabled": False,
                        "privacy.trackingprotection.enabled": False
                    }
            
            # Merge additional options if provided
            if options:
                # Remove user_data_dir from options as it's not a valid launch option
                options_copy = options.copy()
                if "user_data_dir" in options_copy:
                    del options_copy["user_data_dir"]
                launch_options.update(options_copy)
            
            print(f"Setting up {self.browser_type.capitalize()} browser...")
            self._browser = await browser_type.launch(**launch_options)
            print(f"{self.browser_type.capitalize()} browser successfully created")
            
        except Exception as e:
            print(f"Error setting up {self.browser_type.capitalize()}: {e}")
            self._print_troubleshooting_info()
            raise
    
    async def _cleanup_browser(self):
        """Clean up resources associated with the browser."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
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