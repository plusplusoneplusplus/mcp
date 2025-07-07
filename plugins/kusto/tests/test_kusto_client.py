"""
Tests for the KustoClient class in plugins/kusto/tool.py, focused on format_results.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from azure.kusto.data.response import KustoResponseDataSet

from ..tool import KustoClient


@pytest.fixture
def kusto_client():
    """Create a KustoClient instance for testing."""
    return KustoClient()


@pytest.fixture
def mock_kusto_response():
    """Create a mock KustoResponseDataSet for testing."""
    # Create a mock KustoResponseDataSet
    mock_response = MagicMock(spec=KustoResponseDataSet)

    # Create a mock table with columns and rows
    mock_table = MagicMock()
    # Set up __str__ to return a representative string
    mock_table.__str__.return_value = "Table with 3 rows (id, name, value)"

    # Set up the primary results
    mock_response.primary_results = [mock_table]

    return mock_response


@pytest.mark.asyncio
async def test_format_results(kusto_client, mock_kusto_response):
    """Test the format_results method with a KustoResponseDataSet."""
    # Mock DataFrame conversion to return None to force fallback to raw formatting
    with patch.object(kusto_client, '_kusto_response_to_dataframe', return_value=None):
        # Format the response
        formatted = await kusto_client.format_results(mock_kusto_response)

        # Check the structure
        assert formatted["success"] is True
        assert isinstance(formatted["result"], str)

        # Check that the result is the string representation of the primary_results table
        assert formatted["result"] == "Table with 3 rows (id, name, value)"


@pytest.mark.asyncio
async def test_format_results_with_complex_values(kusto_client):
    """Test format_results with complex data types."""
    # Create a mock KustoResponseDataSet
    mock_response = MagicMock(spec=KustoResponseDataSet)

    # Create a mock table with string representation
    mock_table = MagicMock()
    mock_table.__str__.return_value = "Table with complex data types"

    # Set up the primary results
    mock_response.primary_results = [mock_table]

    # Mock DataFrame conversion to return None to force fallback to raw formatting
    with patch.object(kusto_client, '_kusto_response_to_dataframe', return_value=None):
        # Format the results
        formatted = await kusto_client.format_results(mock_response)

        # Check the content
        assert formatted["success"] is True
        assert formatted["result"] == "Table with complex data types"


@pytest.mark.asyncio
async def test_format_results_no_primary_results(kusto_client):
    """Test format_results when there are no primary results."""
    # Create a mock response with no primary results
    mock_response = MagicMock(spec=KustoResponseDataSet)
    mock_response.primary_results = []

    # Format the results
    formatted = await kusto_client.format_results(mock_response)

    # Check the content
    assert formatted["success"] is True
    assert formatted["result"] == "No results found"


@pytest.mark.asyncio
async def test_format_results_error_handling(kusto_client):
    """Test that format_results handles errors during formatting."""
    # Create a mock response that will cause an error when formatting
    mock_response = MagicMock(spec=KustoResponseDataSet)

    # Set up primary_results property to raise an exception when accessed
    type(mock_response).primary_results = PropertyMock(
        side_effect=Exception("Test formatting error")
    )

    # Format the results
    formatted = await kusto_client.format_results(mock_response)

    # Check that error was handled
    assert formatted["success"] is False
    assert "Error formatting results" in formatted["result"]
    assert "Test formatting error" in formatted["result"]


@pytest.mark.asyncio
async def test_execute_query_with_formatting(kusto_client):
    """Test the execute_query method with formatting enabled."""
    # Setup a mock kusto client
    with patch("plugins.kusto.tool.AzureKustoClient") as mock_azure_client:
        # Mock the response
        mock_response = MagicMock(spec=KustoResponseDataSet)
        mock_table = MagicMock()
        mock_table.__str__.return_value = "Table with id and name columns"

        # Set primary_results
        mock_response.primary_results = [mock_table]

        # Configure the mock client instance
        mock_client_instance = mock_azure_client.return_value
        mock_client_instance.execute.return_value = mock_response

        # Patch get_kusto_client to return our mock
        with patch.object(
            kusto_client, "get_kusto_client", return_value=mock_client_instance
        ):
            # Mock DataFrame conversion to return None to force fallback to raw formatting
            with patch.object(kusto_client, '_kusto_response_to_dataframe', return_value=None):
                # Execute the query with formatting (default is True)
                result = await kusto_client.execute_query(
                    database="test_db", query="test_query"
                )

                # Verify result has success and result keys
                assert "success" in result
                assert "result" in result
                assert result["success"] is True

                # Verify formatted result contains expected data
                assert result["result"] == "Table with id and name columns"


@pytest.mark.asyncio
async def test_execute_query_without_formatting(kusto_client):
    """Test the execute_query method with formatting disabled."""
    # Setup a mock kusto client
    with patch("plugins.kusto.tool.AzureKustoClient") as mock_azure_client:
        # Mock the response
        mock_response = MagicMock(spec=KustoResponseDataSet)
        mock_table = MagicMock()
        mock_table.__str__.return_value = "Table with id and name columns"

        mock_response.primary_results = [mock_table]

        # Configure the mock client instance
        mock_client_instance = mock_azure_client.return_value
        mock_client_instance.execute.return_value = mock_response

        # Patch get_kusto_client to return our mock
        with patch.object(
            kusto_client, "get_kusto_client", return_value=mock_client_instance
        ):
            # Execute the query with formatting disabled
            result = await kusto_client.execute_query(
                database="test_db", query="test_query", format_results=False
            )

            # Verify result has the original structure
            assert "success" in result
            assert "raw_response" in result
            assert "primary_results" in result
            assert "tables" in result
            assert result["success"] is True


@pytest.mark.asyncio
async def test_execute_query_client_error(kusto_client):
    """Test execute_query handles client creation errors."""
    # Mock get_kusto_client to raise an exception
    with patch.object(
        kusto_client, "get_kusto_client", side_effect=ValueError("Test client error")
    ):
        # Execute the query
        result = await kusto_client.execute_query(
            database="test_db", query="test_query"
        )

        # Verify error is handled and formatted properly
        assert result["success"] is False
        assert "Failed to create Kusto client" in result["result"]
        assert "Test client error" in result["result"]


@pytest.mark.asyncio
async def test_execute_query_execution_error(kusto_client):
    """Test execute_query handles query execution errors."""
    # Setup a mock kusto client
    with patch("plugins.kusto.tool.AzureKustoClient") as mock_azure_client:
        # Configure the mock client instance to raise an exception
        mock_client_instance = mock_azure_client.return_value
        mock_client_instance.execute.side_effect = Exception("Test execution error")

        # Patch get_kusto_client to return our mock
        with patch.object(
            kusto_client, "get_kusto_client", return_value=mock_client_instance
        ):
            # Execute the query
            result = await kusto_client.execute_query(
                database="test_db", query="test_query"
            )

            # Verify error is handled and formatted properly
            assert result["success"] is False
            assert "Error during query execution" in result["result"]
            assert "Test execution error" in result["result"]


@pytest.mark.asyncio
async def test_execute_tool_respects_format_results(kusto_client):
    """Test that execute_tool respects the format_results parameter."""
    # Mock execute_query to avoid real API calls
    with patch.object(kusto_client, "execute_query", AsyncMock()) as mock_execute_query:
        # Set up the mock to return a specific value
        mock_execute_query.return_value = {
            "success": True,
            "result": "Formatted result string",
        }

        # Call execute_tool with format_results=False
        result = await kusto_client.execute_tool(
            {
                "operation": "execute_query",
                "database": "test_db",
                "query": "test_query",
                "format_results": False,
            }
        )

        # Verify execute_query was called with format_results=False
        mock_execute_query.assert_called_once_with(
            database="test_db",
            query="test_query",
            cluster=None,
            format_results=False,
            formatting_options=None,
            output_limits=None
        )

        # Verify the result is returned
        assert result["success"] is True
        assert result["result"] == "Formatted result string"


@pytest.mark.asyncio
async def test_execute_tool_invalid_operation(kusto_client):
    """Test execute_tool handles invalid operations."""
    # Call execute_tool with an invalid operation
    result = await kusto_client.execute_tool({"operation": "invalid_operation"})

    # Verify error is handled properly
    assert result["success"] is False
    assert "Unknown operation" in result["result"]


@pytest.mark.asyncio
async def test_format_results_with_small_output(kusto_client):
    """Test format_results with output that is under the size limit."""
    # Create a mock response with small output
    mock_response = MagicMock(spec=KustoResponseDataSet)
    mock_table = MagicMock()
    small_output = "This is a small result"
    mock_table.__str__.return_value = small_output

    mock_response.primary_results = [mock_table]

    # Mock DataFrame conversion to return None to force fallback to raw formatting
    with patch.object(kusto_client, '_kusto_response_to_dataframe', return_value=None):
        # Format with default limits (50KB)
        result = await kusto_client.format_results(mock_response)

        # Should return without truncation
        assert result["success"] is True
        assert result["result"] == small_output
        assert "metadata" not in result


@pytest.mark.asyncio
async def test_format_results_with_large_output_truncation(kusto_client):
    """Test format_results with output that exceeds the size limit."""
    # Create a mock response with large output (over 50KB)
    mock_response = MagicMock(spec=KustoResponseDataSet)
    mock_table = MagicMock()
    large_output = "x" * (60 * 1024)  # 60KB of data
    mock_table.__str__.return_value = large_output

    mock_response.primary_results = [mock_table]

    # Mock DataFrame conversion to return None to force fallback to raw formatting
    with patch.object(kusto_client, '_kusto_response_to_dataframe', return_value=None):
        # Format with default limits (50KB)
        result = await kusto_client.format_results(mock_response)

        # Should return with truncation
        assert result["success"] is True
        assert len(result["result"]) < len(large_output)
        assert "metadata" in result
        assert result["metadata"]["truncated"] is True
        assert result["metadata"]["original_size"] == len(large_output)
        assert result["metadata"]["truncated_size"] == len(result["result"])
        assert result["metadata"]["truncation_strategy"] == "smart"
        assert "size_reduction" in result["metadata"]


@pytest.mark.asyncio
async def test_format_results_with_custom_output_limits(kusto_client):
    """Test format_results with custom output limits configuration."""
    # Create a mock response with medium-sized output
    mock_response = MagicMock(spec=KustoResponseDataSet)
    mock_table = MagicMock()
    medium_output = "y" * 2000  # 2KB of data
    mock_table.__str__.return_value = medium_output

    mock_response.primary_results = [mock_table]

    # Set custom limits (1KB max)
    custom_limits = {
        "max_total_length": 1024,  # 1KB
        "truncate_strategy": "end",
        "truncate_message": " [CUSTOM TRUNCATED]"
    }

    # Mock DataFrame conversion to return None to force fallback to raw formatting
    with patch.object(kusto_client, '_kusto_response_to_dataframe', return_value=None):
        # Format with custom limits
        result = await kusto_client.format_results(mock_response, custom_limits)

        # Should return with truncation using custom settings
        assert result["success"] is True
        assert len(result["result"]) <= 1024
        assert "metadata" in result
        assert result["metadata"]["truncated"] is True
        assert result["metadata"]["truncation_strategy"] == "end"
        assert "[CUSTOM TRUNCATED]" in result["result"]


@pytest.mark.asyncio
async def test_format_results_with_preserve_raw_enabled(kusto_client):
    """Test format_results with preserve_raw option enabled."""
    # Create a mock response with large output
    mock_response = MagicMock(spec=KustoResponseDataSet)
    mock_table = MagicMock()
    large_output = "z" * (60 * 1024)  # 60KB of data
    mock_table.__str__.return_value = large_output

    mock_response.primary_results = [mock_table]

    # Enable preserve_raw
    limits = {
        "max_total_length": 10 * 1024,  # 10KB
        "preserve_raw": True
    }

    # Mock DataFrame conversion to return None to force fallback to raw formatting
    with patch.object(kusto_client, '_kusto_response_to_dataframe', return_value=None):
        # Format with preserve_raw enabled
        result = await kusto_client.format_results(mock_response, limits)

        # Should return with both truncated and raw results
        assert result["success"] is True
        assert len(result["result"]) <= 10 * 1024
        assert "metadata" in result
        assert result["metadata"]["truncated"] is True
        assert "raw_result" in result
        assert result["raw_result"] == large_output
        assert len(result["raw_result"]) == 60 * 1024


@pytest.mark.asyncio
async def test_execute_query_with_output_limits(kusto_client):
    """Test execute_query with output_limits parameter."""
    # Setup a mock kusto client
    with patch("plugins.kusto.tool.AzureKustoClient") as mock_azure_client:
        # Mock the response with large output
        mock_response = MagicMock(spec=KustoResponseDataSet)
        mock_table = MagicMock()
        large_output = "Large result data " * 1000  # Create large output
        mock_table.__str__.return_value = large_output

        mock_response.primary_results = [mock_table]

        # Configure the mock client instance
        mock_client_instance = mock_azure_client.return_value
        mock_client_instance.execute.return_value = mock_response

        # Custom output limits
        output_limits = {
            "max_total_length": 500,  # 500 bytes
            "truncate_strategy": "middle",
            "preserve_raw": True
        }

        # Patch get_kusto_client to return our mock
        with patch.object(
            kusto_client, "get_kusto_client", return_value=mock_client_instance
        ):
            # Mock DataFrame conversion to return None to force fallback to raw formatting
            with patch.object(kusto_client, '_kusto_response_to_dataframe', return_value=None):
                # Execute the query with custom output limits
                result = await kusto_client.execute_query(
                    database="test_db",
                    query="test_query",
                    format_results=True,
                    output_limits=output_limits
                )

                # Verify truncation was applied
                assert result["success"] is True
                assert len(result["result"]) <= 500
                assert "metadata" in result
                assert result["metadata"]["truncated"] is True
                assert result["metadata"]["truncation_strategy"] == "middle"
                assert "raw_result" in result
                assert result["raw_result"] == large_output


@pytest.mark.asyncio
async def test_execute_tool_with_output_limits(kusto_client):
    """Test execute_tool with output_limits in arguments."""
    # Mock execute_query to capture the output_limits parameter
    with patch.object(kusto_client, "execute_query", AsyncMock()) as mock_execute_query:
        # Set up the mock to return a truncated result
        mock_execute_query.return_value = {
            "success": True,
            "result": "Truncated result",
            "metadata": {"truncated": True, "original_size": 1000, "truncated_size": 100}
        }

        # Custom output limits
        output_limits = {
            "max_total_length": 100,
            "truncate_strategy": "smart"
        }

        # Call execute_tool with output_limits
        result = await kusto_client.execute_tool(
            {
                "operation": "execute_query",
                "database": "test_db",
                "query": "test_query",
                "output_limits": output_limits
            }
        )

        # Verify execute_query was called with output_limits
        mock_execute_query.assert_called_once_with(
            database="test_db",
            query="test_query",
            cluster=None,
            format_results=True,
            formatting_options=None,
            output_limits=output_limits
        )

        # Verify the result includes truncation metadata
        assert result["success"] is True
        assert result["result"] == "Truncated result"
        assert "metadata" in result
        assert result["metadata"]["truncated"] is True


def test_kusto_response_to_dataframe_success(kusto_client):
    """Test successful conversion of Kusto response to DataFrame."""
    import pandas as pd

    # Create a mock KustoResponseDataSet with proper structure
    mock_response = MagicMock(spec=KustoResponseDataSet)
    mock_primary_result = MagicMock()

    # Mock columns
    mock_col1 = MagicMock()
    mock_col1.column_name = "id"
    mock_col2 = MagicMock()
    mock_col2.column_name = "name"
    mock_col3 = MagicMock()
    mock_col3.column_name = "value"

    mock_primary_result.columns = [mock_col1, mock_col2, mock_col3]

    # Mock row data
    mock_rows = [
        [1, "Alice", 100.5],
        [2, "Bob", 200.0],
        [3, "Charlie", 150.25]
    ]

    # Make the primary result iterable
    mock_primary_result.__iter__ = lambda self: iter(mock_rows)

    mock_response.primary_results = [mock_primary_result]

    # Test DataFrame conversion
    df = kusto_client._kusto_response_to_dataframe(mock_response)

    # Verify DataFrame was created successfully
    assert df is not None
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert list(df.columns) == ["id", "name", "value"]
    assert df.iloc[0]["id"] == 1
    assert df.iloc[0]["name"] == "Alice"
    assert df.iloc[0]["value"] == 100.5


def test_kusto_response_to_dataframe_no_results(kusto_client):
    """Test DataFrame conversion when there are no primary results."""
    mock_response = MagicMock(spec=KustoResponseDataSet)
    mock_response.primary_results = []

    # Test DataFrame conversion
    df = kusto_client._kusto_response_to_dataframe(mock_response)

    # Should return None when no results
    assert df is None


def test_kusto_response_to_dataframe_error_handling(kusto_client):
    """Test DataFrame conversion error handling."""
    mock_response = MagicMock(spec=KustoResponseDataSet)

    # Set up primary_results to raise an exception
    type(mock_response).primary_results = PropertyMock(
        side_effect=Exception("Test DataFrame conversion error")
    )

    # Test DataFrame conversion
    df = kusto_client._kusto_response_to_dataframe(mock_response)

    # Should return None on error
    assert df is None


def test_format_small_dataframe(kusto_client):
    """Test formatting strategy for small DataFrames (≤20 rows)."""
    import pandas as pd

    # Create a small DataFrame
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
        "value": [100.5, 200.0, 150.25]
    })

    # Test small DataFrame formatting
    result = kusto_client._format_small_dataframe(df)

    # Verify the format includes expected elements
    assert "Query Results (3 rows, 3 columns)" in result
    assert "=" * 50 in result
    assert "Alice" in result
    assert "Bob" in result
    assert "Charlie" in result


def test_format_medium_dataframe(kusto_client):
    """Test formatting strategy for medium DataFrames (21-1000 rows)."""
    import pandas as pd
    import numpy as np

    # Create a medium DataFrame (50 rows)
    df = pd.DataFrame({
        "id": range(1, 51),
        "name": [f"User_{i}" for i in range(1, 51)],
        "value": np.random.random(50) * 1000,
        "category": ["A"] * 25 + ["B"] * 25
    })

    # Test medium DataFrame formatting
    result = kusto_client._format_medium_dataframe(df)

    # Verify the format includes expected sections
    assert "Query Results Summary (50 rows, 4 columns)" in result
    assert "Dataset Overview:" in result
    assert "Column Information:" in result
    assert "Sample Data (first 10 rows):" in result
    assert "Numeric Summary:" in result
    assert "Total rows: 50" in result
    assert "Total columns: 4" in result


def test_format_large_dataframe(kusto_client):
    """Test formatting strategy for large DataFrames (>1000 rows)."""
    import pandas as pd
    import numpy as np

    # Create a large DataFrame (2000 rows)
    df = pd.DataFrame({
        "id": range(1, 2001),
        "name": [f"User_{i}" for i in range(1, 2001)],
        "value": np.random.random(2000) * 1000,
        "timestamp": pd.date_range("2024-01-01", periods=2000, freq="H")
    })

    # Test large DataFrame formatting
    result = kusto_client._format_large_dataframe(df)

    # Verify the format includes expected sections
    assert "Large Dataset Summary (2000 rows, 4 columns)" in result
    assert "Dataset Overview:" in result
    assert "Column Information:" in result
    assert "First 5 rows:" in result
    assert "Last 5 rows:" in result
    assert "Numeric Summary" in result
    assert "Total rows: 2,000" in result  # Check comma formatting
    assert "Memory usage:" in result


def test_format_dataframe_smart_strategy_selection(kusto_client):
    """Test that the smart formatting selects the correct strategy based on size."""
    import pandas as pd

    # Test small DataFrame (≤20 rows)
    small_df = pd.DataFrame({"id": range(5), "value": range(5)})
    small_result = kusto_client._format_dataframe_smart(small_df)
    assert "Query Results (5 rows, 2 columns)" in small_result

    # Test medium DataFrame (21-1000 rows)
    medium_df = pd.DataFrame({"id": range(100), "value": range(100)})
    medium_result = kusto_client._format_dataframe_smart(medium_df)
    assert "Query Results Summary (100 rows, 2 columns)" in medium_result

    # Test large DataFrame (>1000 rows)
    large_df = pd.DataFrame({"id": range(1500), "value": range(1500)})
    large_result = kusto_client._format_dataframe_smart(large_df)
    assert "Large Dataset Summary (1500 rows, 2 columns)" in large_result


def test_get_formatting_strategy(kusto_client):
    """Test the formatting strategy selection logic."""
    assert kusto_client._get_formatting_strategy(10) == "small_full_table"
    assert kusto_client._get_formatting_strategy(20) == "small_full_table"
    assert kusto_client._get_formatting_strategy(21) == "medium_summary_sample"
    assert kusto_client._get_formatting_strategy(500) == "medium_summary_sample"
    assert kusto_client._get_formatting_strategy(1000) == "medium_summary_sample"
    assert kusto_client._get_formatting_strategy(1001) == "large_summary_head_tail"
    assert kusto_client._get_formatting_strategy(5000) == "large_summary_head_tail"


@pytest.mark.asyncio
async def test_format_results_with_dataframe_success(kusto_client):
    """Test format_results using successful DataFrame conversion."""
    import pandas as pd

    # Create a mock response that will convert to DataFrame
    mock_response = MagicMock(spec=KustoResponseDataSet)
    mock_primary_result = MagicMock()

    # Mock columns
    mock_col1 = MagicMock()
    mock_col1.column_name = "id"
    mock_col2 = MagicMock()
    mock_col2.column_name = "name"

    mock_primary_result.columns = [mock_col1, mock_col2]

    # Mock row data
    mock_rows = [[1, "Alice"], [2, "Bob"]]
    mock_primary_result.__iter__ = lambda self: iter(mock_rows)

    mock_response.primary_results = [mock_primary_result]

    # Test formatting with DataFrame
    result = await kusto_client.format_results(mock_response)

    # Verify smart DataFrame formatting was used
    assert result["success"] is True
    assert "Query Results (2 rows, 2 columns)" in result["result"]
    assert "metadata" in result
    assert result["metadata"]["formatting"] == "smart_dataframe"
    assert result["metadata"]["rows"] == 2
    assert result["metadata"]["columns"] == 2
    assert result["metadata"]["strategy"] == "small_full_table"


@pytest.mark.asyncio
async def test_format_results_dataframe_fallback_to_raw(kusto_client):
    """Test format_results falls back to raw formatting when DataFrame conversion fails."""
    # Create a mock response that will fail DataFrame conversion
    mock_response = MagicMock(spec=KustoResponseDataSet)
    mock_table = MagicMock()
    mock_table.__str__.return_value = "Raw table output"

    mock_response.primary_results = [mock_table]

    # Mock DataFrame conversion to return None (failure)
    with patch.object(kusto_client, '_kusto_response_to_dataframe', return_value=None):
        result = await kusto_client.format_results(mock_response)

    # Verify fallback to raw formatting
    assert result["success"] is True
    assert result["result"] == "Raw table output"
    # Should not have DataFrame metadata since it fell back to raw


@pytest.mark.asyncio
async def test_format_results_with_formatting_options(kusto_client):
    """Test format_results respects formatting options."""
    import pandas as pd

    # Create a mock response for DataFrame conversion
    mock_response = MagicMock(spec=KustoResponseDataSet)
    mock_primary_result = MagicMock()

    # Mock columns
    mock_col1 = MagicMock()
    mock_col1.column_name = "id"
    mock_col2 = MagicMock()
    mock_col2.column_name = "description"

    mock_primary_result.columns = [mock_col1, mock_col2]

    # Mock row data with long text
    mock_rows = [[1, "This is a very long description that should be truncated"], [2, "Another long description"]]
    mock_primary_result.__iter__ = lambda self: iter(mock_rows)

    mock_response.primary_results = [mock_primary_result]

    # Set formatting options
    kusto_client._current_formatting_options = {
        "max_column_width": 20,
        "show_memory_usage": False
    }

    # Test formatting with options
    result = await kusto_client.format_results(mock_response)

    # Verify formatting was applied
    assert result["success"] is True
    assert result["metadata"]["formatting"] == "smart_dataframe"


@pytest.mark.asyncio
async def test_execute_query_with_formatting_options(kusto_client):
    """Test execute_query with formatting_options parameter."""
    # Mock execute_query implementation for just the formatting options test
    with patch("plugins.kusto.tool.AzureKustoClient") as mock_azure_client:
        # Mock the response
        mock_response = MagicMock(spec=KustoResponseDataSet)
        mock_table = MagicMock()
        mock_table.__str__.return_value = "Table data"

        mock_response.primary_results = [mock_table]

        # Configure the mock client instance
        mock_client_instance = mock_azure_client.return_value
        mock_client_instance.execute.return_value = mock_response

        # Patch get_kusto_client to return our mock
        with patch.object(
            kusto_client, "get_kusto_client", return_value=mock_client_instance
        ):
            # Custom formatting options
            formatting_options = {
                "max_column_width": 30,
                "show_memory_usage": True,
                "force_dataframe": True
            }

            # Execute the query with formatting options
            result = await kusto_client.execute_query(
                database="test_db",
                query="test_query",
                formatting_options=formatting_options
            )

            # Verify formatting options were stored
            assert hasattr(kusto_client, '_current_formatting_options')
            assert kusto_client._current_formatting_options == formatting_options

            # Verify result
            assert result["success"] is True


@pytest.mark.asyncio
async def test_execute_tool_with_formatting_options(kusto_client):
    """Test execute_tool passes formatting_options to execute_query."""
    # Mock execute_query to capture parameters
    with patch.object(kusto_client, "execute_query", AsyncMock()) as mock_execute_query:
        mock_execute_query.return_value = {"success": True, "result": "Formatted output"}

        # Custom formatting options
        formatting_options = {
            "max_column_width": 25,
            "show_memory_usage": False
        }

        # Call execute_tool with formatting options
        result = await kusto_client.execute_tool(
            {
                "operation": "execute_query",
                "database": "test_db",
                "query": "test_query",
                "formatting_options": formatting_options
            }
        )

        # Verify execute_query was called with formatting_options
        mock_execute_query.assert_called_once_with(
            database="test_db",
            query="test_query",
            cluster=None,
            format_results=True,
            formatting_options=formatting_options,
            output_limits=None
        )

        assert result["success"] is True


@pytest.mark.asyncio
async def test_dataframe_formatting_no_string_truncation(kusto_client):
    """Test that DataFrame formatting displays full strings without truncation."""
    import pandas as pd

    # Create a DataFrame with very long strings
    long_string = "This is a very long string that should not be truncated when displayed. " * 10
    test_data = {
        "id": [1, 2, 3],
        "short_text": ["A", "B", "C"],
        "long_text": [long_string, long_string + " Extra", long_string + " More extra content"]
    }

    df = pd.DataFrame(test_data)

    # Test small DataFrame formatting (≤20 rows)
    result = kusto_client._format_small_dataframe(df)

    # Verify that the full long string is present in the output
    assert long_string in result
    assert "..." not in result  # Should not have truncation indicators

    # Test medium DataFrame formatting (21-1000 rows)
    # Create a larger DataFrame
    large_data = {
        "id": list(range(1, 31)),
        "text": [f"Long text entry {i}: {long_string}" for i in range(1, 31)]
    }
    large_df = pd.DataFrame(large_data)

    result = kusto_client._format_medium_dataframe(large_df)

    # Verify that the full long string is present in the sample data
    assert long_string in result

    # Test large DataFrame formatting (>1000 rows)
    # Create an even larger DataFrame
    very_large_data = {
        "id": list(range(1, 1001)),
        "text": [f"Entry {i}: {long_string}" for i in range(1, 1001)]
    }
    very_large_df = pd.DataFrame(very_large_data)

    result = kusto_client._format_large_dataframe(very_large_df)

    # Verify that the full long string is present in head/tail sections
    assert long_string in result


@pytest.mark.asyncio
async def test_dataframe_summarizer_no_string_truncation():
    """Test that DataFrame summarizer displays full strings without truncation."""
    import pandas as pd
    from utils.dataframe_manager.summarizer import DataFrameSummarizer

    # Create a DataFrame with very long strings
    long_string = "This is an extremely long string that historically might have been truncated but should now be displayed in full. " * 5
    test_data = {
        "id": [1, 2, 3],
        "description": [long_string, long_string + " Additional", long_string + " More content"]
    }

    df = pd.DataFrame(test_data)
    summarizer = DataFrameSummarizer()

    # Test table formatting with large size limit
    result = await summarizer.format_for_display(df, max_size_bytes=50000, format_type="table")

    # Verify that the full long string is present
    assert long_string in result
    assert "..." not in result.split('\n')[0]  # First line should not have truncation indicators

    # Test with smaller DataFrame that should fit completely
    small_df = pd.DataFrame({"text": [long_string]})
    result = await summarizer.format_for_display(small_df, max_size_bytes=50000, format_type="table")

    # Verify the full string is displayed
    assert long_string in result
