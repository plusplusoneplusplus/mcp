"""Selenium-based browser client implementation.

This module provides a browser client implementation using Selenium WebDriver.
"""

import os
import time
import shutil
import socket
import subprocess
import platform
import asyncio
from typing import Optional, Dict, Any, Union, Literal
from concurrent.futures import ThreadPoolExecutor

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

from mcp_tools.browser.interface import IBrowserClient
from mcp_tools.plugin import register_tool

class SeleniumBrowserClient(IBrowserClient):
    async def capture_panels(self, url: str, selector: str = ".react-grid-item", out_dir: str = "charts", width: int = 1600, height: int = 900, token: Optional[str] = None, wait_time: int = 30, headless: bool = True, options: Any = None) -> int:
        """
        Capture each matching element as an image and save to the output directory.
        """
        import pathlib
        import re
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.action_chains import ActionChains
        out_path = pathlib.Path(out_dir)
        out_path.mkdir(exist_ok=True, parents=True)
        def _capture():
            driver = self._setup_browser(headless=headless, browser_options=options)
            try:
                # Set viewport size
                driver.set_window_size(width, height)
                # Set Authorization header if possible
                if token:
                    try:
                        driver.execute_cdp_cmd('Network.enable', {})
                        driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {"headers": {"Authorization": f"Bearer {token}"}})
                    except Exception:
                        print("Warning: Could not set Authorization header via Selenium. Proceeding without it.")
                driver.get(url)
                time.sleep(wait_time)
                panels = driver.find_elements(By.CSS_SELECTOR, selector)
                if not panels:
                    print(f"No elements matched '{selector}'.")
                    return 0
                count = 0
                for idx, el in enumerate(panels, 1):
                    pid = None
                    for attr in ["data-panelid", "data-griditem-key", "data-viz-panel-key"]:
                        try:
                            pid = el.get_attribute(attr)
                        except Exception:
                            pid = None
                        if pid:
                            match = re.search(r'(?:panel|grid-item)-(\d+)', pid)
                            if match:
                                pid = match.group(1)
                            break
                    if not pid:
                        pid = f"{idx:02d}"
                    # Scroll element into view
                    try:
                        ActionChains(driver).move_to_element(el).perform()
                    except Exception:
                        pass
                    el.screenshot(str(out_path / f"panel_{pid}.png"))
                    print(f"Saved panel_{pid}.png")
                    count += 1
                return count
            except Exception as e:
                print(f"Error in capture_panels: {e}")
                return 0
            finally:
                self._cleanup_driver(driver)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, _capture)

    """Selenium-based browser client implementation.
    
    This class provides a browser automation implementation using Selenium WebDriver.
    It supports Chrome and Edge browsers.
    """
    
    # Default browser type to use
    DEFAULT_BROWSER_TYPE: Literal["chrome", "edge"] = "chrome"
    
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
    
    def __init__(self, browser_type: Literal["chrome", "edge"] = None):
        """Initialize the Selenium browser client.
        
        Args:
            browser_type: Type of browser to use ('chrome' or 'edge').
                         If None, uses DEFAULT_BROWSER_TYPE.
        """
        self.browser_type = browser_type or self.DEFAULT_BROWSER_TYPE
        self._executor = ThreadPoolExecutor(max_workers=1)
    
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
        def _get_html():
            driver = self._setup_browser(headless=headless, browser_options=options)
            try:
                # Navigate to the page
                print(f"Opening {url} with {self.browser_type.capitalize()}...")
                driver.get(url)

                # Wait for the page to load
                time.sleep(wait_time)

                # Get the page source
                html_content = driver.page_source
                return html_content

            except Exception as e:
                print(f"An error occurred: {e}")
                return None

            finally:
                # Clean up
                self._cleanup_driver(driver)
        
        return await asyncio.get_event_loop().run_in_executor(self._executor, _get_html)
    
    async def take_screenshot(self, url: str, output_path: str, wait_time: int = 30, 
                       headless: bool = True, options: Any = None, auto_scroll: bool = False,
                       scroll_timeout: int = 30, scroll_step: int = 300, scroll_delay: float = 0.3) -> bool:
        """Navigate to a URL and take a screenshot.
        
        Args:
            url: The URL to visit
            output_path: Path where the screenshot should be saved
            wait_time: Time to wait for page load in seconds
            headless: Whether to run browser in headless mode
            options: Browser-specific options
            auto_scroll: Whether to automatically scroll through the page before taking the screenshot
                        (Not implemented for Selenium client)
            scroll_timeout: Maximum time to spend auto-scrolling in seconds
                          (Not implemented for Selenium client)
            scroll_step: Pixel distance to scroll in each step
                       (Not implemented for Selenium client)
            scroll_delay: Delay between scroll steps in seconds
                        (Not implemented for Selenium client)
            
        Returns:
            True if screenshot was successful, False otherwise
        """
        if auto_scroll:
            print("Warning: Auto-scroll is not implemented for SeleniumBrowserClient")
            
        def _take_screenshot():
            driver = self._setup_browser(headless=headless, browser_options=options)
            try:
                # Navigate to the page
                print(f"Opening {url} with {self.browser_type.capitalize()} for screenshot...")
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
                self._cleanup_driver(driver)
        
        return await asyncio.get_event_loop().run_in_executor(self._executor, _take_screenshot)
    
    def _cleanup_driver(self, driver):
        """Clean up resources associated with a WebDriver.
        
        Args:
            driver: WebDriver instance to clean up
        """
        if hasattr(driver, "temp_dir"):
            try:
                shutil.rmtree(driver.temp_dir, ignore_errors=True)
            except Exception:
                pass
        driver.quit()
    
    def _setup_browser(self, headless: bool = False, browser_options = None) -> Union[webdriver.Chrome, webdriver.Edge]:
        """Set up and return a WebDriver instance for Chrome or Edge.
        
        Args:
            headless: Whether to run browser in headless mode
            browser_options: Pre-configured browser options. If provided, these will be merged
                          with default options, with browser_options taking precedence.
            
        Returns:
            Configured WebDriver instance
            
        Raises:
            Exception: If browser or driver cannot be set up properly
        """
        browser_type = self.browser_type
        
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
        debug_port = self._find_free_port()
        options.add_argument(f"--remote-debugging-port={debug_port}")
        
        # Merge browser_options if provided
        self._merge_browser_options(options, browser_options)
        
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
            system = platform.system()
            
            # Get cached driver path if available
            driver_path = self._get_cached_driver_path(system, browser_type)
            
            # If no valid cached path, find or download driver
            if not driver_path:
                if browser_type == "chrome":
                    driver_path = self._setup_chrome_driver(system)
                elif browser_type == "edge":
                    driver_path = self._setup_edge_driver(system)
                
                # Cache the driver path if we found one
                if driver_path and os.path.exists(driver_path):
                    self._cache_driver_path(system, browser_type, driver_path)
                
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
            self._print_troubleshooting_info(browser_type)
            raise
    
    def _get_cached_driver_path(self, system: str, browser_type: str) -> Optional[str]:
        """Get cached driver path for the given system and browser type.
        
        Args:
            system: Operating system name
            browser_type: Type of browser
            
        Returns:
            Cached driver path or None if not available
        """
        cache_key = self._get_cache_key(system)
        if cache_key and self._driver_cache[browser_type][cache_key]:
            cached_path = self._driver_cache[browser_type][cache_key]
            if os.path.exists(cached_path) and os.access(cached_path, os.X_OK):
                print(f"Using cached {browser_type.capitalize()}Driver at: {cached_path}")
                return cached_path
        return None
    
    def _cache_driver_path(self, system: str, browser_type: str, driver_path: str):
        """Cache driver path for future use.
        
        Args:
            system: Operating system name
            browser_type: Type of browser
            driver_path: Path to the driver executable
        """
        cache_key = self._get_cache_key(system)
        if cache_key:
            self._driver_cache[browser_type][cache_key] = driver_path
            print(f"Caching {browser_type.capitalize()}Driver path for {system} at: {driver_path}")
    
    def _get_cache_key(self, system: str) -> Optional[str]:
        """Get cache key for the given operating system.
        
        Args:
            system: Operating system name
            
        Returns:
            Cache key or None if unknown system
        """
        if system == "Darwin":  # macOS
            return "macos"
        elif system == "Windows":
            return "windows"
        elif system == "Linux":
            return "linux"
        return None
    
    def _merge_browser_options(self, options, browser_options):
        """Merge browser options into the default options.
        
        Args:
            options: Default browser options
            browser_options: Additional browser options to merge
        """
        if browser_options is None:
            return
            
        # Merge arguments from browser_options into options
        if hasattr(browser_options, 'arguments') and browser_options.arguments:
            for arg in browser_options.arguments:
                # Check if this is an argument that would override an existing one
                # For arguments with values (e.g., --user-data-dir=path), extract the arg name
                arg_name = arg.split('=')[0] if '=' in arg else arg
                
                # Remove any existing argument that starts with the same name
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
    
    def _find_free_port(self) -> int:
        """Find a free port for remote debugging.
        
        Returns:
            Available port number
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    def _setup_chrome_driver(self, system: str) -> Optional[str]:
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
                    if WEBDRIVER_MANAGER_AVAILABLE:
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
                    else:
                        print("webdriver_manager not available. Please install it with: pip install webdriver_manager")
                
                # Ensure chromedriver has execute permissions
                if driver_path and not os.access(driver_path, os.X_OK):
                    print(f"Adding execute permission to {driver_path}")
                    os.chmod(driver_path, 0o755)
                    
                # Remove macOS quarantine attribute if needed
                if driver_path and system == "Darwin":
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
                    if WEBDRIVER_MANAGER_AVAILABLE:
                        driver_path = ChromeDriverManager().install()
                    else:
                        print("webdriver_manager not available. Please install it with: pip install webdriver_manager")
            except Exception as e:
                print(f"Error with Windows 'where' command: {e}")
                if WEBDRIVER_MANAGER_AVAILABLE:
                    print("Using webdriver_manager instead...")
                    driver_path = ChromeDriverManager().install()
                else:
                    print("webdriver_manager not available. Please install it with: pip install webdriver_manager")
        else:
            # For Linux, first try 'which' command
            print("Using Linux-specific ChromeDriver setup...")
            try:
                driver_path = subprocess.getoutput("which chromedriver").strip()
                if driver_path and os.path.exists(driver_path):
                    print(f"Found ChromeDriver at: {driver_path}")
                else:
                    print("ChromeDriver not found in PATH, using webdriver_manager...")
                    if WEBDRIVER_MANAGER_AVAILABLE:
                        driver_path = ChromeDriverManager().install()
                    else:
                        print("webdriver_manager not available. Please install it with: pip install webdriver_manager")
            except Exception as e:
                print(f"Error with Linux 'which' command: {e}")
                if WEBDRIVER_MANAGER_AVAILABLE:
                    print("Using webdriver_manager instead...")
                    driver_path = ChromeDriverManager().install()
                else:
                    print("webdriver_manager not available. Please install it with: pip install webdriver_manager")
                
        return driver_path
        
    def _setup_edge_driver(self, system: str) -> Optional[str]:
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
                    if WEBDRIVER_MANAGER_AVAILABLE:
                        driver_path = EdgeChromiumDriverManager().install()
                    else:
                        print("webdriver_manager not available. Please install it with: pip install webdriver_manager")
            except Exception as e:
                print(f"Error with Windows 'where' command: {e}")
                if WEBDRIVER_MANAGER_AVAILABLE:
                    print("Using webdriver_manager instead...")
                    driver_path = EdgeChromiumDriverManager().install()
                else:
                    print("webdriver_manager not available. Please install it with: pip install webdriver_manager")
        else:
            # For macOS and Linux
            print(f"Setting up EdgeDriver on {system}...")
            try:
                # Try webdriver_manager directly
                if WEBDRIVER_MANAGER_AVAILABLE:
                    driver_path = EdgeChromiumDriverManager().install()
                    print(f"Installed EdgeDriver at: {driver_path}")
                    
                    # Ensure driver has execute permissions
                    if not os.access(driver_path, os.X_OK):
                        print(f"Adding execute permission to {driver_path}")
                        os.chmod(driver_path, 0o755)
                        
                    # Remove macOS quarantine attribute if on macOS
                    if system == "Darwin":
                        subprocess.run(["xattr", "-d", "com.apple.quarantine", driver_path], check=False)
                else:
                    print("webdriver_manager not available. Please install it with: pip install webdriver_manager")
            except Exception as e:
                print(f"Error setting up EdgeDriver on {system}: {e}")
                print("Microsoft Edge might not be fully supported on this platform.")
                raise
                
        return driver_path
    
    def _print_troubleshooting_info(self, browser_type: str):
        """Print troubleshooting information for browser setup issues.
        
        Args:
            browser_type: Type of browser
        """
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