/**
 * Unit tests for FileOperationManager
 * Testing file operations with wu wei principles: simple, reliable, comprehensive
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';
import { FileOperationManager } from '../../promptStore/FileOperationManager';
import { PromptManager } from '../../promptStore/PromptManager';
import { ConfigurationManager } from '../../promptStore/ConfigurationManager';
import { TemplateManager } from '../../promptStore/TemplateManager';

suite('FileOperationManager Tests', () => {
    let fileOperationManager: FileOperationManager;
    let promptManager: PromptManager;
    let configManager: ConfigurationManager;
    let templateManager: TemplateManager;
    let testDir: string;

    suiteSetup(async () => {
        // Create temporary test directory
        testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'wu-wei-test-'));

        // Mock the extension context
        const context = {
            subscriptions: [],
            workspaceState: {
                get: () => undefined,
                update: () => Promise.resolve()
            },
            globalState: {
                get: () => undefined,
                update: () => Promise.resolve()
            }
        } as any;

        // Initialize managers
        configManager = new ConfigurationManager(context);
        templateManager = new TemplateManager();
        promptManager = new PromptManager();
        fileOperationManager = new FileOperationManager(promptManager, configManager);

        // Mock configuration to use test directory
        const originalGetConfig = configManager.getConfig.bind(configManager);
        configManager.getConfig = () => ({
            ...originalGetConfig(),
            rootDirectory: testDir
        });
    });

    suiteTeardown(async () => {
        // Clean up test directory
        try {
            await fs.rm(testDir, { recursive: true, force: true });
        } catch (error) {
            console.warn('Failed to cleanup test directory:', error);
        }
    });

    setup(async () => {
        // Clean test directory before each test
        try {
            const entries = await fs.readdir(testDir);
            for (const entry of entries) {
                await fs.rm(path.join(testDir, entry), { recursive: true, force: true });
            }
        } catch (error) {
            // Directory might be empty
        }
    });

    test('createNewPrompt - creates basic prompt successfully', async () => {
        const result = await fileOperationManager.createNewPrompt({
            name: 'test-prompt'
        });

        assert.strictEqual(result.success, true);
        assert.strictEqual(typeof result.filePath, 'string');

        // Verify file exists
        const fileExists = await fs.access(result.filePath!).then(() => true, () => false);
        assert.strictEqual(fileExists, true);

        // Verify content
        const content = await fs.readFile(result.filePath!, 'utf8');
        assert.ok(content.includes('test-prompt'));
        assert.ok(content.includes('---')); // Frontmatter
    });

    test('createNewPrompt - creates prompt with category', async () => {
        const result = await fileOperationManager.createNewPrompt({
            name: 'categorized-prompt',
            category: 'development'
        });

        assert.strictEqual(result.success, true);
        assert.ok(result.filePath!.includes('development'));

        // Verify directory structure
        const expectedDir = path.join(testDir, 'development');
        const dirExists = await fs.access(expectedDir).then(() => true, () => false);
        assert.strictEqual(dirExists, true);
    });

    test('createNewPrompt - fails when file already exists', async () => {
        // Create first prompt
        const result1 = await fileOperationManager.createNewPrompt({
            name: 'duplicate-test'
        });
        assert.strictEqual(result1.success, true);

        // Try to create duplicate
        const result2 = await fileOperationManager.createNewPrompt({
            name: 'duplicate-test'
        });
        assert.strictEqual(result2.success, false);
        assert.ok(result2.error!.includes('already exists'));
    });

    test('createNewPrompt - handles invalid names gracefully', async () => {
        const result = await fileOperationManager.createNewPrompt({
            name: 'invalid/\\:*?"<>|name'
        });

        assert.strictEqual(result.success, true);
        // Should sanitize the filename
        assert.ok(result.filePath!.includes('invalidname'));
    });

    test('createNewPrompt - uses template when specified', async () => {
        const result = await fileOperationManager.createNewPrompt({
            name: 'template-test',
            template: 'basic-prompt'
        });

        assert.strictEqual(result.success, true);

        const content = await fs.readFile(result.filePath!, 'utf8');
        // Should contain template placeholders
        assert.ok(content.includes('{{'));
    });

    // Note: duplicatePrompt method is not currently implemented in FileOperationManager
    // test('duplicatePrompt - creates copy with new name', async () => {
    //     // Create original prompt
    //     const original = await fileOperationManager.createNewPrompt({
    //         name: 'original-prompt'
    //     });
    //     assert.strictEqual(original.success, true);

    //     // Duplicate it
    //     const duplicate = await fileOperationManager.duplicatePrompt(
    //         original.filePath!,
    //         'duplicated-prompt'
    //     );

    //     assert.strictEqual(duplicate.success, true);
    //     assert.notStrictEqual(duplicate.filePath, original.filePath);

    //     // Both files should exist
    //     const originalExists = await fs.access(original.filePath!).then(() => true, () => false);
    //     const duplicateExists = await fs.access(duplicate.filePath!).then(() => true, () => false);
    //     assert.strictEqual(originalExists, true);
    //     assert.strictEqual(duplicateExists, true);
    // });

    test('renamePrompt - renames file and updates metadata', async () => {
        // Create original prompt
        const original = await fileOperationManager.createNewPrompt({
            name: 'old-name'
        });
        assert.strictEqual(original.success, true);

        // Rename it
        const renamed = await fileOperationManager.renamePrompt(
            original.filePath!,
            'new-name'
        );

        assert.strictEqual(renamed.success, true);
        assert.ok(renamed.filePath!.includes('new-name'));

        // Original file should not exist
        const originalExists = await fs.access(original.filePath!).then(() => true, () => false);
        assert.strictEqual(originalExists, false);

        // New file should exist
        const newExists = await fs.access(renamed.filePath!).then(() => true, () => false);
        assert.strictEqual(newExists, true);
    });

    test('movePrompt - moves prompt to new category', async () => {
        // Create prompt in default location
        const original = await fileOperationManager.createNewPrompt({
            name: 'moveable-prompt'
        });
        assert.strictEqual(original.success, true);

        // Move to new category
        const moved = await fileOperationManager.movePrompt(
            original.filePath!,
            'new-category'
        );

        assert.strictEqual(moved.success, true);
        assert.ok(moved.filePath!.includes('new-category'));

        // Original file should not exist
        const originalExists = await fs.access(original.filePath!).then(() => true, () => false);
        assert.strictEqual(originalExists, false);

        // New file should exist in new category
        const newExists = await fs.access(moved.filePath!).then(() => true, () => false);
        assert.strictEqual(newExists, true);
    });

    test('batchDeletePrompts - deletes multiple files', async () => {
        // Create multiple prompts
        const prompts = [];
        for (let i = 0; i < 3; i++) {
            const result = await fileOperationManager.createNewPrompt({
                name: `batch-test-${i}`
            });
            assert.strictEqual(result.success, true);
            prompts.push(result.filePath!);
        }

        // Mock user confirmation
        const originalShowWarningMessage = vscode.window.showWarningMessage;
        vscode.window.showWarningMessage = async () => 'Delete All' as any;

        try {
            // Batch delete
            const result = await fileOperationManager.batchDeletePrompts(prompts);

            assert.strictEqual(result.successful.length, 3);
            assert.strictEqual(result.failed.length, 0);

            // Verify files are deleted
            for (const filePath of prompts) {
                const exists = await fs.access(filePath).then(() => true, () => false);
                assert.strictEqual(exists, false);
            }
        } finally {
            vscode.window.showWarningMessage = originalShowWarningMessage;
        }
    });

    test('batchMovePrompts - moves multiple files to new category', async () => {
        // Create multiple prompts
        const prompts = [];
        for (let i = 0; i < 3; i++) {
            const result = await fileOperationManager.createNewPrompt({
                name: `move-test-${i}`
            });
            assert.strictEqual(result.success, true);
            prompts.push(result.filePath!);
        }

        // Batch move
        const result = await fileOperationManager.batchMovePrompts(prompts, 'batch-category');

        assert.strictEqual(result.successful.length, 3);
        assert.strictEqual(result.failed.length, 0);

        // Verify files are moved
        for (const newPath of result.successful) {
            assert.ok(newPath.includes('batch-category'));
            const exists = await fs.access(newPath).then(() => true, () => false);
            assert.strictEqual(exists, true);
        }
    });

    test('exportPrompts - exports to JSON format', async () => {
        // Create test prompts
        const prompts = [];
        for (let i = 0; i < 2; i++) {
            const result = await fileOperationManager.createNewPrompt({
                name: `export-test-${i}`
            });
            assert.strictEqual(result.success, true);
            prompts.push(result.filePath!);
        }

        // Mock file dialog
        const exportPath = path.join(testDir, 'export.json');
        const originalShowSaveDialog = vscode.window.showSaveDialog;
        vscode.window.showSaveDialog = async () => vscode.Uri.file(exportPath);

        try {
            const result = await fileOperationManager.exportPrompts(prompts, 'json');

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.filePath, exportPath);

            // Verify export file exists and contains data
            const exportExists = await fs.access(exportPath).then(() => true, () => false);
            assert.strictEqual(exportExists, true);

            const exportContent = await fs.readFile(exportPath, 'utf8');
            const exportData = JSON.parse(exportContent);
            assert.strictEqual(Array.isArray(exportData), true);
            assert.strictEqual(exportData.length, 2);
        } finally {
            vscode.window.showSaveDialog = originalShowSaveDialog;
        }
    });

    test('sanitizeFileName - handles special characters', async () => {
        const result = await fileOperationManager.createNewPrompt({
            name: 'Test! @#$% File^&*() Name'
        });

        assert.strictEqual(result.success, true);
        assert.ok(result.filePath!.includes('test-file-name'));
    });

    test('generatePromptContent - includes metadata and default content', async () => {
        const result = await fileOperationManager.createNewPrompt({
            name: 'metadata-test',
            metadata: {
                description: 'Test description',
                tags: ['test', 'example']
            }
        });

        assert.strictEqual(result.success, true);

        const content = await fs.readFile(result.filePath!, 'utf8');
        assert.ok(content.includes('description: Test description'));
        assert.ok(content.includes('- test'));
        assert.ok(content.includes('- example'));
        assert.ok(content.includes('# metadata-test'));
    });

    test('error handling - no root directory configured', async () => {
        // Temporarily remove root directory
        const originalGetConfig = configManager.getConfig.bind(configManager);
        configManager.getConfig = () => ({
            ...originalGetConfig(),
            rootDirectory: ''
        });

        try {
            const result = await fileOperationManager.createNewPrompt({
                name: 'test-no-dir'
            });

            assert.strictEqual(result.success, false);
            assert.ok(result.error!.includes('No prompt directory configured'));
        } finally {
            configManager.getConfig = originalGetConfig;
        }
    });
}); 