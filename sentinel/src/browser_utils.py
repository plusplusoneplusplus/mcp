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


class BrowserUtils:
    @staticmethod
    def in_wsl():
        return (
            os.path.exists("/proc/version") and "microsoft" in open("/proc/version").read().lower()
        )

    @staticmethod
    def get_windows_chrome_path():
        if BrowserUtils.in_wsl():
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
    def setup_browser(headless=False):
        """
        Set up and return a Chrome WebDriver instance
        Args:
            headless (bool): Whether to run browser in headless mode
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")  # Run in headless mode if needed

        # Set up Chrome driver to use Windows Chrome from WSL
        driver_path = subprocess.getoutput("which chromedriver").strip()
        service = Service(driver_path)

        # Set up remote debugging port for WSL
        chrome_options.add_argument("--remote-debugging-port=9222")

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

    @staticmethod
    def get_page_html(url, wait_time=30):
        """
        Open a webpage and get its HTML content
        Args:
            url (str): The URL to visit
            wait_time (int): Time to wait for page load in seconds
        """
        driver = BrowserUtils.setup_browser(
            headless=False
        )  # Set to True if you don't want to see the browser

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
