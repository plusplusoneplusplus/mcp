import os
from pathlib import Path
import mimetypes
import base64
from typing import Optional, cast
from config.manager import EnvironmentManager, env_manager
from mcp.types import ImageContent, TextContent, Tool


def get_tool_def() -> Tool:
    return Tool(
        name="get_session_image",
        description="Get an image for a given session_id and image_name.",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "image_name": {"type": "string"},
            },
            "required": ["session_id", "image_name"],
        },
    )


def handle_tool(arguments: dict):
    if (
        "session_id" not in arguments
        or "image_name" not in arguments
        or arguments.get("session_id") is None
        or arguments.get("image_name") is None
    ):
        return [
            TextContent(
                type="text", text="Error: session_id and image_name are required."
            )
        ]

    return get_session_image(arguments["session_id"], arguments["image_name"])


def get_image_dir() -> Path:
    """Get the image directory from configuration."""
    manager: EnvironmentManager = cast(EnvironmentManager, env_manager)
    image_dir = manager.get_setting("image_dir", None)
    if not image_dir:
        raise RuntimeError(
            "IMAGE_DIR is not defined in your MCP configuration. "
            "Set IMAGE_DIR in your .env file or MCP settings."
        )
    return Path(image_dir)


def get_session_image(
    session_id: str, image_name: str
) -> list[ImageContent | TextContent]:
    """
    Return an image for a given session_id and image_name.
    Looks for the image at {IMAGE_DIR}/{session_id}/{image_name}.
    Returns the image bytes base64-encoded as a string with the correct MIME type, or None if not found.
    """
    image_dir = get_image_dir()
    image_path = image_dir / session_id / image_name
    if not image_path.is_file():
        return [TextContent(type="text", text="Image not found.")]

    # Special-case support for JSON files: return raw text content
    if str(image_path).lower().endswith(".json"):
        with open(image_path, "r", encoding="utf-8") as f:
            json_text = f.read()
        return [TextContent(type="text", text=json_text)]

    mime_type, _ = mimetypes.guess_type(str(image_path))
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    return [
        ImageContent(
            type="image",
            data=image_b64,
            mimeType=mime_type or "application/octet-stream",
        )
    ]
