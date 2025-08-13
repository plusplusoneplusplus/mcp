from typing import Optional, Any
from playwright.async_api import (
    async_playwright,
    Playwright,
    Browser,
    Page,
    BrowserContext,
)
import time
import os


class PlaywrightWrapper:
    async def evaluate_dom_tree(
        self,
        do_highlight_elements: bool = True,
        focus_highlight_index: int = -1,
        viewport_expansion: int = 0,
        debug_mode: bool = False,
    ) -> dict:
        """
        Evaluate the DOM tree by injecting and executing buildDomTree.js in the page context.
        Args:
            do_highlight_elements: Whether to highlight elements.
            focus_highlight_index: Which element to focus highlight (-1 for all).
            viewport_expansion: Viewport expansion for visibility checks.
            debug_mode: Whether to enable debug mode for metrics.
        Returns:
            dict: The result from the JS evaluation (DOM tree/hash map).
        """
        if not self.page:
            raise RuntimeError("Page not initialized. Call open_page first.")

        # Load JS code from buildDomTree.js
        js_path = os.path.join(os.path.dirname(__file__), "buildDomTree.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js_code = f.read()

        # Prepare the args for the JS function
        args = {
            "doHighlightElements": do_highlight_elements,
            "focusHighlightIndex": focus_highlight_index,
            "viewportExpansion": viewport_expansion,
            "debugMode": debug_mode,
        }

        # Evaluate the JS code in the browser context
        try:
            result = await self.page.evaluate(js_code, args)
        except Exception as e:
            raise RuntimeError(f"Error evaluating DOM tree JS: {e}")
        return result

    DEFAULT_WAIT_TIME = 5  # Default extra wait time (seconds) after navigation
    DEFAULT_AUTO_SCROLL_TIMEOUT = 30  # Default timeout for auto_scroll (seconds)

    def __init__(
        self,
        browser_type: str = "chromium",
        user_data_dir: Optional[str] = None,
        headless: bool = True,
        channel: Optional[str] = None,
    ):
        """
        Args:
            browser_type: Browser type string (e.g., 'chromium', 'firefox', 'webkit').
                For Chrome, use 'chrome' and for Edge, use 'edge'.
            user_data_dir: Optional path for persistent context.
            headless: Whether to run browser in headless mode (default: False).
            channel: Optional browser channel (e.g., 'chrome', 'msedge').
        """
        # Map browser_type to the actual Playwright engine
        if browser_type in ["chrome", "edge"]:
            self.browser_type = "chromium"  # Both Chrome and Edge use Chromium engine
        else:
            self.browser_type = browser_type

        # Map browser_type to channel for Chrome and Edge
        if browser_type == "chrome":
            self.channel = "chrome"
        elif browser_type == "edge":
            self.channel = "msedge"
        else:
            self.channel = channel

        self.user_data_dir = user_data_dir
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.pages: list = []  # Track all open pages

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        browser_launcher = getattr(self.playwright, self.browser_type)

        # Prepare launch options
        launch_options = {"headless": self.headless}
        if self.channel:
            launch_options["channel"] = self.channel

        if self.user_data_dir:
            # For persistent context with user data directory
            self.browser = await browser_launcher.launch_persistent_context(
                user_data_dir=self.user_data_dir, **launch_options
            )
            self.context = self.browser
        else:
            # For regular browser launch
            self.browser = await browser_launcher.launch(**launch_options)
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
        self.pages.append(self.page)
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

    async def click_element(self, selector: str, index: int = 0):
        """
        Click the element matching the given selector (default: first match).
        Works for links, buttons, and any clickable element.

        Args:
            selector: Selector string to match elements. Can be either:
                - A CSS selector (e.g., 'button.submit')
                - An XPath selector by prefixing with 'xpath=' (e.g., 'xpath=//button[@id="submit"]')
                See Playwright docs for supported selector engines.
            index: Which matched element to click (default: 0 = first).
        Raises:
            RuntimeError: If page not initialized or no element found.
            IndexError: If the index is out of range for the matched elements.
        """
        if not self.page:
            raise RuntimeError("Page not initialized. Call open_page first.")
        locator = self.page.locator(selector)
        count = await locator.count()
        if count == 0:
            raise RuntimeError(f"No element found for selector: {selector}")
        if index < 0 or index >= count:
            raise IndexError(
                f"Element index {index} out of range for selector: {selector}"
            )
        await locator.nth(index).click()

    async def input_text(self, selector: str, value: str, index: int = 0):
        """
        Fill the input or textarea matching the selector (default: first match) with the given value.
        Args:
            selector: Selector string (CSS or XPath, e.g., 'input#foo' or 'xpath=//input[@id="foo"]').
            value: Text to input.
            index: Which matched element to fill (default: 0 = first).
        Raises:
            RuntimeError: If page not initialized or no element found.
            IndexError: If the index is out of range for the matched elements.
        """
        if not self.page:
            raise RuntimeError("Page not initialized. Call open_page first.")
        locator = self.page.locator(selector)
        count = await locator.count()
        if count == 0:
            raise RuntimeError(f"No element found for selector: {selector}")
        if index < 0 or index >= count:
            raise IndexError(
                f"Element index {index} out of range for selector: {selector}"
            )
        await locator.nth(index).fill(value)

    async def extract_texts(self, selector: str):
        """
        Extract text content from all elements matching the given selector on the current page.
        Args:
            selector: CSS selector string to match elements.
        Returns:
            List of text content strings for each matched element.
        """
        if not self.page:
            raise RuntimeError("Page not initialized. Call open_page first.")
        elements = await self.page.locator(selector).all()
        texts = []
        for el in elements:
            try:
                text = await el.inner_text()
                texts.append(text)
            except Exception:
                texts.append("")
        return texts

    async def take_screenshot(self, output_path: str, full_page: bool = True):
        if not self.page:
            raise RuntimeError("Page not initialized. Call open_page first.")
        await self.page.screenshot(path=output_path, full_page=full_page)

    async def take_element_screenshot(self, element, output_path: str):
        """
        Take a screenshot of a specific element handle.
        Args:
            element: Playwright element handle (e.g., from locate_elements).
            output_path: Path to save the screenshot.
        """
        if not self.page:
            raise RuntimeError("Page not initialized. Call open_page first.")
        if element is None:
            raise ValueError("Element handle is None.")
        await element.screenshot(path=output_path)

    async def get_page_html(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        wait_time: int = 30,
        extra_http_headers: dict = None,
        goto_timeout: int = 30,
    ) -> str:
        """
        Open a page and return its HTML content.
        Args:
            url: URL to open.
            wait_until: When to consider navigation succeeded (default: 'domcontentloaded').
            wait_time: Extra time (seconds) to wait after navigation.
            extra_http_headers: Optional headers to set.
            goto_timeout: Max seconds to wait for navigation.
        Returns:
            The HTML content of the page as a string.
        """
        await self.open_page(
            url,
            wait_until=wait_until,
            wait_time=wait_time,
            extra_http_headers=extra_http_headers,
            goto_timeout=goto_timeout,
        )
        return await self.page.content()

    async def get_current_content(self) -> str:
        """
        Return the HTML content of the currently loaded page.
        Raises:
            RuntimeError: If no page is initialized/open.
        Returns:
            The HTML content of the current page as a string.
        """
        if not self.page:
            raise RuntimeError("Page not initialized. Call open_page first.")
        return await self.page.content()

    async def get_cookies(self) -> list:
        """Return cookies for the current browser context.

        Raises:
            RuntimeError: If no browser context is initialized.

        Returns:
            List of cookie dictionaries as returned by Playwright.
        """
        if not self.context:
            raise RuntimeError(
                "Context not initialized. Use 'async with PlaywrightWrapper()' block."
            )
        return await self.context.cookies()

    async def close(self):
        # Close all pages
        for p in getattr(self, "pages", []):
            try:
                await p.close()
            except Exception:
                pass
        self.pages = []
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

    async def list_tabs(self):
        """Return a list of (index, url, title, is_active) for all open tabs."""
        results = []
        if not self.context:
            return results
        for idx, p in enumerate(self.pages):
            try:
                url = p.url if hasattr(p, "url") else None
                title = await p.title() if hasattr(p, "title") else None
            except Exception:
                url = None
                title = None
            is_active = p == self.page
            results.append((idx, url, title, is_active))
        return results

    async def switch_tab(self, index: int):
        """Switch the active page/tab by index."""
        if not self.pages or index < 0 or index >= len(self.pages):
            raise IndexError(f"Tab index {index} out of range.")
        self.page = self.pages[index]

    async def close_tab(self, index: int):
        """Close the tab at the given index and remove it from the list. Adjust active page if needed."""
        if not self.pages or index < 0 or index >= len(self.pages):
            raise IndexError(f"Tab index {index} out of range.")
        page_to_close = self.pages[index]
        await page_to_close.close()
        del self.pages[index]
        # If the closed tab was the active one, switch to another tab if available
        if self.page == page_to_close:
            if self.pages:
                self.page = self.pages[min(index, len(self.pages) - 1)]
            else:
                self.page = None
