#!/usr/bin/env python3
"""
Grab every dashboard panel that matches a CSS selector and save it as PNG.
Example:
    python dashgrab.py https://play.grafana.org/d/000000016/time-series-graphs?orgId=1&from=now-1h&to=now&timezone=browser \
        -s ".react-grid-item" -t $GRAFANA_TOKEN
"""
import pathlib, re, typer
from playwright.sync_api import sync_playwright

app = typer.Typer(help="Capture each matching element as an image")

@app.command()
def capture(
    url: str,
    selector: str = typer.Option(
        ".react-grid-item",
        "--selector", "-s",
        help="CSS selector for chart containers"
    ),
    out_dir: pathlib.Path = typer.Option(
        "charts", "--out", "-o", help="Directory to write PNGs"
    ),
    width: int = typer.Option(1600, "--width", "-w"),
    height: int = typer.Option(900, "--height", "-h"),
    token: str = typer.Option(
        None, "--token", "-t", help="Bearer token for Authorization header"
    ),
):
    out_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        page = p.chromium.launch(headless=True).new_page(
            viewport={'width': width, 'height': height}
        )
        if token:
            page.set_extra_http_headers({"Authorization": f"Bearer {token}"})
        page.goto(url, wait_until="networkidle")

        panels = page.locator(selector).all()
        if not panels:
            typer.echo(f"No elements matched '{selector}'.")
            raise typer.Exit(code=1)

        for idx, el in enumerate(panels, 1):
            # Try different attribute names that might contain panel IDs
            pid = None
            for attr in ["data-panelid", "data-griditem-key", "data-viz-panel-key"]:
                pid = el.get_attribute(attr)
                if pid:
                    # Extract just the numeric part if it follows a pattern like "panel-1"
                    match = re.search(r'(?:panel|grid-item)-(\d+)', pid)
                    if match:
                        pid = match.group(1)
                    break
            
            # If no ID was found, use the index
            if not pid:
                pid = f"{idx:02d}"
                
            el.screenshot(path=out_dir / f"panel_{pid}.png")
            typer.echo(f"Saved panel_{pid}.png")

if __name__ == "__main__":
    app()
