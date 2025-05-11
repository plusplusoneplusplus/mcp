from typing import List, Optional
import asyncio
from mcp_tools.browser.playwright_wrapper import PlaywrightWrapper

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

    async def run_script_line(self, line: str, pw: PlaywrightWrapper):
        """
        Execute a single script line using the given PlaywrightWrapper instance.
        """
        if line.startswith("open "):
            url = line[len("open "):].strip()
            await pw.open_page(url)
        elif line.startswith("wait "):
            arg = line[len("wait "):].strip()
            if arg.endswith("s"):
                seconds = float(arg[:-1])
                await asyncio.sleep(seconds)
            else:
                raise ValueError(f"Invalid wait argument: {arg}")
        elif line.startswith("locate_element "):
            selector = line[len("locate_element "):].strip()
            self.last_located = await pw.locate_elements(selector)
        else:
            raise ValueError(f"Unknown script command: {line}")

    async def run_script(self, script: str):
        lines = [line.strip() for line in script.strip().splitlines() if line.strip()]
        async with self.wrapper as pw:
            for line in lines:
                await self.run_script_line(line, pw)

    def get_last_located(self):
        """Return the element handles from the last locate_element command."""
        return self.last_located
