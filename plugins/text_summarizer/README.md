# Web Summarizer Plugin

A MCP tool plugin that extracts and summarizes web content from HTML or URLs into markdown format.

## Overview

This plugin implements web content extractors that take HTML input or a URL and return clean, formatted markdown. It uses the trafilatura library to extract the main content, removing boilerplate and irrelevant elements.

## Usage

### HTML Content Extraction

```python
from mcp_tools.plugin import registry
from plugins.text_summarizer import WebSummarizerTool

# Get an instance of the tool
web_summarizer = registry.get_tool_instance("web_summarizer")

# Use the tool
result = await web_summarizer.execute_tool({
    "html": "<html>Your HTML content to extract...</html>",
    "include_links": True,  # optional
    "include_images": True   # optional
})

print(result["markdown"])
```

### URL Content Extraction

```python
from mcp_tools.plugin import registry
from plugins.text_summarizer import UrlSummarizerTool

# Get an instance of the tool
url_summarizer = registry.get_tool_instance("url_summarizer")

# Use the tool
result = await url_summarizer.execute_tool({
    "url": "https://example.com/article",
    "include_links": True,  # optional
    "include_images": True,  # optional
    "timeout": 30           # optional
})

print(result["markdown"])
```

## Input Schema

### Web Summarizer Tool

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| html | string | Yes | The HTML content to extract and summarize |
| include_links | boolean | No | Whether to include links in the extracted content (default: True) |
| include_images | boolean | No | Whether to include image references in the extracted content (default: True) |

### URL Summarizer Tool

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | string | Yes | The URL to fetch and extract content from |
| include_links | boolean | No | Whether to include links in the extracted content (default: True) |
| include_images | boolean | No | Whether to include image references in the extracted content (default: True) |
| timeout | integer | No | Timeout in seconds for the HTTP request (default: 30) |

## Output Format

### Web Summarizer Tool

| Key | Type | Description |
|-----|------|-------------|
| markdown | string | The extracted content in markdown format |
| extraction_success | boolean | Whether the extraction was successful |
| original_size | integer | Size (in characters) of the original HTML |
| extracted_size | integer | Size (in characters) of the extracted markdown |

### URL Summarizer Tool

| Key | Type | Description |
|-----|------|-------------|
| markdown | string | The extracted content in markdown format |
| extraction_success | boolean | Whether the extraction was successful |
| url | string | The URL that was processed |
| original_size | integer | Size (in characters) of the original HTML |
| extracted_size | integer | Size (in characters) of the extracted markdown |
| error | string | Error message if fetching the URL failed (only present on error) |

## Integration with MCP

This plugin is automatically registered with the MCP plugin registry when imported. To ensure it's discovered, you can add the plugin folder to your Python path or include it directly in your project.

## Development

To modify this plugin, update the `tool.py` file. Make sure to test your changes before deploying.

## Dependencies

This plugin requires the trafilatura library and httpx. You can install them using:

```
pip install trafilatura httpx
```

or with uv:

```
uv pip install trafilatura httpx
``` 