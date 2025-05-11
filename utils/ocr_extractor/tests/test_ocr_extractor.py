import os
from pathlib import Path
from utils.ocr_extractor import extract_text_from_image

def test_extract_text_from_sample_chart():
    # Use the provided sample chart image
    img_path = Path('assets/stacked-lines-chart.png')
    assert img_path.exists(), f"Test image not found: {img_path}"
    texts = extract_text_from_image(img_path)
    # The output should be a non-empty list of strings (if any text is present)
    assert isinstance(texts, list)
    assert all(isinstance(t, str) for t in texts)
    # Assert that at least one string contains 'Stacked line' (case-insensitive)
    assert any('stacked line' in t.lower() for t in texts), "Expected 'Stacked line' to be found in extracted text."
    print("Extracted text:", texts)
