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
from utils.pyeval import RestrictedPythonEvaluator

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
            "success": True,
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
            "success": True,
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
        response: Dict[str, Any] = {"success": self.success}
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

        return create_success_response({
            "success": True,
            "summary": summary
        })

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

        # Support both 'pandas_expression' and 'expression' field names for backward compatibility
        pandas_expression = body.get("pandas_expression") or body.get("expression")
        if not pandas_expression:
            return create_error_response(
                APIError("MISSING_EXPRESSION", "pandas_expression (or expression) is required")
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

            # Use centralized restricted Python evaluator
            evaluator = RestrictedPythonEvaluator()
            eval_result = evaluator.evaluate_dataframe_expression(pandas_expression, df)

            if not eval_result.success:
                raise ValueError(eval_result.error_message)

            result = eval_result.result
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

        # Check for confirmation parameter
        confirm = request.query_params.get("confirm", "false").lower() == "true"

        # Get DataFrame manager
        manager = get_dataframe_manager()
        await manager.start()

        # Get metadata before deletion for response
        metadata = await manager.storage.get_metadata(df_id)
        if not metadata:
            return create_error_response(
                APIError("DATAFRAME_NOT_FOUND", f"DataFrame with ID '{df_id}' not found"),
                status_code=404
            )

        # If confirmation is required but not provided, return confirmation request
        if not confirm:
            return create_success_response({
                "confirmation_required": True,
                "df_id": df_id,
                "metadata": format_metadata_for_api(metadata),
                "message": f"Confirm deletion of DataFrame '{df_id}' with shape {metadata.shape}",
                "confirm_url": f"/api/dataframes/{df_id}?confirm=true"
            })

        # Delete DataFrame
        deleted = await manager.delete_dataframe(df_id)

        if not deleted:
            return create_error_response(
                APIError("DELETION_FAILED", f"Failed to delete DataFrame '{df_id}'"),
                status_code=500
            )

        return create_success_response({
            "deleted": True,
            "df_id": df_id,
            "freed_memory_bytes": metadata.memory_usage,
            "shape": metadata.shape,
            "message": f"Successfully deleted DataFrame '{df_id}'"
        })

    except Exception as e:
        logger.error(f"Error deleting DataFrame: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to delete DataFrame: {str(e)}"),
            status_code=500
        )


async def api_cleanup_expired_dataframes(request: Request) -> JSONResponse:
    """POST /api/dataframes/cleanup - Clean up expired DataFrames."""
    try:
        # Parse request body for options
        body = {}
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                body = await request.json()
        except Exception:
            # If no body or invalid JSON, use defaults
            pass

        # Get options
        dry_run = body.get("dry_run", False)
        confirm = body.get("confirm", False)

        # Get DataFrame manager
        manager = get_dataframe_manager()
        await manager.start()

        # Get current storage stats before cleanup
        stats_before = await manager.get_storage_stats()

        # Get list of expired DataFrames for reporting
        all_dataframes = await manager.list_stored_dataframes()
        expired_dataframes = [df for df in all_dataframes if df.is_expired]

        # Calculate memory that would be freed
        total_memory_to_free = sum(df.memory_usage for df in expired_dataframes)

        # If dry run, just return what would be cleaned up
        if dry_run:
            return create_success_response({
                "dry_run": True,
                "expired_count": len(expired_dataframes),
                "total_memory_to_free_bytes": total_memory_to_free,
                "total_memory_to_free_mb": round(total_memory_to_free / (1024 * 1024), 2),
                "expired_dataframes": [
                    {
                        "df_id": df.df_id,
                        "shape": df.shape,
                        "memory_usage": df.memory_usage,
                        "expired_since": (datetime.now() - df.expires_at).total_seconds() if df.expires_at else 0
                    }
                    for df in expired_dataframes
                ],
                "message": f"Would clean up {len(expired_dataframes)} expired DataFrames, freeing {round(total_memory_to_free / (1024 * 1024), 2)} MB"
            })

        # If confirmation required but not provided
        if len(expired_dataframes) > 0 and not confirm:
            return create_success_response({
                "confirmation_required": True,
                "expired_count": len(expired_dataframes),
                "total_memory_to_free_bytes": total_memory_to_free,
                "total_memory_to_free_mb": round(total_memory_to_free / (1024 * 1024), 2),
                "message": f"Confirm cleanup of {len(expired_dataframes)} expired DataFrames",
                "confirm_body": {"confirm": True}
            })

        # Perform actual cleanup
        removed_count = await manager.cleanup_expired()

        # Get storage stats after cleanup
        stats_after = await manager.get_storage_stats()

        # Calculate freed memory
        memory_freed = stats_before.get("total_memory_bytes", 0) - stats_after.get("total_memory_bytes", 0)

        return create_success_response({
            "cleaned_up": True,
            "removed_count": removed_count,
            "memory_freed_bytes": memory_freed,
            "memory_freed_mb": round(memory_freed / (1024 * 1024), 2),
            "stats_before": {
                "total_dataframes": stats_before.get("total_dataframes", 0),
                "total_memory_mb": round(stats_before.get("total_memory_bytes", 0) / (1024 * 1024), 2)
            },
            "stats_after": {
                "total_dataframes": stats_after.get("total_dataframes", 0),
                "total_memory_mb": round(stats_after.get("total_memory_bytes", 0) / (1024 * 1024), 2)
            },
            "message": f"Successfully cleaned up {removed_count} expired DataFrames, freed {round(memory_freed / (1024 * 1024), 2)} MB"
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
    try:
        # Parse multipart form data
        form = await request.form()

        # Get uploaded file
        upload_file = form.get("file")
        if not isinstance(upload_file, UploadFile) or not upload_file.filename:
            return create_error_response(
                APIError("MISSING_FILE", "No file uploaded or invalid file format")
            )

        # Get optional parameters
        ttl_seconds_str = form.get("ttl_seconds")
        ttl_seconds: Optional[int] = None
        if ttl_seconds_str and isinstance(ttl_seconds_str, str):
            try:
                ttl_seconds = int(ttl_seconds_str)
            except (ValueError, TypeError):
                return create_error_response(
                    APIError("INVALID_TTL", "ttl_seconds must be a valid integer")
                )

        # Get optional display name
        display_name = form.get("display_name")

        # Get file format options
        csv_separator = form.get("csv_separator", ",")
        csv_encoding = form.get("csv_encoding", "utf-8")
        excel_sheet_str = form.get("excel_sheet", "0")
        excel_sheet: Union[int, str] = 0
        if excel_sheet_str != "0" and isinstance(excel_sheet_str, str):
            try:
                excel_sheet = int(excel_sheet_str)
            except (ValueError, TypeError):
                excel_sheet = excel_sheet_str  # Sheet name

        # Read file content
        file_content = await upload_file.read()
        filename = upload_file.filename

        if not filename:
            return create_error_response(
                APIError("INVALID_FILENAME", "Uploaded file must have a filename")
            )

        # Determine file format from extension
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''

        try:
            # Load DataFrame based on file format
            if file_ext == 'csv':
                import io
                df = pd.read_csv(
                    io.BytesIO(file_content),
                    sep=csv_separator,
                    encoding=csv_encoding
                )
            elif file_ext in ['xlsx', 'xls']:
                import io
                df = pd.read_excel(
                    io.BytesIO(file_content),
                    sheet_name=excel_sheet
                )
            elif file_ext == 'json':
                import io
                df = pd.read_json(io.BytesIO(file_content))
            elif file_ext == 'parquet':
                import io
                df = pd.read_parquet(io.BytesIO(file_content))
            else:
                return create_error_response(
                    APIError("UNSUPPORTED_FORMAT", f"Unsupported file format: {file_ext}. Supported formats: csv, xlsx, xls, json, parquet")
                )

            # Validate DataFrame
            if df.empty:
                return create_error_response(
                    APIError("EMPTY_DATAFRAME", "Uploaded file resulted in empty DataFrame")
                )

            # Get DataFrame manager and store the DataFrame
            manager = get_dataframe_manager()
            await manager.start()

            # Create tags with source information
            tags = {
                "source": f"upload:{filename}",
                "original_filename": filename,
                "file_format": file_ext,
                "upload_timestamp": datetime.now().isoformat()
            }

            # Add display name if provided
            if display_name and isinstance(display_name, str):
                tags["display_name"] = display_name

            # Store DataFrame
            df_id = await manager.store_dataframe(
                df=df,
                ttl_seconds=ttl_seconds,
                tags=tags
            )

            # Get metadata for response
            metadata = await manager.storage.get_metadata(df_id)

            return create_success_response({
                "success": True,
                "df_id": df_id,
                "filename": filename,
                "shape": df.shape,
                "memory_usage": metadata.memory_usage if metadata else None,
                "message": f"Successfully uploaded and stored DataFrame from {filename}"
            }, status_code=201)

        except pd.errors.EmptyDataError:
            return create_error_response(
                APIError("EMPTY_FILE", "Uploaded file is empty or contains no data")
            )
        except pd.errors.ParserError as e:
            return create_error_response(
                APIError("PARSE_ERROR", f"Error parsing file: {str(e)}")
            )
        except Exception as e:
            logger.error(f"Error processing uploaded file {filename}: {e}")
            return create_error_response(
                APIError("PROCESSING_ERROR", f"Error processing uploaded file: {str(e)}")
            )

    except Exception as e:
        logger.error(f"Error in file upload endpoint: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to process file upload: {str(e)}"),
            status_code=500
        )


async def api_load_dataframe_from_url(request: Request) -> JSONResponse:
    """POST /api/dataframes/load-url - Load data from URL."""
    try:
        # Parse request body
        try:
            body = await request.json()
        except Exception:
            return create_error_response(
                APIError("INVALID_REQUEST_BODY", "Invalid JSON in request body")
            )

        # Get required URL parameter
        url = body.get("url")
        if not url:
            return create_error_response(
                APIError("MISSING_URL", "URL is required")
            )

        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            return create_error_response(
                APIError("INVALID_URL", "URL must start with http:// or https://")
            )

        # Get optional parameters
        ttl_seconds = body.get("ttl_seconds")
        if ttl_seconds is not None:
            try:
                ttl_seconds = int(ttl_seconds)
            except ValueError:
                return create_error_response(
                    APIError("INVALID_TTL", "ttl_seconds must be a valid integer")
                )

        # Get optional display name
        display_name = body.get("display_name")

        # Get file format options
        file_format = body.get("format", "auto")  # auto-detect by default
        csv_separator = body.get("csv_separator", ",")
        csv_encoding = body.get("csv_encoding", "utf-8")
        excel_sheet = body.get("excel_sheet", 0)
        if excel_sheet != 0:
            try:
                excel_sheet = int(excel_sheet)
            except ValueError:
                excel_sheet = str(excel_sheet)  # Sheet name

        try:
            # Import aiohttp for async HTTP requests
            import aiohttp
            import asyncio

            # Download data from URL
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return create_error_response(
                            APIError("URL_ERROR", f"Failed to fetch URL: HTTP {response.status}")
                        )

                    # Get content type and file extension from URL
                    content_type = response.headers.get('content-type', '').lower()
                    url_path = url.split('?')[0]  # Remove query parameters
                    file_ext = url_path.split('.')[-1].lower() if '.' in url_path else ''

                    # Auto-detect format if not specified
                    if file_format == "auto":
                        if 'csv' in content_type or file_ext == 'csv':
                            file_format = 'csv'
                        elif 'json' in content_type or file_ext == 'json':
                            file_format = 'json'
                        elif file_ext in ['xlsx', 'xls']:
                            file_format = 'excel'
                        elif file_ext == 'parquet':
                            file_format = 'parquet'
                        else:
                            # Default to CSV for unknown formats
                            file_format = 'csv'

                    # Read response content
                    content = await response.read()

            # Load DataFrame based on format
            import io
            try:
                if file_format == 'csv':
                    df = pd.read_csv(
                        io.BytesIO(content),
                        sep=csv_separator,
                        encoding=csv_encoding
                    )
                elif file_format == 'json':
                    df = pd.read_json(io.BytesIO(content))
                elif file_format == 'excel':
                    df = pd.read_excel(
                        io.BytesIO(content),
                        sheet_name=excel_sheet
                    )
                elif file_format == 'parquet':
                    df = pd.read_parquet(io.BytesIO(content))
                else:
                    return create_error_response(
                        APIError("UNSUPPORTED_FORMAT", f"Unsupported format: {file_format}. Supported formats: csv, json, excel, parquet")
                    )

                # Validate DataFrame
                if df.empty:
                    return create_error_response(
                        APIError("EMPTY_DATAFRAME", "URL data resulted in empty DataFrame")
                    )

                # Get DataFrame manager and store the DataFrame
                manager = get_dataframe_manager()
                await manager.start()

                # Create tags with source information
                tags = {
                    "source": f"url:{url}",
                    "original_url": url,
                    "file_format": file_format,
                    "load_timestamp": datetime.now().isoformat(),
                    "content_type": content_type
                }

                # Add display name if provided
                if display_name:
                    tags["display_name"] = display_name

                # Store DataFrame
                df_id = await manager.store_dataframe(
                    df=df,
                    ttl_seconds=ttl_seconds,
                    tags=tags
                )

                # Get metadata for response
                metadata = await manager.storage.get_metadata(df_id)

                return create_success_response({
                    "success": True,
                    "df_id": df_id,
                    "url": url,
                    "format": file_format,
                    "shape": df.shape,
                    "memory_usage": metadata.memory_usage if metadata else None,
                    "message": f"Successfully loaded DataFrame from URL"
                }, status_code=201)

            except pd.errors.EmptyDataError:
                return create_error_response(
                    APIError("EMPTY_DATA", "URL contains no data or empty file")
                )
            except pd.errors.ParserError as e:
                return create_error_response(
                    APIError("PARSE_ERROR", f"Error parsing data from URL: {str(e)}")
                )
            except Exception as e:
                logger.error(f"Error processing data from URL {url}: {e}")
                return create_error_response(
                    APIError("PROCESSING_ERROR", f"Error processing data from URL: {str(e)}")
                )

        except aiohttp.ClientError as e:
            return create_error_response(
                APIError("NETWORK_ERROR", f"Network error accessing URL: {str(e)}")
            )
        except asyncio.TimeoutError:
            return create_error_response(
                APIError("TIMEOUT_ERROR", "Timeout while fetching data from URL")
            )
        except ImportError:
            return create_error_response(
                APIError("DEPENDENCY_ERROR", "aiohttp library not available for URL loading"),
                status_code=500
            )
        except Exception as e:
            logger.error(f"Error loading data from URL {url}: {e}")
            return create_error_response(
                APIError("URL_LOAD_ERROR", f"Failed to load data from URL: {str(e)}")
            )

    except Exception as e:
        logger.error(f"Error in URL loading endpoint: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to process URL loading: {str(e)}"),
            status_code=500
        )


async def api_batch_delete_dataframes(request: Request) -> JSONResponse:
    """POST /api/dataframes/batch-delete - Delete multiple DataFrames."""
    try:
        # Parse request body
        try:
            body = await request.json()
        except Exception:
            return create_error_response(
                APIError("INVALID_REQUEST_BODY", "Invalid JSON in request body")
            )

        # Get DataFrame IDs to delete
        df_ids = body.get("df_ids", [])
        if not df_ids or not isinstance(df_ids, list):
            return create_error_response(
                APIError("MISSING_DF_IDS", "df_ids array is required")
            )

        # Check for confirmation parameter
        confirm = body.get("confirm", False)

        # Get DataFrame manager
        manager = get_dataframe_manager()
        await manager.start()

        # Get metadata for all DataFrames before deletion
        dataframes_info = []
        total_memory_to_free = 0
        not_found_ids = []

        for df_id in df_ids:
            metadata = await manager.storage.get_metadata(df_id)
            if metadata:
                dataframes_info.append({
                    "df_id": df_id,
                    "shape": metadata.shape,
                    "memory_usage": metadata.memory_usage,
                    "created_at": metadata.created_at.isoformat()
                })
                total_memory_to_free += metadata.memory_usage
            else:
                not_found_ids.append(df_id)

        # If some DataFrames not found, include in response
        if not_found_ids:
            return create_error_response(
                APIError("DATAFRAMES_NOT_FOUND", f"DataFrames not found: {not_found_ids}"),
                status_code=404
            )

        # If confirmation is required but not provided, return confirmation request
        if not confirm:
            return create_success_response({
                "confirmation_required": True,
                "df_count": len(dataframes_info),
                "total_memory_to_free_bytes": total_memory_to_free,
                "total_memory_to_free_mb": round(total_memory_to_free / (1024 * 1024), 2),
                "dataframes": dataframes_info,
                "message": f"Confirm deletion of {len(dataframes_info)} DataFrames",
                "confirm_body": {"df_ids": df_ids, "confirm": True}
            })

        # Perform batch deletion
        deleted_count = 0
        failed_deletions = []

        for df_id in df_ids:
            try:
                deleted = await manager.delete_dataframe(df_id)
                if deleted:
                    deleted_count += 1
                else:
                    failed_deletions.append(df_id)
            except Exception as e:
                logger.error(f"Error deleting DataFrame {df_id}: {e}")
                failed_deletions.append(df_id)

        # Create response
        response_data: Dict[str, Any] = {
            "batch_deleted": True,
            "requested_count": len(df_ids),
            "deleted_count": deleted_count,
            "failed_count": len(failed_deletions),
            "freed_memory_bytes": total_memory_to_free,
            "freed_memory_mb": round(total_memory_to_free / (1024 * 1024), 2),
            "message": f"Successfully deleted {deleted_count} of {len(df_ids)} DataFrames"
        }

        if failed_deletions:
            response_data["failed_deletions"] = failed_deletions
            response_data["message"] = response_data["message"] + f", {len(failed_deletions)} failed"

        return create_success_response(response_data)

    except Exception as e:
        logger.error(f"Error in batch delete endpoint: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to process batch deletion: {str(e)}"),
            status_code=500
        )


async def api_export_dataframe(request: Request) -> JSONResponse:
    """POST /api/dataframes/{df_id}/export - Export DataFrame to file."""
    try:
        df_id = request.path_params["df_id"]

        # Parse request body
        try:
            body = await request.json()
        except Exception:
            return create_error_response(
                APIError("INVALID_REQUEST_BODY", "Invalid JSON in request body")
            )

        # Get export parameters
        export_format = body.get("format", "csv").lower()
        filename = body.get("filename")

        # Validate export format
        supported_formats = ["csv", "json", "excel", "parquet"]
        if export_format not in supported_formats:
            return create_error_response(
                APIError("UNSUPPORTED_FORMAT", f"Unsupported export format: {export_format}. Supported formats: {supported_formats}")
            )

        # Get optional parameters
        limit_rows = body.get("limit_rows")
        if limit_rows is not None:
            try:
                limit_rows = int(limit_rows)
                if limit_rows <= 0:
                    return create_error_response(
                        APIError("INVALID_LIMIT", "limit_rows must be a positive integer")
                    )
            except ValueError:
                return create_error_response(
                    APIError("INVALID_LIMIT", "limit_rows must be a valid integer")
                )

        # Format-specific options
        csv_separator = body.get("csv_separator", ",")
        csv_index = body.get("csv_index", False)
        json_orient = body.get("json_orient", "records")
        excel_sheet_name = body.get("excel_sheet_name", "Sheet1")

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

        # Apply row limit if specified
        original_shape = df.shape
        if limit_rows and len(df) > limit_rows:
            df = df.head(limit_rows)

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dataframe_{df_id}_{timestamp}.{export_format}"
        elif not filename.endswith(f".{export_format}"):
            filename = f"{filename}.{export_format}"

        try:
            # Export DataFrame based on format
            import io
            import tempfile
            import os

            # Create temporary file for export
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{export_format}") as temp_file:
                temp_path = temp_file.name

                if export_format == "csv":
                    df.to_csv(temp_path, sep=csv_separator, index=csv_index)
                elif export_format == "json":
                    df.to_json(temp_path, orient=json_orient, indent=2)
                elif export_format == "excel":
                    df.to_excel(temp_path, sheet_name=excel_sheet_name, index=False)
                elif export_format == "parquet":
                    df.to_parquet(temp_path, index=False)

                # Get file size
                file_size = os.path.getsize(temp_path)

                # Read file content for response
                with open(temp_path, 'rb') as f:
                    file_content = f.read()

                # Clean up temporary file
                os.unlink(temp_path)

            # Prepare response with file content
            import base64
            file_content_b64 = base64.b64encode(file_content).decode('utf-8')

            # Determine MIME type
            mime_types = {
                "csv": "text/csv",
                "json": "application/json",
                "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "parquet": "application/octet-stream"
            }

            return create_success_response({
                "exported": True,
                "df_id": df_id,
                "filename": filename,
                "format": export_format,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "original_shape": original_shape,
                "exported_shape": df.shape,
                "mime_type": mime_types[export_format],
                "file_content": file_content_b64,
                "download_info": {
                    "filename": filename,
                    "content_type": mime_types[export_format],
                    "size": file_size
                },
                "message": f"Successfully exported DataFrame to {export_format.upper()} format"
            })

        except Exception as e:
            logger.error(f"Error exporting DataFrame {df_id} to {export_format}: {e}")
            return create_error_response(
                APIError("EXPORT_ERROR", f"Failed to export DataFrame: {str(e)}")
            )

    except Exception as e:
        logger.error(f"Error in export endpoint: {e}")
        return create_error_response(
            APIError("INTERNAL_ERROR", f"Failed to process export request: {str(e)}"),
            status_code=500
        )
