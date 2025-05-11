#!/usr/bin/env python3
"""
Grab every dashboard panel that matches a CSS selector and save it as PNG.
Example:
    python dashgrab.py https://play.grafana.org/d/000000016/time-series-graphs?orgId=1&from=now-1h&to=now&timezone=browser \
        -s ".react-grid-item" -t $GRAFANA_TOKEN
"""
import pathlib
import re
import click
import asyncio
from mcp_tools.browser.playwright_client import PlaywrightBrowserClient

@click.command(help="Capture each matching element as an image")
@click.argument('url')
@click.option('--selector', '-s', default=".react-grid-item",
             help="CSS selector for chart containers")
@click.option('--out', '-o', default="charts", type=click.Path(),
             help="Directory to write PNGs")
@click.option('--width', '-w', default=1600, type=int)
@click.option('--height', '-h', default=900, type=int)
@click.option('--token', '-t', help="Bearer token for Authorization header")
def capture(url, selector, out, width, height, token):
    """Capture each matching element as an image using the PlaywrightBrowserClient."""
    out_dir = pathlib.Path(out)
    out_dir.mkdir(exist_ok=True)

    async def run_capture():
        client = PlaywrightBrowserClient()
        try:
            count = await client.capture_panels(
                url=url,
                selector=selector,
                out_dir=str(out_dir),
                width=width,
                height=height,
                token=token,
                wait_time=30,
                headless=True,
                options=None
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
