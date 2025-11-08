"""Tests for TransformStep implementation."""

import pytest
from plugins.automation.workflows.steps.transform_step import TransformStep
from plugins.automation.workflows.definition import StepDefinition
from plugins.automation.workflows import WorkflowContext


class TestTransformStep:
    """Test suite for TransformStep."""

    def test_init(self):
        """Test TransformStep initialization."""
        step_def = StepDefinition(
            id="test_transform",
            type="transform",
            config={"operation": "compare_results"},
            inputs={"model_1_result": "test1", "model_2_result": "test2"},
        )
        step = TransformStep(step_def)

        assert step.step_id == "test_transform"
        assert step.definition.type == "transform"
        assert step.definition.config["operation"] == "compare_results"

    def test_validate_compare_results_success(self):
        """Test validation passes with sufficient model results."""
        step_def = StepDefinition(
            id="test_transform",
            type="transform",
            config={"operation": "compare_results"},
            inputs={"model_1_result": "test1", "model_2_result": "test2"},
        )
        # Should not raise during initialization
        step = TransformStep(step_def)
        assert step.step_id == "test_transform"

    def test_validate_compare_results_insufficient_inputs(self):
        """Test validation fails with insufficient model results."""
        step_def = StepDefinition(
            id="test_transform",
            type="transform",
            config={"operation": "compare_results"},
            inputs={"model_1_result": "test1"},  # Only one model
        )

        # Should raise during initialization
        with pytest.raises(ValueError, match="at least 2"):
            step = TransformStep(step_def)

    def test_validate_verify_consensus_missing_comparison(self):
        """Test validation fails when comparison input is missing."""
        step_def = StepDefinition(
            id="test_transform",
            type="transform",
            config={"operation": "verify_consensus"},
            inputs={"threshold": 0.75},  # Missing comparison
        )

        # Should raise during initialization
        with pytest.raises(ValueError, match="requires 'comparison' input"):
            step = TransformStep(step_def)

    @pytest.mark.asyncio
    async def test_aggregate_operation(self):
        """Test aggregate operation through TransformStep."""
        step_def = StepDefinition(
            id="aggregate",
            type="transform",
            config={"operation": "aggregate", "function": "sum"},
            inputs={"items": [1, 2, 3, 4, 5]},
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert result["function"] == "sum"
        assert result["result"] == 15

    @pytest.mark.asyncio
    async def test_filter_operation(self):
        """Test filter operation through TransformStep."""
        step_def = StepDefinition(
            id="filter",
            type="transform",
            config={
                "operation": "filter",
                "condition": "greater_than",
                "value": "5",
            },
            inputs={"items": [3, 7, 4, 9, 2]},
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert result["kept_count"] == 2
        assert 7 in result["filtered_items"]
        assert 9 in result["filtered_items"]

    @pytest.mark.asyncio
    async def test_map_operation(self):
        """Test map operation through TransformStep."""
        step_def = StepDefinition(
            id="map",
            type="transform",
            config={"operation": "map", "function": "extract", "fields": "name"},
            inputs={
                "items": [
                    {"name": "Alice", "age": 30},
                    {"name": "Bob", "age": 25},
                ]
            },
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert result["mapped_items"] == ["Alice", "Bob"]

    @pytest.mark.asyncio
    async def test_compare_results_two_models(self):
        """Test comparing results from two models."""
        step_def = StepDefinition(
            id="compare",
            type="transform",
            config={"operation": "compare_results"},
            inputs={
                "model_1_result": "Async/await is a way to write asynchronous code in Python",
                "model_2_result": "Async and await are keywords for asynchronous programming in Python",
                "threshold": 0.75,
            },
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert "similarity_scores" in result
        assert "model_1_vs_model_2" in result["similarity_scores"]
        assert result["model_count"] == 2
        assert "average_similarity" in result
        assert "all_similar" in result
        assert "consensus" in result

    @pytest.mark.asyncio
    async def test_compare_results_three_models(self):
        """Test comparing results from three models."""
        step_def = StepDefinition(
            id="compare",
            type="transform",
            config={"operation": "compare_results"},
            inputs={
                "model_1_result": "Redis is an in-memory data store",
                "model_2_result": "Redis is a fast in-memory database",
                "model_3_result": "Redis stores data in memory for speed",
                "threshold": 0.70,
            },
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert result["model_count"] == 3
        assert "model_1_vs_model_2" in result["similarity_scores"]
        assert "model_1_vs_model_3" in result["similarity_scores"]
        assert "model_2_vs_model_3" in result["similarity_scores"]
        assert len(result["similarity_scores"]) == 3  # 3 pairs for 3 models

    @pytest.mark.asyncio
    async def test_compare_results_high_similarity(self):
        """Test comparison with high similarity."""
        step_def = StepDefinition(
            id="compare",
            type="transform",
            config={"operation": "compare_results"},
            inputs={
                "model_1_result": "The capital of France is Paris",
                "model_2_result": "Paris is the capital of France",
                "threshold": 0.75,
            },
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert result["average_similarity"] > 0.75
        assert result["all_similar"] is True
        assert "Strong consensus" in result["consensus"] or "Moderate consensus" in result["consensus"]

    @pytest.mark.asyncio
    async def test_compare_results_low_similarity(self):
        """Test comparison with low similarity."""
        step_def = StepDefinition(
            id="compare",
            type="transform",
            config={"operation": "compare_results"},
            inputs={
                "model_1_result": "Machine learning is a subset of artificial intelligence focused on learning from data",
                "model_2_result": "Quantum computing uses quantum mechanics for computation",
                "threshold": 0.75,
            },
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert result["average_similarity"] < 0.75
        assert result["all_similar"] is False
        assert "No consensus" in result["consensus"] or "Weak consensus" in result["consensus"]

    @pytest.mark.asyncio
    async def test_compare_results_includes_differences(self):
        """Test that comparison includes difference analysis."""
        step_def = StepDefinition(
            id="compare",
            type="transform",
            config={"operation": "compare_results"},
            inputs={
                "model_1_result": "Docker containers are lightweight virtualization",
                "model_2_result": "Kubernetes orchestrates containerized applications",
                "threshold": 0.70,
            },
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert "differences" in result
        assert "unique_words_per_model" in result["differences"]
        assert "text_lengths" in result["differences"]
        assert "length_variance" in result["differences"]

    @pytest.mark.asyncio
    async def test_verify_consensus_passes(self):
        """Test consensus verification when threshold is met."""
        comparison_data = {
            "all_similar": True,
            "average_similarity": 0.85,
            "consensus": "Strong consensus: All models produced highly similar results",
        }

        step_def = StepDefinition(
            id="verify",
            type="transform",
            config={"operation": "verify_consensus"},
            inputs={"comparison": comparison_data, "threshold": 0.75},
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert result["verified"] is True
        assert result["passed_threshold"] is True
        assert "reliable" in result["recommendation"].lower()

    @pytest.mark.asyncio
    async def test_verify_consensus_fails(self):
        """Test consensus verification when threshold is not met."""
        comparison_data = {
            "all_similar": False,
            "average_similarity": 0.55,
            "consensus": "Weak consensus: Models show some agreement but notable differences",
        }

        step_def = StepDefinition(
            id="verify",
            type="transform",
            config={"operation": "verify_consensus"},
            inputs={"comparison": comparison_data, "threshold": 0.75},
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert result["verified"] is False
        assert result["passed_threshold"] is False
        assert "disagree" in result["recommendation"].lower() or "review" in result["recommendation"].lower()

    @pytest.mark.asyncio
    async def test_verify_consensus_no_data(self):
        """Test consensus verification with no comparison data."""
        step_def = StepDefinition(
            id="verify",
            type="transform",
            config={"operation": "verify_consensus"},
            inputs={"comparison": None, "threshold": 0.75},
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert result["verified"] is False
        assert "No comparison data available" in result["reason"]

    @pytest.mark.asyncio
    async def test_custom_transform(self):
        """Test custom transform operation (pass-through for unknown operations)."""
        step_def = StepDefinition(
            id="custom",
            type="transform",
            config={"operation": "transform"},
            inputs={"data": "test_data", "value": 123},
        )
        step = TransformStep(step_def)
        context = WorkflowContext(inputs={})

        step_result = await step.execute(context)
        result = step_result.result

        assert result["transformed"] is True
        assert result["inputs"]["data"] == "test_data"
        assert result["inputs"]["value"] == 123

    def test_unknown_operation_raises_error(self):
        """Test that unknown operations raise an error."""
        step_def = StepDefinition(
            id="unknown",
            type="transform",
            config={"operation": "unknown_operation"},
            inputs={},
        )

        with pytest.raises(ValueError, match="Unknown operation"):
            step = TransformStep(step_def)

    @pytest.mark.asyncio
    async def test_chained_operations(self):
        """Test using multiple transform steps in sequence."""
        # First step: aggregate
        aggregate_def = StepDefinition(
            id="aggregate",
            type="transform",
            config={"operation": "aggregate", "function": "count"},
            inputs={"items": ["a", "b", "c", "d", "e"]},
        )
        aggregate_step = TransformStep(aggregate_def)
        context = WorkflowContext(inputs={})

        aggregate_result = await aggregate_step.execute(context)
        context.set_step_result("aggregate", aggregate_result)

        # Second step: use aggregated result
        # In a real workflow, this would use template resolution
        # For now, just verify the result is available
        assert aggregate_result.result["result"] == 5
