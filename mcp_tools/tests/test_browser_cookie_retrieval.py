"""Tests for retrieving cookies after manual Playwright login."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_tools.kv_store.tool import _kv_store

# Import PlaywrightBrowserClient with graceful fallback when Playwright is missing
try:  # pragma: no cover - import guard
    from mcp_tools.browser.playwright_client import PlaywrightBrowserClient
    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover - executed when Playwright isn't installed
    PlaywrightBrowserClient = None
    PLAYWRIGHT_AVAILABLE = False


@pytest.mark.asyncio
async def test_get_cookies_after_login_url_match():
    """Ensure cookies are saved after waiting for the target URL."""
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

    _kv_store.clear()

    with patch(
        "mcp_tools.browser.playwright_client.PlaywrightWrapper", return_value=mock_cm
    ):
        client = PlaywrightBrowserClient("chrome", "user_dir")
        result = await client.get_cookies_after_login(
            "https://login", "home", store_key="test_cookies"
        )

    assert result == "test_cookies"
    assert _kv_store.get("test_cookies") == cookies
    mock_wrapper.open_page.assert_called_once_with(
        "https://login", wait_until="domcontentloaded", wait_time=0
    )
    mock_page.wait_for_url.assert_called_once()
    mock_wrapper.get_cookies.assert_called_once()


@pytest.mark.asyncio
async def test_get_cookies_after_login_default_key():
    """Ensure cookies are saved under a domain-based key when none provided."""
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

    _kv_store.clear()

    with patch(
        "mcp_tools.browser.playwright_client.PlaywrightWrapper", return_value=mock_cm
    ):
        client = PlaywrightBrowserClient("chrome", "user_dir")
        result = await client.get_cookies_after_login(
            "https://example.com/login", "home"
        )

    assert result == "browser.cookies/example.com"
    assert _kv_store.get("browser.cookies/example.com") == cookies
