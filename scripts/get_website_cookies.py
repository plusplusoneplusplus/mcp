#!/usr/bin/env python3
"""
Simple script to get cookies from a website using the PlaywrightWrapper utility.

Usage:
    python scripts/get_website_cookies.py <url> [options]

Examples:
    # Get cookies from a website (headless mode)
    python scripts/get_website_cookies.py https://example.com

    # Get cookies with browser visible
    python scripts/get_website_cookies.py https://example.com --no-headless

    # Get cookies using Chrome instead of default Chromium
    python scripts/get_website_cookies.py https://example.com --browser chrome

    # Get cookies with persistent user data directory for login sessions
    python scripts/get_website_cookies.py https://example.com --user-data-dir ./browser_profile
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.playwright.playwright_wrapper import PlaywrightWrapper


async def get_website_cookies(
    url: str,
    browser_type: str = "chromium",
    headless: bool = True,
    user_data_dir: str | None = None,
    wait_time: int = 5,
    output_format: str = "json",
) -> dict:
    """
    Get cookies from a website using PlaywrightWrapper.

    Args:
        url: The URL to visit and get cookies from
        browser_type: Browser type ('chromium', 'chrome', 'edge', 'firefox', 'webkit')
        headless: Whether to run browser in headless mode
        user_data_dir: Optional path for persistent browser profile
        wait_time: Time to wait after page load before getting cookies
        output_format: Output format ('json', 'table', 'simple')

    Returns:
        Dictionary containing cookies and metadata
    """
    result = {
        "url": url,
        "cookies": [],
        "cookie_count": 0,
        "success": False,
        "error": None,
    }

    try:
        async with PlaywrightWrapper(
            browser_type=browser_type, user_data_dir=user_data_dir, headless=headless
        ) as wrapper:
            # Navigate to the URL
            print(f"Navigating to: {url}")
            await wrapper.open_page(
                url=url, wait_until="networkidle", wait_time=wait_time
            )

            # Get cookies from the browser context
            if wrapper.context:
                cookies = await wrapper.context.cookies()
                result["cookies"] = [
                    {
                        "name": cookie["name"],
                        "value": cookie["value"],
                        "domain": cookie["domain"],
                        "path": cookie["path"],
                        "expires": cookie.get("expires", -1),
                        "httpOnly": cookie.get("httpOnly", False),
                        "secure": cookie.get("secure", False),
                        "sameSite": cookie.get("sameSite", "None"),
                    }
                    for cookie in cookies
                ]
                result["cookie_count"] = len(cookies)
                result["success"] = True

                print(f"Successfully retrieved {len(cookies)} cookies from {url}")
            else:
                result["error"] = "Browser context not available"

    except Exception as e:
        result["error"] = str(e)
        print(f"Error getting cookies: {e}")

    return result


def format_output(result: dict, output_format: str) -> str:
    """Format the cookie result for display."""
    if not result["success"]:
        return f"Error: {result['error']}"

    if output_format == "json":
        return json.dumps(result, indent=2)

    elif output_format == "table":
        output = []
        output.append(f"Cookies from {result['url']} ({result['cookie_count']} total)")
        output.append("=" * 80)
        output.append(
            f"{'Name':<20} {'Domain':<25} {'Path':<15} {'Secure':<8} {'HttpOnly'}"
        )
        output.append("-" * 80)

        for cookie in result["cookies"]:
            output.append(
                f"{cookie['name'][:19]:<20} "
                f"{cookie['domain'][:24]:<25} "
                f"{cookie['path'][:14]:<15} "
                f"{str(cookie['secure']):<8} "
                f"{cookie['httpOnly']}"
            )
        return "\n".join(output)

    elif output_format == "simple":
        output = []
        output.append(f"Found {result['cookie_count']} cookies from {result['url']}:")
        for cookie in result["cookies"]:
            output.append(
                f"  {cookie['name']} = {cookie['value'][:50]}{'...' if len(cookie['value']) > 50 else ''}"
            )
        return "\n".join(output)

    else:
        return "Invalid output format"


def main():
    """Main function to handle command line arguments and run the cookie extractor."""
    parser = argparse.ArgumentParser(
        description="Get cookies from a website using PlaywrightWrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com
  %(prog)s https://example.com --no-headless --browser chrome
  %(prog)s https://example.com --user-data-dir ./profile --output table
        """,
    )

    parser.add_argument("url", help="The URL to get cookies from")
    parser.add_argument(
        "--browser",
        choices=["chromium", "chrome", "edge", "firefox", "webkit"],
        default="chromium",
        help="Browser type to use (default: chromium)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in visible mode (default: headless)",
    )
    parser.add_argument(
        "--user-data-dir",
        help="Path to user data directory for persistent browser profile",
    )
    parser.add_argument(
        "--wait-time",
        type=int,
        default=5,
        help="Time to wait after page load before getting cookies (default: 5)",
    )
    parser.add_argument(
        "--output",
        choices=["json", "table", "simple"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument("--save-to-file", help="Save cookies to specified JSON file")

    args = parser.parse_args()

    # Validate URL
    if not (args.url.startswith("http://") or args.url.startswith("https://")):
        print("Error: URL must start with http:// or https://")
        sys.exit(1)

    # Run the cookie extraction
    result = asyncio.run(
        get_website_cookies(
            url=args.url,
            browser_type=args.browser,
            headless=not args.no_headless,
            user_data_dir=args.user_data_dir,
            wait_time=args.wait_time,
            output_format=args.output,
        )
    )

    # Display results
    output = format_output(result, args.output)
    print(output)

    # Save to file if requested
    if args.save_to_file and result["success"]:
        try:
            with open(args.save_to_file, "w") as f:
                json.dump(result, f, indent=2)
            print(f"\nCookies saved to: {args.save_to_file}")
        except Exception as e:
            print(f"Error saving to file: {e}")

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
