import pytest
from unittest.mock import patch, MagicMock

from mcp_tools.browser.selenium_client import SeleniumBrowserClient
from plugins.knowledge_indexer.tool import KnowledgeIndexerTool


@pytest.mark.asyncio
async def test_browser_tool_network_failure():
    """Browser tool should handle network errors gracefully."""
    client = SeleniumBrowserClient()

    # Patch webdriver setup and cleanup
    with patch.object(client, "_setup_browser") as mock_setup, patch.object(
        client, "_cleanup_driver"
    ) as mock_cleanup:
        mock_driver = MagicMock()
        mock_setup.return_value = mock_driver
        mock_driver.get.side_effect = Exception("Network unreachable")
        result = await client.get_page_html("https://example.com")

    mock_cleanup.assert_called_once_with(mock_driver)
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
