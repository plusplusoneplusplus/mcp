import pytest
import asyncio
from mcp_tools.browser.playwright_script_runner import PlaywrightScriptRunner
from mcp_tools.browser.playwright_wrapper import PlaywrightWrapper

pytestmark = pytest.mark.asyncio

github_io_url = "https://github.com/"

async def test_run_script_open_and_wait(monkeypatch):
    # Patch PlaywrightWrapper methods to avoid real browser actions
    opened_urls = []
    sleep_calls = []
    located_elements = []

    class DummyPW(PlaywrightWrapper):
        async def open_page(self, url, wait_time=None):
            opened_urls.append(url)
            class DummyPage:
                def __init__(self, url):
                    self.url = url
                async def title(self): return "Dummy Title"
            self.page = DummyPage(url)
            return self.page
        async def locate_elements(self, selector):
            located_elements.append(selector)
            return [f"element:{selector}"]
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    runner = PlaywrightScriptRunner(wrapper=DummyPW())
    script = f"""
    open {github_io_url}
    wait 2s
    locate_element header
    """
    await runner.run_script(script)
    assert opened_urls == [github_io_url]
    assert sleep_calls == [2.0]
    assert located_elements == ["header"]
    assert runner.get_last_located() == ["element:header"]
