"""Web Summarizer Plugin for MCP Tools.

This plugin provides tools for extracting content from HTML and URLs and converting it to markdown.
"""

from plugins.text_summarizer.tool import WebSummarizerTool, UrlSummarizerTool

__all__ = ["WebSummarizerTool", "UrlSummarizerTool"]
