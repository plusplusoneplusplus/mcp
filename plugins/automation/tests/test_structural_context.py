"""
Tests for Structural Context (WorkflowContext)
"""

import pytest
from datetime import datetime

from plugins.automation.context import (
    WorkflowContext,
    StepResult,
    StepStatus,
)


class TestStepResult:
    """Tests for StepResult."""

    def test_step_result_creation(self):
        """Test creating a step result."""
        result = StepResult(
            step_id="test_step",
            status=StepStatus.COMPLETED,
            result={"data": "value"},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        assert result.step_id == "test_step"
        assert result.status == StepStatus.COMPLETED
        assert result.result == {"data": "value"}
        assert result.error is None
        assert result.retry_count == 0

    def test_step_result_to_dict(self):
        """Test converting step result to dict."""
        started = datetime.utcnow()
        completed = datetime.utcnow()

        result = StepResult(
            step_id="test_step",
            status=StepStatus.COMPLETED,
            result="output",
            started_at=started,
            completed_at=completed,
            retry_count=2,
        )

        result_dict = result.to_dict()

        assert result_dict["step_id"] == "test_step"
        assert result_dict["status"] == "completed"
        assert result_dict["result"] == "output"
        assert result_dict["started_at"] == started.isoformat()
        assert result_dict["completed_at"] == completed.isoformat()
        assert result_dict["retry_count"] == 2


class TestWorkflowContext:
    """Tests for WorkflowContext."""

    def test_context_creation(self):
        """Test creating a workflow context."""
        context = WorkflowContext(
            inputs={"key": "value"},
            workflow_id="test-workflow",
            execution_id="exec-123",
        )

        assert context.inputs == {"key": "value"}
        assert context.workflow_id == "test-workflow"
        assert context.execution_id == "exec-123"
        assert context.step_results == {}
        assert context.outputs == {}

    def test_get_input(self):
        """Test getting input values."""
        context = WorkflowContext(
            inputs={"param1": "value1", "param2": 42}
        )

        assert context.get("inputs.param1") == "value1"
        assert context.get("inputs.param2") == 42
        assert context.get("inputs.missing", "default") == "default"

    def test_get_step_result(self):
        """Test getting step result values."""
        context = WorkflowContext()

        step_result = StepResult(
            step_id="step1",
            status=StepStatus.COMPLETED,
            result={"key": "value"},
        )
        context.set_step_result("step1", step_result)

        assert context.get("steps.step1.result") == {"key": "value"}
        assert context.get("steps.step1.status") == "completed"

    def test_get_nested_result(self):
        """Test getting nested values from step results."""
        context = WorkflowContext()

        step_result = StepResult(
            step_id="step1",
            status=StepStatus.COMPLETED,
            result={"nested": {"key": "value"}},
        )
        context.set_step_result("step1", step_result)

        assert context.get("steps.step1.result.nested.key") == "value"

    def test_get_step_status(self):
        """Test getting step status."""
        context = WorkflowContext()

        step_result = StepResult(
            step_id="step1",
            status=StepStatus.RUNNING,
            result=None,
        )
        context.set_step_result("step1", step_result)

        assert context.get_step_status("step1") == StepStatus.RUNNING
        assert context.get_step_status("missing_step") is None

    def test_set_output(self):
        """Test setting workflow outputs."""
        context = WorkflowContext()

        context.set_output("result", "value")
        context.set_output("count", 42)

        assert context.outputs["result"] == "value"
        assert context.outputs["count"] == 42

    def test_resolve_template_simple(self):
        """Test resolving simple templates."""
        context = WorkflowContext(
            inputs={"name": "test", "count": 5}
        )

        assert context.resolve_template("{{ inputs.name }}") == "test"
        assert context.resolve_template("{{ inputs.count }}") == 5

    def test_resolve_template_with_text(self):
        """Test resolving templates mixed with text."""
        context = WorkflowContext(
            inputs={"feature": "auth", "path": "/code"}
        )

        template = "Exploring {{ inputs.feature }} in {{ inputs.path }}"
        expected = "Exploring auth in /code"

        assert context.resolve_template(template) == expected

    def test_resolve_template_with_step_result(self):
        """Test resolving templates with step results."""
        context = WorkflowContext()

        step_result = StepResult(
            step_id="analyze",
            status=StepStatus.COMPLETED,
            result="Analysis complete",
        )
        context.set_step_result("analyze", step_result)

        assert context.resolve_template("{{ steps.analyze.result }}") == "Analysis complete"

    def test_resolve_template_with_context_get(self):
        """Test resolving templates with context.get()."""
        context = WorkflowContext(
            inputs={"key": "value"}
        )

        # With default
        template = '{{ context.get("inputs.missing", "default") }}'
        assert context.resolve_template(template) == "default"

        # Without default
        template = '{{ context.get("inputs.key") }}'
        assert context.resolve_template(template) == "value"

    def test_resolve_template_no_template(self):
        """Test resolving non-template strings."""
        context = WorkflowContext()

        assert context.resolve_template("plain text") == "plain text"
        assert context.resolve_template("no {{ templates here") == "no {{ templates here"

    def test_resolve_dict(self):
        """Test resolving all templates in a dictionary."""
        context = WorkflowContext(
            inputs={"feature": "auth", "path": "/code"}
        )

        data = {
            "question": "Where is {{ inputs.feature }}?",
            "codebase_path": "{{ inputs.path }}",
            "static": "no template",
        }

        resolved = context.resolve_dict(data)

        assert resolved["question"] == "Where is auth?"
        assert resolved["codebase_path"] == "/code"
        assert resolved["static"] == "no template"

    def test_to_dict(self):
        """Test converting context to dict."""
        context = WorkflowContext(
            inputs={"key": "value"},
            workflow_id="test-wf",
            execution_id="exec-123",
        )

        step_result = StepResult(
            step_id="step1",
            status=StepStatus.COMPLETED,
            result="output",
        )
        context.set_step_result("step1", step_result)
        context.set_output("final", "result")

        context_dict = context.to_dict()

        assert context_dict["inputs"] == {"key": "value"}
        assert context_dict["metadata"]["workflow_id"] == "test-wf"
        assert context_dict["metadata"]["execution_id"] == "exec-123"
        assert "step1" in context_dict["step_results"]
        assert context_dict["outputs"] == {"final": "result"}

    def test_from_dict(self):
        """Test creating context from dict."""
        data = {
            "inputs": {"key": "value"},
            "metadata": {
                "workflow_id": "test-wf",
                "execution_id": "exec-123",
            },
            "step_results": {
                "step1": {
                    "step_id": "step1",
                    "status": "completed",
                    "result": "output",
                    "error": None,
                    "started_at": None,
                    "completed_at": None,
                    "retry_count": 0,
                }
            },
            "outputs": {"final": "result"},
        }

        context = WorkflowContext.from_dict(data)

        assert context.inputs == {"key": "value"}
        assert context.workflow_id == "test-wf"
        assert context.execution_id == "exec-123"
        assert "step1" in context.step_results
        assert context.outputs == {"final": "result"}

    def test_repr(self):
        """Test string representation."""
        context = WorkflowContext(
            workflow_id="test-wf",
            execution_id="exec-123",
        )

        repr_str = repr(context)

        assert "WorkflowContext" in repr_str
        assert "test-wf" in repr_str
        assert "exec-123" in repr_str
