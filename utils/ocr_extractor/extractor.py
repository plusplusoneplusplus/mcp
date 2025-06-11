"""
OCR extraction utility using EasyOCR.
"""

from pathlib import Path
from typing import List
from PIL import Image


def extract_text_from_image(image_path: Path) -> List[str]:
    """
    Extract text strings from an image file using EasyOCR.

    Args:
        image_path (Path): Path to the image file.

    Returns:
        List[str]: List of extracted text strings.
    """

    try:
        import easyocr
    except ImportError:
        raise ImportError(
            "EasyOCR is not installed. Please run: pip install easyocr pillow"
        )

    reader = easyocr.Reader(["en"], gpu=False)
    results = reader.readtext(str(image_path))
    return [text for _, text, _ in results]
