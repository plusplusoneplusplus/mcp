from typing import List, Optional
import asyncio
from utils.playwright.playwright_wrapper import PlaywrightWrapper
from mcp_tools import time_util

class PlaywrightScriptRunner:
    """
    Runs a simple script of browser actions using PlaywrightWrapper.
    
    Supported commands (one per line):

      open <url>
        - Navigates the browser to the specified URL. (Mutates page)
      wait <seconds>s
        - Waits for the specified duration. Does not interact with the page. (No effect)
      locate_element <selector>
        - Finds elements matching the CSS selector and stores them for later use. (Read-only)
      viewport <width>x<height>
        - Sets the viewport size to the specified width and height. (Mutates page)
      auto_scroll [timeout] [scroll_step] [scroll_delay]
        - Scrolls the page to the bottom, simulating user scrolling. (Mutates page)
      screenshot <output_path> [full_page]
        - Takes a screenshot of the current page. (Read-only, but captures visual state)
      help
        - Shows this help message.
      exit/quit
        - Exits the interactive session.
    
    Notes:
      - Commands marked as 'Mutates page' will cause the browser/page to change state.
      - 'Read-only' commands only observe or capture information, not affecting the page.
      - 'No effect' means the command is for control flow or timing only.
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
            "    - Navigates the browser to the specified URL. (Mutates page)\n"
            "  wait <seconds>s\n"
            "    - Waits for the specified duration. Does not interact with the page. (No effect)\n"
            "  locate_element <selector>\n"
            "    - Finds elements matching the CSS selector and stores them for later use. (Read-only)\n"
            "  viewport <width>x<height>\n"
            "    - Sets the viewport size to the specified width and height. (Mutates page)\n"
            "  auto_scroll [timeout] [scroll_step] [scroll_delay]\n"
            "    - Scrolls the page to the bottom, simulating user scrolling. (Mutates page)\n"
            "  screenshot <output_path> [full_page]\n"
            "    - Takes a screenshot of the current page. (Read-only, but captures visual state)\n"
            "  help\n"
            "    - Shows this help message.\n"
            "  exit/quit\n"
            "    - Exits the interactive session.\n"
            "\nNotes:\n"
            "  - Commands marked as 'Mutates page' will cause the browser/page to change state.\n"
            "  - 'Read-only' commands only observe or capture information, not affecting the page.\n"
            "  - 'No effect' means the command is for control flow or timing only.\n"
        )