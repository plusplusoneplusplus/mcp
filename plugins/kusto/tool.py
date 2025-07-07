"""Azure Data Explorer (Kusto) tool implementation."""

import logging
import json
import re
import traceback
from typing import Dict, Any, Optional, Union, List
import pandas as pd
import numpy as np

from azure.kusto.data import (
    KustoClient as AzureKustoClient,
    KustoConnectionStringBuilder,
)
from azure.kusto.data.exceptions import KustoServiceError
from azure.kusto.data.response import KustoResponseDataSet
from azure.identity import DefaultAzureCredential

# Import the required interfaces and decorators
from mcp_tools.interfaces import ToolInterface, KustoClientInterface
from mcp_tools.plugin import register_tool
from config import env
from utils.output_processor.output_limiter import OutputLimiter
from utils.dataframe_manager import get_dataframe_manager


@register_tool(ecosystem="microsoft", os_type="all")
class KustoClient(KustoClientInterface):
    """Client for interacting with Azure Data Explorer (Kusto).

    This class provides methods to execute queries against Kusto databases
    by setting up authenticated connections to Azure Data Explorer clusters.

    Example:
        # Initialize the client
        kusto_client = KustoClient()

        # Execute a query
        result = await kusto_client.execute_query("MyDatabase", "MyTable | limit 10")

        # The result contains a formatted string representation of the query results
        print(result["result"])
    """

    # Implement ToolInterface properties
    @property
    def name(self) -> str:
        """Get the tool name."""
        return "kusto_client"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Execute queries against Azure Data Explorer (Kusto) databases"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform (execute_query)",
                    "enum": ["execute_query"],
                },
                "database": {
                    "type": "string",
                    "description": "The name of the database to query. When specified, 'cluster' must also be provided.",
                },
                "query": {
                    "type": "string",
                    "description": "The KQL query to execute",
                },
                "cluster": {
                    "type": "string",
                    "description": "The URL or name of the Kusto cluster. When specified, 'database' must also be provided. Can be a full URL (https://cluster.kusto.windows.net), partial URL (cluster.kusto.windows.net), or just the cluster name (cluster).",
                },
                "format_results": {
                    "type": "boolean",
                    "description": "Whether to format the results for LLM analysis using smart DataFrame formatting",
                    "default": True,
                },
                "formatting_options": {
                    "type": "object",
                    "description": "Configuration for DataFrame formatting behavior",
                    "properties": {
                        "force_dataframe": {
                            "type": "boolean",
                            "description": "Force DataFrame conversion even if it fails initially",
                            "default": True
                        },
                        "max_column_width": {
                            "type": "integer",
                            "description": "Maximum column width for display (characters)",
                            "default": 50
                        },
                        "show_memory_usage": {
                            "type": "boolean",
                            "description": "Show memory usage for large datasets",
                            "default": True
                        }
                    }
                },
                "output_limits": {
                    "type": "object",
                    "description": "Configuration for output size limits and truncation",
                    "properties": {
                        "max_total_length": {
                            "type": "integer",
                            "description": "Maximum total output length in bytes (default: 50KB)",
                            "default": 51200
                        },
                        "truncate_strategy": {
                            "type": "string",
                            "description": "Truncation strategy: 'start', 'end', 'middle', or 'smart'",
                            "enum": ["start", "end", "middle", "smart"],
                            "default": "smart"
                        },
                        "preserve_raw": {
                            "type": "boolean",
                            "description": "Whether to preserve raw output in metadata",
                            "default": False
                        }
                    }
                },
            },
            "required": ["operation", "query"],
            "anyOf": [
                {
                    "description": "Use environment configuration for database and cluster",
                    "not": {
                        "anyOf": [
                            {"required": ["database"]},
                            {"required": ["cluster"]}
                        ]
                    }
                },
                {
                    "description": "Specify both database and cluster explicitly",
                    "required": ["database", "cluster"]
                }
            ]
        }

    def __init__(self, config_dict=None):
        """Initialize the KustoClient.

        Args:
            config_dict (dict, optional): Configuration dictionary. If None, uses the default config.
        """
        self.config = config_dict
        self.logger = logging.getLogger(__name__)
        self.output_limiter = OutputLimiter()

        # Default output limits configuration (50KB max as specified in issue)
        self.default_output_limits = {
            "max_total_length": 50 * 1024,  # 50KB
            "truncate_strategy": "smart",
            "truncate_message": "\n... (output truncated due to size limit)",
            "preserve_first_lines": 10,
            "preserve_last_lines": 20,
            "preserve_raw": False  # Set to True if raw data access is needed
        }

    def normalize_cluster_url(self, cluster: Optional[str]) -> Optional[str]:
        """
        Normalize a cluster name or URL to a fully qualified Kusto cluster URL.

        This method handles different formats of cluster input:
        - Full URL (https://cluster.kusto.windows.net)
        - Partial URL (cluster.kusto.windows.net)
        - Cluster name only (cluster)

        Args:
            cluster (str, optional): Cluster name or URL to normalize

        Returns:
            str or None: Fully qualified Kusto cluster URL or None if no cluster provided
        """
        if not cluster:
            # If no cluster provided, return None
            return None

        # If it already has a protocol, assume it's a complete URL
        if cluster.startswith(("http://", "https://")):
            return cluster

        # Check if it's a domain name with dots and ends with kusto.windows.net
        if "." in cluster and cluster.endswith("kusto.windows.net"):
            # It's a domain without protocol, add https://
            return f"https://{cluster}"

        # It's just a cluster name or partial domain, expand to full URL
        return f"https://{cluster}.kusto.windows.net"

    def get_kusto_client(self, cluster=None) -> AzureKustoClient:
        """
        Initialize and return a Kusto client for Azure Data Explorer.

        Args:
            cluster (str, optional): The name or URL of the Kusto cluster. If None, uses the one from config.

        Returns:
            AzureKustoClient: A configured Kusto client
        """
        # Use the provided cluster or get from environment
        raw_cluster = cluster or env.get_kusto_parameter("cluster_url")

        # Normalize the cluster to a fully qualified URL
        cluster_url = self.normalize_cluster_url(raw_cluster)

        # Make sure we have a cluster URL
        if not cluster_url:
            raise ValueError(
                "Kusto cluster URL not found in configuration. "
                "Please make sure KUSTO_CLUSTER_URL is set in your .env file."
            )

        auth_methods_tried = []

        # Try authentication methods in order of preference

        # 1. App registration (service principal) if all required credentials are provided
        app_id = env.get_kusto_parameter("app_id")
        app_key = env.get_kusto_parameter("app_key")
        tenant_id = env.get_kusto_parameter("tenant_id")

        if app_id and app_key and tenant_id:
            try:
                auth_methods_tried.append("Service Principal (App Registration)")
                kcsb = KustoConnectionStringBuilder.with_aad_application_key_authentication(
                    cluster_url=cluster_url,
                    aad_app_id=app_id,
                    app_key=app_key,
                    authority_id=tenant_id,
                )
                return AzureKustoClient(kcsb)
            except Exception as e:
                # Log the error but try other methods
                auth_error = f"Service Principal authentication failed: {str(e)}"
                self.logger.warning(auth_error)

        # 2. DefaultAzureCredential - tries multiple authentication methods
        try:
            auth_methods_tried.append("DefaultAzureCredential")
            # Create a DefaultAzureCredential object
            default_credential = DefaultAzureCredential()
            kcsb = KustoConnectionStringBuilder.with_az_cli_authentication(cluster_url)
            # Modify the connection string to use token provider
            kcsb.federated_security = True
            kcsb.fed_client_id = None  # Will use default
            return AzureKustoClient(kcsb)
        except Exception as e:
            # Log the error but try other methods
            auth_error = f"DefaultAzureCredential authentication failed: {str(e)}"
            self.logger.warning(auth_error)

        # 3. Azure CLI authentication as a fallback
        try:
            auth_methods_tried.append("Azure CLI")
            kcsb = KustoConnectionStringBuilder.with_az_cli_authentication(cluster_url)
            return AzureKustoClient(kcsb)
        except Exception as e:
            # Last resort failed
            auth_error = f"Azure CLI authentication failed: {str(e)}"
            self.logger.error(auth_error)

        raise ValueError(
            f"All authentication methods failed ({', '.join(auth_methods_tried)}). "
            f"Last error: {auth_error}\n"
            f"Please make sure you have appropriate Azure credentials configured. "
            f"You can set KUSTO_APP_ID, KUSTO_APP_KEY, and KUSTO_TENANT_ID in your .env file "
            f"or use az login to authenticate with Azure CLI."
        )

    def _kusto_response_to_dataframe(self, response: KustoResponseDataSet) -> Optional[pd.DataFrame]:
        """
        Convert Kusto response to pandas DataFrame.

        Args:
            response: KustoResponseDataSet object

        Returns:
            pandas DataFrame or None if conversion fails
        """
        try:
            if not hasattr(response, "primary_results") or not response.primary_results:
                return None

            primary_result = response.primary_results[0]

            # Extract column names
            columns = [col.column_name for col in primary_result.columns]

            # Extract data rows
            data = []
            for row in primary_result:
                data.append([row[i] for i in range(len(columns))])

            # Create DataFrame
            df = pd.DataFrame(data, columns=columns)
            return df

        except Exception as e:
            self.logger.warning(f"Failed to convert Kusto response to DataFrame: {str(e)}")
            return None

    def _format_dataframe_smart(self, df: pd.DataFrame) -> str:
        """
        Apply smart formatting strategies based on DataFrame size.

        Args:
            df: pandas DataFrame to format

        Returns:
            Formatted string representation
        """
        row_count = len(df)

        # Strategy 1: Small datasets (≤20 rows) - Show full table
        if row_count <= 20:
            return self._format_small_dataframe(df)

        # Strategy 2: Medium datasets (≤1000 rows) - Show summary + sample
        elif row_count <= 1000:
            return self._format_medium_dataframe(df)

        # Strategy 3: Large datasets (>1000 rows) - Show summary + head/tail
        else:
            return self._format_large_dataframe(df)

    def _format_small_dataframe(self, df: pd.DataFrame) -> str:
        """Format small DataFrames (≤20 rows) by showing the full table."""
        output = []
        output.append(f"Query Results ({len(df)} rows, {len(df.columns)} columns)")
        output.append("=" * 50)

        # Get max column width from formatting options
        max_col_width = getattr(self, '_current_formatting_options', {}).get('max_column_width', 50)
        output.append(df.to_string(index=False, max_colwidth=max_col_width))
        return "\n".join(output)

    def _format_medium_dataframe(self, df: pd.DataFrame) -> str:
        """Format medium DataFrames (21-1000 rows) with summary and sample."""
        output = []
        output.append(f"Query Results Summary ({len(df)} rows, {len(df.columns)} columns)")
        output.append("=" * 50)

        # Dataset summary
        output.append("\nDataset Overview:")
        output.append(f"• Total rows: {len(df)}")
        output.append(f"• Total columns: {len(df.columns)}")

        # Column information
        output.append("\nColumn Information:")
        for col in df.columns:
            dtype = str(df[col].dtype)
            null_count = df[col].isnull().sum()
            unique_count = df[col].nunique()
            output.append(f"• {col}: {dtype} ({unique_count} unique, {null_count} nulls)")

        # Sample data (first 10 rows)
        max_col_width = getattr(self, '_current_formatting_options', {}).get('max_column_width', 40)
        output.append(f"\nSample Data (first 10 rows):")
        output.append(df.head(10).to_string(index=False, max_colwidth=max_col_width))

        # If more than 10 rows, show summary statistics for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            output.append(f"\nNumeric Summary:")
            output.append(df[numeric_cols].describe().to_string(max_colwidth=20))

        return "\n".join(output)

    def _format_large_dataframe(self, df: pd.DataFrame) -> str:
        """Format large DataFrames (>1000 rows) with summary, head, and tail."""
        output = []
        output.append(f"Large Dataset Summary ({len(df)} rows, {len(df.columns)} columns)")
        output.append("=" * 50)

        # Dataset summary
        output.append("\nDataset Overview:")
        output.append(f"• Total rows: {len(df):,}")
        output.append(f"• Total columns: {len(df.columns)}")

        # Show memory usage if requested
        formatting_options = getattr(self, '_current_formatting_options', {})
        if formatting_options.get('show_memory_usage', True):
            output.append(f"• Memory usage: ~{df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")

        # Column information with data ranges
        output.append("\nColumn Information:")
        for col in df.columns:
            dtype = str(df[col].dtype)
            null_count = df[col].isnull().sum()
            unique_count = df[col].nunique()

            # Add data range for numeric columns
            if pd.api.types.is_numeric_dtype(df[col]):
                min_val = df[col].min()
                max_val = df[col].max()
                range_info = f", range: {min_val} to {max_val}"
            else:
                range_info = ""

            output.append(f"• {col}: {dtype} ({unique_count:,} unique, {null_count:,} nulls{range_info})")

        # First 5 rows
        max_col_width = formatting_options.get('max_column_width', 30)
        output.append(f"\nFirst 5 rows:")
        output.append(df.head(5).to_string(index=False, max_colwidth=max_col_width))

        # Last 5 rows
        output.append(f"\nLast 5 rows:")
        output.append(df.tail(5).to_string(index=False, max_colwidth=max_col_width))

        # Summary statistics for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            output.append(f"\nNumeric Summary (top 5 columns):")
            output.append(df[numeric_cols[:5]].describe().to_string(max_colwidth=15))

        return "\n".join(output)

    async def _should_store_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Determine if a DataFrame should be stored based on configuration and size.

        Args:
            df: DataFrame to evaluate

        Returns:
            bool: True if DataFrame should be stored, False otherwise
        """
        # Check if DataFrame storage is enabled
        if not env.get_setting("kusto_dataframe_storage_enabled", True):
            return False

        # Get size threshold from configuration
        threshold_mb = env.get_setting("kusto_dataframe_threshold_mb", 10)

        # Calculate DataFrame memory usage in MB
        memory_usage_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

        return memory_usage_mb > threshold_mb

    async def _store_large_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Store a large DataFrame and return metadata.

        Args:
            df: DataFrame to store

        Returns:
            dict: Storage result with DataFrame ID and metadata
        """
        try:
            # Get DataFrame manager
            df_manager = get_dataframe_manager()

            # Store DataFrame with appropriate tags
            df_id = await df_manager.store_dataframe(
                df=df,
                ttl_seconds=env.get_setting("dataframe_default_ttl_seconds", 3600),
                tags={
                    "source": "kusto",
                    "tool": "kusto_client",
                    "auto_stored": True
                }
            )

            # Generate summary if enabled
            summary = None
            if env.get_setting("kusto_dataframe_auto_summarize", True):
                # Use a reasonable size limit for summary (5KB)
                summary = await df_manager.summarize_dataframe(
                    df_id=df_id,
                    max_size_bytes=5 * 1024,
                    include_sample=True
                )

            return {
                "stored": True,
                "df_id": df_id,
                "summary": summary,
                "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
                "available_operations": [
                    "head", "tail", "sample", "describe", "info", "filter"
                ],
                "query_examples": [
                    f'Use the DataFrame Query Tool with dataframe_id="{df_id}" and operation="head" to see the first rows',
                    f'Use operation="describe" to get statistical summary',
                    f'Use operation="filter" with conditions to filter the data'
                ]
            }

        except Exception as e:
            self.logger.error(f"Failed to store DataFrame: {str(e)}")
            return {
                "stored": False,
                "error": str(e),
                "fallback_reason": "DataFrame storage failed"
            }

    async def format_results(self, response: KustoResponseDataSet, output_limits: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Format the Kusto response with smart DataFrame formatting, intelligent output limiting, and DataFrame storage.

        Args:
            response: A KustoResponseDataSet object returned from query execution
            output_limits: Optional configuration for output limits and truncation

        Returns:
            dict: A dictionary with "success", "result", and optional metadata keys
        """
        try:
            # Use provided limits or defaults
            limits = output_limits or self.default_output_limits

            # Try to convert to DataFrame first for smart formatting
            df = self._kusto_response_to_dataframe(response)

            if df is not None:
                # Check if DataFrame should be stored due to size
                should_store = await self._should_store_dataframe(df)

                if should_store:
                    # Store the DataFrame and return enhanced metadata
                    storage_result = await self._store_large_dataframe(df)

                    if storage_result.get("stored", False):
                        # DataFrame was successfully stored, return summary with ID
                        summary_text = ""

                        if storage_result.get("summary"):
                            summary_text = storage_result["summary"].get("formatted_summary", "")

                        # If no summary or summary is too small, generate a basic one
                        if not summary_text or len(summary_text) < 200:
                            summary_text = self._format_dataframe_smart(df.head(10))

                        return {
                            "success": True,
                            "result": f"""Large Dataset Stored for Interactive Query

DataFrame ID: {storage_result['df_id']}
Memory Usage: {storage_result['memory_usage_mb']:.2f} MB
Rows: {len(df):,}, Columns: {len(df.columns)}

{summary_text}

🔍 Next Steps:
{chr(10).join(['• ' + example for example in storage_result['query_examples']])}

Available Operations: {', '.join(storage_result['available_operations'])}""",
                            "metadata": {
                                "formatting": "stored_dataframe",
                                "dataframe_id": storage_result['df_id'],
                                "rows": len(df),
                                "columns": len(df.columns),
                                "memory_usage_mb": storage_result['memory_usage_mb'],
                                "stored": True,
                                "available_operations": storage_result['available_operations'],
                                "query_examples": storage_result['query_examples'],
                                "summary_included": bool(storage_result.get("summary"))
                            }
                        }
                    else:
                        # Storage failed, fall back to regular formatting with truncation if needed
                        self.logger.warning(f"DataFrame storage failed: {storage_result.get('error', 'Unknown error')}")

                # Regular formatting for small DataFrames or when storage fails
                formatted_result = self._format_dataframe_smart(df)

                # Check if output limiting is needed
                max_length = limits.get("max_total_length", 50 * 1024)
                if isinstance(max_length, str):
                    max_length = int(max_length)
                if len(formatted_result) <= max_length:
                    # Result is within limits, return formatted DataFrame
                    return {
                        "success": True,
                        "result": formatted_result,
                        "metadata": {
                            "formatting": "smart_dataframe",
                            "rows": len(df),
                            "columns": len(df.columns),
                            "strategy": self._get_formatting_strategy(len(df)),
                            "dataframe_storage_attempted": should_store,
                            "dataframe_storage_enabled": env.get_setting("kusto_dataframe_storage_enabled", True)
                        }
                    }
                else:
                    # Apply output limits to the formatted DataFrame result
                    mock_result = {"output": formatted_result, "error": ""}
                    limited_result = self.output_limiter.apply_output_limits(mock_result, limits)

                    return {
                        "success": True,
                        "result": limited_result["output"],
                        "metadata": {
                            "formatting": "smart_dataframe",
                            "rows": len(df),
                            "columns": len(df.columns),
                            "strategy": self._get_formatting_strategy(len(df)),
                            "truncated": True,
                            "original_size": len(formatted_result),
                            "truncated_size": len(limited_result["output"]),
                            "truncation_strategy": limits.get("truncate_strategy", "smart"),
                            "size_reduction": f"{((len(formatted_result) - len(limited_result['output'])) / len(formatted_result) * 100):.1f}%",
                            "dataframe_storage_attempted": should_store,
                            "dataframe_storage_enabled": env.get_setting("kusto_dataframe_storage_enabled", True)
                        }
                    }
            else:
                # Fallback to raw string formatting if DataFrame conversion fails
                if hasattr(response, "primary_results") and response.primary_results:
                    raw_result = str(response.primary_results[0])
                else:
                    raw_result = "No results found"

                # Check if output limiting is needed
                max_length = limits.get("max_total_length", 50 * 1024)
                if isinstance(max_length, str):
                    max_length = int(max_length)
                if len(raw_result) <= max_length:
                    # Result is within limits, return as-is
                    return {"success": True, "result": raw_result}

                # Apply output limits using the OutputLimiter
                mock_result = {"output": raw_result, "error": ""}
                limited_result = self.output_limiter.apply_output_limits(mock_result, limits)

                # Build response with metadata about truncation
                response_dict = {
                    "success": True,
                    "result": limited_result["output"],
                    "metadata": {
                        "formatting": "raw_fallback",
                        "truncated": True,
                        "original_size": len(raw_result),
                        "truncated_size": len(limited_result["output"]),
                        "truncation_strategy": limits.get("truncate_strategy", "smart"),
                        "size_reduction": f"{((len(raw_result) - len(limited_result['output'])) / len(raw_result) * 100):.1f}%"
                    }
                }

                # Include raw output if requested
                if limits.get("preserve_raw", False):
                    response_dict["raw_result"] = raw_result

                return response_dict

        except Exception as e:
            self.logger.error(f"Error formatting results: {str(e)}")
            return {
                "success": False,
                "result": f"Error formatting results: {str(e)}",
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
            }

    def _get_formatting_strategy(self, row_count: int) -> str:
        """Get the formatting strategy name based on row count."""
        if row_count <= 20:
            return "small_full_table"
        elif row_count <= 1000:
            return "medium_summary_sample"
        else:
            return "large_summary_head_tail"

    async def execute_query(
        self,
        database: str,
        query: str,
        client: Optional[AzureKustoClient] = None,
        cluster: Optional[str] = None,
        format_results: bool = True,
        formatting_options: Optional[Dict[str, Any]] = None,
        output_limits: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a Kusto query and return the results.

        Args:
            database (str): The name of the database to query
            query (str): The KQL query to execute
            client (AzureKustoClient, optional): An existing Kusto client to use
            cluster (str, optional): The name or URL of the Kusto cluster to connect to
            format_results (bool, optional): Whether to format the results using smart DataFrame formatting. Default is True.
            formatting_options (Dict[str, Any], optional): Configuration for DataFrame formatting behavior
            output_limits (Dict[str, Any], optional): Configuration for output size limits and truncation

        Returns:
            dict: The query results with either smart DataFrame formatted output or raw response
        """
        # Validate database
        if not database:
            # Try to get database from environment if not specified
            database = env.get_kusto_parameter("database")
            if not database:
                error_msg = "No database specified. Please provide a database name."
                self.logger.error(error_msg)
                return {
                    "success": False,
                    "result": error_msg,
                    "error_type": "ValueError",
                    "traceback": traceback.format_exc(),
                }

        # Use provided client or create a new one
        try:
            kusto_client = client or self.get_kusto_client(cluster)
        except Exception as e:
            error_msg = f"Failed to create Kusto client: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "result": error_msg,
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
            }

        try:
            # Execute the query
            response = kusto_client.execute(database, query)

            # Return formatted results if requested
            if format_results:
                # Store formatting options in the instance for use by format_results
                if formatting_options:
                    self._current_formatting_options = formatting_options
                return await self.format_results(response, output_limits)

            # Otherwise return the original structure for programmatic access
            return {
                "success": True,
                "raw_response": response,
                "primary_results": response.primary_results,
                "tables": [table for table in response],
            }
        except KustoServiceError as e:
            error_msg = f"Query execution failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "result": error_msg,
                "error_type": "KustoServiceError",
                "error_code": getattr(e, "error_code", None),
                "error_category": getattr(e, "error_category", None),
                "traceback": traceback.format_exc(),
            }
        except Exception as e:
            error_msg = f"Error during query execution: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "result": error_msg,
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
            }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments.

        Args:
            arguments: Dictionary of arguments for the tool

        Returns:
            Tool execution result with formatted output
        """
        operation = arguments.get("operation", "")

        if operation == "execute_query":
            # Validate required arguments
            database = arguments.get("database")
            query = arguments.get("query")

            if not query:
                return {
                    "success": False,
                    "result": "Query parameter is required",
                    "error_type": "ValueError",
                }

            # Always format results for LLM when using execute_tool
            result = await self.execute_query(
                database=database or "",
                query=query,
                cluster=arguments.get("cluster"),
                format_results=arguments.get("format_results", True),
                formatting_options=arguments.get("formatting_options"),
                output_limits=arguments.get("output_limits"),
            )
            return result
        else:
            return {
                "success": False,
                "result": f"Unknown operation: {operation}",
                "error_type": "InvalidOperation",
            }
