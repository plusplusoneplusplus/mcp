import os
from pathlib import Path
from typing import Dict, Any, List
import chromadb
from chromadb.config import Settings
from chromadb.api import Collection
import logging
import click
import sys
import asyncio

# Add lifespan support for startup/shutdown with strong typing
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

import logging
from pathlib import Path
from typing import Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    ClientCapabilities,
    TextContent,
    Tool,
    ListRootsResult,
    RootsCapability,
    Prompt,
    PromptArgument,
    GetPromptResult,
    PromptMessage,
    PromptsCapability
)

from enum import Enum
from pydantic import BaseModel

# Import tools and prompts directly since they're in the same directory
import tools
import prompts
import environment

# Import Starlette and uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
import uvicorn

# Create the server
server = Server("mymcp")

# Setup tools
@server.list_tools()
async def list_tools() -> list[Tool]:
    return tools.get_tools()

@server.call_tool()
async def call_tool_handler(name: str, arguments: dict) -> list[TextContent]:
    return await tools.call_tool(name, arguments)

# Setup SSE transport
sse = SseServerTransport("/messages/")

async def handle_sse(request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        options = server.create_initialization_options()
        # Add prompt capabilities
        options.capabilities.prompts = PromptsCapability(supported=True)
        await server.run(
            streams[0], streams[1], options, raise_exceptions=True
        )

# Create Starlette routes
routes = [
    Route("/sse", endpoint=handle_sse),
    Mount("/messages/", app=sse.handle_post_message),
]

# Create Starlette app
starlette_app = Starlette(routes=routes)

# Setup function for logging and environment
def setup():
    # Setup logging
    SCRIPT_DIR = Path(__file__).resolve().parent
    # Ensure the logs directory exists
    log_dir = SCRIPT_DIR / ".logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(SCRIPT_DIR, ".logs", "server.log")),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger(__name__)
    
    # Initialize environment
    env = environment.env
    env.load()
    logger.info(f"Initialized environment: Git root={env.repository_info.git_root}, " +
                f"Workspace folder={env.repository_info.workspace_folder}")


@click.command()
def main() -> None:
    # Run setup first (non-async)
    setup()
    
    # Then run uvicorn directly without nested asyncio.run
    uvicorn.run(starlette_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()