from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import subprocess
import tempfile
import shutil
from datetime import datetime
import socket
from typing import Optional, Dict, Any, List, Union, Literal

# Import interface
from mcp_tools.interfaces import BrowserClientInterface
# Import the plugin decorator
from mcp_tools.plugin import register_tool

# Global configuration for the browser type to use
# Valid values: "chrome" or "edge"
DEFAULT_BROWSER_TYPE: Literal["chrome", "edge"] = "chrome"

@register_tool
class BrowserClient(BrowserClientInterface):
    """Client for browser automation operations.
    
    This class provides a simplified interface for browser operations like opening pages,
    capturing screenshots, etc. using Selenium with Chrome or Microsoft Edge.
    The browser used is controlled by the DEFAULT_BROWSER_TYPE global variable.
    
    Example:
        # Create a browser client
        browser = BrowserClient()
        
        # Get HTML content of a page
        html = browser.get_page_html("https://example.com")
    """
    # Class-level cache for WebDriver paths
    _driver_cache = {
        "chrome": {
            "windows": None,
            "macos": None,
            "linux": None
        },
        "edge": {
            "windows": None,
            "macos": None,
            "linux": None
        }
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
        headless = arguments.get("headless", True)
        browser_options = arguments.get("browser_options", None)
        
        if operation == "get_page_html":
            html = BrowserClient.get_page_html(url, wait_time, options=browser_options, headless=headless)
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
            success = BrowserClient.take_screenshot(url, output_path, wait_time, options=browser_options, headless=headless)
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
    def get_windows_browser_path(browser_type: Literal["chrome", "edge"] = None) -> Optional[str]:
        """Get the path to browser executable in Windows (or from WSL).
        
        Args:
            browser_type: Type of browser to locate ('chrome' or 'edge').
                          If None, uses DEFAULT_BROWSER_TYPE.
            
        Returns:
            Path to the browser executable or None if not found.
        """
        if browser_type is None:
            browser_type = DEFAULT_BROWSER_TYPE
            
        if browser_type == "chrome":
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
        elif browser_type == "edge":
            if BrowserClient.in_wsl():
                """Get the path to Edge in Windows from WSL"""
                possible_paths = [
                    "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
                    "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe",
                ]
            else:
                possible_paths = [
                    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
                ]
        else:
            return None
            
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    @staticmethod
    def setup_browser(headless: bool = False, browser_type: Literal["chrome", "edge"] = None, browser_options = None) -> Union[webdriver.Chrome, webdriver.Edge]:
        """Set up and return a WebDriver instance for Chrome or Edge.
        
        Args:
            headless: Whether to run browser in headless mode
            browser_type: Type of browser to use ('chrome' or 'edge').
                          If None, uses DEFAULT_BROWSER_TYPE.
            browser_options: Pre-configured browser options. If provided, these will be merged
                          with default options, with browser_options taking precedence.
            
        Returns:
            Configured WebDriver instance
            
        Raises:
            Exception: If browser or driver cannot be set up properly
        """
        if browser_type is None:
            browser_type = DEFAULT_BROWSER_TYPE
        
        # Create default options based on browser type
        if browser_type == "chrome":
            options = ChromeOptions()
        elif browser_type == "edge":
            options = EdgeOptions()
        else:
            raise ValueError(f"Unsupported browser type: {browser_type}")
            
        # Add default options for better stability and compatibility
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # Use a dynamic port for remote debugging to avoid conflicts
        def find_free_port():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', 0))
                return s.getsockname()[1]
                
        debug_port = find_free_port()
        options.add_argument(f"--remote-debugging-port={debug_port}")
        
        # Merge browser_options if provided
        if browser_options is not None:
            # Merge arguments from browser_options into options
            # This will allow browser_options to override default options
            if hasattr(browser_options, 'arguments') and browser_options.arguments:
                for arg in browser_options.arguments:
                    # Check if this is an argument that would override an existing one
                    # For arguments with values (e.g., --user-data-dir=path), extract the arg name
                    arg_name = arg.split('=')[0] if '=' in arg else arg
                    
                    # Remove any existing argument that starts with the same name
                    # Since we can't modify options.arguments directly, we need to:
                    # 1. Find conflicting arguments
                    # 2. Clear all arguments 
                    # 3. Add back non-conflicting ones
                    conflicting_args = []
                    non_conflicting_args = []
                    
                    for a in options.arguments:
                        if a.startswith(arg_name):
                            conflicting_args.append(a)
                        else:
                            non_conflicting_args.append(a)
                    
                    # If we found any conflicting args, clear and rebuild the arguments list
                    if conflicting_args:
                        # Clear all arguments
                        while options.arguments:
                            options.arguments.pop()
                        
                        # Add back non-conflicting args
                        for a in non_conflicting_args:
                            options.add_argument(a)
                    
                    # Add the new argument
                    options.add_argument(arg)
                    
            # Copy other attributes from browser_options if they exist
            if hasattr(browser_options, 'experimental_options') and browser_options.experimental_options:
                for key, value in browser_options.experimental_options.items():
                    options.add_experimental_option(key, value)
                    
            # Copy extension related settings if any
            if hasattr(browser_options, 'extensions') and browser_options.extensions:
                for extension in browser_options.extensions:
                    options.add_extension(extension)
        
        # Set headless mode if needed (this should be last to ensure it's not overridden)
        if headless:
            # Check if any argument starts with --headless
            has_headless = False
            for arg in options.arguments:
                if arg.startswith('--headless'):
                    has_headless = True
                    break
            
            if not has_headless:
                options.add_argument("--headless")

        print(f"Setting up {browser_type.capitalize()} browser...")
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
                
            # Check if we have a cached driver path for this OS and browser
            if cache_key and BrowserClient._driver_cache[browser_type][cache_key]:
                cached_path = BrowserClient._driver_cache[browser_type][cache_key]
                if os.path.exists(cached_path) and os.access(cached_path, os.X_OK):
                    print(f"Using cached {browser_type.capitalize()}Driver at: {cached_path}")
                    driver_path = cached_path
            
            # If no valid cached path, find or download driver
            if not driver_path:
                if browser_type == "chrome":
                    driver_path = BrowserClient._setup_chrome_driver(system)
                elif browser_type == "edge":
                    driver_path = BrowserClient._setup_edge_driver(system)
                
                # Cache the driver path if we found one
                if driver_path and os.path.exists(driver_path):
                    BrowserClient._driver_cache[browser_type][cache_key] = driver_path
                    print(f"Caching {browser_type.capitalize()}Driver path for {system} at: {driver_path}")
                
            print(f"Using {browser_type.capitalize()}Driver at: {driver_path}")
            
            if browser_type == "chrome":
                service = ChromeService(driver_path)
                print("Creating Chrome WebDriver...")
                driver = webdriver.Chrome(service=service, options=options)
            elif browser_type == "edge":
                service = EdgeService(driver_path)
                print("Creating Edge WebDriver...")
                driver = webdriver.Edge(service=service, options=options)
                
            print(f"{browser_type.capitalize()} WebDriver successfully created")
            return driver
        except Exception as e:
            print(f"Error setting up {browser_type.capitalize()}: {e}")
            print("\nTroubleshooting steps:")
            print(f"1. Make sure {browser_type.capitalize()} is installed")
            if browser_type == "chrome":
                print("2. If using macOS, you can install ChromeDriver via Homebrew: brew install --cask chromedriver")
                print("3. If using macOS and seeing permission issues, run: xattr -d com.apple.quarantine <path_to_chromedriver>")
                print("4. If using Windows, ensure Chrome is installed and try installing chromedriver manually")
                print("5. If using Linux, try: apt-get install chromium-chromedriver or equivalent for your distribution")
            elif browser_type == "edge":
                print("2. If using Windows, ensure Edge is installed (it's included with Windows 10+)")
                print("3. You can manually download EdgeDriver from: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/")
                print("4. Make sure the EdgeDriver version matches your Edge browser version")
            print(f"6. Ensure you have the latest {browser_type.capitalize()} browser installed")
            print("7. Try killing any existing browser processes:")
            if browser_type == "chrome":
                print("   Windows: taskkill /F /IM chrome.exe")
                print("   macOS/Linux: pkill chrome")
            elif browser_type == "edge":
                print("   Windows: taskkill /F /IM msedge.exe")
                print("   macOS/Linux: pkill msedge")
            raise

    @staticmethod
    def _setup_chrome_driver(system: str) -> Optional[str]:
        """Set up and return ChromeDriver path for the given operating system.
        
        Args:
            system: Operating system name
            
        Returns:
            Path to the ChromeDriver or None if not found
        """
        driver_path = None
        
        if system == "Darwin":  # macOS
            print("Using macOS-specific ChromeDriver setup...")
            try:
                # Try to find chromedriver using 'which' command
                driver_path = subprocess.getoutput("which chromedriver").strip()
                if driver_path and os.path.exists(driver_path):
                    print(f"Found ChromeDriver at: {driver_path}")
                else:
                    # If not found, use webdriver_manager but ensure we get the correct driver
                    print("ChromeDriver not found in PATH, using webdriver_manager...")
                    from webdriver_manager.core.os_manager import ChromeType
                    
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
                
        return driver_path
        
    @staticmethod
    def _setup_edge_driver(system: str) -> Optional[str]:
        """Set up and return EdgeDriver path for the given operating system.
        
        Args:
            system: Operating system name
            
        Returns:
            Path to the EdgeDriver or None if not found
        """
        driver_path = None
        
        if system == "Windows":
            # For Windows, first try 'where' command
            print("Using Windows-specific EdgeDriver setup...")
            try:
                driver_path = subprocess.getoutput("where msedgedriver").split('\n')[0].strip()
                if driver_path and os.path.exists(driver_path):
                    print(f"Found EdgeDriver at: {driver_path}")
                else:
                    print("EdgeDriver not found in PATH, using webdriver_manager...")
                    driver_path = EdgeChromiumDriverManager().install()
            except Exception as e:
                print(f"Error with Windows 'where' command: {e}")
                print("Using webdriver_manager instead...")
                driver_path = EdgeChromiumDriverManager().install()
        else:
            # For macOS and Linux
            print(f"Setting up EdgeDriver on {system}...")
            try:
                # Try webdriver_manager directly
                driver_path = EdgeChromiumDriverManager().install()
                print(f"Installed EdgeDriver at: {driver_path}")
                
                # Ensure driver has execute permissions
                if not os.access(driver_path, os.X_OK):
                    print(f"Adding execute permission to {driver_path}")
                    os.chmod(driver_path, 0o755)
                    
                # Remove macOS quarantine attribute if on macOS
                if system == "Darwin":
                    subprocess.run(["xattr", "-d", "com.apple.quarantine", driver_path], check=False)
            except Exception as e:
                print(f"Error setting up EdgeDriver on {system}: {e}")
                print("Microsoft Edge might not be fully supported on this platform.")
                raise
                
        return driver_path

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
        driver = BrowserClient.setup_browser(headless=headless, browser_options=options)  # Uses DEFAULT_BROWSER_TYPE

        try:
            # Navigate to the page
            print(f"Opening {url} with {DEFAULT_BROWSER_TYPE.capitalize()}...")
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
        driver = BrowserClient.setup_browser(headless=headless, browser_options=options)  # Uses DEFAULT_BROWSER_TYPE

        try:
            # Navigate to the page
            print(f"Opening {url} with {DEFAULT_BROWSER_TYPE.capitalize()} for screenshot...")
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