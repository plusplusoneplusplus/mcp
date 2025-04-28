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
# Import the plugin decorator
from mcp_tools.plugin import register_tool

@register_tool
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
    # Class-level cache for ChromeDriver paths
    _driver_cache = {
        "windows": None,
        "macos": None,
        "linux": None
    }
    
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
            html = BrowserClient.get_page_html(url, wait_time)
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
            success = BrowserClient.take_screenshot(url, output_path, wait_time)
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

        # Add additional options for better stability and compatibility
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        # Use a dynamic port for remote debugging to avoid conflicts
        def find_free_port():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', 0))
                return s.getsockname()[1]
                
        debug_port = find_free_port()
        chrome_options.add_argument(f"--remote-debugging-port={debug_port}")

        print("Setting up Chrome browser...")
        try:
            # Detect operating system
            import platform
            system = platform.system()
            
            # Get cached driver path if available
            driver_path = None
            cache_key = None
            
            if system == "Darwin":  # macOS
                cache_key = "macos"
            elif system == "Windows":
                cache_key = "windows"
            else:  # Linux and others
                cache_key = "linux"
                
            # Check if we have a cached driver path for this OS
            if cache_key and BrowserClient._driver_cache[cache_key]:
                cached_path = BrowserClient._driver_cache[cache_key]
                if os.path.exists(cached_path) and os.access(cached_path, os.X_OK):
                    print(f"Using cached ChromeDriver at: {cached_path}")
                    driver_path = cached_path
            
            # If no valid cached path, find or download chromedriver
            if not driver_path:
                if system == "Darwin":  # macOS
                    print("Using macOS-specific ChromeDriver setup...")
                    try:
                        # Try to find chromedriver using 'which' command
                        import subprocess
                        driver_path = subprocess.getoutput("which chromedriver").strip()
                        if driver_path and os.path.exists(driver_path):
                            print(f"Found ChromeDriver at: {driver_path}")
                        else:
                            # If not found, use webdriver_manager but ensure we get the correct driver
                            print("ChromeDriver not found in PATH, using webdriver_manager...")
                            from webdriver_manager.core.os_manager import ChromeType
                            from webdriver_manager.chrome import ChromeDriverManager

                            driver_path = ChromeDriverManager().install()
                            chromedriver_dir = os.path.dirname(driver_path)
                            # Look for the actual chromedriver binary in the same directory
                            for file in os.listdir(chromedriver_dir):
                                if file.startswith("chromedriver") and not file.endswith((".zip", ".chromedriver")):
                                    potential_path = os.path.join(chromedriver_dir, file)
                                    if os.access(potential_path, os.X_OK):
                                        driver_path = potential_path
                                        print(f"Using executable ChromeDriver at: {driver_path}")
                                        break
                        
                        # Ensure chromedriver has execute permissions
                        if not os.access(driver_path, os.X_OK):
                            print(f"Adding execute permission to {driver_path}")
                            os.chmod(driver_path, 0o755)
                            
                        # Remove macOS quarantine attribute if needed
                        subprocess.run(["xattr", "-d", "com.apple.quarantine", driver_path], check=False)
                    except Exception as e:
                        print(f"Error setting up macOS ChromeDriver: {e}")
                        raise
                elif system == "Windows":
                    # For Windows, first try 'where' command
                    print("Using Windows-specific ChromeDriver setup...")
                    try:
                        import subprocess
                        driver_path = subprocess.getoutput("where chromedriver").split('\n')[0].strip()
                        if driver_path and os.path.exists(driver_path):
                            print(f"Found ChromeDriver at: {driver_path}")
                        else:
                            print("ChromeDriver not found in PATH, using webdriver_manager...")
                            driver_path = ChromeDriverManager().install()
                    except Exception as e:
                        print(f"Error with Windows 'where' command: {e}")
                        print("Using webdriver_manager instead...")
                        driver_path = ChromeDriverManager().install()
                else:
                    # For Linux, first try 'which' command
                    print("Using Linux-specific ChromeDriver setup...")
                    try:
                        import subprocess
                        driver_path = subprocess.getoutput("which chromedriver").strip()
                        if driver_path and os.path.exists(driver_path):
                            print(f"Found ChromeDriver at: {driver_path}")
                        else:
                            print("ChromeDriver not found in PATH, using webdriver_manager...")
                            driver_path = ChromeDriverManager().install()
                    except Exception as e:
                        print(f"Error with Linux 'which' command: {e}")
                        print("Using webdriver_manager instead...")
                        driver_path = ChromeDriverManager().install()
                
                # Cache the driver path if we found one
                if driver_path and os.path.exists(driver_path):
                    BrowserClient._driver_cache[cache_key] = driver_path
                    print(f"Caching ChromeDriver path for {system} at: {driver_path}")
                
            print(f"Using ChromeDriver at: {driver_path}")
            service = Service(driver_path)
            print("Creating Chrome WebDriver...")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Chrome WebDriver successfully created")
            return driver
        except Exception as e:
            print(f"Error setting up Chrome: {e}")
            print("\nTroubleshooting steps:")
            print("1. Make sure Chrome is installed")
            print("2. If using macOS, you can install ChromeDriver via Homebrew: brew install --cask chromedriver")
            print("3. If using macOS and seeing permission issues, run: xattr -d com.apple.quarantine <path_to_chromedriver>")
            print("4. If using Windows, ensure Chrome is installed and try installing chromedriver manually")
            print("5. If using Linux, try: apt-get install chromium-chromedriver or equivalent for your distribution")
            print("6. Ensure you have the latest Chrome browser installed")
            print("7. Try killing any existing Chrome processes:")
            print("   Windows: taskkill /F /IM chrome.exe")
            print("   macOS/Linux: pkill chrome")
            raise

    @staticmethod
    def get_page_html(url: str, wait_time: int = 30) -> Optional[str]:
        """Open a webpage and get its HTML content.
        
        Args:
            url: The URL to visit
            wait_time: Time to wait for page load in seconds
            
        Returns:
            HTML content of the page or None if an error occurred
        """
        driver = BrowserClient.setup_browser(headless=True)  # Set to True for headless mode

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
            
    @staticmethod
    def take_screenshot(url: str, output_path: str, wait_time: int = 30) -> bool:
        """Navigate to a URL and take a screenshot.
        
        Args:
            url: The URL to visit
            output_path: Path where the screenshot should be saved
            wait_time: Time to wait for page load in seconds
            
        Returns:
            True if screenshot was successful, False otherwise
        """
        driver = BrowserClient.setup_browser(headless=True)

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