"""Agent Tool for MCP.

This module provides an MCP tool for invoking specialized agents like ExploreAgent
to perform codebase exploration and analysis tasks.
"""

import logging
from typing import Any, Dict, Optional
from enum import Enum
from pathlib import Path

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool

from ..agents import ExploreAgent, ExploreAgentConfig
from utils.agent import CLIType


class AgentOperationType(str, Enum):
    """Enumeration of supported agent operations."""

    EXPLORE = "explore"
    FIND_IMPLEMENTATION = "find_implementation"
    ANALYZE_STRUCTURE = "analyze_structure"
    FIND_USAGE = "find_usage"
    EXPLAIN_FLOW = "explain_flow"


@register_tool(ecosystem="general", os_type="all")
class AgentTool(ToolInterface):
    """Agent tool for codebase exploration and analysis through MCP."""

    def __init__(self):
        """Initialize the Agent tool."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._agents: Dict[str, ExploreAgent] = {}

    @property
    def name(self) -> str:
        """Return the tool name."""
        return "agent"

    @property
    def description(self) -> str:
        """Return the tool description."""
        return "Invoke specialized AI agents for codebase exploration, implementation finding, structure analysis, and more"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The agent operation to perform",
                    "enum": [op.value for op in AgentOperationType],
                },
                "prompt": {
                    "type": "string",
                    "description": "Main input for the operation (question for explore, symbol name for find_implementation/find_usage, flow description for explain_flow, component name for analyze_structure)",
                },
                "context": {
                    "type": "object",
                    "description": "Optional context and configuration",
                    "properties": {
                        "codebase_path": {
                            "type": "string",
                            "description": "Path to the codebase root directory",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID for maintaining conversation context",
                        },
                        "model": {
                            "type": "string",
                            "description": "Model to use (e.g., 'haiku', 'gpt-4')",
                        },
                        "cli_type": {
                            "type": "string",
                            "description": "CLI type: claude, codex, or copilot",
                            "enum": ["claude", "codex", "copilot"],
                        },
                        "focus_areas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific areas to focus on",
                        },
                        "working_directories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Working directories for context",
                        },
                    },
                },
            },
            "required": ["operation", "prompt"],
        }

    def _get_cli_type(self, cli_type_str: Optional[str]) -> CLIType:
        """Convert string CLI type to CLIType enum."""
        if not cli_type_str:
            return CLIType.CLAUDE

        cli_type_map = {
            "claude": CLIType.CLAUDE,
            "codex": CLIType.CODEX,
            "copilot": CLIType.COPILOT,
        }

        return cli_type_map.get(cli_type_str.lower(), CLIType.CLAUDE)

    def _get_or_create_agent(
        self,
        session_id: Optional[str],
        cli_type: CLIType,
        model: Optional[str],
        codebase_path: Optional[str],
        working_directories: Optional[list],
    ) -> ExploreAgent:
        """Get or create an agent for the session."""
        # Use session_id as cache key, or "default" if not provided
        cache_key = session_id or "default"

        if cache_key not in self._agents:
            config = ExploreAgentConfig(
                cli_type=cli_type,
                model=model,
                session_id=session_id,
                cwd=codebase_path,
                working_directories=working_directories,
            )
            self._agents[cache_key] = ExploreAgent(config)

        return self._agents[cache_key]

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"error": "Missing required parameter: operation"}

        return await self.execute_function(operation, arguments)

    async def execute_function(
        self, function_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an agent function."""
        try:
            operation = AgentOperationType(function_name)

            # Extract prompt (allow empty string for operations like analyze_structure)
            prompt = parameters.get("prompt")
            if prompt is None:
                return {"error": "Missing required parameter: prompt"}

            # Extract context (optional)
            context = parameters.get("context", {})
            codebase_path = context.get("codebase_path")
            focus_areas = context.get("focus_areas")
            cli_type_str = context.get("cli_type", "claude")
            model = context.get("model")
            session_id = context.get("session_id")
            working_directories = context.get("working_directories")

            # Convert CLI type
            cli_type = self._get_cli_type(cli_type_str)

            # Get or create agent
            agent = self._get_or_create_agent(
                session_id=session_id,
                cli_type=cli_type,
                model=model,
                codebase_path=codebase_path,
                working_directories=working_directories,
            )

            # Execute operation based on type
            result = None

            if operation == AgentOperationType.EXPLORE:
                result = await agent.explore(
                    question=prompt,
                    codebase_path=codebase_path,
                    focus_areas=focus_areas,
                )

            elif operation == AgentOperationType.FIND_IMPLEMENTATION:
                result = await agent.find_implementation(
                    feature_or_function=prompt,
                    codebase_path=codebase_path,
                )

            elif operation == AgentOperationType.ANALYZE_STRUCTURE:
                # For analyze_structure, prompt can be optional (None means analyze entire codebase)
                component = prompt if prompt.strip() else None
                result = await agent.analyze_structure(
                    component_or_module=component,
                    codebase_path=codebase_path,
                )

            elif operation == AgentOperationType.FIND_USAGE:
                result = await agent.find_usage(
                    symbol=prompt,
                    codebase_path=codebase_path,
                )

            elif operation == AgentOperationType.EXPLAIN_FLOW:
                result = await agent.explain_flow(
                    flow_description=prompt,
                    codebase_path=codebase_path,
                )

            else:
                return {"error": f"Unknown operation: {operation}"}

            return {
                "success": True,
                "operation": operation.value,
                "result": result,
                "session_id": agent._get_session_id(),
            }

        except ValueError as e:
            self.logger.error(f"Invalid operation: {function_name}")
            return {"error": f"Invalid operation: {function_name}"}
        except Exception as e:
            self.logger.error(f"Error executing agent operation: {e}", exc_info=True)
            return {"error": f"Agent operation failed: {str(e)}"}

    async def cleanup(self):
        """Clean up resources."""
        self._agents.clear()
