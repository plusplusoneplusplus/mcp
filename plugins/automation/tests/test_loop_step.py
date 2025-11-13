"""Tests for Loop Step."""

import pytest
from plugins.automation.workflows.engine import WorkflowEngine
from plugins.automation.workflows.definition import WorkflowDefinition


class TestLoopStep:
    """Tests for loop step functionality."""

    @pytest.mark.asyncio
    async def test_loop_basic(self):
        """Test basic loop execution."""
        yaml_str = """
workflow:
  name: test-loop

  inputs:
    numbers:
      type: array
      required: true

  steps:
    - id: process_numbers
      type: loop
      items: "{{ inputs.numbers }}"
      item_var: num
      steps:
        - id: double
          type: transform
          config:
            operation: aggregate
            function: sum
          inputs:
            items: ["{{ num }}", "{{ num }}"]
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        result = await engine.execute(workflow, {"numbers": [1, 2, 3]})

        assert result.status.value == "completed"
        assert "process_numbers" in result.step_results

        loop_result = result.step_results["process_numbers"].result
        assert loop_result["iterations"] == 3
        assert loop_result["successful"] == 3
        assert loop_result["failed"] == 0

    @pytest.mark.asyncio
    async def test_loop_empty_list(self):
        """Test loop with empty list."""
        yaml_str = """
workflow:
  name: test-loop-empty

  inputs:
    items:
      type: array
      required: true

  steps:
    - id: process_items
      type: loop
      items: "{{ inputs.items }}"
      item_var: item
      steps:
        - id: noop
          type: transform
          config:
            operation: aggregate
            function: count
          inputs:
            items: ["{{ item }}"]
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        result = await engine.execute(workflow, {"items": []})

        assert result.status.value == "completed"
        loop_result = result.step_results["process_items"].result
        assert loop_result["iterations"] == 0
        assert loop_result["successful"] == 0

    @pytest.mark.asyncio
    async def test_loop_with_error_continue(self):
        """Test loop with error handling (continue)."""
        yaml_str = """
workflow:
  name: test-loop-error

  inputs:
    items:
      type: array
      required: true

  steps:
    - id: process_items
      type: loop
      items: "{{ inputs.items }}"
      item_var: item
      steps:
        - id: divide
          type: transform
          script: "result = 10 / int(inputs.get('item', 0))"
          inputs:
            item: "{{ item }}"
          on_error: continue
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        # Include 0 which will cause division by zero
        result = await engine.execute(workflow, {"items": [2, 0, 5]})

        # Loop should complete despite one failure
        assert result.status.value in ["completed", "partial"]
        loop_result = result.step_results["process_items"].result
        assert loop_result["iterations"] == 3
        # At least 2 should succeed (2 and 5)
        assert loop_result["successful"] >= 2

    @pytest.mark.asyncio
    async def test_loop_nested(self):
        """Test nested loops."""
        yaml_str = """
workflow:
  name: test-nested-loop

  inputs:
    matrix:
      type: array
      required: true

  steps:
    - id: outer_loop
      type: loop
      items: "{{ inputs.matrix }}"
      item_var: row
      steps:
        - id: inner_loop
          type: loop
          items: "{{ row }}"
          item_var: cell
          steps:
            - id: process_cell
              type: transform
              config:
                operation: aggregate
                function: sum
              inputs:
                items: ["{{ cell }}"]
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        result = await engine.execute(workflow, {
            "matrix": [[1, 2], [3, 4], [5, 6]]
        })

        assert result.status.value == "completed"
        loop_result = result.step_results["outer_loop"].result
        assert loop_result["iterations"] == 3  # 3 rows
        assert loop_result["successful"] == 3

    @pytest.mark.asyncio
    async def test_loop_with_dict_items(self):
        """Test loop with dictionary items."""
        yaml_str = """
workflow:
  name: test-loop-dict

  inputs:
    tasks:
      type: array
      required: true

  steps:
    - id: process_tasks
      type: loop
      items: "{{ inputs.tasks }}"
      item_var: task
      steps:
        - id: get_items
          type: transform
          config:
            operation: aggregate
            function: count
          inputs:
            items: "{{ task.items }}"
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        result = await engine.execute(workflow, {
            "tasks": [
                {"items": [1, 2, 3]},
                {"items": [4, 5]},
                {"items": [6, 7, 8, 9]}
            ]
        })

        assert result.status.value == "completed"
        loop_result = result.step_results["process_tasks"].result
        assert loop_result["iterations"] == 3
        assert loop_result["successful"] == 3

    @pytest.mark.asyncio
    async def test_loop_validation_missing_items(self):
        """Test loop validation fails without items."""
        yaml_str = """
workflow:
  name: test-loop-invalid

  steps:
    - id: bad_loop
      type: loop
      item_var: item
      steps:
        - id: noop
          type: transform
          script: "result = 1"
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)

        # Should fail validation
        errors = workflow.validate()
        assert any("items" in error.lower() for error in errors)

    @pytest.mark.asyncio
    async def test_loop_validation_missing_steps(self):
        """Test loop validation fails without child steps."""
        yaml_str = """
workflow:
  name: test-loop-invalid

  steps:
    - id: bad_loop
      type: loop
      items: "{{ inputs.data }}"
      item_var: item
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)

        # Should fail validation
        errors = workflow.validate()
        assert any("at least one substep" in error.lower() for error in errors)

    @pytest.mark.asyncio
    async def test_loop_item_variable_scoping(self):
        """Test that loop item variable doesn't leak between iterations."""
        yaml_str = """
workflow:
  name: test-loop-scoping

  inputs:
    values:
      type: array
      required: true

  steps:
    - id: first_loop
      type: loop
      items: "{{ inputs.values }}"
      item_var: val
      steps:
        - id: store_val
          type: transform
          script: "result = inputs['val'] * 2"
          inputs:
            val: "{{ val }}"

    - id: second_loop
      type: loop
      depends_on: [first_loop]
      items: "{{ inputs.values }}"
      item_var: val
      steps:
        - id: use_val
          type: transform
          script: "result = inputs['val'] * 3"
          inputs:
            val: "{{ val }}"
"""

        workflow = WorkflowDefinition.from_yaml(yaml_str)
        engine = WorkflowEngine()

        result = await engine.execute(workflow, {"values": [1, 2, 3]})

        assert result.status.value == "completed"
        # Both loops should complete successfully
        assert result.step_results["first_loop"].result["successful"] == 3
        assert result.step_results["second_loop"].result["successful"] == 3


class TestLoopStepIntegration:
    """Integration tests for loop step in complete workflows."""
    pass
