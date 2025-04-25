"""Tools Adapter - Helps transition from the old tools system to the new modular one."""

import asyncio
import logging
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Type

# Import interfaces
from mcp_tools.interfaces import (
    ToolInterface,
    CommandExecutorInterface,
    RepoClientInterface,
    BrowserClientInterface,
    EnvironmentManagerInterface,
)

# Import plugin system
from mcp_tools.plugin import registry, discover_and_register_tools
# Import dependency injector
from mcp_tools.dependency import injector

# Use local types instead of mcp.types
from mcp_core.types import TextContent, Tool

logger = logging.getLogger(__name__)

class ToolsAdapter:
    """Adapter for transitioning from the old tools system to the new modular one."""
    
    def __init__(self):
        """Initialize the tools adapter with instances of the new tool modules."""
        # Discover and register all available tools
        discover_and_register_tools()
        
        # Resolve all dependencies
        injector.resolve_all_dependencies()
        
        # Get tool instances from the dependency injector
        self.command_executor = injector.get_tool_instance("command_executor")
        self.azure_repo_client = injector.get_tool_instance("azure_repo_client")
        self.browser_client = injector.get_tool_instance("browser_client")
        self.environment_manager = injector.get_tool_instance("environment_manager")
        
        # Load environment
        if self.environment_manager:
            self.environment_manager.load()
        
        # Store registered tools
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._tool_executors: Dict[str, Any] = {}
        
        # Initialize with default tools
        self._register_default_tools()
        
        # Load tools from YAML configuration
        self._load_tools_from_yaml()
    
    def _load_yaml_from_locations(self, filename: str) -> dict:
        """Load YAML file from multiple possible locations with priority order.
        
        Args:
            filename: Name of the YAML file to load
            
        Returns:
            Parsed YAML data as dictionary
        """
        yaml_data = {}
        
        # Define possible locations to look for the file
        # 1. Server directory
        server_dir = Path(__file__).resolve().parent.parent / "server"
        # 2. Private directory in server
        private_dir = server_dir / ".private"
        # 3. Current directory
        current_dir = Path(os.getcwd())
        
        # Check all locations in priority order
        for location in [private_dir, server_dir, current_dir]:
            yaml_path = location / filename
            if yaml_path.exists():
                logger.info(f"Loading {filename} from {yaml_path}")
                try:
                    with open(yaml_path, 'r') as file:
                        yaml_data = yaml.safe_load(file)
                        return yaml_data
                except Exception as e:
                    logger.error(f"Error loading {filename} from {yaml_path}: {e}")
        
        # If we got here, we didn't find a valid file
        logger.warning(f"Could not find {filename} in any of the expected locations")
        return yaml_data
    
    def _load_tools_from_yaml(self):
        """Load tools from the tools.yaml file and register them."""
        yaml_data = self._load_yaml_from_locations("tools.yaml")
        tools_data = yaml_data.get('tools', {})
        
        if not tools_data:
            logger.warning("No tools found in tools.yaml")
            return
        
        logger.info(f"Found {len(tools_data)} tools in tools.yaml")
        
        # Process each tool defined in the YAML
        for name, tool_data in tools_data.items():
            # Check if the tool is enabled
            if tool_data.get('enabled', True) == False:
                logger.info(f"Tool '{name}' is disabled in tools.yaml")
                continue
            
            logger.info(f"Registering tool from YAML: {name}")
            
            # Register the tool
            self._register_tool(
                name=name,
                description=tool_data.get('description', ''),
                input_schema=tool_data.get('inputSchema', {}),
                executor=self._create_yaml_tool_executor(name, tool_data)
            )
    
    def _create_yaml_tool_executor(self, name: str, tool_data: Dict[str, Any]):
        """Create a tool executor function for a YAML-defined tool.
        
        Args:
            name: Tool name
            tool_data: Tool configuration from YAML
            
        Returns:
            Async function that executes the tool
        """
        # Create an executor function for this tool
        async def execute_yaml_tool(arguments: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"Executing YAML-defined tool: {name}")
            
            # Script-based tools (type=script)
            if tool_data.get('type') == 'script':
                return await self._execute_yaml_tool(name, tool_data, arguments, 'script')
            
            # Plain task-based tools (no specific type defined)
            return await self._execute_yaml_tool(name, tool_data, arguments, 'task')
        
        return execute_yaml_tool
    
    async def _execute_yaml_tool(self, name: str, tool_data: Dict[str, Any], arguments: Dict[str, Any], 
                                tool_type: str) -> List[TextContent]:
        """Execute a tool defined in tools.yaml.
        
        Args:
            name: Tool name
            tool_data: Tool configuration from YAML
            arguments: Tool arguments
            tool_type: Type of tool ('script', 'task', etc.)
            
        Returns:
            Tool execution result
        """
        if not self.command_executor:
            return [TextContent(
                type="text",
                text="Error: Command executor not available"
            )]
        
        # Handle different tool types
        if tool_type == 'script':
            return await self._handle_script_tool(name, tool_data, arguments)
        elif name == "execute_task":
            return await self._handle_execute_task(arguments)
        elif name == "query_task_status" or name == "query_script_status":
            return await self._handle_query_status(arguments)
        elif name == "list_tasks":
            return await self._handle_list_tasks()
        elif name == "list_instructions":
            return await self._handle_list_instructions()
        elif name == "get_instruction":
            return await self._handle_get_instruction(arguments)
        
        # Default response for unimplemented tools
        return [TextContent(
            type="text",
            text=f"Tool '{name}' is defined in tools.yaml but not fully implemented yet"
        )]
    
    async def _handle_script_tool(self, name: str, tool_data: Dict[str, Any], arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle execution of a script-based tool.
        
        Args:
            name: Tool name
            tool_data: Tool configuration from YAML
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        # Get OS-specific script if available
        import platform
        os_type = platform.system().lower()
        
        script = None
        scripts = tool_data.get('scripts', {})
        
        if os_type in scripts:
            script = scripts[os_type]
        elif 'script' in tool_data:
            script = tool_data['script']
        
        if not script:
            return [TextContent(
                type="text",
                text=f"Error: No script defined for tool '{name}' on {os_type}"
            )]
        
        # Format the script with arguments
        try:
            # Handle parameters
            formatted_script = self._format_script_with_parameters(script, arguments)
            
            # Execute the script asynchronously
            logger.info(f"Executing script for tool '{name}': {formatted_script}")
            result = await self.command_executor.execute_async(formatted_script)
            
            return [TextContent(
                type="text",
                text=f"Script started with token: {result.get('token')}\nStatus: {result.get('status')}\nPID: {result.get('pid')}"
            )]
        except Exception as e:
            logger.exception(f"Error executing script for tool '{name}'")
            return [TextContent(
                type="text",
                text=f"Error executing script: {str(e)}"
            )]
    
    async def _handle_execute_task(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle execution of a task.
        
        Args:
            arguments: Tool arguments with task_name
            
        Returns:
            Tool execution result
        """
        task_name = arguments.get('task_name', '')
        if not task_name:
            return [TextContent(
                type="text",
                text="Error: Task name is required"
            )]
        
        # Load available tasks
        tasks = self._load_tasks_from_yaml()
        if task_name not in tasks:
            return [TextContent(
                type="text",
                text=f"Error: Task '{task_name}' not found"
            )]
        
        task = tasks[task_name]
        
        # Get the current OS
        import platform
        os_type = platform.system().lower()
        
        # Get the command for this OS
        command = None
        if 'commands' in task and os_type in task['commands']:
            command = task['commands'][os_type]
        elif 'command' in task:
            command = task['command']
        
        if not command:
            return [TextContent(
                type="text",
                text=f"Error: No command defined for task '{task_name}' on {os_type}"
            )]
        
        # Format the command
        try:
            # Handle parameters
            server_dir = Path(__file__).resolve().parent.parent / "server"
            parameters = {'pwd': str(server_dir)}
            command = command.format(**parameters)
            
            # Execute the command asynchronously
            logger.info(f"Executing task '{task_name}': {command}")
            result = await self.command_executor.execute_async(command)
            
            return [TextContent(
                type="text",
                text=f"Task '{task_name}' started with token: {result.get('token')}\nStatus: {result.get('status')}\nPID: {result.get('pid')}"
            )]
        except Exception as e:
            logger.exception(f"Error executing task '{task_name}'")
            return [TextContent(
                type="text",
                text=f"Error executing task: {str(e)}"
            )]
    
    async def _handle_list_tasks(self) -> List[TextContent]:
        """List all available tasks.
        
        Returns:
            List of available tasks
        """
        tasks = self._load_tasks_from_yaml()
        
        if not tasks:
            return [TextContent(
                type="text",
                text="No tasks available"
            )]
        
        # Format the task list
        task_list = []
        for name, task in tasks.items():
            description = task.get('description', 'No description')
            task_list.append(f"- {name}: {description}")
        
        return [TextContent(
            type="text",
            text="Available tasks:\n" + "\n".join(task_list)
        )]
    
    async def _handle_query_status(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Query the status of an async process.
        
        Args:
            arguments: Tool arguments with token
            
        Returns:
            Status of the process
        """
        token = arguments.get('token', '')
        if not token:
            return [TextContent(
                type="text",
                text="Error: Token is required"
            )]
        
        wait = arguments.get('wait', False)
        timeout = arguments.get('timeout')
        
        try:
            result = await self.command_executor.query_process(token, wait, timeout)
            
            if result.get('status') == 'completed':
                error_text = result.get('error')
                error_section = f"\nError:\n{error_text}" if error_text and error_text.strip() else ""
                
                return [TextContent(
                    type="text",
                    text=f"Process completed (token: {token})\nSuccess: {result.get('success')}\nOutput:\n{result.get('output')}{error_section}"
                )]
            else:
                # Just returning status
                status_text = f"Process status (token: {token}): {result.get('status')}"
                if 'pid' in result:
                    status_text += f"\nPID: {result.get('pid')}"
                return [TextContent(
                    type="text",
                    text=status_text
                )]
        except Exception as e:
            logger.exception(f"Error querying process status")
            return [TextContent(
                type="text",
                text=f"Error querying process status: {str(e)}"
            )]
    
    async def _handle_list_instructions(self) -> List[TextContent]:
        """List all available instructions.
        
        Returns:
            List of available instructions
        """
        return [TextContent(
            type="text",
            text="No instructions available"
        )]
    
    async def _handle_get_instruction(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get a specific instruction.
        
        Args:
            arguments: Tool arguments with instruction name
            
        Returns:
            Instruction details
        """
        name = arguments.get('name', '')
        if not name:
            return [TextContent(
                type="text",
                text="Error: Instruction name is required"
            )]
        
        return [TextContent(
            type="text",
            text=f"Instruction '{name}' not found"
        )]
    
    def _format_script_with_parameters(self, script: str, parameters: Dict[str, Any]) -> str:
        """Format a script with parameters."""
        try:
            # Add pwd parameter if not present
            if 'pwd' not in parameters:
                server_dir = Path(__file__).resolve().parent.parent / "server"
                parameters['pwd'] = str(server_dir)
            
            return script.format(**parameters)
        except KeyError as e:
            logger.warning(f"Missing parameter in script: {e}")
            return script
        except ValueError as e:
            logger.warning(f"Invalid format in script: {e}")
            return script
    
    def _load_tasks_from_yaml(self) -> Dict[str, Dict[str, Any]]:
        """Load tasks from the tools.yaml file."""
        yaml_data = self._load_yaml_from_locations("tools.yaml")
        return yaml_data.get('tasks', {})
    
    def _register_default_tools(self):
        """Register the default tools that are part of the original implementation."""
        # Register all tools from the registry
        for tool in injector.instances.values():
            self._register_tool_interface(tool)
        
        # Register additional backwards-compatibility tools
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
        
        self._register_tool(
            name="get_page_html",
            description="Open a webpage and get its HTML content",
            input_schema={"type": "object", "properties": {
                "url": {"type": "string"},
                "wait_time": {"type": "integer", "default": 30}
            }},
            executor=self._get_page_html
        )
    
    def _register_tool_interface(self, tool: ToolInterface):
        """Register a tool from its interface.
        
        Args:
            tool: The tool interface to register
        """
        if not tool:
            return
            
        self._tools[tool.name] = {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.input_schema
        }
        self._tool_executors[tool.name] = tool.execute_tool
        logger.info(f"Registered tool from interface: {tool.name}")
    
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
            
            # Convert result to TextContent if it's not already
            if isinstance(result, list) and all(isinstance(item, TextContent) for item in result):
                return result
            
            # Convert result to TextContent
            if isinstance(result, dict):
                return [TextContent(
                    type="text",
                    text=self._format_result_as_text(result)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=str(result)
                )]
        except Exception as e:
            logger.exception(f"Error executing tool {name}")
            return [TextContent(
                type="text",
                text=f"Error executing tool {name}: {str(e)}"
            )]
            
    def _format_result_as_text(self, result: Dict[str, Any]) -> str:
        """Format a result dictionary as text.
        
        Args:
            result: Result dictionary
            
        Returns:
            Formatted text
        """
        if not result.get("success", True):
            return f"Error: {result.get('error', 'Unknown error')}"
            
        # Different formatting based on the type of result
        if "output" in result:
            return result.get("output", "")
        elif "html" in result:
            return f"HTML content (length: {result.get('html_length', 0)}):\n{result.get('html', '')}"
        elif "parameters" in result:
            params = result.get("parameters", {})
            return "Environment parameters:\n" + "\n".join(f"{k}: {v}" for k, v in params.items())
        else:
            # Generic formatting
            return "\n".join(f"{k}: {v}" for k, v in result.items() if k != "success")
    
    # Example tool executors that use the new modules:
    
    async def _execute_command(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute a command synchronously."""
        command = arguments.get('command', '')
        logger.info(f"Executing command: {command}")
        
        if not self.command_executor:
            return [TextContent(
                type="text",
                text="Error: Command executor not available"
            )]
            
        result = self.command_executor.execute(command)
        
        return [TextContent(
            type="text",
            text=f"Command result:\n{result.get('output', '')}"
        )]
    
    async def _execute_command_async(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Start a command execution asynchronously."""
        command = arguments.get('command', '')
        timeout = arguments.get('timeout')
        
        if not self.command_executor:
            return [TextContent(
                type="text",
                text="Error: Command executor not available"
            )]
            
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
        
        if not self.azure_repo_client:
            return [TextContent(
                type="text",
                text="Error: Azure Repo Client not available"
            )]
            
        logger.info(f"Listing pull requests: repo={repository}, project={project}, org={organization}, status={status}")
        result = await self.azure_repo_client.list_pull_requests(repository, project, organization, status)
        
        return [TextContent(
            type="text",
            text=result.get("output", "No pull requests found")
        )]
    
    async def _get_page_html(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Open a webpage and get its HTML content."""
        url = arguments.get('url', '')
        wait_time = arguments.get('wait_time', 30)
        
        if not self.browser_client:
            return [TextContent(
                type="text",
                text="Error: Browser Client not available"
            )]
            
        logger.info(f"Getting HTML content for URL: {url}, wait_time={wait_time}")
        result = await self.browser_client.get_page_html(url, wait_time)
        
        return [TextContent(
            type="text",
            text=f"HTML content (length: {result.get('html_length', 0)}):\n{result.get('html', '')}"
        )] 