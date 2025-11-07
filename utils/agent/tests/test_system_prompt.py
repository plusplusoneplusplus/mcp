"""
Tests for system prompt utilities.
"""

import pytest
from pathlib import Path
from datetime import datetime

from utils.agent.system_prompt import (
    SystemPromptBuilder,
    create_default_system_prompt,
)


class TestSystemPromptBuilder:
    """Tests for SystemPromptBuilder class"""

    def test_build_default_prompt_basic(self):
        """Test building default prompt with basic parameters"""
        session_id = "test_session_123"
        storage_path = Path("/tmp/.sessions/test_session_123")

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
        )

        assert "# System Configuration" in prompt
        assert "## Session Context" in prompt
        assert f"Session ID**: `{session_id}`" in prompt
        assert f"Session Storage Path**: `{storage_path.absolute()}`" in prompt
        assert "## Guidelines" in prompt

    def test_build_default_prompt_with_role(self):
        """Test building default prompt with agent role"""
        session_id = "test_session_456"
        storage_path = Path("/tmp/.sessions/test_session_456")
        agent_role = "You are a Python expert"

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
            agent_role=agent_role,
        )

        assert "## Agent Role" in prompt
        assert agent_role in prompt

    def test_build_default_prompt_with_instructions(self):
        """Test building default prompt with custom instructions"""
        session_id = "test_session_789"
        storage_path = Path("/tmp/.sessions/test_session_789")
        instructions = "Follow PEP 8 guidelines"

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
            custom_instructions=instructions,
        )

        assert "## Instructions" in prompt
        assert instructions in prompt

    def test_build_default_prompt_full(self):
        """Test building default prompt with all parameters"""
        session_id = "test_full"
        storage_path = Path("/tmp/.sessions/test_full")
        role = "You are a code reviewer"
        instructions = "Focus on security"

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
            agent_role=role,
            custom_instructions=instructions,
            include_timestamp=True,
        )

        assert session_id in prompt
        assert str(storage_path.absolute()) in prompt
        assert role in prompt
        assert instructions in prompt
        assert "Session Started" in prompt

    def test_build_default_prompt_no_timestamp(self):
        """Test building prompt without timestamp"""
        session_id = "test_no_timestamp"
        storage_path = Path("/tmp/.sessions/test_no_timestamp")

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
            include_timestamp=False,
        )

        assert "Session Started" not in prompt

    def test_build_minimal_prompt(self):
        """Test building minimal prompt"""
        session_id = "minimal_session"
        storage_path = Path("/tmp/.sessions/minimal_session")

        prompt = SystemPromptBuilder.build_minimal_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
        )

        assert f"Session ID: {session_id}" in prompt
        assert f"Session Storage: {storage_path.absolute()}" in prompt
        assert "Maintain conversation context" in prompt
        # Should not have headers
        assert "## Session Context" not in prompt

    def test_build_json_context(self):
        """Test building JSON context"""
        session_id = "json_session"
        storage_path = Path("/tmp/.sessions/json_session")

        context = SystemPromptBuilder.build_json_context(
            session_id=session_id,
            session_storage_path=storage_path,
        )

        assert "session" in context
        assert context["session"]["id"] == session_id
        assert context["session"]["storage_path"] == str(storage_path.absolute())
        assert "timestamp" in context["session"]

        # Verify timestamp is valid ISO format
        timestamp = context["session"]["timestamp"]
        datetime.fromisoformat(timestamp)  # Should not raise

    def test_absolute_path_resolution(self):
        """Test that relative paths are converted to absolute"""
        session_id = "path_test"
        relative_path = Path("relative/.sessions/path_test")

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=relative_path,
        )

        # Should contain absolute path
        assert str(relative_path.absolute()) in prompt
        # Should not contain relative path (unless cwd is "relative")
        # This is tested by checking that the prompt contains an absolute path marker
        assert "/" in prompt or "\\" in prompt  # Unix or Windows path separator


class TestConvenienceFunction:
    """Tests for create_default_system_prompt convenience function"""

    def test_create_default_system_prompt_basic(self):
        """Test convenience function with basic parameters"""
        session_id = "convenience_test"
        storage_path = Path("/tmp/.sessions/convenience_test")

        prompt = create_default_system_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
        )

        assert session_id in prompt
        assert str(storage_path.absolute()) in prompt

    def test_create_default_system_prompt_full(self):
        """Test convenience function with all parameters"""
        session_id = "full_convenience"
        storage_path = Path("/tmp/.sessions/full_convenience")
        role = "You are an AI assistant"
        instructions = "Be helpful and concise"

        prompt = create_default_system_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
            agent_role=role,
            custom_instructions=instructions,
        )

        assert session_id in prompt
        assert str(storage_path.absolute()) in prompt
        assert role in prompt
        assert instructions in prompt


class TestPromptStructure:
    """Tests for prompt structure and formatting"""

    def test_prompt_sections_order(self):
        """Test that prompt sections appear in correct order"""
        session_id = "order_test"
        storage_path = Path("/tmp/.sessions/order_test")
        role = "Test role"
        instructions = "Test instructions"

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
            agent_role=role,
            custom_instructions=instructions,
        )

        # Find positions of sections
        config_pos = prompt.find("# System Configuration")
        session_pos = prompt.find("## Session Context")
        storage_info_pos = prompt.find("### Session Storage Information")
        role_pos = prompt.find("## Agent Role")
        instructions_pos = prompt.find("## Instructions")
        guidelines_pos = prompt.find("## Guidelines")

        # Verify order
        assert config_pos < session_pos
        assert session_pos < storage_info_pos
        assert storage_info_pos < role_pos
        assert role_pos < instructions_pos
        assert instructions_pos < guidelines_pos

    def test_prompt_markdown_formatting(self):
        """Test that prompt uses proper markdown formatting"""
        session_id = "markdown_test"
        storage_path = Path("/tmp/.sessions/markdown_test")

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
        )

        # Check for markdown elements
        assert prompt.count("#") >= 4  # Multiple headers
        assert "**Session ID**" in prompt  # Bold text
        assert "`" in prompt  # Code formatting

    def test_prompt_guidelines_content(self):
        """Test that prompt includes proper guidelines"""
        session_id = "guidelines_test"
        storage_path = Path("/tmp/.sessions/guidelines_test")

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
        )

        # Check for key guideline elements
        assert "Session Continuity" in prompt
        assert "Data Persistence" in prompt
        assert "Conversation History" in prompt
        assert "Tool Integration" in prompt


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_empty_session_id(self):
        """Test with empty session ID"""
        storage_path = Path("/tmp/.sessions/empty")

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id="",
            session_storage_path=storage_path,
        )

        # Should still generate prompt, just with empty session ID
        assert "Session ID" in prompt
        assert "Session Storage Path" in prompt

    def test_long_session_id(self):
        """Test with very long session ID"""
        long_id = "a" * 1000
        storage_path = Path("/tmp/.sessions/long")

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=long_id,
            session_storage_path=storage_path,
        )

        assert long_id in prompt

    def test_special_characters_in_path(self):
        """Test with special characters in storage path"""
        session_id = "special_chars"
        storage_path = Path("/tmp/.sessions/test (with) [brackets] & {braces}")

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
        )

        assert str(storage_path.absolute()) in prompt

    def test_multiline_role(self):
        """Test with multiline agent role"""
        session_id = "multiline_test"
        storage_path = Path("/tmp/.sessions/multiline")
        role = """You are an expert assistant.
You have multiple capabilities:
- Code review
- Bug fixing
- Documentation"""

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
            agent_role=role,
        )

        assert role in prompt
        assert "Code review" in prompt

    def test_multiline_instructions(self):
        """Test with multiline custom instructions"""
        session_id = "multiline_inst"
        storage_path = Path("/tmp/.sessions/multiline_inst")
        instructions = """Follow these steps:
1. Analyze the code
2. Identify issues
3. Suggest improvements"""

        prompt = SystemPromptBuilder.build_default_prompt(
            session_id=session_id,
            session_storage_path=storage_path,
            custom_instructions=instructions,
        )

        assert instructions in prompt
        assert "Analyze the code" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
