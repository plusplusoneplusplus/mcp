"""
Integration tests for SpecializedAgent with system prompt functionality.
"""

import pytest
from pathlib import Path

from utils.agent import SpecializedAgent, AgentConfig
from utils.agent.cli_executor import CLIType


class DefaultSystemPromptAgent(SpecializedAgent):
    """Test agent using default system prompt"""

    def get_system_prompt(self) -> str:
        return self.get_default_system_prompt(
            agent_role="Test agent for automated testing",
            custom_instructions="Follow test guidelines",
        )


class MinimalSystemPromptAgent(SpecializedAgent):
    """Test agent using minimal system prompt"""

    def get_system_prompt(self) -> str:
        from utils.agent.system_prompt import SystemPromptBuilder

        return SystemPromptBuilder.build_minimal_prompt(
            session_id=self._get_session_id(),
            session_storage_path=self._get_session_storage_path(),
        )


class CustomSystemPromptAgent(SpecializedAgent):
    """Test agent using custom system prompt with session info"""

    def get_system_prompt(self) -> str:
        session_id = self._get_session_id()
        storage_path = self._get_session_storage_path()

        return f"""Custom Agent

Session: {session_id}
Storage: {storage_path}

Custom instructions here.
"""


class TestAgentSystemPromptIntegration:
    """Integration tests for agent system prompts"""

    def test_agent_with_default_system_prompt(self):
        """Test agent using default system prompt"""
        config = AgentConfig(
            cli_type=CLIType.COPILOT,
            session_id="test_session_001",
            session_storage_path=Path("/tmp/.sessions"),
        )

        agent = DefaultSystemPromptAgent(config)
        prompt = agent.get_system_prompt()

        # Verify session information is included
        assert "test_session_001" in prompt
        assert "/tmp/.sessions/test_session_001" in prompt

        # Verify role and instructions are included
        assert "Test agent for automated testing" in prompt
        assert "Follow test guidelines" in prompt

        # Verify structure
        assert "# System Configuration" in prompt
        assert "## Session Context" in prompt

    def test_agent_with_minimal_system_prompt(self):
        """Test agent using minimal system prompt"""
        config = AgentConfig(
            cli_type=CLIType.CLAUDE,
            session_id="minimal_session",
            session_storage_path=Path("/tmp/.sessions"),
        )

        agent = MinimalSystemPromptAgent(config)
        prompt = agent.get_system_prompt()

        # Verify session information is included
        assert "minimal_session" in prompt
        assert "/tmp/.sessions/minimal_session" in prompt

        # Should be minimal (no headers)
        assert "# System Configuration" not in prompt

    def test_agent_with_custom_system_prompt(self):
        """Test agent using custom system prompt"""
        config = AgentConfig(
            cli_type=CLIType.COPILOT,
            session_id="custom_session",
            session_storage_path=Path("/tmp/.sessions"),
        )

        agent = CustomSystemPromptAgent(config)
        prompt = agent.get_system_prompt()

        # Verify custom format
        assert "Custom Agent" in prompt
        assert "custom_session" in prompt
        assert "/tmp/.sessions/custom_session" in prompt
        assert "Custom instructions here" in prompt

    def test_agent_session_storage_path_default(self):
        """Test agent with default session storage path"""
        config = AgentConfig(
            cli_type=CLIType.COPILOT,
            session_id="default_path_test",
            cwd="/home/user/project",
        )

        agent = DefaultSystemPromptAgent(config)

        # Get storage path
        storage_path = agent._get_session_storage_path()

        # Should default to cwd/.sessions/session_id
        assert storage_path == Path("/home/user/project/.sessions/default_path_test")

    def test_agent_session_storage_path_custom(self):
        """Test agent with custom session storage path"""
        custom_path = Path("/custom/sessions")
        config = AgentConfig(
            cli_type=CLIType.COPILOT,
            session_id="custom_path_test",
            session_storage_path=custom_path,
        )

        agent = DefaultSystemPromptAgent(config)

        # Get storage path
        storage_path = agent._get_session_storage_path()

        # Should use custom path + session_id
        assert storage_path == custom_path / "custom_path_test"

    def test_agent_default_session_id(self):
        """Test agent with default session ID"""
        config = AgentConfig(
            cli_type=CLIType.COPILOT,
            # No session_id specified
        )

        agent = DefaultSystemPromptAgent(config)

        # Get session ID
        session_id = agent._get_session_id()

        # Should default to "default"
        assert session_id == "default"

        # Prompt should include default
        prompt = agent.get_system_prompt()
        assert "default" in prompt

    def test_agent_set_session_updates_prompt(self):
        """Test that changing session updates the prompt"""
        config = AgentConfig(
            cli_type=CLIType.COPILOT,
            session_id="initial_session",
            session_storage_path=Path("/tmp/.sessions"),
        )

        agent = DefaultSystemPromptAgent(config)

        # Get initial prompt
        prompt1 = agent.get_system_prompt()
        assert "initial_session" in prompt1

        # Change session
        agent.set_session("new_session")

        # Get new prompt
        prompt2 = agent.get_system_prompt()
        assert "new_session" in prompt2
        assert "initial_session" not in prompt2

    def test_agent_multiple_sessions(self):
        """Test agent with multiple sessions"""
        config = AgentConfig(
            cli_type=CLIType.COPILOT,
            session_id="session_A",
            session_storage_path=Path("/tmp/.sessions"),
        )

        agent = DefaultSystemPromptAgent(config)

        # Session A
        prompt_a = agent.get_system_prompt()
        assert "session_A" in prompt_a
        storage_a = agent._get_session_storage_path()
        assert storage_a == Path("/tmp/.sessions/session_A")

        # Switch to Session B
        agent.set_session("session_B")
        prompt_b = agent.get_system_prompt()
        assert "session_B" in prompt_b
        storage_b = agent._get_session_storage_path()
        assert storage_b == Path("/tmp/.sessions/session_B")

        # Verify sessions are different
        assert prompt_a != prompt_b
        assert storage_a != storage_b

    def test_prompt_in_build_prompt(self):
        """Test that system prompt is included in _build_prompt"""
        config = AgentConfig(
            cli_type=CLIType.COPILOT,
            session_id="build_test",
            session_storage_path=Path("/tmp/.sessions"),
        )

        agent = DefaultSystemPromptAgent(config)

        # Build a prompt
        full_prompt = agent._build_prompt(
            prompt="Test query",
            include_history=False,
        )

        # System prompt should be included
        assert "# System Instructions" in full_prompt
        assert "build_test" in full_prompt
        assert "/tmp/.sessions/build_test" in full_prompt
        assert "Test agent for automated testing" in full_prompt

    def test_prompt_not_repeated_in_history(self):
        """Test that system prompt is only included at start of session"""
        config = AgentConfig(
            cli_type=CLIType.COPILOT,
            session_id="history_test",
        )

        agent = DefaultSystemPromptAgent(config)

        # First prompt (no history) - should include system prompt
        first_prompt = agent._build_prompt(
            prompt="First message",
            include_history=True,
        )
        assert "# System Instructions" in first_prompt
        assert first_prompt.count("# System Instructions") == 1

        # Add some history
        agent._add_to_history("user", "First message")
        agent._add_to_history("assistant", "First response")

        # Second prompt (with history) - system prompt should NOT be repeated
        second_prompt = agent._build_prompt(
            prompt="Second message",
            include_history=True,
        )

        # System prompt should NOT appear when there's history
        # (it was already shown at the beginning)
        assert "# System Instructions" not in second_prompt

        # But without history, system prompt should appear
        third_prompt = agent._build_prompt(
            prompt="Third message",
            include_history=False,
        )
        assert "# System Instructions" in third_prompt

    def test_repr_includes_session(self):
        """Test that agent __repr__ includes session ID"""
        config = AgentConfig(
            cli_type=CLIType.COPILOT,
            session_id="repr_test",
        )

        agent = DefaultSystemPromptAgent(config)

        # Get string representation
        repr_str = repr(agent)

        # Should include session ID
        assert "repr_test" in repr_str


class TestAgentConfigSessionFields:
    """Tests for AgentConfig session-related fields"""

    def test_config_session_id(self):
        """Test AgentConfig with session_id"""
        config = AgentConfig(
            session_id="test_config_session",
        )

        assert config.session_id == "test_config_session"

    def test_config_session_storage_path(self):
        """Test AgentConfig with session_storage_path"""
        storage_path = Path("/custom/storage")
        config = AgentConfig(
            session_storage_path=storage_path,
        )

        assert config.session_storage_path == storage_path

    def test_config_include_session_in_prompt(self):
        """Test AgentConfig with include_session_in_prompt flag"""
        config = AgentConfig(
            include_session_in_prompt=True,
        )

        assert config.include_session_in_prompt is True

    def test_config_defaults(self):
        """Test AgentConfig default values"""
        config = AgentConfig()

        assert config.session_id is None
        assert config.session_storage_path is None
        assert config.include_session_in_prompt is False

    def test_config_to_cli_config(self):
        """Test that session fields don't break to_cli_config"""
        config = AgentConfig(
            session_id="test_session",
            session_storage_path=Path("/test"),
            include_session_in_prompt=True,
        )

        # Should not raise
        cli_config = config.to_cli_config()

        # CLI config shouldn't have session fields (they're agent-specific)
        assert not hasattr(cli_config, "session_id")
        assert not hasattr(cli_config, "session_storage_path")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
