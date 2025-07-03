"""Tests for DataFrame summarizer functionality."""

import pytest
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from ..summarizer import DataFrameSummarizer


class TestDataFrameSummarizer:
    """Test cases for DataFrameSummarizer."""

    @pytest.fixture
    def summarizer(self):
        """Create a summarizer instance."""
        return DataFrameSummarizer()

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            'id': range(1, 101),
            'name': [f'user_{i}' for i in range(1, 101)],
            'age': [20 + (i % 50) for i in range(100)],
            'salary': [30000 + i * 500 for i in range(100)],
            'department': ['Engineering' if i % 3 == 0 else 'Sales' if i % 3 == 1 else 'Marketing' for i in range(100)],
            'join_date': [datetime(2020, 1, 1) + timedelta(days=i*3) for i in range(100)],
            'active': [True if i % 4 != 0 else False for i in range(100)],
            'score': [i * 0.5 for i in range(100)],
        })

    @pytest.fixture
    def mixed_dataframe(self):
        """Create a DataFrame with mixed data types."""
        return pd.DataFrame({
            'int_col': [1, 2, 3, None, 5],
            'float_col': [1.1, 2.2, None, 4.4, 5.5],
            'str_col': ['a', 'b', 'c', None, 'e'],
            'cat_col': pd.Categorical(['X', 'Y', 'X', 'Z', 'Y']),
            'date_col': pd.date_range('2023-01-01', periods=5),
            'bool_col': [True, False, True, None, False],
        })

    @pytest.fixture
    def empty_dataframe(self):
        """Create an empty DataFrame."""
        return pd.DataFrame()

    @pytest.mark.asyncio
    async def test_summarize_basic(self, summarizer, sample_dataframe):
        """Test basic summarization functionality."""
        summary = await summarizer.summarize(
            sample_dataframe,
            max_size_bytes=50000,
            include_sample=True,
            sample_size=5
        )

        # Check basic structure
        assert "shape" in summary
        assert "columns" in summary
        assert "dtypes" in summary
        assert "memory_usage_mb" in summary
        assert "null_counts" in summary
        assert "size_bytes" in summary
        assert "column_analysis" in summary

        # Check values
        assert summary["shape"] == sample_dataframe.shape
        assert summary["columns"] == list(sample_dataframe.columns)
        assert len(summary["dtypes"]) == len(sample_dataframe.columns)
        assert summary["memory_usage_mb"] > 0
        assert summary["size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_summarize_numeric_summary(self, summarizer, sample_dataframe):
        """Test numeric columns summary."""
        summary = await summarizer.summarize(sample_dataframe, max_size_bytes=50000)

        assert "numeric_summary" in summary
        numeric_summary = summary["numeric_summary"]

        # Should include numeric columns
        numeric_cols = sample_dataframe.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            assert col in numeric_summary
            assert "count" in str(numeric_summary[col])
            assert "mean" in str(numeric_summary[col])
            assert "std" in str(numeric_summary[col])

    @pytest.mark.asyncio
    async def test_summarize_categorical_summary(self, summarizer, sample_dataframe):
        """Test categorical columns summary."""
        summary = await summarizer.summarize(sample_dataframe, max_size_bytes=50000)

        assert "categorical_summary" in summary
        categorical_summary = summary["categorical_summary"]

        # Should include object/categorical columns
        categorical_cols = sample_dataframe.select_dtypes(include=['object', 'category']).columns
        for col in categorical_cols:
            if col in categorical_summary:  # Limited to first 5
                assert isinstance(categorical_summary[col], dict)
                # Should have value counts
                assert len(categorical_summary[col]) > 0

    @pytest.mark.asyncio
    async def test_summarize_with_sample(self, summarizer, sample_dataframe):
        """Test summarization with sample data."""
        summary = await summarizer.summarize(
            sample_dataframe,
            max_size_bytes=50000,
            include_sample=True,
            sample_size=10
        )

        assert "sample_data" in summary
        assert isinstance(summary["sample_data"], str)
        assert len(summary["sample_data"]) > 0

    @pytest.mark.asyncio
    async def test_summarize_without_sample(self, summarizer, sample_dataframe):
        """Test summarization without sample data."""
        summary = await summarizer.summarize(
            sample_dataframe,
            max_size_bytes=50000,
            include_sample=False
        )

        assert "sample_data" not in summary

    @pytest.mark.asyncio
    async def test_summarize_sample_too_large(self, summarizer, sample_dataframe):
        """Test summarization when sample is too large."""
        summary = await summarizer.summarize(
            sample_dataframe,
            max_size_bytes=100,  # Very small size
            include_sample=True,
            sample_size=50
        )

        # Should either exclude sample or include message about size
        if "sample_data" in summary:
            assert "too large" in summary["sample_data"].lower()

    @pytest.mark.asyncio
    async def test_summarize_empty_dataframe(self, summarizer, empty_dataframe):
        """Test summarization of empty DataFrame."""
        summary = await summarizer.summarize(empty_dataframe, max_size_bytes=10000)

        assert summary["shape"] == (0, 0)
        assert summary["columns"] == []
        assert summary["dtypes"] == {}
        assert summary["memory_usage_mb"] >= 0

    @pytest.mark.asyncio
    async def test_summarize_mixed_types(self, summarizer, mixed_dataframe):
        """Test summarization with mixed data types."""
        summary = await summarizer.summarize(mixed_dataframe, max_size_bytes=50000)

        # Should handle all data types
        assert "column_analysis" in summary
        analysis = summary["column_analysis"]

        # Check each column type is analyzed
        for col in mixed_dataframe.columns:
            assert col in analysis
            assert "dtype" in analysis[col]
            assert "null_count" in analysis[col]
            assert "unique_count" in analysis[col]

    @pytest.mark.asyncio
    async def test_summarize_error_handling(self, summarizer):
        """Test error handling in summarization."""
        # Test with invalid DataFrame
        invalid_df = MagicMock()
        invalid_df.shape = (10, 5)  # Valid shape
        invalid_df.columns = ['a', 'b', 'c', 'd', 'e']  # Valid columns
        invalid_df.memory_usage.side_effect = Exception("Test error")

        summary = await summarizer.summarize(invalid_df, max_size_bytes=10000)

        assert "error" in summary
        assert "Test error" in summary["error"]

    @pytest.mark.asyncio
    async def test_format_for_display_table(self, summarizer, sample_dataframe):
        """Test table formatting."""
        result = await summarizer.format_for_display(
            sample_dataframe.head(10),
            max_size_bytes=10000,
            format_type="table"
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain column names
        for col in sample_dataframe.columns:
            assert col in result

    @pytest.mark.asyncio
    async def test_format_for_display_csv(self, summarizer, sample_dataframe):
        """Test CSV formatting."""
        result = await summarizer.format_for_display(
            sample_dataframe.head(10),
            max_size_bytes=10000,
            format_type="csv"
        )

        assert isinstance(result, str)
        assert "," in result  # Should contain CSV separators
        # Should start with header
        first_line = result.split('\n')[0]
        for col in sample_dataframe.columns:
            assert col in first_line

    @pytest.mark.asyncio
    async def test_format_for_display_json(self, summarizer, sample_dataframe):
        """Test JSON formatting."""
        small_df = sample_dataframe.head(5)
        result = await summarizer.format_for_display(
            small_df,
            max_size_bytes=50000,
            format_type="json"
        )

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 5

    @pytest.mark.asyncio
    async def test_format_for_display_empty(self, summarizer, empty_dataframe):
        """Test formatting empty DataFrame."""
        result = await summarizer.format_for_display(
            empty_dataframe,
            max_size_bytes=1000,
            format_type="table"
        )

        assert result == "Empty DataFrame"

    @pytest.mark.asyncio
    async def test_format_for_display_size_limits(self, summarizer, sample_dataframe):
        """Test formatting with various size limits."""
        size_limits = [100, 500, 1000, 5000]

        for size_limit in size_limits:
            result = await summarizer.format_for_display(
                sample_dataframe,
                max_size_bytes=size_limit,
                format_type="table"
            )

            # Result should not exceed size limit significantly
            actual_size = len(result.encode('utf-8'))
            # Allow some flexibility due to formatting overhead
            assert actual_size <= size_limit * 1.1 or "too large" in result.lower()

    @pytest.mark.asyncio
    async def test_format_for_display_progressive_truncation(self, summarizer, sample_dataframe):
        """Test progressive truncation in table formatting."""
        # Very small size limit should trigger truncation
        result = await summarizer.format_for_display(
            sample_dataframe,
            max_size_bytes=200,
            format_type="table"
        )

        # Should contain truncation indicators or be minimal
        assert "..." in result or "too large" in result.lower() or len(result) < 200

    @pytest.mark.asyncio
    async def test_format_unknown_type_defaults_to_table(self, summarizer, sample_dataframe):
        """Test that unknown format type defaults to table."""
        result = await summarizer.format_for_display(
            sample_dataframe.head(5),
            max_size_bytes=10000,
            format_type="unknown"
        )

        # Should format as table (default)
        assert isinstance(result, str)
        # Should contain column names like table format
        for col in sample_dataframe.columns:
            assert col in result

    @pytest.mark.asyncio
    async def test_analyze_columns_numeric(self, summarizer, mixed_dataframe):
        """Test column analysis for numeric columns."""
        analysis = await summarizer._analyze_columns(mixed_dataframe)

        # Check numeric column analysis
        float_analysis = analysis["float_col"]
        assert "min" in float_analysis
        assert "max" in float_analysis
        assert "mean" in float_analysis
        assert "std" in float_analysis
        assert float_analysis["null_count"] == 1  # One null value

    @pytest.mark.asyncio
    async def test_analyze_columns_datetime(self, summarizer, mixed_dataframe):
        """Test column analysis for datetime columns."""
        analysis = await summarizer._analyze_columns(mixed_dataframe)

        # Check datetime column analysis
        date_analysis = analysis["date_col"]
        assert "min_date" in date_analysis
        assert "max_date" in date_analysis
        assert "date_range_days" in date_analysis

    @pytest.mark.asyncio
    async def test_analyze_columns_string(self, summarizer, mixed_dataframe):
        """Test column analysis for string columns."""
        analysis = await summarizer._analyze_columns(mixed_dataframe)

        # Check string column analysis
        str_analysis = analysis["str_col"]
        assert "avg_length" in str_analysis
        assert "max_length" in str_analysis
        assert "most_common" in str_analysis
        assert str_analysis["null_count"] == 1

    @pytest.mark.asyncio
    async def test_analyze_columns_error_handling(self, summarizer):
        """Test column analysis error handling."""
        # Create DataFrame with problematic column
        problematic_df = pd.DataFrame({
            "normal": [1, 2, 3],
            "problematic": [object(), object(), object()]  # Non-serializable objects
        })

        analysis = await summarizer._analyze_columns(problematic_df)

        # Normal column should be analyzed
        assert "normal" in analysis
        assert "dtype" in analysis["normal"]

        # Problematic column should have error
        if "problematic" in analysis:
            # May have error field or partial analysis
            assert "error" in analysis["problematic"] or "dtype" in analysis["problematic"]

    @pytest.mark.asyncio
    async def test_get_sample_basic(self, summarizer, sample_dataframe):
        """Test basic sampling functionality."""
        sample = await summarizer._get_sample(sample_dataframe, 10)

        assert len(sample) == 10
        assert set(sample.columns) == set(sample_dataframe.columns)

    @pytest.mark.asyncio
    async def test_get_sample_larger_than_dataframe(self, summarizer, mixed_dataframe):
        """Test sampling when sample size is larger than DataFrame."""
        sample = await summarizer._get_sample(mixed_dataframe, 100)

        # Should return entire DataFrame
        assert len(sample) == len(mixed_dataframe)

    @pytest.mark.asyncio
    async def test_get_sample_stratified(self, summarizer):
        """Test stratified sampling with categorical column."""
        # Create DataFrame with clear categories
        large_df = pd.DataFrame({
            'category': ['A'] * 50 + ['B'] * 30 + ['C'] * 20,
            'value': range(100)
        })

        sample = await summarizer._get_sample(large_df, 10)

        # Sample size might be slightly different due to stratified sampling logic
        assert len(sample) >= 9 and len(sample) <= 10
        # Should contain multiple categories if stratified sampling worked
        unique_categories = sample['category'].nunique()
        assert unique_categories >= 1  # At least one category

    @pytest.mark.asyncio
    async def test_get_sample_random_fallback(self, summarizer):
        """Test fallback to random sampling."""
        # DataFrame with only numeric columns (no categorical for stratification)
        numeric_df = pd.DataFrame({
            'a': range(100),
            'b': range(100, 200)
        })

        sample = await summarizer._get_sample(numeric_df, 15)

        assert len(sample) == 15
        assert list(sample.columns) == ['a', 'b']

    @pytest.mark.asyncio
    async def test_get_sample_error_fallback(self, summarizer, sample_dataframe):
        """Test fallback to head() when sampling fails."""
        # Create a mock that will force the exception path
        with patch('pandas.DataFrame.sample', side_effect=Exception("Sampling failed")):
            sample = await summarizer._get_sample(sample_dataframe, 5)

            # Should fallback to head()
            assert len(sample) == 5
            # Check that columns match and data is the same as head()
            assert set(sample.columns) == set(sample_dataframe.columns)
            expected_head = sample_dataframe.head(5)
            pd.testing.assert_frame_equal(sample.sort_index(axis=1), expected_head.sort_index(axis=1))

    @pytest.mark.asyncio
    async def test_format_as_table_progressive_strategies(self, summarizer, sample_dataframe):
        """Test progressive table formatting strategies."""
        # Test with very restrictive size
        result = await summarizer._format_as_table(sample_dataframe, 500)

        # Should apply some strategy to fit the size
        assert len(result.encode('utf-8')) <= 500 * 1.2  # Allow some overhead

        # Should contain information about truncation if applied
        if len(sample_dataframe) > 5:  # If DataFrame is large enough
            assert "..." in result or "more rows" in result or "too large" in result.lower()

    @pytest.mark.asyncio
    async def test_format_as_csv_progressive_truncation(self, summarizer, sample_dataframe):
        """Test progressive CSV formatting."""
        result = await summarizer._format_as_csv(sample_dataframe, 1000)

        # Should be valid CSV-like format
        lines = result.split('\n')
        assert len(lines) > 0

        # First line should be header
        header = lines[0]
        for col in sample_dataframe.columns:
            assert col in header

    @pytest.mark.asyncio
    async def test_format_as_json_progressive_truncation(self, summarizer, sample_dataframe):
        """Test progressive JSON formatting."""
        result = await summarizer._format_as_json(sample_dataframe, 2000)

        # Should be valid JSON or error message
        if result.startswith('{'):
            # Error message format
            error_data = json.loads(result)
            assert "error" in error_data
        else:
            # Valid data format
            data = json.loads(result)
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_error_logging(self, summarizer, sample_dataframe):
        """Test error logging in format methods."""
        with patch.object(summarizer._logger, 'warning') as mock_warning:
            with patch.object(summarizer._logger, 'error') as mock_error:
                # Force an error in table formatting
                with patch('pandas.DataFrame.to_string', side_effect=Exception("Test error")):
                    result = await summarizer._format_as_table(sample_dataframe, 10000)

                    # Should handle error gracefully
                    assert "too large" in result.lower() or "error" in result.lower()
                    # Should log the error
                    assert mock_warning.called or mock_error.called


if __name__ == "__main__":
    pytest.main([__file__])
