"""Test fixtures for code-based tools testing.

This module provides common fixtures and utilities for testing code-based tools.
"""

import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def mock_external_dependencies():
    """Fixture to mock external dependencies to avoid side effects during testing."""
    with patch('subprocess.run') as mock_subprocess, \
         patch('asyncio.create_subprocess_shell') as mock_async_subprocess, \
         patch('mcp_tools.browser.factory.BrowserClientFactory.create_client') as mock_browser, \
         patch('psutil.Process') as mock_psutil, \
         patch('requests.get') as mock_requests, \
         patch('requests.post') as mock_requests_post:

        # Configure subprocess mocks
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="mock output",
            stderr=""
        )

        # Configure async subprocess mock
        mock_async_process = AsyncMock()
        mock_async_process.pid = 12345
        mock_async_process.returncode = 0
        mock_async_process.wait = AsyncMock(return_value=0)
        mock_async_subprocess.return_value = mock_async_process

        # Configure browser factory mock
        mock_browser_instance = MagicMock()
        mock_browser_instance.get_page_html = AsyncMock(return_value="<html>Mock HTML</html>")
        mock_browser_instance.take_screenshot = AsyncMock(return_value=True)
        mock_browser.return_value.__aenter__ = AsyncMock(return_value=mock_browser_instance)
        mock_browser.return_value.__aexit__ = AsyncMock(return_value=None)

        # Configure psutil mock
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.status.return_value = "running"
        mock_process.cpu_percent.return_value = 5.0
        mock_process.memory_info.return_value = MagicMock(rss=1024*1024, vms=2048*1024)
        mock_psutil.return_value = mock_process

        # Configure requests mocks
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Mock response content"
        mock_response.json.return_value = {"status": "success", "data": "mock data"}
        mock_requests.return_value = mock_response
        mock_requests_post.return_value = mock_response

        yield {
            'subprocess': mock_subprocess,
            'async_subprocess': mock_async_subprocess,
            'browser': mock_browser,
            'psutil': mock_psutil,
            'requests_get': mock_requests,
            'requests_post': mock_requests_post
        }


@pytest.fixture
def sample_tool_arguments():
    """Fixture providing sample arguments for different types of tools."""
    return {
        'browser_tools': {
            'operation': 'get_page_html',
            'url': 'https://example.com',
            'wait_time': 5
        },
        'command_tools': {
            'command': 'echo "test"',
            'timeout': 10
        },
        'time_tools': {
            'operation': 'get_time',
            'timezone': 'UTC'
        },
        'git_tools': {
            'operation': 'status',
            'repo_path': '/tmp/test-repo'
        },
        'azure_tools': {
            'operation': 'list_repos',
            'organization': 'test-org',
            'project': 'test-project'
        },
        'knowledge_tools': {
            'operation': 'search',
            'query': 'test query',
            'collection': 'test-collection'
        },
        'summarizer_tools': {
            'operation': 'summarize',
            'url': 'https://example.com',
            'max_length': 500
        }
    }


def get_tool_category(tool_name: str) -> str:
    """Determine the category of a tool based on its name."""
    if 'browser' in tool_name.lower() or 'capture' in tool_name.lower():
        return 'browser'
    elif 'command' in tool_name.lower() or 'executor' in tool_name.lower():
        return 'command'
    elif 'time' in tool_name.lower():
        return 'time'
    elif 'git' in tool_name.lower():
        return 'git'
    elif 'azure' in tool_name.lower():
        return 'azure'
    elif 'knowledge' in tool_name.lower():
        return 'knowledge'
    elif 'summarizer' in tool_name.lower():
        return 'summarizer'
    elif 'kusto' in tool_name.lower():
        return 'kusto'
    else:
        return 'other'


def generate_tool_specific_args(tool_name: str, input_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Generate tool-specific arguments based on tool name and schema."""
    category = get_tool_category(tool_name)

    # Base arguments from schema
    args = {}
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    # Add required arguments
    for prop_name, prop_schema in properties.items():
        if prop_name in required:
            prop_type = prop_schema.get("type", "string")
            default_value = prop_schema.get("default")
            enum_values = prop_schema.get("enum")

            if default_value is not None:
                args[prop_name] = default_value
            elif enum_values:
                args[prop_name] = enum_values[0]
            elif prop_type == "string":
                args[prop_name] = get_default_string_value(prop_name, category)
            elif prop_type == "integer":
                args[prop_name] = 1
            elif prop_type == "number":
                args[prop_name] = 1.0
            elif prop_type == "boolean":
                args[prop_name] = True
            elif prop_type == "array":
                args[prop_name] = []
            elif prop_type == "object":
                args[prop_name] = {}

    # Add common optional arguments that tools often expect
    if "operation" in properties and "operation" not in args:
        args["operation"] = get_default_operation(category)

    return args


def get_default_string_value(prop_name: str, category: str) -> str:
    """Get default string value based on property name and tool category."""
    if prop_name == "command":
        return "echo 'test'"
    elif prop_name == "url":
        return "https://example.com"
    elif prop_name == "operation":
        return get_default_operation(category)
    elif prop_name in ["repo_path", "path", "directory"]:
        return "/tmp/test"
    elif prop_name in ["organization", "org"]:
        return "test-org"
    elif prop_name in ["project", "proj"]:
        return "test-project"
    elif prop_name in ["query", "search"]:
        return "test query"
    elif prop_name in ["collection", "index"]:
        return "test-collection"
    elif prop_name in ["timezone", "tz"]:
        return "UTC"
    elif prop_name in ["token", "auth_token"]:
        return "test-token"
    else:
        return "test_value"


def get_default_operation(category: str) -> str:
    """Get default operation for a tool category."""
    operation_map = {
        'browser': 'get_page_html',
        'command': 'execute',
        'time': 'get_time',
        'git': 'status',
        'azure': 'list',
        'knowledge': 'search',
        'summarizer': 'summarize',
        'kusto': 'query'
    }
    return operation_map.get(category, 'test')


class ToolTestResult:
    """Class to store and analyze tool test results."""

    def __init__(self):
        self.results = []

    def add_result(self, tool_name: str, tool_class: str, test_type: str,
                   success: bool, error: Optional[str] = None, **kwargs):
        """Add a test result."""
        result = {
            'tool_name': tool_name,
            'tool_class': tool_class,
            'test_type': test_type,
            'success': success,
            'error': error,
            **kwargs
        }
        self.results.append(result)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of test results."""
        total = len(self.results)
        successful = len([r for r in self.results if r['success']])
        failed = total - successful

        # Group by test type
        by_test_type = {}
        for result in self.results:
            test_type = result['test_type']
            if test_type not in by_test_type:
                by_test_type[test_type] = {'total': 0, 'successful': 0, 'failed': 0}

            by_test_type[test_type]['total'] += 1
            if result['success']:
                by_test_type[test_type]['successful'] += 1
            else:
                by_test_type[test_type]['failed'] += 1

        # Group by tool category
        by_category = {}
        for result in self.results:
            tool_name = str(result['tool_name'])
            category = get_tool_category(tool_name)
            if category not in by_category:
                by_category[category] = {'total': 0, 'successful': 0, 'failed': 0}

            by_category[category]['total'] += 1
            if result['success']:
                by_category[category]['successful'] += 1
            else:
                by_category[category]['failed'] += 1

        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0,
            'by_test_type': by_test_type,
            'by_category': by_category,
            'failed_results': [r for r in self.results if not r['success']]
        }

    def print_summary(self, logger):
        """Print a detailed summary of test results."""
        summary = self.get_summary()

        logger.info("=" * 60)
        logger.info("COMPREHENSIVE CODE TOOLS TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total tests: {summary['total']}")
        logger.info(f"Successful: {summary['successful']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Success rate: {summary['success_rate']:.1%}")

        logger.info("\nResults by test type:")
        for test_type, stats in summary['by_test_type'].items():
            logger.info(f"  {test_type}: {stats['successful']}/{stats['total']} "
                       f"({stats['successful']/stats['total']:.1%})")

        logger.info("\nResults by tool category:")
        for category, stats in summary['by_category'].items():
            logger.info(f"  {category}: {stats['successful']}/{stats['total']} "
                       f"({stats['successful']/stats['total']:.1%})")

        if summary['failed_results']:
            logger.info(f"\nFailed tests ({len(summary['failed_results'])}):")
            for result in summary['failed_results']:
                logger.info(f"  - {result['tool_name']} ({result['test_type']}): {result['error']}")

        logger.info("=" * 60)
