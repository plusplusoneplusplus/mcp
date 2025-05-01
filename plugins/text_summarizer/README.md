# Text Summarizer Plugin

A simple MCP tool plugin that provides text summarization functionality.

## Overview

This plugin implements a basic text summarizer that takes text input and returns a summarized version. The summarization is currently implemented as a simple truncation algorithm, but could be extended to use more sophisticated NLP techniques.

## Usage

```python
from mcp_tools.plugin import registry
from plugins.text_summarizer import TextSummarizerTool

# Get an instance of the tool
summarizer = registry.get_tool_instance("text_summarizer")

# Use the tool
result = await summarizer.execute_tool({
    "text": "Your long text to summarize...",
    "max_length": 50  # optional
})

print(result["summary"])
```

## Input Schema

The tool accepts the following parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | The text content to summarize |
| max_length | integer | No | Maximum length of summary in words (default: 100) |

## Output Format

The tool returns a dictionary with the following keys:

| Key | Type | Description |
|-----|------|-------------|
| summary | string | The summarized text |
| original_length | integer | Word count of the original text |
| summary_length | integer | Word count of the summary |

## Integration with MCP

This plugin is automatically registered with the MCP plugin registry when imported. To ensure it's discovered, you can add the plugin folder to your Python path or include it directly in your project.

## Development

To modify this plugin, update the `tool.py` file. Make sure to test your changes before deploying. 