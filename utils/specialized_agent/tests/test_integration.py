"""
Integration tests for SpecializedAgent with real CLI execution.

These tests are skipped in CI environments but can be run locally
to verify actual CLI integration.

To run these tests locally:
    pytest utils/specialized_agent/tests/test_integration.py -v

To run with specific CLI:
    pytest utils/specialized_agent/tests/test_integration.py -v -k "copilot"
"""

import os
import pytest

from utils.specialized_agent import SpecializedAgent, AgentConfig, CLIType


# Skip all tests in this module if running in CI
pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
    reason="Integration tests are skipped in CI - run manually to test real CLI"
)


class SimpleTestAgent(SpecializedAgent):
    """Simple agent for integration testing"""

    def get_system_prompt(self) -> str:
        return "You are a helpful assistant. Keep responses brief and direct."


@pytest.mark.integration
@pytest.mark.asyncio
async def test_copilot_hello_world():
    """Test actual Copilot CLI with hello world request"""
    config = AgentConfig(
        cli_type=CLIType.COPILOT,
        timeout=30  # 30 second timeout
    )
    agent = SimpleTestAgent(config)

    response = await agent.invoke("Can you say hello world?")

    # Verify response is not an error
    assert not response.startswith("Error:"), f"Got error: {response}"

    # Verify response contains expected content
    response_lower = response.lower()
    assert "hello" in response_lower or "world" in response_lower, \
        f"Response doesn't contain 'hello' or 'world': {response}"

    # Verify response is not empty
    assert len(response.strip()) > 0, "Response is empty"

    print(f"\n✅ Copilot response: {response}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_claude_hello_world():
    """Test actual Claude CLI with hello world request"""
    config = AgentConfig(
        cli_type=CLIType.CLAUDE,
        model="haiku",  # Fast model
        timeout=30
    )
    agent = SimpleTestAgent(config)

    response = await agent.invoke("Can you say hello world?")

    # Verify response is not an error
    assert not response.startswith("Error:"), f"Got error: {response}"

    # Verify response contains expected content
    response_lower = response.lower()
    assert "hello" in response_lower or "world" in response_lower, \
        f"Response doesn't contain 'hello' or 'world': {response}"

    # Verify response is not empty
    assert len(response.strip()) > 0, "Response is empty"

    print(f"\n✅ Claude response: {response}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_codex_hello_world():
    """Test actual Codex CLI with hello world request"""
    config = AgentConfig(
        cli_type=CLIType.CODEX,
        timeout=30
    )
    agent = SimpleTestAgent(config)

    response = await agent.invoke("Can you say hello world?")

    # Verify response is not an error
    assert not response.startswith("Error:"), f"Got error: {response}"

    # Verify response contains expected content
    response_lower = response.lower()
    assert "hello" in response_lower or "world" in response_lower, \
        f"Response doesn't contain 'hello' or 'world': {response}"

    # Verify response is not empty
    assert len(response.strip()) > 0, "Response is empty"

    print(f"\n✅ Codex response: {response}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversation_with_history():
    """Test multi-turn conversation with real CLI"""
    config = AgentConfig(
        cli_type=CLIType.COPILOT,
        session_id="integration-test",
        timeout=30
    )
    agent = SimpleTestAgent(config)

    # First turn
    response1 = await agent.invoke("What is 2+2?")
    assert not response1.startswith("Error:"), f"First turn error: {response1}"
    assert "4" in response1, f"Expected '4' in response: {response1}"

    # Second turn - should have context from first
    response2 = await agent.invoke("What was my previous question?")
    assert not response2.startswith("Error:"), f"Second turn error: {response2}"
    # Response should reference the previous question about 2+2
    response2_lower = response2.lower()
    assert "2" in response2_lower or "previous" in response2_lower or "question" in response2_lower, \
        f"Response doesn't reference previous question: {response2}"

    print(f"\n✅ Turn 1: {response1}")
    print(f"✅ Turn 2: {response2}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_preparation():
    """Test agent with context preparation"""

    class ContextTestAgent(SpecializedAgent):
        def get_system_prompt(self) -> str:
            return "You are a code assistant."

        def prepare_context(self, **kwargs):
            code = kwargs.get("code")
            if code:
                return f"Code to analyze:\n```\n{code}\n```"
            return None

    config = AgentConfig(
        cli_type=CLIType.COPILOT,
        timeout=30
    )
    agent = ContextTestAgent(config)

    sample_code = "def hello():\n    print('Hello, World!')"

    response = await agent.invoke(
        "What does this function do?",
        code=sample_code
    )

    assert not response.startswith("Error:"), f"Got error: {response}"
    response_lower = response.lower()
    assert "hello" in response_lower or "print" in response_lower, \
        f"Response doesn't reference the code: {response}"

    print(f"\n✅ Context test response: {response}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_processing():
    """Test batch processing with real CLI"""
    config = AgentConfig(
        cli_type=CLIType.COPILOT,
        timeout=60  # Longer timeout for batch
    )
    agent = SimpleTestAgent(config)

    prompts = [
        "What is 1+1?",
        "What is the capital of France?",
        "Name one programming language"
    ]

    responses = await agent.batch_invoke(prompts)

    # Verify we got responses for all prompts
    assert len(responses) == len(prompts), \
        f"Expected {len(prompts)} responses, got {len(responses)}"

    # Verify no errors
    for i, response in enumerate(responses):
        assert not response.startswith("Error:"), \
            f"Prompt {i} got error: {response}"
        assert len(response.strip()) > 0, \
            f"Prompt {i} got empty response"

    # Verify expected content
    assert "2" in responses[0].lower(), f"First response missing '2': {responses[0]}"
    assert "paris" in responses[1].lower(), f"Second response missing 'paris': {responses[1]}"

    print(f"\n✅ Batch responses:")
    for i, response in enumerate(responses):
        print(f"  {i+1}. {response}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_timeout_handling():
    """Test that timeout is properly enforced"""
    config = AgentConfig(
        cli_type=CLIType.COPILOT,
        timeout=1  # Very short timeout
    )
    agent = SimpleTestAgent(config)

    # This might timeout if the CLI is slow
    response = await agent.invoke("Write a very long story about space exploration")

    # Response might be a timeout error or actual response if CLI was fast
    # Just verify we got something back and didn't hang
    assert response is not None, "Got None response"
    assert len(response) > 0, "Got empty response"

    if response.startswith("Error:") and "timed out" in response.lower():
        print(f"\n✅ Timeout correctly enforced: {response}")
    else:
        print(f"\n✅ CLI responded before timeout: {response[:100]}...")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_invalid_cli():
    """Test handling of invalid/missing CLI"""
    config = AgentConfig(
        cli_type=CLIType.COPILOT,
        cli_path="/nonexistent/path/to/cli",  # Invalid path
        timeout=5
    )
    agent = SimpleTestAgent(config)

    response = await agent.invoke("Test prompt")

    # Should get an error about CLI not found
    assert response.startswith("Error:"), \
        f"Expected error for invalid CLI path, got: {response}"
    assert "not found" in response.lower() or "failed" in response.lower(), \
        f"Error message should mention CLI not found: {response}"

    print(f"\n✅ Error handling works: {response}")
