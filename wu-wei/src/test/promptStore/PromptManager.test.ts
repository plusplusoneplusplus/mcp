/**
 * Unit tests for PromptManager
 * Testing wu wei principle: comprehensive core business logic validation
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import * as fs from 'fs/promises';
import * as path from 'path';
import { PromptManager } from '../../promptStore/PromptManager';
import { Prompt, PromptStoreConfig, SearchFilter } from '../../promptStore/types';

suite('PromptManager Tests', () => {
    let promptManager: PromptManager;
    let testConfig: Partial<PromptStoreConfig>;
    let tempDir: string;

    setup(async () => {
        // Create temporary directory for testing
        tempDir = path.join(__dirname, 'test-prompts-' + Date.now());
        await fs.mkdir(tempDir, { recursive: true });

        testConfig = {
            rootDirectory: tempDir,
            watchPaths: [tempDir],
            filePatterns: ['**/*.md'],
            excludePatterns: ['**/node_modules/**'],
            autoRefresh: false, // Disable for testing
            refreshInterval: 1000,
            enableCache: true,
            maxCacheSize: 100,
            sortBy: 'name',
            sortOrder: 'asc',
            showCategories: true,
            showTags: true,
            enableSearch: true
        };

        promptManager = new PromptManager(testConfig);
    });

    teardown(async () => {
        promptManager.dispose();

        // Clean up temporary directory
        try {
            await fs.rm(tempDir, { recursive: true, force: true });
        } catch (error) {
            // Ignore cleanup errors
        }
    });

    suite('Initialization', () => {
        test('Should create PromptManager instance', () => {
            assert(promptManager instanceof PromptManager);
        });

        test('Should have configuration', () => {
            const config = promptManager.getConfig();
            assert(typeof config === 'object');
            assert.strictEqual(config.autoRefresh, false);
        });

        test('Should have empty prompts initially', () => {
            const prompts = promptManager.getAllPrompts();
            assert(Array.isArray(prompts));
            assert.strictEqual(prompts.length, 0);
        });
    });

    suite('Prompt Loading', () => {
        test('Should load prompts from file system', async () => {
            // Create test prompt file
            const testPromptContent = `---
title: Test Prompt
description: A test prompt
category: testing
tags: [test, sample]
---

# Test Prompt

This is a test prompt content.`;

            const promptPath = path.join(tempDir, 'test-prompt.md');
            await fs.writeFile(promptPath, testPromptContent, 'utf8');

            // Refresh prompts
            await promptManager.refreshPrompts();

            const prompts = promptManager.getAllPrompts();
            assert.strictEqual(prompts.length, 1);
            assert.strictEqual(prompts[0].metadata.title, 'Test Prompt');
            assert.strictEqual(prompts[0].metadata.category, 'testing');
            assert.deepStrictEqual(prompts[0].metadata.tags, ['test', 'sample']);
        });

        test('Should handle prompts without frontmatter', async () => {
            const testPromptContent = `# Simple Prompt

This is a simple prompt without frontmatter.`;

            const promptPath = path.join(tempDir, 'simple-prompt.md');
            await fs.writeFile(promptPath, testPromptContent, 'utf8');

            await promptManager.refreshPrompts();

            const prompts = promptManager.getAllPrompts();
            assert.strictEqual(prompts.length, 1);
            assert.strictEqual(prompts[0].metadata.title, 'Simple Prompt'); // Should extract from filename
        });

        test('Should ignore non-markdown files', async () => {
            await fs.writeFile(path.join(tempDir, 'test.txt'), 'Not a markdown file', 'utf8');
            await fs.writeFile(path.join(tempDir, 'test.js'), '// JavaScript file', 'utf8');

            await promptManager.refreshPrompts();

            const prompts = promptManager.getAllPrompts();
            assert.strictEqual(prompts.length, 0);
        });

        test('Should exclude files based on patterns', async () => {
            // Create excluded directory
            const excludedDir = path.join(tempDir, 'node_modules');
            await fs.mkdir(excludedDir, { recursive: true });
            await fs.writeFile(path.join(excludedDir, 'excluded.md'), '# Excluded', 'utf8');

            // Create included file
            await fs.writeFile(path.join(tempDir, 'included.md'), '# Included', 'utf8');

            await promptManager.refreshPrompts();

            const prompts = promptManager.getAllPrompts();
            assert.strictEqual(prompts.length, 1);
            assert.strictEqual(prompts[0].metadata.title, 'Included');
        });

        test('Should handle nested directories', async () => {
            const categoryDir = path.join(tempDir, 'development');
            await fs.mkdir(categoryDir, { recursive: true });

            const promptContent = `---
title: Dev Prompt
category: development
---

# Development Prompt`;

            await fs.writeFile(path.join(categoryDir, 'dev-prompt.md'), promptContent, 'utf8');

            await promptManager.refreshPrompts();

            const prompts = promptManager.getAllPrompts();
            assert.strictEqual(prompts.length, 1);
            assert.strictEqual(prompts[0].metadata.category, 'development');
        });
    });

    suite('Prompt Search', () => {
        setup(async () => {
            // Create multiple test prompts
            const prompts = [
                {
                    filename: 'javascript-tutorial.md',
                    content: `---
title: JavaScript Tutorial
description: Learn JavaScript fundamentals
category: programming
tags: [javascript, tutorial, web]
---

# JavaScript Tutorial

Learn the basics of JavaScript programming.`
                },
                {
                    filename: 'python-guide.md',
                    content: `---
title: Python Guide
description: Python programming guide
category: programming
tags: [python, guide]
---

# Python Programming Guide

A comprehensive guide to Python.`
                },
                {
                    filename: 'meeting-notes.md',
                    content: `---
title: Meeting Notes Template
description: Template for meeting notes
category: productivity
tags: [meeting, template]
---

# Meeting Notes

Template for taking meeting notes.`
                }
            ];

            for (const prompt of prompts) {
                await fs.writeFile(path.join(tempDir, prompt.filename), prompt.content, 'utf8');
            }

            await promptManager.refreshPrompts();
        });

        test('Should search by query text', () => {
            const filter: SearchFilter = { query: 'javascript' };
            const results = promptManager.searchPrompts(filter);

            assert.strictEqual(results.length, 1);
            assert.strictEqual(results[0].metadata.title, 'JavaScript Tutorial');
        });

        test('Should search by category', () => {
            const filter: SearchFilter = { category: 'programming' };
            const results = promptManager.searchPrompts(filter);

            assert.strictEqual(results.length, 2);
            assert(results.some(p => p.metadata.title === 'JavaScript Tutorial'));
            assert(results.some(p => p.metadata.title === 'Python Guide'));
        });

        test('Should search by tags', () => {
            const filter: SearchFilter = { tags: ['tutorial'] };
            const results = promptManager.searchPrompts(filter);

            assert.strictEqual(results.length, 1);
            assert.strictEqual(results[0].metadata.title, 'JavaScript Tutorial');
        });

        test('Should search by multiple criteria', () => {
            const filter: SearchFilter = {
                query: 'guide',
                category: 'programming'
            };
            const results = promptManager.searchPrompts(filter);

            assert.strictEqual(results.length, 1);
            assert.strictEqual(results[0].metadata.title, 'Python Guide');
        });

        test('Should return empty results for no matches', () => {
            const filter: SearchFilter = { query: 'nonexistent' };
            const results = promptManager.searchPrompts(filter);

            assert.strictEqual(results.length, 0);
        });
    });

    suite('Prompt Management', () => {
        test('Should get prompt by ID', async () => {
            const promptContent = `---
title: Test Prompt
---

# Test Content`;

            const promptPath = path.join(tempDir, 'test.md');
            await fs.writeFile(promptPath, promptContent, 'utf8');
            await promptManager.refreshPrompts();

            const prompts = promptManager.getAllPrompts();
            const promptId = prompts[0].id;

            const retrievedPrompt = promptManager.getPrompt(promptId);
            assert(retrievedPrompt);
            assert.strictEqual(retrievedPrompt.metadata.title, 'Test Prompt');
        });

        test('Should return undefined for non-existent prompt ID', () => {
            const prompt = promptManager.getPrompt('non-existent-id');
            assert.strictEqual(prompt, undefined);
        });

        test('Should create new prompt', async () => {
            const prompt = await promptManager.createPrompt('New Prompt', 'test-category');

            assert(prompt);
            assert.strictEqual(prompt.metadata.title, 'New Prompt');
            assert.strictEqual(prompt.metadata.category, 'test-category');
            assert(prompt.filePath.includes('new-prompt.md'));

            // Verify file was created
            const fileExists = await fs.access(prompt.filePath).then(() => true).catch(() => false);
            assert(fileExists);
        });

        test('Should save prompt to file system', async () => {
            const prompt: Prompt = {
                id: 'test-prompt',
                filePath: path.join(tempDir, 'save-test.md'),
                fileName: 'save-test.md',
                metadata: {
                    title: 'Save Test',
                    description: 'Test saving',
                    category: 'test',
                    tags: ['save', 'test']
                },
                content: 'Test content',
                lastModified: new Date(),
                isValid: true
            };

            await promptManager.savePrompt(prompt);

            // Verify file was saved
            const fileContent = await fs.readFile(prompt.filePath, 'utf8');
            assert(fileContent.includes('title: Save Test'));
            assert(fileContent.includes('Test content'));
        });

        test('Should delete prompt file', async () => {
            const promptPath = path.join(tempDir, 'delete-test.md');
            await fs.writeFile(promptPath, '# Delete Test', 'utf8');

            await promptManager.deletePrompt(promptPath);

            // Verify file was deleted
            const fileExists = await fs.access(promptPath).then(() => true).catch(() => false);
            assert(!fileExists);
        });
    });

    suite('Configuration Updates', () => {
        test('Should update configuration', () => {
            const newConfig = { autoRefresh: true, sortBy: 'modified' as const };
            promptManager.updateConfig(newConfig);

            const config = promptManager.getConfig();
            assert.strictEqual(config.autoRefresh, true);
            assert.strictEqual(config.sortBy, 'modified');
        });

        test('Should maintain existing config values when updating', () => {
            const originalConfig = promptManager.getConfig();
            const newConfig = { autoRefresh: true };
            promptManager.updateConfig(newConfig);

            const updatedConfig = promptManager.getConfig();
            assert.strictEqual(updatedConfig.autoRefresh, true);
            assert.strictEqual(updatedConfig.enableCache, originalConfig.enableCache);
        });
    });

    suite('Event Handling', () => {
        test('Should emit events when prompts change', (done) => {
            let eventFired = false;

            const disposable = promptManager.onPromptsChanged((prompts) => {
                eventFired = true;
                assert(Array.isArray(prompts));
                disposable.dispose();
                done();
            });

            // Trigger event by refreshing prompts
            promptManager.refreshPrompts().catch(done);
        });
    });

    suite('Sorting', () => {
        setup(async () => {
            const prompts = [
                { name: 'z-prompt.md', title: 'Z Prompt', date: new Date('2023-01-01') },
                { name: 'a-prompt.md', title: 'A Prompt', date: new Date('2023-01-03') },
                { name: 'm-prompt.md', title: 'M Prompt', date: new Date('2023-01-02') }
            ];

            for (const prompt of prompts) {
                const content = `---
title: ${prompt.title}
---

# ${prompt.title}`;
                await fs.writeFile(path.join(tempDir, prompt.name), content, 'utf8');

                // Set file modification time
                await fs.utimes(path.join(tempDir, prompt.name), prompt.date, prompt.date);
            }

            await promptManager.refreshPrompts();
        });

        test('Should sort by name ascending', () => {
            promptManager.updateConfig({ sortBy: 'name', sortOrder: 'asc' });
            const prompts = promptManager.getAllPrompts();

            assert.strictEqual(prompts[0].metadata.title, 'A Prompt');
            assert.strictEqual(prompts[1].metadata.title, 'M Prompt');
            assert.strictEqual(prompts[2].metadata.title, 'Z Prompt');
        });

        test('Should sort by name descending', () => {
            promptManager.updateConfig({ sortBy: 'name', sortOrder: 'desc' });
            const prompts = promptManager.getAllPrompts();

            assert.strictEqual(prompts[0].metadata.title, 'Z Prompt');
            assert.strictEqual(prompts[1].metadata.title, 'M Prompt');
            assert.strictEqual(prompts[2].metadata.title, 'A Prompt');
        });

        test('Should sort by modified date', () => {
            promptManager.updateConfig({ sortBy: 'modified', sortOrder: 'asc' });
            const prompts = promptManager.getAllPrompts();

            // Should be ordered by modification date
            assert.strictEqual(prompts[0].metadata.title, 'Z Prompt'); // 2023-01-01
            assert.strictEqual(prompts[1].metadata.title, 'M Prompt'); // 2023-01-02
            assert.strictEqual(prompts[2].metadata.title, 'A Prompt'); // 2023-01-03
        });
    });

    suite('Error Handling', () => {
        test('Should handle missing directory gracefully', async () => {
            const nonExistentDir = path.join(tempDir, 'non-existent');
            promptManager.updateConfig({ watchPaths: [nonExistentDir] });

            // Should not throw error
            await promptManager.refreshPrompts();

            const prompts = promptManager.getAllPrompts();
            assert.strictEqual(prompts.length, 0);
        });

        test('Should handle corrupted prompt files gracefully', async () => {
            // Create file with invalid YAML frontmatter
            const corruptedContent = `---
title: Invalid YAML
invalid: yaml: syntax: error
---

# Content`;

            await fs.writeFile(path.join(tempDir, 'corrupted.md'), corruptedContent, 'utf8');
            await fs.writeFile(path.join(tempDir, 'valid.md'), '# Valid Prompt', 'utf8');

            await promptManager.refreshPrompts();

            // Should still load valid prompts
            const prompts = promptManager.getAllPrompts();
            assert.strictEqual(prompts.length, 1);
            assert.strictEqual(prompts[0].metadata.title, 'Valid Prompt');
        });
    });
}); 