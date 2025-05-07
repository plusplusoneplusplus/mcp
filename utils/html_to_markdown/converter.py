"""Utility module for converting HTML content to markdown format."""

import trafilatura
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from markdownify import markdownify as md

EXTRACTION_MODE = "bs4"  # Options: 'bs4', 'trafilatura'

def html_to_markdown(
    html: str,
    include_links: bool = True,
    include_images: bool = True
) -> Optional[str]:
    """Convert HTML content to markdown format using the configured extraction mode.
    
    Args:
        html: The HTML content to convert
        include_links: Whether to include links in the extracted content (only for trafilatura)
        include_images: Whether to include image references in the extracted content (only for trafilatura)
        
    Returns:
        Extracted markdown text or None if extraction failed
    """
    if EXTRACTION_MODE == "trafilatura":
        return trafilatura.extract(
            html,
            output_format="markdown",
            include_links=include_links,
            include_images=include_images
        )
    elif EXTRACTION_MODE == "bs4":
        # Use BeautifulSoup to extract the main content, then markdownify
        soup = BeautifulSoup(html, "html.parser")
        # Try to extract <main> or <body> content, fallback to all HTML
        main_content = soup.find("main")
        if main_content is None:
            main_content = soup.body if soup.body else soup
        # Convert to markdown
        markdown = md(str(main_content), strip=['script', 'style'])
        return markdown
    else:
        raise ValueError(f"Unknown extraction mode: {EXTRACTION_MODE}")


def extract_and_format_html(
    html: str,
    include_links: bool = True,
    include_images: bool = True
) -> Dict[str, Any]:
    """Extract content from HTML and return formatted result with metadata.
    
    Args:
        html: The HTML content to extract from
        include_links: Whether to include links in the extracted content (only for trafilatura)
        include_images: Whether to include image references in the extracted content (only for trafilatura)
        
    Returns:
        Dictionary containing the extraction result and metadata
    """
    extracted_text = html_to_markdown(
        html,
        include_links=include_links,
        include_images=include_images
    )
    
    # If extraction failed, return an empty string
    if not extracted_text:
        extracted_text = ""
    
    return {
        "markdown": extracted_text,
        "extraction_success": bool(extracted_text),
        "original_size": len(html),
        "extracted_size": len(extracted_text)
    } 