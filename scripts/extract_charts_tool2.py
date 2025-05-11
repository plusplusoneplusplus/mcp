import cv2
import numpy as np
import pathlib
import argparse


def extract_charts(
    input_image,
    output_dir,
    canny_low=30,
    canny_high=120,
    min_width=250,
    max_width=2000,
    min_height=120,
    verbose=False,
):
    img = cv2.imread(input_image)
    if img is None:
        raise FileNotFoundError(f"Could not read image file: {input_image}")

    if verbose:
        print(f"Image dimensions: {img.shape[1]}x{img.shape[0]}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # highlight panel borders (light gray on dark bg)
    edges = cv2.Canny(gray, canny_low, canny_high)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.dilate(edges, kernel, 2)

    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if verbose:
        print(f"Found {len(cnts)} contours in total")

    out = pathlib.Path(output_dir)
    out.mkdir(exist_ok=True)

    chart_count = 0
    filtered_count = 0
    for i, c in enumerate(cnts):
        x, y, w, h = cv2.boundingRect(c)
        if verbose:
            print(f"Contour {i}: size {w}x{h} at position ({x}, {y})")

        if (
            min_width < w and (max_width == 0 or w < max_width) and h > min_height
        ):  # heuristics for Grafana tiles
            cv2.imwrite(str(out / f"chart_{i}.png"), img[y : y + h, x : x + w])
            chart_count += 1
        else:
            filtered_count += 1

    if verbose:
        print(f"Filtered out {filtered_count} contours based on size constraints")

    return chart_count


def main():
    parser = argparse.ArgumentParser(
        description="Extract charts from a Grafana screenshot"
    )
    parser.add_argument("--input", "-i", required=True, help="Path to the input image")
    parser.add_argument(
        "--output", "-o", default="charts", help="Output directory for extracted charts"
    )
    parser.add_argument(
        "--canny-low",
        type=int,
        default=30,
        help="Lower threshold for Canny edge detection",
    )
    parser.add_argument(
        "--canny-high",
        type=int,
        default=120,
        help="Upper threshold for Canny edge detection",
    )
    parser.add_argument(
        "--min-width", type=int, default=250, help="Minimum width of charts to extract"
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=2000,
        help="Maximum width of charts to extract (0 for no limit)",
    )
    parser.add_argument(
        "--min-height",
        type=int,
        default=120,
        help="Minimum height of charts to extract",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    try:
        chart_count = extract_charts(
            args.input,
            args.output,
            args.canny_low,
            args.canny_high,
            args.min_width,
            args.max_width,
            args.min_height,
            args.verbose,
        )
        print(f"Successfully extracted {chart_count} charts to {args.output}/")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
