import pytest
import sys
import os
import platform
from pathlib import Path
from unittest.mock import patch, MagicMock
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

# Add the parent directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from mcp_tools.browser.selenium_client import SeleniumBrowserClient


class TestBrowserClientOptions:
    """Tests for SeleniumBrowserClient options merging functionality."""

    @patch('mcp_tools.browser.selenium_client.webdriver.Chrome')
    @patch('mcp_tools.browser.selenium_client.ChromeService')
    @patch('socket.socket')
    def test_default_options(self, mock_socket, mock_service, mock_chrome):
        """Test that default options are set correctly."""
        # Setup mock socket to return a fixed port
        mock_socket_instance = MagicMock()
        mock_socket_instance.getsockname.return_value = ('', 12345)
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        # Setup mock chrome driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Setup mock driver path finding
        with patch.object(SeleniumBrowserClient, '_setup_chrome_driver', return_value='/path/to/chromedriver'):
            # Create a client
            client = SeleniumBrowserClient(browser_type="chrome")
            # Call the _setup_browser method
            client._setup_browser()

        # Check that Chrome was called with the expected options
        options = mock_chrome.call_args[1]['options']
        assert "--no-sandbox" in options.arguments
        assert "--disable-dev-shm-usage" in options.arguments
        assert "--disable-gpu" in options.arguments
        assert "--remote-debugging-port=12345" in options.arguments
        assert "--headless" not in options.arguments

    @patch('mcp_tools.browser.selenium_client.webdriver.Chrome')
    @patch('mcp_tools.browser.selenium_client.ChromeService')
    @patch('socket.socket')
    def test_headless_option(self, mock_socket, mock_service, mock_chrome):
        """Test that headless mode is set correctly."""
        # Setup mock socket to return a fixed port
        mock_socket_instance = MagicMock()
        mock_socket_instance.getsockname.return_value = ('', 12345)
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        # Setup mock chrome driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Setup mock driver path finding
        with patch.object(SeleniumBrowserClient, '_setup_chrome_driver', return_value='/path/to/chromedriver'):
            # Create a client
            client = SeleniumBrowserClient(browser_type="chrome")
            # Call the _setup_browser method with headless=True
            client._setup_browser(headless=True)

        # Check that Chrome was called with the expected options
        options = mock_chrome.call_args[1]['options']
        assert "--headless" in options.arguments

    @patch('mcp_tools.browser.selenium_client.webdriver.Chrome')
    @patch('mcp_tools.browser.selenium_client.ChromeService')
    @patch('socket.socket')
    def test_custom_options_override(self, mock_socket, mock_service, mock_chrome):
        """Test that custom options override default options when they conflict."""
        # Setup mock socket to return a fixed port
        mock_socket_instance = MagicMock()
        mock_socket_instance.getsockname.return_value = ('', 12345)
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        # Setup mock chrome driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Create custom options with overrides
        custom_options = ChromeOptions()
        custom_options.add_argument("--disable-gpu=false")  # Override default --disable-gpu
        custom_options.add_argument("--user-data-dir=/path/to/profile")  # Add new option
        
        # Setup mock driver path finding
        with patch.object(SeleniumBrowserClient, '_setup_chrome_driver', return_value='/path/to/chromedriver'):
            # Create a client
            client = SeleniumBrowserClient(browser_type="chrome")
            # Call the _setup_browser method with custom options
            client._setup_browser(browser_options=custom_options)

        # Check that Chrome was called with the expected options
        options = mock_chrome.call_args[1]['options']
        
        # The default options should be present
        assert "--no-sandbox" in options.arguments
        assert "--disable-dev-shm-usage" in options.arguments
        
        # The overridden option should have the custom value
        assert "--disable-gpu=false" in options.arguments
        assert "--disable-gpu" not in options.arguments
        
        # The new option should be present
        assert "--user-data-dir=/path/to/profile" in options.arguments

    @patch('mcp_tools.browser.selenium_client.webdriver.Chrome')
    @patch('mcp_tools.browser.selenium_client.ChromeService')
    @patch('socket.socket')
    def test_experimental_options_merge(self, mock_socket, mock_service, mock_chrome):
        """Test that experimental options are properly merged."""
        # Setup mock socket to return a fixed port
        mock_socket_instance = MagicMock()
        mock_socket_instance.getsockname.return_value = ('', 12345)
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        # Setup mock chrome driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Create custom options with experimental options
        custom_options = ChromeOptions()
        custom_options.add_experimental_option("prefs", {
            "profile.default_content_settings.popups": 0,
            "download.default_directory": "/custom/download/path"
        })
        
        # Setup mock driver path finding
        with patch.object(SeleniumBrowserClient, '_setup_chrome_driver', return_value='/path/to/chromedriver'):
            # Create a client
            client = SeleniumBrowserClient(browser_type="chrome")
            # Call the _setup_browser method with custom options
            client._setup_browser(browser_options=custom_options)

        # Check that Chrome was called with the expected options
        options = mock_chrome.call_args[1]['options']
        
        # The experimental options should be present
        assert options.experimental_options.get("prefs") is not None
        prefs = options.experimental_options.get("prefs")
        assert prefs.get("profile.default_content_settings.popups") == 0
        assert prefs.get("download.default_directory") == "/custom/download/path"

    @patch('mcp_tools.browser.selenium_client.webdriver.Chrome')
    @patch('mcp_tools.browser.selenium_client.ChromeService')
    @patch('socket.socket')
    def test_profile_options(self, mock_socket, mock_service, mock_chrome):
        """Test that profile options are properly set."""
        # Setup mock socket to return a fixed port
        mock_socket_instance = MagicMock()
        mock_socket_instance.getsockname.return_value = ('', 12345)
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        # Setup mock chrome driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Create custom options with profile settings
        custom_options = ChromeOptions()
        custom_options.add_argument("--user-data-dir=/path/to/user/data")
        custom_options.add_argument("--profile-directory=Profile 1")
        
        # Setup mock driver path finding
        with patch.object(SeleniumBrowserClient, '_setup_chrome_driver', return_value='/path/to/chromedriver'):
            # Create a client
            client = SeleniumBrowserClient(browser_type="chrome")
            # Call the _setup_browser method with custom options
            client._setup_browser(browser_options=custom_options)

        # Check that Chrome was called with the expected options
        options = mock_chrome.call_args[1]['options']
        
        # Default options should be present
        assert "--no-sandbox" in options.arguments
        assert "--disable-dev-shm-usage" in options.arguments
        assert "--disable-gpu" in options.arguments
        
        # Profile options should be present
        assert "--user-data-dir=/path/to/user/data" in options.arguments
        assert "--profile-directory=Profile 1" in options.arguments

    @patch('mcp_tools.browser.selenium_client.webdriver.Edge')
    @patch('mcp_tools.browser.selenium_client.EdgeService')
    @patch('socket.socket')
    def test_edge_browser_options(self, mock_socket, mock_service, mock_edge):
        """Test that options are correctly applied for Edge browser."""
        # Setup mock socket to return a fixed port
        mock_socket_instance = MagicMock()
        mock_socket_instance.getsockname.return_value = ('', 12345)
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        # Setup mock edge driver
        mock_driver = MagicMock()
        mock_edge.return_value = mock_driver
        
        # Create custom options for Edge
        custom_options = EdgeOptions()
        custom_options.add_argument("--user-data-dir=/path/to/edge/user/data")
        custom_options.add_argument("--profile-directory=Profile 1")
        
        # Setup mock driver path finding
        with patch.object(SeleniumBrowserClient, '_setup_edge_driver', return_value='/path/to/msedgedriver'):
            # Create a client
            client = SeleniumBrowserClient(browser_type="edge")
            # Call the _setup_browser method with custom options
            client._setup_browser(browser_options=custom_options)

        # Check that Edge was called with the expected options
        options = mock_edge.call_args[1]['options']
        
        # Default options should be present
        assert "--no-sandbox" in options.arguments
        assert "--disable-dev-shm-usage" in options.arguments
        assert "--disable-gpu" in options.arguments
        
        # Profile options should be present
        assert "--user-data-dir=/path/to/edge/user/data" in options.arguments
        assert "--profile-directory=Profile 1" in options.arguments

    @patch('mcp_tools.browser.selenium_client.webdriver.Chrome')
    @patch('mcp_tools.browser.selenium_client.ChromeService')
    @patch('socket.socket')
    def test_headless_with_custom_options(self, mock_socket, mock_service, mock_chrome):
        """Test that headless mode is correctly applied when custom options are provided."""
        # Setup mock socket to return a fixed port
        mock_socket_instance = MagicMock()
        mock_socket_instance.getsockname.return_value = ('', 12345)
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        # Setup mock chrome driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Create custom options without headless
        custom_options = ChromeOptions()
        custom_options.add_argument("--user-data-dir=/path/to/user/data")
        
        # Setup mock driver path finding
        with patch.object(SeleniumBrowserClient, '_setup_chrome_driver', return_value='/path/to/chromedriver'):
            # Create a client
            client = SeleniumBrowserClient(browser_type="chrome")
            # Call the _setup_browser method with custom options and headless=True
            client._setup_browser(browser_options=custom_options, headless=True)

        # Check that Chrome was called with the expected options
        options = mock_chrome.call_args[1]['options']
        
        # Headless mode should be set
        assert "--headless" in options.arguments
        
        # Custom options should be present
        assert "--user-data-dir=/path/to/user/data" in options.arguments

    @patch('mcp_tools.browser.selenium_client.webdriver.Chrome')
    @patch('mcp_tools.browser.selenium_client.ChromeService')
    @patch('socket.socket')
    def test_custom_headless_option_respected(self, mock_socket, mock_service, mock_chrome):
        """Test that custom headless option is respected and not duplicated."""
        # Setup mock socket to return a fixed port
        mock_socket_instance = MagicMock()
        mock_socket_instance.getsockname.return_value = ('', 12345)
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        # Setup mock chrome driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Create custom options with headless already set
        custom_options = ChromeOptions()
        custom_options.add_argument("--headless=new")  # Chrome's new headless mode
        
        # Setup mock driver path finding
        with patch.object(SeleniumBrowserClient, '_setup_chrome_driver', return_value='/path/to/chromedriver'):
            # Create a client
            client = SeleniumBrowserClient(browser_type="chrome")
            # Call the _setup_browser method with custom options and headless=True
            client._setup_browser(browser_options=custom_options, headless=True)

        # Check that Chrome was called with the expected options
        options = mock_chrome.call_args[1]['options']
        
        # Custom headless mode should be present
        assert "--headless=new" in options.arguments
        
        # Standard headless mode should not be added
        headless_count = sum(1 for arg in options.arguments if arg.startswith("--headless"))
        assert headless_count == 1  # Only one headless option should be present 