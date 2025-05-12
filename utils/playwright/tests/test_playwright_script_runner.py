import pytest
import asyncio

try:
    from unittest import mock
except ImportError:
    import mock
from utils.playwright.playwright_script_runner import PlaywrightScriptRunner
from utils.playwright.playwright_wrapper import PlaywrightWrapper

pytestmark = pytest.mark.asyncio

github_io_url = "https://github.com/"


async def test_run_script_real():
    async with PlaywrightScriptRunner() as runner:
        script = """
        open https://github.com/
        wait 2s
        locate_element header
        locate_element main
        """
        await runner.run_script(script)

        # Simple asserts
        assert isinstance(runner, PlaywrightScriptRunner)
        assert hasattr(runner, "get_last_located")
        # Validate the last located element is for <main>
        main_elements = runner.get_last_located()
        assert isinstance(main_elements, list)
        assert len(main_elements) > 0

        # Assert about the content of the HTML for the first <main> element
        # Use Playwright's locator API: element_handle.evaluate('el => el.innerText')
        # Only check the first element for simplicity
        main_element = main_elements[0]
        text_content = await main_element.evaluate("el => el.innerText")
        assert isinstance(text_content, str)
        assert "GitHub" in text_content or len(text_content.strip()) > 0
