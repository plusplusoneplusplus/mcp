import pytest
from unittest.mock import patch, MagicMock

from plugins.logcli.logcli_tool import LogCliTool


@pytest.fixture
def logcli_tool():
    return LogCliTool()


class TestLogCliTool:
    def test_properties(self, logcli_tool):
        assert logcli_tool.name == "logcli"
        assert "Loki" in logcli_tool.description or "logcli" in logcli_tool.description
        schema = logcli_tool.input_schema
        assert schema["type"] == "object"
        assert "operation" in schema["properties"]

    @pytest.mark.asyncio
    @patch("plugins.logcli.logcli_tool.subprocess.run")
    async def test_query_success(self, mock_run, logcli_tool):
        process = MagicMock()
        process.returncode = 0
        process.stdout = "log output"
        mock_run.return_value = process

        result = await logcli_tool.execute_tool(
            {"operation": "query", "query": "{job='app'}"}
        )

        assert result["success"]
        assert "log output" in result["result"]
        mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_missing_params(self, logcli_tool):
        result = await logcli_tool.execute_tool({"operation": "query"})
        assert not result["success"]
        assert "query" in result["error"]

    @pytest.mark.asyncio
    @patch("plugins.logcli.logcli_tool.subprocess.run")
    async def test_labels_success(self, mock_run, logcli_tool):
        process = MagicMock()
        process.returncode = 0
        process.stdout = "label output"
        mock_run.return_value = process

        result = await logcli_tool.execute_tool({"operation": "labels"})

        assert result["success"]
        assert "label output" in result["result"]
        mock_run.assert_called_once()

    @pytest.mark.asyncio
    @patch("plugins.logcli.logcli_tool.subprocess.run")
    async def test_command_failure(self, mock_run, logcli_tool):
        process = MagicMock()
        process.returncode = 1
        process.stderr = "error text"
        mock_run.return_value = process

        result = await logcli_tool.execute_tool(
            {"operation": "query", "query": "{job='app'}"}
        )

        assert not result["success"]
        assert "error text" in result["error"]
        mock_run.assert_called_once()
