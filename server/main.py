import os
from pathlib import Path
import logging
import click
import asyncio

# Starlette and uvicorn imports
from starlette.applications import Starlette
from starlette.routing import Route, Mount
import uvicorn

# MCP imports
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import (
    TextContent,
    Tool,
    PromptsCapability
)

# Local and MCP Core imports
from mcp_core.tools_adapter import ToolsAdapter
import prompts
from mcp_tools.environment import env

# Create the server
server = Server("mymcp")

# Create tools adapter instance
tools_adapter = ToolsAdapter()

# Setup tools using the new tools adapter
@server.list_tools()
async def list_tools() -> list[Tool]:
    # Convert our tools to the mcp.types.Tool format expected by the server
    core_tools = tools_adapter.get_tools()
    mcp_tools = []
    
    for core_tool in core_tools:
        # Create a new mcp.types.Tool instance from our tool data
        mcp_tool = Tool(
            name=core_tool.name,
            description=core_tool.description,
            inputSchema=core_tool.inputSchema
        )
        mcp_tools.append(mcp_tool)
    
    return mcp_tools

@server.call_tool()
async def call_tool_handler(name: str, arguments: dict) -> list[TextContent]:
    # Here we use the TextContent from mcp.types as defined above
    result = await tools_adapter.call_tool(name, arguments)
    
    # Convert our TextContent objects to mcp.types.TextContent objects if needed
    mcp_result = []
    for item in result:
        mcp_text = TextContent(
            type=item.type,
            text=item.text,
            annotations=item.annotations
        )
        mcp_result.append(mcp_text)
        
    return mcp_result

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
    
    # Initialize environment using the new module
    env.load()
    logger.info(f"Initialized environment: Git root={env.get_git_root()}, " +
                f"Workspace folder={env.get_workspace_folder()}")


@click.command()
def main() -> None:
    # Run setup first (non-async)
    setup()
    
    # Then run uvicorn directly without nested asyncio.run
    uvicorn.run(starlette_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()