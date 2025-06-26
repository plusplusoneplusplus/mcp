---
title: Partial Metadata Prompt
tags: [partial, minimal]
---

# Partial Metadata Prompt

This prompt has only some metadata fields defined. The parser should fill in default values for missing fields like:
- description (should be empty)
- category (should be "General")

This tests the parser's ability to handle incomplete metadata gracefully with only the four supported fields: title, description, category, and tags.
