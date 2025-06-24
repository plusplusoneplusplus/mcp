# Prompt Store Extension Panel - Design Document

## Overview

The Prompt Store is a management module for the Wu Wei extension that provides a centralized way to organize, manage, and utilize prompt templates. Following the Wu Wei philosophy of effortless automation, the prompt store enables users to maintain a collection of reusable prompts with minimal friction.

## Core Features

### 1. Directory-Based Prompt Management
- Users configure a root directory for their prompt collection
- All markdown files within the directory become available as prompts
- Supports nested folder structure for hierarchical organization
- Configuration persists across VS Code sessions

### 2. Prompt Library Browser
- Tree-view interface showing all available prompts
- Organized by folder structure (if nested directories are used)
- Real-time updates when files are added/removed/modified
- Search and filter capabilities for large prompt collections

### 3. Inline Prompt Editor
- Click any prompt in the list to open for editing
- Syntax highlighting for markdown content
- Auto-save functionality
- Preview mode for rendered markdown

### 4. Metadata System
- YAML frontmatter support for prompt metadata
- Standardized metadata fields with extensible schema
- Metadata-based filtering and organization
- Template generation with metadata scaffolding

## Technical Architecture

### 3.1 Core Components

#### PromptStoreProvider
```typescript
class PromptStoreProvider implements vscode.WebviewViewProvider {
    // Manages the webview UI and user interactions
    // Handles directory selection and configuration
    // Coordinates between file system and UI
}
```

#### PromptManager
```typescript
class PromptManager {
    // Core business logic for prompt operations
    // File system operations (read, write, delete)
    // Metadata parsing and validation
    // Change detection and notifications
}
```

#### PromptFileWatcher
```typescript
class PromptFileWatcher {
    // Monitors configured directory for changes
    // Triggers UI updates when files change
    // Handles file creation, deletion, and modification events
}
```

#### MetadataParser
```typescript
class MetadataParser {
    // Parses YAML frontmatter from markdown files
    // Validates metadata schema
    // Provides default values for missing fields
}
```

### 3.2 Data Models

#### Prompt Interface
```typescript
interface Prompt {
    id: string;                    // Unique identifier (file path hash)
    name: string;                  // Display name (from filename or metadata)
    filePath: string;              // Absolute path to the markdown file
    relativePath: string;          // Path relative to prompt store root
    content: string;               // Full markdown content
    metadata: PromptMetadata;      // Parsed frontmatter
    lastModified: Date;            // File modification timestamp
    isValid: boolean;              // Whether the file is valid markdown
}
```

#### PromptMetadata Interface
```typescript
interface PromptMetadata {
    title?: string;                // Human-readable title
    description?: string;          // Brief description of the prompt
    tags?: string[];               // Categorization tags
    author?: string;               // Author information
    version?: string;              // Version identifier
    category?: string;             // Primary category
    language?: string;             // Target language (if applicable)
    created?: Date;                // Creation timestamp
    updated?: Date;                // Last update timestamp
    parameters?: ParameterDef[];   // Input parameter definitions
    examples?: string[];           // Usage examples
    [key: string]: any;            // Extensible for custom fields
}
```

#### ParameterDef Interface
```typescript
interface ParameterDef {
    name: string;                  // Parameter name
    type: 'string' | 'number' | 'boolean' | 'array' | 'object';
    description?: string;          // Parameter description
    required?: boolean;            // Whether parameter is required
    default?: any;                 // Default value
    options?: any[];               // Allowed values (for enum-like parameters)
}
```

## User Interface Design

### 4.1 Panel Layout

```
┌─────────────────────────────────────┐
│ Wu Wei Prompt Store                 │
├─────────────────────────────────────┤
│ [📁 Configure Directory]           │
│                                     │
│ 🔍 [Search prompts...]             │
│                                     │
│ ├── 📁 General                     │
│ │   ├── 📄 meeting-notes.md        │
│ │   └── 📄 code-review.md          │
│ ├── 📁 Development                 │
│ │   ├── 📄 bug-analysis.md         │
│ │   ├── 📄 feature-spec.md         │
│ │   └── 📄 test-plan.md            │
│ └── 📁 Communication               │
│     ├── 📄 email-template.md       │
│     └── 📄 presentation.md         │
│                                     │
│ [➕ New Prompt] [🔄 Refresh]       │
└─────────────────────────────────────┘
```

### 4.2 Prompt Editor Integration

- Opens prompts in VS Code's native markdown editor
- Provides template snippets for metadata frontmatter
- Offers quick actions for common operations (duplicate, delete, rename)
- Shows metadata in editor gutter or status bar

### 4.3 Configuration UI

```
┌─────────────────────────────────────┐
│ Prompt Store Configuration          │
├─────────────────────────────────────┤
│ Root Directory:                     │
│ [/Users/name/prompts] [Browse...]   │
│                                     │
│ ☑ Auto-refresh on file changes     │
│ ☑ Show metadata in tooltips        │
│ ☑ Enable prompt templates          │
│                                     │
│ Metadata Schema:                    │
│ ☑ Title       ☑ Description        │
│ ☑ Tags        ☑ Author             │
│ ☑ Category    ☑ Parameters         │
│                                     │
│ [Save Configuration]                │
└─────────────────────────────────────┘
```

## Metadata Schema

### 5.1 Standard Frontmatter Format

```yaml
---
title: "Meeting Notes Template"
description: "Template for structured meeting documentation"
tags: ["meeting", "documentation", "template"]
author: "Wu Wei Team"
version: "1.0.0"
category: "productivity"
created: 2025-06-23
updated: 2025-06-23
parameters:
  - name: "meeting_title"
    type: "string"
    description: "Title of the meeting"
    required: true
  - name: "attendees"
    type: "array"
    description: "List of meeting attendees"
    required: true
  - name: "duration"
    type: "number"
    description: "Meeting duration in minutes"
    default: 60
examples:
  - "Weekly team standup"
  - "Project retrospective"
  - "Client presentation"
---

# Meeting Notes: {{meeting_title}}

**Date:** {{date}}
**Duration:** {{duration}} minutes
**Attendees:** {{attendees}}

## Agenda
1. 
2. 
3. 

## Discussion Points

## Action Items
- [ ] 
- [ ] 

## Next Steps

```

### 5.2 Metadata Validation

- Required fields validation
- Type checking for known fields
- Date format validation
- Parameter definition validation
- Custom validation rules support

## Configuration Management

### 6.1 Workspace Settings

```json
{
  "wu-wei.promptStore.rootDirectory": "",
  "wu-wei.promptStore.autoRefresh": true,
  "wu-wei.promptStore.showMetadataTooltips": true,
  "wu-wei.promptStore.enableTemplates": true,
  "wu-wei.promptStore.metadataSchema": {
    "title": true,
    "description": true,
    "tags": true,
    "author": true,
    "category": true,
    "parameters": true
  },
  "wu-wei.promptStore.fileWatcher.enabled": true,
  "wu-wei.promptStore.fileWatcher.debounceMs": 500
}
```

### 6.2 Session Persistence

- Store selected directory in workspace state
- Remember expanded/collapsed folders
- Persist search filters and sort preferences
- Cache parsed metadata for performance

## Integration Points

### 7.1 Chat Provider Integration

- Allow prompts to be inserted into chat conversations
- Support parameter substitution in chat context
- Enable prompt chaining and composition
- Provide prompt suggestions based on conversation context

### 7.2 Command Palette Integration

```typescript
// Quick commands for prompt operations
'wu-wei.promptStore.openDirectory'
'wu-wei.promptStore.newPrompt'
'wu-wei.promptStore.searchPrompts'
'wu-wei.promptStore.insertPrompt'
'wu-wei.promptStore.duplicatePrompt'
'wu-wei.promptStore.refreshStore'
```

### 7.3 File Explorer Integration

- Context menu actions for markdown files
- "Add to Prompt Store" option
- Quick preview for prompt files
- Batch operations support

## User Workflows

### 8.1 Initial Setup
1. User opens Wu Wei Prompt Store panel
2. Clicks "Configure Directory" button
3. Selects or creates a directory for prompts
4. Directory is scanned and prompts are loaded
5. Configuration is saved for future sessions

### 8.2 Creating a New Prompt
1. User clicks "New Prompt" button
2. Prompted to enter prompt name and optional category
3. Template file created with metadata scaffolding
4. File opens in editor for immediate editing
5. Auto-save updates the prompt store view

### 8.3 Using an Existing Prompt
1. User browses or searches for desired prompt
2. Clicks on prompt name to open in editor
3. Can view metadata and content
4. Can copy content or use as template
5. Modifications are tracked and saved

### 8.4 Organizing Prompts
1. User can create subdirectories in prompt store directory
2. Move files between folders using file explorer
3. Use tags and categories for logical grouping
4. Search and filter by metadata fields
5. Bulk operations for organization tasks

## Error Handling

### 9.1 File System Errors
- Handle permission denied errors gracefully
- Provide clear error messages for invalid directories
- Recover from corrupted metadata
- Validate file paths and handle network drives

### 9.2 Metadata Validation Errors
- Show validation errors in editor gutter
- Provide suggestions for fixing common issues
- Allow prompts to function with invalid metadata
- Offer metadata repair utilities

### 9.3 Performance Considerations
- Lazy loading for large prompt collections
- Debounced file system watchers
- Cached metadata parsing
- Background refresh operations

## Future Enhancements

### 10.1 Advanced Features
- Prompt versioning and history
- Collaborative prompt sharing
- Remote prompt repositories
- AI-powered prompt suggestions
- Prompt performance analytics

### 10.2 Integration Expansions
- GitHub integration for prompt repositories
- Cloud storage synchronization
- Template marketplace
- Import/export functionality
- API for external tool integration

## Implementation Phases

### Phase 1: Core Infrastructure
- Basic file system operations
- Simple UI with directory selection
- Metadata parsing foundation
- File watcher implementation

### Phase 2: User Interface
- Complete webview panel
- Prompt editor integration
- Search and filter functionality
- Configuration management

### Phase 3: Advanced Features
- Parameter substitution
- Template system
- Chat integration
- Command palette integration

### Phase 4: Polish and Optimization
- Performance optimizations
- Error handling improvements
- Documentation and examples
- User testing and feedback integration

---

*This design document embodies the Wu Wei principle of effortless action - creating a system that works naturally with user workflows while providing powerful prompt management capabilities.*
