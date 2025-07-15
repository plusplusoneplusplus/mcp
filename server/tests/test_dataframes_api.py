#!/usr/bin/env python3
"""Test suite for DataFrame API endpoints."""

import asyncio
import sys
import os
import pandas as pd
import pytest

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from utils.dataframe_manager import get_dataframe_manager
from server.api.dataframes import (
    api_list_dataframes,
    api_get_dataframe_detail,
    api_get_storage_stats,
    api_get_dataframe_data,
    api_get_dataframe_summary,
    api_execute_dataframe_operation
)


# Mock request class for testing
class MockRequest:
    def __init__(self, query_params=None, path_params=None):
        self.query_params = query_params or {}
        self.path_params = path_params or {}


class MockRequestWithBody(MockRequest):
    def __init__(self, path_params=None, json_body=None):
        super().__init__(path_params=path_params)
        self._json_body = json_body

    async def json(self):
        return self._json_body


class TestDataFramesAPI:
    """Test class for DataFrame API endpoints."""

    @pytest.fixture
    async def test_dataframe(self):
        """Create a test DataFrame for testing."""
        manager = get_dataframe_manager()
        await manager.start()

        # Create test DataFrame
        test_df = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie', 'Diana'],
            'age': [25, 30, 35, 28],
            'city': ['New York', 'London', 'Paris', 'Tokyo']
        })

        # Store test DataFrame
        df_id = await manager.store_dataframe(
            df=test_df,
            tags={"test": True, "source": "test_script"}
        )

        yield df_id, manager

        # Cleanup
        await manager.delete_dataframe(df_id)

    async def test_list_dataframes(self, test_dataframe):
        """Test listing DataFrames endpoint."""
        df_id, manager = test_dataframe

        request = MockRequest()
        response = await api_list_dataframes(request)

        assert response.status_code == 200
        # Verify response has content
        data = response.body.decode()
        assert len(data) > 0

    async def test_get_dataframe_detail(self, test_dataframe):
        """Test getting DataFrame detail endpoint."""
        df_id, manager = test_dataframe

        request = MockRequest(path_params={"df_id": df_id})
        response = await api_get_dataframe_detail(request)

        assert response.status_code == 200

    async def test_get_storage_stats(self, test_dataframe):
        """Test getting storage statistics endpoint."""
        df_id, manager = test_dataframe

        request = MockRequest()
        response = await api_get_storage_stats(request)

        assert response.status_code == 200

    async def test_get_dataframe_data(self, test_dataframe):
        """Test getting DataFrame data endpoint."""
        df_id, manager = test_dataframe

        request = MockRequest(path_params={"df_id": df_id})
        response = await api_get_dataframe_data(request)

        assert response.status_code == 200

    async def test_dataframe_data_pagination(self, test_dataframe):
        """Test DataFrame data pagination."""
        df_id, manager = test_dataframe

        request = MockRequest(
            path_params={"df_id": df_id},
            query_params={"page": "1", "page_size": "2"}
        )
        response = await api_get_dataframe_data(request)

        assert response.status_code == 200

    async def test_dataframe_column_filtering(self, test_dataframe):
        """Test DataFrame column filtering."""
        df_id, manager = test_dataframe

        request = MockRequest(
            path_params={"df_id": df_id},
            query_params={"columns": "name,age"}
        )
        response = await api_get_dataframe_data(request)

        assert response.status_code == 200

    async def test_get_dataframe_summary(self, test_dataframe):
        """Test getting DataFrame summary endpoint."""
        df_id, manager = test_dataframe

        request = MockRequest(path_params={"df_id": df_id})
        response = await api_get_dataframe_summary(request)

        assert response.status_code == 200

    async def test_execute_pandas_expression(self, test_dataframe):
        """Test pandas expression execution."""
        df_id, manager = test_dataframe

        request = MockRequestWithBody(
            path_params={"df_id": df_id},
            json_body={"pandas_expression": "df.head(2)"}
        )
        response = await api_execute_dataframe_operation(request)

        assert response.status_code == 200

    async def test_execute_invalid_expression(self, test_dataframe):
        """Test invalid pandas expression handling."""
        df_id, manager = test_dataframe

        request = MockRequestWithBody(
            path_params={"df_id": df_id},
            json_body={"pandas_expression": "invalid_syntax("}
        )
        response = await api_execute_dataframe_operation(request)

        assert response.status_code == 400

    async def test_nonexistent_dataframe(self):
        """Test handling of non-existent DataFrame."""
        request = MockRequest(path_params={"df_id": "non-existent"})
        response = await api_get_dataframe_detail(request)

        assert response.status_code == 404


# Standalone test function for manual execution
async def test_dataframe_api_endpoints():
    """Test the DataFrame API endpoints manually."""
    print("Testing DataFrame API endpoints...")

    try:
        # Get DataFrame manager and create test data
        manager = get_dataframe_manager()
        await manager.start()

        # Create test DataFrame
        test_df = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie', 'Diana'],
            'age': [25, 30, 35, 28],
            'city': ['New York', 'London', 'Paris', 'Tokyo']
        })

        # Store test DataFrame
        df_id = await manager.store_dataframe(
            df=test_df,
            tags={"test": True, "source": "test_script"}
        )
        print(f"✓ Created test DataFrame with ID: {df_id}")

        # Test 1: List DataFrames
        print("\n1. Testing list DataFrames endpoint...")
        request = MockRequest()
        response = await api_list_dataframes(request)
        assert response.status_code == 200
        data = response.body.decode()
        print(f"✓ List DataFrames response: {len(data)} bytes")

        # Test 2: Get DataFrame detail
        print("\n2. Testing DataFrame detail endpoint...")
        request = MockRequest(path_params={"df_id": df_id})
        response = await api_get_dataframe_detail(request)
        assert response.status_code == 200
        print("✓ DataFrame detail retrieved successfully")

        # Test 3: Get storage stats
        print("\n3. Testing storage stats endpoint...")
        request = MockRequest()
        response = await api_get_storage_stats(request)
        assert response.status_code == 200
        print("✓ Storage stats retrieved successfully")

        # Test 4: Get DataFrame data
        print("\n4. Testing DataFrame data endpoint...")
        request = MockRequest(path_params={"df_id": df_id})
        response = await api_get_dataframe_data(request)
        assert response.status_code == 200
        print("✓ DataFrame data retrieved successfully")

        # Test 4a: Test pagination
        print("\n4a. Testing DataFrame data pagination...")
        request = MockRequest(
            path_params={"df_id": df_id},
            query_params={"page": "1", "page_size": "2"}
        )
        response = await api_get_dataframe_data(request)
        assert response.status_code == 200
        print("✓ DataFrame data pagination works correctly")

        # Test 4b: Test column filtering
        print("\n4b. Testing DataFrame column filtering...")
        request = MockRequest(
            path_params={"df_id": df_id},
            query_params={"columns": "name,age"}
        )
        response = await api_get_dataframe_data(request)
        assert response.status_code == 200
        print("✓ DataFrame column filtering works correctly")

        # Test 5: Get DataFrame summary
        print("\n5. Testing DataFrame summary endpoint...")
        request = MockRequest(path_params={"df_id": df_id})
        response = await api_get_dataframe_summary(request)
        assert response.status_code == 200
        print("✓ DataFrame summary retrieved successfully")

        # Test 6: Test pandas expression execution
        print("\n6. Testing pandas expression execution...")
        request = MockRequestWithBody(
            path_params={"df_id": df_id},
            json_body={"pandas_expression": "df.head(2)"}
        )
        response = await api_execute_dataframe_operation(request)
        assert response.status_code == 200
        print("✓ Pandas expression execution works correctly")

        # Test 6a: Test invalid expression
        print("\n6a. Testing invalid pandas expression...")
        request = MockRequestWithBody(
            path_params={"df_id": df_id},
            json_body={"pandas_expression": "invalid_syntax("}
        )
        response = await api_execute_dataframe_operation(request)
        assert response.status_code == 400
        print("✓ Invalid expression correctly returns 400 error")

        # Test 7: Test with non-existent DataFrame
        print("\n7. Testing with non-existent DataFrame...")
        request = MockRequest(path_params={"df_id": "non-existent"})
        response = await api_get_dataframe_detail(request)
        assert response.status_code == 404
        print("✓ Correctly returned 404 for non-existent DataFrame")

        # Cleanup
        await manager.delete_dataframe(df_id)
        print(f"✓ Cleaned up test DataFrame: {df_id}")

        print("\n🎉 All DataFrame API endpoint tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_dataframe_api_endpoints())
    sys.exit(0 if success else 1)
