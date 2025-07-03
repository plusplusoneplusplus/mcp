"""Tests for DataFrameQueryTool."""

import pytest
import pandas as pd
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Mock the utils import since it's in a different directory
with patch.dict('sys.modules', {
    'utils.dataframe_manager': Mock(),
    'utils.dataframe_manager.get_dataframe_manager': Mock()
}):
    from mcp_tools.dataframe_query.tool import DataFrameQueryTool


class TestDataFrameQueryTool:
    """Test cases for DataFrameQueryTool."""

    @pytest.fixture
    def tool(self):
        """Create a DataFrameQueryTool instance."""
        return DataFrameQueryTool()

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            'id': range(1, 101),
            'name': [f'User_{i}' for i in range(1, 101)],
            'age': [20 + (i % 50) for i in range(100)],
            'status': ['active' if i % 2 == 0 else 'inactive' for i in range(100)],
            'score': [85.5 + (i % 20) for i in range(100)]
        })

    @pytest.fixture
    def mock_result(self, sample_dataframe):
        """Create a mock DataFrameQueryResult."""
        mock_result = Mock()
        mock_result.data = sample_dataframe.head(5)
        mock_result.operation = "head"
        mock_result.parameters = {"n": 5}
        mock_result.execution_time_ms = 10.5
        mock_result.metadata = {
            "original_shape": sample_dataframe.shape,
            "result_shape": sample_dataframe.head(5).shape,
            "rows_returned": 5
        }
        return mock_result

    def test_tool_properties(self, tool):
        """Test basic tool properties."""
        assert tool.name == "dataframe_query"
        assert "Query and manipulate stored DataFrames" in tool.description

        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "dataframe_id" in schema["required"]
        assert "operation" in schema["required"]
        assert set(schema["properties"]["operation"]["enum"]) == {
            "head", "tail", "sample", "filter", "describe", "info"
        }

    def test_input_schema_structure(self, tool):
        """Test the structure of the input schema."""
        schema = tool.input_schema

        # Check main properties
        assert "dataframe_id" in schema["properties"]
        assert "operation" in schema["properties"]
        assert "parameters" in schema["properties"]

        # Check parameters schema
        params = schema["properties"]["parameters"]["properties"]
        assert "n" in params
        assert "frac" in params
        assert "random_state" in params
        assert "conditions" in params
        assert "include" in params

        # Check operation enum
        operations = schema["properties"]["operation"]["enum"]
        expected_operations = ["head", "tail", "sample", "filter", "describe", "info"]
        assert set(operations) == set(expected_operations)

    @pytest.mark.asyncio
    async def test_execute_tool_missing_dataframe_id(self, tool):
        """Test execute_tool with missing dataframe_id."""
        result = await tool.execute_tool({
            "operation": "head"
        })

        assert result["success"] is False
        assert "dataframe_id is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_missing_operation(self, tool):
        """Test execute_tool with missing operation."""
        result = await tool.execute_tool({
            "dataframe_id": "test-123"
        })

        assert result["success"] is False
        assert "operation is required" in result["error"]

    @pytest.mark.asyncio
    @patch('mcp_tools.dataframe_query.tool.sys')
    @patch('mcp_tools.dataframe_query.tool.os')
    async def test_execute_tool_dataframe_not_found(self, mock_os, mock_sys, tool):
        """Test execute_tool when DataFrame is not found."""
        # Mock the import and manager
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=None)

        with patch('mcp_tools.dataframe_query.tool.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "nonexistent-123",
                "operation": "head"
            })

        assert result["success"] is False
        assert "not found or expired" in result["error"]

    @pytest.mark.asyncio
    @patch('mcp_tools.dataframe_query.tool.sys')
    @patch('mcp_tools.dataframe_query.tool.os')
    async def test_execute_tool_successful_head_operation(self, mock_os, mock_sys, tool, sample_dataframe, mock_result):
        """Test successful head operation execution."""
        # Mock the manager and its methods
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)
        mock_manager.query_dataframe = AsyncMock(return_value=mock_result)

        with patch('mcp_tools.dataframe_query.tool.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "head",
                "parameters": {"n": 5}
            })

        assert result["success"] is True
        assert result["dataframe_id"] == "test-123"
        assert result["operation"] == "head"
        assert result["parameters"] == {"n": 5}
        assert result["result_shape"] == (5, 5)  # 5 rows, 5 columns
        assert "data" in result
        assert "columns" in result

    @pytest.mark.asyncio
    @patch('mcp_tools.dataframe_query.tool.sys')
    @patch('mcp_tools.dataframe_query.tool.os')
    async def test_execute_tool_large_result_handling(self, mock_os, mock_sys, tool, sample_dataframe):
        """Test handling of large results (more than 100 rows)."""
        # Create a large result
        large_result = Mock()
        large_result.data = sample_dataframe  # 100 rows > 100 threshold
        large_result.operation = "sample"
        large_result.parameters = {"n": 150}
        large_result.execution_time_ms = 25.0
        large_result.metadata = {"rows_returned": 100}

        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)
        mock_manager.query_dataframe = AsyncMock(return_value=large_result)

        with patch('mcp_tools.dataframe_query.tool.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "sample",
                "parameters": {"n": 150}
            })

        assert result["success"] is True
        assert "Large result with" in result["data"]
        assert "sample_data" in result
        assert "note" in result

    @pytest.mark.asyncio
    @patch('mcp_tools.dataframe_query.tool.sys')
    @patch('mcp_tools.dataframe_query.tool.os')
    async def test_execute_tool_empty_result(self, mock_os, mock_sys, tool, sample_dataframe):
        """Test handling of empty results."""
        empty_result = Mock()
        empty_result.data = pd.DataFrame()  # Empty DataFrame
        empty_result.operation = "filter"
        empty_result.parameters = {"conditions": {"age": {"gt": 200}}}
        empty_result.execution_time_ms = 5.0
        empty_result.metadata = {"rows_returned": 0}

        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)
        mock_manager.query_dataframe = AsyncMock(return_value=empty_result)

        with patch('mcp_tools.dataframe_query.tool.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "filter",
                "parameters": {"conditions": {"age": {"gt": 200}}}
            })

        assert result["success"] is True
        assert result["data"] == "No data returned (empty result)"

    @pytest.mark.asyncio
    @patch('mcp_tools.dataframe_query.tool.sys')
    @patch('mcp_tools.dataframe_query.tool.os')
    async def test_execute_tool_operation_failure(self, mock_os, mock_sys, tool, sample_dataframe):
        """Test handling of operation failures."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)
        mock_manager.query_dataframe = AsyncMock(return_value=None)  # Operation failed

        with patch('mcp_tools.dataframe_query.tool.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "head"
            })

        assert result["success"] is False
        assert "Failed to execute" in result["error"]

    @pytest.mark.asyncio
    @patch('mcp_tools.dataframe_query.tool.sys')
    @patch('mcp_tools.dataframe_query.tool.os')
    async def test_execute_tool_import_error(self, mock_os, mock_sys, tool):
        """Test handling when DataFrame manager import fails."""
        with patch('mcp_tools.dataframe_query.tool.get_dataframe_manager', side_effect=ImportError("Module not found")):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "head"
            })

        assert result["success"] is False
        assert "DataFrame management framework not available" in result["error"]

    @pytest.mark.asyncio
    @patch('mcp_tools.dataframe_query.tool.sys')
    @patch('mcp_tools.dataframe_query.tool.os')
    async def test_execute_tool_value_error(self, mock_os, mock_sys, tool, sample_dataframe):
        """Test handling of ValueError during operation."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)
        mock_manager.query_dataframe = AsyncMock(side_effect=ValueError("Invalid parameters"))

        with patch('mcp_tools.dataframe_query.tool.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "filter",
                "parameters": {"conditions": {"invalid_column": "value"}}
            })

        assert result["success"] is False
        assert "Invalid operation parameters" in result["error"]

    @pytest.mark.asyncio
    @patch('mcp_tools.dataframe_query.tool.sys')
    @patch('mcp_tools.dataframe_query.tool.os')
    async def test_get_available_dataframes(self, mock_os, mock_sys, tool):
        """Test getting list of available DataFrames."""
        # Mock DataFrame metadata
        mock_metadata = Mock()
        mock_metadata.df_id = "test-123"
        mock_metadata.created_at.isoformat.return_value = "2023-01-01T12:00:00"
        mock_metadata.shape = (100, 5)
        mock_metadata.memory_usage = 1024 * 1024  # 1MB
        mock_metadata.dtypes = {"col1": "int64", "col2": "object"}
        mock_metadata.tags = {"source": "test"}
        mock_metadata.expires_at = None

        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.list_stored_dataframes = AsyncMock(return_value=[mock_metadata])

        with patch('mcp_tools.dataframe_query.tool.get_dataframe_manager', return_value=mock_manager):
            result = await tool.get_available_dataframes()

        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["dataframes"]) == 1

        df_info = result["dataframes"][0]
        assert df_info["id"] == "test-123"
        assert df_info["shape"] == (100, 5)
        assert df_info["memory_usage_mb"] == 1.0

    @pytest.mark.asyncio
    @patch('mcp_tools.dataframe_query.tool.sys')
    @patch('mcp_tools.dataframe_query.tool.os')
    async def test_get_available_dataframes_error(self, mock_os, mock_sys, tool):
        """Test error handling in get_available_dataframes."""
        with patch('mcp_tools.dataframe_query.tool.get_dataframe_manager', side_effect=Exception("Connection failed")):
            result = await tool.get_available_dataframes()

        assert result["success"] is False
        assert "Failed to list DataFrames" in result["error"]

    def test_get_operation_examples(self, tool):
        """Test getting operation examples."""
        examples = tool.get_operation_examples()

        expected_operations = ["head", "tail", "sample", "filter", "describe", "info"]
        assert set(examples.keys()) == set(expected_operations)

        # Check structure of each example
        for operation, example_data in examples.items():
            assert "description" in example_data
            assert "example" in example_data
            assert example_data["example"]["operation"] == operation
            assert "dataframe_id" in example_data["example"]

    def test_head_operation_example(self, tool):
        """Test head operation example structure."""
        examples = tool.get_operation_examples()
        head_example = examples["head"]

        assert "Get first n rows" in head_example["description"]
        assert head_example["example"]["operation"] == "head"
        assert "n" in head_example["example"]["parameters"]

    def test_filter_operation_example(self, tool):
        """Test filter operation example structure."""
        examples = tool.get_operation_examples()
        filter_example = examples["filter"]

        assert "Filter DataFrame rows" in filter_example["description"]
        assert filter_example["example"]["operation"] == "filter"
        assert "conditions" in filter_example["example"]["parameters"]

        conditions = filter_example["example"]["parameters"]["conditions"]
        assert isinstance(conditions, dict)
        assert len(conditions) > 0

    @pytest.mark.asyncio
    async def test_all_operations_coverage(self, tool):
        """Test that all supported operations are covered in examples."""
        schema = tool.input_schema
        supported_operations = set(schema["properties"]["operation"]["enum"])

        examples = tool.get_operation_examples()
        example_operations = set(examples.keys())

        assert supported_operations == example_operations

    @pytest.mark.asyncio
    @patch('mcp_tools.dataframe_query.tool.sys')
    @patch('mcp_tools.dataframe_query.tool.os')
    async def test_different_operations(self, mock_os, mock_sys, tool, sample_dataframe):
        """Test different operations with appropriate mock results."""
        operations_to_test = ["head", "tail", "sample", "filter", "describe", "info"]

        for operation in operations_to_test:
            # Create operation-specific mock result
            mock_result = Mock()
            mock_result.data = sample_dataframe.head(5)  # Small result for testing
            mock_result.operation = operation
            mock_result.parameters = {}
            mock_result.execution_time_ms = 10.0
            mock_result.metadata = {"rows_returned": 5}

            mock_manager = AsyncMock()
            mock_manager.start = AsyncMock()
            mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)
            mock_manager.query_dataframe = AsyncMock(return_value=mock_result)

            with patch('mcp_tools.dataframe_query.tool.get_dataframe_manager', return_value=mock_manager):
                result = await tool.execute_tool({
                    "dataframe_id": "test-123",
                    "operation": operation
                })

            assert result["success"] is True, f"Operation {operation} failed"
            assert result["operation"] == operation

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, tool, sample_dataframe):
        """Test concurrent operations on the same tool instance."""
        mock_result = Mock()
        mock_result.data = sample_dataframe.head(5)
        mock_result.operation = "head"
        mock_result.parameters = {"n": 5}
        mock_result.execution_time_ms = 10.0
        mock_result.metadata = {"rows_returned": 5}

        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)
        mock_manager.query_dataframe = AsyncMock(return_value=mock_result)

        with patch('mcp_tools.dataframe_query.tool.sys'), \
             patch('mcp_tools.dataframe_query.tool.os'), \
             patch('mcp_tools.dataframe_query.tool.get_dataframe_manager', return_value=mock_manager):

            # Run multiple operations concurrently
            tasks = [
                tool.execute_tool({
                    "dataframe_id": f"test-{i}",
                    "operation": "head",
                    "parameters": {"n": 5}
                })
                for i in range(5)
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            for result in results:
                assert result["success"] is True

    def test_tool_registration(self):
        """Test that the tool is properly registered."""
        # This test verifies the decorator is applied
        assert hasattr(DataFrameQueryTool, '_mcp_source')
        # The tool should be discoverable by the plugin system

    @pytest.mark.asyncio
    async def test_comprehensive_error_scenarios(self, tool):
        """Test various error scenarios comprehensively."""
        error_scenarios = [
            # Missing dataframe_id
            ({"operation": "head"}, "dataframe_id is required"),
            # Missing operation
            ({"dataframe_id": "test"}, "operation is required"),
            # Empty dataframe_id
            ({"dataframe_id": "", "operation": "head"}, "dataframe_id is required"),
            # Empty operation
            ({"dataframe_id": "test", "operation": ""}, "operation is required"),
        ]

        for args, expected_error in error_scenarios:
            result = await tool.execute_tool(args)
            assert result["success"] is False
            assert expected_error in result["error"]
