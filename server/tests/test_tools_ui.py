"""Integration tests for the tools UI page."""

import requests
import pytest
from bs4 import BeautifulSoup


class TestToolsUI:
    """Test the tools UI page and its functionality."""

    def test_tools_page_loads(self, server_url):
        """Test that the tools page loads successfully."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_tools_page_contains_table(self, server_url):
        """Test that the tools page contains the tools table."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        soup = BeautifulSoup(resp.text, "html.parser")

        # Check for tools table
        table = soup.find("table", class_="tools-table")
        assert table is not None

        # Check for table headers
        headers = table.find_all("th")
        header_texts = [h.text.strip() for h in headers]
        assert "Name" in header_texts
        assert "Description" in header_texts
        assert "Source" in header_texts
        assert "Status" in header_texts

    def test_tools_page_has_execution_form_styles(self, server_url):
        """Test that the tools page includes execution form CSS."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check for execution-related CSS classes
        assert "execution-section" in resp.text
        assert "execute-btn" in resp.text
        assert "execution-result" in resp.text
        assert "form-group" in resp.text

    def test_tools_page_has_execution_javascript(self, server_url):
        """Test that the tools page includes execution JavaScript functions."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check for execution-related JavaScript functions
        assert "executeTool" in resp.text
        assert "createExecutionForm" in resp.text
        assert "generateInputField" in resp.text
        assert "displayExecutionResult" in resp.text

    def test_tools_page_loads_tools_data(self, server_url):
        """Test that the tools page can load tools data via API."""
        # First verify the API works
        resp = requests.get(f"{server_url}/api/tools", timeout=5)
        assert resp.status_code == 200
        tools_data = resp.json()

        # Now check the page loads
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check that the page has the loadTools function
        assert "loadTools" in resp.text
        assert "/api/tools" in resp.text

    def test_tools_page_has_tool_count_element(self, server_url):
        """Test that the tools page has an element to display tool count."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        soup = BeautifulSoup(resp.text, "html.parser")

        # Check for tool count element
        tool_count_elem = soup.find(id="tool-count")
        assert tool_count_elem is not None

    def test_tools_page_has_form_input_types(self, server_url):
        """Test that the page includes logic for different input types."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check for different input type handling
        assert "form-input" in resp.text
        assert "form-textarea" in resp.text
        assert "form-select" in resp.text
        assert "checkbox" in resp.text

    def test_execution_form_parameter_collection(self, server_url):
        """Test that the execution form includes parameter collection logic."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check for parameter type handling in JavaScript
        assert "type === 'boolean'" in resp.text
        assert "type === 'number'" in resp.text
        assert "type === 'integer'" in resp.text
        assert "type === 'object'" in resp.text
        assert "type === 'array'" in resp.text
        assert "JSON.parse" in resp.text

    def test_execution_result_display(self, server_url):
        """Test that the page includes result display functionality."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check for result display elements and functions
        assert "execution-result" in resp.text
        assert "result-title" in resp.text
        assert "result-content" in resp.text
        assert "displayExecutionResult" in resp.text
        assert "escapeHtml" in resp.text

    def test_execution_error_handling(self, server_url):
        """Test that the page includes error handling for execution."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check for error handling
        assert "catch (error)" in resp.text
        assert "execution-result error" in resp.text
        assert "Execution Error" in resp.text

    def test_tools_page_has_active_tool_check(self, server_url):
        """Test that the page checks if tools are active before allowing execution."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check for active tool validation
        assert "tool.active" in resp.text
        assert "not active and cannot be executed" in resp.text

    def test_execution_button_states(self, server_url):
        """Test that the page handles button states during execution."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        # Check for button state management
        assert "executeBtn.disabled = true" in resp.text
        assert "executeBtn.disabled = false" in resp.text
        assert "Executing..." in resp.text
        assert "Execute Tool" in resp.text

    def test_tools_page_navigation_link(self, server_url):
        """Test that the tools page is accessible from navigation."""
        resp = requests.get(f"{server_url}/tools", timeout=5)
        assert resp.status_code == 200

        soup = BeautifulSoup(resp.text, "html.parser")

        # Check for navigation link
        nav_links = soup.find_all("a", class_="nav-link")
        tools_link = None
        for link in nav_links:
            if "tools" in link.get("href", "").lower():
                tools_link = link
                break

        assert tools_link is not None
