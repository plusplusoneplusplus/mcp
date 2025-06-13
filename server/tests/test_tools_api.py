import requests


class TestToolsAPI:
    def test_list_tools(self, server_url):
        resp = requests.get(f"{server_url}/api/tools", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert data["total"] == len(data["tools"])
