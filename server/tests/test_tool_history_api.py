import requests
import pytest
from .conftest import create_mcp_client


class TestToolHistoryAPI:
    @pytest.mark.asyncio
    async def test_tool_history_flow(self, server_url, mcp_client_info):
        async with create_mcp_client(mcp_client_info["url"], mcp_client_info["worker_id"]) as session:
            await session.list_tools()

        resp = requests.get(f"{server_url}/api/tool-history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        invocation_id = data["history"][0]["invocation_id"]

        detail = requests.get(f"{server_url}/api/tool-history/{invocation_id}")
        assert detail.status_code == 200
        assert detail.json()["records"]

        stats = requests.get(f"{server_url}/api/tool-history/stats")
        assert stats.status_code == 200
        assert stats.json()["stats"]["total_invocations"] >= 1

        export = requests.get(f"{server_url}/api/tool-history/export")
        assert export.status_code == 200
        assert "history" in export.json()

        clear = requests.post(f"{server_url}/api/tool-history/clear", json={"confirm": True})
        assert clear.status_code == 200
        assert requests.get(f"{server_url}/api/tool-history").json()["total"] == 0
