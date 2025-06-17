"""Web Summarizer tool implementation."""

import json
import httpx
from typing import Dict, Any

# Import the required interfaces and decorators
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool
from utils.html_to_markdown import extract_and_format_html


@register_tool(os_type="all")
class WebSummarizerTool(ToolInterface):
    """Tool for summarizing web content and converting it to markdown."""

    @property
    def name(self) -> str:
        """Return the name of the tool."""
        return "web_summarizer"

    @property
    def description(self) -> str:
        """Return a description of the tool."""
        return "Extracts and summarizes content from HTML into markdown format."

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Define the input schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "html": {
                    "type": "string",
                    "description": "The HTML content to extract and summarize",
                },
                "include_links": {
                    "type": "boolean",
                    "description": "Whether to include links in the extracted content",
                    "default": True,
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Whether to include image references in the extracted content",
                    "default": True,
                },
            },
            "required": ["html"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the web content extraction and conversion to markdown.

        Args:
            arguments: Dictionary containing the input parameters

        Returns:
            Dictionary containing the extraction result
        """
        html = arguments.get("html", "")
        include_links = arguments.get("include_links", True)
        include_images = arguments.get("include_images", True)

        # Use the utility function to extract and format HTML
        return extract_and_format_html(
            html, include_links=include_links, include_images=include_images
        )


@register_tool(os_type="all")
class UrlSummarizerTool(ToolInterface):
    """Tool for fetching a URL and extracting its content into markdown."""

    @property
    def name(self) -> str:
        """Return the name of the tool."""
        return "url_summarizer"

    @property
    def description(self) -> str:
        """Return a description of the tool."""
        return "Fetches a URL and extracts its content into markdown format."

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Define the input schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch and extract content from",
                },
                "include_links": {
                    "type": "boolean",
                    "description": "Whether to include links in the extracted content",
                    "default": True,
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Whether to include image references in the extracted content",
                    "default": True,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds for the HTTP request",
                    "default": 30,
                },
            },
            "required": ["url"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the URL fetching, extraction and conversion to markdown.

        Args:
            arguments: Dictionary containing the input parameters

        Returns:
            Dictionary containing the extraction result
        """
        url = arguments.get("url", "")
        include_links = arguments.get("include_links", True)
        include_images = arguments.get("include_images", True)
        timeout = arguments.get("timeout", 30)

        # Fetch the URL content
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=timeout, follow_redirects=True)
                response.raise_for_status()
                html = response.text
        except httpx.HTTPError as e:
            return {
                "markdown": "",
                "extraction_success": False,
                "error": f"Failed to fetch URL: {str(e)}",
                "url": url,
            }

        # Use the utility function to extract and format HTML
        result = extract_and_format_html(
            html, include_links=include_links, include_images=include_images
        )

        # Add the URL to the result
        result["url"] = url

        return result
