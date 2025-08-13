"""Tests for retrieving cookies after manual Playwright login."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import PlaywrightBrowserClient with graceful fallback when Playwright is missing
try:  # pragma: no cover - import guard
    from mcp_tools.browser.playwright_client import PlaywrightBrowserClient
    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover - executed when Playwright isn't installed
    PlaywrightBrowserClient = None
    PLAYWRIGHT_AVAILABLE = False


@pytest.mark.asyncio
async def test_get_cookies_after_login_url_match():
    """Ensure cookies are returned after waiting for the target URL."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available, skipping Playwright-specific test")

    cookies = [{"name": "session", "value": "abc"}]

    mock_page = MagicMock()
    mock_page.wait_for_url = AsyncMock()

    mock_wrapper = MagicMock()
    mock_wrapper.open_page = AsyncMock(return_value=mock_page)
    mock_wrapper.get_cookies = AsyncMock(return_value=cookies)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_wrapper)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "mcp_tools.browser.playwright_client.PlaywrightWrapper", return_value=mock_cm
    ):
        client = PlaywrightBrowserClient("chrome", "user_dir")
        result = await client.get_cookies_after_login("https://login", "home")

    assert result == cookies
    mock_wrapper.open_page.assert_called_once_with(
        "https://login", wait_until="domcontentloaded", wait_time=0
    )
    mock_page.wait_for_url.assert_called_once()
    mock_wrapper.get_cookies.assert_called_once()

