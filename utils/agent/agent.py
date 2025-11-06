"""
SpecializedAgent Base Class

Provides a base class for creating specialized agents that invoke AI CLIs
to perform specific tasks with custom context and prompts.
"""

import logging
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .cli_executor import CLIExecutor, CLIConfig, CLIType

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for a specialized agent"""

    cli_type: CLIType = CLIType.COPILOT
    """CLI type to use: claude, codex, or copilot (default: copilot)"""

    model: Optional[str] = None
    """Model to use for the agent (depends on CLI type)"""

    session_id: Optional[str] = None
    """Optional session ID for tracking conversations"""

    skip_permissions: bool = True
    """Whether to skip permission prompts"""

    cli_path: Optional[str] = None
    """Path to the CLI executable (default: auto-detected from PATH)"""

    timeout: Optional[int] = None
    """Timeout for CLI invocations in seconds"""

    working_directory: Optional[str] = None
    """Working directory for CLI execution"""

    def to_cli_config(self) -> CLIConfig:
        """Convert to CLIConfig for executor"""
        return CLIConfig(
            cli_type=self.cli_type,
            model=self.model,
            skip_permissions=self.skip_permissions,
            cli_path=self.cli_path,
            timeout=self.timeout,
            working_directory=self.working_directory,
        )


class SpecializedAgent(ABC):
    """
    Base class for specialized agents that use AI CLIs to perform tasks.

    This class provides the infrastructure for creating agents that:
    - Invoke Claude, Codex, or Copilot CLI with custom context and prompts
    - Maintain conversation history per session
    - Support batch processing

    Subclasses should implement:
    - get_system_prompt(): Define the agent's behavior and expertise
    - prepare_context(): Prepare context specific to the task
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the specialized agent.

        Args:
            config: Agent configuration
        """
        self.config = config
        self._executor = CLIExecutor(config.to_cli_config())
        self._sessions: Dict[str, List[Dict[str, str]]] = {}

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt that defines the agent's behavior.

        This should return a prompt that sets up the agent's role, expertise,
        and any specific instructions for how it should respond.

        Returns:
            System prompt string
        """
        pass

    def prepare_context(self, **kwargs) -> Optional[str]:
        """
        Prepare additional context for the agent.

        Override this method to provide task-specific context that should
        be included before the user's prompt.

        Args:
            **kwargs: Context parameters

        Returns:
            Context string or None if no additional context is needed
        """
        return None

    def _get_session_id(self) -> str:
        """Get the current session ID"""
        return self.config.session_id or "default"

    def _get_session_history(self) -> List[Dict[str, str]]:
        """Get the message history for the current session"""
        session_id = self._get_session_id()
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        return self._sessions[session_id]

    def _add_to_history(self, role: str, content: str):
        """Add a message to the session history"""
        history = self._get_session_history()
        history.append({"role": role, "content": content})

    def _build_prompt(
        self,
        prompt: str,
        context: Optional[str] = None,
        include_history: bool = True,
        **context_kwargs
    ) -> str:
        """
        Build the complete prompt to send to the CLI.

        Args:
            prompt: User prompt/question
            context: Optional context string
            include_history: Whether to include conversation history
            **context_kwargs: Additional context arguments

        Returns:
            Complete prompt string
        """
        message_parts = []

        # Add system prompt if this is the first message in the session
        session_history = self._get_session_history()
        if not session_history or not include_history:
            system_prompt = self.get_system_prompt()
            if system_prompt:
                message_parts.append(f"# System Instructions\n{system_prompt}")

        # Add conversation history if requested
        if include_history and session_history:
            history_text = "\n\n".join([
                f"**{msg['role'].capitalize()}**: {msg['content']}"
                for msg in session_history
            ])
            message_parts.append(f"# Conversation History\n{history_text}")

        # Add context
        if context is None:
            context = self.prepare_context(**context_kwargs)

        if context:
            message_parts.append(f"# Context\n{context}")

        # Add user prompt
        message_parts.append(f"# Query\n{prompt}")

        return "\n\n---\n\n".join(message_parts)

    async def invoke(
        self,
        prompt: str,
        context: Optional[str] = None,
        include_history: bool = True,
        **context_kwargs
    ) -> str:
        """
        Invoke the agent with a prompt and optional context.

        Args:
            prompt: User prompt/question for the agent
            context: Optional context string (if None, will call prepare_context)
            include_history: Whether to include conversation history
            **context_kwargs: Additional arguments passed to prepare_context

        Returns:
            Agent's response as a string
        """
        # Build the complete prompt
        full_prompt = self._build_prompt(
            prompt=prompt,
            context=context,
            include_history=include_history,
            **context_kwargs
        )

        # Execute via CLI executor
        response = await self._executor.execute(full_prompt)

        # Add to session history (only if not an error and history is enabled)
        if include_history and not response.startswith("Error:"):
            self._add_to_history("user", prompt)
            self._add_to_history("assistant", response)

        return response

    async def batch_invoke(
        self,
        prompts: List[str],
        context: Optional[str] = None,
        **context_kwargs
    ) -> List[str]:
        """
        Invoke the agent with multiple prompts.

        Args:
            prompts: List of prompts to process
            context: Optional context string (if None, will call prepare_context)
            **context_kwargs: Additional arguments passed to prepare_context

        Returns:
            List of responses corresponding to each prompt
        """
        responses = []
        for prompt in prompts:
            response = await self.invoke(
                prompt=prompt,
                context=context,
                include_history=False,
                **context_kwargs
            )
            responses.append(response)

        return responses

    def clear_session_history(self, session_id: Optional[str] = None):
        """
        Clear the conversation history for a session.

        Args:
            session_id: Session to clear (if None, clears current session)
        """
        sid = session_id or self._get_session_id()
        if sid in self._sessions:
            self._sessions[sid] = []
            logger.info(f"Cleared history for session {sid}")

    def get_session_history(self, session_id: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get the conversation history for a session.

        Args:
            session_id: Session to retrieve (if None, gets current session)

        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        sid = session_id or self._get_session_id()
        return self._sessions.get(sid, []).copy()

    def set_session(self, session_id: str):
        """
        Switch to a different session.

        Args:
            session_id: ID of the session to switch to
        """
        self.config.session_id = session_id
        logger.info(f"Switched to session {session_id}")

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"cli_type='{self.config.cli_type.value}', "
            f"model='{self._executor.config.get_default_model()}', "
            f"session_id='{self._get_session_id()}')"
        )
