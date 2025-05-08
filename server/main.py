import os
from pathlib import Path
import logging
import click
import asyncio
import json
import datetime
import time
from typing import Dict, Any, Optional

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

# Import tools directly from mcp_tools
from mcp_tools.plugin import registry, discover_and_register_tools
from mcp_tools.dependency import injector
from mcp_tools.interfaces import ToolInterface

# Import plugin configuration
from mcp_tools.plugin_config import config

import prompts
from config import env

# The configuration is already loaded from environment variables in PluginConfig.__init__
# No need to override it here

# Create the server
server = Server("mymcp")

# Initialize tools system directly
discover_and_register_tools()
injector.resolve_all_dependencies()

# Get all tools and filtered active tools
all_tool_instances = list(injector.get_all_instances().values())
active_tool_instances = list(injector.get_filtered_instances().values())

# Log information about registered and active tools
logging.info(f"Registered {len(all_tool_instances)} total tools, {len(active_tool_instances)} active tools")

# Log tool sources
tool_sources = registry.get_tool_sources()
code_tools = [name for name, source in tool_sources.items() if source == "code"]
yaml_tools = [name for name, source in tool_sources.items() if source == "yaml"]
active_tools = [tool.name for tool in active_tool_instances]
inactive_tools = [name for name in tool_sources.keys() if name not in active_tools]

logging.info(f"Code tools ({len(code_tools)}): {', '.join(code_tools) if code_tools else 'None'}")
logging.info(f"YAML tools ({len(yaml_tools)}): {', '.join(yaml_tools) if yaml_tools else 'None'}")
logging.info(f"Active tools ({len(active_tools)}): {', '.join(active_tools) if active_tools else 'None'}")
logging.info(f"Inactive tools ({len(inactive_tools)}): {', '.join(inactive_tools) if inactive_tools else 'None'}")

for tool in active_tool_instances:
    logging.info(f"  - {tool.name}: {tool.description}")

# Tool history recording functions
def get_new_invocation_dir(tool_name: str) -> Path:
    """Create and return a new directory for this tool invocation."""
    if not env.is_tool_history_enabled():
        return None
    base_path = env.get_tool_history_path()
    if not os.path.isabs(base_path):
        current_dir = Path(__file__).resolve().parent
        base_path = current_dir / base_path
    history_dir = Path(base_path)
    history_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    # Directory name includes tool name for clarity
    invocation_dir = history_dir / f"{timestamp}_{tool_name}"
    invocation_dir.mkdir(parents=True, exist_ok=True)
    return invocation_dir

def record_tool_invocation(tool_name: str, arguments: Dict[str, Any], 
                          result: Any, duration_ms: float,
                          success: bool = True, error: Optional[str] = None,
                          invocation_dir: Optional[Path] = None) -> bool:
    """Record a tool invocation to a record.jsonl file in the invocation directory."""
    if not env.is_tool_history_enabled() or invocation_dir is None:
        return False
    try:
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "tool": tool_name,
            "arguments": arguments,
            "result": result if isinstance(result, (dict, list, str, int, float, bool, type(None))) 
                      else str(result),
            "duration_ms": duration_ms,
            "success": success
        }
        if error:
            record["error"] = error
        record_file = invocation_dir / "record.jsonl"
        with open(record_file, "a", encoding="utf-8") as f:
            json_str = json.dumps(record, indent=4, sort_keys=True)
            f.write(json_str + "\n")
        logging.debug(f"Recorded tool invocation for {tool_name} in {record_file}")
        return True
    except Exception as e:
        logging.error(f"Error recording tool invocation: {e}")
        return False

# Setup tools using the direct plugin system
@server.list_tools()
async def list_tools() -> list[Tool]:
    # Get all tool instances that are active according to config
    tool_instances = list(injector.get_filtered_instances().values())
    mcp_tools = []
    
    for tool in tool_instances:
        # Create a new mcp.types.Tool instance from our tool data
        mcp_tool = Tool(
            name=tool.name,
            description=tool.description,
            inputSchema=tool.input_schema
        )
        mcp_tools.append(mcp_tool)
    
    return mcp_tools

@server.call_tool()
async def call_tool_handler(name: str, arguments: dict) -> list[TextContent]:
    tool = injector.get_tool_instance(name)
    invocation_dir = get_new_invocation_dir(name) if env.is_tool_history_enabled() else None
    if tool and invocation_dir:
        tool.diagnostic_dir = str(invocation_dir)
    if not tool:
        error_msg = f"Error: Tool '{name}' not found."
        record_tool_invocation(name, arguments, error_msg, 0, False, error_msg, invocation_dir)
        return [TextContent(type="text", text=error_msg)]
    tool_sources = registry.get_tool_sources()
    source = tool_sources.get(name, "unknown")
    if not config.is_source_enabled(source):
        error_msg = f"Error: Tool '{name}' is disabled. Source '{source}' is not active."
        record_tool_invocation(name, arguments, error_msg, 0, False, error_msg, invocation_dir)
        return [TextContent(type="text", text=error_msg)]
    start_time = time.time()
    result = None
    success = True
    error_msg = None
    try:
        logging.info(f"Executing tool '{name}' with arguments: {arguments}")
        # Call the tool directly (diagnostic_dir is now set as a property)
        result = await tool.execute_tool(arguments)
        duration_ms = (time.time() - start_time) * 1000
        logging.info(f"Tool '{name}' executed successfully in {duration_ms:.2f}ms")
        if isinstance(result, list) and all(isinstance(item, dict) for item in result):
            text_content = [TextContent(**item) for item in result]
        elif isinstance(result, list) and all(hasattr(item, 'type') and hasattr(item, 'text') for item in result):
            text_content = [TextContent(type=item.type, text=item.text, annotations=getattr(item, 'annotations', None)) for item in result]
        elif isinstance(result, dict):
            text = format_result_as_text(result)
            text_content = [TextContent(type="text", text=text)]
        else:
            text_content = [TextContent(type="text", text=str(result))]
        record_tool_invocation(name, arguments, result, duration_ms, True, None, invocation_dir)
        return text_content
    except Exception as e:
        logging.exception(f"Error executing tool {name}")
        error_msg = f"Error executing tool {name}: {str(e)}"
        success = False
        duration_ms = (time.time() - start_time) * 1000
        record_tool_invocation(name, arguments, None, duration_ms, False, error_msg, invocation_dir)
        return [TextContent(type="text", text=error_msg)]

def format_result_as_text(result: dict) -> str:
    """Format a result dictionary as text."""
    if not result.get("success", True):
        return f"Error: {result.get('error', 'Unknown error')}"
        
    # Different formatting based on the type of result
    if "output" in result:
        return result.get("output", "")
    elif "html" in result:
        return f"HTML content (length: {result.get('html_length', 0)}):\n{result.get('html', '')}"
    elif "parameters" in result:
        params = result.get("parameters", {})
        return "Environment parameters:\n" + "\n".join(f"{k}: {v}" for k, v in params.items())
    else:
        # Generic formatting
        return "\n".join(f"{k}: {v}" for k, v in result.items() if k != "success")

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

    # Use Path consistently for the log file path
    log_file = log_dir / "server.log"
    
    # Reset the logging configuration
    # This is important as basicConfig won't do anything if the root logger 
    # already has handlers configured
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        handler.close()
    
    # Configure logging with explicit handler setup
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # File handler
    file_handler = logging.FileHandler(str(log_file.absolute()))
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Initialize environment using the new module
    env.load()
    logger.info(f"Initialized environment: Git root={env.get_git_root()}, " +
                f"Workspace folder={env.get_workspace_folder()}")
    
    # Log tool history settings
    if env.is_tool_history_enabled():
        history_path = get_new_invocation_dir("NEW_SERVER_START")
        logger.info(f"Tool history recording is enabled. Recording to: {history_path}")
    else:
        logger.info("Tool history recording is disabled")


@click.command()
def main() -> None:
    # Run setup first (non-async)
    setup()
    
    # Then run uvicorn directly without nested asyncio.run
    uvicorn.run(starlette_app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()