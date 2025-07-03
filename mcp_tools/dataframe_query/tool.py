"""DataFrame Query Tool for interactive data exploration.

This module provides a dedicated tool for querying and manipulating stored DataFrames
using their IDs. It supports operations like head, tail, sample, filter, describe, and info.
"""

import logging
import sys
import os
from typing import Any, Dict, List, Optional

from ..interfaces import ToolInterface
from ..plugin import register_tool

logger = logging.getLogger(__name__)


@register_tool()
class DataFrameQueryTool(ToolInterface):
    """A tool for querying stored DataFrames by ID.

    This tool enables users to perform various operations on DataFrames that have been
    stored in the DataFrame management framework by tools like Kusto, CSV import, etc.
    """

    @property
    def name(self) -> str:
        return "dataframe_query"

    @property
    def description(self) -> str:
        return (
            "Query and manipulate stored DataFrames by ID. "
            "Supports operations: head, tail, sample, filter, describe, info. "
            "Works with DataFrames stored by other tools like Kusto, CSV import, etc. "
            "Use this tool to explore large DataFrames without having to reload them."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "dataframe_id": {
                    "type": "string",
                    "description": "The ID of the stored DataFrame to query"
                },
                "operation": {
                    "type": "string",
                    "description": "The operation to perform on the DataFrame",
                    "enum": ["head", "tail", "sample", "filter", "describe", "info"]
                },
                "parameters": {
                    "type": "object",
                    "description": "Parameters for the operation (varies by operation)",
                    "properties": {
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
                        # For filter operation
                        "conditions": {
                            "type": "object",
                            "description": "Filter conditions as {column: condition} pairs",
                            "additionalProperties": {
                                "anyOf": [
                                    {"type": "string"},
                                    {"type": "number"},
                                    {"type": "boolean"},
                                    {
                                        "type": "object",
                                        "description": "Complex condition with operators",
                                        "properties": {
                                            "eq": {"description": "Equal to"},
                                            "ne": {"description": "Not equal to"},
                                            "gt": {"description": "Greater than"},
                                            "gte": {"description": "Greater than or equal"},
                                            "lt": {"description": "Less than"},
                                            "lte": {"description": "Less than or equal"},
                                            "in": {
                                                "type": "array",
                                                "description": "Value in list"
                                            },
                                            "contains": {
                                                "type": "string",
                                                "description": "String contains substring"
                                            },
                                            "startswith": {
                                                "type": "string",
                                                "description": "String starts with substring"
                                            },
                                            "endswith": {
                                                "type": "string",
                                                "description": "String ends with substring"
                                            }
                                        }
                                    }
                                ]
                            }
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
            "required": ["dataframe_id", "operation"],
            "additionalProperties": False
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a query operation on a stored DataFrame."""
        try:
            dataframe_id = arguments.get("dataframe_id")
            operation = arguments.get("operation")
            parameters = arguments.get("parameters", {})

            # Validate required arguments
            if not dataframe_id:
                return {
                    "success": False,
                    "error": "dataframe_id is required"
                }

            if not operation:
                return {
                    "success": False,
                    "error": "operation is required"
                }

            # Get DataFrame manager
            try:
                # Add project root directory to path to access utils
                # Go up three levels: tool.py -> dataframe_query -> mcp_tools -> project root
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
            logger.error(f"Unexpected error in DataFrame query tool: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {e}"
            }

    def _validate_operation_parameters(self, operation: str, parameters: Dict[str, Any]) -> Optional[str]:
        """Validate parameters for specific operations.

        Args:
            operation: The operation being performed
            parameters: The parameters provided

        Returns:
            Error message if validation fails, None if valid
        """
        if operation in ["head", "tail"]:
            n = parameters.get("n", 5)
            if not isinstance(n, int) or n < 1:
                return "Parameter 'n' must be a positive integer"

        elif operation == "sample":
            n = parameters.get("n")
            frac = parameters.get("frac")

            if n is not None and frac is not None:
                return "Cannot specify both 'n' and 'frac' for sample operation"

            if n is not None and (not isinstance(n, int) or n < 1):
                return "Parameter 'n' must be a positive integer"

            if frac is not None and (not isinstance(frac, (int, float)) or frac <= 0 or frac > 1):
                return "Parameter 'frac' must be a number between 0 and 1"

        elif operation == "filter":
            conditions = parameters.get("conditions")
            if not conditions or not isinstance(conditions, dict):
                return "Parameter 'conditions' is required and must be a dictionary for filter operation"

        elif operation == "describe":
            include = parameters.get("include")
            if include is not None:
                if not isinstance(include, (str, list)):
                    return "Parameter 'include' must be a string or list of strings"
                if isinstance(include, list) and not all(isinstance(item, str) for item in include):
                    return "All items in 'include' list must be strings"

        return None

    async def get_available_dataframes(self) -> Dict[str, Any]:
        """Get a list of available DataFrames that can be queried.

        Returns:
            Dictionary with success status and list of available DataFrames
        """
        try:
            # Add project root directory to path to access utils
            # Go up three levels: tool.py -> dataframe_query -> mcp_tools -> project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            from utils.dataframe_manager import get_dataframe_manager
            manager = get_dataframe_manager()
            await manager.start()

            dataframes = await manager.list_stored_dataframes()

            df_list = []
            for metadata in dataframes:
                df_list.append({
                    "id": metadata.df_id,
                    "created_at": metadata.created_at.isoformat(),
                    "shape": metadata.shape,
                    "memory_usage_mb": metadata.memory_usage / (1024 * 1024),
                    "dtypes": metadata.dtypes,
                    "tags": metadata.tags,
                    "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None
                })

            return {
                "success": True,
                "dataframes": df_list,
                "count": len(df_list)
            }

        except Exception as e:
            logger.error(f"Error listing available DataFrames: {e}")
            return {
                "success": False,
                "error": f"Failed to list DataFrames: {e}"
            }

    def get_operation_examples(self) -> Dict[str, Dict[str, Any]]:
        """Get example usage for each operation.

        Returns:
            Dictionary with examples for each supported operation
        """
        return {
            "head": {
                "description": "Get first n rows of the DataFrame",
                "example": {
                    "dataframe_id": "dataframe-abc123",
                    "operation": "head",
                    "parameters": {"n": 10}
                }
            },
            "tail": {
                "description": "Get last n rows of the DataFrame",
                "example": {
                    "dataframe_id": "dataframe-abc123",
                    "operation": "tail",
                    "parameters": {"n": 5}
                }
            },
            "sample": {
                "description": "Get random sample of rows from the DataFrame",
                "example": {
                    "dataframe_id": "dataframe-abc123",
                    "operation": "sample",
                    "parameters": {"n": 20, "random_state": 42}
                }
            },
            "filter": {
                "description": "Filter DataFrame rows based on conditions",
                "example": {
                    "dataframe_id": "dataframe-abc123",
                    "operation": "filter",
                    "parameters": {
                        "conditions": {
                            "age": {"gt": 30},
                            "status": "active",
                            "name": {"contains": "John"}
                        }
                    }
                }
            },
            "describe": {
                "description": "Generate descriptive statistics for the DataFrame",
                "example": {
                    "dataframe_id": "dataframe-abc123",
                    "operation": "describe",
                    "parameters": {"include": "all"}
                }
            },
            "info": {
                "description": "Get DataFrame info including column types and memory usage",
                "example": {
                    "dataframe_id": "dataframe-abc123",
                    "operation": "info"
                }
            }
        }
