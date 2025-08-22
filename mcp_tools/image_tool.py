"""Image retrieval tool for MCP."""

import os
import mimetypes
import base64
from pathlib import Path
from typing import Dict, Any, List, Union, Optional, cast

from mcp.types import ImageContent, TextContent
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool
from config.manager import EnvironmentManager, env_manager


@register_tool
class ImageTool(ToolInterface):
    """Tool for retrieving images and files from configured image directory."""

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "get_session_image"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Get an image for a given session_id and image_name."

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID to look for images in",
                },
                "image_name": {
                    "type": "string",
                    "description": "The name of the image file to retrieve",
                },
            },
            "required": ["session_id", "image_name"],
        }

    def _get_image_dir(self) -> Path:
        """Get the image directory from configuration."""
        manager: EnvironmentManager = cast(EnvironmentManager, env_manager)
        image_dir = manager.get_setting("image_dir", None)
        if not image_dir:
            raise RuntimeError(
                "IMAGE_DIR is not defined in your MCP configuration. "
                "Set IMAGE_DIR in your .env file or MCP settings."
            )
        return Path(image_dir)

    async def execute_tool(
        self, arguments: Dict[str, Any]
    ) -> List[Union[ImageContent, TextContent]]:
        """Execute the image retrieval tool.

        Args:
            arguments: Dictionary containing session_id and image_name

        Returns:
            List containing either ImageContent or TextContent
        """
        # Validate required arguments
        session_id = arguments.get("session_id")
        image_name = arguments.get("image_name")

        if not session_id or not image_name:
            return [
                TextContent(
                    type="text", text="Error: session_id and image_name are required."
                )
            ]

        return self._get_session_image(session_id, image_name)

    def _get_session_image(
        self, session_id: str, image_name: str
    ) -> List[Union[ImageContent, TextContent]]:
        """
        Return an image for a given session_id and image_name.
        Looks for the image at {IMAGE_DIR}/{session_id}/{image_name}.
        Returns the image bytes base64-encoded as a string with the correct MIME type.
        """
        try:
            image_dir = self._get_image_dir()
            image_path = image_dir / session_id / image_name

            if not image_path.is_file():
                return [TextContent(type="text", text="Image not found.")]

            # Special-case support for JSON files: return raw text content
            if str(image_path).lower().endswith(".json"):
                with open(image_path, "r", encoding="utf-8") as f:
                    json_text = f.read()
                return [TextContent(type="text", text=json_text)]

            # Handle image files
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

        except Exception as e:
            return [TextContent(type="text", text=f"Error retrieving image: {str(e)}")]
