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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test web pages using BrowserClient')
    parser.add_argument('url', help='URL to visit')
    parser.add_argument('--operation', '-o', choices=['html', 'screenshot'], default='html',
                        help='Operation to perform: get HTML or take screenshot (default: html)')
    parser.add_argument('--wait', '-w', type=int, default=5,
                        help='Time to wait for page load in seconds (default: 5)')
    parser.add_argument('--output', '-f',
                        help='Output file path for screenshot or HTML (default: auto-generated)')
    parser.add_argument('--browser', '-b', choices=['chrome', 'edge'], default='chrome',
                        help='Browser to use (default: chrome)')
    parser.add_argument('--headless', action='store_true', default=False,
                        help='Run browser in headless mode (default: False)')
    
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
    
    try:
        if args.operation == 'html':
            # Get HTML content
            print("Getting page HTML...")
            # Create a browser client instance with specified headless mode
            browser = BrowserClient.setup_browser(headless=args.headless)
            
            try:
                # Navigate to the page
                browser.get(args.url)
                
                # Wait for the page to load
                time.sleep(args.wait)
                
                # Get the page source
                html = browser.page_source
                
                if html:
                    # Determine output path
                    output_path = args.output
                    if not output_path:
                        timestamp = int(time.time())
                        output_path = f"page_html_{timestamp}.html"
                    
                    # Save HTML to file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(html)
                    
                    print(f"HTML content saved to {output_path}")
                    print(f"HTML length: {len(html)} characters")
                else:
                    print("Failed to retrieve HTML content")
            finally:
                browser.quit()
        
        elif args.operation == 'screenshot':
            # Take screenshot
            output_path = args.output
            if not output_path:
                timestamp = int(time.time())
                output_path = f"screenshot_{timestamp}.png"
            
            print(f"Taking screenshot, saving to {output_path}...")
            
            # Create a browser client instance with specified headless mode
            browser = BrowserClient.setup_browser(headless=args.headless)
            
            try:
                # Navigate to the page
                browser.get(args.url)
                
                # Wait for the page to load
                time.sleep(args.wait)
                
                # Take screenshot
                success = browser.save_screenshot(output_path)
                
                if success:
                    print(f"Screenshot saved successfully to {output_path}")
                else:
                    print("Failed to take screenshot")
            finally:
                browser.quit()
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 