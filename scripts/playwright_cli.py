import asyncio
from utils.playwright.playwright_script_runner import PlaywrightScriptRunner
import argparse

async def main():
    parser = argparse.ArgumentParser(description="Playwright Interactive CLI")
    parser.add_argument('--browser-type', type=str, default='chromium', help="Browser type: chromium, firefox, webkit, chrome, edge")
    args, unknown = parser.parse_known_args()
    print(
        "Playwright Interactive CLI. Type 'help' for commands. Type 'exit' or 'quit' to leave."
    )
    runner = PlaywrightScriptRunner(headless=False, browser_type=args.browser_type)
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