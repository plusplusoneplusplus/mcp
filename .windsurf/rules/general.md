---
trigger: always_on
globs: *.sh,*.md,*.py,*.ps1
---

1. Use uv for package management instead of pip
2. Do not generate readme markdown files unless I explicitly ask
3. Do not generate example unless I explicitly ask
4. Use `uv run pytest test_abc.py` to run the tests