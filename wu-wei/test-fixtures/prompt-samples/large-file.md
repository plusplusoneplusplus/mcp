---
title: Performance Test Prompt
description: This is a large prompt file designed to test parsing performance and memory usage with substantial content. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
category: Performance
tags: [performance, large, test, memory, speed, benchmark, load-testing, stress-test, big-data, scalability]
author: Performance Test Suite
version: 2.0.0-beta
parameters:
  - name: iterations
    type: number
    required: true
    description: Number of iterations to perform
  - name: batchSize
    type: number
    required: false
    description: Size of each processing batch
    defaultValue: 100
  - name: verbose
    type: boolean
    required: false
    description: Enable verbose output
    defaultValue: false
examples:
  - name: Standard Performance Test
    description: Standard performance test configuration
    input:
      iterations: 1000
      batchSize: 50
  - name: High Volume Test
    description: High volume test with large batch sizes
    input:
      iterations: 10000
      batchSize: 500
      verbose: true
---

# Performance Test Prompt

This is a large prompt file designed to test the metadata parser's performance with substantial content.

## Large Content Section

${'Lorem ipsum dolor sit amet, consectetur adipiscing elit. '.repeat(100)}

## Parameters

The following parameters are available:
- {{iterations}}: Controls the number of test iterations
- {{batchSize}}: Sets the processing batch size
- {{verbose}}: Enables detailed output logging

## Performance Characteristics

This prompt tests several aspects of the parser:

1. **Memory Usage**: Large content blocks to test memory efficiency
2. **Parsing Speed**: Complex frontmatter with many fields
3. **Validation Performance**: Multiple parameters and examples
4. **Cache Efficiency**: Repeated access patterns

${'## Repeated Section\n\nThis section is repeated to increase file size and test parser performance with large files.\n\n'.repeat(50)}

## Conclusion

This prompt should successfully parse while demonstrating the parser's ability to handle larger files efficiently.
