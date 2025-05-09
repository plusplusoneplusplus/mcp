"""Playwright-based browser client implementation.

This module provides a browser client implementation using Playwright.
"""

import asyncio
import time
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

    async def _auto_scroll_page(self, 
                              page, 
                              timeout: int = 30, 
                              scroll_step: int = 300, 
                              scroll_delay: float = 0.3) -> None:
        """
        Auto-scroll a page to ensure all content is loaded.
        
        Args:
            page: Playwright page object
            timeout: Maximum time to spend scrolling in seconds
            scroll_step: Pixel distance to scroll in each step
            scroll_delay: Delay between scroll steps in seconds
            
        Returns:
            None
        """
        # Get initial page height
        initial_height = await page.evaluate("""() => {
            return document.body.scrollHeight;
        }""")
        
        print(f"Starting auto-scroll - Initial page height: {initial_height}px")
        
        # Auto-scroll with timeout
        start_time = time.time()
        last_height = initial_height
        total_scrolled = 0
        
        while time.time() - start_time < timeout:
            # Scroll down by step
            current_position = await page.evaluate(f"""(step) => {{
                let currentPos = window.pageYOffset || document.documentElement.scrollTop;
                let newPos = currentPos + step;
                window.scrollTo(0, newPos);
                return newPos;
            }}""", scroll_step)
            
            total_scrolled += scroll_step
            print(f"Scrolled to position: {current_position}px")
            
            # Wait for content to load
            await page.wait_for_timeout(scroll_delay * 1000)
            
            # Check if we've reached the bottom
            new_height = await page.evaluate("""() => {
                return document.body.scrollHeight;
            }""")
            
            # If height hasn't changed and we're at the bottom, we're done
            current_scroll_position = await page.evaluate("""() => {
                return window.pageYOffset + window.innerHeight;
            }""")
            
            if new_height > last_height:
                print(f"Page height increased: {last_height}px -> {new_height}px")
                last_height = new_height
            
            # If we've scrolled to the bottom, break
            if current_scroll_position >= new_height:
                print(f"Reached bottom of page at {current_scroll_position}px")
                break
        
        # Final wait to ensure all content is loaded
        await page.wait_for_timeout(1000)
        
        # Scroll back to top if needed
        await page.evaluate("""() => {
            window.scrollTo(0, 0);
        }""")
        
        final_height = await page.evaluate("""() => {
            return document.body.scrollHeight;
        }""")
        
        print(f"Auto-scroll complete - Final page height: {final_height}px")
        print(f"Height increased by: {final_height - initial_height}px")
        print(f"Total time scrolling: {time.time() - start_time:.2f} seconds")

    async def take_screenshot(self,
                              url: str,
                              output_path: str,
                              wait_time: int = 30,
                              headless: bool = True,
                              options: Any = None,
                              auto_scroll: bool = False,
                              scroll_timeout: int = 30,
                              scroll_step: int = 300,
                              scroll_delay: float = 0.3) -> bool:
        page = None
        try:
            page = await self._get_new_page(headless)
            page.set_default_navigation_timeout(wait_time * 1000)
            await page.goto(url)
            
            # Wait for initial page load
            await page.wait_for_timeout(wait_time * 1000)
            
            # Auto-scroll if requested
            if auto_scroll:
                print("Auto-scrolling page to load all content...")
                await self._auto_scroll_page(
                    page,
                    timeout=scroll_timeout,
                    scroll_step=scroll_step,
                    scroll_delay=scroll_delay
                )
            
            # Take screenshot (full page)
            await page.screenshot(path=output_path, full_page=True)
            return True
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return False
        finally:
            if page is not None:
                await page.close()

    async def close(self):
        """Close the browser and clean up resources."""
        if self.context:
            await self.context.close()
            self.context = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None