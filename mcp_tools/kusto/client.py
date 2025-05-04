"""
Azure Data Explorer (Kusto) client setup.
"""
import logging
import json
import re
from typing import Dict, Any, Optional, Union, List

from azure.kusto.data import KustoClient as AzureKustoClient, KustoConnectionStringBuilder
from azure.kusto.data.exceptions import KustoServiceError
from azure.identity import DefaultAzureCredential

# Import interface
from mcp_tools.interfaces import KustoClientInterface
# Import the plugin decorator
from mcp_tools.plugin import register_tool
from config import env

@register_tool
class KustoClient(KustoClientInterface):
    """Client for interacting with Azure Data Explorer (Kusto).
    
    This class provides methods to execute queries against Kusto databases
    by setting up authenticated connections to Azure Data Explorer clusters.
    
    Example:
        # Initialize the client
        kusto_client = KustoClient()
        
        # Execute a query
        result = await kusto_client.execute_query("MyDatabase", "MyTable | limit 10")
        
        # Get the primary results
        primary_results = result.get("primary_results", [])
        
        # Get formatted results for LLM analysis
        formatted_results = kusto_client.format_results(result)
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
                    "enum": ["execute_query"]
                },
                "database": {
                    "type": "string",
                    "description": "The name of the database to query",
                },
                "query": {
                    "type": "string",
                    "description": "The KQL query to execute",
                },
                "cluster": {
                    "type": "string",
                    "description": "The URL or name of the Kusto cluster",
                    "nullable": True
                },
                "format_results": {
                    "type": "boolean",
                    "description": "Whether to format the results for LLM analysis",
                    "default": True
                }
            },
            "required": ["operation", "database", "query"]
        }
        
    def __init__(self, config_dict=None):
        """Initialize the KustoClient.
        
        Args:
            config_dict (dict, optional): Configuration dictionary. If None, uses the default config.
        """
        self.config = config_dict
        self.logger = logging.getLogger(__name__)
    
    def normalize_cluster_url(self, cluster: Optional[str]) -> str:
        """
        Normalize a cluster name or URL to a fully qualified Kusto cluster URL.
        
        This method handles different formats of cluster input:
        - Full URL (https://cluster.kusto.windows.net)
        - Partial URL (cluster.kusto.windows.net)
        - Cluster name only (cluster)
        
        Args:
            cluster (str, optional): Cluster name or URL to normalize
        
        Returns:
            str: Fully qualified Kusto cluster URL
        """
        if not cluster:
            # If no cluster provided, return None
            return None
            
        # If it already has a protocol, assume it's a complete URL
        if cluster.startswith(('http://', 'https://')):
            return cluster
            
        # Check if it's a domain name with dots and ends with kusto.windows.net
        if '.' in cluster and cluster.endswith('kusto.windows.net'):
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
            raise ValueError("Kusto cluster URL not found in configuration. "
                            "Please make sure KUSTO_CLUSTER_URL is set in your .env file.")
        
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
                    authority_id=tenant_id
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
        
        # If we reached here, all authentication methods failed
        raise ValueError(f"All authentication methods failed ({', '.join(auth_methods_tried)}). "
                        f"Last error: {auth_error}\n"
                        f"Please make sure you have appropriate Azure credentials configured. "
                        f"You can set KUSTO_APP_ID, KUSTO_APP_KEY, and KUSTO_TENANT_ID in your .env file "
                        f"or use az login to authenticate with Azure CLI.")
    
    def format_results(self, result: Dict[str, Any], max_rows: int = 50) -> Dict[str, Any]:
        """
        Format the query results into a human-readable string suitable for LLM analysis.
        Also simplify the return structure to just include success and result.
        
        Args:
            result (dict): The query result dictionary returned by execute_query
            max_rows (int, optional): Maximum number of rows to include. Defaults to 50.
            
        Returns:
            dict: A simplified dictionary with just "success" and "result" keys
        """
        if not result.get("success", False):
            return {
                "success": False,
                "result": f"Error: {result.get('error', 'Unknown error')}"
            }
            
        output_parts = []
        
        # Format all tables from the response
        if "tables" in result:
            for table_idx, table in enumerate(result["tables"]):
                output_parts.append(f"Table {table_idx + 1}:")
                
                # Get columns information
                if hasattr(table, "columns_name"):
                    columns = table.columns_name
                    column_types = table.columns_type if hasattr(table, "columns_type") else [""] * len(columns)
                    
                    # Add column headers with types
                    header = " | ".join([f"{col} ({col_type})" for col, col_type in zip(columns, column_types)])
                    output_parts.append(header)
                    output_parts.append("-" * len(header))
                    
                    # Add row data
                    row_count = 0
                    for row in table.rows:
                        if row_count >= max_rows:
                            output_parts.append(f"... {len(table.rows) - max_rows} more rows (showing first {max_rows} of {len(table.rows)} total)")
                            break
                            
                        # Format row values, handling different data types appropriately
                        formatted_values = []
                        for val in row:
                            if isinstance(val, (dict, list)):
                                try:
                                    formatted_values.append(json.dumps(val, ensure_ascii=False)[:100])
                                except:
                                    formatted_values.append(str(val)[:100])
                            elif val is None:
                                formatted_values.append("NULL")
                            else:
                                formatted_values.append(str(val)[:100])
                                
                        output_parts.append(" | ".join(formatted_values))
                        row_count += 1
                        
                output_parts.append("\n") # Add spacing between tables
        
        # Add summary information
        if "tables" in result and result["tables"]:
            total_tables = len(result["tables"])
            total_rows = sum(len(table.rows) if hasattr(table, "rows") else 0 for table in result["tables"])
            output_parts.append(f"Summary: {total_tables} table(s), {total_rows} total row(s)")
        
        # Return simplified output with just success and result
        return {
            "success": True,
            "result": "\n".join(output_parts)
        }
    
    async def execute_query(
        self,
        database: str,
        query: str,
        client: Optional[AzureKustoClient] = None,
        cluster: Optional[str] = None,
        format_results: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a Kusto query and return the results.
        
        Args:
            database (str): The name of the database to query
            query (str): The KQL query to execute
            client (AzureKustoClient, optional): An existing Kusto client to use
            cluster (str, optional): The name or URL of the Kusto cluster to connect to
            format_results (bool, optional): Whether to format the results for LLM analysis. Default is True.
            
        Returns:
            dict: The query results
        """
        # Validate database
        if not database:
            # Try to get database from environment if not specified
            database = env.get_kusto_parameter("database")
            if not database:
                raise ValueError("No database specified. Please provide a database name.")
        
        # Use provided client or create a new one
        try:
            kusto_client = client or self.get_kusto_client(cluster)
        except Exception as e:
            self.logger.error(f"Failed to create Kusto client: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create Kusto client: {str(e)}"
            }
        
        try:
            response = kusto_client.execute(database, query)
            # Extract the primary results table
            result = {
                "success": True,
                "raw_response": response,
                "primary_results": response.primary_results,
                "tables": [table for table in response]
            }
            
            # Return formatted results if requested
            if format_results:
                return self.format_results(result)
                
            return result
        except KustoServiceError as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            return {
                "success": False,
                "error": f"Query execution failed: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Error during query execution: {str(e)}")
            return {
                "success": False,
                "error": f"Error during query execution: {str(e)}"
            }
    
    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments.
        
        Args:
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Tool execution result
        """
        operation = arguments.get("operation", "")
        
        if operation == "execute_query":
            # Always format results for LLM when using execute_tool
            return await self.execute_query(
                database=arguments.get("database"),
                query=arguments.get("query"),
                cluster=arguments.get("cluster"),
                format_results=True  # Always format results
            )
        else:
            return {
                "success": False,
                "result": f"Unknown operation: {operation}"
            } 