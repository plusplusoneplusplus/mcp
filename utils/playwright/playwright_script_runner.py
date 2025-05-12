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
        else:
            raise ValueError(f"Unknown script command: {line}")

    async def run_script(self, script: str):
        lines = [line.strip() for line in script.strip().splitlines() if line.strip()]
        for line in lines:
            await self.run_script_line(line)

    def get_last_located(self):
        """Return the element handles from the last locate_element command."""
        return self.last_located
