/**
 * Unit tests for MetadataParser
 * Testing wu wei principle: gentle parsing that flows with content
 */

import assert from 'assert';
import * as fs from 'fs/promises';
import * as path from 'path';
import { MetadataParser } from '../../../promptStore/MetadataParser';
import { PromptMetadata, ValidationResult, ParsedPrompt } from '../../../promptStore/types';

suite('MetadataParser Tests', () => {
    let parser: MetadataParser;
    let tempDir: string;

    setup(async () => {
        parser = new MetadataParser();

        // Create temporary directory for test files
        tempDir = path.join(__dirname, 'test-metadata-' + Date.now());
        await fs.mkdir(tempDir, { recursive: true });
    });

    teardown(async () => {
        // Clean up temporary directory
        try {
            await fs.rm(tempDir, { recursive: true, force: true });
        } catch (error) {
            // Ignore cleanup errors
        }
    });

    suite('Frontmatter Extraction', () => {
        test('Should extract valid YAML frontmatter', () => {
            const content = `---
title: Test Prompt
description: A test prompt
category: testing
tags: [test, sample]
---

# Test Content

This is the content.`;

            const result = parser.extractFrontmatter(content);

            assert.strictEqual(result.metadata, `title: Test Prompt
description: A test prompt
category: testing
tags: [test, sample]`);
            assert.strictEqual(result.content.trim(), `# Test Content

This is the content.`);
        });

        test('Should handle content without frontmatter', () => {
            const content = `# Test Content

This is content without frontmatter.`;

            const result = parser.extractFrontmatter(content);

            assert.strictEqual(result.metadata, null);
            assert.strictEqual(result.content, content);
        });

        test('Should handle incomplete frontmatter (no closing delimiter)', () => {
            const content = `---
title: Test Prompt
description: Missing closing delimiter

# Content`;

            const result = parser.extractFrontmatter(content);

            assert.strictEqual(result.metadata, null);
            assert.strictEqual(result.content, content);
        });

        test('Should handle empty frontmatter', () => {
            const content = `---
---

# Content`;

            const result = parser.extractFrontmatter(content);

            assert.strictEqual(result.metadata, '');
            assert.strictEqual(result.content.trim(), '# Content');
        });

        test('Should handle different line endings', () => {
            const content = `---\r\ntitle: Test\r\n---\r\n\r\n# Content`;

            const result = parser.extractFrontmatter(content);

            assert.strictEqual(result.metadata, 'title: Test');
            assert.strictEqual(result.content.trim(), '# Content');
        });
    });

    suite('Content Parsing', () => {
        test('Should parse content with valid frontmatter', () => {
            const content = `---
title: Valid Prompt
description: Test description
category: test
tags: [tag1, tag2]
---

# Content

Test content here.`;

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert(result.metadata);
            assert.strictEqual(result.metadata.title, 'Valid Prompt');
            assert.strictEqual(result.metadata.description, 'Test description');
            assert.strictEqual(result.metadata.category, 'test');
            assert.deepStrictEqual(result.metadata.tags, ['tag1', 'tag2']);
            assert.strictEqual(result.content?.trim(), '# Content\n\nTest content here.');
        });

        test('Should parse content without frontmatter', () => {
            const content = `# Simple Content

Just content without metadata.`;

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert(result.metadata);
            assert.strictEqual(result.metadata.title, 'Untitled Prompt');
            assert.strictEqual(result.content, content);
        });

        test('Should handle invalid YAML in frontmatter', () => {
            const content = `---
title: Invalid YAML
invalid: yaml: syntax: [unclosed
---

# Content`;

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, false);
            assert(result.errors.length > 0);
            assert(result.errors.some(e => e.message.includes('Invalid YAML syntax')));
        });

        test('Should provide default metadata for invalid frontmatter', () => {
            const content = `---
invalid: yaml: syntax
---

# Content`;

            const result = parser.parseContent(content);

            assert(result.metadata);
            assert.strictEqual(result.metadata.title, 'Untitled Prompt');
            assert.strictEqual(result.metadata.category, 'General');
        });
    });

    suite('File Parsing', () => {
        test('Should parse valid file', async () => {
            const content = `---
title: File Test
description: Testing file parsing
category: test
tags: [file, test]
---

# File Content

This is file content.`;

            const filePath = path.join(tempDir, 'test.md');
            await fs.writeFile(filePath, content, 'utf8');

            const result = await parser.parseFile(filePath);

            assert.strictEqual(result.success, true);
            assert(result.prompt);
            assert.strictEqual(result.prompt.metadata.title, 'File Test');
            assert.strictEqual(result.prompt.fileName, 'test.md');
            assert.strictEqual(result.prompt.filePath, filePath);
        });

        test('Should handle non-existent file', async () => {
            const nonExistentPath = path.join(tempDir, 'non-existent.md');

            const result = await parser.parseFile(nonExistentPath);

            assert.strictEqual(result.success, false);
            assert(result.errors.length > 0);
            assert(result.errors.some(e => e.message.includes('Failed to parse file')));
        });

        test('Should cache file results', async () => {
            const content = `---
title: Cache Test
---

# Content`;

            const filePath = path.join(tempDir, 'cache-test.md');
            await fs.writeFile(filePath, content, 'utf8');

            // First parse
            const result1 = await parser.parseFile(filePath);
            assert.strictEqual(result1.success, true);

            // Second parse (should use cache)
            const result2 = await parser.parseFile(filePath);
            assert.strictEqual(result2.success, true);
            assert.strictEqual(result1.prompt?.id, result2.prompt?.id);
        });

        test('Should update cache when file is modified', async () => {
            const filePath = path.join(tempDir, 'modified-test.md');

            // Write initial content
            await fs.writeFile(filePath, `---
title: Original Title
---

# Original Content`, 'utf8');

            const result1 = await parser.parseFile(filePath);
            assert.strictEqual(result1.prompt?.metadata.title, 'Original Title');

            // Wait a bit to ensure different modification time
            await new Promise(resolve => setTimeout(resolve, 10));

            // Modify file
            await fs.writeFile(filePath, `---
title: Modified Title
---

# Modified Content`, 'utf8');

            const result2 = await parser.parseFile(filePath);
            assert.strictEqual(result2.prompt?.metadata.title, 'Modified Title');
        });
    });

    suite('Metadata Validation', () => {
        test('Should validate valid metadata', () => {
            const metadata: PromptMetadata = {
                title: 'Valid Title',
                description: 'Valid description',
                category: 'valid-category',
                tags: ['tag1', 'tag2']
            };

            const result = parser.validateMetadata(metadata);

            assert.strictEqual(result.isValid, true);
            assert.strictEqual(result.errors.length, 0);
        });

        test('Should detect missing title', () => {
            const metadata: PromptMetadata = {
                title: '',
                description: 'Description without title'
            };

            const result = parser.validateMetadata(metadata);

            assert.strictEqual(result.isValid, false);
            assert(result.errors.some(e => e.field === 'title' && e.message.includes('required')));
        });

        test('Should detect title too long', () => {
            const metadata: PromptMetadata = {
                title: 'A'.repeat(250), // Too long
                description: 'Valid description'
            };

            const result = parser.validateMetadata(metadata);

            assert.strictEqual(result.isValid, false);
            assert(result.errors.some(e => e.field === 'title' && e.message.includes('maximum length')));
        });

        test('Should detect invalid title characters', () => {
            const metadata: PromptMetadata = {
                title: 'Title with <invalid> characters',
                description: 'Valid description'
            };

            const result = parser.validateMetadata(metadata);

            assert(result.warnings.some(w => w.field === 'title' && w.message.includes('special characters')));
        });

        test('Should detect very long description', () => {
            const metadata: PromptMetadata = {
                title: 'Valid Title',
                description: 'A'.repeat(2500) // Very long
            };

            const result = parser.validateMetadata(metadata);

            assert(result.warnings.some(w => w.field === 'description' && w.message.includes('very long')));
        });

        test('Should detect invalid category characters', () => {
            const metadata: PromptMetadata = {
                title: 'Valid Title',
                category: 'invalid/category'
            };

            const result = parser.validateMetadata(metadata);

            assert(result.warnings.some(w => w.field === 'category' && w.message.includes('invalid characters')));
        });

        test('Should detect too many tags', () => {
            const metadata: PromptMetadata = {
                title: 'Valid Title',
                tags: Array(25).fill('tag') // Too many tags
            };

            const result = parser.validateMetadata(metadata);

            assert(result.warnings.some(w => w.field === 'tags' && w.message.includes('Too many tags')));
        });

        test('Should detect invalid tag characters', () => {
            const metadata: PromptMetadata = {
                title: 'Valid Title',
                tags: ['valid-tag', 'invalid tag with spaces']
            };

            const result = parser.validateMetadata(metadata);

            assert(result.warnings.some(w => w.field.includes('tags[1]') && w.message.includes('invalid characters')));
        });

        test('Should detect long tags', () => {
            const metadata: PromptMetadata = {
                title: 'Valid Title',
                tags: ['a'.repeat(35)] // Too long
            };

            const result = parser.validateMetadata(metadata);

            assert(result.warnings.some(w => w.field.includes('tags[0]') && w.message.includes('too long')));
        });

        test('Should warn about missing version', () => {
            const metadata: PromptMetadata = {
                title: 'Valid Title'
            };

            const result = parser.validateMetadata(metadata);

            assert(result.warnings.some(w => w.field === 'version' && w.message.includes('not specified')));
        });

        test('Should validate parameter definitions', () => {
            const metadataWithParams = {
                title: 'Valid Title',
                parameters: [
                    { name: 'validParam', type: 'string', description: 'Valid parameter' },
                    { name: 'invalid-param-name!', type: 'string' }, // Invalid name
                    { type: 'string' } // Missing name
                ]
            } as any;

            const result = parser.validateMetadata(metadataWithParams);

            assert(result.errors.some(e => e.field.includes('parameters[1].name')));
            assert(result.errors.some(e => e.field.includes('parameters[2].name')));
        });
    });

    suite('Default Metadata', () => {
        test('Should provide default metadata', () => {
            const defaults = parser.getDefaultMetadata();

            assert.strictEqual(defaults.title, 'Untitled Prompt');
            assert.strictEqual(defaults.description, '');
            assert.strictEqual(defaults.category, 'General');
            assert(Array.isArray(defaults.tags));
            assert.strictEqual(defaults.tags?.length, 0);
        });
    });

    suite('Cache Management', () => {
        test('Should clear cache', async () => {
            const content = `---
title: Cache Test
---

# Content`;

            const filePath = path.join(tempDir, 'cache-clear-test.md');
            await fs.writeFile(filePath, content, 'utf8');

            // Parse file to populate cache
            await parser.parseFile(filePath);

            // Clear cache
            parser.clearCache();

            // Get cache stats
            const stats = parser.getCacheStats();
            assert.strictEqual(stats.size, 0);
            assert.strictEqual(stats.entries.length, 0);
        });

        test('Should provide cache statistics', async () => {
            const filePaths = ['test1.md', 'test2.md', 'test3.md'];

            for (const fileName of filePaths) {
                const filePath = path.join(tempDir, fileName);
                await fs.writeFile(filePath, `---
title: ${fileName}
---

# Content`, 'utf8');
                await parser.parseFile(filePath);
            }

            const stats = parser.getCacheStats();
            assert.strictEqual(stats.size, 3);
            assert.strictEqual(stats.entries.length, 3);
        });
    });

    suite('Edge Cases', () => {
        test('Should handle file with only frontmatter', () => {
            const content = `---
title: Only Frontmatter
---`;

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.metadata?.title, 'Only Frontmatter');
            assert.strictEqual(result.content, '');
        });

        test('Should handle empty file', () => {
            const content = '';

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.metadata?.title, 'Untitled Prompt');
            assert.strictEqual(result.content, '');
        });

        test('Should handle frontmatter with complex nested structures', () => {
            const content = `---
title: Complex Structure
metadata:
  nested:
    value: test
  array: [1, 2, 3]
tags:
  - complex
  - nested
---

# Content`;

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.metadata?.title, 'Complex Structure');
        });

        test('Should handle non-object frontmatter', () => {
            const content = `---
this is not an object
---

# Content`;

            const result = parser.parseContent(content);

            // Should fall back to defaults when frontmatter is not an object
            assert.strictEqual(result.metadata?.title, 'Untitled Prompt');
        });

        test('Should handle tags that are not an array', () => {
            const content = `---
title: Invalid Tags
tags: not-an-array
---

# Content`;

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert(Array.isArray(result.metadata?.tags));
            assert.strictEqual(result.metadata?.tags?.length, 0);
        });
    });
}); 