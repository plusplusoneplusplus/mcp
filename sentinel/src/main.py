import os
from pathlib import Path
from typing import Dict, Any, List
import chromadb
from chromadb.config import Settings
from chromadb.api import Collection
import logging

# Add lifespan support for startup/shutdown with strong typing
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP

from command_executor import CommandExecutor

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AppContext:
    collection: Collection
    cmd_executor: CommandExecutor

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""

    # Setup vector database
    db = chromadb.PersistentClient(path="./.vectordb")
    collection = db.get_or_create_collection(name="sentinel_collection")

    # Setup command executor
    cmd_executor = CommandExecutor()

    try:
        yield AppContext(
            collection=collection,
            cmd_executor=cmd_executor
        )
    finally:
        pass

# Pass lifespan to server
mcp = FastMCP("Sentinel", lifespan=app_lifespan)

# Define allowed commands
LINUX_ALLOWED_COMMANDS = ["ls", "pwd", "echo"]
WINDOWS_ALLOWED_COMMANDS = ["dir", "echo"]

@mcp.tool(
    arguments=[
        {
            "name": "command",
            "type": "string",
            "description": "The command to execute (e.g., ls, dir, echo, pwd)",
            "required": True
        }
    ]
)
async def execute_command(ctx: Context, command: str) -> Dict[str, Any]:
    """Execute allowed system commands"""
    return ctx.request_context.lifespan_context.cmd_executor.execute(command)