"""DataFrame summarization for intelligent data exploration."""

import io
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_any_dtype

from .interface import DataFrameSummarizerInterface

logger = logging.getLogger(__name__)


class DataFrameSummarizer(DataFrameSummarizerInterface):
    """Intelligent DataFrame summarization with size-aware formatting."""

    def __init__(self):
        self._logger = logger.getChild(self.__class__.__name__)

    async def summarize(
        self,
        df: pd.DataFrame,
        max_size_bytes: int,
        include_sample: bool = True,
        sample_size: int = 10,
    ) -> Dict[str, Any]:
        """Create intelligent summary of DataFrame."""
        try:
            # Basic info
            summary = {
                "shape": df.shape,
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
                "null_counts": df.isnull().sum().to_dict(),
                "size_bytes": len(df.to_string().encode('utf-8')),
            }

            # Column analysis
            summary["column_analysis"] = await self._analyze_columns(df)

            # Statistical summary for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                summary["numeric_summary"] = df[numeric_cols].describe().to_dict()

            # Sample data if requested and within size limits
            if include_sample and sample_size > 0:
                sample_df = await self._get_sample(df, sample_size)
                sample_str = await self.format_for_display(
                    sample_df,
                    max_size_bytes // 4,  # Reserve 1/4 of size budget for sample
                    "table"
                )
                if len(sample_str.encode('utf-8')) <= max_size_bytes // 4:
                    summary["sample_data"] = sample_str
                else:
                    summary["sample_data"] = "Sample too large to display"

            # Top/bottom values for categorical columns
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns
            if len(categorical_cols) > 0:
                summary["categorical_summary"] = {}
                for col in categorical_cols[:5]:  # Limit to first 5 categorical columns
                    try:
                        value_counts = df[col].value_counts().head(10)
                        summary["categorical_summary"][col] = value_counts.to_dict()
                    except Exception as e:
                        self._logger.warning(f"Could not analyze categorical column {col}: {e}")

            return summary

        except Exception as e:
            self._logger.error(f"Error creating DataFrame summary: {e}")
            return {
                "error": str(e),
                "shape": df.shape if hasattr(df, 'shape') else None,
                "columns": list(df.columns) if hasattr(df, 'columns') else None,
            }

    async def format_for_display(
        self,
        df: pd.DataFrame,
        max_size_bytes: int,
        format_type: str = "table",
    ) -> str:
        """Format DataFrame for display within size constraints."""
        if df.empty:
            return "Empty DataFrame"

        try:
            # Strategy based on format type
            if format_type == "table":
                return await self._format_as_table(df, max_size_bytes)
            elif format_type == "csv":
                return await self._format_as_csv(df, max_size_bytes)
            elif format_type == "json":
                return await self._format_as_json(df, max_size_bytes)
            else:
                return await self._format_as_table(df, max_size_bytes)

        except Exception as e:
            self._logger.error(f"Error formatting DataFrame: {e}")
            return f"Error formatting DataFrame: {e}"

    async def _analyze_columns(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Analyze each column for type, uniqueness, and patterns."""
        analysis = {}

        for col in df.columns:
            try:
                col_data = df[col]

                analysis[col] = {
                    "dtype": str(col_data.dtype),
                    "null_count": col_data.isnull().sum(),
                    "null_percentage": (col_data.isnull().sum() / len(df)) * 100,
                    "unique_count": col_data.nunique(),
                    "uniqueness_percentage": (col_data.nunique() / len(df)) * 100,
                }

                # Type-specific analysis
                if is_numeric_dtype(col_data):
                    analysis[col].update({
                        "min": col_data.min(),
                        "max": col_data.max(),
                        "mean": col_data.mean(),
                        "std": col_data.std(),
                    })
                elif is_datetime64_any_dtype(col_data):
                    analysis[col].update({
                        "min_date": str(col_data.min()),
                        "max_date": str(col_data.max()),
                        "date_range_days": (col_data.max() - col_data.min()).days,
                    })
                else:
                    # String/categorical analysis
                    analysis[col].update({
                        "avg_length": col_data.astype(str).str.len().mean(),
                        "max_length": col_data.astype(str).str.len().max(),
                        "most_common": col_data.value_counts().head(3).to_dict(),
                    })

            except Exception as e:
                analysis[col] = {"error": str(e)}

        return analysis

    async def _get_sample(self, df: pd.DataFrame, sample_size: int) -> pd.DataFrame:
        """Get a representative sample of the DataFrame."""
        if len(df) <= sample_size:
            return df

        # Try to get a diverse sample
        try:
            # If we have many rows, use stratified sampling on a categorical column if available
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns

            if len(categorical_cols) > 0 and len(df) > sample_size * 2:
                # Use the first categorical column for stratification
                strat_col = categorical_cols[0]
                return df.groupby(strat_col, group_keys=False).apply(
                    lambda x: x.sample(min(len(x), max(1, sample_size // df[strat_col].nunique())))
                ).head(sample_size)

            # Otherwise, just random sample
            return df.sample(n=sample_size, random_state=42)

        except Exception:
            # Fallback to head if sampling fails
            return df.head(sample_size)

    async def _format_as_table(self, df: pd.DataFrame, max_size_bytes: int) -> str:
        """Format DataFrame as a table with progressive truncation."""
        # Start with full DataFrame
        current_df = df.copy()

        # Progressive truncation strategies
        strategies = [
            lambda d: d,  # Full DataFrame
            lambda d: d.head(50),  # First 50 rows
            lambda d: d.head(20),  # First 20 rows
            lambda d: d.head(10),  # First 10 rows
            lambda d: d.head(5),   # First 5 rows
        ]

        for strategy in strategies:
            try:
                truncated_df = strategy(current_df)

                # Try different formatting options
                for with_index in [False, True]:
                    formatted = truncated_df.to_string(
                        index=with_index,
                        max_rows=None,
                        max_cols=None,
                        show_dimensions=True,
                    )

                    if len(formatted.encode('utf-8')) <= max_size_bytes:
                        if len(truncated_df) < len(df):
                            formatted += f"\n\n... ({len(df) - len(truncated_df)} more rows)"
                        return formatted

                # Try with column truncation
                max_cols = min(10, len(truncated_df.columns))
                for num_cols in range(max_cols, 0, -1):
                    col_truncated = truncated_df.iloc[:, :num_cols]
                    formatted = col_truncated.to_string(
                        index=False,
                        show_dimensions=True,
                    )

                    if len(formatted.encode('utf-8')) <= max_size_bytes:
                        if num_cols < len(df.columns):
                            formatted += f"\n\n... ({len(df.columns) - num_cols} more columns)"
                        if len(truncated_df) < len(df):
                            formatted += f"\n... ({len(df) - len(truncated_df)} more rows)"
                        return formatted

            except Exception as e:
                self._logger.warning(f"Table formatting strategy failed: {e}")
                continue

        # Final fallback: basic info
        return f"DataFrame too large to display\nShape: {df.shape}\nColumns: {list(df.columns)}"

    async def _format_as_csv(self, df: pd.DataFrame, max_size_bytes: int) -> str:
        """Format DataFrame as CSV with progressive truncation."""
        current_df = df.copy()

        # Progressive row truncation
        for max_rows in [len(df), 100, 50, 20, 10, 5]:
            if max_rows < len(df):
                current_df = df.head(max_rows)

            try:
                buffer = io.StringIO()
                current_df.to_csv(buffer, index=False)
                csv_str = buffer.getvalue()

                if len(csv_str.encode('utf-8')) <= max_size_bytes:
                    if max_rows < len(df):
                        csv_str += f"\n# ... ({len(df) - max_rows} more rows)"
                    return csv_str

            except Exception as e:
                self._logger.warning(f"CSV formatting failed: {e}")
                continue

        return f"# DataFrame too large for CSV\n# Shape: {df.shape}"

    async def _format_as_json(self, df: pd.DataFrame, max_size_bytes: int) -> str:
        """Format DataFrame as JSON with progressive truncation."""
        current_df = df.copy()

        # Progressive row truncation
        for max_rows in [len(df), 50, 20, 10, 5]:
            if max_rows < len(df):
                current_df = df.head(max_rows)

            try:
                json_str = current_df.to_json(orient='records', indent=2)

                if len(json_str.encode('utf-8')) <= max_size_bytes:
                    return json_str

            except Exception as e:
                self._logger.warning(f"JSON formatting failed: {e}")
                continue

        return f'{{"error": "DataFrame too large for JSON", "shape": {list(df.shape)}}}'
