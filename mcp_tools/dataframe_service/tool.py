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
            "Data Frame Service - Load data from files/URLs and query DataFrames. "
            "Supports loading from local files or URLs, storing with IDs for later queries. "
            "Operations: load_data, head, tail, sample, query, describe, info. "
            "Use this tool to load data once and perform multiple operations efficiently."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform",
                    "enum": ["load_data", "head", "tail", "sample", "query", "describe", "info"]
                },
                "dataframe_id": {
                    "type": "string",
                    "description": "The ID of the stored DataFrame to query (not required for load_data)"
                },
                "parameters": {
                    "type": "object",
                    "description": "Parameters for the operation (varies by operation)",
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
                        # For head and tail operations
                        "n": {
                            "type": "integer",
                            "description": "Number of rows to return (for head, tail)",
                            "minimum": 1,
                            "default": 5
                        },
                        # For sample operation
                        "frac": {
                            "type": "number",
                            "description": "Fraction of rows to sample (for sample)",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "random_state": {
                            "type": "integer",
                            "description": "Random seed for sampling (for sample)"
                        },
                        # For query operation
                        "expr": {
                            "type": "string",
                            "description": "Query expression using pandas query syntax (e.g., 'age > 30 and status == \"active\"')"
                        },
                        # For describe operation
                        "include": {
                            "anyOf": [
                                {"type": "string"},
                                {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            ],
                            "description": "Data types to include in describe (e.g., 'all', ['number'], etc.)"
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

            # For other operations, dataframe_id is required
            if not dataframe_id:
                return {
                    "success": False,
                    "error": "dataframe_id is required for non-load operations"
                }

            # Get DataFrame manager
            try:
                # Add project root directory to path to access utils
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

            # Check if DataFrame exists
            df = await manager.get_dataframe(dataframe_id)
            if df is None:
                return {
                    "success": False,
                    "error": f"DataFrame with ID '{dataframe_id}' not found or expired"
                }

            # Execute the requested operation
            try:
                result = await manager.query_dataframe(
                    df_id=dataframe_id,
                    operation=operation,
                    parameters=parameters
                )

                if result is None:
                    return {
                        "success": False,
                        "error": f"Failed to execute {operation} operation on DataFrame {dataframe_id}"
                    }

                # Format the response
                response = {
                    "success": True,
                    "dataframe_id": dataframe_id,
                    "operation": result.operation,
                    "parameters": result.parameters,
                    "result_shape": result.data.shape,
                    "execution_time_ms": result.execution_time_ms,
                    "metadata": result.metadata
                }

                # Convert result DataFrame to appropriate format
                if result.data.empty:
                    response["data"] = "No data returned (empty result)"
                else:
                    # For small results, include the actual data
                    if len(result.data) <= 100:  # Arbitrary limit for direct display
                        response["data"] = result.data.to_dict('records')
                        response["columns"] = list(result.data.columns)
                    else:
                        # For large results, provide summary and suggest chunking
                        response["data"] = f"Large result with {len(result.data)} rows and {len(result.data.columns)} columns"
                        response["columns"] = list(result.data.columns)
                        response["sample_data"] = result.data.head(5).to_dict('records')
                        response["note"] = "Use smaller parameters or 'head'/'tail' operations for large results"

                return response

            except ValueError as e:
                return {
                    "success": False,
                    "error": f"Invalid operation parameters: {e}"
                }
            except Exception as e:
                logger.error(f"Error executing {operation} on DataFrame {dataframe_id}: {e}")
                return {
                    "success": False,
                    "error": f"Operation failed: {e}"
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
