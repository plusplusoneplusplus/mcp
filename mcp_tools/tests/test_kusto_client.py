"""
Tests for the KustoClient class in mcp_tools/kusto/client.py, focused on format_results.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from mcp_tools.kusto.client import KustoClient


@pytest.fixture
def kusto_client():
    """Create a KustoClient instance for testing."""
    return KustoClient()


def test_format_results_success(kusto_client):
    """Test the format_results method with successful results."""
    # Create a mock table with columns and rows
    mock_table = MagicMock()
    mock_table.columns_name = ["id", "name", "value"]
    mock_table.columns_type = ["int", "string", "real"]
    mock_table.rows = [
        [1, "test1", 10.5],
        [2, "test2", 20.5],
        [3, "test3", 30.5]
    ]
    
    # Create a mock query result
    input_result = {
        "success": True,
        "tables": [mock_table]
    }
    
    # Format the results
    formatted = kusto_client.format_results(input_result)
    
    # Check the structure
    assert formatted["success"] is True
    assert isinstance(formatted["result"], str)
    
    # Check the formatted content
    result_str = formatted["result"]
    assert "Table 1:" in result_str
    assert "id (int) | name (string) | value (real)" in result_str
    assert "1 | test1 | 10.5" in result_str
    assert "2 | test2 | 20.5" in result_str
    assert "3 | test3 | 30.5" in result_str
    assert "Summary: 1 table(s), 3 total row(s)" in result_str


def test_format_results_with_null_and_complex_values(kusto_client):
    """Test format_results with NULL and complex data types."""
    # Create a mock table with columns and rows that include NULL and JSON values
    mock_table = MagicMock()
    mock_table.columns_name = ["id", "data", "is_active"]
    mock_table.columns_type = ["long", "dynamic", "bool"]
    mock_table.rows = [
        [1, {"key": "value"}, True],
        [2, {"array": [1, 2, 3]}, False],
        [3, None, None]
    ]
    
    # Create a mock query result
    input_result = {
        "success": True,
        "tables": [mock_table]
    }
    
    # Format the results
    formatted = kusto_client.format_results(input_result)
    
    # Check the content
    result_str = formatted["result"]
    assert 'id (long) | data (dynamic) | is_active (bool)' in result_str
    assert '1 | {"key": "value"} | True' in result_str
    assert '2 | {"array": [1, 2, 3]} | False' in result_str
    assert '3 | NULL | NULL' in result_str


def test_format_results_error(kusto_client):
    """Test the format_results method with an error result."""
    input_result = {
        "success": False,
        "error": "Test error message"
    }
    
    # Format the results
    formatted = kusto_client.format_results(input_result)
    
    # Check the structure
    assert formatted["success"] is False
    assert formatted["result"] == "Error: Test error message"


@pytest.mark.asyncio
async def test_execute_query_with_formatting(kusto_client):
    """Test the execute_query method with formatting enabled."""
    # Setup a mock kusto client
    with patch('mcp_tools.kusto.client.AzureKustoClient') as mock_azure_client:
        # Mock the response
        mock_response = MagicMock()
        mock_table = MagicMock()
        mock_table.columns_name = ["id", "name"]
        mock_table.columns_type = ["int", "string"]
        mock_table.rows = [[1, "test"]]
        
        mock_response.__iter__.return_value = [mock_table]
        mock_response.primary_results = [mock_table]
        
        # Configure the mock client instance
        mock_client_instance = mock_azure_client.return_value
        mock_client_instance.execute.return_value = mock_response
        
        # Patch get_kusto_client to return our mock
        with patch.object(kusto_client, 'get_kusto_client', return_value=mock_client_instance):
            # Execute the query with formatting (default is True)
            result = await kusto_client.execute_query(
                database="test_db",
                query="test_query"
            )
            
            # Verify result has success and result keys
            assert "success" in result
            assert "result" in result
            assert result["success"] is True
            
            # Verify formatted result contains expected data
            assert "Table 1:" in result["result"]
            assert "id (int) | name (string)" in result["result"]
            assert "1 | test" in result["result"]


@pytest.mark.asyncio
async def test_execute_tool_always_formats(kusto_client):
    """Test that execute_tool always returns formatted results."""
    # Mock execute_query to avoid real API calls
    with patch.object(kusto_client, 'execute_query', AsyncMock()) as mock_execute_query:
        # Set up the mock to return a specific value
        mock_execute_query.return_value = {
            "success": True,
            "result": "Formatted result string"
        }
        
        # Call execute_tool with format_results=False
        # This should be ignored as execute_tool always uses format_results=True
        result = await kusto_client.execute_tool({
            "operation": "execute_query",
            "database": "test_db",
            "query": "test_query",
            "format_results": False
        })
        
        # Verify execute_query was called with format_results=True
        mock_execute_query.assert_called_once_with(
            database="test_db",
            query="test_query",
            cluster=None,
            format_results=True
        )
        
        # Verify the result is the formatted one
        assert result["success"] is True
        assert result["result"] == "Formatted result string" 