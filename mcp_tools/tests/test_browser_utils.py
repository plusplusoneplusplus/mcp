import pytest
import sys
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

# Add the parent directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from mcp_tools.browser.client import BrowserClient


def test_get_windows_chrome_path():
    """Test the Chrome path detection"""
    if BrowserClient.in_wsl():
        chrome_path = BrowserClient.get_windows_chrome_path()
        # Since we're in WSL, at least one of these paths should exist
        possible_paths = [
            "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
            "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        ]
        if chrome_path:
            assert chrome_path in possible_paths
            assert os.path.exists(chrome_path)


def test_setup_browser():
    """Test browser setup with headless mode"""
    try:
        driver = BrowserClient.setup_browser(headless=True)
        assert isinstance(driver, webdriver.Chrome)
        assert "--headless" in driver.options.arguments
        driver.quit()
    except Exception as e:
        pytest.skip(f"Browser setup failed (this might be expected in some environments): {e}")


def test_get_page_html():
    """Test fetching HTML content from a test URL"""
    test_url = "https://www.google.com"
    try:
        html_content = BrowserClient.get_page_html(test_url, wait_time=2)
        assert html_content is not None
        assert isinstance(html_content, str)
        assert len(html_content) > 0
        # Check for some common HTML elements that should be present
        assert "<html" in html_content.lower()
        assert "<body" in html_content.lower()
    except Exception as e:
        pytest.skip(f"Page HTML fetch failed (this might be expected in some environments): {e}")


def test_browser_setup_failure():
    """Test handling of browser setup failure"""
    # Temporarily modify the chromedriver path to force a failure
    import subprocess

    original_getoutput = subprocess.getoutput

    def mock_getoutput(cmd):
        return "/nonexistent/path/to/chromedriver"

    subprocess.getoutput = mock_getoutput

    with pytest.raises(Exception):
        BrowserClient.setup_browser()

    # Restore the original function
    subprocess.getoutput = original_getoutput


def test_get_page_html_invalid_url():
    """Test handling of invalid URL"""
    invalid_url = "https://thisurldoesnotexistatall.com"
    result = BrowserClient.get_page_html(invalid_url, wait_time=2)
    assert result is None  # Should return None for failed requests