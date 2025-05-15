import asyncio
from utils.playwright.playwright_script_runner import PlaywrightScriptRunner


import click

@click.command()
@click.option('--headless', '-H', is_flag=True, default=False, help='Run browser in headless mode (default: False)')
async def main(headless):
    print(
        "Playwright Interactive CLI. Type 'help' for commands. Type 'exit' or 'quit' to leave."
    )
    runner = PlaywrightScriptRunner(headless=headless)
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
    import sys
    import asyncio
    # Use click's main entrypoint for CLI parsing
    if sys.version_info >= (3, 7):
        asyncio.run(main())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
