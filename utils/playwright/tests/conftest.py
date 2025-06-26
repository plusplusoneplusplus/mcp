import pytest
import subprocess
import sys

# Try to import playwright and check availability at module level
try:
    import playwright
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def pytest_configure(config):
    """Configure pytest to add custom markers for Playwright tests."""
    config.addinivalue_line(
        "markers", "playwright: mark test as requiring Playwright and browser"
    )

def check_playwright_browser_installed():
    """Check if Playwright browsers (specifically chromium) are installed."""
    if not PLAYWRIGHT_AVAILABLE:
        return False

    try:
        # Check if chromium is available
        result = subprocess.run(
            [sys.executable, "-c",
             "from playwright.sync_api import sync_playwright; "
             "p = sync_playwright().start(); "
             "p.chromium.launch(headless=True).close(); "
             "p.stop()"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False

@pytest.fixture(scope="session")
def ensure_playwright_browser():
    """Ensure Playwright browsers are available, skip tests if not."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not installed. Install with: pip install playwright")

    if not check_playwright_browser_installed():
        # Try to install browsers
        try:
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                pytest.skip(f"Failed to install Playwright browsers: {result.stderr}")
        except subprocess.TimeoutExpired:
            pytest.skip("Playwright browser installation timed out")
        except Exception as e:
            pytest.skip(f"Failed to install Playwright browsers: {e}")

    return True

# Skip all tests in this module if Playwright is not available
if not PLAYWRIGHT_AVAILABLE:
    pytest.skip("Playwright not installed. Install with: pip install playwright", allow_module_level=True)
