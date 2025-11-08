"""
Agent Step

Execute agent operations within workflows.
"""

import logging
from typing import Any, Dict

from .base import BaseStep
from ...runtime_data import WorkflowContext, StepResult, StepStatus
from ..definition import StepDefinition
from ...agents import ExploreAgent, ExploreAgentConfig
from utils.agent import CLIType


class AgentRegistry:
    """Registry of available agents for workflows."""

    _agents: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, agent_class: Any):
        """
        Register an agent.

        Args:
            name: Agent name
            agent_class: Agent class
        """
        cls._agents[name] = agent_class

    @classmethod
    def get_agent_class(cls, name: str) -> Any:
        """
        Get agent class by name.

        Args:
            name: Agent name

        Returns:
            Agent class

        Raises:
            ValueError: If agent not found
        """
        if name not in cls._agents:
            raise ValueError(f"Unknown agent: {name}")
        return cls._agents[name]

    @classmethod
    def list_agents(cls) -> list:
        """
        List registered agents.

        Returns:
            List of agent names
        """
        return list(cls._agents.keys())


# Register built-in agents
AgentRegistry.register("explore", ExploreAgent)


class AgentStep(BaseStep):
    """
    Agent workflow step.

    Executes an agent operation and stores the result in the workflow context.
    """

    def __init__(self, definition: StepDefinition):
        """
        Initialize agent step.

        Args:
            definition: Step definition

        Raises:
            ValueError: If step is not an agent step
        """
        super().__init__(definition)
        if definition.type != "agent":
            raise ValueError(f"Step {definition.id} is not an agent step")

        self.logger = logging.getLogger(__name__)
        self.agent_type = definition.agent
        self.operation = definition.operation

        if not self.agent_type:
            raise ValueError(f"Agent step {definition.id} must specify 'agent'")
        if not self.operation:
            raise ValueError(f"Agent step {definition.id} must specify 'operation'")

    async def execute(self, context: WorkflowContext) -> StepResult:
        """
        Execute agent operation.

        Args:
            context: Workflow execution context

        Returns:
            StepResult with agent output

        Raises:
            ValueError: If agent or operation invalid
            Exception: If agent execution fails
        """
        # Resolve inputs from context
        inputs = self.resolve_inputs(context)

        self.logger.info(
            f"Executing agent step '{self.step_id}': "
            f"agent={self.agent_type}, operation={self.operation}"
        )

        # Get agent class
        agent_class = AgentRegistry.get_agent_class(self.agent_type)

        # Create agent configuration
        config = self._create_agent_config(inputs, context)

        # Create agent instance
        agent = agent_class(config)

        # Execute operation
        result = await self._execute_operation(agent, inputs)

        # Return step result
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.COMPLETED,
            result=result,
        )

    def _create_agent_config(
        self, inputs: Dict[str, Any], context: WorkflowContext
    ) -> Any:
        """
        Create agent configuration from step config and inputs.

        Args:
            inputs: Resolved step inputs
            context: Workflow context

        Returns:
            Agent configuration object
        """
        step_config = self.definition.config or {}

        # Get configuration values
        cli_type_str = step_config.get("cli_type", "claude")
        cli_type = self._get_cli_type(cli_type_str)

        model = step_config.get("model")
        session_id = step_config.get("session_id") or context.execution_id
        codebase_path = inputs.get("codebase_path")
        working_directories = step_config.get("working_directories")

        # Create appropriate config based on agent type
        if self.agent_type == "explore":
            return ExploreAgentConfig(
                cli_type=cli_type,
                model=model,
                session_id=session_id,
                cwd=codebase_path,
                working_directories=working_directories,
            )
        else:
            # Generic config for other agents
            from utils.agent import AgentConfig

            return AgentConfig(
                cli_type=cli_type,
                model=model,
                session_id=session_id,
            )

    def _get_cli_type(self, cli_type_str: str) -> CLIType:
        """Convert string to CLIType."""
        cli_map = {
            "claude": CLIType.CLAUDE,
            "codex": CLIType.CODEX,
            "copilot": CLIType.COPILOT,
        }
        return cli_map.get(cli_type_str.lower(), CLIType.CLAUDE)

    async def _execute_operation(
        self, agent: Any, inputs: Dict[str, Any]
    ) -> Any:
        """
        Execute the agent operation.

        Args:
            agent: Agent instance
            inputs: Resolved inputs

        Returns:
            Operation result

        Raises:
            ValueError: If operation not supported
        """
        # Map operation to agent method
        if self.agent_type == "explore":
            return await self._execute_explore_operation(agent, inputs)
        else:
            raise ValueError(
                f"Agent type '{self.agent_type}' not supported in workflows yet"
            )

    async def _execute_explore_operation(
        self, agent: ExploreAgent, inputs: Dict[str, Any]
    ) -> str:
        """
        Execute ExploreAgent operation.

        Args:
            agent: ExploreAgent instance
            inputs: Operation inputs

        Returns:
            Operation result

        Raises:
            ValueError: If operation not supported
        """
        codebase_path = inputs.get("codebase_path")
        focus_areas = inputs.get("focus_areas")

        if self.operation == "explore":
            question = inputs.get("question")
            if not question:
                raise ValueError("explore operation requires 'question' input")
            return await agent.explore(
                question=question,
                codebase_path=codebase_path,
                focus_areas=focus_areas,
            )

        elif self.operation == "find_implementation":
            feature = inputs.get("feature_or_function")
            if not feature:
                raise ValueError(
                    "find_implementation operation requires 'feature_or_function' input"
                )
            return await agent.find_implementation(
                feature_or_function=feature,
                codebase_path=codebase_path,
            )

        elif self.operation == "analyze_structure":
            component = inputs.get("component_or_module")
            return await agent.analyze_structure(
                component_or_module=component,
                codebase_path=codebase_path,
            )

        elif self.operation == "find_usage":
            symbol = inputs.get("symbol")
            if not symbol:
                raise ValueError("find_usage operation requires 'symbol' input")
            return await agent.find_usage(
                symbol=symbol,
                codebase_path=codebase_path,
            )

        elif self.operation == "explain_flow":
            flow = inputs.get("flow_description")
            if not flow:
                raise ValueError(
                    "explain_flow operation requires 'flow_description' input"
                )
            return await agent.explain_flow(
                flow_description=flow,
                codebase_path=codebase_path,
            )

        else:
            raise ValueError(
                f"Unknown operation '{self.operation}' for ExploreAgent"
            )
