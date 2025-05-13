"""Playwright-based browser client implementation.

This module provides a browser client implementation using Playwright.
"""

import asyncio
import time
from typing import Optional, Dict, Any, Union, Literal

from mcp_tools.browser.interface import IBrowserClient
from utils.playwright.playwright_wrapper import PlaywrightWrapper
from config import env


class PlaywrightBrowserClient(IBrowserClient):
    def __init__(self, browser: Literal["chrome", "edge"], user_data_dir: str):
        """
        Args:
            browser: 'chrome' or 'edge'
            user_data_dir: path to a folder where profile (cookies, history) is stored
        """
        self.browser = browser
        self.user_data_dir = user_data_dir
        self.wrapper: Optional[PlaywrightWrapper] = PlaywrightWrapper(
            browser_type=browser, user_data_dir=user_data_dir
        )
        self.retry_capture_panels_keywords = [
            "LOADING"
        ]

    async def capture_panels(
        self,
        url: str,
        selector: str = ".react-grid-item",
        width: int = 1600,
        height: int = 900,
        token: Optional[str] = None,
        wait_time: int = 30,
        headless: bool = True,
        autoscroll: bool = False,
    ) -> int:
        """Capture each matching element as an image and save to the output directory."""
        import pathlib
        import re

        out_dir = env.get_setting("image_dir", ".images")
        out_path = pathlib.Path(out_dir)
        out_path.mkdir(exist_ok=True, parents=True)
        count = 0
        try:
            extra_headers = {"Authorization": f"Bearer {token}"} if token else None
            async with PlaywrightWrapper(browser_type=self.browser, user_data_dir=self.user_data_dir) as wrapper:
                await wrapper.open_page(
                    url,
                    wait_until="networkidle",
                    wait_time=wait_time,
                    extra_http_headers=extra_headers,
                )
                await wrapper.set_viewport_size(width, height)
                if autoscroll:
                    await wrapper.auto_scroll()
                panels = await wrapper.locate_elements(selector)
                if not panels:
                    print(f"No elements matched '{selector}'.")
                    return 0
                for idx, el in enumerate(panels, 1):
                    pid = None
                    for attr in ["data-panelid", "data-griditem-key", "data-viz-panel-key"]:
                        try:
                            pid = await el.get_attribute(attr)
                        except Exception:
                            pid = None
                        if pid:
                            match = re.search(r"(?:panel|grid-item)-(\d+)", pid)
                            if match:
                                pid = match.group(1)
                            break
                    if not pid:
                        pid = f"{idx:02d}"
                    # Check if element handle is valid and attached
                    if not el or (hasattr(el, "is_detached") and el.is_detached()):
                        print(
                            f"Warning: Element for panel {pid} is not attached or not found. Skipping."
                        )
                        continue
                    await wrapper.take_element_screenshot(
                        el, str(out_path / f"panel_{pid}.png")
                    )
                    print(f"Saved panel_{pid}.png")
                    count += 1
                return count
        except Exception as e:
            print(f"Error in capture_panels: {e}")
            return count

    async def __aenter__(self):
        """Support for async context manager."""
        if self.wrapper:
            await self.wrapper.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensure resources are cleaned up when exiting context."""
        await self.close()

    async def get_page_html(
        self, url: str, wait_time: int = 30, headless: bool = True, options: Any = None
    ) -> Optional[str]:
        try:
            html = await self.wrapper.get_page_html(
                url, wait_until="networkidle", wait_time=wait_time
            )
            return html
        except Exception:
            return None

    async def take_screenshot(
        self,
        url: str,
        output_path: str,
        wait_time: int = 30,
        headless: bool = True,
        options: Any = None,
        auto_scroll: bool = False,
        scroll_timeout: int = 30,
        scroll_step: int = 300,
        scroll_delay: float = 0.3,
    ) -> bool:
        try:
            await self.wrapper.open_page(url, wait_time=wait_time)
            if auto_scroll:
                print("Auto-scrolling page to load all content...")
                await self.wrapper.auto_scroll(
                    timeout=scroll_timeout,
                    scroll_step=scroll_step,
                    scroll_delay=scroll_delay,
                )
            await self.wrapper.take_screenshot(output_path, full_page=True)
            return True
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return False

    async def close(self):
        """Close the browser and clean up resources."""
        if self.wrapper:
            await self.wrapper.close()
            self.wrapper = None
