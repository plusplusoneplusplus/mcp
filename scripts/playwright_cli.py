import asyncio
from utils.playwright.playwright_script_runner import PlaywrightScriptRunner
import argparse

import os

async def main():
    parser = argparse.ArgumentParser(description="Playwright Interactive CLI")
    parser.add_argument('--browser-type', type=str, default='chromium', help="Browser type: chromium, firefox, webkit, chrome, edge")
    parser.add_argument('--user-data-dir', type=str, default=None, help="Path to persistent browser profile directory (default: .profile in script dir)")
    args, unknown = parser.parse_known_args()

    # Determine user data dir
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = args.user_data_dir or os.path.join(script_dir, '.profile')
    os.makedirs(user_data_dir, exist_ok=True)

    print(
        "Playwright Interactive CLI. Type 'help' for commands. Type 'exit' or 'quit' to leave.\n"
        "For 'eval_dom_tree', you can use --dump-json to save the result as JSON in a temp file."
    )
    runner = PlaywrightScriptRunner(headless=False, browser_type=args.browser_type, user_data_dir=user_data_dir)
    async with runner:
        while True:
            try:
                line = input("pw> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting Playwright CLI.")
                break
            if not line:
                continue
            if line.lower() in ("exit", "quit"):
                print("Exiting Playwright CLI.")
                break
            if line.lower() == "help":
                print(PlaywrightScriptRunner.help())
                continue
            try:
                await runner.run_script_line(line)
                print("[OK]")
            except Exception as e:
                print(f"[ERROR] {e}")


if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())