"""Data Frame Service Tool for loading and querying data.

This module provides a comprehensive service for loading data from files/URLs
and performing operations on stored DataFrames using their IDs.
"""

import logging
import sys
import os
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import pandas as pd
import requests

from ..interfaces import ToolInterface
from ..plugin import register_tool

logger = logging.getLogger(__name__)


@register_tool()
class DataFrameServiceTool(ToolInterface):
    """A comprehensive data frame service for loading and querying data.

    This tool enables users to:
    1. Load data from local files or URLs into DataFrames with assigned IDs
    2. Perform various operations on stored DataFrames by ID
    3. Manage multiple DataFrames efficiently
    """

    @property
    def name(self) -> str:
        return "data_frame_service"

    @property
    def description(self) -> str:
        return (
            "Data Frame Service - Load data from files/URLs and execute pandas operations. "
            "Supports loading from local files or URLs, storing with IDs for later operations. "
            "Operations: load_data, execute. Use execute with any pandas expression like df.head(), df.query('age > 30'), etc. "
            "Use this tool to load data once and perform multiple pandas operations efficiently."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform",
                    "enum": ["load_data", "execute"]
                },
                "dataframe_id": {
                    "type": "string",
                    "description": "The ID of the stored DataFrame to operate on (not required for load_data)"
                },
                "parameters": {
                    "type": "object",
                    "description": "Parameters for the operation",
                    "properties": {
                        # For load_data operation
                        "source": {
                            "type": "string",
                            "description": "File path or URL to load data from (for load_data)"
                        },
                        "file_type": {
                            "type": "string",
                            "description": "Type of file to load (csv, json, parquet, excel) - auto-detected if not specified",
                            "enum": ["csv", "json", "parquet", "excel"]
                        },
                        "custom_id": {
                            "type": "string",
                            "description": "Custom ID for the loaded DataFrame (auto-generated if not provided)"
                        },
                        "csv_options": {
                            "type": "object",
                            "description": "Options for CSV loading (sep, header, etc.)",
                            "properties": {
                                "sep": {"type": "string", "description": "Separator character"},
                                "header": {"type": ["integer", "string"], "description": "Row to use as header"},
                                "skiprows": {"type": "integer", "description": "Rows to skip"},
                                "encoding": {"type": "string", "description": "File encoding"}
                            }
                        },
                        # For execute operation
                        "pandas_expression": {
                            "type": "string",
                            "description": "Any pandas expression to execute on the DataFrame. Examples: 'df.head(10)', 'df.query(\"age > 30\")', 'df[df.column > 0].describe()', 'df.groupby(\"category\").sum()'"
                        }
                    }
                }
            },
            "required": ["operation"],
            "additionalProperties": False
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an operation on the data frame service."""
        try:
            operation = arguments.get("operation")
            dataframe_id = arguments.get("dataframe_id")
            parameters = arguments.get("parameters", {})

            if not operation:
                return {
                    "success": False,
                    "error": "operation is required"
                }

            # Handle load_data operation separately
            if operation == "load_data":
                return await self._load_data(parameters)

            # Handle execute operation
            elif operation == "execute":
                return await self._execute_pandas_expression(dataframe_id, parameters)

            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }

        except Exception as e:
            logger.error(f"Unexpected error in DataFrame service tool: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {e}"
            }

    async def _load_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Load data from a file or URL and store it in the DataFrame manager."""
        try:
            source = parameters.get("source")
            if not source:
                return {
                    "success": False,
                    "error": "source parameter is required for load_data operation"
                }

            file_type = parameters.get("file_type")
            custom_id = parameters.get("custom_id")
            csv_options = parameters.get("csv_options", {})

            # Generate ID if not provided
            if not custom_id:
                custom_id = f"dataframe-{uuid.uuid4().hex[:8]}"

            # Determine if source is URL or file path
            parsed_url = urlparse(source)
            is_url = parsed_url.scheme in ['http', 'https']

            # Auto-detect file type if not specified
            if not file_type:
                if source.lower().endswith('.csv'):
                    file_type = 'csv'
                elif source.lower().endswith('.json'):
                    file_type = 'json'
                elif source.lower().endswith('.parquet'):
                    file_type = 'parquet'
                elif source.lower().endswith(('.xlsx', '.xls')):
                    file_type = 'excel'
                else:
                    file_type = 'csv'  # Default to CSV

            # Load the data
            try:
                if is_url:
                    df = await self._load_from_url(source, file_type, csv_options)
                else:
                    df = await self._load_from_file(source, file_type, csv_options)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to load data from {source}: {e}"
                }

            # Get DataFrame manager and store the data
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)

                from utils.dataframe_manager import get_dataframe_manager
                manager = get_dataframe_manager()
                await manager.start()

                # Store the DataFrame
                metadata = await manager.store_dataframe(
                    df=df,
                    df_id=custom_id,
                    tags={"source": source, "file_type": file_type, "loaded_by": "data_frame_service"}
                )

                return {
                    "success": True,
                    "dataframe_id": custom_id,
                    "source": source,
                    "file_type": file_type,
                    "shape": df.shape,
                    "columns": list(df.columns),
                    "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                    "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
                    "sample_data": df.head(3).to_dict('records') if len(df) > 0 else [],
                    "created_at": metadata.created_at.isoformat(),
                    "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to store DataFrame: {e}"
                }

        except Exception as e:
            logger.error(f"Error in load_data operation: {e}")
            return {
                "success": False,
                "error": f"Load data operation failed: {e}"
            }

    async def _load_from_url(self, url: str, file_type: str, csv_options: Dict[str, Any]) -> pd.DataFrame:
        """Load data from a URL."""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            if file_type == 'csv':
                # Use StringIO to read CSV from string content
                from io import StringIO
                return pd.read_csv(StringIO(response.text), **csv_options)
            elif file_type == 'json':
                return pd.read_json(response.text)
            elif file_type == 'parquet':
                # For parquet, we need to save to temp file first
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
                    tmp.write(response.content)
                    tmp.flush()
                    df = pd.read_parquet(tmp.name)
                    os.unlink(tmp.name)
                    return df
            elif file_type == 'excel':
                # For excel, we need to save to temp file first
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                    tmp.write(response.content)
                    tmp.flush()
                    df = pd.read_excel(tmp.name)
                    os.unlink(tmp.name)
                    return df
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

        except requests.RequestException as e:
            raise Exception(f"Failed to fetch URL: {e}")
        except Exception as e:
            raise Exception(f"Failed to parse {file_type} from URL: {e}")

    async def _load_from_file(self, file_path: str, file_type: str, csv_options: Dict[str, Any]) -> pd.DataFrame:
        """Load data from a local file."""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            if file_type == 'csv':
                return pd.read_csv(file_path, **csv_options)
            elif file_type == 'json':
                return pd.read_json(file_path)
            elif file_type == 'parquet':
                return pd.read_parquet(file_path)
            elif file_type == 'excel':
                return pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

        except Exception as e:
            raise Exception(f"Failed to load {file_type} file: {e}")

    async def _execute_pandas_expression(self, dataframe_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a pandas expression on a stored DataFrame."""
        try:
            if not dataframe_id:
                return {
                    "success": False,
                    "error": "dataframe_id is required for execute operation"
                }

            pandas_expression = parameters.get("pandas_expression")
            if not pandas_expression:
                return {
                    "success": False,
                    "error": "pandas_expression parameter is required for execute operation"
                }

            # Get DataFrame manager
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)

                from utils.dataframe_manager import get_dataframe_manager
                manager = get_dataframe_manager()
            except ImportError as e:
                return {
                    "success": False,
                    "error": f"DataFrame management framework not available: {e}"
                }

            # Ensure manager is started
            await manager.start()

            # Get the DataFrame
            df = await manager.get_dataframe(dataframe_id)
            if df is None:
                return {
                    "success": False,
                    "error": f"DataFrame with ID '{dataframe_id}' not found or expired"
                }

            # Execute the pandas expression
            try:
                import time
                start_time = time.time()
                
                # Create execution environment with the DataFrame
                safe_globals = {
                    'df': df,
                    'pd': pd
                }
                
                # Execute the expression
                result = eval(pandas_expression, safe_globals)
                
                execution_time_ms = (time.time() - start_time) * 1000

                # Handle different result types
                if isinstance(result, pd.DataFrame):
                    result_df = result
                elif isinstance(result, pd.Series):
                    result_df = result.to_frame()
                else:
                    # For scalar results, create a simple DataFrame
                    result_df = pd.DataFrame({'result': [result]})

                # Format the response
                response = {
                    "success": True,
                    "dataframe_id": dataframe_id,
                    "expression": pandas_expression,
                    "result_shape": result_df.shape,
                    "execution_time_ms": round(execution_time_ms, 2)
                }

                # Convert result to appropriate format
                if result_df.empty:
                    response["data"] = "No data returned (empty result)"
                else:
                    # For small results, include the actual data
                    if len(result_df) <= 100:
                        response["data"] = result_df.to_dict('records')
                        response["columns"] = list(result_df.columns)
                    else:
                        # For large results, provide summary
                        response["data"] = f"Large result with {len(result_df)} rows and {len(result_df.columns)} columns"
                        response["columns"] = list(result_df.columns)
                        response["sample_data"] = result_df.head(5).to_dict('records')
                        response["note"] = "Use .head() or .tail() in your expression to limit large results"

                return response

            except SyntaxError as e:
                return {
                    "success": False,
                    "error": f"Invalid pandas expression syntax: {e}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error executing pandas expression: {e}"
                }

        except Exception as e:
            logger.error(f"Error in execute_pandas_expression: {e}")
            return {
                "success": False,
                "error": f"Execute operation failed: {e}"
            }
