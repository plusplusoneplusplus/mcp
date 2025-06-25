---
title: Invalid YAML Test
description: This prompt has malformed YAML
invalid: yaml: syntax: error
  - bad indentation
    - even worse indentation
  missing: 
bracket: [unclosed
---

# Invalid YAML Prompt

This prompt should trigger YAML parsing errors due to:
- Invalid colons in field names
- Inconsistent indentation
- Unclosed brackets
- General YAML syntax violations

The parser should handle this gracefully and return appropriate error messages.
