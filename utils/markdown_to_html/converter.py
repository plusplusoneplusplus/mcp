"""Utility module for converting markdown content to HTML format."""

import re
import mistune
from typing import Optional


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown text to HTML.

    Args:
        markdown_text: The markdown content to convert

    Returns:
        HTML-formatted string
    """
    if not markdown_text:
        return ""

    # Create a mistune renderer and convert markdown to HTML
    return mistune.html(markdown_text)


def is_markdown_content(text: str) -> bool:
    """Detect if text content appears to be markdown.

    This function looks for common markdown patterns to determine
    if the content is likely markdown format.

    Args:
        text: Text content to analyze

    Returns:
        True if content appears to be markdown, False otherwise
    """
    if not text or not text.strip():
        return False

    # Common markdown patterns to look for
    markdown_patterns = [
        r'^#{1,6}\s+',  # Headers (# ## ### etc.)
        r'^\*\s+',      # Unordered list with *
        r'^-\s+',       # Unordered list with -
        r'^\+\s+',      # Unordered list with +
        r'^\d+\.\s+',   # Ordered list (1. 2. etc.)
        r'\*\*.*?\*\*', # Bold text **text**
        r'\*.*?\*',     # Italic text *text*
        r'`.*?`',       # Inline code `code`
        r'^```',        # Code blocks ```
        r'^\>',         # Blockquotes >
        r'\[.*?\]\(.*?\)', # Links [text](url)
        r'!\[.*?\]\(.*?\)', # Images ![alt](url)
        r'^\|.*\|',     # Tables |col1|col2|
        r'^---+$',      # Horizontal rules ---
        r'^===+$',      # Horizontal rules ===
    ]

    # Count how many markdown patterns are found
    pattern_matches = 0
    lines = text.split('\n')

    for pattern in markdown_patterns:
        if re.search(pattern, text, re.MULTILINE):
            pattern_matches += 1

    # Also check for multiple lines with markdown-like formatting
    markdown_line_count = 0
    for line in lines:
        line = line.strip()
        if line:
            for pattern in markdown_patterns:
                if re.match(pattern, line):
                    markdown_line_count += 1
                    break

    # Consider it markdown if:
    # 1. At least 1 markdown pattern is found (more permissive), OR
    # 2. At least 20% of non-empty lines have markdown formatting, OR
    # 3. Contains code blocks (strong indicator), OR
    # 4. Contains inline code, links, or bold/italic text
    non_empty_lines = len([line for line in lines if line.strip()])

    # Strong indicators that should trigger markdown detection
    strong_indicators = [
        r'^```',        # Code blocks
        r'`.*?`',       # Inline code
        r'\[.*?\]\(.*?\)', # Links
        r'!\[.*?\]\(.*?\)', # Images
        r'\*\*.*?\*\*', # Bold text
        r'^#{1,6}\s+',  # Headers
    ]

    # Check for strong indicators
    for indicator in strong_indicators:
        if re.search(indicator, text, re.MULTILINE):
            return True

    # Check for italic text (but be more careful to avoid false positives)
    italic_matches = re.findall(r'\*([^*\s][^*]*[^*\s])\*', text)
    if italic_matches and len(italic_matches) > 0:
        return True

    # If we have multiple patterns or significant markdown formatting
    if pattern_matches >= 1:
        return True

    if non_empty_lines > 0 and (markdown_line_count / non_empty_lines) >= 0.2:
        return True

    return False


def detect_and_convert_markdown(text: str) -> str:
    """Detect if text is markdown and convert to HTML if it is.

    Args:
        text: Text content that might be markdown

    Returns:
        HTML if input was markdown, otherwise returns original text
    """
    if not text:
        return text

    if is_markdown_content(text):
        return markdown_to_html(text)

    return text
