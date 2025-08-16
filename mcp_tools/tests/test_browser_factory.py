import pytest
import sys
from pathlib import Path

# Add the parent directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from mcp_tools.browser.factory import BrowserClientFactory
from mcp_tools.browser.interface import IBrowserClient

# Import PlaywrightBrowserClient with proper error handling
try:
    from mcp_tools.browser.playwright_client import PlaywrightBrowserClient
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    PlaywrightBrowserClient = None


def test_factory_creates_correct_client_type():
    """Test that factory creates the right type of client"""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available, skipping test")
    
    # Create a playwright client using the factory
    client = BrowserClientFactory.create_client("playwright")

    # Check the instance type
    assert isinstance(client, PlaywrightBrowserClient)
    assert isinstance(client, IBrowserClient)


def test_factory_creates_with_browser_type():
    """Test that factory passes browser type to client"""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available, skipping test")
    
    # Create clients with different browser types
    chrome_client = BrowserClientFactory.create_client("playwright", None, "chrome")
    edge_client = BrowserClientFactory.create_client("playwright", None, "edge")

    # Check that browser type was set correctly
    assert chrome_client.browser == "chrome"
    assert edge_client.browser == "edge"


def test_factory_default_parameters():
    """Test that factory uses correct defaults"""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available, skipping Playwright-specific test")

    # Create a client with default parameters
    client = BrowserClientFactory.create_client()

    # Check defaults
    assert isinstance(client, PlaywrightBrowserClient)
    assert client.browser == "chrome"  # Default in PlaywrightBrowserClient


def test_factory_invalid_client_type():
    """Test that factory raises error for invalid client type"""
    # Try to create a client with an invalid type
    with pytest.raises(ValueError):
        BrowserClientFactory.create_client("invalid_type")
    
    # Test selenium is no longer supported
    with pytest.raises(ValueError):
        BrowserClientFactory.create_client("selenium")
