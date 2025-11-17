"""
Tests for DecomposeAgent
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from plugins.automation.agents.decompose_agent import DecomposeAgent
from utils.agent import AgentConfig, CLIType


class TestDecomposeAgent:
    """Tests for DecomposeAgent"""

    def test_init(self):
        """Test decompose agent initialization"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        assert agent.config == config
        assert agent._executor is not None

    def test_init_with_session_config(self):
        """Test initialization with session configuration"""
        config = AgentConfig(
            cli_type=CLIType.CLAUDE,
            session_id="decompose-session",
            session_storage_path=Path("/tmp/sessions"),
            include_session_in_prompt=True
        )
        agent = DecomposeAgent(config)

        assert agent.config.session_id == "decompose-session"
        assert agent.config.session_storage_path == Path("/tmp/sessions")
        assert agent.config.include_session_in_prompt is True

    def test_get_system_prompt(self):
        """Test getting system prompt"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        prompt = agent.get_system_prompt()

        assert "Task Decomposition Agent" in prompt
        assert "Role" in prompt
        assert "parallelizable subtasks" in prompt
        assert "Capabilities" in prompt
        assert "Decomposition Guidelines" in prompt
        assert "Response Format" in prompt
        assert "JSON" in prompt

    def test_get_system_prompt_with_session(self):
        """Test getting system prompt with session context"""
        config = AgentConfig(
            cli_type=CLIType.CLAUDE,
            include_session_in_prompt=True,
            session_id="test-session"
        )
        agent = DecomposeAgent(config)

        prompt = agent.get_system_prompt()

        # Should use default system prompt with session context
        assert "Session" in prompt
        assert "test-session" in prompt
        assert "Decomposition Guidelines" in prompt

    def test_get_decomposition_instructions(self):
        """Test decomposition-specific instructions"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        instructions = agent._get_decomposition_instructions()

        assert "Decomposition Guidelines" in instructions
        assert "JSON" in instructions
        assert "subtopics" in instructions
        assert "importance" in instructions

    @pytest.mark.asyncio
    async def test_decompose_basic(self):
        """Test basic decompose method"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        mock_response = json.dumps({
            "reasoning": "Breaking down into authentication, authorization, and session management",
            "subtopic_count": 3,
            "subtopics": [
                {
                    "id": "subtopic_1",
                    "title": "Authentication Flow",
                    "exploration_task": "How does user authentication work?",
                    "importance": "high",
                    "expected_findings": "Authentication mechanism details"
                },
                {
                    "id": "subtopic_2",
                    "title": "Authorization",
                    "exploration_task": "How are permissions checked?",
                    "importance": "medium",
                    "expected_findings": "Permission system details"
                },
                {
                    "id": "subtopic_3",
                    "title": "Session Management",
                    "exploration_task": "How are sessions managed?",
                    "importance": "medium",
                    "expected_findings": "Session storage and lifecycle"
                }
            ]
        })

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = mock_response

            result = await agent.decompose(
                question="How does the authentication system work?",
                min_subtopics=2,
                max_subtopics=5
            )

            assert result == mock_response
            assert mock_execute.called

            # Verify the prompt includes the question and constraints
            called_prompt = mock_execute.call_args[0][0]
            assert "How does the authentication system work?" in called_prompt
            assert "between 2 and 5 subtopics" in called_prompt
            assert "JSON" in called_prompt

    @pytest.mark.asyncio
    async def test_decompose_with_default_limits(self):
        """Test decompose with default min/max subtopics"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        mock_response = json.dumps({
            "reasoning": "Test",
            "subtopic_count": 3,
            "subtopics": []
        })

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = mock_response

            await agent.decompose(question="Test question")

            # Verify default limits
            called_prompt = mock_execute.call_args[0][0]
            assert "between 2 and 6 subtopics" in called_prompt

    @pytest.mark.asyncio
    async def test_decompose_with_custom_limits(self):
        """Test decompose with custom subtopic limits"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        mock_response = json.dumps({
            "reasoning": "Test",
            "subtopic_count": 4,
            "subtopics": []
        })

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = mock_response

            await agent.decompose(
                question="Complex question",
                min_subtopics=3,
                max_subtopics=8
            )

            called_prompt = mock_execute.call_args[0][0]
            assert "between 3 and 8 subtopics" in called_prompt

    @pytest.mark.asyncio
    async def test_decompose_includes_history_false(self):
        """Test that decompose doesn't include history by default"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        mock_response = json.dumps({
            "reasoning": "Test",
            "subtopic_count": 2,
            "subtopics": []
        })

        with patch.object(agent, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_response

            await agent.decompose(question="Test question")

            # Verify include_history=False was passed to invoke
            call_kwargs = mock_invoke.call_args[1]
            assert call_kwargs.get('include_history') is False

    @pytest.mark.asyncio
    async def test_decompose_complex_question(self):
        """Test decomposing a complex multi-faceted question"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        complex_question = """
        How does the MCP workflow system work, including:
        - YAML configuration parsing
        - Step execution and dependencies
        - Agent integration
        - Error handling
        """

        mock_response = json.dumps({
            "reasoning": "Breaking down into 4 main components",
            "subtopic_count": 4,
            "subtopics": [
                {
                    "id": "subtopic_1",
                    "title": "YAML Configuration",
                    "exploration_task": "How are workflow YAML files parsed?",
                    "importance": "high",
                    "expected_findings": "Configuration structure and validation"
                },
                {
                    "id": "subtopic_2",
                    "title": "Step Execution",
                    "exploration_task": "How are workflow steps executed?",
                    "importance": "high",
                    "expected_findings": "Execution engine and dependency resolution"
                },
                {
                    "id": "subtopic_3",
                    "title": "Agent Integration",
                    "exploration_task": "How are agents integrated into workflows?",
                    "importance": "medium",
                    "expected_findings": "Agent invocation and communication"
                },
                {
                    "id": "subtopic_4",
                    "title": "Error Handling",
                    "exploration_task": "How are errors handled in workflows?",
                    "importance": "medium",
                    "expected_findings": "Error propagation and recovery"
                }
            ]
        })

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = mock_response

            result = await agent.decompose(
                question=complex_question,
                min_subtopics=3,
                max_subtopics=6
            )

            assert result == mock_response
            assert mock_execute.called

            # Verify the full question is in the prompt
            called_prompt = mock_execute.call_args[0][0]
            assert "MCP workflow system" in called_prompt
            assert "YAML configuration" in called_prompt

    @pytest.mark.asyncio
    async def test_decompose_with_session_persistence(self):
        """Test decompose with session persistence enabled"""
        config = AgentConfig(
            cli_type=CLIType.CLAUDE,
            session_id="decompose-123",
            session_storage_path=Path("/tmp/sessions"),
            include_session_in_prompt=True
        )
        agent = DecomposeAgent(config)

        mock_response = json.dumps({
            "reasoning": "Test",
            "subtopic_count": 2,
            "subtopics": []
        })

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = mock_response

            await agent.decompose(question="Test question")

            # Session config should be available
            assert agent.config.session_id == "decompose-123"
            assert agent.config.session_storage_path == Path("/tmp/sessions")

    def test_repr(self):
        """Test agent string representation"""
        config = AgentConfig(
            cli_type=CLIType.CLAUDE,
            model="haiku",
            session_id="decompose-456"
        )
        agent = DecomposeAgent(config)

        repr_str = repr(agent)

        assert "DecomposeAgent" in repr_str
        assert "cli_type='claude'" in repr_str
        assert "model='haiku'" in repr_str
        assert "session_id='decompose-456'" in repr_str

    @pytest.mark.asyncio
    async def test_decompose_prompt_structure(self):
        """Test that decompose creates well-structured prompts"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        mock_response = json.dumps({
            "reasoning": "Test",
            "subtopic_count": 2,
            "subtopics": []
        })

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = mock_response

            await agent.decompose(
                question="Test question",
                min_subtopics=2,
                max_subtopics=4
            )

            called_prompt = mock_execute.call_args[0][0]

            # Verify prompt structure
            assert "Analyze the following question" in called_prompt
            assert "Question:" in called_prompt
            assert "Test question" in called_prompt
            assert "Guidelines:" in called_prompt
            assert "focused and independently explorable" in called_prompt
            assert "Respond with a JSON object:" in called_prompt
            assert "reasoning" in called_prompt
            assert "subtopic_count" in called_prompt
            assert "subtopics" in called_prompt
            assert "exploration_task" in called_prompt
            assert "importance" in called_prompt
            assert "expected_findings" in called_prompt


class TestDecomposeAgentIntegration:
    """Integration tests for DecomposeAgent"""

    @pytest.mark.asyncio
    async def test_decompose_multiple_questions(self):
        """Test decomposing multiple questions in sequence"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        responses = [
            json.dumps({
                "reasoning": "First decomposition",
                "subtopic_count": 2,
                "subtopics": [
                    {"id": "s1", "title": "T1", "exploration_task": "E1", "importance": "high", "expected_findings": "F1"},
                    {"id": "s2", "title": "T2", "exploration_task": "E2", "importance": "medium", "expected_findings": "F2"}
                ]
            }),
            json.dumps({
                "reasoning": "Second decomposition",
                "subtopic_count": 3,
                "subtopics": [
                    {"id": "s1", "title": "T1", "exploration_task": "E1", "importance": "high", "expected_findings": "F1"},
                    {"id": "s2", "title": "T2", "exploration_task": "E2", "importance": "medium", "expected_findings": "F2"},
                    {"id": "s3", "title": "T3", "exploration_task": "E3", "importance": "low", "expected_findings": "F3"}
                ]
            })
        ]

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = responses

            # First decomposition
            r1 = await agent.decompose("How does authentication work?")
            assert "First decomposition" in r1

            # Second decomposition
            r2 = await agent.decompose("How does the database layer work?")
            assert "Second decomposition" in r2

            # Both should have been called
            assert mock_execute.call_count == 2

    @pytest.mark.asyncio
    async def test_decompose_with_different_models(self):
        """Test decompose with different AI models"""
        for cli_type in [CLIType.CLAUDE, CLIType.COPILOT]:
            config = AgentConfig(cli_type=cli_type)
            agent = DecomposeAgent(config)

            mock_response = json.dumps({
                "reasoning": f"Decomposition using {cli_type.value}",
                "subtopic_count": 2,
                "subtopics": []
            })

            with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = mock_response

                result = await agent.decompose("Test question")
                assert cli_type.value in result


class TestDecomposeAgentErrorHandling:
    """Tests for error handling in DecomposeAgent"""

    @pytest.mark.asyncio
    async def test_decompose_with_executor_error(self):
        """Test decompose handles executor errors gracefully"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("Executor error")

            with pytest.raises(Exception) as exc_info:
                await agent.decompose("Test question")

            assert "Executor error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_decompose_with_empty_question(self):
        """Test decompose with empty question string"""
        config = AgentConfig(cli_type=CLIType.CLAUDE)
        agent = DecomposeAgent(config)

        mock_response = json.dumps({
            "reasoning": "No question provided",
            "subtopic_count": 0,
            "subtopics": []
        })

        with patch.object(agent._executor, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = mock_response

            result = await agent.decompose("")

            # Should still call executor with empty question
            assert mock_execute.called
            called_prompt = mock_execute.call_args[0][0]
            assert "Question:" in called_prompt


class TestDecomposeAgentSessionManagement:
    """Tests for session management in DecomposeAgent"""

    @pytest.mark.asyncio
    async def test_session_id_propagation(self):
        """Test that session_id is properly propagated"""
        config = AgentConfig(
            cli_type=CLIType.CLAUDE,
            session_id="test-session-123"
        )
        agent = DecomposeAgent(config)

        assert agent.config.session_id == "test-session-123"
        assert agent._get_session_id() == "test-session-123"

    @pytest.mark.asyncio
    async def test_session_storage_path_propagation(self):
        """Test that session_storage_path is properly propagated"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "sessions"
            config = AgentConfig(
                cli_type=CLIType.CLAUDE,
                session_storage_path=storage_path
            )
            agent = DecomposeAgent(config)

            assert agent.config.session_storage_path == storage_path

    @pytest.mark.asyncio
    async def test_include_session_in_prompt_affects_system_prompt(self):
        """Test that include_session_in_prompt affects system prompt"""
        # Without session in prompt
        config_without = AgentConfig(
            cli_type=CLIType.CLAUDE,
            include_session_in_prompt=False
        )
        agent_without = DecomposeAgent(config_without)
        prompt_without = agent_without.get_system_prompt()

        # With session in prompt
        config_with = AgentConfig(
            cli_type=CLIType.CLAUDE,
            include_session_in_prompt=True,
            session_id="test-session"
        )
        agent_with = DecomposeAgent(config_with)
        prompt_with = agent_with.get_system_prompt()

        # Prompts should be different
        assert prompt_without != prompt_with
        # Session-enabled prompt should include session info
        assert "Session" in prompt_with or "test-session" in prompt_with

    @pytest.mark.asyncio
    async def test_unified_session_config(self):
        """Test that all session config parameters work together"""
        config = AgentConfig(
            cli_type=CLIType.CLAUDE,
            session_id="unified-session",
            session_storage_path=Path("/tmp/unified"),
            include_session_in_prompt=True
        )
        agent = DecomposeAgent(config)

        # All session parameters should be set
        assert agent.config.session_id == "unified-session"
        assert agent.config.session_storage_path == Path("/tmp/unified")
        assert agent.config.include_session_in_prompt is True

        # System prompt should reflect session config
        prompt = agent.get_system_prompt()
        assert "Session" in prompt or "unified-session" in prompt
