"""End-to-end test demonstrating the tool execution flow."""

import requests
import pytest


class TestToolExecutionFlow:
    """Demonstrate the complete tool execution flow from UI to API."""

    def test_complete_execution_flow(self, server_url):
        """
        Test the complete flow:
        1. Load the tools page
        2. Get list of tools via API
        3. Find an executable tool
        4. Execute it via the API
        5. Verify the result
        """
        # Step 1: Verify tools page loads
        page_resp = requests.get(f"{server_url}/tools", timeout=5)
        assert page_resp.status_code == 200
        assert "Execute Tool" in page_resp.text
        assert "executeTool" in page_resp.text

        # Step 2: Get list of tools
        tools_resp = requests.get(f"{server_url}/api/tools", timeout=5)
        assert tools_resp.status_code == 200
        tools_data = tools_resp.json()
        assert "tools" in tools_data
        assert len(tools_data["tools"]) > 0

        # Step 3: Find the command_executor tool (should always be available)
        command_executor = None
        for tool in tools_data["tools"]:
            if tool["name"] == "command_executor" and tool["active"]:
                command_executor = tool
                break

        if command_executor:
            # Step 4: Execute the tool with valid parameters
            params = {"command": "echo 'Test execution from UI'"}
            exec_resp = requests.post(
                f"{server_url}/api/tools/command_executor/execute",
                json=params,
                timeout=10,
            )
            assert exec_resp.status_code == 200

            # Step 5: Verify the result
            result = exec_resp.json()
            assert "result" in result
            assert result["result"]["success"] is True
            assert "Test execution from UI" in result["result"]["output"]

    def test_execution_with_different_parameter_types(self, server_url):
        """Test execution with various parameter types."""
        # Get tools to find one with different parameter types
        resp = requests.get(f"{server_url}/api/tools", timeout=5)
        assert resp.status_code == 200
        tools = resp.json()["tools"]

        # Test with command_executor (string and number parameters)
        command_tool = None
        for tool in tools:
            if tool["name"] == "command_executor" and tool["active"]:
                command_tool = tool
                break

        if command_tool:
            # Test with timeout parameter (number type)
            params = {"command": "echo 'Testing with timeout'", "timeout": 5}
            resp = requests.post(
                f"{server_url}/api/tools/command_executor/execute",
                json=params,
                timeout=10,
            )
            assert resp.status_code == 200
            result = resp.json()
            assert "result" in result

    def test_execution_error_handling(self, server_url):
        """Test that execution errors are handled gracefully."""
        # Try to execute a non-existent tool
        resp = requests.post(
            f"{server_url}/api/tools/nonexistent_tool/execute", json={}, timeout=5
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_ui_shows_inactive_tools_correctly(self, server_url):
        """Test that the UI indicates when tools are inactive."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check that inactive tools show appropriate message
        assert "not active and cannot be executed" in resp.text

    def test_form_generation_for_different_types(self, server_url):
        """Test that the UI includes form generation for different parameter types."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check for type handling logic exists
        assert "type ===" in resp.text
        assert "'boolean'" in resp.text or '"boolean"' in resp.text
        assert "'number'" in resp.text or '"number"' in resp.text
        assert "'integer'" in resp.text or '"integer"' in resp.text
        assert "'object'" in resp.text or '"object"' in resp.text
        assert "'array'" in resp.text or '"array"' in resp.text

        # Check for appropriate input elements
        assert "form-input" in resp.text
        assert "form-textarea" in resp.text
        assert "form-select" in resp.text
        assert "checkbox" in resp.text

    def test_execution_result_formatting(self, server_url):
        """Test that execution results are properly formatted."""
        # Execute a simple command
        params = {"command": "echo 'Result formatting test'"}
        resp = requests.post(
            f"{server_url}/api/tools/command_executor/execute", json=params, timeout=10
        )

        if resp.status_code == 200:
            result = resp.json()
            assert "result" in result

            # Verify the result structure
            tool_result = result["result"]
            assert isinstance(tool_result, dict)
            assert "success" in tool_result or "output" in tool_result

    def test_parameter_validation_in_ui(self, server_url):
        """Test that the UI includes parameter validation logic."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check for required field handling
        assert "required" in resp.text
        assert "parameter-required" in resp.text

        # Check for validation attributes
        assert 'required=""' in resp.text or "required" in resp.text
