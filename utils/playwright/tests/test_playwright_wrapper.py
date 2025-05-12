import os
import tempfile
import pytest
import asyncio
from pathlib import Path
from utils.playwright.playwright_wrapper import PlaywrightWrapper

pytestmark = pytest.mark.asyncio

github_io_url = "https://github.com/"


def get_temp_screenshot_path():
    tmp_dir = tempfile.gettempdir()
    return os.path.join(tmp_dir, "test_pw_screenshot.png")


async def test_context_manager():
    async with PlaywrightWrapper(headless=True) as pw:
        assert pw.playwright is not None
        assert pw.context is not None
        assert pw.browser is not None


async def test_open_page():
    async with PlaywrightWrapper(headless=True) as pw:
        page = await pw.open_page(github_io_url, wait_time=3)
        assert page.url.startswith(github_io_url)
        assert "GitHub" in await page.title()


async def test_set_viewport_size():
    async with PlaywrightWrapper(headless=True) as pw:
        await pw.open_page(github_io_url, wait_time=3)
        await pw.set_viewport_size(800, 600)
        size = pw.page.viewport_size
        assert size == {"width": 800, "height": 600}


async def test_auto_scroll():
    async with PlaywrightWrapper(headless=True) as pw:
        await pw.open_page(github_io_url, wait_time=3)
        # This should not raise and should scroll to bottom
        await pw.auto_scroll(timeout=1, scroll_step=200, scroll_delay=0.1)
        # Check that we're still on the same page
        assert pw.page.url.startswith(github_io_url)


async def test_locate_elements():
    async with PlaywrightWrapper(headless=True) as pw:
        await pw.open_page(github_io_url, wait_time=3)
        # GitHub always has a header element
        elements = await pw.locate_elements("header")
        assert isinstance(elements, list)
        assert len(elements) > 0


async def test_take_screenshot():
    screenshot_path = get_temp_screenshot_path()
    try:
        async with PlaywrightWrapper(headless=True) as pw:
            await pw.open_page(github_io_url, wait_time=3)
            await pw.take_screenshot(screenshot_path, full_page=True)
            assert os.path.exists(screenshot_path)
            assert os.path.getsize(screenshot_path) > 0
    finally:
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
