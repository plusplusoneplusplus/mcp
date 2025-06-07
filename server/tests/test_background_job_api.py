import requests
import pytest


def test_background_job_endpoints(server_url):
    """Ensure background job monitoring endpoints respond."""
    list_resp = requests.get(f"{server_url}/api/background-jobs")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "jobs" in data
    assert "total_count" in data

    stats_resp = requests.get(f"{server_url}/api/background-jobs/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert "current_running" in stats
    assert "total_completed" in stats

    detail_resp = requests.get(f"{server_url}/api/background-jobs/nonexistent")
    assert detail_resp.status_code in (200, 404)
