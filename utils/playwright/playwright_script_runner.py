from typing import List, Optional
import asyncio
from utils.playwright.playwright_wrapper import PlaywrightWrapper
from mcp_tools import time_util
import click
import shlex


class PlaywrightScriptRunner:
    """
    Runs a simple script of browser actions using PlaywrightWrapper.

    Supported commands (one per line):

      open <url> [--headless|-H]
        - Navigates the browser to the specified URL. Optionally force headless mode. (Mutates page)
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

    def __init__(self, wrapper: Optional[PlaywrightWrapper] = None, headless: bool = True):
        self.wrapper = wrapper or PlaywrightWrapper(headless=headless)
        self.last_located = None

    async def __aenter__(self):
        await self.wrapper.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.wrapper.__aexit__(exc_type, exc_val, exc_tb)

    async def run_script_line(self, line: str):
        """
        Execute a single script line using the given PlaywrightWrapper instance.
        Uses click for argument parsing for supported commands.
        """
        if line.startswith("open "):

            @click.command()
            @click.argument("url")
            def open_cmd(url):
                return url

            try:
                args = shlex.split(line[len("open ") :])
                ctx = click.Context(open_cmd)
                url = open_cmd.make_context(
                    "open", args, parent=ctx
                ).params.values()
            except Exception as e:
                raise ValueError(f"Failed to parse open command: {e}")
            if url is None:
                raise ValueError("open command requires a URL")
            await self.wrapper.open_page(url, wait_time=0)

        elif line.startswith("wait "):

            @click.command()
            @click.argument("duration")
            def wait_cmd(duration):
                return duration

            try:
                args = shlex.split(line[len("wait ") :])
                ctx = click.Context(wait_cmd)
                duration_str = wait_cmd.make_context("wait", args, parent=ctx).params[
                    "duration"
                ]
                delta = time_util.parse_delta_string(duration_str)
                await asyncio.sleep(delta.total_seconds())
            except Exception as e:
                raise ValueError(f"Invalid wait argument: {e}")

        elif line.startswith("locate_element "):

            @click.command()
            @click.argument("selector")
            def locate_cmd(selector):
                return selector

            try:
                args = shlex.split(line[len("locate_element ") :])
                ctx = click.Context(locate_cmd)
                selector = locate_cmd.make_context(
                    "locate_element", args, parent=ctx
                ).params["selector"]
                self.last_located = await self.wrapper.locate_elements(selector)
            except Exception as e:
                raise ValueError(f"Invalid locate_element argument: {e}")

        elif line.startswith("viewport "):

            @click.command()
            @click.argument("size")
            def viewport_cmd(size):
                return size

            try:
                args = shlex.split(line[len("viewport ") :])
                ctx = click.Context(viewport_cmd)
                size = viewport_cmd.make_context("viewport", args, parent=ctx).params[
                    "size"
                ]
                if "x" not in size:
                    raise ValueError(f"Invalid viewport argument: {size}")
                width, height = size.split("x")
                await self.wrapper.set_viewport_size(int(width), int(height))
            except Exception as e:
                raise ValueError(f"Invalid viewport argument: {e}")

        elif line.startswith("auto_scroll"):

            @click.command()
            @click.option(
                "--timeout",
                default=self.wrapper.DEFAULT_AUTO_SCROLL_TIMEOUT,
                type=float,
            )
            @click.option("--scroll-step", default=80, type=int)
            @click.option("--scroll-delay", default=0.5, type=float)
            def scroll_cmd(timeout, scroll_step, scroll_delay):
                return timeout, scroll_step, scroll_delay

            try:
                # Support both positional and option args
                args = shlex.split(line[len("auto_scroll") :])
                # If positional, fill in as timeout, scroll_step, scroll_delay
                if args and not any(a.startswith("--") for a in args):
                    # Pad missing args
                    while len(args) < 3:
                        if len(args) == 0:
                            args.append(str(self.wrapper.DEFAULT_AUTO_SCROLL_TIMEOUT))
                        elif len(args) == 1:
                            args.append("80")
                        elif len(args) == 2:
                            args.append("0.5")
                    args = [
                        f"--timeout={args[0]}",
                        f"--scroll-step={args[1]}",
                        f"--scroll-delay={args[2]}",
                    ]
                ctx = click.Context(scroll_cmd)
                timeout, scroll_step, scroll_delay = scroll_cmd.make_context(
                    "auto_scroll", args, parent=ctx
                ).params.values()
                await self.wrapper.auto_scroll(
                    timeout=timeout, scroll_step=scroll_step, scroll_delay=scroll_delay
                )
            except Exception as e:
                raise ValueError(f"Invalid auto_scroll argument: {e}")

        elif line.startswith("screenshot "):

            @click.command()
            @click.argument("output_path")
            @click.option("--full-page", is_flag=True, default=True)
            def shot_cmd(output_path, full_page):
                return output_path, full_page

            try:
                args = shlex.split(line[len("screenshot ") :])
                ctx = click.Context(shot_cmd)
                output_path, full_page = shot_cmd.make_context(
                    "screenshot", args, parent=ctx
                ).params.values()
                await self.wrapper.take_screenshot(output_path, full_page=full_page)
            except Exception as e:
                raise ValueError(f"Invalid screenshot argument: {e}")

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
