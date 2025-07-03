"""Tests for DataFrame query processor."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from ..query.processor import DataFrameQueryProcessor
from ..interface import DataFrameQueryResult


class TestDataFrameQueryProcessor:
    """Test cases for DataFrameQueryProcessor."""

    @pytest.fixture
    def processor(self):
        """Create a query processor instance."""
        return DataFrameQueryProcessor()

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            'id': range(1, 101),
            'name': [f'user_{i}' for i in range(1, 101)],
            'age': [20 + (i % 50) for i in range(100)],
            'category': ['A' if i % 3 == 0 else 'B' if i % 3 == 1 else 'C' for i in range(100)],
            'score': [i * 0.5 for i in range(100)],
            'text': [f'This is text {i}' for i in range(100)],
        })

    @pytest.mark.asyncio
    async def test_head_operation(self, processor, sample_dataframe):
        """Test head operation."""
        result = await processor.head(sample_dataframe, n=5)

        assert isinstance(result, DataFrameQueryResult)
        assert result.operation == "head"
        assert result.parameters == {"n": 5}
        assert result.data.shape == (5, 6)
        assert result.metadata["original_shape"] == (100, 6)
        assert result.metadata["result_shape"] == (5, 6)
        assert result.metadata["rows_returned"] == 5
        assert result.execution_time_ms >= 0

        # Verify data integrity
        pd.testing.assert_frame_equal(result.data, sample_dataframe.head(5))

    @pytest.mark.asyncio
    async def test_head_default_n(self, processor, sample_dataframe):
        """Test head operation with default n=5."""
        result = await processor.head(sample_dataframe)

        assert result.data.shape == (5, 6)
        assert result.parameters == {"n": 5}

    @pytest.mark.asyncio
    async def test_head_larger_than_dataframe(self, processor, sample_dataframe):
        """Test head operation when n is larger than DataFrame."""
        result = await processor.head(sample_dataframe, n=200)

        assert result.data.shape == (100, 6)  # Should return all rows
        assert result.parameters == {"n": 200}
        assert result.metadata["rows_returned"] == 100

    @pytest.mark.asyncio
    async def test_tail_operation(self, processor, sample_dataframe):
        """Test tail operation."""
        result = await processor.tail(sample_dataframe, n=3)

        assert isinstance(result, DataFrameQueryResult)
        assert result.operation == "tail"
        assert result.parameters == {"n": 3}
        assert result.data.shape == (3, 6)
        assert result.metadata["original_shape"] == (100, 6)
        assert result.metadata["result_shape"] == (3, 6)
        assert result.metadata["rows_returned"] == 3

        # Verify data integrity
        pd.testing.assert_frame_equal(result.data, sample_dataframe.tail(3))

    @pytest.mark.asyncio
    async def test_sample_operation_with_n(self, processor, sample_dataframe):
        """Test sample operation with n parameter."""
        result = await processor.sample(sample_dataframe, n=10, random_state=42)

        assert isinstance(result, DataFrameQueryResult)
        assert result.operation == "sample"
        assert result.parameters == {"n": 10, "frac": None, "random_state": 42}
        assert result.data.shape == (10, 6)
        assert result.metadata["original_shape"] == (100, 6)
        assert result.metadata["result_shape"] == (10, 6)
        assert result.metadata["rows_returned"] == 10
        assert result.metadata["sampling_ratio"] == 0.1

    @pytest.mark.asyncio
    async def test_sample_operation_with_frac(self, processor, sample_dataframe):
        """Test sample operation with frac parameter."""
        result = await processor.sample(sample_dataframe, frac=0.2, random_state=42)

        assert result.parameters == {"n": None, "frac": 0.2, "random_state": 42}
        assert result.data.shape == (20, 6)
        assert result.metadata["sampling_ratio"] == 0.2

    @pytest.mark.asyncio
    async def test_sample_operation_default(self, processor, sample_dataframe):
        """Test sample operation with default parameters."""
        result = await processor.sample(sample_dataframe)

        assert result.parameters["n"] == 10  # Default to min(10, len(df))
        assert result.data.shape == (10, 6)

    @pytest.mark.asyncio
    async def test_sample_small_dataframe(self, processor):
        """Test sample operation on small DataFrame."""
        small_df = pd.DataFrame({"a": [1, 2, 3]})
        result = await processor.sample(small_df)

        assert result.parameters["n"] == 3  # Should be min(10, 3)
        assert result.data.shape == (3, 1)

    @pytest.mark.asyncio
    async def test_describe_operation(self, processor, sample_dataframe):
        """Test describe operation."""
        result = await processor.describe(sample_dataframe)

        assert isinstance(result, DataFrameQueryResult)
        assert result.operation == "describe"
        assert result.parameters == {"include": None}
        assert "count" in result.data.index
        assert "mean" in result.data.index
        assert "std" in result.data.index
        assert result.metadata["original_shape"] == (100, 6)
        assert len(result.metadata["columns_analyzed"]) > 0
        assert len(result.metadata["statistics_computed"]) > 0

    @pytest.mark.asyncio
    async def test_describe_with_include(self, processor, sample_dataframe):
        """Test describe operation with include parameter."""
        result = await processor.describe(sample_dataframe, include=['number'])

        assert result.parameters == {"include": ['number']}
        # Should only include numeric columns in the result

    @pytest.mark.asyncio
    async def test_info_operation(self, processor, sample_dataframe):
        """Test info operation."""
        result = await processor.info(sample_dataframe)

        assert isinstance(result, DataFrameQueryResult)
        assert result.operation == "info"
        assert result.parameters == {}

        # Check result DataFrame structure
        assert "Column" in result.data.columns
        assert "Non-Null Count" in result.data.columns
        assert "Dtype" in result.data.columns
        assert "Memory Usage" in result.data.columns

        # Check metadata
        assert result.metadata["original_shape"] == (100, 6)
        assert result.metadata["column_count"] == 6
        assert result.metadata["row_count"] == 100
        assert result.metadata["total_memory_usage"] > 0
        assert result.metadata["total_memory_mb"] > 0

    @pytest.mark.asyncio
    async def test_filter_simple_equality(self, processor, sample_dataframe):
        """Test filter operation with simple equality."""
        result = await processor.filter(sample_dataframe, {"category": "A"})

        assert isinstance(result, DataFrameQueryResult)
        assert result.operation == "filter"
        assert result.parameters == {"conditions": {"category": "A"}}
        assert (result.data["category"] == "A").all()
        assert result.metadata["original_shape"] == (100, 6)
        assert result.metadata["rows_filtered"] > 0
        assert result.metadata["filter_ratio"] < 1.0

    @pytest.mark.asyncio
    async def test_filter_complex_conditions(self, processor, sample_dataframe):
        """Test filter operation with complex conditions."""
        conditions = {"age": {"gt": 30, "lt": 50}}
        result = await processor.filter(sample_dataframe, conditions)

        assert result.parameters == {"conditions": conditions}
        assert (result.data["age"] > 30).all()
        assert (result.data["age"] < 50).all()
        assert "age gt 30" in result.metadata["applied_conditions"][0]
        assert "age lt 50" in result.metadata["applied_conditions"][1]

    @pytest.mark.asyncio
    async def test_filter_all_operators(self, processor, sample_dataframe):
        """Test filter operation with all supported operators."""
        test_cases = [
            ({"age": {"eq": 25}}, lambda df: all(df["age"] == 25)),
            ({"age": {"ne": 25}}, lambda df: all(df["age"] != 25)),
            ({"age": {"gte": 30}}, lambda df: all(df["age"] >= 30)),
            ({"age": {"lte": 30}}, lambda df: all(df["age"] <= 30)),
            ({"category": {"in": ["A", "B"]}}, lambda df: all(df["category"].isin(["A", "B"]))),
            ({"category": {"not_in": ["A"]}}, lambda df: all(~df["category"].isin(["A"]))),
            ({"name": {"contains": "user_1"}}, lambda df: all(df["name"].str.contains("user_1", na=False))),
            ({"name": {"startswith": "user_1"}}, lambda df: all(df["name"].str.startswith("user_1", na=False))),
            ({"name": {"endswith": "0"}}, lambda df: all(df["name"].str.endswith("0", na=False))),
        ]

        for conditions, validator in test_cases:
            result = await processor.filter(sample_dataframe, conditions)
            if len(result.data) > 0:  # Only validate if results exist
                assert validator(result.data), f"Failed validation for conditions: {conditions}"

    @pytest.mark.asyncio
    async def test_filter_nonexistent_column(self, processor, sample_dataframe):
        """Test filter operation with non-existent column."""
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            await processor.filter(sample_dataframe, {"nonexistent": "value"})

    @pytest.mark.asyncio
    async def test_filter_unknown_operator(self, processor, sample_dataframe):
        """Test filter operation with unknown operator."""
        with pytest.raises(ValueError, match="Unknown filter operation"):
            await processor.filter(sample_dataframe, {"age": {"unknown_op": 25}})

    @pytest.mark.asyncio
    async def test_search_operation(self, processor, sample_dataframe):
        """Test search operation."""
        result = await processor.search(sample_dataframe, "user_1", ["name"])

        assert isinstance(result, DataFrameQueryResult)
        assert result.operation == "search"
        assert result.parameters == {"query": "user_1", "columns": ["name"]}
        assert result.metadata["search_query"] == "user_1"
        assert result.metadata["columns_searched"] == ["name"]
        assert result.metadata["matches_found"] > 0

        # All results should contain "user_1" in the name column
        if len(result.data) > 0:
            assert result.data["name"].str.contains("user_1", case=False, na=False).all()

    @pytest.mark.asyncio
    async def test_search_auto_detect_columns(self, processor, sample_dataframe):
        """Test search operation with auto-detected columns."""
        result = await processor.search(sample_dataframe, "user")

        # Should search in string/object columns automatically
        assert "columns_searched" in result.metadata
        searched_cols = result.metadata["columns_searched"]
        assert "name" in searched_cols  # name is object type
        assert "text" in searched_cols  # text is object type

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, processor, sample_dataframe):
        """Test search operation is case insensitive."""
        result_lower = await processor.search(sample_dataframe, "user", ["name"])
        result_upper = await processor.search(sample_dataframe, "USER", ["name"])

        # Should return same number of matches
        assert len(result_lower.data) == len(result_upper.data)

    @pytest.mark.asyncio
    async def test_search_nonexistent_column(self, processor, sample_dataframe):
        """Test search operation with non-existent column."""
        with pytest.raises(ValueError, match="Columns not found"):
            await processor.search(sample_dataframe, "test", ["nonexistent"])

    @pytest.mark.asyncio
    async def test_search_no_searchable_columns(self, processor):
        """Test search operation when no searchable columns exist."""
        numeric_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        with pytest.raises(ValueError, match="No searchable columns found"):
            await processor.search(numeric_df, "test")

    @pytest.mark.asyncio
    async def test_value_counts_operation(self, processor, sample_dataframe):
        """Test value_counts operation."""
        result = await processor.value_counts(sample_dataframe, "category")

        assert isinstance(result, DataFrameQueryResult)
        assert result.operation == "value_counts"
        assert result.parameters == {"column": "category", "normalize": False, "dropna": True}

        # Check result DataFrame structure
        assert "Value" in result.data.columns
        assert "Count" in result.data.columns

        # Check metadata
        assert result.metadata["column_analyzed"] == "category"
        assert result.metadata["unique_values"] > 0
        assert result.metadata["total_values"] > 0
        assert result.metadata["null_values"] >= 0

    @pytest.mark.asyncio
    async def test_value_counts_normalized(self, processor, sample_dataframe):
        """Test value_counts operation with normalization."""
        result = await processor.value_counts(sample_dataframe, "category", normalize=True)

        assert result.parameters["normalize"] is True
        assert "Frequency" in result.data.columns

        # Frequencies should sum to approximately 1.0
        assert abs(result.data["Frequency"].sum() - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_value_counts_with_nulls(self, processor):
        """Test value_counts operation with null values."""
        df_with_nulls = pd.DataFrame({
            "category": ["A", "B", "A", None, "C", None]
        })

        # Test with dropna=True (default)
        result = await processor.value_counts(df_with_nulls, "category", dropna=True)
        assert result.metadata["null_values"] == 2
        assert len(result.data) == 3  # A, B, C (nulls dropped)

        # Test with dropna=False
        result = await processor.value_counts(df_with_nulls, "category", dropna=False)
        assert len(result.data) == 4  # A, B, C, NaN

    @pytest.mark.asyncio
    async def test_value_counts_nonexistent_column(self, processor, sample_dataframe):
        """Test value_counts operation with non-existent column."""
        with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
            await processor.value_counts(sample_dataframe, "nonexistent")

    @pytest.mark.asyncio
    async def test_query_operation_simple(self, processor, sample_dataframe):
        """Test query operation with simple expression."""
        result = await processor.query(sample_dataframe, "age > 30")

        assert isinstance(result, DataFrameQueryResult)
        assert result.operation == "query"
        assert result.parameters == {"expr": "age > 30"}
        assert result.metadata["query_expression"] == "age > 30"
        assert result.metadata["original_shape"] == (100, 6)
        assert result.metadata["rows_filtered"] > 0
        assert result.metadata["filter_ratio"] < 1.0

        # All results should have age > 30
        if len(result.data) > 0:
            assert (result.data["age"] > 30).all()

    @pytest.mark.asyncio
    async def test_query_operation_complex(self, processor, sample_dataframe):
        """Test query operation with complex expression."""
        expr = "age > 30 and category == 'A'"
        result = await processor.query(sample_dataframe, expr)

        assert result.parameters == {"expr": expr}
        assert result.metadata["query_expression"] == expr

        # All results should match the complex condition
        if len(result.data) > 0:
            assert (result.data["age"] > 30).all()
            assert (result.data["category"] == "A").all()

    @pytest.mark.asyncio
    async def test_query_operation_string_methods(self, processor, sample_dataframe):
        """Test query operation with string methods."""
        expr = "name.str.contains('user_1')"
        result = await processor.query(sample_dataframe, expr)

        assert result.parameters == {"expr": expr}
        # All results should contain 'user_1' in name
        if len(result.data) > 0:
            assert result.data["name"].str.contains("user_1", na=False).all()

    @pytest.mark.asyncio
    async def test_query_operation_between(self, processor, sample_dataframe):
        """Test query operation with between method."""
        expr = "age.between(25, 35)"
        result = await processor.query(sample_dataframe, expr)

        assert result.parameters == {"expr": expr}
        # All results should have age between 25 and 35
        if len(result.data) > 0:
            assert result.data["age"].between(25, 35).all()

    @pytest.mark.asyncio
    async def test_query_operation_isin(self, processor, sample_dataframe):
        """Test query operation with isin method."""
        expr = "category.isin(['A', 'B'])"
        result = await processor.query(sample_dataframe, expr)

        assert result.parameters == {"expr": expr}
        # All results should have category in ['A', 'B']
        if len(result.data) > 0:
            assert result.data["category"].isin(["A", "B"]).all()

    @pytest.mark.asyncio
    async def test_query_operation_empty_result(self, processor, sample_dataframe):
        """Test query operation that returns empty result."""
        expr = "age > 1000"  # Should return no results
        result = await processor.query(sample_dataframe, expr)

        assert result.parameters == {"expr": expr}
        assert result.data.empty
        assert result.metadata["rows_filtered"] == len(sample_dataframe)
        assert result.metadata["filter_ratio"] == 0.0

    @pytest.mark.asyncio
    async def test_query_operation_invalid_expression(self, processor, sample_dataframe):
        """Test query operation with invalid expression."""
        with pytest.raises(Exception):  # pandas will raise various exceptions for invalid queries
            await processor.query(sample_dataframe, "invalid_column > 30")

    @pytest.mark.asyncio
    async def test_query_operation_syntax_error(self, processor, sample_dataframe):
        """Test query operation with syntax error in expression."""
        with pytest.raises(Exception):  # pandas will raise SyntaxError or similar
            await processor.query(sample_dataframe, "age > 30 and")

    @pytest.mark.asyncio
    async def test_error_handling_with_logging(self, processor, sample_dataframe):
        """Test error handling includes proper logging."""
        with patch.object(processor._logger, 'error') as mock_logger:
            # Force an error by corrupting the DataFrame
            corrupted_df = MagicMock()
            corrupted_df.head.side_effect = Exception("Test error")

            with pytest.raises(Exception):
                await processor.head(corrupted_df)

            mock_logger.assert_called_once()
            assert "Error in head operation" in str(mock_logger.call_args)

    @pytest.mark.asyncio
    async def test_execution_time_measurement(self, processor, sample_dataframe):
        """Test that all operations measure execution time."""
        operations = [
            processor.head(sample_dataframe),
            processor.tail(sample_dataframe),
            processor.sample(sample_dataframe, n=5),
            processor.describe(sample_dataframe),
            processor.info(sample_dataframe),
            processor.filter(sample_dataframe, {"age": {"gt": 25}}),
            processor.search(sample_dataframe, "user", ["name"]),
            processor.value_counts(sample_dataframe, "category"),
        ]

        for operation in operations:
            result = await operation
            assert result.execution_time_ms >= 0
            assert isinstance(result.execution_time_ms, float)


if __name__ == "__main__":
    pytest.main([__file__])
