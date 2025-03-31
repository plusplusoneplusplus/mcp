import os
from pathlib import Path
import yaml
from typing import Dict, Any, List, Optional, ClassVar, Type
from pydantic import BaseModel
from mcp.types import TextContent, Tool

from sentinel.command_executor import CommandExecutor

executor = CommandExecutor()

class ExecuteCommandInput(BaseModel):
    command: str

class UpdateDcCommandInput(BaseModel):
    dc_name: str

class ToolExecutor:
    """Base class for all tool executors."""
    tool_name: ClassVar[str] = ""
    tool_description: ClassVar[str] = ""
    input_schema: ClassVar[dict] = {}
    
    @classmethod
    def get_tool_definition(cls) -> Tool:
        """Get the tool definition."""
        return Tool(
            name=cls.tool_name,
            description=cls.tool_description,
            inputSchema=cls.input_schema
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
        result = executor.execute_command(command)
        return [TextContent(
            type="text",
            text=f"Command result:\n{result}"
        )]

class ListInstructionsTool(ToolExecutor):
    """Tool to list all available instructions."""
    tool_name = "list_instructions"
    tool_description = "List all available instructions"
    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
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
    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the instruction to retrieve"
            }
        },
        "required": ["name"]
    }
    
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

def load_tools_from_yaml() -> Dict[str, Dict[str, Any]]:
    """Load tools from the tools.yaml file."""
    yaml_path = Path(__file__).resolve().parent / "tools.yaml"
    with open(yaml_path, 'r') as file:
        yaml_data = yaml.safe_load(file)
    
    return yaml_data.get('tools', {})

# Dictionary mapping tool names to their executor classes
TOOL_EXECUTORS = {
    "execute_command": ExecuteCommandTool,
    "list_instructions": ListInstructionsTool,
    "get_instruction": GetInstructionTool,
}

def get_tools() -> list[Tool]:
    """Return a list of available tools."""
    # First get tools from executors
    tools_list = [executor_class().get_tool_definition() for executor_class in TOOL_EXECUTORS.values()]
    
    # Then add any tools from YAML that don't have executors
    yaml_tools = load_tools_from_yaml()
    for name, tool_data in yaml_tools.items():
        if name not in TOOL_EXECUTORS:
            tools_list.append(
                Tool(
                    name=tool_data.get('name', name),
                    description=tool_data.get('description', ''),
                    inputSchema=tool_data.get('inputSchema', {})
                )
            )
        elif tool_data.get('enabled', True) == False:
            tools_list = [tool for tool in tools_list if tool.name != name]
    
    return tools_list

async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Call a tool by name with the provided arguments."""
    # Check if we have an executor for this tool
    if name in TOOL_EXECUTORS:
        tool_executor = TOOL_EXECUTORS[name]()
        return await tool_executor.execute(arguments)
    
    # Check if tool exists in YAML
    yaml_tools = load_tools_from_yaml()
    if name in yaml_tools:
        raise ValueError(f"Tool '{name}' found in YAML but no executor is implemented")
    
    raise ValueError(f"Tool not found: {name}")
