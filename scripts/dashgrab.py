#!/usr/bin/env python3
"""
Grab every dashboard panel that matches a CSS selector and save it as PNG.
Example:
    python dashgrab.py https://play.grafana.org/d/000000016/time-series-graphs?orgId=1&from=now-1h&to=now&timezone=browser \
        -s ".react-grid-item" -t $GRAFANA_TOKEN
"""
import os
import pathlib
import re
import click
import asyncio
from mcp_tools.browser.browser_client import BrowserClientFactory

@click.command(help="Capture each matching element as an image")
# test url: https://play.grafana.org/d/000000016/time-series-graphs\?orgId\=1\&from\=now-1h\&to\=now\&timezone\=browser
@click.argument('url')
@click.option('--selector', '-s', default=".react-grid-item",
             help="CSS selector for chart containers")
@click.option('--out', '-o', default=".charts", type=click.Path(),
             help="Directory to write PNGs")
@click.option('--width', '-w', default=1600, type=int)
@click.option('--height', '-h', default=900, type=int)
@click.option('--token', '-t', help="Bearer token for Authorization header")
def capture(url, selector, out, width, height, token):
    """Capture each matching element as an image using the PlaywrightBrowserClient."""
    # Always use a '.charts' subdirectory in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = pathlib.Path(os.path.join(script_dir, out))
    out_dir.mkdir(exist_ok=True)

    async def run_capture():
        # Use the same default profile path as browser_cli.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_profile_path = os.path.join(script_dir, '.profile')
        browser_type = 'edge'  # or 'chrome', depending on your default preference
        client = BrowserClientFactory.create_client(
            client_type='playwright',
            user_data_dir=default_profile_path,
            browser_type=browser_type
        )
        try:
            count = await client.capture_panels(
                url=url,
                selector=selector,
                out_dir=str(out_dir),
                width=width,
                height=height,
                token=token,
                wait_time=10,
                headless=False,
                options=None,
                autoscroll=True
            )
            if count > 0:
                click.echo(f"Successfully captured {count} panels.")
            else:
                click.echo(f"No elements matched '{selector}'.")
        except Exception as e:
            click.echo(f"Error capturing panels: {e}")
            raise click.Abort()

    asyncio.run(run_capture())

if __name__ == "__main__":
    capture()
