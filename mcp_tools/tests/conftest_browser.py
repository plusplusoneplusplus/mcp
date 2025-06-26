import pytest

# Try to import playwright and check availability at module level
try:
    import playwright
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def pytest_runtest_setup(item):
    """Setup function to skip Playwright-related tests if not available."""
    # Check if this test involves Playwright
    test_file = str(item.fspath)
    if any(keyword in test_file.lower() for keyword in ['playwright', 'browser_factory']) or \
       any(keyword in item.name.lower() for keyword in ['playwright']):
        if not PLAYWRIGHT_AVAILABLE:
            pytest.skip("Playwright not installed. Install with: pip install playwright && playwright install")
