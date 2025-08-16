import pytest
from unittest.mock import patch, MagicMock

from mcp_tools.browser.factory import BrowserClientFactory
from plugins.knowledge_indexer.tool import KnowledgeIndexerTool


@pytest.mark.asyncio
async def test_browser_tool_network_failure():
    """Browser tool should handle network errors gracefully."""
    client = BrowserClientFactory.create_client("playwright")

    # Mock the underlying PlaywrightWrapper to simulate network failure
    with patch("mcp_tools.browser.playwright_client.PlaywrightWrapper") as mock_wrapper:
        # Configure the mock to raise an exception when creating the async context manager
        mock_wrapper.return_value.__aenter__.side_effect = Exception("Network unreachable")

        result = await client.get_page_html("https://example.com")

    assert result is None


@pytest.mark.asyncio
async def test_knowledge_indexer_permission_error():
    """Knowledge indexer should report permission errors."""
    tool = KnowledgeIndexerTool()
    files = [{"filename": "test.md", "content": "# Test", "encoding": "utf-8"}]

    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        result = await tool.execute_tool({"files": files})

    assert result["success"] is False
    assert "Permission denied" in result["error"]
