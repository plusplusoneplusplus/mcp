"""DataFrame query processing implementation."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from ..interface import DataFrameQueryInterface, DataFrameQueryResult

logger = logging.getLogger(__name__)


class DataFrameQueryProcessor(DataFrameQueryInterface):
    """Implementation of DataFrame query operations."""

    def __init__(self):
        self._logger = logger.getChild(self.__class__.__name__)

    async def head(
        self,
        df: pd.DataFrame,
        n: int = 5,
    ) -> DataFrameQueryResult:
        """Get first n rows."""
        start_time = time.time()
        try:
            result_df = df.head(n)
            execution_time = (time.time() - start_time) * 1000

            return DataFrameQueryResult(
                data=result_df,
                operation="head",
                parameters={"n": n},
                metadata={
                    "original_shape": df.shape,
                    "result_shape": result_df.shape,
                    "rows_returned": len(result_df),
                },
                execution_time_ms=execution_time,
            )
        except Exception as e:
            self._logger.error(f"Error in head operation: {e}")
            raise

    async def tail(
        self,
        df: pd.DataFrame,
        n: int = 5,
    ) -> DataFrameQueryResult:
        """Get last n rows."""
        start_time = time.time()
        try:
            result_df = df.tail(n)
            execution_time = (time.time() - start_time) * 1000

            return DataFrameQueryResult(
                data=result_df,
                operation="tail",
                parameters={"n": n},
                metadata={
                    "original_shape": df.shape,
                    "result_shape": result_df.shape,
                    "rows_returned": len(result_df),
                },
                execution_time_ms=execution_time,
            )
        except Exception as e:
            self._logger.error(f"Error in tail operation: {e}")
            raise

    async def sample(
        self,
        df: pd.DataFrame,
        n: Optional[int] = None,
        frac: Optional[float] = None,
        random_state: Optional[int] = None,
    ) -> DataFrameQueryResult:
        """Get random sample of rows."""
        start_time = time.time()
        try:
            if n is None and frac is None:
                n = min(10, len(df))  # Default to 10 rows or less

            result_df = df.sample(n=n, frac=frac, random_state=random_state)
            execution_time = (time.time() - start_time) * 1000

            return DataFrameQueryResult(
                data=result_df,
                operation="sample",
                parameters={"n": n, "frac": frac, "random_state": random_state},
                metadata={
                    "original_shape": df.shape,
                    "result_shape": result_df.shape,
                    "rows_returned": len(result_df),
                    "sampling_ratio": len(result_df) / len(df) if len(df) > 0 else 0,
                },
                execution_time_ms=execution_time,
            )
        except Exception as e:
            self._logger.error(f"Error in sample operation: {e}")
            raise

    async def describe(
        self,
        df: pd.DataFrame,
        include: Optional[Union[str, List[str]]] = None,
    ) -> DataFrameQueryResult:
        """Generate descriptive statistics."""
        start_time = time.time()
        try:
            result_df = df.describe(include=include)
            execution_time = (time.time() - start_time) * 1000

            return DataFrameQueryResult(
                data=result_df,
                operation="describe",
                parameters={"include": include},
                metadata={
                    "original_shape": df.shape,
                    "result_shape": result_df.shape,
                    "columns_analyzed": list(result_df.columns),
                    "statistics_computed": list(result_df.index),
                },
                execution_time_ms=execution_time,
            )
        except Exception as e:
            self._logger.error(f"Error in describe operation: {e}")
            raise

    async def info(
        self,
        df: pd.DataFrame,
    ) -> DataFrameQueryResult:
        """Get DataFrame info (dtypes, memory usage, etc.)."""
        start_time = time.time()
        try:
            # Create a summary DataFrame from info
            info_data = {
                "Column": list(df.columns),
                "Non-Null Count": [df[col].count() for col in df.columns],
                "Dtype": [str(df[col].dtype) for col in df.columns],
                "Memory Usage": [df[col].memory_usage(deep=True) for col in df.columns],
            }

            result_df = pd.DataFrame(info_data)
            execution_time = (time.time() - start_time) * 1000

            total_memory = df.memory_usage(deep=True).sum()

            return DataFrameQueryResult(
                data=result_df,
                operation="info",
                parameters={},
                metadata={
                    "original_shape": df.shape,
                    "result_shape": result_df.shape,
                    "total_memory_usage": total_memory,
                    "total_memory_mb": total_memory / (1024 * 1024),
                    "column_count": len(df.columns),
                    "row_count": len(df),
                },
                execution_time_ms=execution_time,
            )
        except Exception as e:
            self._logger.error(f"Error in info operation: {e}")
            raise

    async def query(
        self,
        df: pd.DataFrame,
        expr: str,
    ) -> DataFrameQueryResult:
        """Query DataFrame using pandas query syntax or Python expressions."""
        start_time = time.time()
        try:
            # Try pandas query syntax first
            result_df = df.query(expr)
            query_method = "pandas_query"
        except Exception:
            # Fall back to Python expression evaluation
            try:
                result_df = eval(expr)
                query_method = "python_eval"
            except Exception as e:
                self._logger.error(f"Error in query operation: {e}")
                raise

        execution_time = (time.time() - start_time) * 1000

        return DataFrameQueryResult(
            data=result_df,
            operation="query",
            parameters={"expr": expr},
            metadata={
                "original_shape": df.shape,
                "result_shape": result_df.shape,
                "rows_filtered": len(df) - len(result_df),
                "filter_ratio": len(result_df) / len(df) if len(df) > 0 else 0,
                "query_expression": expr,
                "query_method": query_method,
            },
            execution_time_ms=execution_time,
        )

    async def filter(
        self,
        df: pd.DataFrame,
        conditions: Dict[str, Any],
    ) -> DataFrameQueryResult:
        """Filter DataFrame based on conditions."""
        start_time = time.time()
        try:
            result_df = df.copy()
            applied_conditions = []

            for column, condition in conditions.items():
                if column not in df.columns:
                    raise ValueError(f"Column '{column}' not found in DataFrame")

                if isinstance(condition, dict):
                    # Handle complex conditions like {"gt": 10, "lt": 100}
                    for op, value in condition.items():
                        if op == "eq":
                            result_df = result_df[result_df[column] == value]
                        elif op == "ne":
                            result_df = result_df[result_df[column] != value]
                        elif op == "gt":
                            result_df = result_df[result_df[column] > value]
                        elif op == "gte":
                            result_df = result_df[result_df[column] >= value]
                        elif op == "lt":
                            result_df = result_df[result_df[column] < value]
                        elif op == "lte":
                            result_df = result_df[result_df[column] <= value]
                        elif op == "in":
                            result_df = result_df[result_df[column].isin(value)]
                        elif op == "not_in":
                            result_df = result_df[~result_df[column].isin(value)]
                        elif op == "contains":
                            result_df = result_df[result_df[column].str.contains(str(value), na=False)]
                        elif op == "startswith":
                            result_df = result_df[result_df[column].str.startswith(str(value), na=False)]
                        elif op == "endswith":
                            result_df = result_df[result_df[column].str.endswith(str(value), na=False)]
                        else:
                            raise ValueError(f"Unknown filter operation: {op}")

                        applied_conditions.append(f"{column} {op} {value}")
                else:
                    # Simple equality condition
                    result_df = result_df[result_df[column] == condition]
                    applied_conditions.append(f"{column} == {condition}")

            execution_time = (time.time() - start_time) * 1000

            return DataFrameQueryResult(
                data=result_df,
                operation="filter",
                parameters={"conditions": conditions},
                metadata={
                    "original_shape": df.shape,
                    "result_shape": result_df.shape,
                    "rows_filtered": len(df) - len(result_df),
                    "filter_ratio": len(result_df) / len(df) if len(df) > 0 else 0,
                    "applied_conditions": applied_conditions,
                },
                execution_time_ms=execution_time,
            )
        except Exception as e:
            self._logger.error(f"Error in filter operation: {e}")
            raise

    async def search(
        self,
        df: pd.DataFrame,
        query: str,
        columns: Optional[List[str]] = None,
    ) -> DataFrameQueryResult:
        """Search DataFrame for text matches."""
        start_time = time.time()
        try:
            if columns is None:
                # Search in all string/object columns
                columns = df.select_dtypes(include=['object', 'string']).columns.tolist()

            if not columns:
                raise ValueError("No searchable columns found in DataFrame")

            # Validate columns exist
            missing_cols = [col for col in columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Columns not found: {missing_cols}")

            # Create search mask
            mask = pd.Series([False] * len(df), index=df.index)

            for col in columns:
                try:
                    # Convert to string and search (case-insensitive)
                    col_mask = df[col].astype(str).str.contains(
                        query, case=False, na=False, regex=False
                    )
                    mask = mask | col_mask
                except Exception as col_error:
                    self._logger.warning(f"Error searching column {col}: {col_error}")
                    continue

            result_df = df[mask]
            execution_time = (time.time() - start_time) * 1000

            return DataFrameQueryResult(
                data=result_df,
                operation="search",
                parameters={"query": query, "columns": columns},
                metadata={
                    "original_shape": df.shape,
                    "result_shape": result_df.shape,
                    "matches_found": len(result_df),
                    "columns_searched": columns,
                    "search_query": query,
                },
                execution_time_ms=execution_time,
            )
        except Exception as e:
            self._logger.error(f"Error in search operation: {e}")
            raise

    async def value_counts(
        self,
        df: pd.DataFrame,
        column: str,
        normalize: bool = False,
        dropna: bool = True,
    ) -> DataFrameQueryResult:
        """Get value counts for a column."""
        start_time = time.time()
        try:
            if column not in df.columns:
                raise ValueError(f"Column '{column}' not found in DataFrame")

            value_counts = df[column].value_counts(normalize=normalize, dropna=dropna)

            # Convert to DataFrame for consistent interface
            result_df = pd.DataFrame({
                "Value": value_counts.index,
                "Count" if not normalize else "Frequency": value_counts.values,
            })

            execution_time = (time.time() - start_time) * 1000

            return DataFrameQueryResult(
                data=result_df,
                operation="value_counts",
                parameters={
                    "column": column,
                    "normalize": normalize,
                    "dropna": dropna,
                },
                metadata={
                    "original_shape": df.shape,
                    "result_shape": result_df.shape,
                    "unique_values": len(result_df),
                    "column_analyzed": column,
                    "total_values": len(df) if dropna else df[column].count(),
                    "null_values": df[column].isnull().sum(),
                },
                execution_time_ms=execution_time,
            )
        except Exception as e:
            self._logger.error(f"Error in value_counts operation: {e}")
            raise
