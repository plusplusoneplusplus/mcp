#!/bin/bash

# Format all Python files tracked by Git using 'uv run black'

# Get all Python files tracked by git
PY_FILES=$(git ls-files '*.py')

if [ -z "$PY_FILES" ]; then
  echo "No Python files tracked by git."
  exit 0
fi

# Format each file
uv run black $PY_FILES