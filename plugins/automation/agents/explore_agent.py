"""
Explore Agent

A specialized agent for exploring codebases and answering questions about code structure,
implementations, and patterns.
"""

import logging
from typing import Optional, List
from dataclasses import dataclass, field
from pathlib import Path

from utils.agent import SpecializedAgent, AgentConfig, CLIType

logger = logging.getLogger(__name__)


@dataclass
class ExploreAgentConfig(AgentConfig):
    """Configuration for the Explore Agent"""

    # Code exploration specific settings
    search_paths: List[str] = field(default_factory=list)
    """Paths to search within the codebase"""

    file_extensions: List[str] = field(default_factory=lambda: [".py", ".js", ".ts", ".tsx", ".java", ".go", ".rs"])
    """File extensions to focus on during exploration"""

    max_file_size: int = 100000
    """Maximum file size in bytes to read (default: 100KB)"""

    ignore_patterns: List[str] = field(default_factory=lambda: [
        "node_modules",
        "__pycache__",
        ".git",
        "*.pyc",
        "dist",
        "build",
        ".venv",
        "venv",
    ])
    """Patterns to ignore during exploration"""


class ExploreAgent(SpecializedAgent):
    """
    Specialized agent for codebase exploration and analysis.

    This agent is designed to:
    - Explore codebase structure and organization
    - Find specific files, classes, functions, or patterns
    - Analyze code implementations and dependencies
    - Answer questions about how the codebase works
    - Identify architectural patterns and design decisions
    """

    def __init__(self, config: ExploreAgentConfig):
        """
        Initialize the Explore Agent.

        Args:
            config: ExploreAgentConfig with exploration-specific settings
        """
        if not isinstance(config, ExploreAgentConfig):
            # Convert generic AgentConfig to ExploreAgentConfig
            config = ExploreAgentConfig(
                cli_type=config.cli_type,
                model=config.model,
                session_id=config.session_id,
                session_storage_path=config.session_storage_path,
                skip_permissions=config.skip_permissions,
                cli_path=config.cli_path,
                timeout=config.timeout,
                working_directories=config.working_directories,
                cwd=config.cwd,
                include_session_in_prompt=config.include_session_in_prompt,
            )

        super().__init__(config)
        self.explore_config: ExploreAgentConfig = config

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for the Explore Agent.

        Returns:
            System prompt that defines the agent's codebase exploration behavior
        """
        if self.config.include_session_in_prompt:
            return self.get_default_system_prompt(
                agent_role="You are an expert codebase explorer and code analyst.",
                custom_instructions=self._get_exploration_instructions()
            )

        return f"""# Codebase Exploration Agent

## Role
You are an expert codebase explorer and code analyst. Your primary function is to help users understand and navigate complex codebases by:
- Finding specific files, classes, functions, or code patterns
- Analyzing code structure and dependencies
- Explaining how different parts of the codebase work
- Identifying architectural patterns and design decisions
- Answering questions about implementations

## Capabilities
You have access to powerful code exploration tools:
1. **File Search**: Find files by name patterns (glob patterns)
2. **Content Search**: Search for specific code patterns or text (grep/ripgrep)
3. **File Reading**: Read and analyze file contents
4. **Pattern Recognition**: Identify common patterns and architectural decisions

## Exploration Guidelines

### 1. Search Strategy
- Start with broad searches and narrow down based on findings
- Use glob patterns for file searches (e.g., `**/*.py`, `src/**/*.tsx`)
- Use ripgrep for content searches with regex support
- Consider file organization and naming conventions

### 2. Analysis Approach
- Read relevant files to understand implementation details
- Look for imports/dependencies to understand relationships
- Identify design patterns and architectural choices
- Consider context from directory structure

### 3. Answer Quality
- Provide specific file paths and line numbers when referencing code
- Include relevant code snippets in your explanations
- Explain both "what" and "why" when analyzing code
- Suggest related areas to explore if relevant

### 4. Efficiency
- Use the most appropriate tool for each task
- Avoid reading large binary files or generated code
- Focus on relevant file types: {', '.join(self.explore_config.file_extensions)}
- Skip common ignore patterns: {', '.join(self.explore_config.ignore_patterns)}

## Response Format
When answering questions:
1. **Summary**: Brief answer to the question
2. **Location**: Specific file paths and line numbers
3. **Details**: Relevant code snippets and explanations
4. **Context**: How this fits into the larger codebase
5. **Related**: Other relevant files or areas to explore

## Important Notes
- Always provide file paths in the format: `file_path:line_number`
- Be thorough but concise in your explanations
- If you can't find something, suggest alternative search strategies
- Consider multiple possible locations for ambiguous queries
"""

    def _get_exploration_instructions(self) -> str:
        """
        Get exploration-specific instructions for the system prompt.

        Returns:
            Custom instructions for code exploration
        """
        return f"""
## Exploration Configuration
- **File Extensions**: {', '.join(self.explore_config.file_extensions)}
- **Ignore Patterns**: {', '.join(self.explore_config.ignore_patterns)}
- **Max File Size**: {self.explore_config.max_file_size} bytes

## Search Guidelines
1. Use glob patterns for file searches
2. Use ripgrep for content searches
3. Focus on relevant file types
4. Provide specific file paths and line numbers
5. Include code snippets when helpful

## Response Format
- **Summary**: Brief answer
- **Location**: file_path:line_number
- **Details**: Code snippets and explanations
- **Context**: How it fits in the codebase
"""

    def prepare_context(
        self,
        codebase_path: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Prepare context for codebase exploration.

        Args:
            codebase_path: Path to the codebase root
            **kwargs: Additional context parameters

        Returns:
            Context string with codebase information
        """
        context_parts = []

        # Add codebase path if provided
        if codebase_path:
            context_parts.append(f"**Codebase Path**: `{codebase_path}`")

        # Add working directories from config
        if self.config.working_directories:
            dirs = "\n".join([f"  - `{d}`" for d in self.config.working_directories])
            context_parts.append(f"**Working Directories**:\n{dirs}")

        # Add current working directory
        if self.config.cwd:
            context_parts.append(f"**Current Directory**: `{self.config.cwd}`")

        # Add search paths if configured
        if self.explore_config.search_paths:
            paths = "\n".join([f"  - `{p}`" for p in self.explore_config.search_paths])
            context_parts.append(f"**Search Paths**:\n{paths}")

        if context_parts:
            return "\n\n".join(context_parts)

        return None

    async def explore(
        self,
        question: str,
        codebase_path: Optional[str] = None,
    ) -> str:
        """
        Explore the codebase to answer a specific question.

        Args:
            question: Question about the codebase
            codebase_path: Path to the codebase root

        Returns:
            Answer with code locations and explanations
        """
        return await self.invoke(
            prompt=question,
            codebase_path=codebase_path,
        )

    async def find_implementation(
        self,
        feature_or_function: str,
        codebase_path: Optional[str] = None,
    ) -> str:
        """
        Find the implementation of a specific feature or function.

        Args:
            feature_or_function: Name of the feature or function to find
            codebase_path: Path to the codebase root

        Returns:
            Location and details of the implementation
        """
        question = f"Find the implementation of '{feature_or_function}'. Provide the file path, line numbers, and a brief explanation of how it works."
        return await self.explore(question, codebase_path=codebase_path)

    async def analyze_structure(
        self,
        component_or_module: Optional[str] = None,
        codebase_path: Optional[str] = None,
    ) -> str:
        """
        Analyze the structure of a component or the entire codebase.

        Args:
            component_or_module: Specific component to analyze (or None for full codebase)
            codebase_path: Path to the codebase root

        Returns:
            Structural analysis with key files and organization
        """
        if component_or_module:
            question = f"Analyze the structure of the '{component_or_module}' component. Describe the key files, their purposes, and how they interact."
        else:
            question = "Analyze the overall codebase structure. Describe the main directories, their purposes, and the overall architecture."

        return await self.explore(question, codebase_path=codebase_path)

    async def find_usage(
        self,
        symbol: str,
        codebase_path: Optional[str] = None,
    ) -> str:
        """
        Find all usages of a specific symbol (function, class, variable).

        Args:
            symbol: Symbol to find usages of
            codebase_path: Path to the codebase root

        Returns:
            List of usage locations with context
        """
        question = f"Find all usages of '{symbol}' in the codebase. List the file paths, line numbers, and how it's being used in each location."
        return await self.explore(question, codebase_path=codebase_path)

    async def explain_flow(
        self,
        flow_description: str,
        codebase_path: Optional[str] = None,
    ) -> str:
        """
        Explain how a specific flow or process works in the codebase.

        Args:
            flow_description: Description of the flow to explain
            codebase_path: Path to the codebase root

        Returns:
            Step-by-step explanation of the flow with code references
        """
        question = f"Explain how {flow_description} works in this codebase. Trace through the relevant files and functions, providing the execution flow."
        return await self.explore(question, codebase_path=codebase_path)

    def __repr__(self) -> str:
        """String representation of the Explore Agent"""
        return (
            f"ExploreAgent("
            f"cli_type='{self.config.cli_type.value}', "
            f"model='{self._executor.config.get_default_model()}', "
            f"session_id='{self._get_session_id()}', "
            f"search_paths={len(self.explore_config.search_paths)})"
        )


# Convenience function for quick exploration
async def explore_codebase(
    question: str,
    codebase_path: Optional[str] = None,
    cli_type: CLIType = CLIType.CLAUDE,
    model: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """
    Convenience function to quickly explore a codebase.

    Args:
        question: Question about the codebase
        codebase_path: Path to the codebase root
        cli_type: CLI type to use (default: Claude)
        model: Model to use
        session_id: Session ID for tracking

    Returns:
        Answer to the question

    Example:
        >>> answer = await explore_codebase(
        ...     "Where is error handling implemented?",
        ...     codebase_path="/path/to/project"
        ... )
    """
    config = ExploreAgentConfig(
        cli_type=cli_type,
        model=model,
        session_id=session_id,
        cwd=codebase_path,
    )

    agent = ExploreAgent(config)
    return await agent.explore(question, codebase_path=codebase_path)
