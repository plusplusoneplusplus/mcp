"""API endpoints for Python expression evaluation using the pyeval utility."""

import logging
from typing import Any, Dict, Optional

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from utils.pyeval.evaluator import RestrictedPythonEvaluator, EvaluationError

logger = logging.getLogger(__name__)


async def evaluate_expression(request: Request) -> JSONResponse:
    """Evaluate a Python expression using the RestrictedPythonEvaluator.

    POST /api/pyeval/evaluate

    Request body:
    {
        "expression": "python_expression_to_evaluate",
        "context": {
            "variable_name": "variable_value",
            ...
        }
    }

    Response:
    {
        "success": true/false,
        "result": "evaluation_result" | null,
        "execution_time_ms": 123.45,
        "error_message": "error_description" | null
    }
    """
    try:
        # Parse request body
        body = await request.json()
        expression = body.get("expression", "").strip()
        context = body.get("context", {})

        # Validate input
        if not expression:
            return JSONResponse({
                "success": False,
                "result": None,
                "execution_time_ms": 0.0,
                "error_message": "Expression cannot be empty"
            }, status_code=400)

        if not isinstance(context, dict):
            return JSONResponse({
                "success": False,
                "result": None,
                "execution_time_ms": 0.0,
                "error_message": "Context must be a dictionary"
            }, status_code=400)

        logger.info(f"Evaluating expression: {expression[:100]}{'...' if len(expression) > 100 else ''}")
        logger.debug(f"Context variables: {list(context.keys())}")

        # Create evaluator and evaluate expression
        evaluator = RestrictedPythonEvaluator()
        result = evaluator.evaluate_expression(expression, context)

        # Format result for JSON response
        if result.success:
            # Convert result to string representation for JSON serialization
            result_str = _format_result_for_json(result.result)
            logger.info(f"Expression evaluated successfully in {result.execution_time_ms:.2f}ms")

            return JSONResponse({
                "success": True,
                "result": result_str,
                "execution_time_ms": result.execution_time_ms,
                "error_message": None
            })
        else:
            logger.warning(f"Expression evaluation failed: {result.error_message}")
            return JSONResponse({
                "success": False,
                "result": None,
                "execution_time_ms": result.execution_time_ms,
                "error_message": result.error_message
            })

    except Exception as e:
        logger.error(f"Error in evaluate_expression endpoint: {e}", exc_info=True)
        return JSONResponse({
            "success": False,
            "result": None,
            "execution_time_ms": 0.0,
            "error_message": f"Server error: {str(e)}"
        }, status_code=500)


def _format_result_for_json(result: Any) -> str:
    """Format evaluation result for JSON serialization.

    Args:
        result: The result from expression evaluation

    Returns:
        String representation of the result suitable for JSON response
    """
    try:
        # Handle pandas DataFrames specially
        if hasattr(result, 'to_string'):
            # This covers pandas DataFrames and Series
            return result.to_string()

        # Handle numpy arrays
        elif hasattr(result, 'tolist'):
            return str(result)

        # Handle other iterables (but not strings)
        elif hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
            # Convert to string representation, but limit length for very large iterables
            str_result = str(result)
            if len(str_result) > 10000:
                return str_result[:10000] + "... (truncated)"
            return str_result

        # Handle basic types
        else:
            str_result = str(result)
            # Limit very long string results
            if len(str_result) > 10000:
                return str_result[:10000] + "... (truncated)"
            return str_result

    except Exception as e:
        logger.warning(f"Error formatting result for JSON: {e}")
        return f"<Error formatting result: {str(e)}>"


# API routes for pyeval functionality
pyeval_routes = [
    Route("/api/pyeval/evaluate", endpoint=evaluate_expression, methods=["POST"]),
]
