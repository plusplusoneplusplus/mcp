"""
Unit tests for SpecializedAgent
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from utils.agent.agent import SpecializedAgent, AgentConfig
from utils.agent.cli_executor import CLIType, CLIExecutor


# Test agent implementations (not test classes, just agent implementations for testing)
class SimpleAgent(SpecializedAgent):
    """Simple agent for testing"""

    def get_system_prompt(self) -> str:
        return "You are a test agent."


class ContextAwareAgent(SpecializedAgent):
    """Agent with context preparation for testing"""

    def get_system_prompt(self) -> str:
        return "You are a context-aware agent."

    def prepare_context(self, **kwargs):
        data = kwargs.get("data")
        if data:
            return f"Data: {data}"
        return None


class TestAgentConfig:
    """Tests for AgentConfig"""

    def test_default_config(self):
        """Test default agent configuration"""
        config = AgentConfig()

        assert config.cli_type == CLIType.COPILOT
        assert config.model is None
        assert config.session_id is None
        assert config.skip_permissions is True
        assert config.cli_path is None
        assert config.timeout is None
        assert config.working_directories is None
        assert config.cwd is None

    def test_custom_config(self):
        """Test custom agent configuration"""
        config = AgentConfig(
            cli_type=CLIType.CODEX,
            model="gpt-4",
            session_id="test-session",
            skip_permissions=False,
            timeout=120
        )

        assert config.cli_type == CLIType.CODEX
        assert config.model == "gpt-4"
        assert config.session_id == "test-session"
        assert config.skip_permissions is False
        assert config.timeout == 120

    def test_to_cli_config(self):
        """Test conversion to CLIConfig"""
        config = AgentConfig(
            cli_type=CLIType.CLAUDE,
            model="haiku",
            skip_permissions=True,
            cli_path="/custom/claude",
            timeout=60,
            working_directories=["/work/dir1", "/work/dir2"],
            cwd="/work/dir1"
        )

        cli_config = config.to_cli_config()

        assert cli_config.cli_type == CLIType.CLAUDE
        assert cli_config.model == "haiku"
        assert cli_config.skip_permissions is True
        assert cli_config.cli_path == "/custom/claude"
        assert cli_config.timeout == 60
        assert cli_config.working_directories == ["/work/dir1", "/work/dir2"]
        assert cli_config.cwd == "/work/dir1"

    def test_working_directories_list(self):
        """Test configuration with multiple working directories"""
        config = AgentConfig(
            working_directories=["/dir1", "/dir2", "/dir3"]
        )

        assert config.working_directories == ["/dir1", "/dir2", "/dir3"]
        assert len(config.working_directories) == 3

    def test_cwd_without_working_directories(self):
        """Test configuration with cwd but no working_directories"""
        config = AgentConfig(cwd="/current/dir")

        assert config.cwd == "/current/dir"
        assert config.working_directories is None

    def test_working_directories_and_cwd_together(self):
        """Test configuration with both working_directories and cwd"""
        config = AgentConfig(
            working_directories=["/dir1", "/dir2"],
            cwd="/dir1"
        )

        assert config.working_directories == ["/dir1", "/dir2"]
        assert config.cwd == "/dir1"


class TestSpecializedAgent:
    """Tests for SpecializedAgent"""

    def test_init(self):
        """Test agent initialization"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = SimpleAgent(config)

        assert agent.config == config
        assert agent._executor is not None
        assert isinstance(agent._executor, CLIExecutor)
        assert agent._session_manager is not None
        # Verify session was created
        session_id = agent._get_session_id()
        assert agent._session_manager.storage.session_exists(session_id)

    def test_get_system_prompt(self):
        """Test getting system prompt"""
        config = AgentConfig()
        agent = SimpleAgent(config)

        prompt = agent.get_system_prompt()
        assert prompt == "You are a test agent."

    def test_prepare_context_default(self):
        """Test default context preparation (returns None)"""
        config = AgentConfig()
        agent = SimpleAgent(config)

        context = agent.prepare_context()
        assert context is None

    def test_prepare_context_custom(self):
        """Test custom context preparation"""
        config = AgentConfig()
        agent = ContextAwareAgent(config)

        context = agent.prepare_context(data="test-data")
        assert context == "Data: test-data"

        context = agent.prepare_context()
        assert context is None

    def test_get_session_id_default(self):
        """Test getting default session ID"""
        config = AgentConfig()
        agent = SimpleAgent(config)

        assert agent._get_session_id() == "default"

    def test_get_session_id_custom(self):
        """Test getting custom session ID"""
        config = AgentConfig(session_id="custom-session")
        agent = SimpleAgent(config)

        assert agent._get_session_id() == "custom-session"

    def test_session_history(self):
        """Test session history management"""
        config = AgentConfig()
        agent = SimpleAgent(config)

        # Initially empty
        history = agent._get_session_history()
        assert history == []

        # Add messages
        agent._add_to_history("user", "Hello")
        agent._add_to_history("assistant", "Hi there")

        history = agent._get_session_history()
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there"}

    def test_multiple_sessions(self):
        """Test managing multiple sessions"""
        config = AgentConfig(session_id="session1")
        agent = SimpleAgent(config)

        # Add to session1
        agent._add_to_history("user", "Message 1")

        # Switch to session2
        agent.set_session("session2")
        agent._add_to_history("user", "Message 2")

        # Verify separate histories
        session1_history = agent.get_session_history("session1")
        session2_history = agent.get_session_history("session2")

        assert len(session1_history) == 1
        assert session1_history[0]["content"] == "Message 1"

        assert len(session2_history) == 1
        assert session2_history[0]["content"] == "Message 2"

    def test_clear_session_history(self):
        """Test clearing session history"""
        config = AgentConfig()
        agent = SimpleAgent(config)

        agent._add_to_history("user", "Test message")
        assert len(agent._get_session_history()) == 1

        agent.clear_session_history()
        assert len(agent._get_session_history()) == 0

    def test_build_prompt_basic(self):
        """Test building basic prompt"""
        config = AgentConfig()
        agent = SimpleAgent(config)

        prompt = agent._build_prompt("What is Python?")

        assert "# System Instructions" in prompt
        assert "You are a test agent." in prompt
        assert "# Query" in prompt
        assert "What is Python?" in prompt

    def test_build_prompt_with_context(self):
        """Test building prompt with context"""
        config = AgentConfig()
        agent = ContextAwareAgent(config)

        prompt = agent._build_prompt("Analyze this", data="test-data")

        assert "# Context" in prompt
        assert "Data: test-data" in prompt
        assert "# Query" in prompt
        assert "Analyze this" in prompt

    def test_build_prompt_with_history(self):
        """Test building prompt with conversation history"""
        config = AgentConfig()
        agent = SimpleAgent(config)

        # Add some history
        agent._add_to_history("user", "Previous question")
        agent._add_to_history("assistant", "Previous answer")

        prompt = agent._build_prompt("New question", include_history=True)

        assert "# Conversation History" in prompt
        assert "Previous question" in prompt
        assert "Previous answer" in prompt
        assert "New question" in prompt

    def test_build_prompt_without_history(self):
        """Test building prompt without history"""
        config = AgentConfig()
        agent = SimpleAgent(config)

        # Add some history
        agent._add_to_history("user", "Previous question")

        prompt = agent._build_prompt("New question", include_history=False)

        assert "# Conversation History" not in prompt
        assert "Previous question" not in prompt
        assert "New question" in prompt

    @pytest.mark.asyncio
    async def test_invoke_success(self):
        """Test successful agent invocation"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = SimpleAgent(config)

        # Mock the executor
        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Python is a programming language."

            response = await agent.invoke("What is Python?")

            assert response == "Python is a programming language."
            assert mock_execute.called

            # Check history was updated
            history = agent._get_session_history()
            assert len(history) == 2
            assert history[0]["content"] == "What is Python?"
            assert history[1]["content"] == "Python is a programming language."

    @pytest.mark.asyncio
    async def test_invoke_error_no_history(self):
        """Test that errors are not added to history"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = SimpleAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Error: CLI failed"

            response = await agent.invoke("What is Python?")

            assert response == "Error: CLI failed"

            # Check history was NOT updated due to error
            history = agent._get_session_history()
            assert len(history) == 0

    @pytest.mark.asyncio
    async def test_invoke_without_history(self):
        """Test invocation without history tracking"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = SimpleAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Response"

            await agent.invoke("Question", include_history=False)

            # History should not be updated
            history = agent._get_session_history()
            assert len(history) == 0

    @pytest.mark.asyncio
    async def test_invoke_with_context(self):
        """Test invocation with context"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = ContextAwareAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Analysis complete"

            await agent.invoke("Analyze", data="test-data")

            # Check that context was included in the prompt
            called_prompt = mock_execute.call_args[0][0]
            assert "Data: test-data" in called_prompt

    @pytest.mark.asyncio
    async def test_batch_invoke(self):
        """Test batch invocation"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = SimpleAgent(config)

        prompts = ["Question 1", "Question 2", "Question 3"]
        expected_responses = ["Answer 1", "Answer 2", "Answer 3"]

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = expected_responses

            responses = await agent.batch_invoke(prompts)

            assert responses == expected_responses
            assert mock_execute.call_count == 3

            # Batch invoke should not add to history
            history = agent._get_session_history()
            assert len(history) == 0

    @pytest.mark.asyncio
    async def test_batch_invoke_with_context(self):
        """Test batch invocation with shared context"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = ContextAwareAgent(config)

        prompts = ["Q1", "Q2"]

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Answer"

            await agent.batch_invoke(prompts, data="shared-data")

            # Verify context was included in all prompts
            for call in mock_execute.call_args_list:
                called_prompt = call[0][0]
                assert "Data: shared-data" in called_prompt

    def test_set_session(self):
        """Test switching sessions"""
        config = AgentConfig(session_id="initial")
        agent = SimpleAgent(config)

        assert agent._get_session_id() == "initial"

        agent.set_session("new-session")
        assert agent._get_session_id() == "new-session"
        assert agent.config.session_id == "new-session"

    def test_repr(self):
        """Test agent string representation"""
        config = AgentConfig(
            cli_type=CLIType.CLAUDE,
            model="haiku",
            session_id="test-session"
        )
        agent = SimpleAgent(config)

        repr_str = repr(agent)

        assert "SimpleAgent" in repr_str
        assert "cli_type='claude'" in repr_str
        assert "model='haiku'" in repr_str
        assert "session_id='test-session'" in repr_str


class TestAgentIntegration:
    """Integration tests for agent with different CLI types"""

    @pytest.mark.asyncio
    async def test_agent_with_claude(self):
        """Test agent with Claude CLI"""
        config = AgentConfig(
            cli_type=CLIType.CLAUDE,
            model="haiku"
        )
        agent = SimpleAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Claude response"

            response = await agent.invoke("Test prompt")

            assert response == "Claude response"

    @pytest.mark.asyncio
    async def test_agent_with_codex(self):
        """Test agent with Codex CLI"""
        config = AgentConfig(
            cli_type=CLIType.CODEX
        )
        agent = SimpleAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Codex response"

            response = await agent.invoke("Test prompt")

            assert response == "Codex response"

    @pytest.mark.asyncio
    async def test_agent_with_copilot(self):
        """Test agent with Copilot CLI"""
        config = AgentConfig(
            cli_type=CLIType.COPILOT
        )
        agent = SimpleAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Copilot response"

            response = await agent.invoke("Test prompt")

            assert response == "Copilot response"

    @pytest.mark.asyncio
    async def test_agent_conversation_flow(self):
        """Test multi-turn conversation flow"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = SimpleAgent(config)

        responses = ["Hi!", "I can help with that.", "You're welcome!"]

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = responses

            # Turn 1
            r1 = await agent.invoke("Hello")
            assert r1 == "Hi!"

            # Turn 2 - should include previous turn in context
            r2 = await agent.invoke("Can you help?")
            assert r2 == "I can help with that."

            # Verify second prompt includes history
            second_prompt = mock_execute.call_args_list[1][0][0]
            assert "Hello" in second_prompt
            assert "Hi!" in second_prompt

            # Turn 3
            r3 = await agent.invoke("Thanks!")
            assert r3 == "You're welcome!"

            # Verify conversation history
            history = agent.get_session_history()
            assert len(history) == 6  # 3 user + 3 assistant messages
