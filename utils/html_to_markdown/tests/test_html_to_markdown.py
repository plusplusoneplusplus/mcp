"""Tests for the HTML to markdown converter."""

import pytest
from utils.html_to_markdown import html_to_markdown, extract_and_format_html
import utils.html_to_markdown.converter as converter


@pytest.mark.parametrize("mode", ["bs4", "trafilatura"])
def test_html_to_markdown(mode):
    """Test the HTML to markdown conversion."""
    original_mode = converter.EXTRACTION_MODE
    converter.EXTRACTION_MODE = mode
    try:
        html = "<html><body><h1>Test</h1><p>This is a test.</p></body></html>"
        markdown = html_to_markdown(html)
        assert markdown is not None
        assert "Test" in markdown
        assert "This is a test" in markdown
    finally:
        converter.EXTRACTION_MODE = original_mode


@pytest.mark.parametrize("mode", ["bs4", "trafilatura"])
def test_extract_and_format_html(mode):
    """Test the extract_and_format_html function."""
    original_mode = converter.EXTRACTION_MODE
    converter.EXTRACTION_MODE = mode
    try:
        html = "<html><body><h1>Test</h1><p>This is a test.</p></body></html>"
        result = extract_and_format_html(html)

        assert result["extraction_success"] is True
        assert result["original_size"] == len(html)
        assert result["extracted_size"] > 0
        assert "Test" in result["markdown"]
        assert "This is a test" in result["markdown"]
    finally:
        converter.EXTRACTION_MODE = original_mode


@pytest.mark.parametrize("mode", ["bs4", "trafilatura"])
def test_extract_and_format_html_empty(mode):
    """Test the extract_and_format_html function with empty HTML."""
    original_mode = converter.EXTRACTION_MODE
    converter.EXTRACTION_MODE = mode
    try:
        html = ""
        result = extract_and_format_html(html)

        assert result["extraction_success"] is False
        assert result["original_size"] == 0
        assert result["extracted_size"] == 0
        assert result["markdown"] == ""
    finally:
        converter.EXTRACTION_MODE = original_mode
