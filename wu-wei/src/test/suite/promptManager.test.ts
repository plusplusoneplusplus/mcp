/**
 * Unit tests for PromptManager file system operations
 * Testing the core file discovery, reading, and writing functionality
 */

import assert from 'assert';
import * as path from 'path';
import * as fs from 'fs/promises';
import * as os from 'os';
import { PromptManager } from '../../promptStore/PromptManager';
import { Prompt, PromptStoreConfig } from '../../promptStore/types';

describe('PromptManager File System Operations', () => {
    let tempDir: string;
    let promptManager: PromptManager;
    let testConfig: Partial<PromptStoreConfig>;

    beforeEach(async () => {
        // Create temporary directory for tests
        tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'prompt-manager-test-'));

        testConfig = {
            watchPaths: [tempDir],
            autoRefresh: false,
            enableCache: false
        };

        promptManager = new PromptManager(testConfig);
    });

    afterEach(async () => {
        // Clean up
        promptManager.dispose();
        await fs.rm(tempDir, { recursive: true, force: true });
    });

    describe('Directory Scanning', () => {
        it('should discover markdown files in flat directory', async () => {
            // Create test files
            await fs.writeFile(path.join(tempDir, 'prompt1.md'), '# Test Prompt 1\nContent');
            await fs.writeFile(path.join(tempDir, 'prompt2.md'), '# Test Prompt 2\nContent');
            await fs.writeFile(path.join(tempDir, 'not-a-prompt.txt'), 'Regular text file');

            const files = await promptManager.scanDirectory(tempDir);

            assert.strictEqual(files.length, 2);
            assert(files.some((f: string) => f.endsWith('prompt1.md')));
            assert(files.some((f: string) => f.endsWith('prompt2.md')));
        });

        it('should discover markdown files in nested directories', async () => {
            // Create nested directory structure
            const category1Dir = path.join(tempDir, 'category1');
            const category2Dir = path.join(tempDir, 'category2');
            await fs.mkdir(category1Dir);
            await fs.mkdir(category2Dir);

            await fs.writeFile(path.join(category1Dir, 'nested1.md'), '# Nested 1\nContent');
            await fs.writeFile(path.join(category2Dir, 'nested2.md'), '# Nested 2\nContent');
            await fs.writeFile(path.join(tempDir, 'root.md'), '# Root\nContent');

            const files = await promptManager.scanDirectory(tempDir);

            assert.strictEqual(files.length, 3);
            assert(files.some((f: string) => f.includes('category1') && f.endsWith('nested1.md')));
            assert(files.some((f: string) => f.includes('category2') && f.endsWith('nested2.md')));
            assert(files.some((f: string) => f.endsWith('root.md')));
        });

        it('should ignore hidden files and directories', async () => {
            // Create hidden files and directories
            await fs.mkdir(path.join(tempDir, '.hidden-dir'));
            await fs.writeFile(path.join(tempDir, '.hidden-file.md'), '# Hidden\nContent');
            await fs.writeFile(path.join(tempDir, '.hidden-dir', 'nested.md'), '# Nested Hidden\nContent');
            await fs.writeFile(path.join(tempDir, 'visible.md'), '# Visible\nContent');

            const files = await promptManager.scanDirectory(tempDir);

            assert.strictEqual(files.length, 1);
            assert(files[0].endsWith('visible.md'));
        });

        it('should handle non-existent directories gracefully', async () => {
            const nonExistentDir = path.join(tempDir, 'does-not-exist');

            const files = await promptManager.scanDirectory(nonExistentDir);

            assert.strictEqual(files.length, 0);
        });
    });

    describe('Prompt Loading', () => {
        it('should load prompt with metadata', async () => {
            const promptFile = path.join(tempDir, 'test-prompt.md');
            const content = `---
title: Test Prompt
description: A test prompt
category: Testing
tags: [test, example]
---

# Test Prompt

This is a test prompt content.`;

            await fs.writeFile(promptFile, content);

            const prompt = await promptManager.loadPrompt(promptFile);

            assert.strictEqual(prompt.metadata.title, 'Test Prompt');
            assert.strictEqual(prompt.metadata.description, 'A test prompt');
            assert.strictEqual(prompt.metadata.category, 'Testing');
            assert.deepStrictEqual(prompt.metadata.tags, ['test', 'example']);
            assert(prompt.content.includes('This is a test prompt content.'));
        });

        it('should load prompt without metadata', async () => {
            const promptFile = path.join(tempDir, 'simple-prompt.md');
            const content = `# Simple Prompt

Just content, no metadata.`;

            await fs.writeFile(promptFile, content);

            const prompt = await promptManager.loadPrompt(promptFile);

            assert(prompt.content.includes('Simple Prompt'));
            assert(prompt.content.includes('Just content, no metadata.'));
        });

        it('should load all prompts from directory', async () => {
            // Create multiple prompt files
            await fs.writeFile(path.join(tempDir, 'prompt1.md'), '# Prompt 1\nContent 1');
            await fs.writeFile(path.join(tempDir, 'prompt2.md'), '# Prompt 2\nContent 2');

            // Create subdirectory with prompt
            const subDir = path.join(tempDir, 'subdir');
            await fs.mkdir(subDir);
            await fs.writeFile(path.join(subDir, 'prompt3.md'), '# Prompt 3\nContent 3');

            const prompts = await promptManager.loadAllPrompts(tempDir);

            assert.strictEqual(prompts.length, 3);
            const titles = prompts.map((p: Prompt) => p.content).join(' ');
            assert(titles.includes('Prompt 1'));
            assert(titles.includes('Prompt 2'));
            assert(titles.includes('Prompt 3'));
        });

        it('should handle invalid prompt files gracefully', async () => {
            const promptFile = path.join(tempDir, 'invalid.md');
            await fs.writeFile(promptFile, 'Invalid content without proper structure');

            const prompts = await promptManager.loadAllPrompts(tempDir);

            // Should not fail, but might not include the invalid prompt
            assert(Array.isArray(prompts));
        });
    });

    describe('Prompt Saving', () => {
        it('should save prompt with metadata', async () => {
            const promptFile = path.join(tempDir, 'new-prompt.md');
            const prompt: Prompt = {
                id: 'test-prompt',
                filePath: promptFile,
                fileName: 'new-prompt.md',
                metadata: {
                    title: 'New Prompt',
                    description: 'A newly created prompt',
                    category: 'Test',
                    tags: ['new', 'test']
                },
                content: '# New Prompt\n\nThis is new content.',
                lastModified: new Date(),
                isValid: true
            };

            await promptManager.savePrompt(prompt);

            // Verify file was created
            const exists = await fs.access(promptFile).then(() => true).catch(() => false);
            assert(exists);

            // Verify content
            const savedContent = await fs.readFile(promptFile, 'utf8');
            assert(savedContent.includes('title: New Prompt'));
            assert(savedContent.includes('description: A newly created prompt'));
            assert(savedContent.includes('This is new content.'));
        });

        it('should save prompt without metadata', async () => {
            const promptFile = path.join(tempDir, 'simple-new.md');
            const prompt: Prompt = {
                id: 'simple-test',
                filePath: promptFile,
                fileName: 'simple-new.md',
                metadata: {
                    title: 'Simple'
                },
                content: '# Simple Prompt\n\nJust content.',
                lastModified: new Date(),
                isValid: true
            };

            await promptManager.savePrompt(prompt);

            const savedContent = await fs.readFile(promptFile, 'utf8');
            assert(savedContent.includes('# Simple Prompt'));
            assert(savedContent.includes('Just content.'));
        });

        it('should create directory structure when saving', async () => {
            const nestedDir = path.join(tempDir, 'new', 'category');
            const promptFile = path.join(nestedDir, 'nested-prompt.md');
            const prompt: Prompt = {
                id: 'nested-test',
                filePath: promptFile,
                fileName: 'nested-prompt.md',
                metadata: {
                    title: 'Nested Prompt'
                },
                content: 'Nested content',
                lastModified: new Date(),
                isValid: true
            };

            await promptManager.savePrompt(prompt);

            // Verify file and directories were created
            const exists = await fs.access(promptFile).then(() => true).catch(() => false);
            assert(exists);
        });
    });

    describe('Prompt Creation', () => {
        it('should create new prompt in root directory', async () => {
            const prompt = await promptManager.createPrompt('My New Prompt');

            assert.strictEqual(prompt.metadata.title, 'My New Prompt');
            assert.strictEqual(prompt.metadata.category, 'General');
            assert(prompt.filePath.endsWith('my-new-prompt.md'));

            // Verify file was created
            const exists = await fs.access(prompt.filePath).then(() => true).catch(() => false);
            assert(exists);
        });

        it('should create new prompt in category directory', async () => {
            const prompt = await promptManager.createPrompt('Categorized Prompt', 'Development');

            assert.strictEqual(prompt.metadata.title, 'Categorized Prompt');
            assert.strictEqual(prompt.metadata.category, 'Development');
            assert(prompt.filePath.includes('Development'));
            assert(prompt.filePath.endsWith('categorized-prompt.md'));
        });

        it('should handle special characters in prompt names', async () => {
            const prompt = await promptManager.createPrompt('Prompt with: Special/Characters?');

            assert.strictEqual(prompt.metadata.title, 'Prompt with: Special/Characters?');
            // File name should be sanitized
            assert(prompt.fileName.match(/^[a-z0-9\-_.]+\.md$/));
        });

        it('should reject creating prompt with existing name', async () => {
            await promptManager.createPrompt('Duplicate Name');

            await assert.rejects(
                () => promptManager.createPrompt('Duplicate Name'),
                /already exists/
            );
        });
    });

    describe('Prompt Deletion', () => {
        it('should delete existing prompt file', async () => {
            const promptFile = path.join(tempDir, 'to-delete.md');
            await fs.writeFile(promptFile, '# To Delete\nThis will be deleted');

            await promptManager.deletePrompt(promptFile);

            // Verify file was deleted
            const exists = await fs.access(promptFile).then(() => true).catch(() => false);
            assert(!exists);
        });

        it('should handle deleting non-existent file gracefully', async () => {
            const nonExistentFile = path.join(tempDir, 'does-not-exist.md');

            // Should not throw
            await promptManager.deletePrompt(nonExistentFile);
        });
    });

    describe('Error Handling', () => {
        it('should handle permission errors gracefully', async () => {
            // This test is platform-dependent and might be skipped on some systems
            if (process.platform === 'win32') {
                return; // Skip on Windows due to different permission model
            }

            const restrictedDir = path.join(tempDir, 'restricted');
            await fs.mkdir(restrictedDir);
            await fs.chmod(restrictedDir, 0o000); // No permissions

            try {
                const files = await promptManager.scanDirectory(restrictedDir);
                // Should return empty array instead of throwing
                assert(Array.isArray(files));
            } finally {
                // Restore permissions for cleanup
                await fs.chmod(restrictedDir, 0o755);
            }
        });

        it('should handle concurrent file operations', async () => {
            const promptFile1 = path.join(tempDir, 'concurrent1.md');
            const promptFile2 = path.join(tempDir, 'concurrent2.md');
            const prompt1: Prompt = {
                id: 'concurrent-1',
                filePath: promptFile1,
                fileName: 'concurrent1.md',
                metadata: { title: 'Concurrent 1' },
                content: 'Content 1',
                lastModified: new Date(),
                isValid: true
            };
            const prompt2: Prompt = {
                id: 'concurrent-2',
                filePath: promptFile2,
                fileName: 'concurrent2.md',
                metadata: { title: 'Concurrent 2' },
                content: 'Content 2',
                lastModified: new Date(),
                isValid: true
            };

            // Try to save both prompts concurrently to different files
            const promises = [
                promptManager.savePrompt(prompt1),
                promptManager.savePrompt(prompt2)
            ];

            // Both should complete without error
            await Promise.all(promises);

            // Files should exist and be readable
            const content1 = await fs.readFile(promptFile1, 'utf8');
            const content2 = await fs.readFile(promptFile2, 'utf8');
            assert(content1.length > 0);
            assert(content2.length > 0);
        });
    });
});
