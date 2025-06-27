/**
 * Unit tests for File Operation Commands
 * Testing wu wei principle: simple, intuitive commands that flow naturally
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import { FileOperationCommands } from '../../promptStore/commands';
import { FileOperationManager } from '../../promptStore/FileOperationManager';
import { TemplateManager } from '../../promptStore/TemplateManager';
import { PromptManager } from '../../promptStore/PromptManager';
import { ConfigurationManager } from '../../promptStore/ConfigurationManager';

suite('FileOperationCommands Tests', () => {
    let commands: FileOperationCommands;
    let mockFileOperationManager: FileOperationManager;
    let mockTemplateManager: TemplateManager;
    let mockContext: vscode.ExtensionContext;
    let registeredCommands: Map<string, any>;

    setup(() => {
        // Create mock context
        mockContext = {
            subscriptions: [],
            workspaceState: { get: () => undefined, update: () => Promise.resolve() },
            globalState: { get: () => undefined, update: () => Promise.resolve() },
            extensionPath: '/mock/path'
        } as any;

        // Track registered commands
        registeredCommands = new Map();

        // Mock vscode.commands.registerCommand
        const originalRegisterCommand = vscode.commands.registerCommand;
        vscode.commands.registerCommand = (command: string, handler: any) => {
            registeredCommands.set(command, handler);
            return { dispose: () => { } } as vscode.Disposable;
        };

        // Create mock dependencies
        const mockPromptManager = new PromptManager();
        const mockConfigManager = new ConfigurationManager(mockContext);
        mockFileOperationManager = new FileOperationManager(mockPromptManager, mockConfigManager);
        mockTemplateManager = new TemplateManager();

        commands = new FileOperationCommands(mockFileOperationManager, mockTemplateManager);
    });

    teardown(() => {
        // Restore original functions if needed
    });

    suite('Command Registration', () => {
        test('Should register all expected commands', () => {
            const disposables = commands.registerCommands(mockContext);

            assert(Array.isArray(disposables));
            assert(disposables.length > 0);

            // Check that expected commands are registered
            const expectedCommands = [
                'wu-wei.promptStore.newPrompt',
                'wu-wei.promptStore.newPromptFromTemplate',
                'wu-wei.promptStore.deletePrompt',
                'wu-wei.promptStore.renamePrompt',
                'wu-wei.promptStore.movePrompt',
                'wu-wei.promptStore.exportPrompts',
                'wu-wei.promptStore.batchDelete',
                'wu-wei.promptStore.openPrompt',
                'wu-wei.promptStore.openPromptPreview'
            ];

            expectedCommands.forEach(command => {
                assert(registeredCommands.has(command), `Command ${command} should be registered`);
            });
        });

        test('Should return disposable objects', () => {
            const disposables = commands.registerCommands(mockContext);

            disposables.forEach(disposable => {
                assert(typeof disposable.dispose === 'function');
            });
        });
    });

    suite('New Prompt Command', () => {
        test('Should handle new prompt creation', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.newPrompt');

            // Mock user input
            let inputCallCount = 0;
            const originalShowInputBox = vscode.window.showInputBox;
            vscode.window.showInputBox = async (options: any) => {
                inputCallCount++;
                if (inputCallCount === 1) {
                    return 'Test Prompt'; // name
                } else if (inputCallCount === 2) {
                    return 'test-category'; // category
                }
                return undefined;
            };

            // Mock file operation
            mockFileOperationManager.createNewPrompt = async (options: any) => ({
                success: true,
                filePath: '/test/path/test-prompt.md'
            });

            mockFileOperationManager.openPrompt = async (filePath: string) => {
                // Mock opening prompt
            };

            try {
                await handler();
                assert.strictEqual(inputCallCount, 2);
            } finally {
                vscode.window.showInputBox = originalShowInputBox;
            }
        });

        test('Should handle cancellation', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.newPrompt');

            // Mock user cancelling input
            vscode.window.showInputBox = async () => undefined;

            // Should not throw error when user cancels
            await handler();
        });

        test('Should validate prompt name', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.newPrompt');

            let validationCalled = false;
            vscode.window.showInputBox = async (options: any) => {
                if (options.validateInput) {
                    // Test validation function
                    const emptyResult = options.validateInput('');
                    assert(emptyResult); // Should return error message

                    const invalidResult = options.validateInput('invalid@name!');
                    assert(invalidResult); // Should return error message

                    const validResult = options.validateInput('valid-name');
                    assert(!validResult); // Should return undefined for valid name

                    validationCalled = true;
                }
                return undefined; // Cancel to end test
            };

            await handler();
            assert(validationCalled);
        });
    });

    suite('New Prompt From Template Command', () => {
        test('Should show template selection', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.newPromptFromTemplate');

            let quickPickCalled = false;
            (vscode.window.showQuickPick as any) = async (items: any[], options?: any) => {
                quickPickCalled = true;
                assert(Array.isArray(items));
                assert(items.length > 0);
                return undefined; // Cancel selection
            };

            await handler();
            assert(quickPickCalled);
        });

        test('Should handle template selection and creation', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.newPromptFromTemplate');

            const mockTemplate = {
                label: 'Basic Prompt',
                description: 'A basic prompt template',
                template: {
                    id: 'basic-prompt',
                    name: 'Basic Prompt',
                    description: 'Basic template',
                    content: '# {{title}}',
                    metadata: { category: 'general' }
                }
            };

            let inputCallCount = 0;
            (vscode.window.showQuickPick as any) = async () => mockTemplate;
            vscode.window.showInputBox = async (options: any) => {
                inputCallCount++;
                if (inputCallCount === 1) {
                    return 'Template Test';
                }
                if (inputCallCount === 2) {
                    return 'template-category';
                }
                return undefined;
            };

            mockTemplateManager.renderTemplate = async () => '# Template Test\n\nRendered content';
            mockFileOperationManager.createNewPrompt = async () => ({
                success: true,
                filePath: '/test/template-test.md'
            });

            // Mock workspace edit
            const originalApplyEdit = vscode.workspace.applyEdit;
            vscode.workspace.applyEdit = async () => true;

            try {
                await handler();
                assert.strictEqual(inputCallCount, 2);
            } finally {
                vscode.workspace.applyEdit = originalApplyEdit;
            }
        });
    });

    suite('Delete Prompt Command', () => {
        test('Should handle prompt deletion', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.deletePrompt');

            mockFileOperationManager.deletePrompt = async (filePath: string) => ({
                success: true
            });

            let messageShown = false;
            const originalShowInformationMessage = vscode.window.showInformationMessage;
            vscode.window.showInformationMessage = async (message: string) => {
                messageShown = true;
                assert(message.includes('deleted successfully'));
                return undefined;
            };

            try {
                await handler('/test/prompt.md');
                assert(messageShown);
            } finally {
                vscode.window.showInformationMessage = originalShowInformationMessage;
            }
        });

        test('Should handle deletion failure', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.deletePrompt');

            mockFileOperationManager.deletePrompt = async () => ({
                success: false,
                error: 'Delete failed'
            });

            let errorShown = false;
            const originalShowErrorMessage = vscode.window.showErrorMessage;
            vscode.window.showErrorMessage = async (message: string) => {
                errorShown = true;
                assert(message.includes('Delete failed'));
                return undefined;
            };

            try {
                await handler('/test/prompt.md');
                assert(errorShown);
            } finally {
                vscode.window.showErrorMessage = originalShowErrorMessage;
            }
        });
    });

    suite('Rename Prompt Command', () => {
        test('Should handle prompt renaming', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.renamePrompt');

            vscode.window.showInputBox = async (options: any) => {
                assert.strictEqual(options.value, 'current-name'); // Should prefill current name
                return 'new-name';
            };

            mockFileOperationManager.renamePrompt = async (filePath: string, newName: string) => {
                assert.strictEqual(newName, 'new-name');
                return {
                    success: true,
                    filePath: '/test/new-name.md'
                };
            };

            mockFileOperationManager.openPrompt = async (filePath: string) => {
                assert.strictEqual(filePath, '/test/new-name.md');
            };

            await handler('/test/current-name.md');
        });

        test('Should validate new name', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.renamePrompt');

            let validationTested = false;
            vscode.window.showInputBox = async (options: any) => {
                if (options.validateInput) {
                    const emptyResult = options.validateInput('');
                    assert(emptyResult);

                    const invalidResult = options.validateInput('invalid@name!');
                    assert(invalidResult);

                    validationTested = true;
                }
                return undefined;
            };

            await handler('/test/prompt.md');
            assert(validationTested);
        });

        test('Should handle same name (no change)', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.renamePrompt');

            vscode.window.showInputBox = async (options: any) => {
                return options.value; // Return same name
            };

            // Should not call rename operation
            let renameCalled = false;
            mockFileOperationManager.renamePrompt = async () => {
                renameCalled = true;
                return { success: true };
            };

            await handler('/test/current-name.md');
            assert(!renameCalled);
        });
    });

    suite('Move Prompt Command', () => {
        test('Should handle prompt moving', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.movePrompt');

            vscode.window.showInputBox = async (options: any) => {
                return 'new-category';
            };

            mockFileOperationManager.movePrompt = async (filePath: string, category: string) => {
                assert.strictEqual(category, 'new-category');
                return { success: true };
            };

            let successMessageShown = false;
            vscode.window.showInformationMessage = async (message: string) => {
                successMessageShown = true;
                assert(message.includes('new-category'));
                return undefined;
            };

            await handler('/test/prompt.md');
            assert(successMessageShown);
        });
    });

    suite('Export Prompts Command', () => {
        test('Should show format selection', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.exportPrompts');

            let formatOptions: any[] = [];
            (vscode.window.showQuickPick as any) = async (items: any[]) => {
                formatOptions = items;
                return items[0]; // Select first option
            };

            mockFileOperationManager.exportPrompts = async () => ({
                success: true,
                filePath: '/export/prompts.json'
            });

            await handler(['/test/prompt1.md', '/test/prompt2.md']);

            assert(formatOptions.length >= 2);
            assert(formatOptions.some(opt => opt.value === 'json'));
            assert(formatOptions.some(opt => opt.value === 'zip'));
        });

        test('Should handle export success', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.exportPrompts');

            (vscode.window.showQuickPick as any) = async (items: any[]) => items[0];

            mockFileOperationManager.exportPrompts = async (filePaths: string[], format: any) => {
                assert.strictEqual(filePaths.length, 2);
                return {
                    success: true,
                    filePath: '/export/prompts.json'
                };
            };

            let successMessageShown = false;
            vscode.window.showInformationMessage = async (message: string) => {
                successMessageShown = true;
                assert(message.includes('Exported 2 prompts'));
                return undefined;
            };

            await handler(['/test/prompt1.md', '/test/prompt2.md']);
            assert(successMessageShown);
        });
    });

    suite('Batch Delete Command', () => {
        test('Should handle batch deletion', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.batchDelete');

            mockFileOperationManager.batchDeletePrompts = async (filePaths: string[]) => {
                assert.strictEqual(filePaths.length, 3);
                return {
                    successful: ['/test/prompt1.md', '/test/prompt2.md'],
                    failed: [{ filePath: '/test/prompt3.md', error: 'Permission denied' }]
                };
            };

            let infoMessage = '';
            let warningMessage = '';

            vscode.window.showInformationMessage = async (message: string) => {
                infoMessage = message;
                return undefined;
            };

            vscode.window.showWarningMessage = async (message: string) => {
                warningMessage = message;
                return undefined;
            };

            await handler(['/test/prompt1.md', '/test/prompt2.md', '/test/prompt3.md']);

            assert(infoMessage.includes('Deleted 2 prompts'));
            assert(warningMessage.includes('Failed to delete'));
            assert(warningMessage.includes('prompt3.md'));
        });

        test('Should handle all successful deletions', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.batchDelete');

            mockFileOperationManager.batchDeletePrompts = async () => ({
                successful: ['/test/prompt1.md', '/test/prompt2.md'],
                failed: []
            });

            let infoMessageShown = false;
            let warningMessageShown = false;

            vscode.window.showInformationMessage = async () => {
                infoMessageShown = true;
                return undefined;
            };

            vscode.window.showWarningMessage = async () => {
                warningMessageShown = true;
                return undefined;
            };

            await handler(['/test/prompt1.md', '/test/prompt2.md']);

            assert(infoMessageShown);
            assert(!warningMessageShown);
        });
    });

    suite('Open Prompt Commands', () => {
        test('Should handle open prompt', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.openPrompt');

            let openCalled = false;
            mockFileOperationManager.openPrompt = async (filePath: string) => {
                openCalled = true;
                assert.strictEqual(filePath, '/test/prompt.md');
            };

            await handler('/test/prompt.md');
            assert(openCalled);
        });

        test('Should handle open prompt in preview', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.openPromptPreview');

            let previewCalled = false;
            mockFileOperationManager.openPromptInPreview = async (filePath: string) => {
                previewCalled = true;
                assert.strictEqual(filePath, '/test/prompt.md');
            };

            await handler('/test/prompt.md');
            assert(previewCalled);
        });
    });

    suite('Error Handling', () => {
        test('Should handle file operation errors gracefully', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.newPrompt');

            vscode.window.showInputBox = async () => 'Test Prompt';

            mockFileOperationManager.createNewPrompt = async () => {
                throw new Error('File operation failed');
            };

            let errorShown = false;
            vscode.window.showErrorMessage = async (message: string) => {
                errorShown = true;
                assert(message.includes('File operation failed'));
                return undefined;
            };

            await handler();
            assert(errorShown);
        });

        test('Should handle template manager errors', async () => {
            const disposables = commands.registerCommands(mockContext);
            const handler = registeredCommands.get('wu-wei.promptStore.newPromptFromTemplate');

            mockTemplateManager.getTemplates = () => {
                throw new Error('Template loading failed');
            };

            let errorShown = false;
            vscode.window.showErrorMessage = async (message: string) => {
                errorShown = true;
                assert(message.includes('Template loading failed'));
                return undefined;
            };

            await handler();
            assert(errorShown);
        });

        test('Should handle missing file paths', async () => {
            const disposables = commands.registerCommands(mockContext);
            const deleteHandler = registeredCommands.get('wu-wei.promptStore.deletePrompt');
            const renameHandler = registeredCommands.get('wu-wei.promptStore.renamePrompt');

            // Test delete without file path
            let errorShown = false;
            vscode.window.showErrorMessage = async () => {
                errorShown = true;
                return undefined;
            };

            await deleteHandler(); // No file path
            await deleteHandler(null); // Null file path
            await deleteHandler(''); // Empty file path

            await renameHandler(); // No file path

            // Should handle gracefully without throwing
        });
    });
}); 