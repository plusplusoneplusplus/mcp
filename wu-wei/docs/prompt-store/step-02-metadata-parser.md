# Step 2: Metadata Parser Implementation

## Overview
Implement the core metadata parsing functionality to handle YAML frontmatter in markdown files. This is the foundation for all prompt metadata features.

## Objectives
- Parse YAML frontmatter from markdown files
- Validate metadata against schema
- Handle parsing errors gracefully
- Support optional metadata (files work without frontmatter)
- Provide default values for missing fields

## Tasks

### 2.1 Core Parser Implementation
Implement `MetadataParser` class with the following methods:

```typescript
class MetadataParser {
    parseFile(filePath: string): Promise<ParsedPrompt>
    parseContent(content: string): ParsedPrompt
    validateMetadata(metadata: any): ValidationResult
    extractFrontmatter(content: string): { metadata: any, content: string }
    getDefaultMetadata(): PromptMetadata
}
```

### 2.2 Frontmatter Extraction
- Detect YAML frontmatter blocks (between `---` delimiters)
- Handle files without frontmatter gracefully
- Support both Windows and Unix line endings
- Extract content after frontmatter for prompt body

### 2.3 Metadata Validation
Implement validation for:
- Required field presence
- Type checking (string, array, object, date)
- Date format validation (ISO 8601)
- Parameter definition structure validation
- Custom validation rules support

### 2.4 Error Handling
- Malformed YAML syntax errors
- Invalid metadata field types
- Missing required fields
- File system access errors
- Encoding issues (UTF-8 support)

### 2.5 Default Values
Provide sensible defaults for:
- Title (derived from filename)
- Created date (file creation time)
- Updated date (file modification time)
- Author (from Git config or system user)
- Empty arrays for tags and examples

### 2.6 Performance Optimization
- Cache parsed metadata with file modification time
- Lazy loading for large files
- Streaming for very large markdown files
- Memory management for batch operations

## Implementation Details

### 2.6.1 Frontmatter Detection
```typescript
private extractFrontmatter(content: string): { metadata: any, content: string } {
    const frontmatterRegex = /^---\r?\n([\s\S]*?)\r?\n---\r?\n/;
    const match = content.match(frontmatterRegex);
    
    if (!match) {
        return { metadata: {}, content };
    }
    
    return {
        metadata: yaml.parse(match[1]),
        content: content.substring(match[0].length)
    };
}
```

### 2.6.2 Validation Schema
```typescript
interface ValidationRule {
    field: string;
    type: 'string' | 'array' | 'object' | 'date' | 'boolean';
    required?: boolean;
    validator?: (value: any) => boolean;
}
```

### 2.6.3 Error Result Structure
```typescript
interface ParseResult {
    success: boolean;
    prompt?: Prompt;
    errors: ValidationError[];
    warnings: ValidationWarning[];
}
```

## Testing Requirements

### 2.7 Unit Tests
Create tests for:
- Valid YAML frontmatter parsing
- Invalid YAML syntax handling
- Files without frontmatter
- Various metadata field types
- Edge cases (empty files, binary files, etc.)
- Performance with large files

### 2.8 Test Files
Create sample markdown files:
- `valid-metadata.md` - Complete valid frontmatter
- `partial-metadata.md` - Some fields missing
- `invalid-yaml.md` - Malformed YAML
- `no-frontmatter.md` - Plain markdown
- `empty-file.md` - Empty file
- `large-file.md` - Performance testing

## Acceptance Criteria
- [ ] Successfully parses valid YAML frontmatter
- [ ] Handles files without frontmatter gracefully
- [ ] Validates all defined metadata fields
- [ ] Provides meaningful error messages
- [ ] Returns default values for missing optional fields
- [ ] Processes files with different encodings
- [ ] Performance acceptable for files up to 10MB
- [ ] All unit tests pass
- [ ] Memory usage remains stable during batch operations

## Dependencies
- **Step 1**: Project setup must be completed
- YAML parsing library installed
- TypeScript types defined

## Estimated Effort
**4-6 hours**

## Files to Implement
1. `src/promptStore/MetadataParser.ts` (main implementation)
2. `src/promptStore/types.ts` (add parsing-related types)
3. `test/promptStore/MetadataParser.test.ts` (unit tests)
4. `test/fixtures/prompt-samples/` (test markdown files)

## Next Step
Proceed to **Step 3: File System Operations** once metadata parsing is solid and tested.
