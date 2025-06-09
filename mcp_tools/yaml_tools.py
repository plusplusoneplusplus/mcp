"""YAML-based tools loader.

This module handles loading tool definitions from YAML files and creating
dynamic tool implementations that can be registered with the plugin system.
"""

import logging
import os
import inspect
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Type, Tuple

from mcp_tools.interfaces import ToolInterface, CommandExecutorInterface
from mcp_tools.plugin import register_tool, registry
from mcp_tools.dependency import injector
from utils.secret_scanner import redact_secrets
from utils.output_processor import OutputLimiter

# Configuration
DEFAULT_WAIT_FOR_QUERY = True  # Default wait for task
DEFAULT_STATUS_QUERY_TIMEOUT = 25  # Default timeout in seconds for status queries

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
        if tool_name is None and hasattr(self.__class__, "_tool_name"):
            tool_name = self.__class__._tool_name
        if tool_data is None and hasattr(self.__class__, "_tool_data"):
            tool_data = getattr(self.__class__, "_tool_data", {})

        # Fall back to a default if still not set
        if tool_name is None:
            tool_name = "unknown_yaml_tool"
        if tool_data is None:
            tool_data = {}

        # Ensure tool_data is a dictionary
        if not isinstance(tool_data, dict):
            logger.warning(f"Invalid tool_data type for tool '{tool_name}': {type(tool_data)}. Using empty dict.")
            tool_data = {}

        self._name = tool_name
        self._description = tool_data.get("description", "")
        self._input_schema = tool_data.get(
            "inputSchema", {"type": "object", "properties": {}, "required": []}
        )
        self._tool_data = tool_data
        self._tool_type = tool_data.get("type", "object")

        # Get command executor from injector if not provided
        if command_executor is None:
            try:
                self._command_executor = injector.get_tool_instance("command_executor")
            except Exception as e:
                logger.warning(f"Failed to get command executor from injector: {e}")
                self._command_executor = None
        else:
            self._command_executor = command_executor

        # Initialize output limiter
        self._output_limiter = OutputLimiter()

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
        # Ensure input_schema is a dictionary
        if not isinstance(self._input_schema, dict):
            logger.warning(f"Invalid input_schema type for tool '{self._name}': {type(self._input_schema)}. Using default.")
            return {"type": "object", "properties": {}, "required": []}
        return self._input_schema

    async def execute_tool(self, arguments: Dict[str, Any]) -> Any:
        """Execute the tool based on its type.

        Args:
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if not self._command_executor:
            return {"success": False, "error": "Command executor not available"}

        logger.info(f"Executing tool: {self._name}, type: {self._tool_type}")

        if self._tool_type == "script":
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
            logger.warning(
                f"Tool '{self._name}' with type '{self._tool_type}' is not fully implemented"
            )
            return [
                {
                    "type": "text",
                    "text": f"Tool '{self._name}' is defined in YAML but not fully implemented",
                }
            ]

    async def _execute_script(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a script-based tool.

        Args:
            arguments: Tool arguments

        Returns:
            Script execution result
        """
        # Validate input schema first
        input_schema = self._tool_data.get("inputSchema", {})
        validation_error = self._validate_input_schema(arguments, input_schema)
        if validation_error:
            return [
                {"type": "text", "text": f"Input validation error: {validation_error}"}
            ]

        # Get OS-specific script
        import platform

        os_type = platform.system().lower()

        script = None
        scripts = self._tool_data.get("scripts", {})

        if os_type in scripts:
            script = scripts[os_type]
        elif "script" in self._tool_data:
            script = self._tool_data["script"]

        if not script:
            return [
                {
                    "type": "text",
                    "text": f"Error: No script defined for tool '{self._name}' on {os_type}",
                }
            ]

        # Format the script with arguments
        try:
            # Add server_dir parameter
            server_dir = self._get_server_dir()
            params = {
                "pwd": str(server_dir),
                "private_tool_root": os.environ.get("PRIVATE_TOOL_ROOT", ""),
            }

            # Add additional parameters from tool data if specified
            additional_params = self._tool_data.get("parameters", {})
            for param_name, param_value in additional_params.items():
                if param_name not in params:  # Don't override existing params
                    params[param_name] = param_value

            # Add user arguments
            params.update(arguments)

            # Log parameters being used
            logger.info(
                f"Executing script for tool '{self._name}' with parameters: {params}"
            )

            try:
                formatted_script = script.format(**params)
            except KeyError as e:
                return [
                    {
                        "type": "text",
                        "text": f"Error: Missing required parameter in script: {str(e)}",
                    }
                ]

            # Execute the script
            logger.info(f"Executing script: {formatted_script}")
            result = await self._command_executor.execute_async(formatted_script)

            return [
                {
                    "type": "text",
                    "text": f"Script started with token: {result.get('token')}\nStatus: {result.get('status')}\nPID: {result.get('pid')}",
                }
            ]
        except Exception as e:
            logger.exception(f"Error executing script for tool '{self._name}'")
            return [{"type": "text", "text": f"Error executing script: {str(e)}"}]

    def _validate_input_schema(
        self, arguments: Dict[str, Any], schema: Dict[str, Any]
    ) -> Optional[str]:
        """Validate input arguments against the schema.

        Args:
            arguments: The input arguments to validate
            schema: The input schema to validate against

        Returns:
            Error message if validation fails, None if validation succeeds
        """
        if not schema:
            return None

        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in arguments:
                return f"Missing required field: {field}"

        # Validate properties
        properties = schema.get("properties", {})
        for arg_name, arg_value in arguments.items():
            if arg_name in properties:
                prop_schema = properties[arg_name]
                # Validate type
                expected_type = prop_schema.get("type")
                if expected_type:
                    if expected_type == "string" and not isinstance(arg_value, str):
                        return f"Field '{arg_name}' must be a string"
                    elif expected_type == "number" and not isinstance(
                        arg_value, (int, float)
                    ):
                        return f"Field '{arg_name}' must be a number"
                    elif expected_type == "integer" and not isinstance(arg_value, int):
                        return f"Field '{arg_name}' must be an integer"
                    elif expected_type == "boolean" and not isinstance(arg_value, bool):
                        return f"Field '{arg_name}' must be a boolean"
                    elif expected_type == "array" and not isinstance(arg_value, list):
                        return f"Field '{arg_name}' must be an array"
                    elif expected_type == "object" and not isinstance(arg_value, dict):
                        return f"Field '{arg_name}' must be an object"

                # Validate enum if specified
                if "enum" in prop_schema and arg_value not in prop_schema["enum"]:
                    return f"Field '{arg_name}' must be one of: {', '.join(map(str, prop_schema['enum']))}"

                # Validate pattern if specified
                if "pattern" in prop_schema:
                    import re

                    if not re.match(prop_schema["pattern"], str(arg_value)):
                        return f"Field '{arg_name}' does not match required pattern: {prop_schema['pattern']}"

        return None

    def _apply_output_attachment_config(self, result: Dict, config: Dict) -> Dict:
        """Apply output attachment configuration to command result.

        Args:
            result: The command execution result
            config: The post_processing configuration

        Returns:
            Modified result with output attachment configuration applied
        """
        # Create a copy to avoid modifying the original
        processed_result = result.copy()

        # Control stdout attachment
        if not config.get("attach_stdout", True):
            processed_result["output"] = ""

        # Control stderr attachment
        attach_stderr = config.get("attach_stderr", True)
        stderr_on_failure_only = config.get("stderr_on_failure_only", False)

        if not attach_stderr or (stderr_on_failure_only and result.get("success", False)):
            processed_result["error"] = ""

        return processed_result

    def _apply_security_filtering(self, stdout: str, stderr: str, config: Dict) -> Tuple[str, str]:
        """Apply security filtering using existing proven security detection.

        Args:
            stdout: Standard output content
            stderr: Standard error content
            config: Security filtering configuration

        Returns:
            Tuple of (filtered_stdout, filtered_stderr)
        """
        apply_to = config.get("apply_to", ["stdout", "stderr"])

        filtered_stdout = stdout
        filtered_stderr = stderr
        all_findings = []

        if "stdout" in apply_to:
            filtered_stdout, stdout_findings = redact_secrets(stdout)
            all_findings.extend(stdout_findings)

        if "stderr" in apply_to:
            filtered_stderr, stderr_findings = redact_secrets(stderr)
            all_findings.extend(stderr_findings)

        # Log security alerts (without exposing secrets)
        if all_findings and config.get("log_findings", True):
            self._log_security_findings(all_findings)

        return filtered_stdout, filtered_stderr

    def _log_security_findings(self, findings: List[Dict]) -> None:
        """Log security findings without revealing secrets (following browser client pattern).

        Args:
            findings: List of security findings from the secret scanner
        """
        if not findings:
            return

        # Group findings by type
        secret_types = {}
        for finding in findings:
            secret_type = finding.get("SecretType", "Unknown")
            line_num = finding.get("LineNumber", 0)

            if secret_type not in secret_types:
                secret_types[secret_type] = []
            secret_types[secret_type].append(line_num)

        # Log security alert
        logger.warning(
            f"*******************************************************************\n"
            f"*** SECURITY ALERT: Detected and redacted {len(findings)} potential secrets\n"
            f"*** Tool: {self._name}\n"
            f"*** Type: Script output\n"
            f"*******************************************************************"
        )

        # Log details for each type
        for secret_type, line_numbers in secret_types.items():
            line_ranges = self._summarize_line_numbers(line_numbers)
            logger.warning(
                f"SECURITY DETAIL: Found {len(line_numbers)} instance(s) of '{secret_type}' "
                f"at {line_ranges} in tool '{self._name}' output"
            )

    def _summarize_line_numbers(self, line_numbers: List[int]) -> str:
        """Create a readable summary of line numbers.

        Args:
            line_numbers: List of line numbers

        Returns:
            A string representation of the line numbers in a readable format
        """
        if not line_numbers:
            return "unknown locations"

        # Sort line numbers
        sorted_lines = sorted(line_numbers)

        if len(sorted_lines) == 1:
            return f"line {sorted_lines[0]}"
        elif len(sorted_lines) == 2:
            return f"lines {sorted_lines[0]} and {sorted_lines[1]}"
        else:
            # Group consecutive numbers into ranges
            ranges = []
            range_start = sorted_lines[0]
            range_end = range_start

            for line in sorted_lines[1:]:
                if line == range_end + 1:
                    range_end = line
                else:
                    if range_start == range_end:
                        ranges.append(f"{range_start}")
                    else:
                        ranges.append(f"{range_start}-{range_end}")
                    range_start = line
                    range_end = line

            # Add the last range
            if range_start == range_end:
                ranges.append(f"{range_start}")
            else:
                ranges.append(f"{range_start}-{range_end}")

            if len(ranges) == 1:
                return f"lines {ranges[0]}"
            elif len(ranges) == 2:
                return f"lines {ranges[0]} and {ranges[1]}"
            else:
                last_range = ranges.pop()
                return f"lines {', '.join(ranges)}, and {last_range}"

    def _format_result(self, result: Dict, token: str) -> str:
        """Format the final result for display.

        Args:
            result: The processed command execution result
            token: The process token

        Returns:
            Formatted result string
        """
        output_text = result.get("output", "")
        error_text = result.get("error", "")

        # Build the result text
        result_parts = [f"Process completed (token: {token})", f"Success: {result.get('success')}"]

        # Add output section if there's content
        if output_text and output_text.strip():
            result_parts.append(f"Output:\n{output_text}")

        # Add error section if there's content
        if error_text and error_text.strip():
            result_parts.append(f"Error:\n{error_text}")

        return "\n".join(result_parts)

    async def _execute_task(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a predefined task.

        Args:
            arguments: Tool arguments

        Returns:
            Task execution result
        """
        task_name = arguments.get("task_name", "")
        if not task_name:
            return [{"type": "text", "text": "Error: Task name is required"}]

        # Load tasks from YAML
        tasks = self._load_tasks_from_yaml()
        if task_name not in tasks:
            return [{"type": "text", "text": f"Error: Task '{task_name}' not found"}]

        task = tasks[task_name]

        # Get OS-specific command
        import platform

        os_type = platform.system().lower()

        command = None
        if "commands" in task and os_type in task["commands"]:
            command = task["commands"][os_type]
        elif "command" in task:
            command = task["command"]

        if not command:
            return [
                {
                    "type": "text",
                    "text": f"Error: No command defined for task '{task_name}' on {os_type}",
                }
            ]

        # Format the command with parameters
        try:
            server_dir = self._get_server_dir()
            params = {
                "pwd": str(server_dir),
                "private_tool_root": os.environ.get("PRIVATE_TOOL_ROOT", ""),
            }
            # Format command with parameters
            formatted_command = command.format(**params)

            # Execute the command
            logger.info(f"Executing task '{task_name}': {formatted_command}")
            result = await self._command_executor.execute_async(formatted_command)

            return [
                {
                    "type": "text",
                    "text": f"Task '{task_name}' started with token: {result.get('token')}\nStatus: {result.get('status')}\nPID: {result.get('pid')}",
                }
            ]
        except Exception as e:
            logger.exception(f"Error executing task '{task_name}'")
            return [{"type": "text", "text": f"Error executing task: {str(e)}"}]

    async def _query_status(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query the status of an async process.

        Args:
            arguments: Tool arguments

        Returns:
            Process status
        """
        token = arguments.get("token", "")
        if not token:
            return [{"type": "text", "text": "Error: Token is required"}]

        wait = arguments.get("wait", DEFAULT_WAIT_FOR_QUERY)
        timeout = arguments.get(
            "timeout", DEFAULT_STATUS_QUERY_TIMEOUT
        )  # Use default timeout from config

        try:
            import asyncio

            start_time = asyncio.get_event_loop().time()

            while True:
                result = await self._command_executor.query_process(
                    token, wait=False, timeout=None
                )
                current_time = asyncio.get_event_loop().time()
                elapsed = current_time - start_time

                # If process completed, return the result
                if result.get("status") == "completed":
                    # Apply post-processing configuration
                    post_config = self._tool_data.get("post_processing", {})

                    # Apply security filtering if enabled (default: True for security)
                    security_config = post_config.get("security_filtering", {})
                    if security_config.get("enabled", True):
                        stdout_content = result.get("output", "")
                        stderr_content = result.get("error", "")

                        filtered_stdout, filtered_stderr = self._apply_security_filtering(
                            stdout_content, stderr_content, security_config
                        )

                        # Update result with filtered content
                        result = result.copy()
                        result["output"] = filtered_stdout
                        result["error"] = filtered_stderr

                    # Apply output length limits if configured
                    output_limits = post_config.get("output_limits", {})
                    if output_limits:
                        result = self._output_limiter.apply_output_limits(result, output_limits)

                    processed_result = self._apply_output_attachment_config(result, post_config)

                    return [
                        {
                            "type": "text",
                            "text": self._format_result(processed_result, token),
                        }
                    ]

                # If timeout specified and exceeded, return current status
                if timeout is not None and elapsed >= timeout:
                    status_text = f"Process status (token: {token}): {result.get('status')} (timeout after {elapsed:.1f}s)"
                    if "pid" in result:
                        status_text += f"\nPID: {result.get('pid')}"
                    return [{"type": "text", "text": status_text}]

                # If not waiting or no timeout specified, return current status
                if not wait:
                    status_text = (
                        f"Process status (token: {token}): {result.get('status')}"
                    )
                    if "pid" in result:
                        status_text += f"\nPID: {result.get('pid')}"
                    return [{"type": "text", "text": status_text}]

                # Wait 1 second before next check
                await asyncio.sleep(1)

        except Exception as e:
            logger.exception(f"Error querying process status")
            return [
                {"type": "text", "text": f"Error querying process status: {str(e)}"}
            ]

    async def _list_tasks(self) -> List[Dict[str, Any]]:
        """List all available tasks.

        Returns:
            List of tasks
        """
        tasks = self._load_tasks_from_yaml()

        if not tasks:
            return [{"type": "text", "text": "No tasks available"}]

        # Format the task list
        task_list = []
        for name, task in tasks.items():
            description = task.get("description", "No description")
            task_list.append(f"- {name}: {description}")

        return [{"type": "text", "text": "Available tasks:\n" + "\n".join(task_list)}]

    async def _list_instructions(self) -> List[Dict[str, Any]]:
        """List all available instructions.

        Returns:
            List of instructions
        """
        return [{"type": "text", "text": "No instructions available"}]

    async def _get_instruction(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get a specific instruction.

        Args:
            arguments: Tool arguments

        Returns:
            Instruction details
        """
        name = arguments.get("name", "")
        if not name:
            return [{"type": "text", "text": "Error: Instruction name is required"}]

        return [{"type": "text", "text": f"Instruction '{name}' not found"}]

    def _load_tasks_from_yaml(self) -> Dict[str, Dict[str, Any]]:
        """Load tasks from the tools.yaml file."""
        yaml_data = self._load_yaml_from_locations("tools.yaml")
        return yaml_data.get("tasks", {})

    def _load_yaml_from_locations(self, filename: str) -> dict:
        """Load YAML file from multiple possible locations with priority order.

        Args:
            filename: Name of the YAML file to load

        Returns:
            Parsed YAML data as dictionary
        """
        yaml_data = {}

        try:
            # Import the plugin config
            from mcp_tools.plugin_config import config

            # Get paths from configuration
            locations = config.get_yaml_tool_paths()

            # Check all locations in order
            for location in locations:
                yaml_path = location / filename
                if yaml_path.exists():
                    logger.info(f"Loading {filename} from {yaml_path}")
                    try:
                        with open(yaml_path, "r") as file:
                            content = file.read()
                            try:
                                yaml_data = yaml.safe_load(content)

                                # Validate the loaded YAML data
                                if not isinstance(yaml_data, dict):
                                    logger.error(
                                        f"Invalid YAML format in {yaml_path}: root must be a dictionary"
                                    )
                                    yaml_data = {}

                                # Make sure 'tools' key exists and is a dictionary
                                if "tools" in yaml_data and not isinstance(
                                    yaml_data["tools"], dict
                                ):
                                    logger.error(
                                        f"Invalid 'tools' section in {yaml_path}: must be a dictionary"
                                    )
                                    yaml_data["tools"] = {}

                                # Make sure 'tasks' key exists and is a dictionary if present
                                if "tasks" in yaml_data and not isinstance(
                                    yaml_data["tasks"], dict
                                ):
                                    logger.error(
                                        f"Invalid 'tasks' section in {yaml_path}: must be a dictionary"
                                    )
                                    yaml_data["tasks"] = {}

                                return yaml_data
                            except yaml.YAMLError as e:
                                logger.error(f"YAML parsing error in {yaml_path}: {e}")
                                # Return empty dict instead of invalid data
                                return {}
                    except Exception as e:
                        logger.error(f"Error loading {filename} from {yaml_path}: {e}")

            # If we got here, we didn't find a valid file
            logger.warning(
                f"Could not find {filename} in any of the expected locations: {[str(p) for p in locations]}"
            )
        except Exception as e:
            logger.error(f"Error finding {filename}: {e}")

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


def get_yaml_tool_names() -> set:
    """Get the names of tools defined in YAML.

    Returns:
        Set of tool names defined in YAML
    """
    logger.info("Getting YAML tool names")

    try:
        # Import plugin config
        from mcp_tools.plugin_config import config

        # Create a base instance to load YAML
        base_tool = YamlToolBase()
        yaml_data = base_tool._load_yaml_from_locations("tools.yaml")
        tools_data = yaml_data.get("tools", {})

        # Get tool names and filter out disabled tools
        tool_names = {
            name
            for name, data in tools_data.items()
            if data.get("enabled", True) != False
        }

        logger.info(f"Found {len(tool_names)} tools in YAML: {', '.join(tool_names)}")
        return tool_names
    except Exception as e:
        logger.error(f"Error getting YAML tool names: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return set()


def load_yaml_tools() -> List[Type[ToolInterface]]:
    """Load tools from tools.yaml and register them with comprehensive error handling.

    Returns:
        List of registered YAML tool classes
    """
    # Import plugin config
    from mcp_tools.plugin_config import config

    # Skip if YAML tools are disabled
    if not config.register_yaml_tools:
        logger.info("YAML tool registration is disabled, skipping")
        return []

    logger.info("Loading YAML-defined tools")

    successful_tools = []
    failed_tools = []

    try:
        # Create a base instance to load YAML
        try:
            base_tool = YamlToolBase()
            yaml_data = base_tool._load_yaml_from_locations("tools.yaml")
        except Exception as e:
            logger.error(f"Error loading tools.yaml file: {e}")
            return []

        tools_data = yaml_data.get("tools", {})

        if not tools_data:
            logger.warning("No tools found in tools.yaml")
            return []

        logger.info(f"Found {len(tools_data)} tools in tools.yaml")

        # DIRECT FIX: Ensure all tools have valid inputSchema.type values
        # This is a quick fix to handle the specific error reported
        for tool_name, tool_data in tools_data.items():
            try:
                if "inputSchema" in tool_data and isinstance(
                    tool_data["inputSchema"], dict
                ):
                    if "type" in tool_data["inputSchema"] and not isinstance(
                        tool_data["inputSchema"]["type"], str
                    ):
                        logger.warning(
                            f"DIRECT FIX: Tool '{tool_name}' has non-string inputSchema.type: {tool_data['inputSchema']['type']} ({type(tool_data['inputSchema']['type'])})"
                        )
                        # Force set to string "object"
                        tool_data["inputSchema"]["type"] = "object"
            except Exception as e:
                logger.warning(f"Error applying schema fix to tool '{tool_name}': {e}")

        # Debug output for all tools before processing
        for i, (name, tool_data) in enumerate(tools_data.items()):
            try:
                logger.debug(f"DEBUG Tool #{i}: {name}")
                logger.debug(f"  Description: {tool_data.get('description', 'N/A')}")
                logger.debug(f"  Tool Type: {tool_data.get('type', 'N/A')}")
                if "inputSchema" in tool_data:
                    input_schema = tool_data["inputSchema"]
                    logger.debug(f"  InputSchema: {type(input_schema)}")

                    if isinstance(input_schema, dict):
                        schema_type = input_schema.get("type")
                        logger.debug(
                            f"  Schema.type: {schema_type} (type: {type(schema_type)})"
                        )
                        logger.debug(
                            f"  Properties: {input_schema.get('properties', {})}"
                        )
                        logger.debug(f"  Required: {input_schema.get('required', [])}")
                    else:
                        logger.debug(f"  Schema value (invalid): {input_schema}")
                else:
                    logger.debug("  No inputSchema found")
            except Exception as e:
                logger.warning(f"Error logging debug info for tool '{name}': {e}")

        # List to hold dynamically created classes
        yaml_tool_classes = []

        # Process each tool defined in the YAML with individual error handling
        for name, tool_data in tools_data.items():
            try:
                logger.debug(f"Processing YAML tool: {name}")

                # Skip disabled tools
                if tool_data.get("enabled", True) == False:
                    logger.info(f"Tool '{name}' is disabled in tools.yaml")
                    continue

                # Comprehensive validation of tool data
                validation_errors = []

                try:
                    # Verify basic structure
                    if not isinstance(tool_data, dict):
                        validation_errors.append(
                            f"Invalid tool data type: {type(tool_data)}"
                        )
                    else:
                        # Check required fields
                        if "description" not in tool_data:
                            validation_errors.append("Missing 'description' field")
                        elif not isinstance(tool_data["description"], str):
                            validation_errors.append(
                                f"Invalid description type: {type(tool_data['description'])}"
                            )

                        if "inputSchema" not in tool_data:
                            validation_errors.append("Missing 'inputSchema' field")
                        elif not isinstance(tool_data["inputSchema"], dict):
                            validation_errors.append(
                                f"Invalid inputSchema type: {type(tool_data['inputSchema'])}"
                            )
                        else:
                            # Validate inputSchema structure
                            input_schema = tool_data["inputSchema"]
                            if "type" not in input_schema:
                                validation_errors.append(
                                    "Missing 'type' in inputSchema"
                                )
                            elif not isinstance(input_schema["type"], str):
                                validation_errors.append(
                                    f"Invalid inputSchema.type: {type(input_schema['type'])}"
                                )

                    if validation_errors:
                        error_msg = f"Validation failed: {'; '.join(validation_errors)}"
                        logger.error(f"Tool '{name}' validation errors: {error_msg}")
                        failed_tools.append(f"{name}: {error_msg}")
                        continue

                except Exception as validation_error:
                    error_msg = f"Validation exception: {str(validation_error)}"
                    logger.error(f"Tool '{name}' validation exception: {error_msg}")
                    failed_tools.append(f"{name}: {error_msg}")
                    continue

                # Create a dynamic class for this tool with error handling
                try:
                    # Ensure name is set in the tool_data
                    if "name" not in tool_data or not tool_data["name"]:
                        tool_data["name"] = name
                        logger.debug(f"Setting missing name property for tool '{name}'")

                    # Log the final tool data
                    logger.debug(f"Creating class for '{name}' with validated data")

                    # Create the tool class
                    tool_class = type(
                        f"YamlTool_{name}",
                        (YamlToolBase,),
                        {"_tool_name": name, "_tool_data": tool_data},
                    )

                    # Validate the created class by testing instantiation
                    try:
                        test_instance = tool_class()
                        test_name = test_instance.name
                        test_description = test_instance.description
                        test_schema = test_instance.input_schema

                        logger.debug(
                            f"Tool class '{name}' instantiation test successful"
                        )
                    except Exception as instantiation_error:
                        error_msg = f"Class instantiation test failed: {str(instantiation_error)}"
                        logger.error(f"Tool '{name}' instantiation error: {error_msg}")
                        failed_tools.append(f"{name}: {error_msg}")
                        continue

                    # Register the tool
                    logger.debug(f"Registering YAML tool: {name}")
                    tool_class = register_tool(source="yaml")(tool_class)
                    yaml_tool_classes.append(tool_class)
                    successful_tools.append(name)
                    logger.info(f"Successfully registered YAML tool: {name}")

                except Exception as create_error:
                    error_msg = (
                        f"Class creation/registration failed: {str(create_error)}"
                    )
                    logger.error(
                        f"Error creating or registering class for YAML tool '{name}': {error_msg}"
                    )
                    failed_tools.append(f"{name}: {error_msg}")

            except Exception as e:
                error_msg = f"General processing error: {str(e)}"
                logger.error(f"Error processing YAML tool '{name}': {error_msg}")
                failed_tools.append(f"{name}: {error_msg}")
                import traceback

                logger.debug(
                    f"Full traceback for tool '{name}': {traceback.format_exc()}"
                )

        # Log comprehensive summary
        logger.info(f"YAML tools loading summary:")
        logger.info(f"  - Total tools in YAML: {len(tools_data)}")
        logger.info(f"  - Successfully loaded: {len(successful_tools)}")
        logger.info(f"  - Failed to load: {len(failed_tools)}")

        if successful_tools:
            logger.info(f"  - Successful tools: {', '.join(successful_tools)}")

        if failed_tools:
            logger.warning(f"  - Failed tools:")
            for failed_tool in failed_tools:
                logger.warning(f"    - {failed_tool}")

        return yaml_tool_classes
    except Exception as e:
        logger.error(f"Critical error loading YAML tools: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
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
