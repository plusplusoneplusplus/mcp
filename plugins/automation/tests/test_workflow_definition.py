"""
Tests for WorkflowDefinition
"""

import pytest
import tempfile
from pathlib import Path

from plugins.automation.workflows.definition import (
    WorkflowDefinition,
    WorkflowInput,
    WorkflowOutput,
    StepDefinition,
)


class TestWorkflowInput:
    """Tests for WorkflowInput."""

    def test_from_dict(self):
        """Test creating input from dict."""
        data = {
            "type": "string",
            "required": True,
            "description": "Test input",
        }

        inp = WorkflowInput.from_dict("param_name", data)

        assert inp.name == "param_name"
        assert inp.type == "string"
        assert inp.required is True
        assert inp.description == "Test input"

    def test_from_dict_with_default(self):
        """Test creating input with default value."""
        data = {
            "type": "number",
            "required": False,
            "default": 42,
        }

        inp = WorkflowInput.from_dict("count", data)

        assert inp.name == "count"
        assert inp.type == "number"
        assert inp.required is False
        assert inp.default == 42


class TestStepDefinition:
    """Tests for StepDefinition."""

    def test_agent_step_from_dict(self):
        """Test creating agent step from dict."""
        data = {
            "id": "explore_code",
            "type": "agent",
            "agent": "explore",
            "operation": "find_implementation",
            "inputs": {"feature": "auth"},
            "depends_on": ["step1"],
        }

        step = StepDefinition.from_dict(data)

        assert step.id == "explore_code"
        assert step.type == "agent"
        assert step.agent == "explore"
        assert step.operation == "find_implementation"
        assert step.inputs == {"feature": "auth"}
        assert step.depends_on == ["step1"]

    def test_get_all_step_ids(self):
        """Test getting all step IDs including nested."""
        data = {
            "id": "parent",
            "type": "conditional",
            "condition": "{{ true }}",
            "then": [
                {"id": "then_step", "type": "agent"}
            ],
            "else": [
                {"id": "else_step", "type": "agent"}
            ],
        }

        step = StepDefinition.from_dict(data)
        ids = step.get_all_step_ids()

        assert "parent" in ids
        assert "then_step" in ids
        assert "else_step" in ids


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition."""

    def test_from_yaml_simple(self):
        """Test parsing simple workflow from YAML."""
        yaml_str = """
workflow:
  name: "test-workflow"
  version: "1.0"
  description: "Test workflow"

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "test"
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)

        assert workflow.name == "test-workflow"
        assert workflow.version == "1.0"
        assert workflow.description == "Test workflow"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].id == "step1"

    def test_from_yaml_with_inputs(self):
        """Test parsing workflow with inputs."""
        yaml_str = """
workflow:
  name: "test"

  inputs:
    param1:
      type: string
      required: true
    param2:
      type: number
      required: false
      default: 42

  steps:
    - id: step1
      type: agent
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)

        assert len(workflow.inputs) == 2
        assert workflow.inputs["param1"].required is True
        assert workflow.inputs["param2"].default == 42

    def test_from_yaml_with_dependencies(self):
        """Test parsing workflow with step dependencies."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore

    - id: step2
      type: agent
      agent: explore
      operation: find_implementation
      depends_on: [step1]
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)

        assert len(workflow.steps) == 2
        assert workflow.steps[1].depends_on == ["step1"]

    def test_from_file(self):
        """Test loading workflow from file."""
        yaml_content = """
workflow:
  name: "file-workflow"
  version: "1.0"

  steps:
    - id: step1
      type: agent
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            workflow = WorkflowDefinition.from_file(temp_path)

            assert workflow.name == "file-workflow"
            assert len(workflow.steps) == 1
        finally:
            Path(temp_path).unlink()

    def test_from_file_not_found(self):
        """Test loading workflow from non-existent file."""
        with pytest.raises(FileNotFoundError):
            WorkflowDefinition.from_file("/nonexistent/file.yaml")

    def test_validate_success(self):
        """Test validating valid workflow."""
        yaml_str = """
workflow:
  name: "valid-workflow"

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        errors = workflow.validate()

        assert len(errors) == 0

    def test_validate_no_name(self):
        """Test validating workflow without name."""
        workflow = WorkflowDefinition(name="")

        errors = workflow.validate()

        assert any("name" in error.lower() for error in errors)

    def test_validate_no_steps(self):
        """Test validating workflow without steps."""
        workflow = WorkflowDefinition(name="test", steps=[])

        errors = workflow.validate()

        assert any("step" in error.lower() for error in errors)

    def test_validate_duplicate_step_ids(self):
        """Test validating workflow with duplicate step IDs."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore

    - id: step1
      type: agent
      agent: explore
      operation: explore
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        errors = workflow.validate()

        assert any("duplicate" in error.lower() for error in errors)

    def test_validate_unknown_dependency(self):
        """Test validating workflow with unknown dependency."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore
      depends_on: [unknown_step]
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        errors = workflow.validate()

        assert any("unknown step" in error.lower() for error in errors)

    def test_validate_invalid_step_type(self):
        """Test validating workflow with invalid step type."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: invalid_type
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        errors = workflow.validate()

        assert any("invalid type" in error.lower() for error in errors)

    def test_validate_agent_step_missing_agent(self):
        """Test validating agent step without agent field."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: agent
      operation: explore
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        errors = workflow.validate()

        assert any("agent" in error.lower() and "specify" in error.lower() for error in errors)

    def test_validate_agent_step_missing_operation(self):
        """Test validating agent step without operation field."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: agent
      agent: explore
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        errors = workflow.validate()

        assert any("operation" in error.lower() and "specify" in error.lower() for error in errors)

    def test_validate_transform_step_with_operation(self):
        """Test validating transform step with operation (no script required)."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: transform
      config:
        operation: aggregate
        function: sum
      inputs:
        items: [1, 2, 3]
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        errors = workflow.validate()

        # Should not have errors - operation is valid alternative to script
        assert len(errors) == 0

    def test_validate_transform_step_with_script(self):
        """Test validating transform step with script."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: transform
      script: "result = inputs['x'] * 2"
      inputs:
        x: 5
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        errors = workflow.validate()

        # Should not have errors - script is provided
        assert len(errors) == 0

    def test_validate_transform_step_missing_both(self):
        """Test validating transform step without script or operation."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: transform
      inputs:
        x: 5
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        errors = workflow.validate()

        # Should have error - needs either script or operation
        assert any("script" in error.lower() or "operation" in error.lower() for error in errors)

    def test_get_step(self):
        """Test getting step by ID."""
        yaml_str = """
workflow:
  name: "test"

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore

    - id: step2
      type: agent
      agent: explore
      operation: find_implementation
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)

        step1 = workflow.get_step("step1")
        step2 = workflow.get_step("step2")
        missing = workflow.get_step("missing")

        assert step1 is not None
        assert step1.id == "step1"
        assert step2 is not None
        assert step2.id == "step2"
        assert missing is None

    def test_to_dict(self):
        """Test converting workflow to dict."""
        yaml_str = """
workflow:
  name: "test"
  version: "1.0"
  description: "Test workflow"

  inputs:
    param1:
      type: string
      required: true

  steps:
    - id: step1
      type: agent
      agent: explore
      operation: explore
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        workflow_dict = workflow.to_dict()

        assert workflow_dict["name"] == "test"
        assert workflow_dict["version"] == "1.0"
        assert workflow_dict["description"] == "Test workflow"
        assert "param1" in workflow_dict["inputs"]
        assert len(workflow_dict["steps"]) == 1

    def test_repr(self):
        """Test string representation."""
        workflow = WorkflowDefinition(
            name="test-workflow",
            version="2.0",
            steps=[
                StepDefinition(id="step1", type="agent"),
                StepDefinition(id="step2", type="agent"),
            ],
        )

        repr_str = repr(workflow)

        assert "WorkflowDefinition" in repr_str
        assert "test-workflow" in repr_str
        assert "2.0" in repr_str
        assert "steps=2" in repr_str
