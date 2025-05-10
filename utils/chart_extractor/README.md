## Chart Extraction

The MCP project includes functionality for extracting individual charts from dashboard screenshots (particularly Grafana dashboards).

### Methodology

The chart extraction process works through the following steps:

1. **Image Pre-processing**:
   - Convert image to grayscale
   - Apply Gaussian blur to reduce noise
   - Detect edges using Canny edge detection

2. **Chart Detection**:
   - Identify contours in the edge-detected image
   - Filter contours based on minimum width and height thresholds
   - Merge overlapping contours that likely belong to the same chart

3. **Adaptive Boundary Detection**:
   - Detect text regions (axis labels, titles, legends) around each chart
   - Analyze and categorize text elements based on their position relative to the chart:
     - Title: positioned above the chart
     - X-axis labels: positioned below the chart
     - Y-axis labels: positioned to the left/right of the chart
     - Legends: positioned near the chart but not overlapping with axis labels
   - Expand chart boundaries to include relevant text elements
   - Apply adaptive boundary detection to handle charts with multiple Y-axes

4. **Chart Extraction and Output**:
   - Extract each chart with its labels and relevant text
   - Save each chart as a separate image

This approach ensures that charts are extracted not only with their visual elements but also with contextual information like axis labels and titles, making them more useful and interpretable.

### Usage

The chart extraction functionality can be accessed through the command-line interface:

```bash
python scripts/extract_charts.py dashboard.png -o extracted_charts
```

See `scripts/extract_charts.py --help` for additional options and parameters.