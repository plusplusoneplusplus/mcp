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
from sentinel.command_executor import CommandExecutor

# Setup logging
SCRIPT_DIR = Path(__file__).resolve().parent
# Ensure the logs directory exists
log_dir = SCRIPT_DIR / ".logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(SCRIPT_DIR, ".logs", "sentinel.log")),
        logging.StreamHandler(),
    ],
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
    db_path = SCRIPT_DIR / ".vectordb"
    db = chromadb.PersistentClient(path=str(db_path))
    collection = db.get_or_create_collection(name="sentinel_collection")

    # Setup command executor
    cmd_executor = CommandExecutor()

    try:
        yield AppContext(collection=collection, cmd_executor=cmd_executor)
    finally:
        pass


# Pass lifespan to server
mcp = FastMCP("Sentinel", lifespan=app_lifespan)

# Define allowed commands
LINUX_ALLOWED_COMMANDS = ["ls", "pwd", "echo"]
WINDOWS_ALLOWED_COMMANDS = ["dir", "echo"]

@mcp.prompt()
async def add_or_update_dc(ctx: Context, dc_name: str) -> Dict[str, Any]:
    """Add or update a dc"""
    return f"Creating {dc_name}.json file"


if __name__ == "__main__":
    # Start the server
    import uvicorn

    print("Starting fast server...")  # Add a log message for clarity
    uvicorn.run(mcp.app, host="0.0.0.0", port=8000)