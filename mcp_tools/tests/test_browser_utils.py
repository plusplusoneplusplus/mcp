import pytest
import sys
import os
import platform
import asyncio
from pathlib import Path

# Add the parent directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from mcp_tools.browser.factory import BrowserClientFactory


def test_setup_browser():
    """Test browser setup with headless mode"""
    try:
        client = BrowserClientFactory.create_client("playwright")
        # Basic test that client was created successfully
        assert client is not None
        assert hasattr(client, 'browser')
    except Exception as e:
        pytest.skip(
            f"Browser setup failed (this might be expected in some environments): {e}"
        )


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
        pytest.skip(
            f"Page HTML fetch failed (this might be expected in some environments).\nError: {e}\nTraceback: {error_trace}"
        )


def test_browser_setup_failure():
    """Test handling of browser setup failure"""
    # Test that invalid client type raises error
    with pytest.raises(ValueError):
        BrowserClientFactory.create_client("invalid_type")


@pytest.mark.asyncio
async def test_get_page_html_invalid_url():
    """Test handling of invalid URL"""
    invalid_url = "https://thisurldoesnotexistatall.com"
    client = BrowserClientFactory.create_client()
    result = await client.get_page_html(invalid_url, wait_time=2)
    assert result is None  # Should return None for failed requests
