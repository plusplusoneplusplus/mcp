#!/usr/bin/env python3
"""
A fast, high-performance CLI tool to extract strings (text) from an image using EasyOCR.
Usage:
    python extract_text_from_image.py /path/to/image.png

Requires: easyocr, pillow
Install with: pip install easyocr pillow
"""
import sys
import argparse
from pathlib import Path

from utils.ocr_extractor import extract_text_from_image
from PIL import Image


def main():
    parser = argparse.ArgumentParser(
        description="Extract text from an image using EasyOCR."
    )
    parser.add_argument("image_path", type=Path, help="Path to the image file.")
    args = parser.parse_args()

    if not args.image_path.exists():
        print(f"Image file does not exist: {args.image_path}")
        sys.exit(1)

    try:
        # Check if image can be opened
        Image.open(args.image_path)
    except Exception as e:
        print(f"Error opening image: {e}")
        sys.exit(1)

    print(f"Extracting text from: {args.image_path}")
    texts = extract_text_from_image(args.image_path)
    if texts:
        print("\n".join(texts))
    else:
        print("No text found in the image.")


if __name__ == "__main__":
    main()
