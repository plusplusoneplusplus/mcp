"""
CLI Executor Module

Handles execution of different AI CLI tools (Claude, Codex, Copilot).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .models import ModelInfo

logger = logging.getLogger(__name__)


class CLIType(str, Enum):
    """Supported CLI types"""

    CLAUDE = "claude"
    CODEX = "codex"
    COPILOT = "copilot"


@dataclass
class CLIConfig:
    """Configuration for CLI execution"""

    cli_type: CLIType = CLIType.COPILOT
    """CLI type to use: claude, codex, or copilot (default: copilot)"""

    model: Optional[Union[ModelInfo, str]] = None
    """
    Model to use for the agent. Can be a ModelInfo object or model name string.
    - Claude Code: Only Claude family models (default: claude-opus-4.5)
    - Codex: Only GPT family models (default: gpt-5)
    - Copilot: GPT, Claude, or Gemini models (default: claude-opus-4.5)
    """

    skip_permissions: bool = True
    """
    Whether to skip permission prompts:
    - Claude: --dangerously-skip-permissions
    - Codex: --full-auto
    - Copilot: --allow-all-tools
    """

    cli_path: Optional[str] = None
    """Path to the CLI executable (default: auto-detected based on cli_type)"""

    timeout: Optional[int] = None
    """Timeout for CLI invocations in seconds (None for no timeout)"""

    working_directories: Optional[List[str]] = None
    """Working directories for the agent's context"""

    cwd: Optional[str] = None
    """Current working directory for CLI execution (None for current directory)"""

    additional_cli_args: List[str] = field(default_factory=list)
    """Additional CLI arguments to pass"""

    # Codex-specific options
    codex_mode: str = "exec"
    """Codex execution mode: 'exec' for scripted runs, '' for interactive (default: exec)"""

    codex_approval_mode: Optional[str] = None
    """Codex approval mode: suggest, auto-edit, or full-auto (default: None)"""

    # Copilot-specific options
    copilot_use_programmatic: bool = True
    """Whether to use Copilot's programmatic mode with -p flag (default: True)"""

    def get_cli_path(self) -> str:
        """Get the CLI executable path"""
        if self.cli_path:
            return self.cli_path
        return self.cli_type.value

    def get_model_name(self) -> str:
        """
        Get the canonical model name string.

        Returns the model name from ModelInfo or the string directly.
        If no model is set, returns the default model for the CLI type.
        """
        if self.model is not None:
            # Import here to avoid circular import
            from .models import ModelInfo as MI

            if isinstance(self.model, MI):
                return self.model.name
            return self.model

        # Use defaults from models module
        from .models import get_default_model

        return get_default_model(self.cli_type)

    def get_cli_model_name(self) -> str:
        """
        Get the CLI-specific model name.

        Different CLIs may use different naming conventions. For example,
        Claude CLI uses 'sonnet', 'opus', 'haiku' as aliases instead of
        full model names like 'claude-sonnet-4.5'.

        Returns:
            The model name appropriate for the configured CLI type.
        """
        from .models import get_cli_model_name as convert_model_name, ModelInfo as MI

        if self.model is not None:
            if isinstance(self.model, MI):
                return self.model.get_cli_model_name(self.cli_type)
            # String model name - convert it
            return convert_model_name(self.cli_type, self.model)

        # Use default model and convert
        from .models import get_default_model

        default_model = get_default_model(self.cli_type)
        return convert_model_name(self.cli_type, default_model)

    def get_model_info(self) -> Optional[ModelInfo]:
        """
        Get the ModelInfo object for the configured model.

        Returns ModelInfo if model is set (either directly or looked up by name),
        or None if no model is configured.
        """
        from .models import ModelInfo as MI, get_model_info as lookup_model

        if self.model is None:
            # Get default model info
            from .models import get_default_model

            default_name = get_default_model(self.cli_type)
            if default_name:
                return lookup_model(default_name)
            return None

        if isinstance(self.model, MI):
            return self.model

        # Look up by name
        return lookup_model(self.model)

    def validate_model(self) -> None:
        """
        Validate that the configured model is supported by the CLI type.

        Raises:
            ValueError: If the model is not supported by the CLI type
        """
        from .models import validate_model_for_cli

        model_name = self.get_model_name()
        if model_name:
            validate_model_for_cli(self.cli_type, model_name)

    # Keep for backward compatibility
    def get_default_model(self) -> str:
        """Get default model for the CLI type (deprecated, use get_model_name)"""
        return self.get_model_name()


class CLIExecutor:
    """Executes AI CLI commands"""

    def __init__(self, config: CLIConfig):
        """
        Initialize the CLI executor.

        Args:
            config: CLI configuration
        """
        self.config = config

    def build_command(self, prompt: str) -> List[str]:
        """
        Build the CLI command based on the CLI type.

        Args:
            prompt: The prompt to send to the CLI

        Returns:
            List of command arguments
        """
        base_cmd = [self.config.get_cli_path()]

        if self.config.cli_type == CLIType.CLAUDE:
            return self._build_claude_command(base_cmd, prompt)
        elif self.config.cli_type == CLIType.CODEX:
            return self._build_codex_command(base_cmd, prompt)
        elif self.config.cli_type == CLIType.COPILOT:
            return self._build_copilot_command(base_cmd, prompt)
        else:
            raise ValueError(f"Unsupported CLI type: {self.config.cli_type}")

    def _build_claude_command(self, base_cmd: List[str], prompt: str) -> List[str]:
        """Build Claude CLI command"""
        cmd = base_cmd.copy()

        # Add skip permissions flag
        if self.config.skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        # Add model flag (use CLI-specific name for Claude, e.g., 'sonnet', 'opus')
        model = self.config.get_cli_model_name()
        if model:
            cmd.extend(["--model", model])

        # Add any additional CLI args
        cmd.extend(self.config.additional_cli_args)

        # Add the prompt
        cmd.append(prompt)

        return cmd

    def _build_codex_command(self, base_cmd: List[str], prompt: str) -> List[str]:
        """Build Codex CLI command"""
        cmd = base_cmd.copy()

        # Add execution mode (exec for scripted runs)
        if self.config.codex_mode:
            cmd.append(self.config.codex_mode)

        # Add approval mode if specified
        if self.config.skip_permissions and not self.config.codex_approval_mode:
            cmd.append("--full-auto")
        elif self.config.codex_approval_mode:
            cmd.append(f"--{self.config.codex_approval_mode}")

        # Add any additional CLI args
        cmd.extend(self.config.additional_cli_args)

        # Add the prompt
        cmd.append(prompt)

        return cmd

    def _build_copilot_command(self, base_cmd: List[str], prompt: str) -> List[str]:
        """Build GitHub Copilot CLI command"""
        cmd = base_cmd.copy()

        # Add skip permissions flag (allow all tools without confirmation)
        if self.config.skip_permissions:
            cmd.append("--allow-all-tools")

        # Use programmatic mode with -p flag
        if self.config.copilot_use_programmatic:
            cmd.extend(["-p", prompt])
        else:
            # In interactive mode, prompt would need to be piped via stdin
            cmd.append(prompt)

        # Add any additional CLI args
        cmd.extend(self.config.additional_cli_args)

        return cmd

    async def execute(self, prompt: str) -> str:
        """
        Execute the CLI with the given prompt.

        Args:
            prompt: The prompt to send to the CLI

        Returns:
            CLI response as a string, or error message if execution failed
        """
        # Build command
        cmd = self.build_command(prompt)

        try:
            # Execute CLI
            logger.debug(f"Executing: {' '.join(cmd[:3])} [prompt...]")
            logger.debug(f"Full command: {cmd}")
            logger.debug(f"Prompt length: {len(prompt)} chars")

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.cwd,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    result.communicate(), timeout=self.config.timeout
                )
            except asyncio.TimeoutError:
                result.kill()
                await result.wait()
                return f"Error: CLI execution timed out after {self.config.timeout} seconds"

            # Decode output
            response = stdout.decode("utf-8").strip()
            error_output = stderr.decode("utf-8").strip()

            logger.debug(f"Response length: {len(response)} chars")
            logger.debug(f"Response preview: {response[:200]}...")

            # Check for errors
            if result.returncode != 0:
                error_msg = f"CLI failed with exit code {result.returncode}"
                if error_output:
                    error_msg += f"\nStderr: {error_output}"
                if response:
                    error_msg += f"\nStdout: {response}"
                logger.error(
                    f"CLI execution failed:\nCommand: {' '.join(cmd[:3])} [prompt...]\n{error_msg}"
                )
                return f"Error: {error_msg}"

            if error_output:
                logger.warning(f"CLI stderr: {error_output}")

            return response

        except FileNotFoundError:
            error_msg = f"CLI not found at: {self.config.get_cli_path()}"
            logger.error(error_msg)
            return f"Error: {error_msg}. Please ensure {self.config.cli_type.value} is installed."

        except Exception as e:
            error_msg = f"Failed to invoke CLI: {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
