"""Tests for the RestrictedPythonEvaluator class."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from ..evaluator import RestrictedPythonEvaluator, EvaluationError, EvaluationResult


class TestRestrictedPythonEvaluator:
    """Test cases for RestrictedPythonEvaluator."""

    @pytest.fixture
    def evaluator(self):
        """Create an evaluator instance for testing."""
        return RestrictedPythonEvaluator()

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            'id': range(1, 101),
            'name': [f'User_{i}' for i in range(1, 101)],
            'age': range(20, 120),
            'status': ['active' if i % 2 == 0 else 'inactive' for i in range(1, 101)],
            'score': np.linspace(85.5, 135.0, 100)
        })

    # Basic functionality tests

    def test_evaluator_initialization(self, evaluator):
        """Test that evaluator initializes correctly."""
        assert evaluator is not None
        assert hasattr(evaluator, '_logger')

    def test_simple_expression_evaluation(self, evaluator):
        """Test evaluation of simple mathematical expressions."""
        result = evaluator.evaluate_expression("2 + 2")

        assert result.success is True
        assert result.result == 4
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_expression_with_context(self, evaluator):
        """Test evaluation with custom context variables."""
        context = {'x': 10, 'y': 20}
        result = evaluator.evaluate_expression("x + y", context)

        assert result.success is True
        assert result.result == 30
        assert result.execution_time_ms > 0
        assert result.error_message is None

    # DataFrame operation tests

    def test_dataframe_head_operation(self, evaluator, sample_dataframe):
        """Test DataFrame head operation."""
        result = evaluator.evaluate_dataframe_expression("df.head(5)", sample_dataframe)

        assert result.success is True
        assert isinstance(result.result, pd.DataFrame)
        assert len(result.result) == 5
        assert list(result.result.columns) == ['id', 'name', 'age', 'status', 'score']
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_dataframe_tail_operation(self, evaluator, sample_dataframe):
        """Test DataFrame tail operation."""
        result = evaluator.evaluate_dataframe_expression("df.tail(3)", sample_dataframe)

        assert result.success is True
        assert isinstance(result.result, pd.DataFrame)
        assert len(result.result) == 3
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_dataframe_describe_operation(self, evaluator, sample_dataframe):
        """Test DataFrame describe operation."""
        result = evaluator.evaluate_dataframe_expression("df.describe()", sample_dataframe)

        assert result.success is True
        assert isinstance(result.result, pd.DataFrame)
        assert 'count' in result.result.index
        assert 'mean' in result.result.index
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_dataframe_query_operation(self, evaluator, sample_dataframe):
        """Test DataFrame query operation."""
        result = evaluator.evaluate_dataframe_expression("df.query('age > 50')", sample_dataframe)

        assert result.success is True
        assert isinstance(result.result, pd.DataFrame)
        assert len(result.result) > 0
        assert all(result.result['age'] > 50)
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_dataframe_column_access(self, evaluator, sample_dataframe):
        """Test accessing DataFrame columns."""
        result = evaluator.evaluate_dataframe_expression("df['age']", sample_dataframe)

        assert result.success is True
        assert isinstance(result.result, pd.Series)
        assert len(result.result) == 100
        assert result.result.name == 'age'
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_dataframe_series_to_frame(self, evaluator, sample_dataframe):
        """Test converting Series result to DataFrame."""
        result = evaluator.evaluate_dataframe_expression("df['name'].head(5)", sample_dataframe)

        assert result.success is True
        assert isinstance(result.result, pd.Series)
        assert len(result.result) == 5
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_dataframe_aggregation_operations(self, evaluator, sample_dataframe):
        """Test DataFrame aggregation operations."""
        result = evaluator.evaluate_dataframe_expression("df['age'].mean()", sample_dataframe)

        assert result.success is True
        assert isinstance(result.result, (int, float, np.number))
        assert result.result > 0
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_dataframe_with_pandas_functions(self, evaluator, sample_dataframe):
        """Test using pandas functions in expressions."""
        result = evaluator.evaluate_dataframe_expression("pd.concat([df.head(2), df.tail(2)])", sample_dataframe)

        assert result.success is True
        assert isinstance(result.result, pd.DataFrame)
        assert len(result.result) == 4
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_dataframe_without_pandas_module(self, evaluator, sample_dataframe):
        """Test DataFrame operations without pandas module in context."""
        result = evaluator.evaluate_dataframe_expression("df.shape[0]", sample_dataframe, include_pandas=False)

        assert result.success is True
        assert result.result == 100
        assert result.execution_time_ms > 0
        assert result.error_message is None

    # Built-in function tests

    def test_builtin_functions_len(self, evaluator, sample_dataframe):
        """Test len() built-in function."""
        result = evaluator.evaluate_dataframe_expression("len(df)", sample_dataframe)

        assert result.success is True
        assert result.result == 100
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_builtin_functions_max_min(self, evaluator, sample_dataframe):
        """Test max() and min() built-in functions."""
        result = evaluator.evaluate_dataframe_expression("max(df['age'])", sample_dataframe)

        assert result.success is True
        assert result.result == 119
        assert result.execution_time_ms > 0
        assert result.error_message is None

        result = evaluator.evaluate_dataframe_expression("min(df['age'])", sample_dataframe)

        assert result.success is True
        assert result.result == 20
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_builtin_functions_sum(self, evaluator, sample_dataframe):
        """Test sum() built-in function."""
        result = evaluator.evaluate_dataframe_expression("sum(df['id'])", sample_dataframe)

        assert result.success is True
        assert result.result == sum(range(1, 101))
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_builtin_functions_round(self, evaluator, sample_dataframe):
        """Test round() built-in function."""
        result = evaluator.evaluate_dataframe_expression("round(df['score'].mean(), 2)", sample_dataframe)

        assert result.success is True
        assert isinstance(result.result, float)
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_builtin_type_constructors(self, evaluator):
        """Test built-in type constructors."""
        # Test list
        result = evaluator.evaluate_expression("list(range(5))")
        assert result.success is True
        assert result.result == [0, 1, 2, 3, 4]

        # Test dict
        result = evaluator.evaluate_expression("dict(a=1, b=2)")
        assert result.success is True
        assert result.result == {'a': 1, 'b': 2}

        # Test tuple
        result = evaluator.evaluate_expression("tuple([1, 2, 3])")
        assert result.success is True
        assert result.result == (1, 2, 3)

        # Test set
        result = evaluator.evaluate_expression("set([1, 2, 2, 3])")
        assert result.success is True
        assert result.result == {1, 2, 3}

    # Error handling tests

    def test_syntax_error_handling(self, evaluator, sample_dataframe):
        """Test handling of syntax errors."""
        result = evaluator.evaluate_dataframe_expression("df.head(", sample_dataframe)

        assert result.success is False
        assert result.result is None
        assert "Invalid expression syntax" in result.error_message
        assert result.execution_time_ms == 0

    def test_runtime_error_handling(self, evaluator, sample_dataframe):
        """Test handling of runtime errors."""
        result = evaluator.evaluate_dataframe_expression("df['nonexistent_column']", sample_dataframe)

        assert result.success is False
        assert result.result is None
        assert "Error executing expression" in result.error_message
        assert result.execution_time_ms == 0

    def test_empty_expression(self, evaluator):
        """Test handling of empty expressions."""
        result = evaluator.evaluate_expression("")

        assert result.success is False
        assert result.result is None
        assert "Invalid expression syntax" in result.error_message
        assert result.execution_time_ms == 0

    def test_none_expression(self, evaluator):
        """Test handling of None as expression."""
        result = evaluator.evaluate_expression("None")

        assert result.success is False
        assert result.result is None
        assert "Expression did not produce a result" in result.error_message

    def test_invalid_variable_access(self, evaluator):
        """Test that accessing undefined variables fails safely."""
        result = evaluator.evaluate_expression("undefined_variable")

        assert result.success is False
        assert result.result is None
        assert "Error executing expression" in result.error_message
        assert result.execution_time_ms == 0

    # Security tests

    def test_restricted_import_access(self, evaluator):
        """Test that import statements are restricted."""
        result = evaluator.evaluate_expression("import os")

        assert result.success is False
        assert result.result is None
        assert "Invalid expression syntax" in result.error_message

    def test_restricted_exec_access(self, evaluator):
        """Test that exec() is not available."""
        result = evaluator.evaluate_expression("exec('print(\"hello\")')")

        assert result.success is False
        assert result.result is None
        assert "Invalid expression syntax" in result.error_message
        assert "Exec calls are not allowed" in result.error_message

    def test_restricted_eval_access(self, evaluator):
        """Test that eval() is not available."""
        result = evaluator.evaluate_expression("eval('2 + 2')")

        assert result.success is False
        assert result.result is None
        assert "Invalid expression syntax" in result.error_message
        assert "Eval calls are not allowed" in result.error_message

    def test_restricted_file_access(self, evaluator):
        """Test that file operations are restricted."""
        result = evaluator.evaluate_expression("open('/etc/passwd', 'r')")

        assert result.success is False
        assert result.result is None
        assert "Error executing expression" in result.error_message

    def test_restricted_dangerous_functions(self, evaluator):
        """Test that dangerous functions are not available."""
        dangerous_expressions = [
            "__import__('os')",
            "globals()",
            "locals()",
            "dir()",
            "hasattr(object, '__class__')",
        ]

        for expr in dangerous_expressions:
            result = evaluator.evaluate_expression(expr)
            assert result.success is False, f"Expression '{expr}' should fail but succeeded"
            assert result.result is None
            assert result.error_message is not None

    # Edge cases and special scenarios

    def test_large_result_handling(self, evaluator):
        """Test handling of large results."""
        # Create a large DataFrame
        large_df = pd.DataFrame({
            'col1': range(10000),
            'col2': range(10000, 20000)
        })

        result = evaluator.evaluate_dataframe_expression("df.shape", large_df)

        assert result.success is True
        assert result.result == (10000, 2)
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_empty_dataframe_operations(self, evaluator):
        """Test operations on empty DataFrames."""
        empty_df = pd.DataFrame()

        result = evaluator.evaluate_dataframe_expression("len(df)", empty_df)

        assert result.success is True
        assert result.result == 0
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_complex_pandas_operations(self, evaluator, sample_dataframe):
        """Test complex pandas operations."""
        complex_expr = "df.groupby('status')['age'].mean().sort_values(ascending=False)"
        result = evaluator.evaluate_dataframe_expression(complex_expr, sample_dataframe)

        assert result.success is True
        assert isinstance(result.result, pd.Series)
        assert len(result.result) == 2  # active and inactive
        assert result.execution_time_ms > 0
        assert result.error_message is None

    def test_multiple_operations_chaining(self, evaluator, sample_dataframe):
        """Test chaining multiple operations."""
        chained_expr = "df.query('age > 50').head(10).shape[0]"
        result = evaluator.evaluate_dataframe_expression(chained_expr, sample_dataframe)

        assert result.success is True
        assert isinstance(result.result, (int, np.integer))
        assert result.result <= 10  # Should be at most 10 due to head(10)
        assert result.execution_time_ms > 0
        assert result.error_message is None

    # Performance and logging tests

    def test_execution_time_measurement(self, evaluator, sample_dataframe):
        """Test that execution time is properly measured."""
        result = evaluator.evaluate_dataframe_expression("df.describe()", sample_dataframe)

        assert result.success is True
        assert result.execution_time_ms > 0
        assert isinstance(result.execution_time_ms, float)

    @patch('utils.pyeval.evaluator.logger')
    def test_debug_logging(self, mock_logger, evaluator, sample_dataframe):
        """Test that debug logging works correctly."""
        mock_child_logger = MagicMock()
        mock_logger.getChild.return_value = mock_child_logger

        evaluator = RestrictedPythonEvaluator()  # Reinitialize to pick up mock
        result = evaluator.evaluate_dataframe_expression("df.head(5)", sample_dataframe)

        assert result.success is True
        # Verify logger was accessed
        mock_logger.getChild.assert_called()

    @patch('utils.pyeval.evaluator.logger')
    def test_error_logging(self, mock_logger, evaluator, sample_dataframe):
        """Test that error logging works correctly."""
        mock_child_logger = MagicMock()
        mock_logger.getChild.return_value = mock_child_logger

        evaluator = RestrictedPythonEvaluator()  # Reinitialize to pick up mock
        result = evaluator.evaluate_dataframe_expression("invalid syntax (", sample_dataframe)

        assert result.success is False
        # Verify logger was accessed
        mock_logger.getChild.assert_called()

    # Context and environment tests

    def test_custom_context_override(self, evaluator):
        """Test that custom context can override default variables."""
        # Create custom context that shadows built-in
        custom_context = {'len': lambda x: 42}
        result = evaluator.evaluate_expression("len([1, 2, 3])", custom_context)

        assert result.success is True
        assert result.result == 42  # Should use our custom len function

    def test_context_isolation(self, evaluator):
        """Test that context variables don't leak between evaluations."""
        # First evaluation with custom context
        result1 = evaluator.evaluate_expression("x + y", {'x': 10, 'y': 20})
        assert result1.success is True
        assert result1.result == 30

        # Second evaluation without context should fail
        result2 = evaluator.evaluate_expression("x + y")
        assert result2.success is False
        assert "Error executing expression" in result2.error_message

    def test_dataframe_context_parameter(self, evaluator, sample_dataframe):
        """Test that DataFrame context parameter works correctly."""
        # Test with explicit DataFrame context
        context = {'df': sample_dataframe, 'pd': pd}
        result = evaluator.evaluate_expression("df.shape[0]", context)

        assert result.success is True
        assert result.result == 100

        # Compare with convenience method
        result2 = evaluator.evaluate_dataframe_expression("df.shape[0]", sample_dataframe)

        assert result2.success is True
        assert result2.result == result.result
