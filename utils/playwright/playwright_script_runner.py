from typing import List, Optional
import asyncio
from utils.playwright.playwright_wrapper import PlaywrightWrapper
from mcp_tools import time_util
import click
import shlex
import json
import tempfile
import os


# Decorator for command descriptions
def description(text):
    def decorator(func):
        func._description = text
        return func

    return decorator


class PlaywrightScriptRunner:
    """
    Runs a simple script of browser actions using PlaywrightWrapper.

    Notes:
      - Commands marked as 'Mutates page' will cause the browser/page to change state.
      - 'Read-only' commands only observe or capture information, not affecting the page.
      - 'No effect' means the command is for control flow or timing only.
    """

    def __init__(
        self,
        wrapper: Optional[PlaywrightWrapper] = None,
        headless: bool = True,
        browser_type: str = "chromium",
        user_data_dir: str = None,
    ):
        self.wrapper = wrapper or PlaywrightWrapper(
            headless=headless, browser_type=browser_type, user_data_dir=user_data_dir
        )
        self.last_located = None
        # List of (aliases, handler) pairs as a class member
        self.command_list = [
            (["open", "o"], self.cmd_open),
            (["wait", "w"], self.cmd_wait),
            (["locate_element", "locate", "l"], self.cmd_locate),
            (["eval_dom_tree", "eval", "e"], self.cmd_eval_dom_tree),
            (["viewport", "v"], self.cmd_viewport),
            (["auto_scroll", "scroll", "s"], self.cmd_scroll),
            (["screenshot", "shot", "ss"], self.cmd_shot),
            (["extract_texts", "extract", "x"], self.cmd_extract_texts),
            (["click", "g"], self.cmd_click),
            (["input", "i"], self.cmd_input),
            (["list_tabs", "tabs", "t"], self.cmd_list_tabs),
            (["switch_tab", "switch", "s"], self.cmd_switch_tab),
            (["close_tab", "close", "c"], self.cmd_close_tab),
            (["help", "h"], self.cmd_help),
            (["exit", "quit", "q"], self.cmd_exit),
        ]

    async def __aenter__(self):
        await self.wrapper.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.wrapper.__aexit__(exc_type, exc_val, exc_tb)

    async def run_script_line(self, line: str):
        """
        Execute a single script line using the given PlaywrightWrapper instance.
        Uses a command registry for dispatch and supports aliases.
        """
        import functools
        import inspect

        # Use the class member command_list
        command_map = {}
        for aliases, handler in self.command_list:
            for alias in aliases:
                command_map[alias] = handler

        # Parse command and args
        try:
            tokens = shlex.split(line)
        except Exception as e:
            raise ValueError(f"Failed to parse command line: {e}")
        if not tokens:
            return
        cmd = tokens[0].lower()
        args = tokens[1:]

        handler = command_map.get(cmd)
        if not handler:
            raise ValueError(f"Unknown script command: {cmd}")
        # Call handler with args
        if inspect.iscoroutinefunction(handler):
            await handler(*args)
        else:
            handler(*args)

    # --- Command Handlers ---
    @description(
        """input <selector> <value> [index]
        - Inputs text into the field matching the selector (default: first match). Optionally specify index for multiple matches. (Mutates page)
        - Selector can be CSS or XPath (prefix with 'xpath=')."""
    )
    async def cmd_input(self, selector, value, index=None):
        idx = int(index) if index is not None else 0
        await self.wrapper.input_text(selector, value, idx)
        print(f"[OK] Input '{value}' into {selector} (index {idx})")

    @description(
        """click <selector> [index]
        - Clicks the element matching the selector (default: first match). Optionally specify index for multiple matches. (Mutates page)
        - Selector can be CSS or XPath (prefix with 'xpath=')."""
    )
    async def cmd_click(self, selector, index=None):
        idx = int(index) if index is not None else 0
        await self.wrapper.click_element(selector, idx)
        print(f"[OK] Clicked element {selector} (index {idx})")

    @description(
        """open <url>
        - Navigates the browser to the specified URL. (Mutates page)"""
    )
    async def cmd_open(self, url):
        await self.wrapper.open_page(url, wait_time=0)
        print("[OK]")

    @description(
        """eval_dom_tree [highlight] [focus] [viewport_expansion] [debug] [--dump-json]
    - Evaluates the DOM tree and returns a JSON representation. (Read-only)
    - [highlight] can be 'true' or 'false' (default: true)
    - [focus] can be an integer index or -1 (default: -1)
    - [viewport_expansion] can be an integer (default: 0)
    - [debug] can be 'true' or 'false' (default: false)
    - [--dump-json] can be 'true' or 'false' (default: false)"""
    )
    async def cmd_eval_dom_tree(self, *args):
        # Parse options from args (reuse click for consistency)
        @click.command()
        @click.option(
            "--highlight/--no-highlight", default=True, help="Highlight elements"
        )
        @click.option("--focus", default=-1, type=int, help="Focus highlight index")
        @click.option(
            "--viewport-expansion", default=0, type=int, help="Viewport expansion"
        )
        @click.option("--debug", is_flag=True, default=False, help="Enable debug mode")
        @click.option(
            "--dump-json",
            is_flag=True,
            default=False,
            help="Dump result JSON to a temp file",
        )
        def eval_cmd(highlight, focus, viewport_expansion, debug, dump_json):
            return highlight, focus, viewport_expansion, debug, dump_json

        params = eval_cmd.make_context("eval_dom_tree", list(args)).params
        result = await self.wrapper.evaluate_dom_tree(
            do_highlight_elements=params["highlight"],
            focus_highlight_index=params["focus"],
            viewport_expansion=params["viewport_expansion"],
            debug_mode=params["debug"],
        )
        if params["dump_json"]:
            fd, path = tempfile.mkstemp(suffix=".json", prefix="eval_dom_tree_")
            os.close(fd)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"[eval_dom_tree] JSON dumped to: {path}")
        else:
            print(json.dumps(result, indent=2))

    @description(
        """wait <seconds>s
    - Waits for the specified duration. Does not interact with the page. (No effect)"""
    )
    async def cmd_wait(self, duration):
        if not duration.endswith("s"):
            raise ValueError("wait duration must end with 's'")
        try:
            seconds = float(duration[:-1])
        except Exception as e:
            raise ValueError(f"Invalid wait duration: {e}")
        await asyncio.sleep(seconds)
        print(f"[wait] Slept for {seconds} seconds.")

    @description(
        """locate_element <selector>
    - Finds elements matching the CSS selector and stores them for later use. (Read-only)"""
    )
    async def cmd_locate(self, selector):
        self.last_located = await self.wrapper.locate_elements(selector)
        print(f"Located {len(self.last_located)} elements.")

    @description(
        """viewport <width>x<height>
    - Sets the viewport size to the specified width and height. (Mutates page)"""
    )
    async def cmd_viewport(self, size):
        if "x" not in size:
            raise ValueError("Viewport size must be in <width>x<height> format.")
        width, height = size.split("x")
        await self.wrapper.set_viewport_size(int(width), int(height))
        print(f"Viewport set to {width}x{height}.")

    @description(
        """auto_scroll [timeout] [scroll_step] [scroll_delay]
    - Scrolls the page to the bottom, simulating user scrolling. (Mutates page)"""
    )
    async def cmd_scroll(self, timeout=None, scroll_step=None, scroll_delay=None):
        timeout = int(timeout) if timeout else self.wrapper.DEFAULT_AUTO_SCROLL_TIMEOUT
        scroll_step = int(scroll_step) if scroll_step else 80
        scroll_delay = float(scroll_delay) if scroll_delay else 0.5
        await self.wrapper.auto_scroll(timeout, scroll_step, scroll_delay)
        print(
            f"Auto-scrolled for {timeout}s, step {scroll_step}, delay {scroll_delay}."
        )

    @description(
        """screenshot <output_path> [full_page]
    - Takes a screenshot of the current page. (Read-only, but captures visual state)"""
    )
    async def cmd_shot(self, output_path, full_page=None):
        full_page = full_page.lower() == "true" if full_page is not None else True
        await self.wrapper.take_screenshot(output_path, full_page=full_page)
        print(f"Screenshot saved to {output_path} (full_page={full_page}).")

    @description(
        """extract_texts <selector> [output_format]
    - Extracts text content from all elements matching the selector and prints as JSON or markdown. (Read-only, only if supported by wrapper)
    - [output_format] can be 'json' (default) or 'markdown'.
    """
    )
    async def cmd_extract_texts(self, selector, output_format=None):
        """
        Extract text content from elements matching the selector.
        Optionally output as markdown if output_format == 'markdown'.
        """
        if not hasattr(self.wrapper, "extract_texts"):
            raise RuntimeError(
                "extract_texts is not supported by the current PlaywrightWrapper."
            )
        texts = await self.wrapper.extract_texts(selector)
        if output_format and output_format.lower() == "markdown":
            # Lazy import to avoid unnecessary dependency if not used
            from utils.html_to_markdown.converter import html_to_markdown

            # If texts is a list of HTML strings, convert each to markdown
            if isinstance(texts, list):
                markdowns = [html_to_markdown(t) for t in texts]
                print("\n\n---\n\n".join(markdowns))
            elif isinstance(texts, dict):
                # If dict, convert each value
                markdowns = {k: html_to_markdown(v) for k, v in texts.items()}
                for k, md in markdowns.items():
                    print(f"## {k}\n\n{md}\n")
            else:
                print(html_to_markdown(str(texts)))
        else:
            print(json.dumps(texts, ensure_ascii=False, indent=2))

    @description(
        """list_tabs
    - Lists all open tabs with index, URL, and title. (Read-only)"""
    )
    async def cmd_list_tabs(self):
        tabs = await self.wrapper.list_tabs()
        if not tabs:
            print("No open tabs.")
        else:
            print("Open tabs:")
            for idx, url, title, is_active in tabs:
                active_marker = " *" if is_active else ""
                print(
                    f"  [{idx}]{active_marker} {url or '<no url>'} | {title or '<no title>'}"
                )

    @description(
        """switch_tab <index>
    - Sets the active tab. (Mutates page)"""
    )
    async def cmd_switch_tab(self, idx):
        idx = int(idx)
        await self.wrapper.switch_tab(idx)
        print(f"Switched to tab {idx}.")

    @description(
        """close_tab <index>
    - Closes the tab at the specified index. (Mutates page)"""
    )
    async def cmd_close_tab(self, idx):
        idx = int(idx)
        await self.wrapper.close_tab(idx)
        print(f"Closed tab {idx}.")

    @description(
        """help
    - Shows this help message."""
    )
    def cmd_help(self):
        print(self.help())

    @description(
        """exit/quit
    - Exits the interactive session."""
    )
    def cmd_exit(self):
        print("Exiting Playwright CLI.")
        raise SystemExit(0)

    async def run_script(self, script: str):
        lines = [line.strip() for line in script.strip().splitlines() if line.strip()]
        for line in lines:
            await self.run_script_line(line)

    def get_last_located(self):
        """Return the element handles from the last locate_element command."""
        return self.last_located

    @classmethod
    def help(cls):
        # Collect all methods with a _description attribute
        import inspect

        lines = ["Supported commands:"]
        for name, member in inspect.getmembers(cls):
            if callable(member) and hasattr(member, "_description"):
                desc = member._description
                # Only show the first alias for the command
                lines.append(f"  {desc}")
        lines.append("\nNotes:")
        lines.append(
            "  - Commands marked as 'Mutates page' will cause the browser/page to change state."
        )
        lines.append(
            "  - 'Read-only' commands only observe or capture information, not affecting the page."
        )
        lines.append(
            "  - 'No effect' means the command is for control flow or timing only."
        )
        return "\n".join(lines)
