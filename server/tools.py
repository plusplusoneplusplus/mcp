import os
from pathlib import Path
import yaml
from typing import Dict, Any, List, Optional, ClassVar, Type
from pydantic import BaseModel
from mcp.types import TextContent, Tool

from sentinel.command_executor import CommandExecutor

executor = CommandExecutor()
pwd = Path(__file__).resolve().parent

class ExecuteCommandInput(BaseModel):
    command: str

class ExecuteCommandAsyncInput(BaseModel):
    command: str
    timeout: Optional[float] = None

class QueryCommandStatusInput(BaseModel):
    token: str
    wait: bool = False
    timeout: Optional[float] = None

class UpdateDcCommandInput(BaseModel):
    dc_name: str

class ToolExecutor:
    """Base class for all tool executors."""
    tool_name: str = ""
    tool_description: str = ""
    input_schema: dict = {}

    def get_tool_definition(self) -> Tool:
        """Get the tool definition."""
        return Tool(
            name=self.tool_name,
            description=self.tool_description,
            inputSchema=self.input_schema
        )
    
    async def execute(self, arguments: dict) -> list[TextContent]:
        """Execute the tool with the provided arguments."""
        raise NotImplementedError("Subclasses must implement this method")

class ExecuteCommandTool(ToolExecutor):
    """Tool to execute system commands."""
    tool_name = "execute_command"
    tool_description = "Execute a command"
    input_schema = ExecuteCommandInput.model_json_schema()
    
    async def execute(self, arguments: dict) -> list[TextContent]:
        """Execute a command and return the result."""
        command = arguments.get('command', '')
        print(f"Executing command: {command}")
        result = executor.execute(command)
        return [TextContent(
            type="text",
            text=f"Command result:\n{result}"
        )]

class ExecuteCommandAsyncTool(ToolExecutor):
    """Tool to execute system commands asynchronously."""
    tool_name = "execute_command_async"
    tool_description = "Start a command execution asynchronously and return a token for tracking"
    input_schema = ExecuteCommandAsyncInput.model_json_schema()
    
    async def execute(self, arguments: dict) -> list[TextContent]:
        """Start a command execution asynchronously and return a token for tracking."""
        command = arguments.get('command', '')
        timeout = arguments.get('timeout')
        
        print(f"Starting async command execution: {command}")
        result = await executor.execute_async(command, timeout)
        
        return [TextContent(
            type="text",
            text=f"Command started with token: {result['token']}\nStatus: {result['status']}\nPID: {result['pid']}"
        )]

class QueryCommandStatusTool(ToolExecutor):
    """Tool to query the status of an asynchronous command execution."""
    tool_name = "query_command_status"
    tool_description = "Query the status of an asynchronous command execution or wait for it to complete"
    input_schema = QueryCommandStatusInput.model_json_schema()
    
    async def execute(self, arguments: dict) -> list[TextContent]:
        """Query the status of an asynchronous command execution or wait for it to complete."""
        token = arguments.get('token', '')
        wait = arguments.get('wait', False)
        timeout = arguments.get('timeout')
        
        print(f"Querying command status for token: {token}, wait: {wait}")
        
        result = await executor.query_process(token, wait, timeout)
        
        if result.get('status') == 'completed':
            return [TextContent(
                type="text",
                text=f"Command completed (token: {token})\nSuccess: {result.get('success')}\nOutput:\n{result.get('output')}\nError:\n{result.get('error')}"
            )]
        else:
            # Just returning status
            status_text = f"Command status (token: {token}): {result.get('status')}"
            if 'pid' in result:
                status_text += f"\nPID: {result.get('pid')}"
            if 'cpu_percent' in result:
                status_text += f"\nCPU: {result.get('cpu_percent')}%"
            if 'memory_info' in result:
                status_text += f"\nMemory: {result.get('memory_info')}"
            
            return [TextContent(
                type="text",
                text=status_text
            )]

class ListInstructionsTool(ToolExecutor):
    """Tool to list all available instructions."""
    tool_name = "list_instructions"
    tool_description = "List all available instructions"
    input_schema = {}
    
    async def execute(self, arguments: dict) -> list[TextContent]:
        """List all available instructions."""
        # Import here to avoid circular imports
        import prompts
        available_instructions = prompts.get_prompts()
        instruction_list = "\n".join([f"- {p.name}: {p.description}" for p in available_instructions])
        
        return [TextContent(
            type="text",
            text=f"Available instructions:\n{instruction_list}"
        )]

class GetInstructionTool(ToolExecutor):
    """Tool to get a specific instruction with its details."""
    tool_name = "get_instruction"
    tool_description = "Get a specific instruction with its details"
    input_schema = {}
    
    async def execute(self, arguments: dict) -> list[TextContent]:
        """Get a specific instruction with its details."""
        # Import here to avoid circular imports
        import prompts
        
        instruction_name = arguments.get('name')
        if not instruction_name:
            raise ValueError("Instruction name is required")
        
        # Get all instructions
        yaml_prompts = prompts.load_prompts_from_yaml()
        if instruction_name not in yaml_prompts:
            raise ValueError(f"Instruction not found: {instruction_name}")
        
        instruction_data = yaml_prompts[instruction_name]
        
        # Format the response
        args_desc = ""
        if 'arguments' in instruction_data:
            args_desc = "\nArguments:\n" + "\n".join([
                f"- {arg.get('name')}: {arg.get('description')} "
                f"({'Required' if arg.get('required') else 'Optional'})"
                for arg in instruction_data['arguments']
            ])
        
        template = f"\nTemplate:\n{instruction_data.get('template', 'No template available')}" if 'template' in instruction_data else ""
        
        return [TextContent(
            type="text",
            text=f"Instruction: {instruction_data.get('name')}\nDescription: {instruction_data.get('description')}{args_desc}{template}"
        )]

class ScriptTool(ToolExecutor):
    """Tool to execute scripts defined in YAML."""
    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, name: str, description: str, script_path: str, input_schema: dict):
        self.tool_name = name
        self.tool_description = description
        self.script_path = script_path
        self.input_schema = input_schema
    
    @classmethod
    def from_yaml(cls, name: str, tool_data: dict) -> 'ScriptTool':
        """Create a ScriptTool instance from YAML data."""
        return cls(
            name=name,
            description=tool_data.get('description', ''),
            script_path=tool_data.get('script', ''),
            input_schema=tool_data.get('inputSchema', {})
        )
    
    async def execute(self, arguments: dict) -> list[TextContent]:
        """Execute the script with the provided arguments."""
        defaultparams = {"pwd": pwd}
        script_path = self.script_path.format(**defaultparams)
        script_path = Path(script_path)
        
        # Build command with arguments
        command = [str(script_path)]
        for arg_name, arg_value in arguments.items():
            command.extend([f"--{arg_name}", str(arg_value)])
        
        print(f"Executing script: {' '.join(command)}")
        result = executor.execute(' '.join(command))
        return [TextContent(
            type="text",
            text=f"Script result:\n{result}"
        )]

def load_tools_from_yaml() -> Dict[str, Dict[str, Any]]:
    """Load tools from the tools.yaml file."""
    # First try to load from private directory
    private_yaml_path = pwd / ".private" / "tools.yaml"
    if private_yaml_path.exists():
        with open(private_yaml_path, 'r') as file:
            yaml_data = yaml.safe_load(file)
            return yaml_data.get('tools', {})
    
    # Fallback to default location if private file doesn't exist
    yaml_path = pwd / "tools.yaml"
    with open(yaml_path, 'r') as file:
        yaml_data = yaml.safe_load(file)
    
    return yaml_data.get('tools', {})

# Dictionary mapping tool names to their executor classes
TOOL_EXECUTORS = {
    # "execute_command": ExecuteCommandTool,
    "execute_command_async": ExecuteCommandAsyncTool,
    "query_command_status": QueryCommandStatusTool,
    "list_instructions": ListInstructionsTool,
    "get_instruction": GetInstructionTool,
}

# initialize the tools
yaml_tools = load_tools_from_yaml()
tools_mapping = {}

for name, tool_data in yaml_tools.items():
    if name not in TOOL_EXECUTORS:
        print(f"Adding tool: {name}")
        if tool_data.get('type') == 'script':
            # Create a script-based tool
            script_tool = ScriptTool.from_yaml(name, tool_data)
            tools_mapping[name] = script_tool
        else:
            # Create a regular tool
            tools_mapping[name] = Tool(
                name=tool_data.get('name', name),
                description=tool_data.get('description', ''),
                inputSchema=tool_data.get('inputSchema', {})
            )
    elif tool_data.get('enabled', True) == False:
        if name in tools_mapping:
            tools_mapping.pop(name)
    else:
        # Create tool instance with YAML data
        tool_class = TOOL_EXECUTORS[name]
        tool_instance = tool_class()
        
        # Override properties with YAML data if provided
        if 'name' in tool_data:
            tool_instance.tool_name = tool_data['name']
        if 'description' in tool_data:
            tool_instance.tool_description = tool_data['description']
        if 'inputSchema' in tool_data:
            tool_instance.input_schema = tool_data['inputSchema']

        # print(f"tool_instance: {tool_instance.get_tool_definition()}")

        tools_mapping[name] = tool_instance

def get_tools() -> list[Tool]:
    """Return a list of available tools."""
    result = [tool.get_tool_definition() for tool in tools_mapping.values()]
    print(f"result: {result}")
    return result

async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Call a tool by name with the provided arguments."""
    # Check if we have an executor for this tool
    if name in tools_mapping:
        return await tools_mapping[name].execute(arguments)
    
    # Check if tool exists in YAML
    yaml_tools = load_tools_from_yaml()
    if name in yaml_tools:
        raise ValueError(f"Tool '{name}' found in YAML but no executor is implemented")
    
    raise ValueError(f"Tool not found: {name}")
