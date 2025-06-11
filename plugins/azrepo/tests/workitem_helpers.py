"""
Test helpers for Azure Work Item tool tests.
"""

import json
from typing import Optional
from unittest.mock import patch, MagicMock, AsyncMock


def mock_aiohttp_response(
    method: str = "post",
    status_code: int = 200,
    response_data: Optional[dict] = None,
    error_message: Optional[str] = None,
    raw_response_text: Optional[str] = None,
):
    """
    Helper function to mock aiohttp responses for different methods (post, patch, get).

    Args:
        method: The HTTP method to mock (e.g., "post", "patch", "get").
        status_code: The HTTP status code to return.
        response_data: The JSON response data to return on success.
        error_message: The error message to return on failure.
        raw_response_text: Optional raw text to be returned by response.text().

    Returns:
        A patch object for aiohttp.ClientSession.
    """
    json_payload = None
    if raw_response_text is not None:
        text_payload = raw_response_text
        try:
            json_payload = json.loads(text_payload)
        except json.JSONDecodeError:
            json_payload = {"error": "invalid json in mock"}
    else:
        if status_code < 300 and response_data is None:
            response_data = {
                "id": 12345,
                "rev": 1,
                "fields": {"System.Title": "Test Work Item"},
                "url": "https://dev.azure.com/testorg/test-project/_apis/wit/workitems/12345",
            }

        json_payload = (
            response_data if status_code < 300 else {"message": error_message}
        )
        text_payload = json.dumps(json_payload)

    mock_response = MagicMock()
    mock_response.status = status_code
    mock_response.text = AsyncMock(return_value=text_payload)
    mock_response.json = AsyncMock(return_value=json_payload)

    mock_session = MagicMock()
    http_method_mock = getattr(mock_session, method)
    http_method_mock.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    http_method_mock.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    return patch("aiohttp.ClientSession", return_value=mock_session)


def mock_azure_http_client(
    method: str = "post",
    status_code: int = 200,
    response_data: Optional[dict] = None,
    error_message: Optional[str] = None,
    raw_response_text: Optional[str] = None,
):
    """
    Helper function to mock AzureHttpClient responses for different methods (post, patch, get).

    Args:
        method: The HTTP method to mock (e.g., "post", "patch", "get").
        status_code: The HTTP status code to return.
        response_data: The JSON response data to return on success.
        error_message: The error message to return on failure.
        raw_response_text: Optional raw text to be returned by response.text().

    Returns:
        A patch object for AzureHttpClient.
    """
    # Prepare the response data
    if raw_response_text is not None:
        text_payload = raw_response_text
        try:
            json_payload = json.loads(text_payload)
        except json.JSONDecodeError:
            json_payload = {"error": "invalid json in mock"}
    else:
        if status_code < 300 and response_data is None:
            response_data = {
                "id": 12345,
                "rev": 1,
                "fields": {"System.Title": "Test Work Item"},
                "url": "https://dev.azure.com/testorg/test-project/_apis/wit/workitems/12345",
            }

        json_payload = (
            response_data if status_code < 300 else {"message": error_message}
        )
        text_payload = json.dumps(json_payload)

    # Create the standardized AzureHttpClient response format
    if status_code < 300:
        mock_result = {
            "success": True,
            "data": json_payload,
            "status_code": status_code,
            "raw_response": text_payload
        }
    else:
        mock_result = {
            "success": False,
            "error": error_message or f"HTTP {status_code}",
            "status_code": status_code,
            "raw_response": text_payload
        }

    # Create the mock AzureHttpClient
    mock_client = MagicMock()
    mock_client.request = AsyncMock(return_value=mock_result)

    # Set up the async context manager
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    return patch("plugins.azrepo.workitem_tool.AzureHttpClient", return_value=mock_client)
