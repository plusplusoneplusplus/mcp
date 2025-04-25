from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import subprocess
import tempfile
import shutil
from datetime import datetime
import socket
from typing import Optional, Dict, Any, List

# Import interface
from mcp_tools.interfaces import BrowserClientInterface

class BrowserClient(BrowserClientInterface):
    """Client for browser automation operations.
    
    This class provides a simplified interface for browser operations like opening pages,
    capturing screenshots, etc. using Selenium and Chrome.
    
    Example:
        # Create a browser client
        browser = BrowserClient()
        
        # Get HTML content of a page
        html = browser.get_page_html("https://example.com")
    """
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
        
        if operation == "get_page_html":
            html = self.get_page_html(url, wait_time)
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
            success = self.take_screenshot(url, output_path, wait_time)
            return {
                "success": success,
                "output_path": output_path
            }
        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}"
            }

    @staticmethod
    def in_wsl() -> bool:
        """Check if running in Windows Subsystem for Linux.
        
        Returns:
            True if running in WSL, False otherwise.
        """
        return (
            os.path.exists("/proc/version") and 
            "microsoft" in open("/proc/version").read().lower()
        )

    @staticmethod
    def get_windows_chrome_path() -> Optional[str]:
        """Get the path to Chrome browser in Windows (or from WSL).
        
        Returns:
            Path to the Chrome executable or None if not found.
        """
        if BrowserClient.in_wsl():
            """Get the path to Chrome in Windows from WSL"""
            possible_paths = [
                "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
                "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            ]
        else:
            possible_paths = [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    @staticmethod
    def setup_browser(headless: bool = False) -> webdriver.Chrome:
        """Set up and return a Chrome WebDriver instance.
        
        Args:
            headless: Whether to run browser in headless mode
            
        Returns:
            Configured Chrome WebDriver instance
            
        Raises:
            Exception: If Chrome or chromedriver cannot be set up properly
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")  # Run in headless mode if needed

        # Set up Chrome driver 
        if os.name == "nt":  # Windows
            driver_path = subprocess.getoutput("where chromedriver").strip()
        else:  # Linux/Unix
            driver_path = subprocess.getoutput("which chromedriver").strip()
        service = Service(driver_path)

        # Use a dynamic port for remote debugging to avoid conflicts
        def find_free_port():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', 0))
                return s.getsockname()[1]
                
        debug_port = find_free_port()
        chrome_options.add_argument(f"--remote-debugging-port={debug_port}")

        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except Exception as e:
            print(f"Error setting up Chrome: {e}")
            print("\nTroubleshooting steps:")
            print("1. Make sure Chrome is installed in Windows")
            print("2. Install chromedriver in WSL: `apt install chromium-chromedriver`")
            print("3. Ensure you have X server running in Windows if not using headless mode")
            print("4. Try killing any existing Chrome processes:")
            print("   Windows: taskkill /F /IM chrome.exe")
            print("   WSL: pkill chrome")
            raise

    def get_page_html(self, url: str, wait_time: int = 30) -> Optional[str]:
        """Open a webpage and get its HTML content.
        
        Args:
            url: The URL to visit
            wait_time: Time to wait for page load in seconds
            
        Returns:
            HTML content of the page or None if an error occurred
        """
        driver = self.setup_browser(headless=False)  # Set to True if you don't want to see the browser

        try:
            # Navigate to the page
            print(f"Opening {url}...")
            driver.get(url)

            # Wait for the page to load (adjust time as needed)
            time.sleep(wait_time)

            # Get the page source
            html_content = driver.page_source

            return html_content

        except Exception as e:
            print(f"An error occurred: {e}")
            return None

        finally:
            # Clean up
            if hasattr(driver, "temp_dir"):
                try:
                    shutil.rmtree(driver.temp_dir, ignore_errors=True)
                except Exception:
                    pass
            driver.quit()
            
    def take_screenshot(self, url: str, output_path: str, wait_time: int = 30) -> bool:
        """Navigate to a URL and take a screenshot.
        
        Args:
            url: The URL to visit
            output_path: Path where the screenshot should be saved
            wait_time: Time to wait for page load in seconds
            
        Returns:
            True if screenshot was successful, False otherwise
        """
        driver = self.setup_browser(headless=True)

        try:
            # Navigate to the page
            print(f"Opening {url} for screenshot...")
            driver.get(url)

            # Wait for the page to load
            time.sleep(wait_time)

            # Take screenshot
            driver.save_screenshot(output_path)
            print(f"Screenshot saved to {output_path}")
            
            return True

        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return False

        finally:
            # Clean up
            if hasattr(driver, "temp_dir"):
                try:
                    shutil.rmtree(driver.temp_dir, ignore_errors=True)
                except Exception:
                    pass
            driver.quit() 