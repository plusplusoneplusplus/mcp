---
title: Valid Complete Prompt
description: A comprehensive prompt with all metadata fields properly filled
category: Testing
tags: [test, complete, valid, metadata]
author: Test Author
version: 1.2.3
created: 2024-01-15T10:30:00Z
modified: 2024-01-20T15:45:00Z
parameters:
  - name: userName
    type: string
    required: true
    description: The name of the user
    defaultValue: "Anonymous"
  - name: count
    type: number
    required: false
    description: Number of items to process
    validation:
      min: 1
      max: 100
examples:
  - name: Basic Usage
    description: Simple example with minimal parameters
    input:
      userName: "John Doe"
  - name: Advanced Usage
    description: Example with all parameters
    input:
      userName: "Jane Smith"
      count: 42
model:
  preferred: "gpt-4"
  temperature: 0.7
  maxTokens: 2048
---

# Valid Complete Prompt

This is a test prompt that demonstrates proper frontmatter structure with all possible fields correctly defined.

The prompt content uses the following parameters:
- {{userName}}: Will be replaced with the user's name
- {{count}}: Optional parameter for item count

This prompt is designed to test the metadata parser's ability to handle complex, well-formed YAML frontmatter.
