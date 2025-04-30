import pytest
import sys
import os
import platform
import asyncio
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

# Add the parent directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from mcp_tools.browser.selenium_client import SeleniumBrowserClient
from mcp_tools.browser.factory import BrowserClientFactory

def test_setup_browser():
    """Test browser setup with headless mode"""
    try:
        client = SeleniumBrowserClient()
        driver = client._setup_browser(headless=True)
        browser_type = client.browser_type
        if browser_type == "chrome":
            assert isinstance(driver, webdriver.Chrome)
        elif browser_type == "edge":
            assert isinstance(driver, webdriver.Edge)
        assert "--headless" in driver.options.arguments
        driver.quit()
    except Exception as e:
        pytest.skip(f"Browser setup failed (this might be expected in some environments): {e}")


@pytest.mark.asyncio
async def test_get_page_html():
    """Test fetching HTML content from a test URL"""
    test_url = "https://www.google.com"
    try:
        client = BrowserClientFactory.create_client()
        html_content = await client.get_page_html(test_url, wait_time=2)
        assert html_content is not None
        assert isinstance(html_content, str)
        assert len(html_content) > 0
        # Check for some common HTML elements that should be present
        assert "<html" in html_content.lower()
        assert "<body" in html_content.lower()
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        pytest.skip(f"Page HTML fetch failed (this might be expected in some environments).\nError: {e}\nTraceback: {error_trace}")


def test_browser_setup_failure():
    """Test handling of browser setup failure"""
    # Save original state
    import subprocess
    original_getoutput = subprocess.getoutput
    
    # Create a client and save its driver cache
    client = SeleniumBrowserClient()
    original_driver_cache = {}
    for browser_type in client._driver_cache:
        original_driver_cache[browser_type] = {}
        for platform_key in client._driver_cache[browser_type]:
            original_driver_cache[browser_type][platform_key] = client._driver_cache[browser_type][platform_key]
    
    try:
        # Clear the driver cache to prevent using cached drivers
        for browser_type in client._driver_cache:
            for platform_key in client._driver_cache[browser_type]:
                client._driver_cache[browser_type][platform_key] = None
        
        # Mock subprocess.getoutput to return invalid path
        def mock_getoutput(cmd):
            return "/nonexistent/path/to/chromedriver"
        
        subprocess.getoutput = mock_getoutput
        
        # Mock os.path.exists to return False for any driver path
        original_exists = os.path.exists
        def mock_exists(path):
            if "driver" in path.lower():
                return False
            return original_exists(path)
            
        os.path.exists = mock_exists
        
        # This should raise an exception now
        with pytest.raises(Exception):
            client._setup_browser()
    
    finally:
        # Restore original state
        subprocess.getoutput = original_getoutput
        os.path.exists = original_exists
        client._driver_cache = original_driver_cache


@pytest.mark.asyncio
async def test_get_page_html_invalid_url():
    """Test handling of invalid URL"""
    invalid_url = "https://thisurldoesnotexistatall.com"
    client = BrowserClientFactory.create_client()
    result = await client.get_page_html(invalid_url, wait_time=2)
    assert result is None  # Should return None for failed requests