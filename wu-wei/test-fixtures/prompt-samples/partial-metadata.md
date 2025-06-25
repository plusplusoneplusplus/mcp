---
title: Partial Metadata Prompt
author: Test Author
tags: [partial, minimal]
---

# Partial Metadata Prompt

This prompt has only some metadata fields defined. The parser should fill in default values for missing fields like:
- description (should be empty)
- category (should be "General")
- version (should be "1.0.0")
- created/modified dates (should be set from file system)
- parameters (should be empty array)
- examples (should be empty array)

This tests the parser's ability to handle incomplete metadata gracefully.
