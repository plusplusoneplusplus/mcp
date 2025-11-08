"""Tests for Transform operations."""

import pytest
from plugins.automation.workflows.steps.operations.comparison import (
    ComparisonOperation,
    ConsensusVerificationOperation,
)
from plugins.automation.workflows.steps.operations.aggregation import (
    AggregateOperation,
)
from plugins.automation.workflows.steps.operations.filtering import FilterOperation
from plugins.automation.workflows.steps.operations.mapping import MapOperation


class TestComparisonOperation:
    """Test suite for ComparisonOperation."""

    def test_validate_success(self):
        """Test validation passes with sufficient inputs."""
        operation = ComparisonOperation(
            config={},
            inputs={
                "model_1_result": "test1",
                "model_2_result": "test2",
            },
        )
        assert operation.validate() is None

    def test_validate_insufficient_inputs(self):
        """Test validation fails with insufficient inputs."""
        operation = ComparisonOperation(
            config={},
            inputs={"model_1_result": "test1"},
        )
        error = operation.validate()
        assert error is not None
        assert "at least 2" in error

    def test_calculate_similarity_identical(self):
        """Test similarity calculation for identical texts."""
        operation = ComparisonOperation(config={}, inputs={})

        text = "The quick brown fox jumps over the lazy dog"
        similarity = operation._calculate_similarity(text, text)

        assert similarity == 1.0

    def test_calculate_similarity_different(self):
        """Test similarity calculation for different texts."""
        operation = ComparisonOperation(config={}, inputs={})

        text_a = "Machine learning algorithms"
        text_b = "Quantum physics equations"
        similarity = operation._calculate_similarity(text_a, text_b)

        assert similarity < 0.3

    def test_calculate_similarity_similar(self):
        """Test similarity calculation for similar texts."""
        operation = ComparisonOperation(config={}, inputs={})

        text_a = "Python is a high-level programming language"
        text_b = "Python is a high-level language for programming"
        similarity = operation._calculate_similarity(text_a, text_b)

        assert similarity > 0.7

    @pytest.mark.asyncio
    async def test_execute_two_models(self):
        """Test comparing two model results."""
        operation = ComparisonOperation(
            config={},
            inputs={
                "model_1_result": "Async/await is a way to write asynchronous code in Python",
                "model_2_result": "Async and await are keywords for asynchronous programming in Python",
                "threshold": 0.75,
            },
        )

        result = await operation.execute()

        assert "similarity_scores" in result
        assert "model_1_vs_model_2" in result["similarity_scores"]
        assert result["model_count"] == 2
        assert "average_similarity" in result
        assert "all_similar" in result
        assert "consensus" in result

    @pytest.mark.asyncio
    async def test_execute_three_models(self):
        """Test comparing three model results."""
        operation = ComparisonOperation(
            config={},
            inputs={
                "model_1_result": "Redis is an in-memory data store",
                "model_2_result": "Redis is a fast in-memory database",
                "model_3_result": "Redis stores data in memory for speed",
                "threshold": 0.70,
            },
        )

        result = await operation.execute()

        assert result["model_count"] == 3
        assert len(result["similarity_scores"]) == 3  # 3 pairs

    def test_build_consensus(self):
        """Test consensus building."""
        operation = ComparisonOperation(config={}, inputs={})

        # Strong consensus
        consensus = operation._build_consensus({}, {"pair1": 0.95})
        assert "Strong consensus" in consensus

        # Moderate consensus
        consensus = operation._build_consensus({}, {"pair1": 0.80})
        assert "Moderate consensus" in consensus

        # Weak consensus
        consensus = operation._build_consensus({}, {"pair1": 0.60})
        assert "Weak consensus" in consensus

        # No consensus
        consensus = operation._build_consensus({}, {"pair1": 0.30})
        assert "No consensus" in consensus


class TestConsensusVerificationOperation:
    """Test suite for ConsensusVerificationOperation."""

    def test_validate_success(self):
        """Test validation passes with comparison input."""
        operation = ConsensusVerificationOperation(
            config={},
            inputs={"comparison": {}, "threshold": 0.75},
        )
        assert operation.validate() is None

    def test_validate_missing_comparison(self):
        """Test validation fails without comparison input."""
        operation = ConsensusVerificationOperation(
            config={},
            inputs={"threshold": 0.75},
        )
        error = operation.validate()
        assert error is not None
        assert "comparison" in error

    @pytest.mark.asyncio
    async def test_execute_verified(self):
        """Test verification passes."""
        comparison_data = {
            "all_similar": True,
            "average_similarity": 0.85,
            "consensus": "Strong consensus",
        }

        operation = ConsensusVerificationOperation(
            config={},
            inputs={"comparison": comparison_data, "threshold": 0.75},
        )

        result = await operation.execute()

        assert result["verified"] is True
        assert result["passed_threshold"] is True

    @pytest.mark.asyncio
    async def test_execute_not_verified(self):
        """Test verification fails."""
        comparison_data = {
            "all_similar": False,
            "average_similarity": 0.55,
            "consensus": "Weak consensus",
        }

        operation = ConsensusVerificationOperation(
            config={},
            inputs={"comparison": comparison_data, "threshold": 0.75},
        )

        result = await operation.execute()

        assert result["verified"] is False
        assert result["passed_threshold"] is False


class TestAggregateOperation:
    """Test suite for AggregateOperation."""

    def test_validate_success(self):
        """Test validation passes with function."""
        operation = AggregateOperation(
            config={"function": "sum"},
            inputs={"items": [1, 2, 3]},
        )
        assert operation.validate() is None

    def test_validate_missing_function(self):
        """Test validation fails without function."""
        operation = AggregateOperation(config={}, inputs={})
        error = operation.validate()
        assert error is not None
        assert "function" in error

    @pytest.mark.asyncio
    async def test_sum(self):
        """Test sum aggregation."""
        operation = AggregateOperation(
            config={"function": "sum"},
            inputs={"items": [1, 2, 3, 4, 5]},
        )
        result = await operation.execute()
        assert result["result"] == 15

    @pytest.mark.asyncio
    async def test_avg(self):
        """Test average aggregation."""
        operation = AggregateOperation(
            config={"function": "avg"},
            inputs={"items": [2, 4, 6, 8]},
        )
        result = await operation.execute()
        assert result["result"] == 5.0

    @pytest.mark.asyncio
    async def test_count(self):
        """Test count aggregation."""
        operation = AggregateOperation(
            config={"function": "count"},
            inputs={"items": [1, 2, None, 3, None, 4]},
        )
        result = await operation.execute()
        assert result["result"] == 4  # Excludes None values

    @pytest.mark.asyncio
    async def test_min_max(self):
        """Test min/max aggregation."""
        items = [5, 2, 8, 1, 9]

        min_op = AggregateOperation(
            config={"function": "min"},
            inputs={"items": items},
        )
        min_result = await min_op.execute()
        assert min_result["result"] == 1

        max_op = AggregateOperation(
            config={"function": "max"},
            inputs={"items": items},
        )
        max_result = await max_op.execute()
        assert max_result["result"] == 9

    @pytest.mark.asyncio
    async def test_concat(self):
        """Test concatenation."""
        operation = AggregateOperation(
            config={"function": "concat", "separator": " | "},
            inputs={"items": ["foo", "bar", "baz"]},
        )
        result = await operation.execute()
        assert result["result"] == "foo | bar | baz"


class TestFilterOperation:
    """Test suite for FilterOperation."""

    def test_validate_success(self):
        """Test validation passes with condition."""
        operation = FilterOperation(
            config={"condition": "equals", "value": "test"},
            inputs={"items": []},
        )
        assert operation.validate() is None

    def test_validate_missing_condition(self):
        """Test validation fails without condition."""
        operation = FilterOperation(config={}, inputs={})
        error = operation.validate()
        assert error is not None
        assert "condition" in error

    @pytest.mark.asyncio
    async def test_filter_equals(self):
        """Test equals filter."""
        operation = FilterOperation(
            config={"condition": "equals", "value": "active"},
            inputs={"items": ["active", "inactive", "active", "pending"]},
        )
        result = await operation.execute()
        assert result["kept_count"] == 2
        assert result["filtered_items"] == ["active", "active"]

    @pytest.mark.asyncio
    async def test_filter_contains(self):
        """Test contains filter."""
        operation = FilterOperation(
            config={"condition": "contains", "value": "error"},
            inputs={"items": ["error: failed", "success", "warning: error found"]},
        )
        result = await operation.execute()
        assert result["kept_count"] == 2

    @pytest.mark.asyncio
    async def test_filter_greater_than(self):
        """Test greater than filter."""
        operation = FilterOperation(
            config={"condition": "greater_than", "value": "5"},
            inputs={"items": [3, 7, 4, 9, 2]},
        )
        result = await operation.execute()
        assert result["filtered_items"] == [7, 9]


class TestMapOperation:
    """Test suite for MapOperation."""

    def test_validate_success(self):
        """Test validation passes with function."""
        operation = MapOperation(
            config={"function": "extract"},
            inputs={"items": []},
        )
        assert operation.validate() is None

    def test_validate_missing_function(self):
        """Test validation fails without function."""
        operation = MapOperation(config={}, inputs={})
        error = operation.validate()
        assert error is not None
        assert "function" in error

    @pytest.mark.asyncio
    async def test_extract_single_field(self):
        """Test extracting single field."""
        operation = MapOperation(
            config={"function": "extract", "fields": "name"},
            inputs={
                "items": [
                    {"name": "Alice", "age": 30},
                    {"name": "Bob", "age": 25},
                ]
            },
        )
        result = await operation.execute()
        assert result["mapped_items"] == ["Alice", "Bob"]

    @pytest.mark.asyncio
    async def test_extract_multiple_fields(self):
        """Test extracting multiple fields."""
        operation = MapOperation(
            config={"function": "extract", "fields": ["name", "age"]},
            inputs={
                "items": [
                    {"name": "Alice", "age": 30, "city": "NYC"},
                    {"name": "Bob", "age": 25, "city": "SF"},
                ]
            },
        )
        result = await operation.execute()
        assert len(result["mapped_items"]) == 2
        assert result["mapped_items"][0] == {"name": "Alice", "age": 30}

    @pytest.mark.asyncio
    async def test_project(self):
        """Test projection."""
        operation = MapOperation(
            config={
                "function": "project",
                "projection": {"fullname": "name", "years": "age"},
            },
            inputs={
                "items": [
                    {"name": "Alice", "age": 30},
                    {"name": "Bob", "age": 25},
                ]
            },
        )
        result = await operation.execute()
        assert result["mapped_items"][0] == {"fullname": "Alice", "years": 30}

    @pytest.mark.asyncio
    async def test_compute(self):
        """Test compute operation."""
        operation = MapOperation(
            config={
                "function": "compute",
                "expression": "item['age'] * 2",
                "output_field": "double_age",
            },
            inputs={
                "items": [
                    {"name": "Alice", "age": 30},
                    {"name": "Bob", "age": 25},
                ]
            },
        )
        result = await operation.execute()
        assert result["mapped_items"][0]["double_age"] == 60
        assert result["mapped_items"][1]["double_age"] == 50
