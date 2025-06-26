/**
 * Unit tests for MetadataParser
 */

import * as assert from 'assert';
import * as path from 'path';
import * as fs from 'fs';
import { MetadataParser } from '../../promptStore/MetadataParser';
import { PromptMetadata } from '../../promptStore/types';

describe('MetadataParser', () => {
    let parser: MetadataParser;
    let tempDir: string;

    beforeEach(() => {
        parser = new MetadataParser();
        tempDir = path.join(__dirname, '..', '..', '..', 'test-fixtures');
    });

    afterEach(() => {
        parser.clearCache();
    });

    describe('parseContent', () => {
        it('should parse valid YAML frontmatter', () => {
            const content = `---
title: Test Prompt
description: A test prompt for unit testing
category: Testing
tags: [test, unit]
author: Test Author
version: 1.0.0
parameters:
  - name: testParam
    type: string
    required: true
    description: A test parameter
---

This is the prompt content.`;

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.metadata?.title, 'Test Prompt');
            assert.strictEqual(result.metadata?.description, 'A test prompt for unit testing');
            assert.strictEqual(result.metadata?.category, 'Testing');
            assert.deepStrictEqual(result.metadata?.tags, ['test', 'unit']);
            assert.strictEqual(result.content, 'This is the prompt content.');
            assert.strictEqual(result.errors.length, 0);
        });

        it('should handle content without frontmatter', () => {
            const content = 'This is just plain content without frontmatter.';

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.metadata?.title, 'Untitled Prompt');
            assert.strictEqual(result.content, content);
            assert.strictEqual(result.errors.length, 0);
        });

        it('should handle invalid YAML syntax', () => {
            const content = `---
title: Test Prompt
invalid: yaml: syntax: here
  - bad indentation
---

Content here.`;

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, false);
            assert.strictEqual(result.errors.length, 1);
            assert.strictEqual(result.errors[0].field, 'frontmatter');
            assert(result.errors[0].message.includes('Invalid YAML syntax'));
        });

        it('should handle partial frontmatter', () => {
            const content = `---
title: Partial Prompt
---

Content with minimal metadata.`;

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.metadata?.title, 'Partial Prompt');
            assert.strictEqual(result.metadata?.category, 'General');
            assert.deepStrictEqual(result.metadata?.tags, []);
            assert.strictEqual(result.content, 'Content with minimal metadata.');
        });

        it('should handle empty file', () => {
            const content = '';

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.metadata?.title, 'Untitled Prompt');
            assert.strictEqual(result.content, '');
        });

        it('should handle frontmatter without closing delimiter', () => {
            const content = `---
title: Unclosed Frontmatter
description: This frontmatter has no closing delimiter

This should be treated as regular content.`;

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.metadata?.title, 'Untitled Prompt');
            assert.strictEqual(result.content, content);
        });

        it('should handle Windows line endings', () => {
            const content = `---\r\ntitle: Windows Test\r\ndescription: Testing Windows line endings\r\n---\r\n\r\nContent with CRLF line endings.`;

            const result = parser.parseContent(content);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.metadata?.title, 'Windows Test');
            assert.strictEqual(result.metadata?.description, 'Testing Windows line endings');
            assert.strictEqual(result.content, 'Content with CRLF line endings.');
        });
    });

    describe('validateMetadata', () => {
        it('should validate required title', () => {
            const metadata: PromptMetadata = {
                title: '',
                category: 'Test',
                tags: []
            };

            const result = parser.validateMetadata(metadata);

            assert.strictEqual(result.isValid, false);
            assert.strictEqual(result.errors.length, 1);
            assert.strictEqual(result.errors[0].field, 'title');
            assert.strictEqual(result.errors[0].message, 'Title is required');
        });

        it('should validate title length', () => {
            const longTitle = 'A'.repeat(250);
            const metadata: PromptMetadata = {
                title: longTitle,
                category: 'Test',
                tags: [],
            };

            const result = parser.validateMetadata(metadata);

            assert.strictEqual(result.isValid, false);
            assert.strictEqual(result.errors.length, 1);
            assert.strictEqual(result.errors[0].field, 'title');
            assert(result.errors[0].message.includes('exceeds maximum length'));
        });

        it('should validate tag count', () => {
            const manyTags = Array.from({ length: 25 }, (_, i) => `tag${i}`);
            const metadata: PromptMetadata = {
                title: 'Test',
                category: 'Test',
                tags: manyTags,
            };

            const result = parser.validateMetadata(metadata);

            assert.strictEqual(result.warnings.length >= 1, true);
            assert(result.warnings.some(w => w.field === 'tags' && w.message.includes('Too many tags')));
        });

        it('should validate version format', () => {
            const metadata: PromptMetadata = {
                title: 'Test',
                category: 'Test',
                tags: [],
            };

            const result = parser.validateMetadata(metadata);

            assert(result.warnings.some(w => w.field === 'version'));
        });

        it('should validate parameter names', () => {
            const metadata: PromptMetadata = {
                title: 'Test',
                category: 'Test',
                tags: [],
            };

            const result = parser.validateMetadata(metadata);

            assert.strictEqual(result.isValid, false);
            assert(result.errors.some(e => e.field === 'parameters[0].name'));
        });
    });

    describe('extractFrontmatter', () => {
        it('should extract valid frontmatter', () => {
            const content = `---
title: Test
---
Content here`;

            const result = parser.extractFrontmatter(content);

            assert.strictEqual(result.metadata, 'title: Test');
            assert.strictEqual(result.content, 'Content here');
        });

        it('should return null for no frontmatter', () => {
            const content = 'Just content';

            const result = parser.extractFrontmatter(content);

            assert.strictEqual(result.metadata, null);
            assert.strictEqual(result.content, content);
        });

        it('should handle empty frontmatter', () => {
            const content = `---
---
Content after empty frontmatter`;

            const result = parser.extractFrontmatter(content);

            assert.strictEqual(result.metadata, '');
            assert.strictEqual(result.content, 'Content after empty frontmatter');
        });
    });

    describe('getDefaultMetadata', () => {
        it('should return valid default metadata', () => {
            const defaults = parser.getDefaultMetadata();

            assert.strictEqual(defaults.title, 'Untitled Prompt');
            assert.strictEqual(defaults.category, 'General');
            assert(Array.isArray(defaults.tags));
        });
    });

    describe('cache functionality', () => {
        it('should track cache statistics', () => {
            const stats = parser.getCacheStats();

            assert.strictEqual(typeof stats.size, 'number');
            assert(Array.isArray(stats.entries));
        });

        it('should clear cache', () => {
            parser.clearCache();
            const stats = parser.getCacheStats();

            assert.strictEqual(stats.size, 0);
            assert.strictEqual(stats.entries.length, 0);
        });
    });
});
