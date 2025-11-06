# SpecializedAgent Tests

This directory contains tests for the SpecializedAgent module.

## Test Types

### Unit Tests (Always Run)

- `test_agent.py` - Unit tests for SpecializedAgent with mocked CLI
- `test_cli_executor.py` - Unit tests for CLIExecutor with mocked subprocess

These tests use mocks and run automatically in CI.

```bash
# Run all unit tests
uv run pytest utils/agent/tests/test_agent.py -v
uv run pytest utils/agent/tests/test_cli_executor.py -v
```

### Integration Tests (Manual Only)

- `test_integration.py` - Integration tests with real CLI execution

These tests are **skipped in CI** but can be run manually to verify actual CLI integration.

**Requirements:**
- The CLI tool must be installed and available in PATH:
  - `copilot` - GitHub Copilot CLI
  - `claude` - Claude CLI
  - `codex` - OpenAI Codex CLI
- Proper authentication configured for the CLI

## Running Integration Tests

### Run All Integration Tests

```bash
uv run pytest utils/agent/tests/test_integration.py -v
```

### Run Specific CLI Tests

```bash
# Test only Copilot
uv run pytest utils/agent/tests/test_integration.py -v -k "copilot"

# Test only Claude
uv run pytest utils/agent/tests/test_integration.py -v -k "claude"

# Test only Codex
uv run pytest utils/agent/tests/test_integration.py -v -k "codex"
```

### Run Specific Test Cases

```bash
# Test hello world responses
uv run pytest utils/agent/tests/test_integration.py::test_copilot_hello_world -v

# Test conversation history
uv run pytest utils/agent/tests/test_integration.py::test_conversation_with_history -v

# Test context preparation
uv run pytest utils/agent/tests/test_integration.py::test_context_preparation -v
```

## Integration Test Coverage

| Test | Description |
|------|-------------|
| `test_copilot_hello_world` | Basic Copilot CLI test with "hello world" |
| `test_claude_hello_world` | Basic Claude CLI test with "hello world" |
| `test_codex_hello_world` | Basic Codex CLI test with "hello world" |
| `test_conversation_with_history` | Multi-turn conversation with history |
| `test_context_preparation` | Agent with custom context |
| `test_batch_processing` | Batch processing multiple prompts |
| `test_timeout_handling` | Timeout enforcement |
| `test_error_handling_invalid_cli` | Error handling for missing CLI |

## Troubleshooting

### Tests are skipped

Integration tests are automatically skipped in CI environments. To run them locally:

```bash
# Make sure CI env vars are not set
unset CI
unset GITHUB_ACTIONS

# Then run the tests
uv run pytest utils/agent/tests/test_integration.py -v
```

### CLI not found errors

Make sure the CLI is installed and in your PATH:

```bash
# Check if CLI is available
which copilot
which claude
which codex

# Or install the CLI
# For Copilot: https://github.com/github/copilot-cli
# For Claude: https://claude.ai/cli
# For Codex: npm install -g @openai/codex
```

### Authentication errors

Ensure you're authenticated with the respective service:

```bash
# Copilot
gh auth login

# Claude
claude auth

# Codex
codex login
```

### Test failures

If integration tests fail:

1. Verify CLI is working manually: `copilot "hello"`
2. Check timeout settings (default: 30s)
3. Review CLI output in test failures
4. Ensure internet connectivity
5. Check service status

## CI Behavior

Integration tests are **automatically skipped** in CI by checking for:
- `CI=true` environment variable
- `GITHUB_ACTIONS=true` environment variable

This ensures CI runs remain fast and don't require CLI authentication.
