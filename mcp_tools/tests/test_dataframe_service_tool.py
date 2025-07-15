"""Tests for DataFrameServiceTool with comprehensive load_data coverage."""

import pytest
import pandas as pd
import asyncio
import tempfile
import os
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any
import uuid

# Mock the utils import since it's in a different directory
with patch.dict('sys.modules', {
    'utils.dataframe_manager': Mock(),
    'utils.dataframe_manager.get_dataframe_manager': Mock()
}):
    from mcp_tools.dataframe_service.tool import DataFrameServiceTool


class TestDataFrameServiceTool:
    """Test cases for DataFrameServiceTool."""

    @pytest.fixture
    def tool(self):
        """Create a DataFrameServiceTool instance."""
        return DataFrameServiceTool()

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            'id': range(1, 101),
            'name': [f'User_{i}' for i in range(1, 101)],
            'age': range(20, 120),
            'status': ['active' if i % 2 == 0 else 'inactive' for i in range(1, 101)],
            'score': [85.5 + i * 0.5 for i in range(100)]
        })

    @pytest.fixture
    def mock_query_result(self, sample_dataframe):
        """Create a mock query result."""
        mock_result = Mock()
        mock_result.data = sample_dataframe.head(5)
        mock_result.operation = "head"
        mock_result.parameters = {"n": 5}
        mock_result.execution_time_ms = 15.0
        mock_result.metadata = {"rows_returned": 5}
        return mock_result

    @pytest.fixture
    def mock_metadata(self):
        """Create mock DataFrame metadata."""
        mock_metadata = Mock()
        mock_metadata.created_at.isoformat.return_value = "2023-01-01T12:00:00"
        mock_metadata.expires_at = None
        return mock_metadata

    def test_tool_properties(self, tool):
        """Test tool basic properties."""
        assert tool.name == "data_frame_service"
        assert "Data Frame Service" in tool.description
        assert "load_data" in tool.description

    def test_input_schema_structure(self, tool):
        """Test the input schema structure."""
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "operation" in schema["required"]
        assert schema["required"] == ["operation"]

        # Check operation enum values
        operations = schema["properties"]["operation"]["enum"]
        expected_operations = ["load_data", "execute"]
        assert operations == expected_operations

        # Check load_data specific parameters
        params = schema["properties"]["parameters"]["properties"]
        assert "source" in params
        assert "file_type" in params
        assert "custom_id" in params
        assert "csv_options" in params
        
        # Check execute specific parameters
        assert "pandas_expression" in params

    # Tests for load_data operation
    @pytest.mark.asyncio
    async def test_load_data_missing_source(self, tool):
        """Test load_data with missing source parameter."""
        result = await tool.execute_tool({
            "operation": "load_data",
            "parameters": {}
        })

        assert result["success"] is False
        assert "source parameter is required" in result["error"]

    @pytest.mark.asyncio
    async def test_load_data_csv_file_success(self, tool, sample_dataframe, mock_metadata):
        """Test successful CSV file loading."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            sample_dataframe.to_csv(f.name, index=False)
            temp_file_path = f.name

        try:
            # Mock the manager
            mock_manager = AsyncMock()
            mock_manager.start = AsyncMock()
            mock_manager.store_dataframe = AsyncMock(return_value=mock_metadata)

            with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
                result = await tool.execute_tool({
                    "operation": "load_data",
                    "parameters": {
                        "source": temp_file_path,
                        "custom_id": "test-csv-123"
                    }
                })

            assert result["success"] is True
            assert result["dataframe_id"] == "test-csv-123"
            assert result["file_type"] == "csv"
            assert result["shape"] == (100, 5)
            assert "columns" in result
            assert "sample_data" in result
            assert "memory_usage_mb" in result

        finally:
            # Clean up the temp file
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_load_data_json_file_success(self, tool, sample_dataframe, mock_metadata):
        """Test successful JSON file loading."""
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            sample_dataframe.to_json(f.name, orient='records')
            temp_file_path = f.name

        try:
            # Mock the manager
            mock_manager = AsyncMock()
            mock_manager.start = AsyncMock()
            mock_manager.store_dataframe = AsyncMock(return_value=mock_metadata)

            with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
                result = await tool.execute_tool({
                    "operation": "load_data",
                    "parameters": {
                        "source": temp_file_path
                    }
                })

            assert result["success"] is True
            assert result["file_type"] == "json"
            assert result["shape"] == (100, 5)
            assert result["dataframe_id"].startswith("dataframe-")

        finally:
            # Clean up the temp file
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_load_data_file_not_found(self, tool):
        """Test load_data with non-existent file."""
        result = await tool.execute_tool({
            "operation": "load_data",
            "parameters": {
                "source": "/nonexistent/path/file.csv"
            }
        })

        assert result["success"] is False
        assert "Failed to load data" in result["error"]

    @pytest.mark.asyncio
    async def test_load_data_auto_detect_file_types(self, tool, mock_metadata):
        """Test auto-detection of file types."""
        test_cases = [
            ("test.csv", "csv"),
            ("test.json", "json"),
            ("test.parquet", "parquet"),
            ("test.xlsx", "excel"),
            ("test.xls", "excel"),
            ("test.unknown", "csv"),  # Default to CSV
        ]

        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.store_dataframe = AsyncMock(return_value=mock_metadata)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            for filename, expected_type in test_cases:
                with patch.object(tool, '_load_from_file', AsyncMock(return_value=pd.DataFrame({'test': [1, 2, 3]}))):
                    result = await tool.execute_tool({
                        "operation": "load_data",
                        "parameters": {
                            "source": filename
                        }
                    })

                    assert result["success"] is True
                    assert result["file_type"] == expected_type

    @pytest.mark.asyncio
    async def test_load_data_custom_file_type(self, tool, mock_metadata):
        """Test explicit file type specification."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.store_dataframe = AsyncMock(return_value=mock_metadata)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            with patch.object(tool, '_load_from_file', AsyncMock(return_value=pd.DataFrame({'test': [1, 2, 3]}))):
                result = await tool.execute_tool({
                    "operation": "load_data",
                    "parameters": {
                        "source": "test.unknown",
                        "file_type": "json"
                    }
                })

                assert result["success"] is True
                assert result["file_type"] == "json"

    @pytest.mark.asyncio
    async def test_load_data_csv_with_options(self, tool, mock_metadata):
        """Test CSV loading with custom options."""
        # Create a temporary CSV file with custom separator
        test_data = "id;name;age\n1;John;25\n2;Jane;30"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(test_data)
            temp_file_path = f.name

        try:
            mock_manager = AsyncMock()
            mock_manager.start = AsyncMock()
            mock_manager.store_dataframe = AsyncMock(return_value=mock_metadata)

            with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
                result = await tool.execute_tool({
                    "operation": "load_data",
                    "parameters": {
                        "source": temp_file_path,
                        "csv_options": {"sep": ";"}
                    }
                })

                assert result["success"] is True
                assert result["shape"] == (2, 3)

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_load_data_url_success(self, tool, mock_metadata):
        """Test successful URL loading."""
        test_df = pd.DataFrame({
            'id': [1, 2],
            'name': ['John', 'Jane'],
            'age': [25, 30]
        })

        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.store_dataframe = AsyncMock(return_value=mock_metadata)

        with patch.object(tool, '_load_from_url', AsyncMock(return_value=test_df)):
            with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
                result = await tool.execute_tool({
                    "operation": "load_data",
                    "parameters": {
                        "source": "https://example.com/data.csv"
                    }
                })

                assert result["success"] is True
                assert result["file_type"] == "csv"
                assert result["shape"] == (2, 3)

    @pytest.mark.asyncio
    async def test_load_data_url_failure(self, tool):
        """Test URL loading failure."""
        with patch.object(tool, '_load_from_url', AsyncMock(side_effect=Exception("Connection failed"))):
            result = await tool.execute_tool({
                "operation": "load_data",
                "parameters": {
                    "source": "https://example.com/data.csv"
                }
            })

            assert result["success"] is False
            assert "Failed to load data" in result["error"]

    @pytest.mark.asyncio
    async def test_load_data_storage_failure(self, tool):
        """Test failure when storing DataFrame in manager."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name\n1,John\n2,Jane")
            temp_file_path = f.name

        try:
            mock_manager = AsyncMock()
            mock_manager.start = AsyncMock()
            mock_manager.store_dataframe = AsyncMock(side_effect=Exception("Storage failed"))

            with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
                result = await tool.execute_tool({
                    "operation": "load_data",
                    "parameters": {
                        "source": temp_file_path
                    }
                })

                assert result["success"] is False
                assert "Failed to store DataFrame" in result["error"]

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_load_data_manager_import_error(self, tool):
        """Test failure when DataFrame manager import fails."""
        with patch.object(tool, '_load_from_file', AsyncMock(return_value=pd.DataFrame({'test': [1, 2, 3]}))):
            with patch('utils.dataframe_manager.get_dataframe_manager', side_effect=ImportError("Module not found")):
                result = await tool.execute_tool({
                    "operation": "load_data",
                    "parameters": {
                        "source": "test.csv"
                    }
                })

                assert result["success"] is False
                assert "Failed to store DataFrame" in result["error"]

    @pytest.mark.asyncio
    async def test_load_data_id_generation(self, tool, mock_metadata):
        """Test automatic ID generation."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.store_dataframe = AsyncMock(return_value=mock_metadata)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            with patch.object(tool, '_load_from_file', AsyncMock(return_value=pd.DataFrame({'test': [1, 2, 3]}))):
                result = await tool.execute_tool({
                    "operation": "load_data",
                    "parameters": {
                        "source": "test.csv"
                    }
                })

                assert result["success"] is True
                assert result["dataframe_id"].startswith("dataframe-")
                assert len(result["dataframe_id"]) == len("dataframe-") + 8  # 8 hex chars

    # Note: Direct URL testing is covered through the main load_data operation tests above
    # These provide more realistic integration testing of the URL loading functionality

    # Tests for _load_from_file method
    @pytest.mark.asyncio
    async def test_load_from_file_csv(self, tool, sample_dataframe):
        """Test _load_from_file with CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            sample_dataframe.to_csv(f.name, index=False)
            temp_file_path = f.name

        try:
            df = await tool._load_from_file(temp_file_path, "csv", {})
            assert len(df) == 100
            assert list(df.columns) == list(sample_dataframe.columns)
        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_load_from_file_nonexistent(self, tool):
        """Test _load_from_file with non-existent file."""
        with pytest.raises(Exception, match="File not found"):
            await tool._load_from_file("/nonexistent/file.csv", "csv", {})

    @pytest.mark.asyncio
    async def test_load_from_file_unsupported_type(self, tool):
        """Test _load_from_file with unsupported file type."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test data")
            temp_file_path = f.name

        try:
            with pytest.raises(Exception, match="Unsupported file type"):
                await tool._load_from_file(temp_file_path, "xyz", {})
        finally:
            os.unlink(temp_file_path)

    # Tests for execute operation
    @pytest.mark.asyncio
    async def test_execute_tool_missing_operation(self, tool):
        """Test execute_tool with missing operation."""
        result = await tool.execute_tool({})

        assert result["success"] is False
        assert "operation is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_missing_dataframe_id(self, tool):
        """Test execute operation with missing dataframe_id."""
        result = await tool.execute_tool({
            "operation": "execute"
        })

        assert result["success"] is False
        assert "dataframe_id is required for execute operation" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_missing_pandas_expression(self, tool):
        """Test execute operation with missing pandas_expression."""
        result = await tool.execute_tool({
            "operation": "execute",
            "dataframe_id": "test-123"
        })

        assert result["success"] is False
        assert "pandas_expression parameter is required" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_dataframe_not_found(self, tool):
        """Test execute operation when DataFrame is not found."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=None)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "nonexistent-123",
                "operation": "execute",
                "parameters": {"pandas_expression": "df.head()"}
            })

        assert result["success"] is False
        assert "not found or expired" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_successful_head_operation(self, tool, sample_dataframe):
        """Test successful head operation using pandas expression."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "execute",
                "parameters": {"pandas_expression": "df.head(5)"}
            })

        assert result["success"] is True
        assert result["dataframe_id"] == "test-123"
        assert result["expression"] == "df.head(5)"
        assert result["result_shape"] == (5, 5)
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_execute_query_operation(self, tool, sample_dataframe):
        """Test query operation using pandas expression."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "execute",
                "parameters": {"pandas_expression": "df.query('age > 50')"}
            })

        assert result["success"] is True
        assert result["dataframe_id"] == "test-123"
        assert result["expression"] == "df.query('age > 50')"
        # Should return rows where age > 50 (ages 51-119, so 69 rows)
        assert result["result_shape"] == (69, 5)

    @pytest.mark.asyncio
    async def test_execute_describe_operation(self, tool, sample_dataframe):
        """Test describe operation using pandas expression."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "execute",
                "parameters": {"pandas_expression": "df.describe()"}
            })

        assert result["success"] is True
        assert result["dataframe_id"] == "test-123"
        assert result["expression"] == "df.describe()"
        # describe() returns 8 rows (count, mean, std, min, 25%, 50%, 75%, max) for numeric columns
        assert result["result_shape"][0] == 8

    @pytest.mark.asyncio
    async def test_execute_series_result(self, tool, sample_dataframe):
        """Test handling of Series results."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "execute",
                "parameters": {"pandas_expression": "df['age']"}
            })

        assert result["success"] is True
        assert result["dataframe_id"] == "test-123"
        assert result["expression"] == "df['age']"
        # Series converted to DataFrame should have 100 rows, 1 column
        assert result["result_shape"] == (100, 1)

    @pytest.mark.asyncio
    async def test_execute_scalar_result(self, tool, sample_dataframe):
        """Test handling of scalar results."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "execute",
                "parameters": {"pandas_expression": "len(df)"}
            })

        # Debug: print the result if it fails
        if not result["success"]:
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        assert result["success"] is True
        assert result["dataframe_id"] == "test-123"
        assert result["expression"] == "len(df)"
        # Scalar result converted to DataFrame should have 1 row, 1 column
        assert result["result_shape"] == (1, 1)
        assert result["data"] == [{"result": 100}]

    @pytest.mark.asyncio
    async def test_execute_large_result_handling(self, tool, sample_dataframe):
        """Test handling of large results."""
        # Create a larger DataFrame for testing
        large_df = pd.concat([sample_dataframe] * 2)  # 200 rows > 100 threshold
        
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=large_df)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "execute",
                "parameters": {"pandas_expression": "df"}
            })

        assert result["success"] is True
        assert "Large result with" in result["data"]
        assert "sample_data" in result
        assert result["result_shape"] == (200, 5)

    @pytest.mark.asyncio
    async def test_execute_empty_result(self, tool, sample_dataframe):
        """Test handling of empty results."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "execute",
                "parameters": {"pandas_expression": "df.query('age > 200')"}
            })

        assert result["success"] is True
        assert result["data"] == "No data returned (empty result)"

    @pytest.mark.asyncio
    async def test_execute_syntax_error(self, tool, sample_dataframe):
        """Test handling of syntax errors in pandas expressions."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "execute",
                "parameters": {"pandas_expression": "df.head("}  # Invalid syntax
            })

        assert result["success"] is False
        assert "Invalid pandas expression syntax" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_runtime_error(self, tool, sample_dataframe):
        """Test handling of runtime errors in pandas expressions."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.get_dataframe = AsyncMock(return_value=sample_dataframe)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "execute",
                "parameters": {"pandas_expression": "df['nonexistent_column']"}
            })

        assert result["success"] is False
        assert "Error executing pandas expression" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_import_error(self, tool):
        """Test handling when DataFrame manager import fails."""
        with patch('utils.dataframe_manager.get_dataframe_manager', side_effect=ImportError("Module not found")):
            result = await tool.execute_tool({
                "dataframe_id": "test-123",
                "operation": "execute",
                "parameters": {"pandas_expression": "df.head()"}
            })

        assert result["success"] is False
        assert "DataFrame management framework not available" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_unknown_operation(self, tool):
        """Test handling of unknown operations."""
        result = await tool.execute_tool({
            "operation": "unknown_operation"
        })

        assert result["success"] is False
        assert "Unknown operation: unknown_operation" in result["error"]

    def test_tool_registration(self):
        """Test that the tool is properly registered."""
        assert hasattr(DataFrameServiceTool, '_mcp_source')

    @pytest.mark.asyncio
    async def test_comprehensive_load_data_scenarios(self, tool, mock_metadata):
        """Test various load_data error scenarios."""
        error_scenarios = [
            # Missing source
            ({"operation": "load_data", "parameters": {}}, "source parameter is required"),
            # Empty source
            ({"operation": "load_data", "parameters": {"source": ""}}, "source parameter is required"),
        ]

        for args, expected_error in error_scenarios:
            result = await tool.execute_tool(args)
            assert result["success"] is False
            assert expected_error in result["error"]

    @pytest.mark.asyncio
    async def test_load_data_concurrent_operations(self, tool, mock_metadata):
        """Test concurrent load_data operations."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.store_dataframe = AsyncMock(return_value=mock_metadata)

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            with patch.object(tool, '_load_from_file', AsyncMock(return_value=pd.DataFrame({'test': [1, 2, 3]}))):
                # Run multiple load operations concurrently
                tasks = [
                    tool.execute_tool({
                        "operation": "load_data",
                        "parameters": {
                            "source": f"test_{i}.csv",
                            "custom_id": f"test-{i}"
                        }
                    })
                    for i in range(5)
                ]

                results = await asyncio.gather(*tasks)

                # All should succeed
                for i, result in enumerate(results):
                    assert result["success"] is True
                    assert result["dataframe_id"] == f"test-{i}"

    @pytest.mark.asyncio
    async def test_load_data_parquet_support(self, tool, mock_metadata):
        """Test parquet file type detection and loading."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.store_dataframe = AsyncMock(return_value=mock_metadata)

        test_df = pd.DataFrame({'id': [1, 2], 'value': [10, 20]})

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            with patch.object(tool, '_load_from_file', AsyncMock(return_value=test_df)):
                result = await tool.execute_tool({
                    "operation": "load_data",
                    "parameters": {
                        "source": "data.parquet"
                    }
                })

                assert result["success"] is True
                assert result["file_type"] == "parquet"

    @pytest.mark.asyncio
    async def test_load_data_excel_support(self, tool, mock_metadata):
        """Test excel file type detection and loading."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.store_dataframe = AsyncMock(return_value=mock_metadata)

        test_df = pd.DataFrame({'id': [1, 2], 'value': [10, 20]})

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            with patch.object(tool, '_load_from_file', AsyncMock(return_value=test_df)):
                for ext in ['.xlsx', '.xls']:
                    result = await tool.execute_tool({
                        "operation": "load_data",
                        "parameters": {
                            "source": f"data{ext}"
                        }
                    })

                    assert result["success"] is True
                    assert result["file_type"] == "excel"

    @pytest.mark.asyncio
    async def test_load_data_metadata_fields(self, tool, mock_metadata):
        """Test that all expected metadata fields are included in response."""
        mock_manager = AsyncMock()
        mock_manager.start = AsyncMock()
        mock_manager.store_dataframe = AsyncMock(return_value=mock_metadata)

        test_df = pd.DataFrame({'id': [1, 2, 3], 'name': ['A', 'B', 'C'], 'value': [10, 20, 30]})

        with patch('utils.dataframe_manager.get_dataframe_manager', return_value=mock_manager):
            with patch.object(tool, '_load_from_file', AsyncMock(return_value=test_df)):
                result = await tool.execute_tool({
                    "operation": "load_data",
                    "parameters": {
                        "source": "test.csv",
                        "custom_id": "metadata-test"
                    }
                })

                assert result["success"] is True
                # Check all expected fields are present
                expected_fields = [
                    "dataframe_id", "source", "file_type", "shape", "columns",
                    "dtypes", "memory_usage_mb", "sample_data", "created_at"
                ]
                for field in expected_fields:
                    assert field in result, f"Missing field: {field}"

                # Check field contents
                assert result["dataframe_id"] == "metadata-test"
                assert result["source"] == "test.csv"
                assert result["shape"] == (3, 3)
                assert len(result["columns"]) == 3
                assert len(result["dtypes"]) == 3
                assert isinstance(result["memory_usage_mb"], float)
                assert len(result["sample_data"]) == 3  # All 3 rows since <100
