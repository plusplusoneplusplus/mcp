from typing import Optional, Any
from playwright.async_api import (
    async_playwright,
    Playwright,
    Browser,
    Page,
    BrowserContext,
)
import time


class PlaywrightWrapper:
    DEFAULT_WAIT_TIME = 30  # Default extra wait time (seconds) after navigation
    DEFAULT_AUTO_SCROLL_TIMEOUT = 30  # Default timeout for auto_scroll (seconds)

    def __init__(
        self,
        browser_type: str = "chromium",
        user_data_dir: Optional[str] = None,
        headless: bool = False,
    ):
        """
        Args:
            browser_type: Browser type string (e.g., 'chromium', 'firefox', 'webkit').
            user_data_dir: Optional path for persistent context.
            headless: Whether to run browser in headless mode (default: False).
        """
        self.browser_type = browser_type
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        browser_launcher = getattr(self.playwright, self.browser_type)
        if self.user_data_dir:
            self.browser = await browser_launcher.launch_persistent_context(
                user_data_dir=self.user_data_dir, headless=self.headless
            )
            self.context = self.browser
        else:
            self.browser = await browser_launcher.launch(headless=self.headless)
            self.context = await self.browser.new_context()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open_page(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        wait_time: int = DEFAULT_WAIT_TIME,
        extra_http_headers: Optional[dict] = None,
        goto_timeout: int = DEFAULT_WAIT_TIME,
    ):
        """
        Open a page and wait for the specified event.
        Args:
            url: URL to open.
            wait_until: When to consider navigation succeeded. Supported values:
                - 'load': Waits for the load event (all resources loaded).
                - 'domcontentloaded': Waits for the DOMContentLoaded event (default; DOM ready, but not all resources).
                - 'networkidle': Waits until there are no network connections for at least 500 ms.
                - 'commit': Considers navigation finished when the network response is received and the document starts loading.
            wait_time: Extra time (seconds) to wait after navigation (default DEFAULT_WAIT_TIME).
            extra_http_headers: Optional headers to set.
            goto_timeout: Max seconds to wait for navigation (default DEFAULT_WAIT_TIME).
        """
        if not self.context:
            raise RuntimeError(
                "Context not initialized. Use 'async with PlaywrightWrapper()' block."
            )
        self.page = await self.context.new_page()
        if extra_http_headers:
            await self.page.set_extra_http_headers(extra_http_headers)
        await self.page.goto(url, wait_until=wait_until, timeout=goto_timeout * 1000)
        await self.page.wait_for_timeout(wait_time * 1000)
        return self.page

    async def set_viewport_size(self, width: int, height: int):
        """
        Set the viewport size for the current page.
        Args:
            width: Width of the viewport in pixels.
            height: Height of the viewport in pixels.
        """
        if not self.page:
            raise RuntimeError("Page not initialized. Call open_page first.")
        await self.page.set_viewport_size({"width": width, "height": height})

    async def auto_scroll(
        self,
        timeout: int = DEFAULT_AUTO_SCROLL_TIMEOUT,
        scroll_step: int = 80,
        scroll_delay: float = 0.5,
    ):
        """
        Automatically scrolls the page to the bottom, simulating user scrolling.
        Args:
            timeout: Maximum time in seconds to keep scrolling (default DEFAULT_AUTO_SCROLL_TIMEOUT).
            scroll_step: Number of pixels to scroll per step (default 80).
            scroll_delay: Delay in seconds between scroll steps (default 0.5).
        """
        if not self.page:
            raise RuntimeError("Page not initialized. Call open_page first.")
        initial_height = await self.page.evaluate(
            """() => document.body.scrollHeight"""
        )
        start_time = time.time()
        last_height = initial_height
        while time.time() - start_time < timeout:
            current_position = await self.page.evaluate(
                f"""(step) => {{
                    let currentPos = window.pageYOffset || document.documentElement.scrollTop;
                    let newPos = currentPos + step;
                    window.scrollTo(0, newPos);
                    return newPos;
                }}""",
                scroll_step,
            )
            await self.page.wait_for_timeout(scroll_delay * 1000)
            new_height = await self.page.evaluate(
                """() => document.body.scrollHeight"""
            )
            current_scroll_position = await self.page.evaluate(
                """() => window.pageYOffset + window.innerHeight"""
            )
            if new_height > last_height:
                last_height = new_height
            if current_scroll_position >= new_height:
                break
        await self.page.wait_for_timeout(1000)
        await self.page.evaluate("""() => { window.scrollTo(0, 0); }""")

    async def locate_elements(self, selector: str):
        """
        Locate all elements matching the given selector on the current page.
        Args:
            selector: CSS selector string to match elements.
        Returns:
            List of element handles matching the selector.
        """
        if not self.page:
            raise RuntimeError("Page not initialized. Call open_page first.")
        return await self.page.locator(selector).all()

    async def take_screenshot(self, output_path: str, full_page: bool = True):
        if not self.page:
            raise RuntimeError("Page not initialized. Call open_page first.")
        await self.page.screenshot(path=output_path, full_page=full_page)

    async def close(self):
        if self.page:
            await self.page.close()
            self.page = None
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser and not self.browser_type == "chromium":
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
