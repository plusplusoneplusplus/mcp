# Additional Instructions

## Python Execution
- Always use `uv run python` instead of just `python` for running Python scripts
- Always use `uv run pytest` instead of just `pytest` for running tests
- For installing packages, use `uv add` instead of `pip install`
- For package management operations, use `uv` commands consistently

## Pull Requests
- Add editor information (e.g., gemini-cli) to the PR description.
- Add "(Gemini)" at the end of the PR title.

## Examples:
- Running tests: `uv run pytest tests/`
- Running Python scripts: `uv run python script.py`
- Installing dependencies: `uv add package_name`
- Running modules: `uv run python -m module_name`
