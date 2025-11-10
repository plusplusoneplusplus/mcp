"""Tests for AI-powered split operation."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from plugins.automation.workflows.steps.operations import AISplitOperation


class TestAISplitOperation:
    """Test AI-powered split operation."""

    def test_validation_success(self):
        """Test validation with valid config."""
        config = {"max_tasks": 5, "min_tasks": 2}
        inputs = {"goal": "Understand authentication"}

        operation = AISplitOperation(config, inputs)
        assert operation.validate() is None

    def test_validation_missing_goal(self):
        """Test validation fails without goal."""
        config = {}
        inputs = {}

        operation = AISplitOperation(config, inputs)
        error = operation.validate()
        assert error is not None
        assert "goal" in error.lower()

    def test_validation_invalid_task_counts(self):
        """Test validation fails when max_tasks < min_tasks."""
        config = {"max_tasks": 2, "min_tasks": 5}
        inputs = {"goal": "Test"}

        operation = AISplitOperation(config, inputs)
        error = operation.validate()
        assert error is not None
        assert "max_tasks" in error

    def test_build_split_prompt_basic(self):
        """Test prompt building with basic inputs."""
        config = {"min_tasks": 2, "max_tasks": 5}
        inputs = {"goal": "Understand authentication"}

        operation = AISplitOperation(config, inputs)
        prompt = operation._build_split_prompt(
            goal="Understand authentication",
            codebase_path=None,
            focus_areas=[],
            constraints=None,
            context="",
            min_tasks=2,
            max_tasks=5
        )

        assert "Understand authentication" in prompt
        assert "2-5" in prompt
        assert "JSON" in prompt

    def test_build_split_prompt_comprehensive(self):
        """Test prompt building with all optional fields."""
        config = {}
        inputs = {"goal": "Test"}

        operation = AISplitOperation(config, inputs)
        prompt = operation._build_split_prompt(
            goal="Understand security",
            codebase_path="/path/to/code",
            focus_areas=["authentication", "authorization"],
            constraints="Focus on backend only",
            context="Legacy system",
            min_tasks=3,
            max_tasks=8
        )

        assert "Understand security" in prompt
        assert "/path/to/code" in prompt
        assert "authentication" in prompt
        assert "Focus on backend only" in prompt
        assert "Legacy system" in prompt

    @pytest.mark.asyncio
    async def test_execute_with_valid_ai_response(self):
        """Test execution with valid AI JSON response."""
        config = {"model": "haiku", "max_tasks": 5, "min_tasks": 2}
        inputs = {"goal": "Understand auth", "codebase_path": "/code"}

        operation = AISplitOperation(config, inputs)

        # Mock AI response
        mock_ai_response = {
            "reasoning": "Split into login, session, and security",
            "tasks": [
                {
                    "title": "Login Flow",
                    "query": "Trace user login",
                    "type": "flow",
                    "priority": "high",
                    "estimated_complexity": "moderate"
                },
                {
                    "title": "Session Management",
                    "query": "Find session handling",
                    "type": "implementation",
                    "priority": "high",
                    "estimated_complexity": "complex"
                }
            ]
        }

        # Mock the AI call
        with patch.object(operation, '_call_ai_for_split', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_ai_response

            result = await operation.execute()

            assert result["task_count"] == 2
            assert len(result["tasks"]) == 2
            assert result["reasoning"] == "Split into login, session, and security"
            assert result["tasks"][0]["title"] == "Login Flow"
            assert result["tasks"][0]["index"] == 0
            assert result["metadata"]["goal"] == "Understand auth"

    @pytest.mark.asyncio
    async def test_execute_with_too_many_tasks(self):
        """Test execution truncates when AI generates too many tasks."""
        config = {"max_tasks": 3, "min_tasks": 2}
        inputs = {"goal": "Test"}

        operation = AISplitOperation(config, inputs)

        # Mock AI response with too many tasks
        mock_ai_response = {
            "reasoning": "Detailed split",
            "tasks": [
                {"title": f"Task {i}", "query": f"Q{i}", "type": "question", "priority": "medium"}
                for i in range(10)  # Generate 10 tasks
            ]
        }

        with patch.object(operation, '_call_ai_for_split', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_ai_response

            result = await operation.execute()

            # Should be truncated to max_tasks
            assert result["task_count"] == 3
            assert len(result["tasks"]) == 3

    @pytest.mark.asyncio
    async def test_call_ai_for_split_with_clean_json(self):
        """Test AI call with clean JSON response."""
        config = {}
        inputs = {"goal": "Test"}
        operation = AISplitOperation(config, inputs)

        mock_response = json.dumps({
            "reasoning": "Test reasoning",
            "tasks": [
                {"title": "Task 1", "query": "Q1", "type": "question", "priority": "high"}
            ]
        })

        with patch('utils.agent.cli_executor.CLIExecutor') as MockExecutor:
            mock_executor = MockExecutor.return_value
            mock_executor.execute = AsyncMock(return_value=mock_response)

            result = await operation._call_ai_for_split("test prompt", "haiku")

            assert result["reasoning"] == "Test reasoning"
            assert len(result["tasks"]) == 1

    @pytest.mark.asyncio
    async def test_call_ai_for_split_with_json_in_text(self):
        """Test AI call when JSON is embedded in text."""
        config = {}
        inputs = {"goal": "Test"}
        operation = AISplitOperation(config, inputs)

        # AI response with explanation before/after JSON
        mock_response = """Here's my analysis:

        {
            "reasoning": "Embedded JSON",
            "tasks": [
                {"title": "Task", "query": "Q", "type": "question", "priority": "high"}
            ]
        }

        Hope this helps!"""

        with patch('utils.agent.cli_executor.CLIExecutor') as MockExecutor:
            mock_executor = MockExecutor.return_value
            mock_executor.execute = AsyncMock(return_value=mock_response)

            result = await operation._call_ai_for_split("test prompt", "haiku")

            assert result["reasoning"] == "Embedded JSON"
            assert len(result["tasks"]) == 1

    @pytest.mark.asyncio
    async def test_call_ai_for_split_fallback_on_error(self):
        """Test fallback split when AI call fails."""
        config = {}
        inputs = {"goal": "Test authentication"}
        operation = AISplitOperation(config, inputs)

        with patch('utils.agent.cli_executor.CLIExecutor') as MockExecutor:
            mock_executor = MockExecutor.return_value
            mock_executor.execute = AsyncMock(side_effect=Exception("API error"))

            result = await operation._call_ai_for_split("test prompt", "haiku")

            # Should return fallback split
            assert "Fallback split" in result["reasoning"]
            assert len(result["tasks"]) == 3  # Default fallback has 3 tasks
            assert "Test authentication" in result["tasks"][0]["query"]

    @pytest.mark.asyncio
    async def test_call_ai_for_split_fallback_on_invalid_json(self):
        """Test fallback when AI returns invalid JSON."""
        config = {}
        inputs = {"goal": "Test"}
        operation = AISplitOperation(config, inputs)

        # AI returns text without JSON
        mock_response = "I cannot parse this request as JSON"

        with patch('utils.agent.cli_executor.CLIExecutor') as MockExecutor:
            mock_executor = MockExecutor.return_value
            mock_executor.execute = AsyncMock(return_value=mock_response)

            result = await operation._call_ai_for_split("test prompt", "haiku")

            # Should use fallback
            assert "Fallback split" in result["reasoning"]
            assert len(result["tasks"]) >= 3

    def test_create_fallback_split(self):
        """Test fallback split generation."""
        config = {}
        inputs = {"goal": "Understand database operations"}
        operation = AISplitOperation(config, inputs)

        result = operation._create_fallback_split("Some error")

        assert "Fallback split" in result["reasoning"]
        assert len(result["tasks"]) == 3
        assert "database operations" in result["tasks"][0]["query"]
        assert all("title" in task for task in result["tasks"])
        assert all("query" in task for task in result["tasks"])
        assert all("type" in task for task in result["tasks"])

    def test_parse_ai_response_valid(self):
        """Test parsing valid AI response."""
        config = {}
        inputs = {"goal": "Test"}
        operation = AISplitOperation(config, inputs)

        ai_response = {
            "reasoning": "Test",
            "tasks": [
                {"title": "T1", "query": "Q1", "type": "question", "priority": "high"},
                {"title": "T2", "query": "Q2", "type": "implementation", "priority": "medium"}
            ]
        }

        tasks = operation._parse_ai_response(ai_response, min_tasks=2, max_tasks=5)

        assert len(tasks) == 2
        assert tasks[0]["index"] == 0
        assert tasks[1]["index"] == 1

    @pytest.mark.asyncio
    async def test_execute_with_focus_areas(self):
        """Test execution with focus areas."""
        config = {"max_tasks": 5}
        inputs = {
            "goal": "Understand system",
            "focus_areas": ["performance", "security"],
            "constraints": "Backend only"
        }

        operation = AISplitOperation(config, inputs)

        mock_response = {
            "reasoning": "Focused on performance and security",
            "tasks": [
                {"title": "Security", "query": "Security aspects", "type": "question", "priority": "high"}
            ]
        }

        with patch.object(operation, '_call_ai_for_split', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            result = await operation.execute()

            # Verify focus areas were included in the call
            call_args = mock_call.call_args[0][0]  # Get prompt
            assert "performance" in call_args
            assert "security" in call_args
            assert "Backend only" in call_args


class TestAISplitIntegration:
    """Integration tests for AI split with CLIExecutor."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_ai_split_execution(self):
        """
        Integration test with real CLIExecutor (mocked).

        This tests the full flow including CLIExecutor integration.
        """
        config = {"model": "haiku", "max_tasks": 5, "min_tasks": 3}
        inputs = {
            "goal": "Understand authentication flow in the application",
            "codebase_path": "/path/to/code",
            "focus_areas": ["security", "user management"]
        }

        operation = AISplitOperation(config, inputs)

        # Mock CLIExecutor at a higher level
        mock_cli_response = json.dumps({
            "reasoning": "Authentication involves login, session, and security. Splitting into focused areas.",
            "tasks": [
                {
                    "title": "User Login Flow",
                    "query": "Trace the user login process from form submission to session creation",
                    "type": "flow",
                    "priority": "high",
                    "estimated_complexity": "complex"
                },
                {
                    "title": "Session Management",
                    "query": "Investigate how user sessions are stored and validated",
                    "type": "implementation",
                    "priority": "high",
                    "estimated_complexity": "moderate"
                },
                {
                    "title": "Security Mechanisms",
                    "query": "Find password hashing, encryption, and security measures",
                    "type": "structure",
                    "priority": "high",
                    "estimated_complexity": "moderate"
                },
                {
                    "title": "User Management",
                    "query": "Explore user creation, updates, and permission management",
                    "type": "implementation",
                    "priority": "medium",
                    "estimated_complexity": "simple"
                }
            ]
        })

        with patch('utils.agent.cli_executor.CLIExecutor') as MockExecutor:
            mock_executor = MockExecutor.return_value
            mock_executor.execute = AsyncMock(return_value=mock_cli_response)

            result = await operation.execute()

            # Verify execution
            assert mock_executor.execute.called
            prompt = mock_executor.execute.call_args[0][0]
            assert "Understand authentication flow" in prompt
            assert "security" in prompt

            # Verify results
            assert result["task_count"] == 4
            assert len(result["tasks"]) == 4
            assert "Authentication involves" in result["reasoning"]

            # Verify task structure
            first_task = result["tasks"][0]
            assert first_task["title"] == "User Login Flow"
            assert first_task["type"] == "flow"
            assert first_task["priority"] == "high"
            assert "index" in first_task
