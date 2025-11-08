"""
Tests for WorkflowEngine
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from plugins.automation.workflows import (
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowContext,
)
from plugins.automation.workflows.engine import WorkflowStatus
from plugins.automation.context import StepStatus


class TestWorkflowEngine:
    """Tests for WorkflowEngine."""

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(self):
        """Test executing a simple single-step workflow."""
        yaml_str = """
workflow:
  name: "simple"

  inputs:
    question:
      type: string
      required: true

  steps:
    - id: explore
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "{{ inputs.question }}"
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        # Mock agent execution via AgentRegistry
        mock_agent_class = MagicMock()
        mock_agent = mock_agent_class.return_value
        mock_agent.explore = AsyncMock(return_value="Result from agent")

        with patch('plugins.automation.workflows.steps.agent_step.AgentRegistry.get_agent_class', return_value=mock_agent_class):
            result = await engine.execute(
                workflow,
                inputs={"question": "test question"}
            )

            assert result.status == WorkflowStatus.COMPLETED
            assert "explore" in result.step_results
            assert result.step_results["explore"].status == StepStatus.COMPLETED
            assert mock_agent.explore.called

    @pytest.mark.asyncio
    async def test_execute_with_dependencies(self):
        """Test executing workflow with step dependencies."""
        yaml_str = """
workflow:
  name: "dependent"

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "first"

    - id: step2
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "second"
      depends_on: [step1]
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        # Mock agent execution via AgentRegistry
        mock_agent_class = MagicMock()
        mock_agent = mock_agent_class.return_value
        mock_agent.explore = AsyncMock(side_effect=["Result 1", "Result 2"])

        with patch('plugins.automation.workflows.steps.agent_step.AgentRegistry.get_agent_class', return_value=mock_agent_class):
            result = await engine.execute(workflow)

            assert result.status == WorkflowStatus.COMPLETED
            assert len(result.step_results) == 2
            assert result.step_results["step1"].status == StepStatus.COMPLETED
            assert result.step_results["step2"].status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_validates_workflow(self):
        """Test that engine validates workflow before execution."""
        # Invalid workflow (missing agent name)
        yaml_str = """
workflow:
  name: "invalid"

  steps:
    - id: step1
      type: agent
      operation: explore
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        with pytest.raises(ValueError, match="Invalid workflow"):
            await engine.execute(workflow)

    @pytest.mark.asyncio
    async def test_execute_validates_inputs(self):
        """Test that engine validates required inputs."""
        yaml_str = """
workflow:
  name: "test"

  inputs:
    required_param:
      type: string
      required: true

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        # Missing required input
        with pytest.raises(ValueError, match="Required input"):
            await engine.execute(workflow, inputs={})

    @pytest.mark.asyncio
    async def test_execute_handles_step_failure(self):
        """Test handling step failure with stop policy."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: failing_step
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "test"
      on_error: stop
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        # Mock agent to raise exception via AgentRegistry
        mock_agent_class = MagicMock()
        mock_agent = mock_agent_class.return_value
        mock_agent.explore = AsyncMock(side_effect=Exception("Test error"))

        with patch('plugins.automation.workflows.steps.agent_step.AgentRegistry.get_agent_class', return_value=mock_agent_class):
            result = await engine.execute(workflow)

            assert result.status == WorkflowStatus.FAILED
            assert "failing_step" in result.step_results
            assert result.step_results["failing_step"].status == StepStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_continues_on_error(self):
        """Test continuing execution when step fails with continue policy."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: failing_step
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "test"
      on_error: continue

    - id: success_step
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "test2"
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        # Mock agent - first fails, second succeeds via AgentRegistry
        mock_agent_class = MagicMock()
        mock_agent = mock_agent_class.return_value
        mock_agent.explore = AsyncMock(side_effect=[
            Exception("Test error"),
            "Success result"
        ])

        with patch('plugins.automation.workflows.steps.agent_step.AgentRegistry.get_agent_class', return_value=mock_agent_class):
            result = await engine.execute(workflow)

            assert result.status == WorkflowStatus.PARTIAL
            assert result.step_results["failing_step"].status == StepStatus.FAILED
            assert result.step_results["success_step"].status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_with_retry(self):
        """Test step retry on failure."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: retry_step
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "test"
      retry:
        max_attempts: 3
        backoff: fixed
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        # Mock agent - fail twice, then succeed via AgentRegistry
        mock_agent_class = MagicMock()
        mock_agent = mock_agent_class.return_value
        mock_agent.explore = AsyncMock(side_effect=[
            Exception("Fail 1"),
            Exception("Fail 2"),
            "Success"
        ])

        with patch('plugins.automation.workflows.steps.agent_step.AgentRegistry.get_agent_class', return_value=mock_agent_class):
            result = await engine.execute(workflow)

            assert result.status == WorkflowStatus.COMPLETED
            assert result.step_results["retry_step"].status == StepStatus.COMPLETED
            assert result.step_results["retry_step"].retry_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_existing_context(self):
        """Test resuming execution with existing context."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "test"
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        # Create context with execution ID
        context = WorkflowContext(
            workflow_id="test",
            execution_id="existing-exec-123"
        )

        # Mock agent execution via AgentRegistry
        mock_agent_class = MagicMock()
        mock_agent = mock_agent_class.return_value
        mock_agent.explore = AsyncMock(return_value="Result")

        with patch('plugins.automation.workflows.steps.agent_step.AgentRegistry.get_agent_class', return_value=mock_agent_class):
            result = await engine.execute(workflow, context=context)

            assert result.execution_id == "existing-exec-123"

    @pytest.mark.asyncio
    async def test_execute_populates_result_fields(self):
        """Test that execution result is fully populated."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "test"
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        # Mock agent execution via AgentRegistry
        mock_agent_class = MagicMock()
        mock_agent = mock_agent_class.return_value
        mock_agent.explore = AsyncMock(return_value="Result")

        with patch('plugins.automation.workflows.steps.agent_step.AgentRegistry.get_agent_class', return_value=mock_agent_class):
            result = await engine.execute(workflow)

            assert result.workflow_id == "test"
            assert result.execution_id is not None
            assert result.status == WorkflowStatus.COMPLETED
            assert result.started_at is not None
            assert result.completed_at is not None
            assert len(result.step_results) == 1

    @pytest.mark.asyncio
    async def test_execute_result_to_dict(self):
        """Test converting execution result to dict."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "test"
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        # Mock agent execution via AgentRegistry
        mock_agent_class = MagicMock()
        mock_agent = mock_agent_class.return_value
        mock_agent.explore = AsyncMock(return_value="Result")

        with patch('plugins.automation.workflows.steps.agent_step.AgentRegistry.get_agent_class', return_value=mock_agent_class):
            result = await engine.execute(workflow)
            result_dict = result.to_dict()

            assert result_dict["workflow_id"] == "test"
            assert result_dict["status"] == "completed"
            assert "step1" in result_dict["step_results"]
            assert result_dict["started_at"] is not None
            assert result_dict["completed_at"] is not None
