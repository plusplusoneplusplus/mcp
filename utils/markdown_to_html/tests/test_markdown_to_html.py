"""Tests for the markdown to HTML converter."""

import pytest
from utils.markdown_to_html import markdown_to_html, detect_and_convert_markdown
from utils.markdown_to_html.converter import is_markdown_content


class TestMarkdownToHtml:
    """Test the markdown_to_html function."""

    def test_empty_string(self):
        """Test conversion of empty string."""
        assert markdown_to_html("") == ""

    def test_simple_text(self):
        """Test conversion of simple text without markdown."""
        text = "This is just plain text."
        result = markdown_to_html(text)
        assert "<p>This is just plain text.</p>" in result

    def test_header_conversion(self):
        """Test conversion of markdown headers."""
        markdown = "# Header 1\n## Header 2\n### Header 3"
        result = markdown_to_html(markdown)
        assert "<h1>Header 1</h1>" in result
        assert "<h2>Header 2</h2>" in result
        assert "<h3>Header 3</h3>" in result

    def test_bold_italic_conversion(self):
        """Test conversion of bold and italic text."""
        markdown = "This is **bold** and this is *italic*."
        result = markdown_to_html(markdown)
        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result

    def test_list_conversion(self):
        """Test conversion of lists."""
        markdown = "- Item 1\n- Item 2\n- Item 3"
        result = markdown_to_html(markdown)
        assert "<ul>" in result
        assert "<li>Item 1</li>" in result
        assert "<li>Item 2</li>" in result
        assert "<li>Item 3</li>" in result

    def test_ordered_list_conversion(self):
        """Test conversion of ordered lists."""
        markdown = "1. First item\n2. Second item\n3. Third item"
        result = markdown_to_html(markdown)
        assert "<ol>" in result
        assert "<li>First item</li>" in result
        assert "<li>Second item</li>" in result
        assert "<li>Third item</li>" in result

    def test_code_block_conversion(self):
        """Test conversion of code blocks."""
        markdown = "```python\nprint('Hello, World!')\n```"
        result = markdown_to_html(markdown)
        assert "<pre><code" in result
        assert "print('Hello, World!')" in result

    def test_inline_code_conversion(self):
        """Test conversion of inline code."""
        markdown = "Use the `print()` function to output text."
        result = markdown_to_html(markdown)
        assert "<code>print()</code>" in result

    def test_link_conversion(self):
        """Test conversion of links."""
        markdown = "Visit [Google](https://www.google.com) for search."
        result = markdown_to_html(markdown)
        assert '<a href="https://www.google.com">Google</a>' in result

    def test_blockquote_conversion(self):
        """Test conversion of blockquotes."""
        markdown = "> This is a blockquote."
        result = markdown_to_html(markdown)
        assert "<blockquote>" in result
        assert "This is a blockquote." in result


class TestIsMarkdownContent:
    """Test the is_markdown_content function."""

    def test_empty_string(self):
        """Test detection of empty string."""
        assert is_markdown_content("") is False
        assert is_markdown_content("   ") is False

    def test_plain_text(self):
        """Test detection of plain text."""
        text = "This is just plain text without any markdown formatting."
        assert is_markdown_content(text) is False

    def test_header_detection(self):
        """Test detection of markdown headers."""
        assert is_markdown_content("# Header 1") is True
        assert is_markdown_content("## Header 2") is True
        assert is_markdown_content("### Header 3") is True

    def test_list_detection(self):
        """Test detection of markdown lists."""
        assert is_markdown_content("- Item 1\n- Item 2") is True
        assert is_markdown_content("* Item 1\n* Item 2") is True
        assert is_markdown_content("1. Item 1\n2. Item 2") is True

    def test_bold_italic_detection(self):
        """Test detection of bold and italic text."""
        assert is_markdown_content("This is **bold** text") is True
        assert is_markdown_content("This is *italic* text") is True

    def test_code_detection(self):
        """Test detection of code blocks and inline code."""
        assert is_markdown_content("```python\nprint('hello')\n```") is True
        assert is_markdown_content("Use `print()` function") is True

    def test_link_detection(self):
        """Test detection of markdown links."""
        assert is_markdown_content("Visit [Google](https://google.com)") is True
        assert is_markdown_content("![Image](image.png)") is True

    def test_blockquote_detection(self):
        """Test detection of blockquotes."""
        assert is_markdown_content("> This is a quote") is True

    def test_table_detection(self):
        """Test detection of markdown tables."""
        table = "| Column 1 | Column 2 |\n|----------|----------|\n| Data 1   | Data 2   |"
        assert is_markdown_content(table) is True

    def test_horizontal_rule_detection(self):
        """Test detection of horizontal rules."""
        assert is_markdown_content("---") is True
        assert is_markdown_content("===") is True

    def test_mixed_content(self):
        """Test detection of mixed markdown content."""
        mixed = "# Title\n\nThis is **bold** and this is *italic*.\n\n- Item 1\n- Item 2"
        assert is_markdown_content(mixed) is True

    def test_minimal_markdown(self):
        """Test detection of minimal markdown that should be detected."""
        # Single header should be detected
        assert is_markdown_content("# Just a header") is True
        # Code block should be detected
        assert is_markdown_content("```\ncode\n```") is True

    def test_false_positives(self):
        """Test cases that might look like markdown but aren't."""
        # Single asterisk without closing
        assert is_markdown_content("This * is not markdown") is False
        # Hash without space (not a header)
        assert is_markdown_content("#hashtag") is False


class TestDetectAndConvertMarkdown:
    """Test the detect_and_convert_markdown function."""

    def test_empty_string(self):
        """Test conversion of empty string."""
        assert detect_and_convert_markdown("") == ""
        assert detect_and_convert_markdown(None) is None

    def test_plain_text_unchanged(self):
        """Test that plain text is not converted."""
        text = "This is just plain text."
        assert detect_and_convert_markdown(text) == text

    def test_markdown_converted(self):
        """Test that markdown is converted to HTML."""
        markdown = "# Header\n\nThis is **bold** text."
        result = detect_and_convert_markdown(markdown)
        assert result != markdown  # Should be different (converted)
        assert "<h1>Header</h1>" in result
        assert "<strong>bold</strong>" in result

    def test_mixed_content_converted(self):
        """Test that mixed markdown content is converted."""
        markdown = "# Title\n\n- Item 1\n- Item 2\n\n```python\nprint('hello')\n```"
        result = detect_and_convert_markdown(markdown)
        assert result != markdown
        assert "<h1>Title</h1>" in result
        assert "<ul>" in result
        assert "<pre><code" in result

    def test_work_item_description_example(self):
        """Test a realistic work item description example."""
        description = """# Bug Report

## Description
The login functionality is **not working** properly.

## Steps to Reproduce
1. Navigate to login page
2. Enter valid credentials
3. Click login button

## Expected Result
User should be logged in successfully.

## Actual Result
Error message appears: `Invalid credentials`

## Additional Notes
- This affects all browsers
- Issue started after the latest deployment
"""
        result = detect_and_convert_markdown(description)
        assert result != description
        assert "<h1>Bug Report</h1>" in result
        assert "<h2>Description</h2>" in result
        assert "<strong>not working</strong>" in result
        assert "<ol>" in result  # Ordered list for steps
        assert "<code>Invalid credentials</code>" in result
