import pytest

# Configure pytest-asyncio to use auto mode
pytest_plugins = ["pytest_asyncio"]

def pytest_configure(config):
    """Add custom markers for tests"""
    config.addinivalue_line("markers", "asyncio: mark test as an asyncio test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    
    # Set default event loop scope for asyncio fixtures
    config.option.asyncio_default_fixture_loop_scope = "function" 