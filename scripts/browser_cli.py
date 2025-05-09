#!/usr/bin/env python3
"""
Standalone program for using IBrowserClient to test different web pages.
This program allows you to get HTML content or take screenshots of web pages.
"""

import os
import argparse
import time
import asyncio
from mcp_tools.browser.factory import BrowserClientFactory
from mcp_tools.browser.client import BrowserClient
from utils.html_to_markdown import extract_and_format_html
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

async def main():
    # Get the scripts directory path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(script_dir, 'browser_outputs')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create default profile directory if it doesn't exist
    default_profile_path = os.path.join(script_dir, '.profile')
    os.makedirs(default_profile_path, exist_ok=True)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test web pages using a browser client')
    parser.add_argument('url', help='URL to visit')
    parser.add_argument('--operation', '-o', choices=['html', 'screenshot', 'markdown'], default='html',
                        help='Operation to perform: get HTML, take screenshot, or get markdown (default: html)')
    parser.add_argument('--wait', '-w', type=int, default=5,
                        help='Time to wait for page load in seconds (default: 5)')
    parser.add_argument('--output', '-f',
                        help=f'Output file path for screenshot or HTML (default: auto-generated in {output_dir})')
    parser.add_argument('--browser', '-b', choices=['chrome', 'edge', 'chromium', 'firefox', 'webkit'], default='edge',
                        help='Browser to use (default: edge)')
    parser.add_argument('--headless', action='store_true', default=False,
                        help='Run browser in headless mode (default: False)')
    parser.add_argument('--profile-path', '-p', default=default_profile_path,
                        help=f'Path to browser profile directory (default: {default_profile_path})')
    parser.add_argument('--profile-dir', '-d', default='Default',
                        help='Profile directory name within the profile path (default: Default)')
    parser.add_argument('--no-profile', action='store_true', default=False,
                        help='Do not use a profile (ignore profile-path and profile-dir)')
    parser.add_argument('--client-type', choices=['selenium', 'playwright'], default='playwright',
                        help='Type of browser client to use (default: playwright)')
    parser.add_argument('--include-links', action='store_true', default=True,
                        help='Include links in the extracted markdown (default: True, for markdown operation)')
    parser.add_argument('--include-images', action='store_true', default=False,
                        help='Include image references in the extracted markdown (default: False, for markdown operation)')
    parser.add_argument('--auto-scroll', action='store_true', default=False,
                        help='Automatically scroll through the page before taking screenshot (for screenshot operation)')
    parser.add_argument('--scroll-timeout', type=int, default=30,
                        help='Maximum time to spend auto-scrolling in seconds (default: 30)')
    parser.add_argument('--scroll-step', type=int, default=300,
                        help='Pixel distance to scroll in each step (default: 300)')
    parser.add_argument('--scroll-delay', type=float, default=0.3,
                        help='Delay between scroll steps in seconds (default: 0.3)')
    
    args = parser.parse_args()
    
    print(f"Using browser client: {args.client_type}")
    print(f"Using browser: {args.browser}")
    print(f"Operation: {args.operation}")
    print(f"URL: {args.url}")
    print(f"Wait time: {args.wait} seconds")
    print(f"Headless mode: {args.headless}")
    
    # Reset profile path if --no-profile is specified
    if args.no_profile:
        args.profile_path = None
        print("Not using a profile")
    else:
        print(f"Profile path: {args.profile_path}")
        print(f"Profile directory: {args.profile_dir}")
    
    browser_client = None
    try:
        # Set up browser options
        browser_options = None
        
        if args.client_type == 'selenium':
            # Selenium-specific options
            if args.profile_path and not args.no_profile:
                if args.browser == 'chrome':
                    browser_options = ChromeOptions()
                    browser_options.add_argument(f"user-data-dir={args.profile_path}")
                    browser_options.add_argument(f"profile-directory={args.profile_dir}")
                elif args.browser == 'edge':
                    browser_options = EdgeOptions()
                    browser_options.add_argument(f"user-data-dir={args.profile_path}")
                    browser_options.add_argument(f"profile-directory={args.profile_dir}")
        else:
            # Playwright-specific options
            if args.browser == 'edge':
                # For Edge, we use Chromium with Edge-specific channel
                browser_options = {
                    "channel": "msedge"
                }
            elif args.profile_path and not args.no_profile:
                # For other browsers, we can use the profile path
                browser_options = {
                    "user_data_dir": args.profile_path
                }
        
        # Create a browser client
        browser_client = BrowserClientFactory.create_client(
            client_type=args.client_type,
            user_data_dir=args.profile_path,
            browser_type='edge' if args.client_type == 'playwright' and args.browser == 'edge' else args.browser
        )

        async with browser_client:  # Use as async context manager
            if args.operation == 'html':
                # Get HTML content
                print("Getting page HTML...")
                
                # Get the HTML content
                html = await browser_client.get_page_html(
                    args.url, 
                    wait_time=args.wait, 
                    headless=args.headless, 
                    options=browser_options
                )
                
                if html:
                    # Determine output path
                    output_path = args.output
                    if not output_path:
                        timestamp = int(time.time())
                        filename = f"page_html_{timestamp}.html"
                        output_path = os.path.join(output_dir, filename)
                    
                    # Save HTML to file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(html)
                    
                    print(f"HTML content saved to {output_path}")
                    print(f"HTML length: {len(html)} characters")
                else:
                    print("Failed to retrieve HTML content")
            
            elif args.operation == 'screenshot':
                # Take screenshot
                output_path = args.output
                if not output_path:
                    timestamp = int(time.time())
                    filename = f"screenshot_{timestamp}.png"
                    output_path = os.path.join(output_dir, filename)
                
                print(f"Taking screenshot, saving to {output_path}...")
                
                # Use the built-in auto-scroll functionality in the browser client
                success = await browser_client.take_screenshot(
                    args.url, 
                    output_path, 
                    wait_time=args.wait, 
                    headless=args.headless, 
                    options=browser_options,
                    auto_scroll=args.auto_scroll,
                    scroll_timeout=args.scroll_timeout,
                    scroll_step=args.scroll_step,
                    scroll_delay=args.scroll_delay
                )
                
                if success:
                    print(f"Screenshot saved successfully to {output_path}")
                else:
                    print("Failed to take screenshot")
            
            elif args.operation == 'markdown':
                # Get page markdown
                print("Getting page markdown...")
                
                # Get the HTML content first
                html_content = await browser_client.get_page_html(
                    args.url,
                    wait_time=args.wait,
                    headless=args.headless,
                    options=browser_options
                )

                if html_content:
                    # Convert HTML to Markdown
                    markdown_result = extract_and_format_html(
                        html_content,
                        include_links=args.include_links,
                        include_images=args.include_images
                    )

                    if markdown_result.get("extraction_success"):
                        markdown_content = markdown_result.get("markdown", "")
                        # Determine output path
                        output_path = args.output
                        if not output_path:
                            timestamp = int(time.time())
                            # Ensure the filename indicates it's a markdown file
                            base_name = os.path.splitext(os.path.basename(args.url.rstrip('/')))[0]
                            if not base_name or base_name == "index": # handle cases like example.com/ or example.com/index.html
                                base_name = "page"
                            filename = f"{base_name}_markdown_{timestamp}.md"
                            output_path = os.path.join(output_dir, filename)
                        
                        # Save Markdown to file
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(markdown_content)
                        
                        print(f"Markdown content saved to {output_path}")
                        print(f"Markdown length: {len(markdown_content)} characters")
                        if markdown_result.get("title"):
                            print(f"Page Title: {markdown_result.get('title')}")
                    else:
                        print(f"Failed to extract markdown from HTML. Error: {markdown_result.get('error')}")
                else:
                    print(f"Failed to retrieve HTML from {args.url} to generate markdown.")
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        # Ensure browser is properly closed, even if we didn't use the context manager
        if browser_client and not isinstance(browser_client, type):
            try:
                await browser_client.close()
            except Exception as e:
                print(f"Error during browser cleanup: {e}")
        
        # Force garbage collection
        import gc
        gc.collect()
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main())) 