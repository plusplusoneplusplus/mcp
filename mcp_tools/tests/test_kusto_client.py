"""
Tests for the KustoClient class in mcp_tools/kusto/client.py, focused on format_results.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from azure.kusto.data.response import KustoResponseDataSet

from mcp_tools.kusto.client import KustoClient


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


def test_format_results(kusto_client, mock_kusto_response):
    """Test the format_results method with a KustoResponseDataSet."""
    # Format the response
    formatted = kusto_client.format_results(mock_kusto_response)
    
    # Check the structure
    assert formatted["success"] is True
    assert isinstance(formatted["result"], str)
    
    # Check that the result is the string representation of the primary_results table
    assert formatted["result"] == "Table with 3 rows (id, name, value)"


def test_format_results_with_complex_values(kusto_client):
    """Test format_results with complex data types."""
    # Create a mock KustoResponseDataSet
    mock_response = MagicMock(spec=KustoResponseDataSet)
    
    # Create a mock table with string representation
    mock_table = MagicMock()
    mock_table.__str__.return_value = "Table with complex data types"
    
    # Set up the primary results
    mock_response.primary_results = [mock_table]
    
    # Format the results
    formatted = kusto_client.format_results(mock_response)
    
    # Check the content
    assert formatted["success"] is True
    assert formatted["result"] == "Table with complex data types"


def test_format_results_no_primary_results(kusto_client):
    """Test format_results when there are no primary results."""
    # Create a mock response with no primary results
    mock_response = MagicMock(spec=KustoResponseDataSet)
    mock_response.primary_results = []
    
    # Format the results
    formatted = kusto_client.format_results(mock_response)
    
    # Check the content
    assert formatted["success"] is True
    assert formatted["result"] == "No results found"


def test_format_results_error_handling(kusto_client):
    """Test that format_results handles errors during formatting."""
    # Create a mock response that will cause an error when formatting
    mock_response = MagicMock(spec=KustoResponseDataSet)
    
    # Set up primary_results property to raise an exception when accessed
    type(mock_response).primary_results = PropertyMock(side_effect=Exception("Test formatting error"))
    
    # Format the results
    formatted = kusto_client.format_results(mock_response)
    
    # Check that error was handled
    assert formatted["success"] is False
    assert "Error formatting results" in formatted["result"]
    assert "Test formatting error" in formatted["result"]


@pytest.mark.asyncio
async def test_execute_query_with_formatting(kusto_client):
    """Test the execute_query method with formatting enabled."""
    # Setup a mock kusto client
    with patch('mcp_tools.kusto.client.AzureKustoClient') as mock_azure_client:
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
            assert result["result"] == "Table with id and name columns"


@pytest.mark.asyncio
async def test_execute_query_without_formatting(kusto_client):
    """Test the execute_query method with formatting disabled."""
    # Setup a mock kusto client
    with patch('mcp_tools.kusto.client.AzureKustoClient') as mock_azure_client:
        # Mock the response
        mock_response = MagicMock(spec=KustoResponseDataSet)
        mock_table = MagicMock()
        mock_table.__str__.return_value = "Table with id and name columns"
        
        mock_response.primary_results = [mock_table]
        
        # Configure the mock client instance
        mock_client_instance = mock_azure_client.return_value
        mock_client_instance.execute.return_value = mock_response
        
        # Patch get_kusto_client to return our mock
        with patch.object(kusto_client, 'get_kusto_client', return_value=mock_client_instance):
            # Execute the query with formatting disabled
            result = await kusto_client.execute_query(
                database="test_db",
                query="test_query",
                format_results=False
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
    with patch.object(kusto_client, 'get_kusto_client', side_effect=ValueError("Test client error")):
        # Execute the query
        result = await kusto_client.execute_query(
            database="test_db",
            query="test_query"
        )
        
        # Verify error is handled and formatted properly
        assert result["success"] is False
        assert "Failed to create Kusto client" in result["result"]
        assert "Test client error" in result["result"]


@pytest.mark.asyncio
async def test_execute_query_execution_error(kusto_client):
    """Test execute_query handles query execution errors."""
    # Setup a mock kusto client
    with patch('mcp_tools.kusto.client.AzureKustoClient') as mock_azure_client:
        # Configure the mock client instance to raise an exception
        mock_client_instance = mock_azure_client.return_value
        mock_client_instance.execute.side_effect = Exception("Test execution error")
        
        # Patch get_kusto_client to return our mock
        with patch.object(kusto_client, 'get_kusto_client', return_value=mock_client_instance):
            # Execute the query
            result = await kusto_client.execute_query(
                database="test_db",
                query="test_query"
            )
            
            # Verify error is handled and formatted properly
            assert result["success"] is False
            assert "Error during query execution" in result["result"]
            assert "Test execution error" in result["result"]


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


@pytest.mark.asyncio
async def test_execute_tool_invalid_operation(kusto_client):
    """Test execute_tool handles invalid operations."""
    # Call execute_tool with an invalid operation
    result = await kusto_client.execute_tool({
        "operation": "invalid_operation"
    })
    
    # Verify error is handled properly
    assert result["success"] is False
    assert "Unknown operation" in result["result"] 