"""YAML-based tools loader.

This module handles loading tool definitions from YAML files and creating
dynamic tool implementations that can be registered with the plugin system.
"""

import logging
import os
import inspect
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Type

from mcp_tools.interfaces import ToolInterface, CommandExecutorInterface
from mcp_tools.plugin import register_tool, registry
from mcp_tools.dependency import injector

logger = logging.getLogger(__name__)

class YamlToolBase(ToolInterface):
    """Base class for YAML-defined tools."""
    
    def __init__(self, tool_name=None, tool_data=None, command_executor=None):
        """Initialize a YAML-defined tool.
        
        Args:
            tool_name: Name of the tool, defaults to _tool_name class attribute if set
            tool_data: Tool configuration from YAML, defaults to _tool_data class attribute if set
            command_executor: Optional command executor dependency
        """
        # Use class attributes as defaults if parameters not provided
        # This allows direct instantiation by the plugin system
        if tool_name is None and hasattr(self.__class__, '_tool_name'):
            tool_name = self.__class__._tool_name
        if tool_data is None and hasattr(self.__class__, '_tool_data'):
            tool_data = getattr(self.__class__, '_tool_data', {})
            
        # Fall back to a default if still not set
        if tool_name is None:
            tool_name = "unknown_yaml_tool"
        if tool_data is None:
            tool_data = {}
            
        self._name = tool_name
        self._description = tool_data.get('description', '')
        self._input_schema = tool_data.get('inputSchema', {"type": "object", "properties": {}, "required": []})
        self._tool_data = tool_data
        self._tool_type = tool_data.get('type', 'object')
        
        # Get command executor from injector if not provided
        if command_executor is None:
            self._command_executor = injector.get_tool_instance("command_executor")
        else:
            self._command_executor = command_executor
    
    @property
    def name(self) -> str:
        """Get the tool name."""
        return self._name
    
    @property
    def description(self) -> str:
        """Get the tool description."""
        return self._description
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the tool input schema."""
        return self._input_schema

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the tool based on its type.
        
        Args:
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if not self._command_executor:
            return {
                "success": False,
                "error": "Command executor not available"
            }
        
        logger.info(f"Executing tool: {self._name}, type: {self._tool_type}")
        
        if self._tool_type == 'script':
            return await self._execute_script(arguments)
        elif self._name == "execute_task":
            return await self._execute_task(arguments)
        elif self._name == "query_task_status" or self._name == "query_script_status":
            return await self._query_status(arguments)
        elif self._name == "list_tasks":
            return await self._list_tasks()
        elif self._name == "list_instructions":
            return await self._list_instructions()
        elif self._name == "get_instruction":
            return await self._get_instruction(arguments)
        else:
            logger.warning(f"Tool '{self._name}' with type '{self._tool_type}' is not fully implemented")
            return [{
                "type": "text",
                "text": f"Tool '{self._name}' is defined in YAML but not fully implemented"
            }]
    
    async def _execute_script(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a script-based tool.
        
        Args:
            arguments: Tool arguments
            
        Returns:
            Script execution result
        """
        # Get OS-specific script
        import platform
        os_type = platform.system().lower()
        
        script = None
        scripts = self._tool_data.get('scripts', {})
        
        if os_type in scripts:
            script = scripts[os_type]
        elif 'script' in self._tool_data:
            script = self._tool_data['script']
        
        if not script:
            return [{
                "type": "text",
                "text": f"Error: No script defined for tool '{self._name}' on {os_type}"
            }]
        
        # Format the script with arguments
        try:
            # Add server_dir parameter
            server_dir = self._get_server_dir()
            params = {'pwd': str(server_dir)}
            # Add user arguments
            params.update(arguments)
            
            formatted_script = script.format(**params)
            
            # Execute the script
            logger.info(f"Executing script for tool '{self._name}': {formatted_script}")
            result = await self._command_executor.execute_async(formatted_script)
            
            return [{
                "type": "text",
                "text": f"Script started with token: {result.get('token')}\nStatus: {result.get('status')}\nPID: {result.get('pid')}"
            }]
        except Exception as e:
            logger.exception(f"Error executing script for tool '{self._name}'")
            return [{
                "type": "text",
                "text": f"Error executing script: {str(e)}"
            }]
    
    async def _execute_task(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a predefined task.
        
        Args:
            arguments: Tool arguments
            
        Returns:
            Task execution result
        """
        task_name = arguments.get('task_name', '')
        if not task_name:
            return [{
                "type": "text",
                "text": "Error: Task name is required"
            }]
        
        # Load tasks from YAML
        tasks = self._load_tasks_from_yaml()
        if task_name not in tasks:
            return [{
                "type": "text",
                "text": f"Error: Task '{task_name}' not found"
            }]
        
        task = tasks[task_name]
        
        # Get OS-specific command
        import platform
        os_type = platform.system().lower()
        
        command = None
        if 'commands' in task and os_type in task['commands']:
            command = task['commands'][os_type]
        elif 'command' in task:
            command = task['command']
        
        if not command:
            return [{
                "type": "text",
                "text": f"Error: No command defined for task '{task_name}' on {os_type}"
            }]
        
        # Format the command with parameters
        try:
            server_dir = self._get_server_dir()
            params = {'pwd': str(server_dir)}
            # Format command with parameters
            formatted_command = command.format(**params)
            
            # Execute the command
            logger.info(f"Executing task '{task_name}': {formatted_command}")
            result = await self._command_executor.execute_async(formatted_command)
            
            return [{
                "type": "text",
                "text": f"Task '{task_name}' started with token: {result.get('token')}\nStatus: {result.get('status')}\nPID: {result.get('pid')}"
            }]
        except Exception as e:
            logger.exception(f"Error executing task '{task_name}'")
            return [{
                "type": "text",
                "text": f"Error executing task: {str(e)}"
            }]
    
    async def _query_status(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query the status of an async process.
        
        Args:
            arguments: Tool arguments
            
        Returns:
            Process status
        """
        token = arguments.get('token', '')
        if not token:
            return [{
                "type": "text",
                "text": "Error: Token is required"
            }]
        
        wait = arguments.get('wait', False)
        timeout = arguments.get('timeout')
        
        try:
            result = await self._command_executor.query_process(token, wait, timeout)
            
            if result.get('status') == 'completed':
                error_text = result.get('error')
                error_section = f"\nError:\n{error_text}" if error_text and error_text.strip() else ""
                
                return [{
                    "type": "text",
                    "text": f"Process completed (token: {token})\nSuccess: {result.get('success')}\nOutput:\n{result.get('output')}{error_section}"
                }]
            else:
                # Just returning status
                status_text = f"Process status (token: {token}): {result.get('status')}"
                if 'pid' in result:
                    status_text += f"\nPID: {result.get('pid')}"
                return [{
                    "type": "text",
                    "text": status_text
                }]
        except Exception as e:
            logger.exception(f"Error querying process status")
            return [{
                "type": "text",
                "text": f"Error querying process status: {str(e)}"
            }]
    
    async def _list_tasks(self) -> List[Dict[str, Any]]:
        """List all available tasks.
        
        Returns:
            List of tasks
        """
        tasks = self._load_tasks_from_yaml()
        
        if not tasks:
            return [{
                "type": "text",
                "text": "No tasks available"
            }]
        
        # Format the task list
        task_list = []
        for name, task in tasks.items():
            description = task.get('description', 'No description')
            task_list.append(f"- {name}: {description}")
        
        return [{
            "type": "text",
            "text": "Available tasks:\n" + "\n".join(task_list)
        }]
    
    async def _list_instructions(self) -> List[Dict[str, Any]]:
        """List all available instructions.
        
        Returns:
            List of instructions
        """
        return [{
            "type": "text",
            "text": "No instructions available"
        }]
    
    async def _get_instruction(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get a specific instruction.
        
        Args:
            arguments: Tool arguments
            
        Returns:
            Instruction details
        """
        name = arguments.get('name', '')
        if not name:
            return [{
                "type": "text",
                "text": "Error: Instruction name is required"
            }]
        
        return [{
            "type": "text",
            "text": f"Instruction '{name}' not found"
        }]
    
    def _load_tasks_from_yaml(self) -> Dict[str, Dict[str, Any]]:
        """Load tasks from the tools.yaml file."""
        yaml_data = self._load_yaml_from_locations("tools.yaml")
        return yaml_data.get('tasks', {})
    
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
        server_dir = self._get_server_dir()
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
                        content = file.read()
                        try:
                            yaml_data = yaml.safe_load(content)
                            
                            # Validate the loaded YAML data
                            if not isinstance(yaml_data, dict):
                                logger.error(f"Invalid YAML format in {yaml_path}: root must be a dictionary")
                                yaml_data = {}
                            
                            # Make sure 'tools' key exists and is a dictionary
                            if 'tools' in yaml_data and not isinstance(yaml_data['tools'], dict):
                                logger.error(f"Invalid 'tools' section in {yaml_path}: must be a dictionary")
                                yaml_data['tools'] = {}
                            
                            # Make sure 'tasks' key exists and is a dictionary if present
                            if 'tasks' in yaml_data and not isinstance(yaml_data['tasks'], dict):
                                logger.error(f"Invalid 'tasks' section in {yaml_path}: must be a dictionary")
                                yaml_data['tasks'] = {}
                                
                            return yaml_data
                        except yaml.YAMLError as e:
                            logger.error(f"YAML parsing error in {yaml_path}: {e}")
                            # Return empty dict instead of invalid data
                            return {}
                except Exception as e:
                    logger.error(f"Error loading {filename} from {yaml_path}: {e}")
        
        # If we got here, we didn't find a valid file
        logger.warning(f"Could not find {filename} in any of the expected locations")
        return yaml_data
    
    def _get_server_dir(self) -> Path:
        """Get the server directory path.
        
        Returns:
            Path to the server directory
        """
        # Get the path of the current file
        current_file = Path(__file__).resolve()
        # Go up to the project root
        project_root = current_file.parent.parent
        # Get the server directory
        return project_root / "server"

def load_yaml_tools() -> List[Type[ToolInterface]]:
    """Load tools from tools.yaml and register them.
    
    Returns:
        List of registered YAML tool classes
    """
    logger.info("Loading YAML-defined tools")
    
    try:
        # Create a base instance to load YAML
        base_tool = YamlToolBase()
        yaml_data = base_tool._load_yaml_from_locations("tools.yaml")
        tools_data = yaml_data.get('tools', {})
        
        if not tools_data:
            logger.warning("No tools found in tools.yaml")
            return []
        
        logger.info(f"Found {len(tools_data)} tools in tools.yaml")
        
        # DIRECT FIX: Ensure all tools have valid inputSchema.type values
        # This is a quick fix to handle the specific error reported
        for tool_name, tool_data in tools_data.items():
            if 'inputSchema' in tool_data and isinstance(tool_data['inputSchema'], dict):
                if 'type' in tool_data['inputSchema'] and not isinstance(tool_data['inputSchema']['type'], str):
                    logger.warning(f"DIRECT FIX: Tool '{tool_name}' has non-string inputSchema.type: {tool_data['inputSchema']['type']} ({type(tool_data['inputSchema']['type'])})")
                    # Force set to string "object"
                    tool_data['inputSchema']['type'] = "object"
        
        # Debug output for all tools before processing
        for i, (name, tool_data) in enumerate(tools_data.items()):
            logger.info(f"DEBUG Tool #{i}: {name}")
            logger.info(f"  Description: {tool_data.get('description', 'N/A')}")
            logger.info(f"  Tool Type: {tool_data.get('type', 'N/A')}")
            if 'inputSchema' in tool_data:
                input_schema = tool_data['inputSchema']
                logger.info(f"  InputSchema: {type(input_schema)}")
                
                if isinstance(input_schema, dict):
                    schema_type = input_schema.get('type')
                    logger.info(f"  Schema.type: {schema_type} (type: {type(schema_type)})")
                    logger.info(f"  Properties: {input_schema.get('properties', {})}")
                    logger.info(f"  Required: {input_schema.get('required', [])}")
                else:
                    logger.info(f"  Schema value (invalid): {input_schema}")
            else:
                logger.info("  No inputSchema found")
        
        # List to hold dynamically created classes
        yaml_tool_classes = []
        
        # Process each tool defined in the YAML
        for name, tool_data in tools_data.items():
            try:
                # Skip disabled tools
                if tool_data.get('enabled', True) == False:
                    logger.info(f"Tool '{name}' is disabled in tools.yaml")
                    continue
                
                logger.info(f"Processing YAML tool: {name}")
                
                # Verify schema after fixing
                if not isinstance(tool_data, dict):
                    logger.error(f"Invalid tool data for '{name}' after schema fix")
                    continue
                    
                if 'inputSchema' not in tool_data:
                    logger.error(f"Missing inputSchema for tool '{name}' after schema fix")
                    continue
                    
                if not isinstance(tool_data['inputSchema'], dict):
                    logger.error(f"Invalid inputSchema type for tool '{name}' after schema fix: {type(tool_data['inputSchema'])}")
                    continue
                
                # Create a dynamic class for this tool
                try:
                    # Ensure name is set in the tool_data
                    if 'name' not in tool_data or not tool_data['name']:
                        tool_data['name'] = name
                        logger.warning(f"Setting missing name property for tool '{name}'")
                    
                    # Log the final tool data
                    logger.info(f"Creating class for '{name}' with data: {tool_data}")
                    
                    tool_class = type(
                        f"YamlTool_{name}",
                        (YamlToolBase,),
                        {
                            "_tool_name": name,
                            "_tool_data": tool_data
                        }
                    )
                    
                    # Register the tool
                    logger.info(f"Registering YAML tool: {name}")
                    tool_class = register_tool(tool_class)
                    yaml_tool_classes.append(tool_class)
                except Exception as create_error:
                    logger.error(f"Error creating or registering class for YAML tool '{name}': {create_error}")
            except Exception as e:
                logger.error(f"Error processing YAML tool '{name}': {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        return yaml_tool_classes
    except Exception as e:
        logger.error(f"Error loading YAML tools: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def discover_and_register_yaml_tools():
    """Discover and register all YAML-defined tools.
    
    Returns:
        List of registered tool classes
    """
    try:
        return load_yaml_tools()
    except Exception as e:
        logger.error(f"Error in discover_and_register_yaml_tools: {e}")
        return [] 