from typing import List, Optional
import asyncio
from utils.playwright.playwright_wrapper import PlaywrightWrapper
from mcp_tools import time_util

class PlaywrightScriptRunner:
    """
    Runs a simple script of browser actions using PlaywrightWrapper.
    Supported commands (one per line):
        open <url>
        wait <seconds>s
        locate_element <selector>
        viewport <width>x<height>
        auto_scroll [timeout] [scroll_step] [scroll_delay]
        screenshot <output_path> [full_page]
    """
    def __init__(self, wrapper: Optional[PlaywrightWrapper] = None):
        self.wrapper = wrapper or PlaywrightWrapper()
        self.last_located = None

    async def __aenter__(self):
        await self.wrapper.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.wrapper.__aexit__(exc_type, exc_val, exc_tb)

    async def run_script_line(self, line: str):
        """
        Execute a single script line using the given PlaywrightWrapper instance.
        """
        if line.startswith("open "):
            url = line[len("open "):].strip()
            await self.wrapper.open_page(url, wait_time = 0)
        elif line.startswith("wait "):
            arg = line[len("wait "):].strip()
            try:
                delta = time_util.parse_delta_string(arg)
                await asyncio.sleep(delta.total_seconds())
            except Exception as e:
                raise ValueError(f"Invalid wait argument: {arg} ({e})")
        elif line.startswith("locate_element "):
            selector = line[len("locate_element "):].strip()
            self.last_located = await self.wrapper.locate_elements(selector)
        elif line.startswith("viewport "):
            dims = line[len("viewport "):].strip()
            if 'x' not in dims:
                raise ValueError(f"Invalid viewport argument: {dims}")
            width, height = dims.split('x')
            await self.wrapper.set_viewport_size(int(width), int(height))
        elif line.startswith("auto_scroll"):
            parts = line[len("auto_scroll"):].strip().split()
            timeout = float(parts[0]) if len(parts) > 0 else self.wrapper.DEFAULT_AUTO_SCROLL_TIMEOUT
            scroll_step = int(parts[1]) if len(parts) > 1 else 80
            scroll_delay = float(parts[2]) if len(parts) > 2 else 0.5
            await self.wrapper.auto_scroll(timeout=timeout, scroll_step=scroll_step, scroll_delay=scroll_delay)
        elif line.startswith("screenshot "):
            args = line[len("screenshot "):].strip().split()
            if not args:
                raise ValueError("screenshot requires an output path")
            output_path = args[0]
            full_page = args[1].lower() == 'true' if len(args) > 1 else True
            await self.wrapper.take_screenshot(output_path, full_page=full_page)
        else:
            raise ValueError(f"Unknown script command: {line}")

    async def run_script(self, script: str):
        lines = [line.strip() for line in script.strip().splitlines() if line.strip()]
        for line in lines:
            await self.run_script_line(line)

    def get_last_located(self):
        """Return the element handles from the last locate_element command."""
        return self.last_located

    @classmethod
    def help(cls):
        return (
            "Supported commands:\n"
            "  open <url>\n"
            "  wait <seconds>s\n"
            "  locate_element <selector>\n"
            "  viewport <width>x<height>\n"
            "  auto_scroll [timeout] [scroll_step] [scroll_delay]\n"
            "  screenshot <output_path> [full_page]\n"
            "  help\n"
            "  exit/quit\n"
        )