"""Utility module for converting HTML content to markdown format."""

import trafilatura
from typing import Optional, Dict, Any


def html_to_markdown(
    html: str,
    include_links: bool = True,
    include_images: bool = True
) -> Optional[str]:
    """Convert HTML content to markdown format using trafilatura.
    
    Args:
        html: The HTML content to convert
        include_links: Whether to include links in the extracted content
        include_images: Whether to include image references in the extracted content
        
    Returns:
        Extracted markdown text or None if extraction failed
    """
    return trafilatura.extract(
        html,
        output_format="markdown",
        include_links=include_links,
        include_images=include_images
    )


def extract_and_format_html(
    html: str,
    include_links: bool = True,
    include_images: bool = True
) -> Dict[str, Any]:
    """Extract content from HTML and return formatted result with metadata.
    
    Args:
        html: The HTML content to extract from
        include_links: Whether to include links in the extracted content
        include_images: Whether to include image references in the extracted content
        
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