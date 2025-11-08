"""
Automation Plugin

AI-powered automation for development tasks including specialized agents for codebase
exploration, code review, and pre-defined workflows for common development patterns.

This plugin provides:
- AI Agents: Specialized agents for specific tasks (exploration, review, etc.)
- Workflows: Pre-defined multi-step automation workflows (future)
- MCP Tools: Tool interfaces for invoking agents and workflows via MCP
"""

from .agents import ExploreAgent, ExploreAgentConfig, explore_codebase
from .tools import AgentTool
from .runtime_data import WorkflowContext, StepResult, StepStatus

__all__ = [
    "ExploreAgent",
    "ExploreAgentConfig",
    "explore_codebase",
    "AgentTool",
    "WorkflowContext",
    "StepResult",
    "StepStatus",
]
