/**
 * Integration tests for file operations
 * Testing end-to-end file operations with VS Code integration
 */

import assert from 'assert';
import * as vscode from 'vscode';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';
import { FileOperationManager } from '../../../promptStore/FileOperationManager';
import { FileOperationCommands } from '../../../promptStore/commands';
import { PromptManager } from '../../../promptStore/PromptManager';
import { ConfigurationManager } from '../../../promptStore/ConfigurationManager';
import { TemplateManager } from '../../../promptStore/TemplateManager';

suite('File Operations Integration Tests', () => {
    let fileOperationManager: FileOperationManager;
    let fileOperationCommands: FileOperationCommands;
    let promptManager: PromptManager;
    let configManager: ConfigurationManager;
    let templateManager: TemplateManager;
    let testDir: string;
    let context: vscode.ExtensionContext;
    let originalGetConfiguration: typeof vscode.workspace.getConfiguration;

    suiteSetup(async () => {
        // Create temporary test directory
        testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'wu-wei-integration-test-'));

        // Mock the extension context
        context = {
            subscriptions: [],
            workspaceState: {
                get: () => undefined,
                update: () => Promise.resolve()
            },
            globalState: {
                get: () => undefined,
                update: () => Promise.resolve()
            },
            extensionPath: testDir,
            storagePath: testDir,
            globalStoragePath: testDir
        } as any;

        // Initialize managers
        configManager = new ConfigurationManager(context);
        templateManager = new TemplateManager();
        promptManager = new PromptManager();
        fileOperationManager = new FileOperationManager(promptManager, configManager);
        fileOperationCommands = new FileOperationCommands(fileOperationManager, templateManager);

        // Store original configuration function
        originalGetConfiguration = vscode.workspace.getConfiguration;

        // Mock VS Code configuration to use test directory
        vscode.workspace.getConfiguration = (section?: string) => {
            if (section === 'wu-wei.promptStore') {
                return {
                    get: (key: string, defaultValue?: any) => {
                        if (key === 'rootDirectory') return testDir;
                        if (key === 'autoRefresh') return true;
                        if (key === 'showMetadataTooltips') return true;
                        if (key === 'enableTemplates') return true;
                        if (key.startsWith('fileWatcher.')) {
                            const watcherKey = key.replace('fileWatcher.', '');
                            const defaults: any = {
                                enabled: true,
                                debounceMs: 500,
                                maxDepth: 10,
                                ignorePatterns: [],
                                usePolling: false,
                                pollingInterval: 1000
                            };
                            return defaults[watcherKey] ?? defaultValue;
                        }
                        return defaultValue;
                    },
                    update: async () => Promise.resolve(),
                    has: () => true,
                    inspect: () => ({ key: '', defaultValue: undefined })
                } as any;
            }
            return originalGetConfiguration(section);
        };

        // Mock configuration manager to use test directory
        const originalGetConfig = configManager.getConfig.bind(configManager);
        configManager.getConfig = () => ({
            ...originalGetConfig(),
            rootDirectory: testDir
        });

        // Register commands with test instances
        const disposables = fileOperationCommands.registerCommands(context);
        context.subscriptions.push(...disposables);

        // Load custom templates
        await templateManager.loadCustomTemplates();

        // Wait for commands to be registered
        await new Promise(resolve => setTimeout(resolve, 100));

        // Verify commands are registered
        const commands = await vscode.commands.getCommands(true);
        const promptStoreCommands = commands.filter(cmd => cmd.startsWith('wu-wei.promptStore'));
        console.log('Registered prompt store commands:', promptStoreCommands);
    });

    suiteTeardown(async () => {
        // Restore original configuration function
        vscode.workspace.getConfiguration = originalGetConfiguration;

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

    test('Command registration works correctly', async () => {
        const disposables = fileOperationCommands.registerCommands(context);

        assert.ok(disposables.length > 0);
        assert.ok(disposables.every(d => typeof d.dispose === 'function'));

        // Clean up
        disposables.forEach(d => d.dispose());
    });

    test('End-to-end prompt creation workflow', async () => {
        // Mock user input for new prompt
        const originalShowInputBox = vscode.window.showInputBox;
        let inputCallCount = 0;
        vscode.window.showInputBox = async (options: any) => {
            inputCallCount++;
            if (inputCallCount === 1) {
                return 'integration-test-prompt'; // name
            } else if (inputCallCount === 2) {
                return 'testing'; // category
            }
            return undefined;
        };

        // Mock document opening
        const mockDocument = {
            uri: vscode.Uri.file(path.join(testDir, 'testing', 'integration-test-prompt.md')),
            lineCount: 10,
            save: async () => true
        } as any;

        const originalOpenTextDocument = vscode.workspace.openTextDocument;
        vscode.workspace.openTextDocument = async () => mockDocument;

        const originalShowTextDocument = vscode.window.showTextDocument;
        vscode.window.showTextDocument = async () => ({} as any);

        const originalShowInformationMessage = vscode.window.showInformationMessage;
        vscode.window.showInformationMessage = async () => undefined;

        try {
            // Execute the command
            await vscode.commands.executeCommand('wu-wei.promptStore.newPrompt');

            // Verify file was created
            const expectedPath = path.join(testDir, 'testing', 'integration-test-prompt.md');
            const fileExists = await fs.access(expectedPath).then(() => true, () => false);
            assert.strictEqual(fileExists, true);

            // Verify content
            const content = await fs.readFile(expectedPath, 'utf8');
            assert.ok(content.includes('integration-test-prompt'));
            assert.ok(content.includes('category: testing'));

        } finally {
            vscode.window.showInputBox = originalShowInputBox;
            vscode.workspace.openTextDocument = originalOpenTextDocument;
            vscode.window.showTextDocument = originalShowTextDocument;
            vscode.window.showInformationMessage = originalShowInformationMessage;
        }
    });

    test('Template-based prompt creation workflow', async () => {
        // Mock user selections
        const originalShowQuickPick = vscode.window.showQuickPick;
        (vscode.window.showQuickPick as any) = async (items: any) => {
            // Return the first template (basic-prompt)
            return Array.isArray(items) ? items[0] : undefined;
        };

        let inputCallCount = 0;
        const originalShowInputBox = vscode.window.showInputBox;
        vscode.window.showInputBox = async (options: any) => {
            inputCallCount++;
            switch (inputCallCount) {
                case 1: return 'template-test-prompt'; // name
                case 2: return 'development'; // category
                case 3: return 'Template Test'; // title parameter
                case 4: return 'A test prompt from template'; // description
                case 5: return 'Do something amazing'; // instructions
                case 6: return 'Amazing results'; // expected output
                default: return undefined;
            }
        };

        // Mock file operations
        const mockDocument = {
            uri: vscode.Uri.file(path.join(testDir, 'development', 'template-test-prompt.md')),
            lineCount: 20,
            save: async () => true
        } as any;

        const originalOpenTextDocument = vscode.workspace.openTextDocument;
        vscode.workspace.openTextDocument = async () => mockDocument;

        const originalShowTextDocument = vscode.window.showTextDocument;
        vscode.window.showTextDocument = async () => ({} as any);

        const originalApplyEdit = vscode.workspace.applyEdit;
        vscode.workspace.applyEdit = async () => true;

        const originalShowInformationMessage = vscode.window.showInformationMessage;
        vscode.window.showInformationMessage = async () => undefined;

        try {
            // Execute the command
            await vscode.commands.executeCommand('wu-wei.promptStore.newPromptFromTemplate');

            // Verify file was created
            const expectedPath = path.join(testDir, 'development', 'template-test-prompt.md');
            const fileExists = await fs.access(expectedPath).then(() => true, () => false);
            assert.strictEqual(fileExists, true);

        } finally {
            vscode.window.showQuickPick = originalShowQuickPick;
            vscode.window.showInputBox = originalShowInputBox;
            vscode.workspace.openTextDocument = originalOpenTextDocument;
            vscode.window.showTextDocument = originalShowTextDocument;
            vscode.workspace.applyEdit = originalApplyEdit;
            vscode.window.showInformationMessage = originalShowInformationMessage;
        }
    });

    // Note: Duplicate prompt functionality is currently commented out in commands
    // test('Prompt duplication workflow', async () => {
    //     // Create original prompt
    //     const original = await fileOperationManager.createNewPrompt({
    //         name: 'original-for-duplication',
    //         category: 'test'
    //     });
    //     assert.strictEqual(original.success, true);

    //     // Mock user input for new name
    //     const originalShowInputBox = vscode.window.showInputBox;
    //     vscode.window.showInputBox = async () => 'duplicated-prompt';

    //     // Mock file operations
    //     const mockDocument = {
    //         uri: vscode.Uri.file(path.join(testDir, 'test', 'duplicated-prompt.md')),
    //         save: async () => true
    //     } as any;

    //     const originalOpenTextDocument = vscode.workspace.openTextDocument;
    //     vscode.workspace.openTextDocument = async () => mockDocument;

    //     const originalShowTextDocument = vscode.window.showTextDocument;
    //     vscode.window.showTextDocument = async () => ({} as any);

    //     const originalShowInformationMessage = vscode.window.showInformationMessage;
    //     vscode.window.showInformationMessage = async () => undefined;

    //     try {
    //         // Execute duplicate command
    //         await vscode.commands.executeCommand('wu-wei.promptStore.duplicatePrompt', original.filePath);

    //         // Verify both files exist
    //         const originalExists = await fs.access(original.filePath!).then(() => true, () => false);
    //         const duplicateExists = await fs.access(
    //             path.join(testDir, 'test', 'duplicated-prompt.md')
    //         ).then(() => true, () => false);

    //         assert.strictEqual(originalExists, true);
    //         assert.strictEqual(duplicateExists, true);

    //     } finally {
    //         vscode.window.showInputBox = originalShowInputBox;
    //         vscode.workspace.openTextDocument = originalOpenTextDocument;
    //         vscode.window.showTextDocument = originalShowTextDocument;
    //         vscode.window.showInformationMessage = originalShowInformationMessage;
    //     }
    // });

    test('Prompt deletion workflow', async () => {
        // Create prompt to delete
        const prompt = await fileOperationManager.createNewPrompt({
            name: 'to-be-deleted'
        });
        assert.strictEqual(prompt.success, true);

        // Mock confirmation dialog
        const originalShowWarningMessage = vscode.window.showWarningMessage;
        vscode.window.showWarningMessage = async () => 'Delete' as any;

        const originalShowInformationMessage = vscode.window.showInformationMessage;
        vscode.window.showInformationMessage = async () => undefined;

        try {
            // Execute delete command
            await vscode.commands.executeCommand('wu-wei.promptStore.deletePrompt', prompt.filePath);

            // Verify file is deleted
            const fileExists = await fs.access(prompt.filePath!).then(() => true, () => false);
            assert.strictEqual(fileExists, false);

        } finally {
            vscode.window.showWarningMessage = originalShowWarningMessage;
            vscode.window.showInformationMessage = originalShowInformationMessage;
        }
    });

    test('Error handling for invalid operations', async () => {
        // Test deleting non-existent file
        const originalShowErrorMessage = vscode.window.showErrorMessage;
        let errorMessage = '';
        vscode.window.showErrorMessage = async (message: string) => {
            errorMessage = message;
            return undefined;
        };

        const originalShowWarningMessage = vscode.window.showWarningMessage;
        vscode.window.showWarningMessage = async () => 'Delete' as any;

        try {
            await vscode.commands.executeCommand(
                'wu-wei.promptStore.deletePrompt',
                path.join(testDir, 'non-existent.md')
            );

            // Should have shown an error message
            assert.ok(errorMessage.length > 0);

        } finally {
            vscode.window.showErrorMessage = originalShowErrorMessage;
            vscode.window.showWarningMessage = originalShowWarningMessage;
        }
    });

    test('Batch operations integration', async () => {
        // Create multiple prompts
        const prompts = [];
        for (let i = 0; i < 3; i++) {
            const result = await fileOperationManager.createNewPrompt({
                name: `batch-integration-${i}`
            });
            assert.strictEqual(result.success, true);
            prompts.push(result.filePath!);
        }

        // Mock batch delete confirmation
        const originalShowWarningMessage = vscode.window.showWarningMessage;
        vscode.window.showWarningMessage = async () => 'Delete All' as any;

        const originalShowInformationMessage = vscode.window.showInformationMessage;
        vscode.window.showInformationMessage = async () => undefined;

        try {
            // Execute batch delete command
            await vscode.commands.executeCommand('wu-wei.promptStore.batchDelete', prompts);

            // Verify all files are deleted
            for (const filePath of prompts) {
                const exists = await fs.access(filePath).then(() => true, () => false);
                assert.strictEqual(exists, false);
            }

        } finally {
            vscode.window.showWarningMessage = originalShowWarningMessage;
            vscode.window.showInformationMessage = originalShowInformationMessage;
        }
    });

    test('Export functionality integration', async () => {
        // Create test prompts
        const prompts = [];
        for (let i = 0; i < 2; i++) {
            const result = await fileOperationManager.createNewPrompt({
                name: `export-integration-${i}`,
                category: 'test-export'
            });
            assert.strictEqual(result.success, true);
            prompts.push(result.filePath!);
        }

        // Mock export dialog
        const exportPath = path.join(testDir, 'integration-export.json');
        const originalShowQuickPick = vscode.window.showQuickPick;
        (vscode.window.showQuickPick as any) = async () => ({ label: 'JSON', value: 'json' });

        const originalShowSaveDialog = vscode.window.showSaveDialog;
        vscode.window.showSaveDialog = async () => vscode.Uri.file(exportPath);

        const originalShowInformationMessage = vscode.window.showInformationMessage;
        vscode.window.showInformationMessage = async () => undefined;

        try {
            // Execute export command
            await vscode.commands.executeCommand('wu-wei.promptStore.exportPrompts', prompts);

            // Verify export file exists and contains correct data
            const exportExists = await fs.access(exportPath).then(() => true, () => false);
            assert.strictEqual(exportExists, true);

            const exportContent = await fs.readFile(exportPath, 'utf8');
            const exportData = JSON.parse(exportContent);
            assert.strictEqual(Array.isArray(exportData), true);
            assert.strictEqual(exportData.length, 2);

        } finally {
            vscode.window.showQuickPick = originalShowQuickPick;
            vscode.window.showSaveDialog = originalShowSaveDialog;
            vscode.window.showInformationMessage = originalShowInformationMessage;
        }
    });

    test('File watching integration', async () => {
        // Initialize prompt manager with file watching
        await promptManager.initialize();

        // Create a prompt file directly (simulating external file creation)
        const testFilePath = path.join(testDir, 'externally-created.md');
        const content = `---
title: Externally Created
description: Created outside the extension
---

# Externally Created Prompt

This prompt was created externally.
`;
        await fs.writeFile(testFilePath, content, 'utf8');

        // Wait for file watcher to detect the change
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Verify the prompt manager detected the new file
        const prompts = promptManager.getAllPrompts();
        const foundPrompt = prompts.find(p => p.fileName === 'externally-created.md');
        assert.ok(foundPrompt, 'File watcher should detect externally created files');
        assert.strictEqual(foundPrompt.metadata.title, 'Externally Created');
    });
}); 