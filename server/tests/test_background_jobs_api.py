import re
import asyncio
import requests
import pytest
import logging
import platform
from .conftest import create_mcp_client

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestBackgroundJobsAPI:
    def test_list_jobs_initially_empty(self, server_url):
        logger.debug(f"Testing list_jobs_initially_empty with server_url: {server_url}")
        resp = requests.get(f"{server_url}/api/background-jobs", timeout=5)
        logger.debug(f"Response status: {resp.status_code}")
        assert resp.status_code == 200
        data = resp.json()
        logger.debug(f"Response data: {data}")
        assert data["total_count"] == 0
        assert data["running_count"] == 0

    @pytest.mark.asyncio
    @pytest.mark.skipif(platform.system() == "Windows", reason="Disabled on Windows")
    async def test_background_job_lifecycle(self, server_url, mcp_client_info):
        logger.debug(f"Starting test_background_job_lifecycle with server_url: {server_url}")
        logger.debug(f"MCP client info: {mcp_client_info}")
        
        server_sse_url = mcp_client_info["url"]
        worker_id = mcp_client_info["worker_id"]
        
        logger.debug(f"Creating MCP client with URL: {server_sse_url}, worker_id: {worker_id}")
        async with create_mcp_client(server_sse_url, worker_id) as session:
            logger.debug("MCP client session created successfully")
            
            logger.debug("Calling execute_task tool with system_info")
            result = await session.call_tool("execute_task", {"task_name": "system_info"})
            logger.debug(f"execute_task result: {result}")
            
            token = None
            logger.debug("Searching for token in result content")
            for c in result.content:
                text = getattr(c, "text", "")
                logger.debug(f"Processing content text: {text}")
                m = re.search(r"token: ([A-Za-z0-9-]+)", text)
                if m:
                    token = m.group(1)
                    logger.debug(f"Found token: {token}")
                    break
            assert token, "Token not found in tool output"
            
            logger.debug(f"Calling query_task_status with token: {token}")
            await session.call_tool("query_task_status", {"token": token, "wait": True})
            logger.debug("query_task_status completed")

        logger.debug(f"MCP session closed, now checking job status via HTTP API")
        resp = requests.get(f"{server_url}/api/background-jobs/{token}", timeout=5)
        logger.debug(f"Job status response: {resp.status_code}")
        assert resp.status_code == 200
        job = resp.json()
        logger.debug(f"Job details: {job}")
        assert job["status"] == "completed"
        assert job.get("duration", 0) >= 0

        logger.debug("Getting all background jobs")
        resp = requests.get(f"{server_url}/api/background-jobs", timeout=5)
        data = resp.json()
        logger.debug(f"All jobs response: {data}")
        assert any(j.get("token") == token for j in data["jobs"])

        logger.debug("Getting background jobs stats")
        stats_resp = requests.get(f"{server_url}/api/background-jobs/stats", timeout=5)
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        logger.debug(f"Stats response: {stats}")
        assert stats["total_completed"] >= 1
        
        logger.debug("test_background_job_lifecycle completed successfully")
