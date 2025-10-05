import requests
import pytest


class TestToolsAPI:
    def test_list_tools(self, server_url):
        resp = requests.get(f"{server_url}/api/tools", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert data["total"] == len(data["tools"])

    def test_get_tool_detail(self, server_url):
        # First get list of tools
        resp = requests.get(f"{server_url}/api/tools", timeout=5)
        assert resp.status_code == 200
        tools = resp.json()["tools"]

        if len(tools) > 0:
            # Get detail for first tool
            tool_name = tools[0]["name"]
            resp = requests.get(f"{server_url}/api/tools/{tool_name}", timeout=5)
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == tool_name
            assert "description" in data
            assert "input_schema" in data
            assert "category" in data
            assert "source" in data
            assert "active" in data

    def test_get_tool_detail_not_found(self, server_url):
        resp = requests.get(f"{server_url}/api/tools/nonexistent_tool_xyz", timeout=5)
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_tool_stats(self, server_url):
        resp = requests.get(f"{server_url}/api/tools/stats", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tools" in data
        assert "active_tools" in data
        assert "code_tools" in data
        assert "yaml_tools" in data

    def test_tool_categories(self, server_url):
        resp = requests.get(f"{server_url}/api/tools/categories", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert "plugin_groups" in data
        assert "tool_sources" in data

    def test_execute_tool_not_found(self, server_url):
        resp = requests.post(
            f"{server_url}/api/tools/nonexistent_tool_xyz/execute", json={}, timeout=5
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_execute_tool_with_no_parameters(self, server_url):
        # First get list of tools
        resp = requests.get(f"{server_url}/api/tools", timeout=5)
        assert resp.status_code == 200
        tools = resp.json()["tools"]

        # Find a tool with no parameters
        tool_without_params = None
        for tool in tools:
            if tool["active"]:
                schema = tool.get("input_schema", {})
                properties = schema.get("properties", {})
                if len(properties) == 0:
                    tool_without_params = tool
                    break

        if tool_without_params:
            # Execute the tool
            resp = requests.post(
                f"{server_url}/api/tools/{tool_without_params['name']}/execute",
                json={},
                timeout=10,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "result" in data

    def test_execute_tool_with_parameters(self, server_url):
        # First get list of tools
        resp = requests.get(f"{server_url}/api/tools", timeout=5)
        assert resp.status_code == 200
        tools = resp.json()["tools"]

        # Find an active tool with parameters
        tool_with_params = None
        for tool in tools:
            if tool["active"]:
                schema = tool.get("input_schema", {})
                properties = schema.get("properties", {})
                if len(properties) > 0:
                    tool_with_params = tool
                    break

        if tool_with_params:
            # Build minimal valid parameters
            schema = tool_with_params["input_schema"]
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            # Create parameters with required fields
            params = {}
            for prop_name in required:
                prop_details = properties.get(prop_name, {})
                prop_type = prop_details.get("type", "string")

                # Provide minimal valid values based on type
                if prop_type == "string":
                    params[prop_name] = "test_value"
                elif prop_type == "number" or prop_type == "integer":
                    params[prop_name] = 1
                elif prop_type == "boolean":
                    params[prop_name] = True
                elif prop_type == "array":
                    params[prop_name] = []
                elif prop_type == "object":
                    params[prop_name] = {}

            # Execute the tool (may fail due to invalid params, but should not 404)
            resp = requests.post(
                f"{server_url}/api/tools/{tool_with_params['name']}/execute",
                json=params,
                timeout=10,
            )
            # Accept both success and error responses (as long as tool was found)
            assert resp.status_code in [200, 400, 500]
            data = resp.json()
            # Should have either result or error
            assert "result" in data or "error" in data

    def test_execute_tool_with_invalid_json(self, server_url):
        # First get an active tool
        resp = requests.get(f"{server_url}/api/tools", timeout=5)
        assert resp.status_code == 200
        tools = resp.json()["tools"]

        active_tool = None
        for tool in tools:
            if tool["active"]:
                active_tool = tool
                break

        if active_tool:
            # Send invalid JSON (as text)
            resp = requests.post(
                f"{server_url}/api/tools/{active_tool['name']}/execute",
                data="invalid json",
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            # Should handle gracefully (either 400 or execute with empty params)
            assert resp.status_code in [200, 400, 500]

    def test_execute_tool_empty_body(self, server_url):
        # First get an active tool
        resp = requests.get(f"{server_url}/api/tools", timeout=5)
        assert resp.status_code == 200
        tools = resp.json()["tools"]

        active_tool = None
        for tool in tools:
            if tool["active"]:
                active_tool = tool
                break

        if active_tool:
            # Execute with no body
            resp = requests.post(
                f"{server_url}/api/tools/{active_tool['name']}/execute", timeout=10
            )
            # Should handle gracefully
            assert resp.status_code in [200, 400, 500]
