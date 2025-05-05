"""Playwright-based browser client implementation.

This module provides a browser client implementation using Playwright.
"""

import asyncio
from typing import Optional, Dict, Any, Union, Literal

from playwright.async_api import async_playwright, Playwright, BrowserContext
from mcp_tools.browser.interface import IBrowserClient

class PlaywrightBrowserClient(IBrowserClient):
    def __init__(self,
                 browser: Literal['chrome', 'edge'],
                 user_data_dir: str):
        """
        Args:
            browser: 'chrome' or 'edge'
            user_data_dir: path to a folder where profile (cookies, history) is stored
        """
        self.browser = browser
        self.user_data_dir = user_data_dir
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        
    async def __aenter__(self):
        """Support for async context manager."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensure resources are cleaned up when exiting context."""
        await self.close()

    async def _get_context(self, headless: bool) -> BrowserContext:
        # launch Playwright once
        if not self.playwright:
            self.playwright = await async_playwright().start()

        # create (or reuse) a persistent context
        if not self.context:
            # Playwright uses 'chrome' and 'msedge' as channel names
            channel = 'chrome' if self.browser == 'chrome' else 'msedge'
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                channel=channel,
                headless=headless,
            )
        return self.context
    
    async def _get_new_page(self, headless: bool):
        ctx = await self._get_context(headless)
        page = ctx.pages[0]            # already open about:blank page
        return page

    async def get_page_html(self,
                            url: str,
                            wait_time: int = 30,
                            headless: bool = True,
                            options: Any = None) -> Optional[str]:
        page = None
        try:
            page = await self._get_new_page(headless)
            page.set_default_navigation_timeout(wait_time * 1000)
            await page.goto(url)
            # wait for network to be quiet, adjust as needed
            # await page.wait_for_load_state('networkidle', timeout=wait_time * 1000)
            await page.wait_for_timeout(wait_time * 1000)
            return await page.content()
        except Exception:
            return None
        finally:
            if page is not None:
                await page.close()

    async def take_screenshot(self,
                              url: str,
                              output_path: str,
                              wait_time: int = 30,
                              headless: bool = True,
                              options: Any = None) -> bool:
        page = None
        try:
            page = await self._get_new_page(headless)
            page.set_default_navigation_timeout(wait_time * 1000)
            await page.goto(url)
            # await page.wait_for_load_state('networkidle', timeout=wait_time * 1000)
            await page.wait_for_timeout(wait_time * 1000)
            await page.screenshot(path=output_path, full_page=True)
            return True
        except Exception:
            return False
        finally:
            if page is not None:
                await page.close()

    async def close(self):
        """Clean up Playwright resources when you're done."""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
            # Force garbage collection to release resources
            import gc
            gc.collect()
        except Exception as e:
            print(f"Error during cleanup: {e}")