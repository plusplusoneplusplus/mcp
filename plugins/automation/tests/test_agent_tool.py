"""
Tests for AgentTool with simplified parameters
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from plugins.automation import AgentTool
from plugins.automation.tools.agent_tool import AgentOperationType
from utils.agent import CLIType


class TestAgentTool:
    """Tests for AgentTool"""

    def test_init(self):
        """Test agent tool initialization"""
        tool = AgentTool()

        assert tool.name == "agent"
        assert tool._agents == {}

    def test_name_property(self):
        """Test name property"""
        tool = AgentTool()
        assert tool.name == "agent"

    def test_description_property(self):
        """Test description property"""
        tool = AgentTool()
        description = tool.description

        assert "codebase" in description.lower()
        assert "agent" in description.lower()

    def test_input_schema(self):
        """Test simplified input schema"""
        tool = AgentTool()
        schema = tool.input_schema

        assert schema["type"] == "object"
        assert "operation" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "context" in schema["properties"]
        assert schema["required"] == ["operation", "prompt"]

        # Check operation enum
        operations = schema["properties"]["operation"]["enum"]
        assert "explore" in operations
        assert "find_implementation" in operations
        assert "analyze_structure" in operations
        assert "find_usage" in operations
        assert "explain_flow" in operations

        # Check context properties
        context_props = schema["properties"]["context"]["properties"]
        assert "codebase_path" in context_props
        assert "session_id" in context_props
        assert "model" in context_props
        assert "cli_type" in context_props

    def test_get_cli_type(self):
        """Test CLI type conversion"""
        tool = AgentTool()

        assert tool._get_cli_type("claude") == CLIType.CLAUDE
        assert tool._get_cli_type("codex") == CLIType.CODEX
        assert tool._get_cli_type("copilot") == CLIType.COPILOT
        assert tool._get_cli_type("CLAUDE") == CLIType.CLAUDE  # Case insensitive
        assert tool._get_cli_type(None) == CLIType.CLAUDE  # Default
        assert tool._get_cli_type("invalid") == CLIType.CLAUDE  # Fallback

    def test_get_or_create_agent(self):
        """Test agent creation and caching"""
        tool = AgentTool()

        # Create first agent
        agent1 = tool._get_or_create_agent(
            session_id="session1",
            cli_type=CLIType.CLAUDE,
            model="haiku",
            codebase_path="/project",
            working_directories=None,
        )

        assert agent1 is not None
        assert "session1" in tool._agents

        # Get same agent
        agent2 = tool._get_or_create_agent(
            session_id="session1",
            cli_type=CLIType.CLAUDE,
            model="haiku",
            codebase_path="/project",
            working_directories=None,
        )

        assert agent2 is agent1  # Same instance

        # Create different agent
        agent3 = tool._get_or_create_agent(
            session_id="session2",
            cli_type=CLIType.CLAUDE,
            model="haiku",
            codebase_path="/project",
            working_directories=None,
        )

        assert agent3 is not agent1  # Different instance
        assert "session2" in tool._agents

    def test_get_or_create_agent_default_session(self):
        """Test agent creation with default session"""
        tool = AgentTool()

        agent = tool._get_or_create_agent(
            session_id=None,
            cli_type=CLIType.CLAUDE,
            model=None,
            codebase_path=None,
            working_directories=None,
        )

        assert agent is not None
        assert "default" in tool._agents

    @pytest.mark.asyncio
    async def test_execute_tool_missing_operation(self):
        """Test execute_tool with missing operation"""
        tool = AgentTool()

        result = await tool.execute_tool({})

        assert "error" in result
        assert "operation" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_tool_missing_prompt(self):
        """Test execute_tool with missing prompt"""
        tool = AgentTool()

        result = await tool.execute_tool({
            "operation": "explore"
        })

        assert "error" in result
        assert "prompt" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_explore_operation(self):
        """Test explore operation with simplified parameters"""
        tool = AgentTool()

        # Mock the agent
        with patch.object(tool, '_get_or_create_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.explore = AsyncMock(return_value="Exploration result")
            mock_agent._get_session_id = MagicMock(return_value="test-session")
            mock_get_agent.return_value = mock_agent

            result = await tool.execute_tool({
                "operation": "explore",
                "prompt": "Where is the main entry point?",
                "context": {
                    "codebase_path": "/project"
                }
            })

            assert result["success"] is True
            assert result["operation"] == "explore"
            assert result["result"] == "Exploration result"
            assert result["session_id"] == "test-session"
            assert mock_agent.explore.called

    @pytest.mark.asyncio
    async def test_execute_explore_minimal(self):
        """Test explore with minimal parameters (no context)"""
        tool = AgentTool()

        with patch.object(tool, '_get_or_create_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.explore = AsyncMock(return_value="Result")
            mock_agent._get_session_id = MagicMock(return_value="default")
            mock_get_agent.return_value = mock_agent

            result = await tool.execute_tool({
                "operation": "explore",
                "prompt": "Where is authentication?"
            })

            assert result["success"] is True
            assert mock_agent.explore.called

    @pytest.mark.asyncio
    async def test_execute_find_implementation_operation(self):
        """Test find_implementation operation"""
        tool = AgentTool()

        with patch.object(tool, '_get_or_create_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.find_implementation = AsyncMock(return_value="Found in file.py:42")
            mock_agent._get_session_id = MagicMock(return_value="test-session")
            mock_get_agent.return_value = mock_agent

            result = await tool.execute_tool({
                "operation": "find_implementation",
                "prompt": "UserLogin",
                "context": {
                    "codebase_path": "/project"
                }
            })

            assert result["success"] is True
            assert result["operation"] == "find_implementation"
            assert result["result"] == "Found in file.py:42"
            assert mock_agent.find_implementation.called

    @pytest.mark.asyncio
    async def test_execute_analyze_structure_operation(self):
        """Test analyze_structure operation"""
        tool = AgentTool()

        with patch.object(tool, '_get_or_create_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.analyze_structure = AsyncMock(return_value="Structure analysis")
            mock_agent._get_session_id = MagicMock(return_value="test-session")
            mock_get_agent.return_value = mock_agent

            result = await tool.execute_tool({
                "operation": "analyze_structure",
                "prompt": "auth module",
                "context": {
                    "codebase_path": "/project"
                }
            })

            assert result["success"] is True
            assert result["operation"] == "analyze_structure"
            assert result["result"] == "Structure analysis"
            assert mock_agent.analyze_structure.called

    @pytest.mark.asyncio
    async def test_analyze_structure_empty_prompt(self):
        """Test analyze_structure with empty prompt (analyze entire codebase)"""
        tool = AgentTool()

        with patch.object(tool, '_get_or_create_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.analyze_structure = AsyncMock(return_value="Overall structure")
            mock_agent._get_session_id = MagicMock(return_value="test-session")
            mock_get_agent.return_value = mock_agent

            result = await tool.execute_tool({
                "operation": "analyze_structure",
                "prompt": "",
                "context": {
                    "codebase_path": "/project"
                }
            })

            assert result["success"] is True
            # Should call with component=None
            mock_agent.analyze_structure.assert_called_once_with(
                component_or_module=None,
                codebase_path="/project"
            )

    @pytest.mark.asyncio
    async def test_execute_find_usage_operation(self):
        """Test find_usage operation"""
        tool = AgentTool()

        with patch.object(tool, '_get_or_create_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.find_usage = AsyncMock(return_value="Usages found")
            mock_agent._get_session_id = MagicMock(return_value="test-session")
            mock_get_agent.return_value = mock_agent

            result = await tool.execute_tool({
                "operation": "find_usage",
                "prompt": "UserModel",
                "context": {
                    "codebase_path": "/project"
                }
            })

            assert result["success"] is True
            assert result["operation"] == "find_usage"
            assert result["result"] == "Usages found"
            assert mock_agent.find_usage.called

    @pytest.mark.asyncio
    async def test_execute_explain_flow_operation(self):
        """Test explain_flow operation"""
        tool = AgentTool()

        with patch.object(tool, '_get_or_create_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.explain_flow = AsyncMock(return_value="Flow explanation")
            mock_agent._get_session_id = MagicMock(return_value="test-session")
            mock_get_agent.return_value = mock_agent

            result = await tool.execute_tool({
                "operation": "explain_flow",
                "prompt": "user authentication",
                "context": {
                    "codebase_path": "/project"
                }
            })

            assert result["success"] is True
            assert result["operation"] == "explain_flow"
            assert result["result"] == "Flow explanation"
            assert mock_agent.explain_flow.called

    @pytest.mark.asyncio
    async def test_execute_with_full_context(self):
        """Test execution with full context object"""
        tool = AgentTool()

        with patch.object(tool, '_get_or_create_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.explore = AsyncMock(return_value="Result")
            mock_agent._get_session_id = MagicMock(return_value="custom-session")
            mock_get_agent.return_value = mock_agent

            result = await tool.execute_tool({
                "operation": "explore",
                "prompt": "Test question",
                "context": {
                    "codebase_path": "/project",
                    "session_id": "custom-session",
                    "model": "gpt-4",
                    "cli_type": "codex",
                    "focus_areas": ["auth", "database"],
                    "working_directories": ["/project/src"]
                }
            })

            assert result["success"] is True
            assert result["session_id"] == "custom-session"

            # Verify context was passed correctly
            call_args = mock_get_agent.call_args
            assert call_args.kwargs["cli_type"] == CLIType.CODEX
            assert call_args.kwargs["model"] == "gpt-4"
            assert call_args.kwargs["session_id"] == "custom-session"
            assert call_args.kwargs["codebase_path"] == "/project"
            assert call_args.kwargs["working_directories"] == ["/project/src"]

            # Verify focus_areas passed to explore
            explore_call_args = mock_agent.explore.call_args
            assert explore_call_args.kwargs["focus_areas"] == ["auth", "database"]

    @pytest.mark.asyncio
    async def test_execute_invalid_operation(self):
        """Test execution with invalid operation"""
        tool = AgentTool()

        result = await tool.execute_tool({
            "operation": "invalid_operation",
            "prompt": "test"
        })

        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_with_exception(self):
        """Test execution when agent raises exception"""
        tool = AgentTool()

        with patch.object(tool, '_get_or_create_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.explore = AsyncMock(side_effect=Exception("Test error"))
            mock_agent._get_session_id = MagicMock(return_value="test-session")
            mock_get_agent.return_value = mock_agent

            result = await tool.execute_tool({
                "operation": "explore",
                "prompt": "Test",
            })

            assert "error" in result
            assert "Test error" in result["error"]

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup method"""
        tool = AgentTool()

        # Create some agents
        tool._get_or_create_agent("session1", CLIType.CLAUDE, None, None, None)
        tool._get_or_create_agent("session2", CLIType.CLAUDE, None, None, None)

        assert len(tool._agents) == 2

        # Cleanup
        await tool.cleanup()

        assert len(tool._agents) == 0


class TestAgentToolIntegration:
    """Integration tests for AgentTool"""

    @pytest.mark.asyncio
    async def test_multi_operation_session(self):
        """Test multiple operations in same session"""
        tool = AgentTool()

        with patch.object(tool, '_get_or_create_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.explore = AsyncMock(return_value="Result 1")
            mock_agent.find_implementation = AsyncMock(return_value="Result 2")
            mock_agent._get_session_id = MagicMock(return_value="multi-session")
            mock_get_agent.return_value = mock_agent

            # First operation
            result1 = await tool.execute_tool({
                "operation": "explore",
                "prompt": "Question 1",
                "context": {"session_id": "multi-session"}
            })

            # Second operation (same session)
            result2 = await tool.execute_tool({
                "operation": "find_implementation",
                "prompt": "Feature",
                "context": {"session_id": "multi-session"}
            })

            assert result1["success"] is True
            assert result2["success"] is True

            # Should use same session
            assert mock_get_agent.call_count == 2
            assert mock_get_agent.call_args_list[0].kwargs["session_id"] == "multi-session"
            assert mock_get_agent.call_args_list[1].kwargs["session_id"] == "multi-session"

    @pytest.mark.asyncio
    async def test_simplified_workflow(self):
        """Test typical workflow with simplified parameters"""
        tool = AgentTool()

        with patch.object(tool, '_get_or_create_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.explore = AsyncMock(return_value="Auth is in src/auth.py")
            mock_agent.find_usage = AsyncMock(return_value="Used in 5 places")
            mock_agent._get_session_id = MagicMock(return_value="workflow-session")
            mock_get_agent.return_value = mock_agent

            # Simple explore
            r1 = await tool.execute_tool({
                "operation": "explore",
                "prompt": "Where is authentication?"
            })

            # Find usage with context
            r2 = await tool.execute_tool({
                "operation": "find_usage",
                "prompt": "authenticate_user",
                "context": {
                    "codebase_path": "/project",
                    "session_id": "workflow-session"
                }
            })

            assert r1["success"] is True
            assert r2["success"] is True
