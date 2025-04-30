#!/usr/bin/env python3
"""
Standalone program for using the BrowserClient tool to test different web pages.
This program allows you to get HTML content or take screenshots of web pages.
"""

import os
import argparse
import time
from mcp_tools.browser.client import BrowserClient

def main():
    # Get the scripts directory path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(script_dir, 'browser_outputs')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create default profile directory if it doesn't exist
    default_profile_path = os.path.join(script_dir, '.profile')
    os.makedirs(default_profile_path, exist_ok=True)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test web pages using BrowserClient')
    parser.add_argument('url', help='URL to visit')
    parser.add_argument('--operation', '-o', choices=['html', 'screenshot'], default='html',
                        help='Operation to perform: get HTML or take screenshot (default: html)')
    parser.add_argument('--wait', '-w', type=int, default=30,
                        help='Time to wait for page load in seconds (default: 30)')
    parser.add_argument('--output', '-f',
                        help=f'Output file path for screenshot or HTML (default: auto-generated in {output_dir})')
    parser.add_argument('--browser', '-b', choices=['chrome', 'edge'], default='chrome',
                        help='Browser to use (default: chrome)')
    parser.add_argument('--headless', action='store_true', default=False,
                        help='Run browser in headless mode (default: False)')
    parser.add_argument('--profile-path', '-p', default=default_profile_path,
                        help=f'Path to browser profile directory (default: {default_profile_path})')
    parser.add_argument('--profile-dir', '-d', default='Default',
                        help='Profile directory name within the profile path (default: Default)')
    parser.add_argument('--no-profile', action='store_true', default=False,
                        help='Do not use a profile (ignore profile-path and profile-dir)')
    
    args = parser.parse_args()
    
    # Set the browser type
    from mcp_tools.browser.client import DEFAULT_BROWSER_TYPE
    import mcp_tools.browser.client as browser_module
    browser_module.DEFAULT_BROWSER_TYPE = args.browser
    
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
    
    try:
        # Set up browser options if profile is specified
        browser_options = None
        if args.profile_path and not args.no_profile:
            if args.browser == 'chrome':
                from selenium.webdriver.chrome.options import Options as ChromeOptions
                browser_options = ChromeOptions()
                browser_options.add_argument(f"user-data-dir={args.profile_path}")
                browser_options.add_argument(f"profile-directory={args.profile_dir}")
            elif args.browser == 'edge':
                from selenium.webdriver.edge.options import Options as EdgeOptions
                browser_options = EdgeOptions()
                browser_options.add_argument(f"user-data-dir={args.profile_path}")
                browser_options.add_argument(f"profile-directory={args.profile_dir}")
        
        if args.operation == 'html':
            # Get HTML content
            print("Getting page HTML...")
            
            # Get the HTML content
            html = BrowserClient.get_page_html(args.url, args.wait, options=browser_options, headless=args.headless)
            
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
            
            # Take the screenshot
            success = BrowserClient.take_screenshot(args.url, output_path, args.wait, options=browser_options, headless=args.headless)
            
            if success:
                print(f"Screenshot saved successfully to {output_path}")
            else:
                print("Failed to take screenshot")
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 