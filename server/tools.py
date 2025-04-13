import os
from pathlib import Path
import yaml
from typing import Dict, Any, List, Optional, ClassVar, Type
from pydantic import BaseModel
from mcp.types import TextContent, Tool
import platform

# Use absolute imports with 'import command_executor' instead of relative imports
import command_executor
from environment import env, get_private_tool_root

PRIVATE_DIRECTORY_NAME = ".private"
DEFAULT_TIMEOUT = 25

executor = command_executor.CommandExecutor()
pwd = Path(__file__).resolve().parent

g_default_parameters = {
    "pwd": pwd
}

def format_command_with_parameters(command: str, parameters: Dict[str, Any]) -> str:
    """Format a command with parameters.

    Args:
        command: The command string with placeholders
        parameters: Dictionary of parameters to substitute
    """
    # Merge with global default parameters if not already defined
    merged_parameters = {**g_default_parameters}
    merged_parameters.update(parameters)

    try:
        return command.format(**merged_parameters)
    except KeyError as e:
        print(f"Warning: Missing parameter in command: {e}")
        return command  # Return original command if formatting fails
    except ValueError as e:
        print(f"Warning: Invalid format in command: {e}")
        return command  # Return original command if formatting fails

class ExecuteCommandInput(BaseModel):
    command: str

class ExecuteCommandAsyncInput(BaseModel):
    command: str
    timeout: Optional[float] = None

class QueryCommandStatusInput(BaseModel):
    token: str
    wait: bool = False
    timeout: Optional[float] = None

class ExecuteTaskInput(BaseModel):
    task_name: str
    timeout: Optional[float] = None

class QueryTaskStatusInput(BaseModel):
    token: str
    wait: bool = False
    timeout: Optional[float] = None

class QueryScriptStatusInput(BaseModel):
    token: str
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
        timeout = arguments.get('timeout', DEFAULT_TIMEOUT)

        print(f"Querying command status for token: {token}, wait: {wait}")

        result = await executor.query_process(token, wait, timeout)

        if result.get('status') == 'completed':
            error_text = result.get('error')
            error_section = f"\nError:\n{error_text}" if error_text and error_text.strip() else ""
            
            return [TextContent(
                type="text",
                text=f"Command completed (token: {token})\nSuccess: {result.get('success')}\nOutput:\n{result.get('output')}{error_section}"
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

class ExecuteTaskTool(ToolExecutor):
    """Tool to execute predefined tasks by name."""
    tool_name = "execute_task"
    tool_description = "Execute a predefined task by name and start it asynchronously"
    input_schema = ExecuteTaskInput.model_json_schema()

    async def execute(self, arguments: dict) -> list[TextContent]:
        """Execute a predefined task by name."""
        task_name = arguments.get('task_name', '')
        timeout = arguments.get('timeout', DEFAULT_TIMEOUT)

        # Load available tasks
        tasks = load_tasks_from_yaml()
        if task_name not in tasks:
            return [TextContent(
                type="text",
                text=f"Error: Task '{task_name}' not found. Use 'list_tasks' to see available tasks."
            )]

        task = tasks[task_name]

        # Get the current OS
        os_type = platform.system().lower()

        # Check if this task has OS-conditional commands
        if 'commands' in task:
            # Get the command for the current OS
            if os_type not in task['commands']:
                return [TextContent(
                    type="text",
                    text=f"Error: Task '{task_name}' does not support the {os_type} operating system."
                )]
            command = task['commands'][os_type]
        elif 'command' in task:
            # Fallback to the simple command if no OS-conditional commands are defined
            command = task.get('command', '')
        else:
            return [TextContent(
                type="text",
                text=f"Error: Task '{task_name}' does not have a valid command definition."
            )]

        # Use the task-defined timeout if available and not overridden
        if timeout is None and 'timeout' in task:
            timeout = task.get('timeout')

        command = format_command_with_parameters(command, g_default_parameters)

        print(f"Starting task '{task_name}' with command: {command}")
        result = await executor.execute_async(command, timeout)

        return [TextContent(
            type="text",
            text=f"Task '{task_name}' started with token: {result['token']}\nStatus: {result['status']}\nPID: {result['pid']}\nCommand: {command}\nOS: {os_type}"
        )]

class QueryTaskStatusTool(ToolExecutor):
    """Tool to query the status of an asynchronously executed task."""
    tool_name = "query_task_status"
    tool_description = "Query the status of an asynchronously executed task"
    input_schema = QueryTaskStatusInput.model_json_schema()

    async def execute(self, arguments: dict) -> list[TextContent]:
        """Query the status of an executed task."""
        token = arguments.get('token', '')
        wait = arguments.get('wait', False)
        timeout = arguments.get('timeout', DEFAULT_TIMEOUT)

        print(f"Querying task status for token: {token}, wait: {wait}")

        result = await executor.query_process(token, wait, timeout)

        if result.get('status') == 'completed':
            error_text = result.get('error')
            error_section = f"\nError:\n{error_text}" if error_text and error_text.strip() else ""
            
            return [TextContent(
                type="text",
                text=f"Task completed (token: {token})\nSuccess: {result.get('success')}\nOutput:\n{result.get('output')}{error_section}"
            )]
        else:
            # Just returning status
            status_text = f"Task status (token: {token}): {result.get('status')}"
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

class ListTasksTool(ToolExecutor):
    """Tool to list all available predefined tasks."""
    tool_name = "list_tasks"
    tool_description = "List all available predefined tasks"
    input_schema = {}

    async def execute(self, arguments: dict) -> list[TextContent]:
        """List all available predefined tasks."""
        tasks = load_tasks_from_yaml()

        if not tasks:
            return [TextContent(
                type="text",
                text="No predefined tasks found."
            )]

        # Get the current OS
        os_type = platform.system().lower()

        task_list = []
        for name, task in tasks.items():
            description = task.get('description', 'No description')
            timeout = f", timeout: {task.get('timeout')} seconds" if 'timeout' in task else ""

            # Handle OS-conditional commands
            if 'commands' in task:
                if os_type in task['commands']:
                    command = task['commands'][os_type]
                    os_support = f"Current OS command ({os_type}): {command}"
                else:
                    command = "No command available for current OS"
                    os_support = f"Warning: This task does not support the current OS ({os_type})"

                # Add all supported OS commands
                all_commands = "\n  ".join([f"{os}: {cmd}" for os, cmd in task['commands'].items()])
                command_info = f"All OS commands:\n  {all_commands}"
            elif 'command' in task:
                command = task.get('command', 'No command')
                os_support = "Generic command (all OS)"
                command_info = f"Command: {command}"
            else:
                command = "No command defined"
                os_support = "Warning: This task has no command defined"
                command_info = ""

            task_list.append(f"- {name}: {description}{timeout}\n  {os_support}\n  {command_info}")

        return [TextContent(
            type="text",
            text=f"Available predefined tasks:\n\n" + "\n\n".join(task_list)
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

class ScriptAsyncTool(ToolExecutor):
    """Tool to execute scripts defined in YAML."""
    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, name: str, description: str, script_path: str, input_schema: dict, scripts: dict = None):
        self.tool_name = name
        self.tool_description = description
        self.script_path = script_path
        self.input_schema = input_schema
        self.scripts = scripts or {}  # OS-specific scripts

    @classmethod
    def from_yaml(cls, name: str, tool_data: dict) -> 'ScriptAsyncTool':
        """Create a ScriptAsyncTool instance from YAML data."""
        return cls(
            name=name,
            description=tool_data.get('description', ''),
            script_path=tool_data.get('script', ''),
            input_schema=tool_data.get('inputSchema', {}),
            scripts=tool_data.get('scripts', {})
        )

    async def execute(self, arguments: dict) -> list[TextContent]:
        """Execute the script with the provided arguments."""
        # Get the current OS
        os_type = platform.system().lower()
        
        # Check if there are OS-specific scripts defined
        if self.scripts and os_type in self.scripts:
            # Use OS-specific script
            script_cmd = self.scripts[os_type]
        else:
            # Use default script path
            script_cmd = self.script_path
            
        # Format with parameters
        script_cmd = format_command_with_parameters(script_cmd, g_default_parameters)
        
        # Build command with arguments
        if "{args}" in script_cmd:
            # If {args} placeholder exists, construct args string and inject it
            args_str = ""
            for arg_name, arg_value in arguments.items():
                if arg_name != 'timeout':  # Handle timeout separately
                    if isinstance(arg_value, bool):
                        if arg_value:
                            args_str += f" --{arg_name}"
                    else:
                        args_str += f" --{arg_name} {arg_value}"
            
            # Replace {args} with constructed args string
            command = script_cmd.replace("{args}", args_str.strip())
        else:
            # Otherwise construct command array and join
            command_parts = [script_cmd]
            for arg_name, arg_value in arguments.items():
                if arg_name != 'timeout':  # Handle timeout separately
                    if isinstance(arg_value, bool):
                        if arg_value:
                            command_parts.append(f"--{arg_name}")
                    else:
                        command_parts.append(f"--{arg_name}")
                        command_parts.append(str(arg_value))
            
            command = " ".join(command_parts)

        timeout = arguments.get('timeout')
        
        # Execute asynchronously
        print(f"Starting async script execution: {command}")
        result = await executor.execute_async(command, timeout)
        return [TextContent(
            type="text",
            text=f"Script started with token: {result['token']}\nStatus: {result['status']}\nPID: {result['pid']}"
        )]

class QueryScriptStatusTool(QueryCommandStatusTool):
    """Tool to query the status of an asynchronously executed script."""
    tool_name = "query_script_status"
    tool_description = "Query the status of an asynchronously executed script"
    input_schema = QueryScriptStatusInput.model_json_schema()

    # This tool reuses the implementation from QueryCommandStatusTool
    # but never waits for completion
    
    async def execute(self, arguments: dict) -> list[TextContent]:
        """Query the status of an executed script without waiting."""
        token = arguments.get('token', '')
        timeout = arguments.get('timeout', DEFAULT_TIMEOUT)

        print(f"Querying script status for token: {token}")

        # Force wait to False to ensure we never wait
        result = await executor.query_process(token, False, timeout)

        if result.get('status') == 'completed':
            error_text = result.get('error')
            error_section = f"\nError:\n{error_text}" if error_text and error_text.strip() else ""
            
            return [TextContent(
                type="text",
                text=f"Script completed (token: {token})\nSuccess: {result.get('success')}\nOutput:\n{result.get('output')}{error_section}"
            )]
        else:
            # Just returning status
            status_text = f"Script status (token: {token}): {result.get('status')}"
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

def load_yaml_from_locations(filename: str) -> dict:
    """Load YAML file from multiple possible locations with priority order."""
    yaml_data = {}

    # Priority 1: Load from PRIVATE_TOOL_ROOT if set
    private_tool_root = get_private_tool_root()
    if private_tool_root:
        private_root_path = Path(private_tool_root)
        private_yaml_path = private_root_path / filename
        if private_yaml_path.exists():
            print(f"Loading {filename} from PRIVATE_TOOL_ROOT: {private_yaml_path}")
            try:
                with open(private_yaml_path, 'r') as file:
                    yaml_data = yaml.safe_load(file)
                    return yaml_data
            except Exception as e:
                print(f"Error loading from PRIVATE_TOOL_ROOT: {e}")

    # Priority 2: Load from private directory in server folder
    private_yaml_path = pwd / PRIVATE_DIRECTORY_NAME / filename
    if private_yaml_path.exists():
        print(f"Loading {filename} from private directory: {private_yaml_path}")
        try:
            with open(private_yaml_path, 'r') as file:
                yaml_data = yaml.safe_load(file)
                return yaml_data
        except Exception as e:
            print(f"Error loading from private directory: {e}")

    # Priority 3: Fallback to default location
    yaml_path = pwd / filename
    if yaml_path.exists():
        print(f"Loading {filename} from default location: {yaml_path}")
        try:
            with open(yaml_path, 'r') as file:
                yaml_data = yaml.safe_load(file)
        except Exception as e:
            print(f"Error loading from default location: {e}")

    return yaml_data

def load_tasks_from_yaml() -> Dict[str, Dict[str, Any]]:
    """Load tasks from the tools.yaml file."""
    yaml_data = load_yaml_from_locations("tools.yaml")
    return yaml_data.get('tasks', {})

def load_tools_from_yaml() -> Dict[str, Dict[str, Any]]:
    """Load tools from the tools.yaml file."""
    yaml_data = load_yaml_from_locations("tools.yaml")
    return yaml_data.get('tools', {})

# Update default parameters with environment variables
env_params = env.get_parameter_dict()
g_default_parameters.update(env_params)

# Dictionary mapping tool names to their executor classes
TOOL_EXECUTORS = {
    "execute_command": ExecuteCommandTool,
    "execute_command_async": ExecuteCommandAsyncTool,
    "query_command_status": QueryCommandStatusTool,
    "execute_task": ExecuteTaskTool,
    "query_task_status": QueryTaskStatusTool,
    "list_tasks": ListTasksTool,
    "list_instructions": ListInstructionsTool,
    "get_instruction": GetInstructionTool,
    "query_script_status": QueryScriptStatusTool,
}

# initialize the tools
yaml_tools = load_tools_from_yaml()
tools_mapping = {}

for name, tool_data in yaml_tools.items():
    if name not in TOOL_EXECUTORS:
        print(f"Adding tool: {name}")
        if tool_data.get('type') == 'script':
            # Create a script-based tool (always async)
            script_tool = ScriptAsyncTool.from_yaml(name, tool_data)
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
