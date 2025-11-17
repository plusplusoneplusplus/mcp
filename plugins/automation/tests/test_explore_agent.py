"""
Tests for ExploreAgent
"""

import pytest
import tempfile
from unittest.mock import AsyncMock, patch
from pathlib import Path

from plugins.automation import ExploreAgent, ExploreAgentConfig, explore_codebase
from utils.agent import CLIType


class TestExploreAgentConfig:
    """Tests for ExploreAgentConfig"""

    def test_default_config(self):
        """Test default explore agent configuration"""
        config = ExploreAgentConfig()

        assert config.cli_type == CLIType.COPILOT
        assert config.search_paths == []
        assert ".py" in config.file_extensions
        assert ".js" in config.file_extensions
        assert config.max_file_size == 100000
        assert "node_modules" in config.ignore_patterns
        assert "__pycache__" in config.ignore_patterns

    def test_custom_config(self):
        """Test custom explore agent configuration"""
        config = ExploreAgentConfig(
            cli_type=CLIType.CLAUDE,
            model="haiku",
            session_id="explore-session",
            search_paths=["/path1", "/path2"],
            file_extensions=[".py", ".rs"],
            max_file_size=50000,
            ignore_patterns=["build", "dist"],
        )

        assert config.cli_type == CLIType.CLAUDE
        assert config.model == "haiku"
        assert config.session_id == "explore-session"
        assert config.search_paths == ["/path1", "/path2"]
        assert config.file_extensions == [".py", ".rs"]
        assert config.max_file_size == 50000
        assert config.ignore_patterns == ["build", "dist"]

    def test_working_directories_config(self):
        """Test configuration with working directories"""
        config = ExploreAgentConfig(
            working_directories=["/work/dir1", "/work/dir2"],
            cwd="/work/dir1"
        )

        assert config.working_directories == ["/work/dir1", "/work/dir2"]
        assert config.cwd == "/work/dir1"


class TestExploreAgent:
    """Tests for ExploreAgent"""

    def test_init(self):
        """Test explore agent initialization"""
        config = ExploreAgentConfig(cli_type=CLIType.CLAUDE)
        agent = ExploreAgent(config)

        assert agent.config == config
        assert agent.explore_config == config
        assert agent._executor is not None

    def test_init_from_base_config(self):
        """Test initialization from base AgentConfig"""
        from utils.agent import AgentConfig

        base_config = AgentConfig(
            cli_type=CLIType.CLAUDE,
            model="haiku",
            session_id="test"
        )

        agent = ExploreAgent(base_config)

        assert isinstance(agent.explore_config, ExploreAgentConfig)
        assert agent.config.cli_type == CLIType.CLAUDE
        assert agent.config.model == "haiku"

    def test_get_system_prompt(self):
        """Test getting system prompt"""
        config = ExploreAgentConfig()
        agent = ExploreAgent(config)

        prompt = agent.get_system_prompt()

        assert "Codebase Exploration Agent" in prompt
        assert "Role" in prompt
        assert "Capabilities" in prompt
        assert "Search Strategy" in prompt
        assert ".py" in prompt  # File extensions should be mentioned

    def test_get_system_prompt_with_session(self):
        """Test getting system prompt with session context"""
        config = ExploreAgentConfig(
            include_session_in_prompt=True,
            session_id="test-session"
        )
        agent = ExploreAgent(config)

        prompt = agent.get_system_prompt()

        assert "Session" in prompt
        assert "test-session" in prompt

    def test_prepare_context_empty(self):
        """Test context preparation with no parameters"""
        config = ExploreAgentConfig()
        agent = ExploreAgent(config)

        context = agent.prepare_context()
        assert context is None

    def test_prepare_context_with_codebase_path(self):
        """Test context preparation with codebase path"""
        config = ExploreAgentConfig()
        agent = ExploreAgent(config)

        context = agent.prepare_context(codebase_path="/path/to/code")

        assert context is not None
        assert "/path/to/code" in context
        assert "Codebase Path" in context

    def test_prepare_context_with_working_directories(self):
        """Test context preparation with working directories"""
        config = ExploreAgentConfig(
            working_directories=["/dir1", "/dir2"]
        )
        agent = ExploreAgent(config)

        context = agent.prepare_context()

        assert context is not None
        assert "/dir1" in context
        assert "/dir2" in context
        assert "Working Directories" in context

    def test_prepare_context_with_search_paths(self):
        """Test context preparation with search paths"""
        config = ExploreAgentConfig(
            search_paths=["/src/auth", "/src/db"]
        )
        agent = ExploreAgent(config)

        context = agent.prepare_context()

        assert context is not None
        assert "/src/auth" in context
        assert "/src/db" in context
        assert "Search Paths" in context

    def test_prepare_context_comprehensive(self):
        """Test context preparation with all parameters"""
        config = ExploreAgentConfig(
            working_directories=["/work"],
            cwd="/work/current",
            search_paths=["/work/src"]
        )
        agent = ExploreAgent(config)

        context = agent.prepare_context(
            codebase_path="/work"
        )

        assert context is not None
        assert "/work" in context
        assert "/work/current" in context
        assert "/work/src" in context

    @pytest.mark.asyncio
    async def test_explore(self):
        """Test explore method"""
        config = ExploreAgentConfig(cli_type=CLIType.CLAUDE)
        agent = ExploreAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Found implementation in src/auth.py:42"

            response = await agent.explore(
                "Where is authentication implemented?",
                codebase_path="/project"
            )

            assert response == "Found implementation in src/auth.py:42"
            assert mock_execute.called

            # Verify the question was in the prompt
            called_prompt = mock_execute.call_args[0][0]
            assert "Where is authentication implemented?" in called_prompt

    @pytest.mark.asyncio
    async def test_find_implementation(self):
        """Test find_implementation method"""
        config = ExploreAgentConfig(cli_type=CLIType.CLAUDE)
        agent = ExploreAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Implementation found"

            response = await agent.find_implementation(
                "login",
                codebase_path="/project"
            )

            assert response == "Implementation found"

            # Verify the prompt includes the feature name
            called_prompt = mock_execute.call_args[0][0]
            assert "login" in called_prompt
            assert "implementation" in called_prompt.lower()

    @pytest.mark.asyncio
    async def test_analyze_structure(self):
        """Test analyze_structure method"""
        config = ExploreAgentConfig(cli_type=CLIType.CLAUDE)
        agent = ExploreAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Structure analysis"

            response = await agent.analyze_structure(
                component_or_module="auth module",
                codebase_path="/project"
            )

            assert response == "Structure analysis"

            # Verify component is in prompt
            called_prompt = mock_execute.call_args[0][0]
            assert "auth module" in called_prompt
            assert "structure" in called_prompt.lower()

    @pytest.mark.asyncio
    async def test_analyze_structure_full_codebase(self):
        """Test analyze_structure for entire codebase"""
        config = ExploreAgentConfig(cli_type=CLIType.CLAUDE)
        agent = ExploreAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Full analysis"

            response = await agent.analyze_structure(codebase_path="/project")

            assert response == "Full analysis"

            # Should ask about overall structure
            called_prompt = mock_execute.call_args[0][0]
            assert "overall" in called_prompt.lower() or "codebase structure" in called_prompt.lower()

    @pytest.mark.asyncio
    async def test_find_usage(self):
        """Test find_usage method"""
        config = ExploreAgentConfig(cli_type=CLIType.CLAUDE)
        agent = ExploreAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Usages found"

            response = await agent.find_usage(
                "UserModel",
                codebase_path="/project"
            )

            assert response == "Usages found"

            # Verify symbol is in prompt
            called_prompt = mock_execute.call_args[0][0]
            assert "UserModel" in called_prompt
            assert "usage" in called_prompt.lower()

    @pytest.mark.asyncio
    async def test_explain_flow(self):
        """Test explain_flow method"""
        config = ExploreAgentConfig(cli_type=CLIType.CLAUDE)
        agent = ExploreAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Flow explanation"

            response = await agent.explain_flow(
                "user authentication",
                codebase_path="/project"
            )

            assert response == "Flow explanation"

            # Verify flow description is in prompt
            called_prompt = mock_execute.call_args[0][0]
            assert "user authentication" in called_prompt
            assert "flow" in called_prompt.lower()

    @pytest.mark.asyncio
    async def test_session_history(self):
        """Test that explore maintains session history"""
        config = ExploreAgentConfig(cli_type=CLIType.CLAUDE)
        agent = ExploreAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = ["First answer", "Second answer"]

            # First question
            await agent.explore("First question")

            # Second question
            await agent.explore("Second question")

            # Verify history was maintained
            history = agent.get_session_history()
            assert len(history) == 4  # 2 user + 2 assistant
            assert history[0]["content"] == "First question"
            assert history[1]["content"] == "First answer"
            assert history[2]["content"] == "Second question"
            assert history[3]["content"] == "Second answer"

    def test_repr(self):
        """Test agent string representation"""
        config = ExploreAgentConfig(
            cli_type=CLIType.CLAUDE,
            model="haiku",
            session_id="explore-123",
            search_paths=["/path1", "/path2"]
        )
        agent = ExploreAgent(config)

        repr_str = repr(agent)

        assert "ExploreAgent" in repr_str
        assert "cli_type='claude'" in repr_str
        assert "model='haiku'" in repr_str
        assert "session_id='explore-123'" in repr_str
        assert "search_paths=2" in repr_str


class TestExploreCodebaseFunction:
    """Tests for explore_codebase convenience function"""

    @pytest.mark.asyncio
    async def test_explore_codebase_basic(self):
        """Test basic explore_codebase usage"""
        with patch('plugins.automation.agents.explore_agent.ExploreAgent') as MockAgent:
            mock_agent = MockAgent.return_value
            mock_agent.explore = AsyncMock(return_value="Answer")

            result = await explore_codebase(
                "Where is the main entry point?",
                codebase_path="/project"
            )

            assert result == "Answer"
            assert MockAgent.called
            assert mock_agent.explore.called

    @pytest.mark.asyncio
    async def test_explore_codebase_with_options(self):
        """Test explore_codebase with custom options"""
        with patch('plugins.automation.agents.explore_agent.ExploreAgent') as MockAgent:
            mock_agent = MockAgent.return_value
            mock_agent.explore = AsyncMock(return_value="Answer")

            result = await explore_codebase(
                "Question",
                codebase_path="/project",
                cli_type=CLIType.CODEX,
                model="gpt-4",
                session_id="custom-session"
            )

            assert result == "Answer"

            # Verify config was created with correct parameters
            call_args = MockAgent.call_args[0][0]
            assert call_args.cli_type == CLIType.CODEX
            assert call_args.model == "gpt-4"
            assert call_args.session_id == "custom-session"


class TestExploreAgentIntegration:
    """Integration tests for ExploreAgent"""

    @pytest.mark.asyncio
    async def test_multi_turn_exploration(self):
        """Test multi-turn exploration conversation"""
        config = ExploreAgentConfig(cli_type=CLIType.CLAUDE)
        agent = ExploreAgent(config)

        responses = [
            "Found in src/auth.py",
            "It uses JWT tokens",
            "Stored in Redis"
        ]

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = responses

            # Turn 1
            r1 = await agent.explore("Where is authentication?")
            assert r1 == responses[0]

            # Turn 2 - should have context from turn 1
            r2 = await agent.explore("How does it work?")
            assert r2 == responses[1]

            # Verify second prompt includes history
            second_prompt = mock_execute.call_args_list[1][0][0]
            assert "Where is authentication?" in second_prompt
            assert "Found in src/auth.py" in second_prompt

            # Turn 3
            r3 = await agent.explore("Where are tokens stored?")
            assert r3 == responses[2]

            # Verify conversation history
            history = agent.get_session_history()
            assert len(history) == 6  # 3 user + 3 assistant

    @pytest.mark.asyncio
    async def test_different_exploration_methods(self):
        """Test using different exploration methods in sequence"""
        config = ExploreAgentConfig(cli_type=CLIType.CLAUDE)
        agent = ExploreAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = "Result"

            # Use different methods
            await agent.find_implementation("feature")
            await agent.analyze_structure("module")
            await agent.find_usage("symbol")
            await agent.explain_flow("process")

            # All should have been executed
            assert mock_execute.call_count == 4


class TestExploreAgentSessionManagement:
    """Tests for session management in ExploreAgent"""

    def test_session_id_propagation(self):
        """Test that session_id is properly propagated"""
        config = ExploreAgentConfig(
            cli_type=CLIType.CLAUDE,
            session_id="explore-session-123"
        )
        agent = ExploreAgent(config)

        assert agent.config.session_id == "explore-session-123"
        assert agent._get_session_id() == "explore-session-123"

    def test_session_storage_path_propagation(self):
        """Test that session_storage_path is properly propagated"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "explore" / "sessions"
            config = ExploreAgentConfig(
                cli_type=CLIType.CLAUDE,
                session_storage_path=storage_path
            )
            agent = ExploreAgent(config)

            assert agent.config.session_storage_path == storage_path

    def test_include_session_in_prompt_false(self):
        """Test system prompt without session context"""
        config = ExploreAgentConfig(
            cli_type=CLIType.CLAUDE,
            include_session_in_prompt=False
        )
        agent = ExploreAgent(config)

        prompt = agent.get_system_prompt()

        # Should use basic system prompt without session context
        assert "Codebase Exploration Agent" in prompt
        # Should not include session-specific content
        assert "Session ID:" not in prompt

    def test_include_session_in_prompt_true(self):
        """Test system prompt with session context"""
        config = ExploreAgentConfig(
            cli_type=CLIType.CLAUDE,
            include_session_in_prompt=True,
            session_id="explore-with-context"
        )
        agent = ExploreAgent(config)

        prompt = agent.get_system_prompt()

        # Should include session context
        assert "Session" in prompt
        assert "explore-with-context" in prompt

    def test_unified_session_config(self):
        """Test that all session config parameters work together"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "unified" / "explore"
            config = ExploreAgentConfig(
                cli_type=CLIType.CLAUDE,
                session_id="unified-explore-session",
                session_storage_path=storage_path,
                include_session_in_prompt=True
            )
            agent = ExploreAgent(config)

            # All session parameters should be set
            assert agent.config.session_id == "unified-explore-session"
            assert agent.config.session_storage_path == storage_path
            assert agent.config.include_session_in_prompt is True

            # System prompt should reflect session config
            prompt = agent.get_system_prompt()
            assert "Session" in prompt
            assert "unified-explore-session" in prompt

    @pytest.mark.asyncio
    async def test_session_persistence_across_calls(self):
        """Test that session data persists across multiple calls"""
        config = ExploreAgentConfig(
            cli_type=CLIType.CLAUDE,
            session_id="persistent-session"
        )
        agent = ExploreAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = ["First answer", "Second answer", "Third answer"]

            # Make multiple calls
            await agent.explore("First question")
            await agent.explore("Second question")
            await agent.find_implementation("feature")

            # Session history should contain all interactions
            history = agent.get_session_history()
            assert len(history) == 6  # 3 user + 3 assistant

            # Verify session ID remains consistent
            assert agent._get_session_id() == "persistent-session"

    @pytest.mark.asyncio
    async def test_session_history_included_in_prompts(self):
        """Test that session history is included in subsequent prompts"""
        config = ExploreAgentConfig(
            cli_type=CLIType.CLAUDE,
            session_id="history-session"
        )
        agent = ExploreAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = ["Found in auth.py", "Uses JWT tokens"]

            # First call
            await agent.explore("Where is authentication?")

            # Second call
            await agent.explore("How does it work?")

            # The second call should include history from the first
            second_call_prompt = mock_execute.call_args_list[1][0][0]
            assert "Where is authentication?" in second_call_prompt
            assert "Found in auth.py" in second_call_prompt

    def test_session_config_from_base_agent_config(self):
        """Test that session config is preserved when converting from base AgentConfig"""
        from utils.agent import AgentConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "base" / "storage"
            base_config = AgentConfig(
                cli_type=CLIType.CLAUDE,
                session_id="base-session",
                session_storage_path=storage_path,
                include_session_in_prompt=True
            )

            agent = ExploreAgent(base_config)

            # Session config should be preserved
            assert agent.config.session_id == "base-session"
            assert agent.config.session_storage_path == storage_path
            assert agent.config.include_session_in_prompt is True

    @pytest.mark.asyncio
    async def test_different_sessions_are_isolated(self):
        """Test that different session IDs maintain separate histories"""
        config1 = ExploreAgentConfig(
            cli_type=CLIType.CLAUDE,
            session_id="session-1"
        )
        agent1 = ExploreAgent(config1)

        config2 = ExploreAgentConfig(
            cli_type=CLIType.CLAUDE,
            session_id="session-2"
        )
        agent2 = ExploreAgent(config2)

        with patch.object(agent1._executor, 'execute', new_callable=AsyncMock) as mock1:
            with patch.object(agent2._executor, 'execute', new_callable=AsyncMock) as mock2:
                mock1.return_value = "Answer from session 1"
                mock2.return_value = "Answer from session 2"

                # Agent 1 interaction
                await agent1.explore("Question for session 1")

                # Agent 2 interaction
                await agent2.explore("Question for session 2")

                # Sessions should be separate
                history1 = agent1.get_session_history()
                history2 = agent2.get_session_history()

                assert len(history1) == 2  # 1 user + 1 assistant
                assert len(history2) == 2  # 1 user + 1 assistant

                assert history1[0]["content"] == "Question for session 1"
                assert history2[0]["content"] == "Question for session 2"
