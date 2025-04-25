"""Tools Adapter - Helps transition from the old tools system to the new modular one."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union

# Import the new tool modules
from mcp_tools.command_executor import CommandExecutor
from mcp_tools.azrepo import AzureRepoClient
from mcp_tools.browser import BrowserClient
from mcp_tools.environment import env

# For backward compatibility with MCP types
from mcp.types import TextContent, Tool

logger = logging.getLogger(__name__)

class ToolsAdapter:
    """Adapter for transitioning from the old tools system to the new modular one."""
    
    def __init__(self):
        """Initialize the tools adapter with instances of the new tool modules."""
        self.command_executor = CommandExecutor()
        self.azure_repo_client = AzureRepoClient(self.command_executor)
        self.browser_client = BrowserClient()
        
        # Load environment
        env.load()
        
        # Store registered tools
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._tool_executors: Dict[str, Any] = {}
        
        # Initialize with default tools
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register the default tools that are part of the original implementation."""
        # This will be expanded with all the original tools
        # For now, just adding a few examples
        
        # Register command execution tools
        self._register_tool(
            name="execute_command",
            description="Execute a command",
            input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
            executor=self._execute_command
        )
        
        self._register_tool(
            name="execute_command_async",
            description="Start a command execution asynchronously and return a token for tracking",
            input_schema={"type": "object", "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "number", "nullable": True}
            }},
            executor=self._execute_command_async
        )
        
        # Register Azure repo tools
        self._register_tool(
            name="list_pull_requests",
            description="List pull requests in the Azure DevOps repository",
            input_schema={"type": "object", "properties": {
                "repository": {"type": "string", "nullable": True},
                "project": {"type": "string", "nullable": True},
                "organization": {"type": "string", "nullable": True},
                "status": {"type": "string", "nullable": True}
            }},
            executor=self._list_pull_requests
        )
        
        # Register browser tools
        self._register_tool(
            name="get_page_html",
            description="Open a webpage and get its HTML content",
            input_schema={"type": "object", "properties": {
                "url": {"type": "string"},
                "wait_time": {"type": "integer", "default": 30}
            }},
            executor=self._get_page_html
        )
    
    def _register_tool(self, name: str, description: str, input_schema: Dict[str, Any], executor: callable):
        """Register a tool with the adapter.
        
        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON Schema for the tool inputs
            executor: Async function that executes the tool logic
        """
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema
        }
        self._tool_executors[name] = executor
        logger.info(f"Registered tool: {name}")
    
    def get_tools(self) -> List[Tool]:
        """Get all registered tools.
        
        Returns:
            List of Tool objects
        """
        return [Tool(**tool_def) for tool_def in self._tools.values()]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Call a registered tool by name.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            List of TextContent objects with the tool result
        """
        if name not in self._tool_executors:
            return [TextContent(
                type="text",
                text=f"Error: Tool '{name}' not found."
            )]
        
        try:
            executor = self._tool_executors[name]
            result = await executor(arguments)
            return result
        except Exception as e:
            logger.exception(f"Error executing tool {name}")
            return [TextContent(
                type="text",
                text=f"Error executing tool {name}: {str(e)}"
            )]
    
    # Example tool executors that use the new modules:
    
    async def _execute_command(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute a command synchronously."""
        command = arguments.get('command', '')
        logger.info(f"Executing command: {command}")
        
        result = self.command_executor.execute(command)
        
        return [TextContent(
            type="text",
            text=f"Command result:\n{result.get('output', '')}"
        )]
    
    async def _execute_command_async(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Start a command execution asynchronously."""
        command = arguments.get('command', '')
        timeout = arguments.get('timeout')
        
        logger.info(f"Starting async command execution: {command}")
        result = await self.command_executor.execute_async(command, timeout)
        
        return [TextContent(
            type="text",
            text=f"Command started with token: {result.get('token')}\nStatus: {result.get('status')}\nPID: {result.get('pid')}"
        )]
    
    async def _list_pull_requests(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """List pull requests in the Azure DevOps repository."""
        repository = arguments.get('repository')
        project = arguments.get('project')
        organization = arguments.get('organization')
        status = arguments.get('status')
        
        result = await self.azure_repo_client.list_pull_requests(
            repository=repository,
            project=project,
            organization=organization,
            status=status
        )
        
        if not result.get('success', False):
            return [TextContent(
                type="text",
                text=f"Error listing pull requests: {result.get('error', 'Unknown error')}"
            )]
        
        # Format PR list
        prs = result.get('data', [])
        if not prs:
            return [TextContent(
                type="text",
                text="No pull requests found."
            )]
        
        formatted_prs = []
        for pr in prs:
            pr_line = f"PR #{pr.get('pullRequestId')}: {pr.get('title')} - Status: {pr.get('status')}"
            formatted_prs.append(pr_line)
        
        return [TextContent(
            type="text",
            text="Pull Requests:\n" + "\n".join(formatted_prs)
        )]
    
    async def _get_page_html(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Open a webpage and get its HTML content."""
        url = arguments.get('url', '')
        wait_time = arguments.get('wait_time', 30)
        
        html = self.browser_client.get_page_html(url, wait_time)
        
        if html:
            # Limit the size of the returned HTML to avoid overwhelming the response
            max_length = 10000
            if len(html) > max_length:
                html_excerpt = html[:max_length] + f"\n... (truncated, total length: {len(html)} characters)"
            else:
                html_excerpt = html
                
            return [TextContent(
                type="text",
                text=f"HTML content of {url}:\n{html_excerpt}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Error: Could not retrieve HTML from {url}"
            )] 