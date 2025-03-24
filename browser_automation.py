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

def get_windows_chrome_path():
    """Get the path to Chrome in Windows from WSL"""
    possible_paths = [
        "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
        "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def setup_browser(headless=False):
    """
    Set up and return a Chrome WebDriver instance
    Args:
        headless (bool): Whether to run browser in headless mode
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")  # Run in headless mode if needed
    # chrome_options.add_argument("--start-maximized")
    
    # # WSL-specific configuration
    # chrome_path = get_windows_chrome_path()
    # if not chrome_path:
    #     raise Exception("Could not find Chrome installation in Windows")
   
    # # Set up Chrome driver to use Windows Chrome from WSL
    driver_path = subprocess.getoutput("which chromedriver").strip()
    service = Service(driver_path)
     
    # chrome_options.binary_location = chrome_path
    
    # Set up remote debugging port for WSL
    chrome_options.add_argument("--remote-debugging-port=9222")
    # Allow running as root in WSL if necessary
    # chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # Store the temp directory path in the driver object for cleanup
        return driver
    except Exception as e:
        # Clean up the temporary directory if driver creation fails
        print(f"Error setting up Chrome: {e}")
        print("\nTroubleshooting steps:")
        print("1. Make sure Chrome is installed in Windows")
        print("2. Install chromedriver in WSL: `apt install chromium-chromedriver`")
        print("3. Ensure you have X server running in Windows if not using headless mode")
        print("4. Try killing any existing Chrome processes:")
        print("   Windows: taskkill /F /IM chrome.exe")
        print("   WSL: pkill chrome")
        raise

def get_page_html(url, wait_time=30):
    """
    Open a webpage and get its HTML content
    Args:
        url (str): The URL to visit
        wait_time (int): Time to wait for page load in seconds
    """
    driver = setup_browser(headless=False)  # Set to True if you don't want to see the browser
    
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
        if hasattr(driver, 'temp_dir'):
            try:
                shutil.rmtree(driver.temp_dir, ignore_errors=True)
            except Exception:
                pass
        driver.quit()

if __name__ == "__main__":
    # Example usage
    url = "https://www.google.com"  # Replace with your target URL
    html = get_page_html(url)
    if html:
        print("HTML content length:", len(html))
        print("\nFirst 500 characters of HTML:")
        print(html[:500])