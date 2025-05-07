"""
Azure Data Explorer (Kusto) client setup.
"""
import logging
import json
import re
import traceback
from typing import Dict, Any, Optional, Union, List

from azure.kusto.data import KustoClient as AzureKustoClient, KustoConnectionStringBuilder
from azure.kusto.data.exceptions import KustoServiceError
from azure.kusto.data.response import KustoResponseDataSet
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
    
    def format_results(self, response: KustoResponseDataSet) -> Dict[str, Any]:
        """
        Format the Kusto response using a simple approach that directly returns the primary results.
        
        Args:
            response: A KustoResponseDataSet object returned from query execution
            
        Returns:
            dict: A simplified dictionary with "success" and "result" keys
        """
        try:
            # Simply return the primary results directly
            if hasattr(response, 'primary_results') and response.primary_results:
                return {
                    "success": True,
                    "result": str(response.primary_results[0])
                }
            else:
                return {
                    "success": True,
                    "result": "No results found"
                }
        except Exception as e:
            self.logger.error(f"Error formatting results: {str(e)}")
            return {
                "success": False,
                "result": f"Error formatting results: {str(e)}",
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
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
            dict: The query results with either formatted output or raw response
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
                    "traceback": traceback.format_exc()
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
                "traceback": traceback.format_exc()
            }
        
        try:
            # Execute the query
            response = kusto_client.execute(database, query)
            
            # Return formatted results if requested
            if format_results:
                return self.format_results(response)
                
            # Otherwise return the original structure for programmatic access
            return {
                "success": True,
                "raw_response": response,
                "primary_results": response.primary_results,
                "tables": [table for table in response]
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
                "traceback": traceback.format_exc()
            }
        except Exception as e:
            error_msg = f"Error during query execution: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "result": error_msg,
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
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
            # Always format results for LLM when using execute_tool
            result = await self.execute_query(
                database=arguments.get("database"),
                query=arguments.get("query"),
                cluster=arguments.get("cluster"),
                format_results=True  # Always format results
            )
            return result
        else:
            return {
                "success": False,
                "result": f"Unknown operation: {operation}",
                "error_type": "InvalidOperation"
            } 