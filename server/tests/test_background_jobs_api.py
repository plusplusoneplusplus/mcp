import re
import asyncio
import requests
import pytest
from .conftest import create_mcp_client

class TestBackgroundJobsAPI:
    def test_list_jobs_initially_empty(self, server_url):
        resp = requests.get(f"{server_url}/api/background-jobs", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 0
        assert data["running_count"] == 0

    @pytest.mark.asyncio
    async def test_background_job_lifecycle(self, server_url, mcp_client_info):
        server_sse_url = mcp_client_info["url"]
        worker_id = mcp_client_info["worker_id"]
        async with create_mcp_client(server_sse_url, worker_id) as session:
            result = await session.call_tool("execute_task", {"task_name": "system_info"})
            token = None
            for c in result.content:
                text = getattr(c, "text", "")
                m = re.search(r"token: ([A-Za-z0-9-]+)", text)
                if m:
                    token = m.group(1)
                    break
            assert token, "Token not found in tool output"
            await session.call_tool("query_task_status", {"token": token, "wait": True})

        resp = requests.get(f"{server_url}/api/background-jobs/{token}", timeout=5)
        assert resp.status_code == 200
        job = resp.json()
        assert job["status"] == "completed"
        assert job.get("duration", 0) >= 0

        resp = requests.get(f"{server_url}/api/background-jobs", timeout=5)
        data = resp.json()
        assert any(j.get("token") == token for j in data["jobs"])

        stats_resp = requests.get(f"{server_url}/api/background-jobs/stats", timeout=5)
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["total_completed"] >= 1
