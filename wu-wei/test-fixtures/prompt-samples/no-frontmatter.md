# No Frontmatter Prompt

This is a plain markdown file without any YAML frontmatter. The parser should:

1. Detect that there's no frontmatter
2. Use default metadata values
3. Set the title based on the filename
4. Treat the entire content as the prompt body

This is a common case for existing markdown files that users want to convert to prompts without adding frontmatter initially.
