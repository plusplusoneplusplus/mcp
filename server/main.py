import os
from pathlib import Path
import logging
import click
import json
import datetime
import time
from typing import Dict, Any, Optional, Union, List

# Import startup tracing utilities
from server.startup_tracer import (
    time_operation,
    trace_startup_time,
    log_startup_summary,
    save_startup_report,
    start_timing,
    finish_timing,
)

# Starlette and uvicorn imports
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from server.api import api_routes

import uvicorn

# MCP imports
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, ImageContent, Tool, PromptsCapability

# Import tools directly from mcp_tools
from mcp_tools.plugin import registry, discover_and_register_tools
from mcp_tools.dependency import injector

# Import plugin configuration
from mcp_tools.plugin_config import config

from config import env

from server import image_tool
from server.tool_result_processor import process_tool_result

# Create the server
server = Server("mymcp")

# Add debug logging for server events
logging.info("MCP Server created successfully")

# Initialize tools system directly with tracing
with time_operation("Tool Discovery and Registration"):
    discover_and_register_tools()

with time_operation("Dependency Resolution"):
    injector.resolve_all_dependencies()

# Get all tools and filtered active tools
all_tool_instances = list(injector.get_all_instances().values())
active_tool_instances = list(injector.get_filtered_instances().values())

# Log information about registered and active tools with enhanced plugin visibility
logging.info("=" * 60)
logging.info("TOOL REGISTRATION AND ACTIVATION SUMMARY")
logging.info("=" * 60)
logging.info(
    f"Registered {len(all_tool_instances)} total tools, {len(active_tool_instances)} active tools"
)

# Log tool sources with plugin information
tool_sources = registry.get_tool_sources()
code_tools = [name for name, source in tool_sources.items() if source == "code"]
yaml_tools = [name for name, source in tool_sources.items() if source == "yaml"]
active_tools = [tool.name for tool in active_tool_instances]
inactive_tools = [name for name in tool_sources.keys() if name not in active_tools]

# Get plugin loading summary for enhanced visibility
plugin_summary = registry.get_plugin_loading_summary()

logging.info(
    f"Code tools ({len(code_tools)}): {', '.join(code_tools) if code_tools else 'None'}"
)
logging.info(
    f"YAML tools ({len(yaml_tools)}): {', '.join(yaml_tools) if yaml_tools else 'None'}"
)
logging.info(
    f"Active tools ({len(active_tools)}): {', '.join(active_tools) if active_tools else 'None'}"
)
logging.info(
    f"Inactive tools ({len(inactive_tools)}): {', '.join(inactive_tools) if inactive_tools else 'None'}"
)

# Enhanced plugin source information
if plugin_summary.get("plugin_groups"):
    logging.info(f"Tools by plugin source:")
    for plugin_source, tools in plugin_summary["plugin_groups"].items():
        if tools:
            active_in_source = [tool for tool in tools if tool in active_tools]
            inactive_in_source = [tool for tool in tools if tool not in active_tools]
            logging.info(f"  • {plugin_source}:")
            if active_in_source:
                logging.info(f"    Active: {', '.join(active_in_source)}")
            if inactive_in_source:
                logging.info(f"    Inactive: {', '.join(inactive_in_source)}")

# Plugin root directories information
from mcp_tools.plugin_config import config

plugin_roots = config.get_plugin_roots()
if plugin_roots:
    logging.info(f"Plugin root directories:")
    for plugin_root in plugin_roots:
        logging.info(f"  • {plugin_root}")

# Discovered plugin directories
if plugin_summary.get("discovered_plugin_paths"):
    logging.info(f"Discovered plugin directories:")
    for plugin_path in plugin_summary["discovered_plugin_paths"]:
        logging.info(f"  • {plugin_path}")

logging.info(f"Active tool details:")
for tool in active_tool_instances:
    source = tool_sources.get(tool.name, "unknown")
    source_prefix = (
        "[CODE]" if source == "code" else "[YAML]" if source == "yaml" else "[UNKNOWN]"
    )
    logging.info(f"  {source_prefix} {tool.name}: {tool.description}")

logging.info("=" * 60)


# Tool history recording functions
def get_new_invocation_dir(tool_name: str) -> Optional[Path]:
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


def record_tool_invocation(
    tool_name: str,
    arguments: Dict[str, Any],
    result: Any,
    duration_ms: float,
    success: bool = True,
    error: Optional[str] = None,
    invocation_dir: Optional[Path] = None,
) -> bool:
    """Record a tool invocation to a record.jsonl file in the invocation directory."""
    if not env.is_tool_history_enabled() or invocation_dir is None:
        return False
    try:
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "tool": tool_name,
            "arguments": arguments,
            "result": (
                result
                if isinstance(result, (dict, list, str, int, float, bool, type(None)))
                else str(result)
            ),
            "duration_ms": duration_ms,
            "success": success,
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


@server.list_tools()
async def list_tools() -> list[Tool]:
    # Get all tool instances that are active according to config
    tool_instances = list(injector.get_filtered_instances().values())
    mcp_tools = []

    for tool in tool_instances:
        # Create a new mcp.types.Tool instance from our tool data
        mcp_tool = Tool(
            name=tool.name, description=tool.description, inputSchema=tool.input_schema
        )
        mcp_tools.append(mcp_tool)

    mcp_tools.append(image_tool.get_tool_def())
    return mcp_tools


@server.call_tool()
async def call_tool_handler(
    name: str, arguments: dict
) -> list[Union[TextContent, ImageContent]]:
    logging.info(f"TOOL CALL HANDLER INVOKED: {name} with arguments: {arguments}")
    logging.info(f"Handler running on platform: {os.name}")

    invocation_dir = (
        get_new_invocation_dir(name) if env.is_tool_history_enabled() else None
    )

    # Special case for image_tool
    if name == "get_session_image":
        try:
            return image_tool.handle_tool(arguments)
        except Exception as e:
            return [TextContent(type="text", text=str(e))]
        finally:
            record_tool_invocation(
                name, arguments, None, 0, False, None, invocation_dir
            )

    tool = injector.get_tool_instance(name)
    if tool and invocation_dir:
        tool.diagnostic_dir = str(invocation_dir)
    if not tool:
        # Debug: Log available tools when tool is not found
        available_tools = list(injector.get_all_instances().keys())
        filtered_tools = list(injector.get_filtered_instances().keys())
        logging.error(f"Tool '{name}' not found. Available tools: {available_tools}")
        logging.error(f"Filtered tools: {filtered_tools}")

        # Enhanced error message with more explicit error indicators
        error_msg = f"Error: Tool '{name}' not found. Available tools: {', '.join(available_tools) if available_tools else 'None'}"

        # Log additional debugging information for Windows troubleshooting
        logging.debug(
            f"Tool lookup failed for '{name}' - Platform: {os.name}, Worker: {os.environ.get('PYTEST_WORKER_ID', 'unknown')}"
        )

        record_tool_invocation(
            name, arguments, error_msg, 0, False, error_msg, invocation_dir
        )
        response = [TextContent(type="text", text=error_msg)]
        logging.info(f"Returning error response for tool '{name}': {response}")
        return response
    tool_sources = registry.get_tool_sources()
    source = tool_sources.get(name, "unknown")
    if not config.is_source_enabled(source):
        error_msg = (
            f"Error: Tool '{name}' is disabled. Source '{source}' is not active."
        )
        record_tool_invocation(
            name, arguments, error_msg, 0, False, error_msg, invocation_dir
        )
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

        # Process the tool result into appropriate content types
        content_items = process_tool_result(result)
        record_tool_invocation(
            name, arguments, result, duration_ms, True, None, invocation_dir
        )
        return content_items
    except Exception as e:
        logging.exception(f"Error executing tool {name}")
        error_msg = f"Error executing tool {name}: {str(e)}"
        success = False
        duration_ms = (time.time() - start_time) * 1000

        # Enhanced error logging for debugging
        logging.debug(
            f"Tool execution exception details - Tool: {name}, Platform: {os.name}, Exception: {repr(e)}"
        )

        record_tool_invocation(
            name, arguments, None, duration_ms, False, error_msg, invocation_dir
        )
        return [TextContent(type="text", text=error_msg)]


# Setup SSE transport
sse = SseServerTransport("/messages/")


async def handle_sse(request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        options = server.create_initialization_options()
        # Add prompt capabilities
        options.capabilities.prompts = PromptsCapability(supported=True)

        # Enhanced error handling for Windows compatibility
        try:
            await server.run(streams[0], streams[1], options, raise_exceptions=False)
        except Exception as e:
            logging.error(f"SSE handler error: {type(e).__name__}: {e}")
            logging.debug(f"SSE handler exception details: {repr(e)}")
            # Don't re-raise to prevent worker crashes
            pass


# --- Web Knowledge Import UI ---
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# --- Main Web Page ---
from server.api.base import PERSIST_DIR


async def index(request: Request):
    # Redirect to knowledge page as the main landing page
    from starlette.responses import RedirectResponse

    return RedirectResponse(url="/knowledge", status_code=302)


# --- New Page Routes ---
async def knowledge(request: Request):
    return templates.TemplateResponse(
        "knowledge.html",
        {"request": request, "import_path": PERSIST_DIR, "current_page": "knowledge"},
    )


async def jobs(request: Request):
    return templates.TemplateResponse(
        "jobs.html", {"request": request, "current_page": "jobs"}
    )


async def config_page(request: Request):
    return templates.TemplateResponse(
        "config.html", {"request": request, "current_page": "config"}
    )


async def tools_page(request: Request):
    return templates.TemplateResponse(
        "tools.html", {"request": request, "current_page": "tools"}
    )


async def tool_history_page(request: Request):
    return templates.TemplateResponse(
        "tool_history.html", {"request": request, "current_page": "tool_history"}
    )


async def visualizations_page(request: Request):
    return templates.TemplateResponse(
        "task_visualization.html",
        {"request": request, "current_page": "visualizations"},
    )


async def dataframes_page(request: Request):
    return templates.TemplateResponse(
        "dataframes.html", {"request": request, "current_page": "dataframes"}
    )


async def dataframe_detail_page(request: Request):
    df_id = request.path_params["df_id"]
    return templates.TemplateResponse(
        "dataframe_detail.html",
        {"request": request, "current_page": "dataframes", "df_id": df_id},
    )


async def pyeval_page(request: Request):
    return templates.TemplateResponse(
        "pyeval.html", {"request": request, "current_page": "pyeval"}
    )


# --- Add routes ---
routes = [
    Route("/", endpoint=index, methods=["GET"]),
    Route("/knowledge", endpoint=knowledge, methods=["GET"]),
    Route("/jobs", endpoint=jobs, methods=["GET"]),
    Route("/tools", endpoint=tools_page, methods=["GET"]),
    Route("/tool-history", endpoint=tool_history_page, methods=["GET"]),
    Route("/visualizations", endpoint=visualizations_page, methods=["GET"]),
    Route("/dataframes", endpoint=dataframes_page, methods=["GET"]),
    Route("/dataframes/{df_id}", endpoint=dataframe_detail_page, methods=["GET"]),
    Route("/pyeval", endpoint=pyeval_page, methods=["GET"]),
    Route("/config", endpoint=config_page, methods=["GET"]),
    Route("/sse", endpoint=handle_sse),
    Mount("/messages/", app=sse.handle_post_message),
    Mount(
        "/static",
        StaticFiles(directory=str(Path(__file__).parent / "static")),
        name="static",
    ),
] + api_routes

# Create Starlette app
starlette_app = Starlette(routes=routes)


# Setup function for logging and environment
@trace_startup_time("Server Setup")
def setup():
    with time_operation("Logging Configuration"):
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
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    with time_operation("Environment Initialization"):
        # Initialize environment using the new module
        env.load()
        logger.info(f"Initialized environment: Git root={env.get_git_root()}")

        # Log tool history settings
        if env.is_tool_history_enabled():
            history_path = get_new_invocation_dir("NEW_SERVER_START")
            logger.info(
                f"Tool history recording is enabled. Recording to: {history_path}"
            )
        else:
            logger.info("Tool history recording is disabled")


@click.command()
@click.option("--port", default=None, type=int, help="Port to run the server on")
@trace_startup_time("Main Server Startup")
def main(port: Optional[int] = None) -> None:
    with time_operation("Complete Server Initialization"):
        # Run setup first (non-async)
        setup()

        # Determine port from CLI argument, environment variable, or default
        if port is None:
            port = int(os.environ.get("SERVER_PORT", 8000))

        logging.info(f"Starting server on port {port}")

        # Log startup summary before starting the server
        log_startup_summary()
        save_startup_report()

    # Then run uvicorn directly without nested asyncio.run
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
