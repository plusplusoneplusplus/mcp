"""Tests for the HTML to markdown converter."""

import pytest
from utils.html_to_markdown import html_to_markdown, extract_and_format_html


def test_html_to_markdown():
    """Test the HTML to markdown conversion."""
    html = "<html><body><h1>Test</h1><p>This is a test.</p></body></html>"
    markdown = html_to_markdown(html)
    assert markdown is not None
    assert "Test" in markdown
    assert "This is a test" in markdown


def test_extract_and_format_html():
    """Test the extract_and_format_html function."""
    html = "<html><body><h1>Test</h1><p>This is a test.</p></body></html>"
    result = extract_and_format_html(html)
    
    assert result["extraction_success"] is True
    assert result["original_size"] == len(html)
    assert result["extracted_size"] > 0
    assert "Test" in result["markdown"]
    assert "This is a test" in result["markdown"]


def test_extract_and_format_html_empty():
    """Test the extract_and_format_html function with empty HTML."""
    html = ""
    result = extract_and_format_html(html)
    
    assert result["extraction_success"] is False
    assert result["original_size"] == 0
    assert result["extracted_size"] == 0
    assert result["markdown"] == "" 