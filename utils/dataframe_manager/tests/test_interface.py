"""Tests for DataFrame manager interfaces and data classes."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
import pandas as pd

from ..interface import (
    DataFrameMetadata,
    DataFrameQueryResult,
    DataFrameStorageInterface,
    DataFrameQueryInterface,
    DataFrameSummarizerInterface,
    DataFrameManagerInterface,
)


class TestDataFrameMetadata:
    """Test cases for DataFrameMetadata."""

    def test_metadata_creation(self):
        """Test creating metadata with all parameters."""
        df_id = uuid4()
        created_at = datetime.now()
        shape = (100, 5)
        dtypes = {"col1": "int64", "col2": "object"}

        metadata = DataFrameMetadata(
            df_id=df_id,
            created_at=created_at,
            size_bytes=1024,
            shape=shape,
            dtypes=dtypes,
            memory_usage=2048,
            ttl_seconds=3600,
            tags={"type": "test", "version": "1"},
        )

        assert metadata.df_id == df_id
        assert metadata.created_at == created_at
        assert metadata.size_bytes == 1024
        assert metadata.shape == shape
        assert metadata.dtypes == dtypes
        assert metadata.memory_usage == 2048
        assert metadata.ttl_seconds == 3600
        assert metadata.tags == {"type": "test", "version": "1"}

    def test_metadata_creation_minimal(self):
        """Test creating metadata with minimal parameters."""
        df_id = uuid4()
        created_at = datetime.now()

        metadata = DataFrameMetadata(
            df_id=df_id,
            created_at=created_at,
            size_bytes=1024,
            shape=(10, 2),
            dtypes={"col1": "int64"},
            memory_usage=512,
        )

        assert metadata.df_id == df_id
        assert metadata.created_at == created_at
        assert metadata.ttl_seconds is None
        assert metadata.tags == {}

    def test_expires_at_property(self):
        """Test expires_at property calculation."""
        created_at = datetime.now()
        ttl_seconds = 3600

        metadata = DataFrameMetadata(
            df_id=uuid4(),
            created_at=created_at,
            size_bytes=1024,
            shape=(10, 2),
            dtypes={"col1": "int64"},
            memory_usage=512,
            ttl_seconds=ttl_seconds,
        )

        expected_expires_at = created_at + timedelta(seconds=ttl_seconds)
        assert metadata.expires_at == expected_expires_at

    def test_expires_at_none_when_no_ttl(self):
        """Test expires_at returns None when no TTL is set."""
        metadata = DataFrameMetadata(
            df_id=uuid4(),
            created_at=datetime.now(),
            size_bytes=1024,
            shape=(10, 2),
            dtypes={"col1": "int64"},
            memory_usage=512,
        )

        assert metadata.expires_at is None

    def test_is_expired_false_when_no_ttl(self):
        """Test is_expired returns False when no TTL is set."""
        metadata = DataFrameMetadata(
            df_id=uuid4(),
            created_at=datetime.now(),
            size_bytes=1024,
            shape=(10, 2),
            dtypes={"col1": "int64"},
            memory_usage=512,
        )

        assert metadata.is_expired is False

    def test_is_expired_false_when_not_expired(self):
        """Test is_expired returns False when not expired."""
        metadata = DataFrameMetadata(
            df_id=uuid4(),
            created_at=datetime.now(),
            size_bytes=1024,
            shape=(10, 2),
            dtypes={"col1": "int64"},
            memory_usage=512,
            ttl_seconds=3600,  # 1 hour from now
        )

        assert metadata.is_expired is False

    def test_is_expired_true_when_expired(self):
        """Test is_expired returns True when expired."""
        # Create metadata with past creation time
        past_time = datetime.now() - timedelta(hours=2)
        metadata = DataFrameMetadata(
            df_id=uuid4(),
            created_at=past_time,
            size_bytes=1024,
            shape=(10, 2),
            dtypes={"col1": "int64"},
            memory_usage=512,
            ttl_seconds=3600,  # 1 hour, but created 2 hours ago
        )

        assert metadata.is_expired is True


class TestDataFrameQueryResult:
    """Test cases for DataFrameQueryResult."""

    def test_query_result_creation(self):
        """Test creating a query result."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        operation = "head"
        parameters = {"n": 5}
        metadata = {"original_shape": (100, 2), "result_shape": (3, 2)}
        execution_time_ms = 15.5

        result = DataFrameQueryResult(
            data=df,
            operation=operation,
            parameters=parameters,
            metadata=metadata,
            execution_time_ms=execution_time_ms,
        )

        assert result.data.equals(df)
        assert result.operation == operation
        assert result.parameters == parameters
        assert result.metadata == metadata
        assert result.execution_time_ms == execution_time_ms

    def test_query_result_empty_dataframe(self):
        """Test creating a query result with empty DataFrame."""
        df = pd.DataFrame()

        result = DataFrameQueryResult(
            data=df,
            operation="filter",
            parameters={"conditions": {"col": {"gt": 100}}},
            metadata={"rows_filtered": 10},
            execution_time_ms=5.2,
        )

        assert result.data.empty
        assert result.operation == "filter"


class TestInterfaceAbstractions:
    """Test that interfaces are properly abstract."""

    def test_storage_interface_is_abstract(self):
        """Test that DataFrameStorageInterface cannot be instantiated."""
        with pytest.raises(TypeError):
            DataFrameStorageInterface()

    def test_query_interface_is_abstract(self):
        """Test that DataFrameQueryInterface cannot be instantiated."""
        with pytest.raises(TypeError):
            DataFrameQueryInterface()

    def test_summarizer_interface_is_abstract(self):
        """Test that DataFrameSummarizerInterface cannot be instantiated."""
        with pytest.raises(TypeError):
            DataFrameSummarizerInterface()

    def test_manager_interface_is_abstract(self):
        """Test that DataFrameManagerInterface cannot be instantiated."""
        with pytest.raises(TypeError):
            DataFrameManagerInterface()


if __name__ == "__main__":
    pytest.main([__file__])
