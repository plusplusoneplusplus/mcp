"""Chart extractor functionality.

This module contains functions to extract individual charts from a dashboard screenshot.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image


def extract_charts(
    image_path: Union[str, Path],
    output_dir: Union[str, Path],
    min_chart_height: int = 100,
    min_chart_width: int = 150,
    edge_detection_threshold1: int = 50,
    edge_detection_threshold2: int = 150,
    text_margin: int = 40,  # Fallback margin if adaptive detection fails
    adaptive_boundary: bool = True,  # Use adaptive boundary detection
    debug: bool = False,
) -> List[str]:
    """Extract individual charts from a dashboard screenshot.

    Args:
        image_path: Path to the dashboard screenshot.
        output_dir: Directory to save the extracted charts.
        min_chart_height: Minimum height of a chart in pixels.
        min_chart_width: Minimum width of a chart in pixels.
        edge_detection_threshold1: First threshold for Canny edge detection.
        edge_detection_threshold2: Second threshold for Canny edge detection.
        text_margin: Fallback margin if adaptive detection fails.
        adaptive_boundary: Whether to use adaptive boundary detection.
        debug: Whether to save intermediate processing images for debugging.

    Returns:
        List of file paths to the saved chart images.
    """
    # Convert input paths to Path objects
    image_path = Path(image_path)
    output_dir = Path(output_dir)

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load the image
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Could not load image from {image_path}")

    # Convert to grayscale for better processing
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Detect edges
    edges = cv2.Canny(blurred, edge_detection_threshold1, edge_detection_threshold2)

    if debug:
        cv2.imwrite(str(output_dir / "debug_edges.png"), edges)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours to find chart boundaries
    chart_contours = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > min_chart_width and h > min_chart_height:
            chart_contours.append((x, y, w, h))

    # Merge overlapping boxes
    merged_charts = _merge_overlapping_boxes(chart_contours)

    # Prepare for text and axis detection
    if adaptive_boundary:
        # Detect text regions in the entire image
        global_text_regions = _detect_text_regions(gray)

        if debug:
            debug_img = image.copy()
            for x, y, w, h in global_text_regions:
                cv2.rectangle(debug_img, (x, y), (x + w, y + h), (255, 0, 255), 1)
            cv2.imwrite(str(output_dir / "debug_text_regions.png"), debug_img)

    # Extract and save each chart
    saved_paths = []
    for i, (x, y, w, h) in enumerate(merged_charts):
        if adaptive_boundary:
            # Get adaptive boundaries that include relevant text and axes
            x_min, y_min, w_ex, h_ex, debug_info = _get_adaptive_chart_boundaries(
                gray,
                global_text_regions,
                x,
                y,
                w,
                h,
                image.shape[1],  # image width
                image.shape[0],  # image height
                text_margin,  # fallback margin
                debug=debug,
            )
        else:
            # Use fixed margin if adaptive detection is disabled
            x_min = max(0, x - text_margin)
            y_min = max(0, y - text_margin)
            w_ex = min(image.shape[1] - x_min, w + 2 * text_margin)
            h_ex = min(image.shape[0] - y_min, h + 2 * text_margin)
            debug_info = None

        # Ensure we have integer bounds
        x_min, y_min, w_ex, h_ex = int(x_min), int(y_min), int(w_ex), int(h_ex)

        # Extract the chart region with the adaptive boundaries
        chart_img = image[y_min : y_min + h_ex, x_min : x_min + w_ex]

        # Convert from BGR to RGB (OpenCV uses BGR, but most image libraries use RGB)
        chart_img_rgb = cv2.cvtColor(chart_img, cv2.COLOR_BGR2RGB)

        # Save the chart
        chart_filename = f"chart_{i+1}.png"
        chart_path = output_dir / chart_filename
        pil_img = Image.fromarray(chart_img_rgb)
        pil_img.save(str(chart_path))

        saved_paths.append(str(chart_path))

        if debug:
            # Draw the original chart boundaries
            debug_img = image.copy()
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 1)  # Red

            # Draw the adaptive boundaries
            cv2.rectangle(
                debug_img,
                (x_min, y_min),
                (x_min + w_ex, y_min + h_ex),
                (0, 255, 0),  # Green
                2,
            )

            # If we have debug info from adaptive boundary detection
            if debug_info and adaptive_boundary:
                relevant_text = debug_info.get("relevant_text", [])

                # Draw each type of text with different colors
                for tx, ty, tw, th, text_type in relevant_text:
                    color = (0, 255, 255)  # Yellow default

                    if text_type == "title":
                        color = (255, 0, 0)  # Blue
                    elif text_type == "x-axis":
                        color = (0, 165, 255)  # Orange
                    elif text_type == "y-axis":
                        color = (0, 255, 0)  # Green
                    elif text_type == "y-axis2":
                        color = (0, 128, 255)  # Light Orange
                    elif text_type == "legend":
                        color = (128, 0, 128)  # Purple

                    cv2.rectangle(debug_img, (tx, ty), (tx + tw, ty + th), color, 1)

                    # Add text type label
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    cv2.putText(
                        debug_img,
                        text_type,
                        (tx, ty - 2),
                        font,
                        0.4,
                        color,
                        1,
                        cv2.LINE_AA,
                    )

            # Save the debug image for this chart
            debug_chart_path = output_dir / f"debug_chart_{i+1}.png"
            cv2.imwrite(str(debug_chart_path), debug_img)

    if debug:
        # Save the image with rectangles around the detected charts
        debug_image_path = output_dir / "debug_detected_charts.png"
        debug_img = image.copy()

        for i, (x, y, w, h) in enumerate(merged_charts):
            # Draw chart index
            cv2.putText(
                debug_img,
                f"Chart {i+1}",
                (x + 5, y + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
                cv2.LINE_AA,
            )

            # Draw original boundary
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 2)  # Red

        cv2.imwrite(str(debug_image_path), debug_img)

    return saved_paths


def _get_adaptive_chart_boundaries(
    gray_image,
    text_regions,
    chart_x,
    chart_y,
    chart_w,
    chart_h,
    img_width,
    img_height,
    fallback_margin,
    debug=False,
):
    """Determine adaptive boundaries for a chart by analyzing text regions and axes.

    Args:
        gray_image: Grayscale version of the original image.
        text_regions: List of detected text regions as (x, y, w, h).
        chart_x: X coordinate of the detected chart.
        chart_y: Y coordinate of the detected chart.
        chart_w: Width of the detected chart.
        chart_h: Height of the detected chart.
        img_width: Width of the original image.
        img_height: Height of the original image.
        fallback_margin: Margin to use if adaptive detection fails.
        debug: Whether to collect debug info.

    Returns:
        Tuple of (x, y, width, height, debug_info) for the expanded chart boundaries.
    """
    # Define a more restricted expansion zone around the chart
    # This controls how far from the chart we look for related text
    expansion_zone = 60  # Further reduced from 80 to 60 pixels

    # Initial boundary is just the chart itself
    x_min = chart_x
    y_min = chart_y
    x_max = chart_x + chart_w
    y_max = chart_y + chart_h

    # Track relevant text by position (title, x-axis, y-axis, etc.)
    relevant_text = []

    # Define chart quadrants for text categorization
    chart_center_x = chart_x + chart_w / 2
    chart_center_y = chart_y + chart_h / 2

    # Debug info
    debug_info = {
        "chart_bounds": (chart_x, chart_y, chart_w, chart_h),
        "expansion_zone": expansion_zone,
        "relevant_text": [],
        "skipped_text": [],
        "right_side_limit": False,
        "left_side_limit": False,
    }

    # Detect if this chart likely has multiple Y-axes
    # Charts with multiple Y-axes typically have text on both the left and right sides
    left_side_text = [
        region
        for region in text_regions
        if region[0] < chart_x
        and region[0] + region[2] >= chart_x - expansion_zone
        and region[1] + region[3] > chart_y
        and region[1] < chart_y + chart_h
    ]

    right_side_text = [
        region
        for region in text_regions
        if region[0] > chart_x + chart_w
        and region[0] <= chart_x + chart_w + expansion_zone
        and region[1] + region[3] > chart_y
        and region[1] < chart_y + chart_h
    ]

    has_multiple_y_axes = len(left_side_text) > 0 and len(right_side_text) > 0

    # For charts with multiple Y-axes, be even more selective about what text to include
    # This is especially important for dashboard layouts with side panels
    if has_multiple_y_axes:
        expansion_zone = 50  # Be even more restrictive for multi-axis charts

    for tx, ty, tw, th in text_regions:
        # Skip very large text blocks (likely not chart labels but panels/descriptions)
        if tw > chart_w * 0.6 and th > 20:  # More restrictive size filter (0.8 -> 0.6)
            if debug:
                debug_info["skipped_text"].append((tx, ty, tw, th, "too_large"))
            continue

        # Skip text blocks that are too far away (in a different panel)
        # This helps avoid including text from adjacent panels or sections
        if tx > chart_x + chart_w + expansion_zone:
            if debug:
                debug_info["skipped_text"].append((tx, ty, tw, th, "too_far_right"))
            continue

        # For charts with multiple Y-axes, be extra careful about text on the right side
        # This is where side panels with descriptions often appear in dashboards
        if has_multiple_y_axes and tx > chart_x + chart_w + expansion_zone * 0.7:
            if debug:
                debug_info["skipped_text"].append(
                    (tx, ty, tw, th, "outside_right_y_axis_range")
                )
            continue

        # Calculate text center
        text_center_x = tx + tw / 2
        text_center_y = ty + th / 2

        # Check if text is near the chart (within expansion zone)
        if (
            tx + tw >= chart_x - expansion_zone
            and tx <= chart_x + chart_w + expansion_zone
            and ty + th >= chart_y - expansion_zone
            and ty <= chart_y + chart_h + expansion_zone
        ):

            # Text categorization with stricter criteria

            # Title: Above the chart, horizontally centered
            is_title = (
                abs(text_center_x - chart_center_x)
                < chart_w * 0.4  # Centered with 40% tolerance
                and ty < chart_y
                and ty + th >= chart_y - expansion_zone * 0.8
            )  # Closer to chart top

            # X-axis label: Below the chart, horizontally aligned
            is_x_axis_label = (
                ty >= chart_y + chart_h - 10
                and ty
                <= chart_y + chart_h + expansion_zone * 0.6  # Reduced vertical range
                and tx + tw > chart_x
                and tx < chart_x + chart_w
            )  # Must overlap horizontally

            # Y-axis label: Left of the chart, vertically aligned
            is_y_axis_label = (
                tx < chart_x
                and tx + tw
                >= chart_x - expansion_zone * 0.7  # Reduced horizontal range
                and ty + th > chart_y
                and ty < chart_y + chart_h
            )  # Must overlap vertically

            # Y-axis secondary label: Right of the chart, vertically aligned
            is_y_axis_secondary = (
                tx > chart_x + chart_w - 5
                and tx
                <= chart_x + chart_w + expansion_zone * 0.7  # Reduced horizontal range
                and ty + th > chart_y
                and ty < chart_y + chart_h
            )  # Must overlap vertically

            # Legend: Below or near the chart, not overlapping with axis labels
            is_legend = (
                not is_title
                and not is_x_axis_label
                and not is_y_axis_label
                and not is_y_axis_secondary
                and tx + tw >= chart_x
                and tx <= chart_x + chart_w
                and ty >= chart_y
                and ty <= chart_y + chart_h + expansion_zone * 0.5
            )

            # If this text appears to be related to the chart, include it
            if (
                is_title
                or is_x_axis_label
                or is_y_axis_label
                or is_y_axis_secondary
                or is_legend
            ):
                text_type = (
                    "title"
                    if is_title
                    else (
                        "x-axis"
                        if is_x_axis_label
                        else (
                            "y-axis"
                            if is_y_axis_label
                            else "y-axis2" if is_y_axis_secondary else "legend"
                        )
                    )
                )

                relevant_text.append((tx, ty, tw, th, text_type))

                if debug:
                    debug_info["relevant_text"].append((tx, ty, tw, th, text_type))

                # Update boundaries to include this text
                x_min = min(x_min, tx)
                y_min = min(y_min, ty)
                x_max = max(x_max, tx + tw)
                y_max = max(y_max, ty + th)
            elif debug:
                debug_info["skipped_text"].append((tx, ty, tw, th, "not_relevant"))
        elif debug:
            debug_info["skipped_text"].append(
                (tx, ty, tw, th, "outside_expansion_zone")
            )

    # If no relevant text was found, fall back to a fixed margin
    if not relevant_text:
        x_min = max(0, chart_x - fallback_margin)
        y_min = max(0, chart_y - fallback_margin)
        x_max = min(img_width, chart_x + chart_w + fallback_margin)
        y_max = min(img_height, chart_y + chart_h + fallback_margin)

        if debug:
            debug_info["using_fallback"] = True
    else:
        # Add a small padding around the expanded boundaries
        padding = 10
        x_min = max(0, x_min - padding)
        y_min = max(0, y_min - padding)
        x_max = min(img_width, x_max + padding)
        y_max = min(img_height, y_max + padding)

        # Apply some restrictions to avoid overly large boundaries

        # Limit horizontal expansion (for wide dashboards with side panels)
        if x_max - x_min > chart_w * 1.8:  # Reduced from 2.0 to 1.8
            # If we're expanding too much horizontally, restrict it
            # This helps with dashboards that have info panels on the sides
            right_expansion = x_max - (chart_x + chart_w)
            left_expansion = chart_x - x_min

            # If right expansion is very large, restrict it
            if right_expansion > chart_w * 0.6:  # Reduced from 0.8 to 0.6
                x_max = min(
                    x_max, chart_x + chart_w + chart_w * 0.4
                )  # Reduced from 0.5 to 0.4
                if debug:
                    debug_info["right_side_limit"] = True

            # If left expansion is very large, restrict it
            if left_expansion > chart_w * 0.6:  # Reduced from 0.8 to 0.6
                x_min = max(x_min, chart_x - chart_w * 0.4)  # Reduced from 0.5 to 0.4
                if debug:
                    debug_info["left_side_limit"] = True

        # Special handling for multi-axis charts
        if has_multiple_y_axes:
            # For charts with multiple Y-axes, be more aggressive about limiting expansion
            # particularly on the right side where dashboard info panels often appear
            right_expansion = x_max - (chart_x + chart_w)
            if right_expansion > chart_w * 0.3:  # Very strict limit
                x_max = min(x_max, chart_x + chart_w + chart_w * 0.3)
                if debug:
                    debug_info["multi_axis_right_limit"] = True

    # Calculate final width and height
    final_width = x_max - x_min
    final_height = y_max - y_min

    if debug:
        debug_info["final_bounds"] = (x_min, y_min, final_width, final_height)
        debug_info["has_multiple_y_axes"] = has_multiple_y_axes

    return x_min, y_min, final_width, final_height, debug_info if debug else None


def _detect_text_regions(gray_image):
    """Detect regions that likely contain text in the image.

    This function uses various image processing techniques to identify
    areas that are likely to contain text, such as labels, titles, and legends.

    Args:
        gray_image: Grayscale image to analyze.

    Returns:
        List of bounding rectangles for text regions as (x, y, w, h).
    """
    # Apply adaptive thresholding to better isolate text
    binary = cv2.adaptiveThreshold(
        gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

    # Create horizontal and vertical kernels for morphological operations
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 10))

    # Remove horizontal and vertical lines (often part of charts, not text)
    horizontal_lines = cv2.morphologyEx(
        binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=1
    )
    vertical_lines = cv2.morphologyEx(
        binary, cv2.MORPH_OPEN, vertical_kernel, iterations=1
    )
    grid_mask = cv2.bitwise_or(horizontal_lines, vertical_lines)
    text_only = cv2.bitwise_and(binary, cv2.bitwise_not(grid_mask))

    # Define a kernel for connecting text characters
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    connected = cv2.morphologyEx(text_only, cv2.MORPH_CLOSE, kernel)

    # Find contours of connected components
    contours, _ = cv2.findContours(
        connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    # Filter contours to find potential text regions
    text_regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        # Filter based on typical text characteristics
        if h > 5 and w > 5 and 0.1 < w / h < 15:
            # Compute the density of the contour area
            roi = connected[y : y + h, x : x + w]
            pixel_density = cv2.countNonZero(roi) / (w * h)

            # Text typically has a certain density of pixels
            if 0.1 < pixel_density < 0.95:
                text_regions.append((x, y, w, h))

    # Merge nearby text regions that likely belong together
    return _merge_nearby_text_regions(text_regions)


def _merge_nearby_text_regions(regions, distance_threshold=15):
    """Merge text regions that are close to each other and likely belong together.

    Args:
        regions: List of text regions as (x, y, w, h).
        distance_threshold: Maximum distance between regions to merge.

    Returns:
        List of merged text regions.
    """
    if not regions:
        return []

    # Convert (x, y, w, h) to (x1, y1, x2, y2) for easier calculations
    rects = [(x, y, x + w, y + h) for x, y, w, h in regions]

    # Sort by y-coordinate (vertical position) to help with line-based grouping
    rects.sort(key=lambda r: r[1])

    merged = []
    current_group = [rects[0]]

    for i in range(1, len(rects)):
        current_rect = rects[i]
        prev_rect = current_group[-1]

        # Check if current rectangle is close to the previous one
        # (either horizontally aligned or vertically close)
        horizontally_aligned = abs(current_rect[1] - prev_rect[1]) < distance_threshold
        vertically_close = abs(current_rect[1] - prev_rect[3]) < distance_threshold
        horizontally_close = (current_rect[0] - prev_rect[2]) < distance_threshold

        if (horizontally_aligned or vertically_close) and horizontally_close:
            # Merge with current group
            current_group.append(current_rect)
        else:
            # Finish the current group and start a new one
            x1 = min(r[0] for r in current_group)
            y1 = min(r[1] for r in current_group)
            x2 = max(r[2] for r in current_group)
            y2 = max(r[3] for r in current_group)
            merged.append((x1, y1, x2 - x1, y2 - y1))
            current_group = [current_rect]

    # Add the last group
    if current_group:
        x1 = min(r[0] for r in current_group)
        y1 = min(r[1] for r in current_group)
        x2 = max(r[2] for r in current_group)
        y2 = max(r[3] for r in current_group)
        merged.append((x1, y1, x2 - x1, y2 - y1))

    return merged


def _merge_overlapping_boxes(
    boxes: List[Tuple[int, int, int, int]], overlap_threshold: float = 0.3
) -> List[Tuple[int, int, int, int]]:
    """Merge overlapping bounding boxes.

    Args:
        boxes: List of bounding boxes as (x, y, width, height).
        overlap_threshold: Threshold for considering boxes as overlapping.

    Returns:
        List of merged bounding boxes as (x, y, width, height).
    """
    if not boxes:
        return []

    # Convert (x, y, w, h) to (x1, y1, x2, y2) for easier overlap calculation
    boxes_xyxy = [(x, y, x + w, y + h) for x, y, w, h in boxes]

    # Sort boxes by area in descending order
    boxes_xyxy.sort(key=lambda box: (box[2] - box[0]) * (box[3] - box[1]), reverse=True)

    merged_boxes = []
    while boxes_xyxy:
        current_box = boxes_xyxy.pop(0)

        i = 0
        while i < len(boxes_xyxy):
            if _boxes_overlap(current_box, boxes_xyxy[i], overlap_threshold):
                # Merge the boxes
                current_box = _merge_boxes(current_box, boxes_xyxy.pop(i))
            else:
                i += 1

        merged_boxes.append(current_box)

    # Convert back to (x, y, w, h) format
    return [(x1, y1, x2 - x1, y2 - y1) for x1, y1, x2, y2 in merged_boxes]


def _boxes_overlap(
    box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int], threshold: float
) -> bool:
    """Check if two boxes overlap by more than the threshold.

    Args:
        box1: First box in (x1, y1, x2, y2) format.
        box2: Second box in (x1, y1, x2, y2) format.
        threshold: Overlap threshold.

    Returns:
        True if boxes overlap by more than the threshold.
    """
    # Calculate intersection area
    x_left = max(box1[0], box2[0])
    y_top = max(box1[1], box2[1])
    x_right = min(box1[2], box2[2])
    y_bottom = min(box1[3], box2[3])

    if x_right < x_left or y_bottom < y_top:
        return False

    intersection_area = (x_right - x_left) * (y_bottom - y_top)

    # Calculate areas of both boxes
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])

    # Calculate overlap ratio
    smaller_area = min(box1_area, box2_area)
    overlap_ratio = intersection_area / smaller_area if smaller_area > 0 else 0

    return overlap_ratio > threshold


def _merge_boxes(
    box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]
) -> Tuple[int, int, int, int]:
    """Merge two bounding boxes.

    Args:
        box1: First box in (x1, y1, x2, y2) format.
        box2: Second box in (x1, y1, x2, y2) format.

    Returns:
        Merged box in (x1, y1, x2, y2) format.
    """
    x1 = min(box1[0], box2[0])
    y1 = min(box1[1], box2[1])
    x2 = max(box1[2], box2[2])
    y2 = max(box1[3], box2[3])

    return (x1, y1, x2, y2)
