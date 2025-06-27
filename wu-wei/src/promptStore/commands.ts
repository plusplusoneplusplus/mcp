/**
 * VS Code commands for file operations
 * Following wu wei principles: simple, intuitive commands that flow naturally
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { FileOperationManager } from './FileOperationManager';
import { TemplateManager } from './TemplateManager';
import { WuWeiLogger } from '../logger';

export class FileOperationCommands {
    private logger: WuWeiLogger;

    constructor(
        private fileOperationManager: FileOperationManager,
        private templateManager: TemplateManager
    ) {
        this.logger = WuWeiLogger.getInstance();
    }

    /**
     * Register all file operation commands
     */
    registerCommands(context: vscode.ExtensionContext): vscode.Disposable[] {
        const disposables: vscode.Disposable[] = [];

        // New prompt command
        disposables.push(
            vscode.commands.registerCommand('wu-wei.promptStore.newPrompt', async () => {
                await this.handleNewPrompt();
            })
        );

        // New prompt from template command
        disposables.push(
            vscode.commands.registerCommand('wu-wei.promptStore.newPromptFromTemplate', async () => {
                await this.handleNewPromptFromTemplate();
            })
        );

        // Delete prompt command
        disposables.push(
            vscode.commands.registerCommand('wu-wei.promptStore.deletePrompt', async (filePath: string) => {
                await this.handleDeletePrompt(filePath);
            })
        );

        // Duplicate prompt command (commented out)
        // disposables.push(
        //     vscode.commands.registerCommand('wu-wei.promptStore.duplicatePrompt', async (filePath: string) => {
        //         await this.handleDuplicatePrompt(filePath);
        //     })
        // );

        // Rename prompt command
        disposables.push(
            vscode.commands.registerCommand('wu-wei.promptStore.renamePrompt', async (filePath: string) => {
                await this.handleRenamePrompt(filePath);
            })
        );

        // Move prompt command
        disposables.push(
            vscode.commands.registerCommand('wu-wei.promptStore.movePrompt', async (filePath: string) => {
                await this.handleMovePrompt(filePath);
            })
        );

        // Export prompts command
        disposables.push(
            vscode.commands.registerCommand('wu-wei.promptStore.exportPrompts', async (filePaths: string[]) => {
                await this.handleExportPrompts(filePaths);
            })
        );

        // Batch delete command
        disposables.push(
            vscode.commands.registerCommand('wu-wei.promptStore.batchDelete', async (filePaths: string[]) => {
                await this.handleBatchDelete(filePaths);
            })
        );

        // Open prompt command
        disposables.push(
            vscode.commands.registerCommand('wu-wei.promptStore.openPrompt', async (filePath: string) => {
                await this.fileOperationManager.openPrompt(filePath);
            })
        );

        // Open prompt in preview command
        disposables.push(
            vscode.commands.registerCommand('wu-wei.promptStore.openPromptPreview', async (filePath: string) => {
                await this.fileOperationManager.openPromptInPreview(filePath);
            })
        );

        return disposables;
    }

    private async handleNewPrompt(): Promise<void> {
        try {
            const name = await vscode.window.showInputBox({
                prompt: 'Enter prompt name',
                placeHolder: 'my-awesome-prompt',
                validateInput: (value) => {
                    if (!value.trim()) {return 'Name cannot be empty';}
                    if (!/^[a-zA-Z0-9\s\-_]+$/.test(value)) {return 'Name contains invalid characters';}
                    return undefined;
                }
            });

            if (!name) {return;}

            const category = await vscode.window.showInputBox({
                prompt: 'Enter category (optional)',
                placeHolder: 'general, development, analysis, etc.'
            });

            const result = await this.fileOperationManager.createNewPrompt({
                name,
                category: category || undefined
            });

            if (result.success) {
                await this.fileOperationManager.openPrompt(result.filePath!);
                vscode.window.showInformationMessage(`Created prompt: ${name}`);
            } else {
                vscode.window.showErrorMessage(result.error!);
            }

        } catch (error: any) {
            this.logger.error('Failed to create new prompt:', error);
            vscode.window.showErrorMessage(`Failed to create prompt: ${error.message}`);
        }
    }

    private async handleNewPromptFromTemplate(): Promise<void> {
        try {
            const templates = this.templateManager.getTemplates();

            const templateItems = templates.map(template => ({
                label: template.name,
                description: template.description,
                detail: `Category: ${template.metadata.category}`,
                template
            }));

            const selectedTemplate = await vscode.window.showQuickPick(templateItems, {
                placeHolder: 'Select a template',
                matchOnDescription: true,
                matchOnDetail: true
            });

            if (!selectedTemplate) {return;}

            const name = await vscode.window.showInputBox({
                prompt: 'Enter prompt name',
                placeHolder: 'my-prompt-from-template',
                validateInput: (value) => {
                    if (!value.trim()) {return 'Name cannot be empty';}
                    if (!/^[a-zA-Z0-9\s\-_]+$/.test(value)) {return 'Name contains invalid characters';}
                    return undefined;
                }
            });

            if (!name) {return;}

            const category = await vscode.window.showInputBox({
                prompt: 'Enter category (optional)',
                placeHolder: selectedTemplate.template.metadata.category || 'general'
            });

            // Get template parameters for substitution
            const parameters: Record<string, any> = {
                title: name,
                current_date: new Date().toISOString().split('T')[0],
                current_time: new Date().toLocaleTimeString(),
                current_datetime: new Date().toISOString()
            };

            // Render template with parameters
            const templateContent = await this.templateManager.renderTemplate(
                selectedTemplate.template.id,
                parameters
            );

            const result = await this.fileOperationManager.createNewPrompt({
                name,
                category: category || selectedTemplate.template.metadata.category,
                metadata: {
                    ...selectedTemplate.template.metadata,
                    title: name
                }
            });

            if (result.success) {
                // Replace the default content with rendered template
                const document = await vscode.workspace.openTextDocument(result.filePath!);
                const edit = new vscode.WorkspaceEdit();
                edit.replace(document.uri, new vscode.Range(0, 0, document.lineCount, 0), templateContent);
                await vscode.workspace.applyEdit(edit);
                await document.save();

                await this.fileOperationManager.openPrompt(result.filePath!);
                vscode.window.showInformationMessage(`Created prompt from template: ${name}`);
            } else {
                vscode.window.showErrorMessage(result.error!);
            }

        } catch (error: any) {
            this.logger.error('Failed to create prompt from template:', error);
            vscode.window.showErrorMessage(`Failed to create prompt from template: ${error.message}`);
        }
    }

    private async handleDeletePrompt(filePath: string): Promise<void> {
        const result = await this.fileOperationManager.deletePrompt(filePath);
        if (!result.success && result.error !== 'Deletion cancelled') {
            vscode.window.showErrorMessage(result.error!);
        } else if (result.success) {
            vscode.window.showInformationMessage('Prompt deleted successfully');
        }
    }

    // private async handleDuplicatePrompt(filePath: string): Promise<void> {
    //     try {
    //         const originalName = path.basename(filePath, path.extname(filePath));
    //         const newName = await vscode.window.showInputBox({
    //             prompt: 'Enter name for duplicate',
    //             value: `${originalName} (Copy)`,
    //             validateInput: (value) => {
    //                 if (!value.trim()) return 'Name cannot be empty';
    //                 if (!/^[a-zA-Z0-9\s\-_]+$/.test(value)) return 'Name contains invalid characters';
    //                 return undefined;
    //             }
    //         });

    //         if (!newName) return;

    //         const result = await this.fileOperationManager.duplicatePrompt(filePath, newName);
    //         if (result.success) {
    //             await this.fileOperationManager.openPrompt(result.filePath!);
    //             vscode.window.showInformationMessage(`Duplicated prompt: ${newName}`);
    //         } else {
    //             vscode.window.showErrorMessage(result.error!);
    //         }

    //     } catch (error: any) {
    //         this.logger.error('Failed to duplicate prompt:', error);
    //         vscode.window.showErrorMessage(`Failed to duplicate prompt: ${error.message}`);
    //     }
    // }

    private async handleRenamePrompt(filePath: string): Promise<void> {
        try {
            const currentName = path.basename(filePath, path.extname(filePath));
            const newName = await vscode.window.showInputBox({
                prompt: 'Enter new name',
                value: currentName,
                validateInput: (value) => {
                    if (!value.trim()) {return 'Name cannot be empty';}
                    if (!/^[a-zA-Z0-9\s\-_]+$/.test(value)) {return 'Name contains invalid characters';}
                    return undefined;
                }
            });

            if (!newName || newName === currentName) {return;}

            const result = await this.fileOperationManager.renamePrompt(filePath, newName);
            if (result.success) {
                await this.fileOperationManager.openPrompt(result.filePath!);
                vscode.window.showInformationMessage(`Renamed prompt to: ${newName}`);
            } else {
                vscode.window.showErrorMessage(result.error!);
            }

        } catch (error: any) {
            this.logger.error('Failed to rename prompt:', error);
            vscode.window.showErrorMessage(`Failed to rename prompt: ${error.message}`);
        }
    }

    private async handleMovePrompt(filePath: string): Promise<void> {
        try {
            const newCategory = await vscode.window.showInputBox({
                prompt: 'Enter new category',
                placeHolder: 'general, development, analysis, etc.'
            });

            if (!newCategory) {return;}

            const result = await this.fileOperationManager.movePrompt(filePath, newCategory);
            if (result.success) {
                vscode.window.showInformationMessage(`Moved prompt to category: ${newCategory}`);
            } else {
                vscode.window.showErrorMessage(result.error!);
            }

        } catch (error: any) {
            this.logger.error('Failed to move prompt:', error);
            vscode.window.showErrorMessage(`Failed to move prompt: ${error.message}`);
        }
    }

    private async handleExportPrompts(filePaths: string[]): Promise<void> {
        try {
            const format = await vscode.window.showQuickPick([
                { label: 'JSON', value: 'json' as const },
                { label: 'ZIP Archive', value: 'zip' as const }
            ], {
                placeHolder: 'Select export format'
            });

            if (!format) {return;}

            const result = await this.fileOperationManager.exportPrompts(filePaths, format.value);
            if (result.success) {
                vscode.window.showInformationMessage(`Exported ${filePaths.length} prompts to: ${result.filePath}`);
            } else {
                vscode.window.showErrorMessage(result.error!);
            }

        } catch (error: any) {
            this.logger.error('Failed to export prompts:', error);
            vscode.window.showErrorMessage(`Failed to export prompts: ${error.message}`);
        }
    }

    private async handleBatchDelete(filePaths: string[]): Promise<void> {
        try {
            const result = await this.fileOperationManager.batchDeletePrompts(filePaths);

            if (result.successful.length > 0) {
                vscode.window.showInformationMessage(`Deleted ${result.successful.length} prompts`);
            }

            if (result.failed.length > 0) {
                const failedNames = result.failed.map(f => path.basename(f.filePath)).join(', ');
                vscode.window.showWarningMessage(`Failed to delete: ${failedNames}`);
            }

        } catch (error: any) {
            this.logger.error('Failed to batch delete prompts:', error);
            vscode.window.showErrorMessage(`Failed to batch delete prompts: ${error.message}`);
        }
    }
}
