"""DataFrame API endpoints for web interface.

This module provides RESTful API endpoints for DataFrame management operations
including listing, viewing, manipulating, and managing stored DataFrames.
"""

import logging
import time
import json
import numpy as np
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.datastructures import UploadFile
import pandas as pd

# Import DataFrame manager
from utils.dataframe_manager import get_dataframe_manager
from utils.dataframe_manager.interface import DataFrameMetadata

logger = logging.getLogger(__name__)


# Request/Response Models and Validation Schemas

class DataFrameListResponse:
    """Response model for DataFrame list endpoint."""

    def __init__(self, dataframes: List[Dict[str, Any]], total_count: int, storage_stats: Dict[str, Any]):
        self.dataframes = dataframes
        self.total_count = total_count
        self.storage_stats = storage_stats

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataframes": self.dataframes,
            "total_count": self.total_count,
            "storage_stats": self.storage_stats
        }


class DataFrameDetailResponse:
    """Response model for DataFrame detail endpoint."""

    def __init__(self, df_id: str, metadata: Dict[str, Any], summary: Optional[Dict[str, Any]] = None):
        self.df_id = df_id
        self.metadata = metadata
        self.summary = summary

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "df_id": self.df_id,
            "metadata": self.metadata
        }
        if self.summary:
            result["summary"] = self.summary
        return result


class DataFrameDataResponse:
    """Response model for DataFrame data endpoint."""

    def __init__(self, data: List[Dict[str, Any]], columns: List[str], dtypes: Dict[str, str],
                 total_rows: int, page: int, page_size: int, has_more: bool):
        self.data = data
        self.columns = columns
        self.dtypes = dtypes
        self.total_rows = total_rows
        self.page = page
        self.page_size = page_size
        self.has_more = has_more

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "columns": self.columns,
            "dtypes": self.dtypes,
            "total_rows": self.total_rows,
            "page": self.page,
            "page_size": self.page_size,
            "has_more": self.has_more
        }


class ExecuteOperationResponse:
    """Response model for operation execution endpoint."""

    def __init__(self, success: bool, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.success = success
        self.result = result
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        response = {"success": self.success}
        if self.result:
            response["result"] = self.result
        if self.error:
            response["error"] = self.error
        return response


class APIError:
    """Standard API error response."""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }


# Utility Functions

def convert_numpy_types(obj: Any) -> Any:
    """Convert numpy/pandas types to JSON-serializable Python types."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj


def format_metadata_for_api(metadata: DataFrameMetadata) -> Dict[str, Any]:
    """Convert DataFrameMetadata to API-friendly dictionary."""
    return {
        "df_id": metadata.df_id,
        "created_at": metadata.created_at.isoformat(),
        "expires_at": metadata.expires_at.isoformat() if metadata.expires_at else None,
        "is_expired": metadata.is_expired,
        "shape": metadata.shape,
        "size_bytes": metadata.size_bytes,
        "memory_usage": metadata.memory_usage,
        "dtypes": metadata.dtypes,
        "tags": metadata.tags,
        "ttl_seconds": metadata.ttl_seconds
    }


def validate_pagination_params(page: int, page_size: int) -> tuple[int, int]:
    """Validate and normalize pagination parameters."""
    page = max(1, page)
    page_size = min(max(10, page_size), 1000)  # Limit page size between 10-1000
    return page, page_size


def create_error_response(error: APIError, status_code: int = 400) -> JSONResponse:
    """Create standardized error response."""
    return JSONResponse(content=error.to_dict(), status_code=status_code)


def create_success_response(data: Any, status_code: int = 200) -> JSONResponse:
    """Create standardized success response."""
    if hasattr(data, 'to_dict'):
        content = data.to_dict()
    elif isinstance(data, dict):
        content = data
    else:
        content = {"data": data}

    # Convert numpy types to JSON-serializable types
    content = convert_numpy_types(content)

    return JSONResponse(content=content, status_code=status_code)


# API Endpoint Functions

async def api_list_dataframes(request: Request) -> JSONResponse:
    """GET /api/dataframes - List all stored DataFrames with metadata and statistics."""
    try:
        # Get query parameters
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))
        tags_filter = request.query_params.get("tags")

        # Validate pagination
        page, page_size = validate_pagination_params(page, page_size)

        # Parse tags filter if provided
        tags = None
        if tags_filter:
            try:
                tags = json.loads(tags_filter)
            except json.JSONDecodeError:
                return create_error_response(
                    APIError("INVALID_TAGS_FILTER", "Invalid JSON format for tags filter")
                )

        # Get DataFrame manager
        manager = get_dataframe_manager()
        await manager.start()

        # Get DataFrames and storage stats
        dataframes_metadata = await manager.list_stored_dataframes(tags=tags)
        storage_stats = await manager.get_storage_stats()

        # Convert metadata to API format
        dataframes_list = [format_metadata_for_api(metadata) for metadata in dataframes_metadata]

        # Apply pagination
        total_count = len(dataframes_list)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_dataframes = dataframes_list[start_idx:end_idx]

        # Create response
        response = DataFrameListResponse(
            dataframes=paginated_dataframes,
            total_count=total_count,
            storage_stats=storage_stats
        )

        return create_success_response(response)

    except Exception as e:
        logger.error(f"Error listing DataFrames: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to list DataFrames: {str(e)}"),
            status_code=500
        )


async def api_get_dataframe_detail(request: Request) -> JSONResponse:
    """GET /api/dataframes/{df_id} - Get detailed information about a specific DataFrame."""
    try:
        df_id = request.path_params["df_id"]
        include_summary = request.query_params.get("include_summary", "false").lower() == "true"

        # Get DataFrame manager
        manager = get_dataframe_manager()
        await manager.start()

        # Get metadata
        metadata = await manager.storage.get_metadata(df_id)
        if not metadata:
            return create_error_response(
                APIError("DATAFRAME_NOT_FOUND", f"DataFrame with ID '{df_id}' not found or expired"),
                status_code=404
            )

        # Get summary if requested
        summary = None
        if include_summary:
            summary = await manager.summarize_dataframe(df_id, max_size_bytes=10240)

        # Create response
        response = DataFrameDetailResponse(
            df_id=df_id,
            metadata=format_metadata_for_api(metadata),
            summary=summary
        )

        return create_success_response(response)

    except Exception as e:
        logger.error(f"Error getting DataFrame detail: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to get DataFrame detail: {str(e)}"),
            status_code=500
        )


async def api_get_storage_stats(request: Request) -> JSONResponse:
    """GET /api/dataframes/stats - Get storage statistics."""
    try:
        # Get DataFrame manager
        manager = get_dataframe_manager()
        await manager.start()

        # Get storage statistics
        stats = await manager.get_storage_stats()

        return create_success_response(stats)

    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to get storage stats: {str(e)}"),
            status_code=500
        )


async def api_get_dataframe_data(request: Request) -> JSONResponse:
    """GET /api/dataframes/{df_id}/data - Get DataFrame data with pagination support."""
    try:
        df_id = request.path_params["df_id"]
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))
        columns = request.query_params.get("columns")  # Comma-separated column names

        # Validate pagination
        page, page_size = validate_pagination_params(page, page_size)

        # Parse columns filter if provided
        column_list = None
        if columns:
            column_list = [col.strip() for col in columns.split(",") if col.strip()]

        # Get DataFrame manager
        manager = get_dataframe_manager()
        await manager.start()

        # Get DataFrame
        df = await manager.get_dataframe(df_id)
        if df is None:
            return create_error_response(
                APIError("DATAFRAME_NOT_FOUND", f"DataFrame with ID '{df_id}' not found or expired"),
                status_code=404
            )

        # Apply column filtering if specified
        if column_list:
            missing_cols = [col for col in column_list if col not in df.columns]
            if missing_cols:
                return create_error_response(
                    APIError("INVALID_COLUMNS", f"Columns not found: {missing_cols}")
                )
            df = df[column_list]

        # Apply pagination
        total_rows = len(df)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_df = df.iloc[start_idx:end_idx]

        # Convert to records format
        data = paginated_df.to_dict('records')
        columns = list(paginated_df.columns)
        dtypes = {col: str(dtype) for col, dtype in paginated_df.dtypes.items()}
        has_more = end_idx < total_rows

        # Create response
        response = DataFrameDataResponse(
            data=data,
            columns=columns,
            dtypes=dtypes,
            total_rows=total_rows,
            page=page,
            page_size=page_size,
            has_more=has_more
        )

        return create_success_response(response)

    except Exception as e:
        logger.error(f"Error getting DataFrame data: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to get DataFrame data: {str(e)}"),
            status_code=500
        )


async def api_get_dataframe_summary(request: Request) -> JSONResponse:
    """GET /api/dataframes/{df_id}/summary - Get DataFrame summary information."""
    try:
        df_id = request.path_params["df_id"]
        max_size_bytes = int(request.query_params.get("max_size_bytes", 10240))
        include_sample = request.query_params.get("include_sample", "true").lower() == "true"

        # Get DataFrame manager
        manager = get_dataframe_manager()
        await manager.start()

        # Get summary
        summary = await manager.summarize_dataframe(
            df_id=df_id,
            max_size_bytes=max_size_bytes,
            include_sample=include_sample
        )

        if summary is None:
            return create_error_response(
                APIError("DATAFRAME_NOT_FOUND", f"DataFrame with ID '{df_id}' not found or expired"),
                status_code=404
            )

        return create_success_response(summary)

    except Exception as e:
        logger.error(f"Error getting DataFrame summary: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to get DataFrame summary: {str(e)}"),
            status_code=500
        )


async def api_execute_dataframe_operation(request: Request) -> JSONResponse:
    """POST /api/dataframes/{df_id}/execute - Execute pandas expressions on DataFrame."""
    try:
        df_id = request.path_params["df_id"]

        # Parse request body
        try:
            body = await request.json()
        except Exception:
            return create_error_response(
                APIError("INVALID_REQUEST_BODY", "Invalid JSON in request body")
            )

        pandas_expression = body.get("pandas_expression")
        if not pandas_expression:
            return create_error_response(
                APIError("MISSING_EXPRESSION", "pandas_expression is required")
            )

        # Get DataFrame manager
        manager = get_dataframe_manager()
        await manager.start()

        # Get DataFrame
        df = await manager.get_dataframe(df_id)
        if df is None:
            return create_error_response(
                APIError("DATAFRAME_NOT_FOUND", f"DataFrame with ID '{df_id}' not found or expired"),
                status_code=404
            )

        # Execute pandas expression
        try:
            start_time = time.time()

            # Create safe execution environment
            safe_globals = {
                'df': df,
                'pd': pd
            }

            # Execute the expression
            result = eval(pandas_expression, safe_globals)
            execution_time_ms = (time.time() - start_time) * 1000

            # Handle different result types
            if isinstance(result, pd.DataFrame):
                result_data = {
                    "data": result.to_dict('records') if len(result) <= 100 else f"Large result with {len(result)} rows",
                    "shape": result.shape,
                    "execution_time_ms": round(execution_time_ms, 2),
                    "result_type": "dataframe"
                }
                if len(result) > 100:
                    result_data["sample_data"] = result.head(5).to_dict('records')
                    result_data["note"] = "Use .head() or .tail() in your expression to limit large results"
            elif isinstance(result, pd.Series):
                result_df = result.to_frame()
                result_data = {
                    "data": result_df.to_dict('records') if len(result_df) <= 100 else f"Large result with {len(result_df)} rows",
                    "shape": result_df.shape,
                    "execution_time_ms": round(execution_time_ms, 2),
                    "result_type": "series"
                }
            else:
                # Scalar result
                result_data = {
                    "data": result,
                    "execution_time_ms": round(execution_time_ms, 2),
                    "result_type": "scalar"
                }

            response = ExecuteOperationResponse(success=True, result=result_data)
            return create_success_response(response)

        except SyntaxError as e:
            return create_error_response(
                APIError("SYNTAX_ERROR", f"Invalid pandas expression syntax: {str(e)}")
            )
        except Exception as e:
            return create_error_response(
                APIError("EXECUTION_ERROR", f"Error executing pandas expression: {str(e)}")
            )

    except Exception as e:
        logger.error(f"Error executing DataFrame operation: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to execute operation: {str(e)}"),
            status_code=500
        )


async def api_delete_dataframe(request: Request) -> JSONResponse:
    """DELETE /api/dataframes/{df_id} - Delete a specific DataFrame."""
    try:
        df_id = request.path_params["df_id"]

        # Get DataFrame manager
        manager = get_dataframe_manager()
        await manager.start()

        # Delete DataFrame
        deleted = await manager.delete_dataframe(df_id)

        if not deleted:
            return create_error_response(
                APIError("DATAFRAME_NOT_FOUND", f"DataFrame with ID '{df_id}' not found"),
                status_code=404
            )

        return create_success_response({"deleted": True, "df_id": df_id})

    except Exception as e:
        logger.error(f"Error deleting DataFrame: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to delete DataFrame: {str(e)}"),
            status_code=500
        )


async def api_cleanup_expired_dataframes(request: Request) -> JSONResponse:
    """POST /api/dataframes/cleanup - Clean up expired DataFrames."""
    try:
        # Get DataFrame manager
        manager = get_dataframe_manager()
        await manager.start()

        # Cleanup expired DataFrames
        removed_count = await manager.cleanup_expired()

        return create_success_response({
            "cleaned_up": True,
            "removed_count": removed_count
        })

    except Exception as e:
        logger.error(f"Error cleaning up expired DataFrames: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to cleanup expired DataFrames: {str(e)}"),
            status_code=500
        )


# Placeholder functions for file upload and export (to be implemented in later tasks)

async def api_upload_dataframe(request: Request) -> JSONResponse:
    """POST /api/dataframes/upload - Upload file and create DataFrame."""
    # TODO: Implement in task 2.1
    return create_error_response(
        APIError("NOT_IMPLEMENTED", "File upload functionality not yet implemented"),
        status_code=501
    )


async def api_load_dataframe_from_url(request: Request) -> JSONResponse:
    """POST /api/dataframes/load-url - Load data from URL."""
    # TODO: Implement in task 2.1
    return create_error_response(
        APIError("NOT_IMPLEMENTED", "URL loading functionality not yet implemented"),
        status_code=501
    )


async def api_export_dataframe(request: Request) -> JSONResponse:
    """POST /api/dataframes/{df_id}/export - Export DataFrame to file."""
    # TODO: Implement in task 2.3
    return create_error_response(
        APIError("NOT_IMPLEMENTED", "Export functionality not yet implemented"),
        status_code=501
    )
