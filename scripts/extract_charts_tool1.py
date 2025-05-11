#!/usr/bin/env python3
"""Command-line tool for extracting charts from dashboard images.

This script provides a simple command-line interface to extract individual charts
from dashboard screenshots or other images containing multiple charts or graphs.
"""

import argparse
import os
import sys
from pathlib import Path

from utils.chart_extractor import extract_charts


def get_default_output_dir():
    """Get default output directory relative to the script's location."""
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    return str(script_dir / ".extracted_charts")


def main():
    """Run the chart extraction tool from the command line."""
    default_output_dir = get_default_output_dir()

    parser = argparse.ArgumentParser(
        description="Extract individual charts from dashboard screenshots or images.",
        epilog="Example: python extract_charts.py dashboard.png -o extracted_charts",
    )
    parser.add_argument(
        "image_path",
        type=str,
        help="Path to the dashboard screenshot or image containing charts.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=default_output_dir,
        help=f"Directory to save the extracted charts. Default: {default_output_dir}",
    )
    parser.add_argument(
        "--min-height",
        type=int,
        default=100,
        help="Minimum height of a chart in pixels. Default: 100",
    )
    parser.add_argument(
        "--min-width",
        type=int,
        default=150,
        help="Minimum width of a chart in pixels. Default: 150",
    )
    parser.add_argument(
        "--edge-threshold1",
        type=int,
        default=50,
        help="First threshold for Canny edge detection. Default: 50",
    )
    parser.add_argument(
        "--edge-threshold2",
        type=int,
        default=150,
        help="Second threshold for Canny edge detection. Default: 150",
    )
    parser.add_argument(
        "--text-margin",
        type=int,
        default=40,
        help="Fallback margin if adaptive detection fails. Default: 40",
    )
    parser.add_argument(
        "--no-adaptive",
        action="store_true",
        help="Disable adaptive boundary detection and use fixed margins only.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save intermediate processing images for debugging.",
    )

    args = parser.parse_args()

    try:
        print(f"Processing image: {args.image_path}")
        print(f"Saving extracted charts to: {args.output_dir}")

        # Use adaptive boundary detection by default, unless explicitly disabled
        adaptive_boundary = not args.no_adaptive

        if adaptive_boundary:
            print("Using adaptive boundary detection to include labels and text")
        else:
            print(f"Using fixed margin of {args.text_margin} pixels")

        extracted_paths = extract_charts(
            args.image_path,
            args.output_dir,
            min_chart_height=args.min_height,
            min_chart_width=args.min_width,
            edge_detection_threshold1=args.edge_threshold1,
            edge_detection_threshold2=args.edge_threshold2,
            text_margin=args.text_margin,
            adaptive_boundary=adaptive_boundary,
            debug=args.debug,
        )

        print(f"\nSuccessfully extracted {len(extracted_paths)} charts:")
        for i, path in enumerate(extracted_paths, 1):
            print(f"  {i}. {path}")

        if args.debug:
            print("\nDebug images saved to output directory:")
            print("  - debug_edges.png: Edge detection result")
            print("  - debug_text_regions.png: Detected text regions")
            print(
                "  - debug_detected_charts.png: Original image with detected charts outlined"
            )

        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(
            "Please check that the image file exists and the path is correct.",
            file=sys.stderr,
        )
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
