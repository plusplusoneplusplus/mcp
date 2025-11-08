"""
System prompt utilities for specialized agents.

Provides utilities for generating default system prompts with session context,
including session ID and storage path information.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime


class SystemPromptBuilder:
    """
    Builder for creating comprehensive system prompts with session context.

    Generates system prompts that include:
    - Session ID for tracking conversations
    - Session storage absolute path for data persistence
    - Timestamp information
    - Optional custom instructions
    """

    @staticmethod
    def build_default_prompt(
        session_id: str,
        session_storage_path: Path,
        agent_role: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        include_timestamp: bool = True,
    ) -> str:
        """
        Build a default system prompt with session information.

        Args:
            session_id: Unique session identifier
            session_storage_path: Absolute path to session storage directory
            agent_role: Optional role/purpose description of the agent
            custom_instructions: Optional custom instructions for the agent
            include_timestamp: Whether to include current timestamp

        Returns:
            Complete system prompt string with session context
        """
        prompt_parts = []

        # Header
        prompt_parts.append("# System Configuration")
        prompt_parts.append("")

        # Session Information
        prompt_parts.append("## Session Context")
        prompt_parts.append(f"- **Session ID**: `{session_id}`")
        prompt_parts.append(
            f"- **Session Storage Path**: `{session_storage_path.absolute()}`"
        )

        if include_timestamp:
            prompt_parts.append(
                f"- **Session Started**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        prompt_parts.append("")

        # Session storage information
        prompt_parts.append("### Session Storage Information")
        prompt_parts.append(
            "All session data, including conversation history, metadata, and "
            "linked tool invocations are stored in the session storage path. "
            "You can reference this location for data persistence and retrieval."
        )
        prompt_parts.append("")

        # Agent Role (if provided)
        if agent_role:
            prompt_parts.append("## Agent Role")
            prompt_parts.append(agent_role)
            prompt_parts.append("")

        # Custom Instructions (if provided)
        if custom_instructions:
            prompt_parts.append("## Instructions")
            prompt_parts.append(custom_instructions)
            prompt_parts.append("")

        # Guidelines
        prompt_parts.append("## Guidelines")
        prompt_parts.append(
            "1. **Session Continuity**: Maintain context across invocations using the session ID"
        )
        prompt_parts.append(
            "2. **Data Persistence**: Store and retrieve session-specific data in the session storage path"
        )
        prompt_parts.append(
            "3. **Conversation History**: Reference previous messages in the session for context"
        )
        prompt_parts.append(
            "4. **Tool Integration**: Link tool invocations to the session for comprehensive tracking"
        )
        prompt_parts.append("")

        return "\n".join(prompt_parts)

    @staticmethod
    def build_minimal_prompt(session_id: str, session_storage_path: Path) -> str:
        """
        Build a minimal system prompt with just session essentials.

        Args:
            session_id: Unique session identifier
            session_storage_path: Absolute path to session storage directory

        Returns:
            Minimal system prompt string
        """
        return (
            f"Session ID: {session_id}\n"
            f"Session Storage: {session_storage_path.absolute()}\n"
            f"\n"
            f"Maintain conversation context and store session data in the specified storage path."
        )

    @staticmethod
    def build_json_context(session_id: str, session_storage_path: Path) -> dict:
        """
        Build session context as JSON for structured prompts.

        Args:
            session_id: Unique session identifier
            session_storage_path: Absolute path to session storage directory

        Returns:
            Dictionary with session context
        """
        return {
            "session": {
                "id": session_id,
                "storage_path": str(session_storage_path.absolute()),
                "timestamp": datetime.now().isoformat(),
            }
        }


def create_default_system_prompt(
    session_id: str,
    session_storage_path: Path,
    agent_role: Optional[str] = None,
    custom_instructions: Optional[str] = None,
) -> str:
    """
    Convenience function to create a default system prompt.

    Args:
        session_id: Unique session identifier
        session_storage_path: Absolute path to session storage directory
        agent_role: Optional role/purpose description of the agent
        custom_instructions: Optional custom instructions for the agent

    Returns:
        Complete system prompt string with session context

    Example:
        >>> from pathlib import Path
        >>> prompt = create_default_system_prompt(
        ...     session_id="session_20241107_123456_abc123",
        ...     session_storage_path=Path("/path/to/project/.sessions/session_20241107_123456_abc123"),
        ...     agent_role="You are a code review assistant specialized in Python.",
        ...     custom_instructions="Focus on security and performance issues."
        ... )
    """
    return SystemPromptBuilder.build_default_prompt(
        session_id=session_id,
        session_storage_path=session_storage_path,
        agent_role=agent_role,
        custom_instructions=custom_instructions,
    )
