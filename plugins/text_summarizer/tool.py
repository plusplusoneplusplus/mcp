"""Text Summarizer tool implementation."""

import json
from typing import Dict, Any

# Import the required interfaces and decorators
from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool


@register_tool
class TextSummarizerTool(ToolInterface):
    """Tool for summarizing text content."""
    
    @property
    def name(self) -> str:
        """Return the name of the tool."""
        return "text_summarizer"
    
    @property
    def description(self) -> str:
        """Return a description of the tool."""
        return "Summarizes the provided text content into a concise form."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Define the input schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text content to summarize"
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum length of the summary in words",
                    "default": 100
                }
            },
            "required": ["text"]
        }
    
    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the text summarization.
        
        Args:
            arguments: Dictionary containing the input parameters
            
        Returns:
            Dictionary containing the summary result
        """
        text = arguments.get("text", "")
        max_length = arguments.get("max_length", 100)
        
        # Simple summarization algorithm - just for demonstration
        # In a real plugin, you would use a proper NLP library
        words = text.split()
        if len(words) <= max_length:
            summary = text
        else:
            # Very naive summarization - take first max_length words
            summary = " ".join(words[:max_length]) + "..."
        
        return {
            "summary": summary,
            "original_length": len(words),
            "summary_length": min(len(words), max_length)
        } 