"""
Unit tests for CLIExecutor
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

from utils.agent.cli_executor import CLIExecutor, CLIConfig, CLIType


class TestCLIConfig:
    """Tests for CLIConfig"""

    def test_default_config(self):
        """Test default configuration values"""
        config = CLIConfig()

        assert config.cli_type == CLIType.COPILOT
        assert config.model is None
        assert config.skip_permissions is True
        assert config.cli_path is None
        assert config.timeout is None
        assert config.working_directories is None
        assert config.cwd is None
        assert config.codex_mode == "exec"
        assert config.codex_approval_mode is None
        assert config.copilot_use_programmatic is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = CLIConfig(
            cli_type=CLIType.CODEX,
            model="gpt-4",
            skip_permissions=False,
            cli_path="/custom/path/codex",
            timeout=60
        )

        assert config.cli_type == CLIType.CODEX
        assert config.model == "gpt-4"
        assert config.skip_permissions is False
        assert config.cli_path == "/custom/path/codex"
        assert config.timeout == 60

    def test_get_cli_path_default(self):
        """Test getting CLI path with default"""
        # Test default (Copilot)
        config = CLIConfig()
        assert config.get_cli_path() == "copilot"

        # Test other CLI types
        config = CLIConfig(cli_type=CLIType.CLAUDE)
        assert config.get_cli_path() == "claude"

        config = CLIConfig(cli_type=CLIType.CODEX)
        assert config.get_cli_path() == "codex"

        config = CLIConfig(cli_type=CLIType.COPILOT)
        assert config.get_cli_path() == "copilot"

    def test_get_cli_path_custom(self):
        """Test getting CLI path with custom path"""
        config = CLIConfig(
            cli_type=CLIType.CLAUDE,
            cli_path="/usr/local/bin/claude"
        )
        assert config.get_cli_path() == "/usr/local/bin/claude"

    def test_get_default_model_claude(self):
        """Test getting default model for Claude"""
        config = CLIConfig(cli_type=CLIType.CLAUDE)
        assert config.get_default_model() == "sonnet"

        config = CLIConfig(cli_type=CLIType.CLAUDE, model="haiku")
        assert config.get_default_model() == "haiku"

    def test_get_default_model_copilot(self):
        """Test getting default model for Copilot"""
        config = CLIConfig(cli_type=CLIType.COPILOT)
        assert config.get_default_model() == "claude-sonnet-4.5"

    def test_get_default_model_codex(self):
        """Test getting default model for Codex"""
        config = CLIConfig(cli_type=CLIType.CODEX)
        assert config.get_default_model() == ""


class TestCLIExecutor:
    """Tests for CLIExecutor"""

    def test_init(self):
        """Test executor initialization"""
        config = CLIConfig(cli_type=CLIType.CLAUDE)
        executor = CLIExecutor(config)

        assert executor.config == config
        assert executor.config.cli_type == CLIType.CLAUDE

    def test_build_claude_command_basic(self):
        """Test building basic Claude command"""
        config = CLIConfig(
            cli_type=CLIType.CLAUDE,
            model="haiku",
            skip_permissions=True
        )
        executor = CLIExecutor(config)

        cmd = executor.build_command("test prompt")

        assert cmd[0] == "claude"
        assert "--dangerously-skip-permissions" in cmd
        assert "--model" in cmd
        assert "haiku" in cmd
        assert "test prompt" in cmd

    def test_build_claude_command_no_skip_permissions(self):
        """Test building Claude command without skip permissions"""
        config = CLIConfig(
            cli_type=CLIType.CLAUDE,
            skip_permissions=False
        )
        executor = CLIExecutor(config)

        cmd = executor.build_command("test prompt")

        assert "--dangerously-skip-permissions" not in cmd

    def test_build_codex_command_basic(self):
        """Test building basic Codex command"""
        config = CLIConfig(
            cli_type=CLIType.CODEX,
            skip_permissions=True
        )
        executor = CLIExecutor(config)

        cmd = executor.build_command("test prompt")

        assert cmd[0] == "codex"
        assert "exec" in cmd
        assert "--full-auto" in cmd
        assert "test prompt" in cmd

    def test_build_codex_command_custom_approval(self):
        """Test building Codex command with custom approval mode"""
        config = CLIConfig(
            cli_type=CLIType.CODEX,
            codex_approval_mode="suggest",
            skip_permissions=False
        )
        executor = CLIExecutor(config)

        cmd = executor.build_command("test prompt")

        assert "--suggest" in cmd
        assert "--full-auto" not in cmd

    def test_build_copilot_command_basic(self):
        """Test building basic Copilot command"""
        config = CLIConfig(
            cli_type=CLIType.COPILOT,
            skip_permissions=True,
            copilot_use_programmatic=True
        )
        executor = CLIExecutor(config)

        cmd = executor.build_command("test prompt")

        assert cmd[0] == "copilot"
        assert "--allow-all-tools" in cmd
        assert "-p" in cmd
        assert "test prompt" in cmd

    def test_build_copilot_command_no_skip_permissions(self):
        """Test building Copilot command without skip permissions"""
        config = CLIConfig(
            cli_type=CLIType.COPILOT,
            skip_permissions=False
        )
        executor = CLIExecutor(config)

        cmd = executor.build_command("test prompt")

        assert "--allow-all-tools" not in cmd

    def test_build_command_with_additional_args(self):
        """Test building command with additional CLI args"""
        config = CLIConfig(
            cli_type=CLIType.CLAUDE,
            additional_cli_args=["--verbose", "--debug"]
        )
        executor = CLIExecutor(config)

        cmd = executor.build_command("test prompt")

        assert "--verbose" in cmd
        assert "--debug" in cmd

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful command execution"""
        config = CLIConfig(cli_type=CLIType.CLAUDE)
        executor = CLIExecutor(config)

        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"Success response", b"")
        )
        mock_process.returncode = 0

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            response = await executor.execute("test prompt")

        assert response == "Success response"
        assert mock_process.communicate.called

    @pytest.mark.asyncio
    async def test_execute_with_stderr_warning(self):
        """Test execution with stderr warnings"""
        config = CLIConfig(cli_type=CLIType.CLAUDE)
        executor = CLIExecutor(config)

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"Success response", b"Warning: something")
        )
        mock_process.returncode = 0

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            response = await executor.execute("test prompt")

        assert response == "Success response"

    @pytest.mark.asyncio
    async def test_execute_failure(self):
        """Test failed command execution"""
        config = CLIConfig(cli_type=CLIType.CLAUDE)
        executor = CLIExecutor(config)

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error occurred")
        )
        mock_process.returncode = 1

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            response = await executor.execute("test prompt")

        assert response.startswith("Error:")
        assert "exit code 1" in response

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        """Test command execution timeout"""
        config = CLIConfig(cli_type=CLIType.CLAUDE, timeout=0.1)
        executor = CLIExecutor(config)

        mock_process = AsyncMock()
        # Simulate slow response
        async def slow_communicate():
            await asyncio.sleep(1)
            return (b"response", b"")

        mock_process.communicate = slow_communicate
        mock_process.kill = Mock()
        mock_process.wait = AsyncMock()

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            response = await executor.execute("test prompt")

        assert "timed out" in response.lower()
        assert mock_process.kill.called

    @pytest.mark.asyncio
    async def test_execute_file_not_found(self):
        """Test execution when CLI not found"""
        config = CLIConfig(cli_type=CLIType.CLAUDE)
        executor = CLIExecutor(config)

        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError()):
            response = await executor.execute("test prompt")

        assert "CLI not found" in response
        assert "claude" in response

    @pytest.mark.asyncio
    async def test_execute_general_exception(self):
        """Test execution with general exception"""
        config = CLIConfig(cli_type=CLIType.CLAUDE)
        executor = CLIExecutor(config)

        with patch('asyncio.create_subprocess_exec', side_effect=Exception("Test error")):
            response = await executor.execute("test prompt")

        assert "Failed to invoke CLI" in response
        assert "Test error" in response

    @pytest.mark.asyncio
    async def test_execute_with_cwd(self):
        """Test execution with custom cwd (current working directory)"""
        config = CLIConfig(
            cli_type=CLIType.CLAUDE,
            cwd="/custom/dir"
        )
        executor = CLIExecutor(config)

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"response", b""))
        mock_process.returncode = 0

        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            await executor.execute("test prompt")

            # Verify cwd was passed
            call_kwargs = mock_exec.call_args[1]
            assert call_kwargs['cwd'] == "/custom/dir"

    @pytest.mark.asyncio
    async def test_execute_with_working_directories_and_cwd(self):
        """Test execution with both working_directories and cwd"""
        config = CLIConfig(
            cli_type=CLIType.CLAUDE,
            working_directories=["/dir1", "/dir2", "/dir3"],
            cwd="/dir1"
        )
        executor = CLIExecutor(config)

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"response", b""))
        mock_process.returncode = 0

        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            await executor.execute("test prompt")

            # Verify cwd was passed (not working_directories)
            call_kwargs = mock_exec.call_args[1]
            assert call_kwargs['cwd'] == "/dir1"

    def test_config_with_working_directories_list(self):
        """Test configuration with multiple working directories"""
        config = CLIConfig(
            cli_type=CLIType.CLAUDE,
            working_directories=["/dir1", "/dir2", "/dir3"]
        )

        assert config.working_directories == ["/dir1", "/dir2", "/dir3"]
        assert len(config.working_directories) == 3
        assert config.cwd is None

    def test_build_command_invalid_cli_type(self):
        """Test building command with invalid CLI type"""
        config = CLIConfig(cli_type=CLIType.CLAUDE)
        executor = CLIExecutor(config)

        # Create a mock invalid CLI type
        class InvalidCLIType:
            value = "invalid"

        # Temporarily change to invalid type
        executor.config.cli_type = InvalidCLIType()

        with pytest.raises(ValueError, match="Unsupported CLI type"):
            executor.build_command("test")
