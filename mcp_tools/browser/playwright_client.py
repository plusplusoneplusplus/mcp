"""Playwright-based browser client implementation.

This module provides a browser client implementation using Playwright.
"""

import asyncio
from typing import Optional, Any, Literal, List, Dict
import re

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
        self.retry_capture_panels_keywords = ["LOADING"]
        self.max_retry_capture_panels = 3

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
        max_parallelism: int = 4,
    ) -> dict:
        """
        Capture each matching element as an image, extract OCR content, and return results.
        Supports parallelism: up to max_parallelism panel captures (including retry) run concurrently.
        Args:
            url: The dashboard URL to visit
            selector: CSS selector for chart/panel containers
            width: Browser viewport width
            height: Browser viewport height
            token: Bearer token for Authorization header (optional)
            wait_time: Time to wait for page load in seconds
            headless: Whether to run browser in headless mode
            autoscroll: If true, autoscroll each panel into view and scroll its contents before capturing.
            max_parallelism: Maximum number of panels to capture in parallel (default 4)
        Returns:
            Dict[str, Any]:
                - Success: Whether the operation was successful
                - SessionId: Session ID
                - Count: Number of panels captured
                - Panels: List of dicts with PanelID, Path, Content
                - URL: Dashboard URL visited
        """
        import pathlib
        import re
        import datetime

        out_dir = env.get_setting("image_dir", ".images")
        # Generate session ID as timestamp to second (e.g., 20250513_094112)
        session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = pathlib.Path(out_dir) / session_id
        session_dir.mkdir(exist_ok=True, parents=True)
        panels_info = []
        try:
            extra_headers = {"Authorization": f"Bearer {token}"} if token else None
            async with PlaywrightWrapper(
                browser_type=self.browser,
                user_data_dir=self.user_data_dir,
                headless=headless,
            ) as wrapper:
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
                    return {
                        "Count": 0,
                        "Panels": [],
                        "URL": url,
                        "SessionId": session_id,
                    }

                semaphore = asyncio.Semaphore(max_parallelism)
                panel_results: List[Optional[Dict[str, Any]]] = [None for _ in range(len(panels))]

                async def capture_panel(idx, el):
                    pid = None
                    for attr in [
                        "data-panelid",
                        "data-griditem-key",
                        "data-viz-panel-key",
                    ]:
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
                        pid = f"{idx+1:02d}"

                    # Check if element handle is valid and attached
                    if not el or (hasattr(el, "is_detached") and el.is_detached()):
                        print(
                            f"Warning: Element for panel {pid} is not attached or not found. Skipping."
                        )
                        return None

                    image_path = session_dir / f"panel_{pid}.png"
                    delay = 1
                    ocr_content = []
                    for attempt in range(self.max_retry_capture_panels):
                        await wrapper.take_element_screenshot(el, str(image_path))
                        print(f"Saved panel_{pid}.png (attempt {attempt+1})")
                        try:
                            from utils.ocr_extractor import extract_text_from_image

                            ocr_content = extract_text_from_image(image_path)
                        except Exception as ocr_e:
                            print(f"OCR extraction failed for {image_path}: {ocr_e}")
                            ocr_content = []
                        # Check if any retry keyword is present in any extracted text
                        found_keyword = False
                        for text in ocr_content:
                            for kw in self.retry_capture_panels_keywords:
                                if kw in text:
                                    found_keyword = True
                                    break
                            if found_keyword:
                                break
                        if (
                            not found_keyword
                            or attempt == self.max_retry_capture_panels - 1
                        ):
                            break
                        print(
                            f"Retrying screenshot/OCR for panel {pid} in {delay} seconds due to keyword match..."
                        )
                        await asyncio.sleep(delay)
                        delay *= 2
                    return {
                        "PanelID": pid,
                        "Path": str(image_path),
                        "Content": ocr_content,
                    }

                async def sem_task(idx, el):
                    async with semaphore:
                        result = await capture_panel(idx, el)
                        if result is not None:
                            panel_results[idx] = result

                tasks = [
                    asyncio.create_task(sem_task(idx, el))
                    for idx, el in enumerate(panels)
                ]
                await asyncio.gather(*tasks)

                panels_info = [r for r in panel_results if r is not None]
                return {
                    "Count": len(panels_info),
                    "Panels": panels_info,
                    "URL": url,
                    "SessionId": session_id,
                }
        except Exception as e:
            print(f"Error in capture_panels: {e}")
            return {"Count": len(panels_info), "Panels": panels_info, "URL": url}

    async def __aenter__(self):
        """Support for async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensure resources are cleaned up when exiting context."""
        await self.close()

    async def get_page_html(
        self, url: str, wait_time: int = 30, headless: bool = True, options: Any = None
    ) -> Optional[str]:
        try:
            # Create a new wrapper instance with the specified headless mode
            async with PlaywrightWrapper(
                browser_type=self.browser,
                user_data_dir=self.user_data_dir,
                headless=headless,
            ) as temp_wrapper:
                html = await temp_wrapper.get_page_html(
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
            async with PlaywrightWrapper(
                browser_type=self.browser,
                user_data_dir=self.user_data_dir,
                headless=headless,
            ) as wrapper:
                await wrapper.open_page(url, wait_time=wait_time)
                if auto_scroll:
                    print("Auto-scrolling page to load all content...")
                    await wrapper.auto_scroll(
                        timeout=scroll_timeout,
                        scroll_step=scroll_step,
                        scroll_delay=scroll_delay,
                    )
                await wrapper.take_screenshot(output_path, full_page=True)
                return True
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return False

    async def close(self):
        """Close the browser and clean up resources."""
        pass

    async def get_cookies_after_login(
        self,
        url: str,
        wait_url: str,
        headless: bool = False,
        timeout: int = 60,
    ) -> List[Dict[str, Any]]:
        """Open a page for manual login and return cookies after URL match."""
        async with PlaywrightWrapper(
            browser_type=self.browser,
            user_data_dir=self.user_data_dir,
            headless=headless,
        ) as wrapper:
            page = await wrapper.open_page(
                url, wait_until="domcontentloaded", wait_time=0
            )
            if wait_url:
                try:
                    await page.wait_for_url(
                        re.compile(wait_url), timeout=timeout * 1000
                    )
                except Exception:
                    pass
            else:
                await page.wait_for_timeout(timeout * 1000)
            return await wrapper.get_cookies()
