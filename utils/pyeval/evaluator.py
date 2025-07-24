"""Restricted Python expression evaluator for secure code execution.

This module provides a secure way to evaluate Python expressions using RestrictedPython,
specifically designed for DataFrame operations and similar use cases where user-provided
code needs to be executed safely.
"""

import logging
import time
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass

import pandas as pd
from RestrictedPython import compile_restricted_exec, safe_globals, limited_builtins
from RestrictedPython.Guards import safer_getattr, guarded_setattr

logger = logging.getLogger(__name__)


class EvaluationError(Exception):
    """Exception raised when expression evaluation fails."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


@dataclass
class EvaluationResult:
    """Result of a restricted Python expression evaluation."""

    result: Any
    execution_time_ms: float
    success: bool
    error_message: Optional[str] = None


class RestrictedPythonEvaluator:
    """Secure Python expression evaluator using RestrictedPython.

    This class provides a safe way to evaluate Python expressions in a restricted
    environment with access to pandas DataFrames and common built-in functions.
    """

    def __init__(self):
        """Initialize the evaluator."""
        self._logger = logger.getChild(self.__class__.__name__)

    def _create_safe_builtins(self) -> Dict[str, Any]:
        """Create a dictionary of safe built-in functions for expression evaluation.

        Returns:
            Dictionary containing safe built-in functions.
        """
        safe_builtins = limited_builtins.copy()
        safe_builtins.update({
            # Mathematical functions
            'len': len,
            'max': max,
            'min': min,
            'sum': sum,
            'abs': abs,
            'round': round,

            # Collection functions
            'sorted': sorted,
            'enumerate': enumerate,
            'zip': zip,
            'range': range,

            # Type constructors
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
        })
        return safe_builtins

    def _create_safe_getitem(self) -> callable:
        """Create a safe getitem function for accessing DataFrame columns and Series values.

        Returns:
            Safe getitem function for pandas objects.
        """
        def safe_getitem(obj: Any, key: Any) -> Any:
            """Safe item access for pandas DataFrames and Series.

            Args:
                obj: Object to access (typically DataFrame or Series)
                key: Key to access (column name, index, etc.)

            Returns:
                The accessed value.

            Raises:
                KeyError: If key doesn't exist
                TypeError: If object doesn't support item access
            """
            try:
                return obj[key]
            except Exception as e:
                self._logger.warning(f"Safe getitem failed for key '{key}': {e}")
                raise

        return safe_getitem

    def _create_restricted_globals(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create the restricted globals dictionary for expression evaluation.

        Args:
            context: Additional context variables to include in the evaluation environment.

        Returns:
            Dictionary containing the restricted execution environment.
        """
        restricted_globals = safe_globals.copy()

        restricted_globals.update({
            '__builtins__': self._create_safe_builtins(),
            '_getattr_': safer_getattr,
            '_setattr_': guarded_setattr,
            '_getitem_': self._create_safe_getitem(),
        })

        # Add user-provided context
        restricted_globals.update(context)

        return restricted_globals

    def evaluate_expression(
        self,
        expression: str,
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """Evaluate a Python expression in a restricted environment.

        Args:
            expression: The Python expression to evaluate.
            context: Optional dictionary of variables to make available in the expression.
                    Common keys include 'df' for DataFrames and 'pd' for pandas.

        Returns:
            EvaluationResult containing the result, execution time, and success status.

        Example:
            >>> evaluator = RestrictedPythonEvaluator()
            >>> df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
            >>> result = evaluator.evaluate_expression("df.head(2)", {"df": df, "pd": pd})
            >>> print(result.result)
               a  b
            0  1  4
            1  2  5
        """
        if context is None:
            context = {}

        start_time = time.perf_counter()

        try:
            # Create restricted execution environment
            restricted_globals = self._create_restricted_globals(context)

            # Compile the expression in restricted mode
            code = compile_restricted_exec(f"result = {expression}")
            if code.errors:
                error_msg = f"Invalid expression syntax: {', '.join(code.errors)}"
                self._logger.error(f"Compilation errors for expression '{expression}': {code.errors}")
                return EvaluationResult(
                    result=None,
                    execution_time_ms=0.0,
                    success=False,
                    error_message=error_msg
                )

            # Execute the restricted code
            local_vars = {}
            exec(code.code, restricted_globals, local_vars)
            result = local_vars.get('result')

            if result is None:
                error_msg = "Expression did not produce a result"
                self._logger.error(f"No result from expression '{expression}'")
                return EvaluationResult(
                    result=None,
                    execution_time_ms=0.0,
                    success=False,
                    error_message=error_msg
                )

            execution_time_ms = (time.perf_counter() - start_time) * 1000

            self._logger.debug(
                f"Successfully evaluated expression '{expression}' in {execution_time_ms:.2f}ms"
            )

            return EvaluationResult(
                result=result,
                execution_time_ms=execution_time_ms,
                success=True
            )

        except SyntaxError as e:
            error_msg = f"Invalid expression syntax: {str(e)}"
            self._logger.error(f"Syntax error in expression '{expression}': {e}")
            return EvaluationResult(
                result=None,
                execution_time_ms=0.0,
                success=False,
                error_message=error_msg
            )

        except Exception as e:
            error_msg = f"Error executing expression: {str(e)}"
            self._logger.error(f"Runtime error in expression '{expression}': {e}")
            return EvaluationResult(
                result=None,
                execution_time_ms=0.0,
                success=False,
                error_message=error_msg
            )

    def evaluate_dataframe_expression(
        self,
        expression: str,
        dataframe: pd.DataFrame,
        include_pandas: bool = True
    ) -> EvaluationResult:
        """Evaluate a pandas DataFrame expression in a restricted environment.

        This is a convenience method specifically for DataFrame operations.

        Args:
            expression: The pandas expression to evaluate (e.g., "df.head(5)")
            dataframe: The DataFrame to operate on
            include_pandas: Whether to include the pandas module as 'pd' in the context

        Returns:
            EvaluationResult containing the result, execution time, and success status.

        Example:
            >>> evaluator = RestrictedPythonEvaluator()
            >>> df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
            >>> result = evaluator.evaluate_dataframe_expression("df.describe()", df)
            >>> print(result.result)
                      a         b
            count  3.000000  3.000000
            mean   2.000000  5.000000
            std    1.000000  1.000000
            min    1.000000  4.000000
            25%    1.500000  4.500000
            50%    2.000000  5.000000
            75%    2.500000  5.500000
            max    3.000000  6.000000
        """
        context = {'df': dataframe}
        if include_pandas:
            context['pd'] = pd

        return self.evaluate_expression(expression, context)
