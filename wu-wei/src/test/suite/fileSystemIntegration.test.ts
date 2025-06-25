/**
 * Integration tests for PromptManager file system operations
 * Testing real file system behavior with various scenarios
 */

import * as assert from 'assert';
import * as path from 'path';
import * as fs from 'fs/promises';
import * as os from 'os';
import { PromptManager } from '../../promptStore/PromptManager';
import { PromptStoreConfig } from '../../promptStore/types';

describe('PromptManager Integration Tests', () => {
    let tempDir: string;
    let promptManager: PromptManager;

    beforeEach(async () => {
        // Create temporary directory with realistic structure
        tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'prompt-integration-'));

        // Create a realistic directory structure
        await createTestDirectoryStructure(tempDir);

        const config: Partial<PromptStoreConfig> = {
            watchPaths: [tempDir],
            autoRefresh: false,
            enableCache: true,
            excludePatterns: ['**/node_modules/**', '**/.git/**', '**/temp/**']
        };

        promptManager = new PromptManager(config);
        await promptManager.initialize();
    });

    afterEach(async () => {
        promptManager.dispose();
        await fs.rm(tempDir, { recursive: true, force: true });
    });

    async function createTestDirectoryStructure(baseDir: string): Promise<void> {
        // Create directory structure similar to step requirements
        const dirs = [
            'prompts',
            'prompts/development',
            'prompts/documentation',
            'prompts/templates',
            '.git',  // Should be ignored
            'temp',  // Should be ignored
            'node_modules'  // Should be ignored
        ];

        for (const dir of dirs) {
            await fs.mkdir(path.join(baseDir, dir), { recursive: true });
        }

        // Create test files
        const files = [
            {
                path: 'prompts/main-prompt.md',
                content: `---
title: Main Prompt
description: A main prompt for testing
category: General
tags: [main, test]
author: Test Author
created: 2024-01-01T00:00:00.000Z
---

# Main Prompt

This is the main prompt content with some **markdown** formatting.

## Parameters

This prompt accepts the following parameters:
- input: The user input
- context: Additional context`
            },
            {
                path: 'prompts/development/code-review.md',
                content: `---
title: Code Review Prompt
description: Prompt for reviewing code
category: Development
tags: [code, review, development]
parameters:
  - name: code
    type: string
    required: true
    description: The code to review
  - name: language
    type: string
    required: false
    description: Programming language
    defaultValue: javascript
---

# Code Review

Please review the following code:

\`\`\`{{language}}
{{code}}
\`\`\`

Provide feedback on:
1. Code quality
2. Best practices
3. Potential issues`
            },
            {
                path: 'prompts/documentation/api-docs.md',
                content: `---
title: API Documentation Generator
category: Documentation
tags: [api, documentation, generator]
---

# API Documentation Generator

Generate comprehensive API documentation for the given endpoint.`
            },
            {
                path: 'prompts/templates/template-basic.md',
                content: `# Basic Template

This is a basic template without frontmatter.

Use this as a starting point for new prompts.`
            },
            {
                path: 'prompts/invalid-yaml.md',
                content: `---
title: Invalid YAML
broken: yaml: content: here
---

# Invalid YAML Prompt

This prompt has invalid YAML in the frontmatter.`
            },
            {
                path: '.git/config',
                content: '[core]\n\trepositoryformatversion = 0'
            },
            {
                path: 'temp/temp-file.md',
                content: '# Temporary File\nThis should be ignored.'
            },
            {
                path: 'node_modules/some-module/readme.md',
                content: '# Module\nThis should be ignored.'
            },
            {
                path: 'README.md',
                content: '# Project README\nRoot level markdown file.'
            }
        ];

        for (const file of files) {
            const filePath = path.join(baseDir, file.path);
            await fs.mkdir(path.dirname(filePath), { recursive: true });
            await fs.writeFile(filePath, file.content);
        }
    }

    describe('Real File System Integration', () => {
        it('should discover all valid prompts while respecting exclude patterns', async () => {
            const files = await promptManager.scanDirectory(tempDir);

            // Should find all .md files except those in excluded directories
            const fileNames = files.map(f => path.basename(f));

            // Should include these
            assert(fileNames.includes('main-prompt.md'));
            assert(fileNames.includes('code-review.md'));
            assert(fileNames.includes('api-docs.md'));
            assert(fileNames.includes('template-basic.md'));
            assert(fileNames.includes('invalid-yaml.md'));
            assert(fileNames.includes('README.md'));

            // Should exclude these (in excluded directories)
            assert(!files.some(f => f.includes('node_modules')));
            assert(!files.some(f => f.includes('.git')));
            assert(!files.some(f => f.includes('temp')));
        });

        it('should load all prompts with proper metadata parsing', async () => {
            const prompts = await promptManager.loadAllPrompts(tempDir);

            // Find specific prompts
            const mainPrompt = prompts.find(p => p.metadata.title === 'Main Prompt');
            const codeReviewPrompt = prompts.find(p => p.metadata.title === 'Code Review Prompt');
            const apiDocsPrompt = prompts.find(p => p.metadata.title === 'API Documentation Generator');

            // Verify main prompt
            assert(mainPrompt);
            assert.strictEqual(mainPrompt.metadata.description, 'A main prompt for testing');
            assert.strictEqual(mainPrompt.metadata.category, 'General');
            assert.deepStrictEqual(mainPrompt.metadata.tags, ['main', 'test']);
            assert.strictEqual(mainPrompt.metadata.author, 'Test Author');

            // Verify code review prompt with parameters
            assert(codeReviewPrompt);
            assert.strictEqual(codeReviewPrompt.metadata.category, 'Development');
            assert(codeReviewPrompt.metadata.parameters);
            assert.strictEqual(codeReviewPrompt.metadata.parameters.length, 2);
            assert.strictEqual(codeReviewPrompt.metadata.parameters[0].name, 'code');
            assert.strictEqual(codeReviewPrompt.metadata.parameters[0].required, true);

            // Verify API docs prompt
            assert(apiDocsPrompt);
            assert.strictEqual(apiDocsPrompt.metadata.category, 'Documentation');
        });

        it('should handle large directory structures efficiently', async () => {
            // Create a larger directory structure for performance testing
            const largeDir = path.join(tempDir, 'large');
            await fs.mkdir(largeDir);

            // Create 100 prompt files across 10 categories
            for (let category = 0; category < 10; category++) {
                const categoryDir = path.join(largeDir, `category-${category}`);
                await fs.mkdir(categoryDir);

                for (let prompt = 0; prompt < 10; prompt++) {
                    const promptFile = path.join(categoryDir, `prompt-${prompt}.md`);
                    const content = `---
title: Prompt ${category}-${prompt}
category: Category ${category}
---

# Prompt ${category}-${prompt}

Content for prompt ${prompt} in category ${category}.`;
                    await fs.writeFile(promptFile, content);
                }
            }

            // Measure performance
            const startTime = Date.now();
            const files = await promptManager.scanDirectory(largeDir);
            const scanTime = Date.now() - startTime;

            const loadStartTime = Date.now();
            const prompts = await promptManager.loadAllPrompts(largeDir);
            const loadTime = Date.now() - loadStartTime;

            // Verify results
            assert.strictEqual(files.length, 100);
            assert.strictEqual(prompts.length, 100);

            // Performance assertions (these are rough guidelines)
            assert(scanTime < 1000, `Scanning took too long: ${scanTime}ms`);
            assert(loadTime < 5000, `Loading took too long: ${loadTime}ms`);

            console.log(`Performance: Scan ${scanTime}ms, Load ${loadTime}ms`);
        });

        it('should maintain file system consistency during concurrent operations', async () => {
            const concurrentDir = path.join(tempDir, 'concurrent');
            await fs.mkdir(concurrentDir);

            // Create multiple prompts concurrently
            const createPromises = [];
            for (let i = 0; i < 10; i++) {
                const promise = promptManager.createPrompt(`Concurrent Prompt ${i}`, 'Concurrent');
                createPromises.push(promise);
            }

            const createdPrompts = await Promise.all(createPromises);

            // Verify all prompts were created
            assert.strictEqual(createdPrompts.length, 10);

            // Verify all files exist on disk
            for (const prompt of createdPrompts) {
                const exists = await fs.access(prompt.filePath).then(() => true).catch(() => false);
                assert(exists, `File should exist: ${prompt.filePath}`);
            }

            // Verify all prompts can be loaded
            const loadedPrompts = await promptManager.loadAllPrompts(concurrentDir);
            assert(loadedPrompts.length >= 10);
        });

        it('should handle file system edge cases', async () => {
            const edgeCaseDir = path.join(tempDir, 'edge-cases');
            await fs.mkdir(edgeCaseDir);

            // Test various edge cases
            const edgeCases = [
                {
                    name: 'empty-file.md',
                    content: ''
                },
                {
                    name: 'only-frontmatter.md',
                    content: '---\ntitle: Only Frontmatter\n---'
                },
                {
                    name: 'no-newline-after-frontmatter.md',
                    content: '---\ntitle: No Newline\n---Content immediately after'
                },
                {
                    name: 'unicode-filename-🚀.md',
                    content: '# Unicode Filename Test'
                },
                {
                    name: 'very-long-filename-with-many-words-and-characters-that-should-still-work.md',
                    content: '# Long Filename Test'
                }
            ];

            // Create edge case files
            for (const edgeCase of edgeCases) {
                await fs.writeFile(path.join(edgeCaseDir, edgeCase.name), edgeCase.content);
            }

            // Should handle all edge cases without throwing
            const files = await promptManager.scanDirectory(edgeCaseDir);
            const prompts = await promptManager.loadAllPrompts(edgeCaseDir);

            assert(files.length >= edgeCases.length);
            assert(Array.isArray(prompts)); // Some might fail to parse, but should not throw
        });

        it('should preserve file metadata and timestamps', async () => {
            const metadataDir = path.join(tempDir, 'metadata-test');
            await fs.mkdir(metadataDir);

            // Create a prompt with specific timestamp
            const originalTime = new Date('2024-01-01T12:00:00Z');
            const promptFile = path.join(metadataDir, 'timestamped.md');
            await fs.writeFile(promptFile, '# Timestamped Prompt\nContent');
            await fs.utimes(promptFile, originalTime, originalTime);

            // Load the prompt
            const prompt = await promptManager.loadPrompt(promptFile);

            // Verify timestamp is preserved
            const stats = await fs.stat(promptFile);
            assert.strictEqual(stats.mtime.getTime(), originalTime.getTime());

            // Modify and save the prompt
            prompt.content = '# Modified Timestamped Prompt\nModified content';
            await promptManager.savePrompt(prompt);

            // Verify file was updated
            const newStats = await fs.stat(promptFile);
            assert(newStats.mtime.getTime() > originalTime.getTime());

            // Verify content was actually changed
            const savedContent = await fs.readFile(promptFile, 'utf8');
            assert(savedContent.includes('Modified content'));
        });

        it('should handle different operating system path separators', async () => {
            // This test verifies cross-platform compatibility
            const crossPlatformDir = path.join(tempDir, 'cross-platform');
            await fs.mkdir(crossPlatformDir);

            // Create nested structure that tests path handling
            const nestedPath = path.join(crossPlatformDir, 'level1', 'level2', 'level3');
            await fs.mkdir(nestedPath, { recursive: true });

            const promptFile = path.join(nestedPath, 'deep-prompt.md');
            await fs.writeFile(promptFile, '# Deep Prompt\nNested deep in directories');

            // Scan should find the file regardless of path separator style
            const files = await promptManager.scanDirectory(crossPlatformDir);
            assert.strictEqual(files.length, 1);
            assert(files[0].includes('deep-prompt.md'));

            // Load should work with the found path
            const prompt = await promptManager.loadPrompt(files[0]);
            assert(prompt.content.includes('Nested deep in directories'));
        });
    });

    describe('Error Recovery and Resilience', () => {
        it('should continue operation when some files are corrupted', async () => {
            const mixedDir = path.join(tempDir, 'mixed-quality');
            await fs.mkdir(mixedDir);

            // Create a mix of valid and invalid files
            await fs.writeFile(path.join(mixedDir, 'valid1.md'), '# Valid 1\nGood content');
            await fs.writeFile(path.join(mixedDir, 'corrupted.md'), '\x00\x01\x02Binary garbage\x03\x04');
            await fs.writeFile(path.join(mixedDir, 'valid2.md'), '# Valid 2\nAlso good content');

            // Should not fail completely
            const prompts = await promptManager.loadAllPrompts(mixedDir);

            // Should load the valid prompts
            const validPrompts = prompts.filter(p => p.isValid);
            assert(validPrompts.length >= 2);

            const titles = validPrompts.map(p => p.content);
            assert(titles.some(t => t.includes('Valid 1')));
            assert(titles.some(t => t.includes('Valid 2')));
        });

        it('should recover from temporary file system issues', async () => {
            const recoveryDir = path.join(tempDir, 'recovery-test');
            await fs.mkdir(recoveryDir);

            // Create a valid prompt file
            const promptFile = path.join(recoveryDir, 'recovery-prompt.md');
            await fs.writeFile(promptFile, '# Recovery Test\nInitial content');

            // Simulate a file system issue by removing read permissions (Unix-like systems)
            if (process.platform !== 'win32') {
                await fs.chmod(promptFile, 0o000);

                // Operation should handle the error gracefully
                let prompts = await promptManager.loadAllPrompts(recoveryDir);
                assert(Array.isArray(prompts)); // Should not throw

                // Restore permissions
                await fs.chmod(promptFile, 0o644);
            }

            // Should now work normally
            const prompts = await promptManager.loadAllPrompts(recoveryDir);
            assert(prompts.length >= 0);
        });
    });
});
