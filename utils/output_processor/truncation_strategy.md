# Output Truncation Strategy

## Overview
Implement a configurable truncation system that intelligently reduces large MCP tool outputs to fit within model context windows while preserving the most important information.

## Goals
- Prevent context window overflow from large tool outputs
- Preserve critical information (errors, warnings, key data)
- Provide multiple truncation strategies for different use cases
- Make truncation behavior configurable per tool/task/user
- Maintain backward compatibility with existing tools

## Configuration System Design

### Configuration Levels (Priority Order)
1. **Task-level**: Specific to individual MCP calls
2. **Tool-level**: Default for specific tools defined in YAML tool definitions
3. **User-level**: User preferences stored in config
4. **System-level**: Global defaults

### Configuration Schema
```yaml
truncation:
  strategy: "head_tail"  # head_tail, smart_summary, size_limit, none
  max_chars: 50000      # ~50KB default
  max_lines: 1000       # Line-based limit
  head_lines: 100       # Lines to keep from start
  tail_lines: 100       # Lines to keep from end
  preserve_errors: true # Always include error messages
  preserve_warnings: true # Always include warnings
  content_detection: true # Detect and preserve structured data
```

### Configuration Sources
```python
# Task-level (highest priority)
await session.call_tool("command_executor", {
    "command": "large_command",
    "truncation": {
        "strategy": "smart_summary",
        "max_chars": 30000
    }
})
```

```yaml
# Tool-level configuration in tools.yaml (YAML tool definition)
command_executor:
  name: "command_executor"
  description: "Execute system commands"
  truncation:
    strategy: "head_tail"
    max_chars: 50000
    max_lines: 1000
    head_lines: 100
    tail_lines: 100
    preserve_errors: true
    preserve_warnings: true
    content_detection: true

browser_automation:
  name: "browser_automation"
  description: "Automate browser interactions"
  truncation:
    strategy: "smart_summary"
    max_chars: 30000
    preserve_errors: true
```

```bash
# User-level in .env or config
TRUNCATION_STRATEGY=head_tail
TRUNCATION_MAX_CHARS=50000

# System defaults in code
```

## Truncation Strategies

### 1. Head-Tail Strategy
**Best for**: Log files, command outputs, sequential data
- Keep first N lines and last N lines
- Show truncation indicator with count of skipped content
- Preserve structure markers (headers, footers)

### 2. Smart Summary Strategy
**Best for**: Mixed content with errors/warnings
- Extract and prioritize errors and warnings
- Identify structured data (JSON, tables, CSV)
- Keep representative samples from different sections
- Generate content summary with statistics

### 3. Size Limit Strategy
**Best for**: Simple character-based truncation
- Hard cutoff at character limit
- Try to break at word/line boundaries
- Add truncation indicator

### 4. None Strategy
**Best for**: Small outputs or when full content needed
- No truncation applied
- Pass through original content

## Implementation Plan

### Phase 1: Core Infrastructure
1. **Configuration Manager**
   - Hierarchical config resolution (task → YAML tool → user → system)
   - YAML tool definition parsing and validation
   - Schema validation
   - Runtime config updates

2. **Truncation Engine**
   - Strategy pattern implementation
   - Pluggable truncation algorithms
   - Metadata preservation

3. **Integration Points**
   - CommandExecutor integration
   - Generic tool wrapper
   - Response formatting

### Phase 2: Advanced Features
1. **Content Analysis**
   - Error/warning detection
   - Structured data identification
   - Content type classification

2. **Smart Preservation**
   - Critical section detection
   - Context-aware truncation
   - Adaptive limits based on content

### Phase 3: User Experience
1. **Configuration UI**
   - Web interface for settings
   - Per-tool configuration
   - Preview truncation results

2. **Monitoring & Analytics**
   - Truncation frequency tracking
   - Content loss analysis
   - Optimization recommendations

## Technical Implementation

### Core Classes
```python
class TruncationConfig:
    strategy: TruncationStrategy
    max_chars: int
    max_lines: int
    # ... other config options

class TruncationEngine:
    def truncate(self, content: str, config: TruncationConfig) -> TruncationResult
    def get_strategy(self, strategy_name: str) -> TruncationStrategy

class TruncationResult:
    content: str
    truncated: bool
    original_size: int
    strategy_used: str
    metadata: Dict[str, Any]
```

### Integration Points
1. **YAML Tool Definitions**: Truncation config embedded in tool definitions
2. **Tool Wrapper**: Automatic truncation for all tools based on YAML config
3. **Response Middleware**: Server-level processing
4. **Client Configuration**: Per-session settings

## Benefits
- **Immediate**: Prevents context overflow issues
- **Flexible**: Multiple strategies for different needs
- **Configurable**: Users control truncation behavior
- **Backward Compatible**: Existing tools work unchanged
- **Extensible**: Easy to add new truncation strategies

## Risks & Mitigations
- **Information Loss**: Mitigated by smart preservation and user control
- **Performance Impact**: Minimal processing overhead
- **Configuration Complexity**: Clear defaults and documentation
- **User Confusion**: Progressive disclosure of advanced options

## Success Metrics
- Reduction in context overflow errors
- User adoption of configuration options
- Preserved information quality scores
- Performance impact measurements
