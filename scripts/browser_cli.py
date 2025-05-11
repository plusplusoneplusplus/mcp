#!/usr/bin/env python3
"""
Standalone program for using IBrowserClient to test different web pages.
This program allows you to get HTML content or take screenshots of web pages.
"""

import os
import time
import asyncio
import click
from mcp_tools.browser.factory import BrowserClientFactory
from mcp_tools.browser.client import BrowserClient
from utils.html_to_markdown import extract_and_format_html
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

# Get the scripts directory path
script_dir = os.path.dirname(os.path.abspath(__file__))

# Default paths
output_dir = os.path.join(script_dir, 'browser_outputs')
default_profile_path = os.path.join(script_dir, '.profile')

# Ensure directories exist
os.makedirs(output_dir, exist_ok=True)
os.makedirs(default_profile_path, exist_ok=True)

# Common options for all commands
def common_browser_options(f):
    """Common browser configuration options."""
    f = click.option('--browser', '-b', 
                   type=click.Choice(['chrome', 'edge', 'chromium', 'firefox', 'webkit']), 
                   default='edge', help='Browser to use (default: edge)')(f)
    f = click.option('--wait', '-w', type=int, default=5,
                   help='Time to wait for page load in seconds (default: 5)')(f)
    f = click.option('--headless/--no-headless', default=False, 
                   help='Run browser in headless mode (default: False)')(f)
    f = click.option('--client-type', type=click.Choice(['selenium', 'playwright']), 
                   default='playwright', help='Type of browser client to use (default: playwright)')(f)
    f = click.option('--output', '-o', help=f'Output file path (default: auto-generated in {output_dir})')(f)
    return f

def profile_options(f):
    """Browser profile related options."""
    f = click.option('--profile-path', '-p', default=default_profile_path,
                  help=f'Path to browser profile (default: {default_profile_path})')(f)
    f = click.option('--profile-dir', '-d', default='Default',
                  help='Profile directory name (default: Default)')(f)
    f = click.option('--no-profile', is_flag=True, default=False,
                  help='Do not use a browser profile')(f)
    return f

# Create a Click command group
@click.group(help='Web page testing tool using browser automation')
def cli():
    """Web page testing tool that allows getting HTML, screenshots, or markdown from web pages."""
    pass

# Helper function to set up browser options
def setup_browser_options(client_type, browser, profile_path, profile_dir, no_profile):
    """Set up browser options based on client type and browser."""
    if no_profile:
        profile_path = None
    
    browser_options = None
    if client_type == 'selenium':
        if profile_path:
            if browser == 'chrome':
                browser_options = ChromeOptions()
                browser_options.add_argument(f"user-data-dir={profile_path}")
                browser_options.add_argument(f"profile-directory={profile_dir}")
            elif browser == 'edge':
                browser_options = EdgeOptions()
                browser_options.add_argument(f"user-data-dir={profile_path}")
                browser_options.add_argument(f"profile-directory={profile_dir}")
    else:
        if browser == 'edge':
            browser_options = {"channel": "msedge"}
        elif profile_path:
            browser_options = {"user_data_dir": profile_path}
    
    return browser_options, profile_path

# Helper function to create browser client
async def create_browser_client(client_type, browser, profile_path):
    """Create a browser client based on the specified options."""
    return BrowserClientFactory.create_client(
        client_type=client_type,
        user_data_dir=profile_path,
        browser_type='edge' if client_type == 'playwright' and browser == 'edge' else browser
    )

# Helper function to generate output path
def get_output_path(output, operation, url=None):
    """Generate an output path if one isn't provided."""
    if output:
        return output
    
    timestamp = int(time.time())
    
    if operation == 'html':
        filename = f"page_html_{timestamp}.html"
    elif operation == 'screenshot':
        filename = f"screenshot_{timestamp}.png"
    elif operation == 'markdown' and url:
        base_name = os.path.splitext(os.path.basename(url.rstrip('/')))[0]
        if not base_name or base_name == "index":
            base_name = "page"
        filename = f"{base_name}_markdown_{timestamp}.md"
    else:
        filename = f"output_{timestamp}"
        
    return os.path.join(output_dir, filename)

# HTML command
@cli.command()
@click.argument('url')
@common_browser_options
@profile_options
async def html(url, browser, wait, headless, client_type, output, profile_path, profile_dir, no_profile):
    """Get HTML content from a web page."""
    click.echo(f"Getting HTML from {url}")
    
    browser_options, profile_path = setup_browser_options(
        client_type, browser, profile_path, profile_dir, no_profile
    )
    
    browser_client = await create_browser_client(client_type, browser, profile_path)
    
    try:
        async with browser_client:
            html_content = await browser_client.get_page_html(
                url, wait_time=wait, headless=headless, options=browser_options
            )
            
            if html_content:
                output_path = get_output_path(output, 'html')
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                click.echo(f"HTML content saved to {output_path}")
                click.echo(f"HTML length: {len(html_content)} characters")
                return 0
            else:
                click.echo("Failed to retrieve HTML content")
                return 1
    except Exception as e:
        click.echo(f"Error: {e}")
        return 1
    finally:
        if browser_client:
            try:
                await browser_client.close()
            except Exception as e:
                click.echo(f"Error during browser cleanup: {e}")

# Screenshot command
@cli.command()
@click.argument('url')
@common_browser_options
@profile_options
@click.option('--auto-scroll/--no-auto-scroll', default=False,
             help='Automatically scroll through the page (default: False)')
@click.option('--scroll-timeout', type=int, default=30,
             help='Maximum time for auto-scrolling in seconds (default: 30)')
@click.option('--scroll-step', type=int, default=300,
             help='Pixel distance per scroll step (default: 300)')
@click.option('--scroll-delay', type=float, default=0.3,
             help='Delay between scroll steps in seconds (default: 0.3)')
async def screenshot(url, browser, wait, headless, client_type, output, profile_path, 
                  profile_dir, no_profile, auto_scroll, scroll_timeout, scroll_step, scroll_delay):
    """Take a screenshot of a web page."""
    browser_options, profile_path = setup_browser_options(
        client_type, browser, profile_path, profile_dir, no_profile
    )
    
    output_path = get_output_path(output, 'screenshot')
    click.echo(f"Taking screenshot of {url}, saving to {output_path}")
    
    browser_client = await create_browser_client(client_type, browser, profile_path)
    
    try:
        async with browser_client:
            success = await browser_client.take_screenshot(
                url, output_path, wait_time=wait, headless=headless, options=browser_options,
                auto_scroll=auto_scroll, scroll_timeout=scroll_timeout,
                scroll_step=scroll_step, scroll_delay=scroll_delay
            )
            
            if success:
                click.echo(f"Screenshot saved successfully to {output_path}")
                return 0
            else:
                click.echo("Failed to take screenshot")
                return 1
    except Exception as e:
        click.echo(f"Error: {e}")
        return 1
    finally:
        if browser_client:
            try:
                await browser_client.close()
            except Exception as e:
                click.echo(f"Error during browser cleanup: {e}")

# Markdown command
@cli.command()
@click.argument('url')
@common_browser_options
@profile_options
@click.option('--include-links/--no-include-links', default=True,
             help='Include links in the markdown (default: True)')
@click.option('--include-images/--no-include-images', default=False,
             help='Include image references in the markdown (default: False)')
async def markdown(url, browser, wait, headless, client_type, output, profile_path, 
                profile_dir, no_profile, include_links, include_images):
    """Convert a web page to markdown."""
    click.echo(f"Converting {url} to markdown")
    
    browser_options, profile_path = setup_browser_options(
        client_type, browser, profile_path, profile_dir, no_profile
    )
    
    browser_client = await create_browser_client(client_type, browser, profile_path)
    
    try:
        async with browser_client:
            html_content = await browser_client.get_page_html(
                url, wait_time=wait, headless=headless, options=browser_options
            )
            
            if html_content:
                markdown_result = extract_and_format_html(
                    html_content, include_links=include_links, include_images=include_images
                )
                
                if markdown_result.get("extraction_success"):
                    markdown_content = markdown_result.get("markdown", "")
                    output_path = get_output_path(output, 'markdown', url)
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                    
                    click.echo(f"Markdown content saved to {output_path}")
                    click.echo(f"Markdown length: {len(markdown_content)} characters")
                    if markdown_result.get("title"):
                        click.echo(f"Page Title: {markdown_result.get('title')}")
                    return 0
                else:
                    click.echo(f"Failed to extract markdown: {markdown_result.get('error')}")
                    return 1
            else:
                click.echo(f"Failed to retrieve HTML from {url}")
                return 1
    except Exception as e:
        click.echo(f"Error: {e}")
        return 1
    finally:
        if browser_client:
            try:
                await browser_client.close()
            except Exception as e:
                click.echo(f"Error during browser cleanup: {e}")
        
        # Force garbage collection
        import gc
        gc.collect()

# Main entry point
def main():
    """Entry point for the CLI application."""
    return asyncio.run(cli())

if __name__ == "__main__":
    exit(main()) 