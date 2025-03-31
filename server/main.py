import os
from pathlib import Path
from typing import Dict, Any, List
import chromadb
from chromadb.config import Settings
from chromadb.api import Collection
import logging
import click
import sys

# Add lifespan support for startup/shutdown with strong typing
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

import logging
from pathlib import Path
from typing import Sequence
from mcp.server import Server
from mcp.server.session import ServerSession
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

server = Server("mymcp")

async def start_server() -> None:
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

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return tools.get_tools()

    @server.call_tool()
    async def call_tool_handler(name: str, arguments: dict) -> list[TextContent]:
        return await tools.call_tool(name, arguments)

    options = server.create_initialization_options()
    # Add prompt capabilities
    options.capabilities.prompts = PromptsCapability(supported=True)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)


@click.command()
def main() -> None:
    import asyncio
    asyncio.run(start_server())

if __name__ == "__main__":
    main()