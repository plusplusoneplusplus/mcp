/**
 * File Operation Manager - Core file operations for prompt management
 * Following wu wei principles: simple, efficient file operations that flow naturally
 */

import * as vscode from 'vscode';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as yaml from 'yaml';
import {
    FileOperationResult,
    NewPromptOptions,
    BatchOperationResult,
    Prompt,
    PromptMetadata
} from './types';
import { PromptManager } from './PromptManager';
import { ConfigurationManager } from './ConfigurationManager';
import { WuWeiLogger } from '../logger';
// import { TemplateManager } from './TemplateManager';

export class FileOperationManager {
    private logger: WuWeiLogger;

    constructor(
        private promptManager: PromptManager,
        private configManager: ConfigurationManager
        // private templateManager: TemplateManager
    ) {
        this.logger = WuWeiLogger.getInstance();
    }

    /**
     * Create a new prompt file with optional template
     */
    async createNewPrompt(options: NewPromptOptions): Promise<FileOperationResult> {
        try {
            const config = this.configManager.getConfig();

            if (!config.rootDirectory) {
                return {
                    success: false,
                    error: 'No prompt directory configured. Please configure a root directory in settings.'
                };
            }

            // Generate file path
            const filePath = await this.generatePromptPath(options.name, options.category);

            // Check if file already exists
            if (await this.fileExists(filePath)) {
                return {
                    success: false,
                    error: `Prompt '${options.name}' already exists`
                };
            }

            // Create directory if needed
            await this.ensureDirectoryExists(path.dirname(filePath));

            // Generate content from template
            const content = await this.generatePromptContent(options);

            // Write file
            await fs.writeFile(filePath, content, 'utf8');

            // Log operation
            this.logger.info(`Created new prompt: ${filePath}`);

            return {
                success: true,
                filePath
            };

        } catch (error: any) {
            this.logger.error('Failed to create new prompt:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Open a prompt in VS Code editor
     */
    async openPrompt(filePath: string): Promise<void> {
        try {
            // Verify file exists
            if (!await this.fileExists(filePath)) {
                throw new Error(`Prompt file not found: ${filePath}`);
            }

            // Open in VS Code editor
            const document = await vscode.workspace.openTextDocument(filePath);
            await vscode.window.showTextDocument(document, {
                preview: false,
                preserveFocus: false
            });

            this.logger.info(`Opened prompt: ${filePath}`);

        } catch (error: any) {
            this.logger.error('Failed to open prompt:', error);
            vscode.window.showErrorMessage(`Failed to open prompt: ${error.message}`);
        }
    }

    /**
     * Open a prompt in preview mode
     */
    async openPromptInPreview(filePath: string): Promise<void> {
        try {
            const document = await vscode.workspace.openTextDocument(filePath);
            await vscode.window.showTextDocument(document, {
                preview: true,
                preserveFocus: true,
                viewColumn: vscode.ViewColumn.Beside
            });

        } catch (error: any) {
            this.logger.error('Failed to open prompt in preview:', error);
        }
    }

    /**
     * Delete a prompt file with confirmation
     */
    async deletePrompt(filePath: string): Promise<FileOperationResult> {
        try {
            // Confirm deletion
            const fileName = path.basename(filePath);
            const confirm = await vscode.window.showWarningMessage(
                `Delete prompt '${fileName}'? This action cannot be undone.`,
                { modal: true },
                'Delete'
            );

            if (confirm !== 'Delete') {
                return { success: false, error: 'Deletion cancelled' };
            }

            // Close any open editors for this file
            await this.closeEditorsForFile(filePath);

            // Delete file
            await fs.unlink(filePath);

            // Clean up empty directories
            await this.cleanupEmptyDirectories(path.dirname(filePath));

            this.logger.info(`Deleted prompt: ${filePath}`);

            return { success: true };

        } catch (error: any) {
            this.logger.error('Failed to delete prompt:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Rename a prompt file and update metadata
     */
    async renamePrompt(filePath: string, newName: string): Promise<FileOperationResult> {
        try {
            // Generate new file path
            const oldPrompt = await this.promptManager.loadPrompt(filePath);
            const newFilePath = await this.generatePromptPath(newName, oldPrompt.metadata.category);

            // Check if new file already exists
            if (await this.fileExists(newFilePath)) {
                return {
                    success: false,
                    error: `Prompt '${newName}' already exists`
                };
            }

            // Close any open editors for the old file
            await this.closeEditorsForFile(filePath);

            // Update metadata
            const updatedMetadata: PromptMetadata = {
                ...oldPrompt.metadata,
                title: newName
            };

            // Create updated prompt
            const updatedPrompt: Prompt = {
                ...oldPrompt,
                filePath: newFilePath,
                metadata: updatedMetadata
            };

            // Save to new location
            await this.promptManager.savePrompt(updatedPrompt);

            // Delete old file
            await fs.unlink(filePath);

            // Clean up empty directories
            await this.cleanupEmptyDirectories(path.dirname(filePath));

            this.logger.info(`Renamed prompt: ${filePath} -> ${newFilePath}`);

            return {
                success: true,
                filePath: newFilePath
            };

        } catch (error: any) {
            this.logger.error('Failed to rename prompt:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Move a prompt to a different category
     */
    async movePrompt(filePath: string, newCategory: string): Promise<FileOperationResult> {
        try {
            const prompt = await this.promptManager.loadPrompt(filePath);
            const newFilePath = await this.generatePromptPath(prompt.metadata.title, newCategory);

            if (await this.fileExists(newFilePath)) {
                return {
                    success: false,
                    error: `Prompt already exists in category '${newCategory}'`
                };
            }

            // Update metadata
            const updatedMetadata: PromptMetadata = {
                ...prompt.metadata,
                category: newCategory
            };

            const updatedPrompt: Prompt = {
                ...prompt,
                filePath: newFilePath,
                metadata: updatedMetadata
            };

            // Create directory if needed
            await this.ensureDirectoryExists(path.dirname(newFilePath));

            // Save to new location
            await this.promptManager.savePrompt(updatedPrompt);

            // Delete old file
            await fs.unlink(filePath);

            // Clean up empty directories
            await this.cleanupEmptyDirectories(path.dirname(filePath));

            this.logger.info(`Moved prompt: ${filePath} -> ${newFilePath}`);

            return {
                success: true,
                filePath: newFilePath
            };

        } catch (error: any) {
            this.logger.error('Failed to move prompt:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Batch delete multiple prompts
     */
    async batchDeletePrompts(filePaths: string[]): Promise<BatchOperationResult> {
        const result: BatchOperationResult = {
            successful: [],
            failed: []
        };

        // Confirm batch deletion
        const confirm = await vscode.window.showWarningMessage(
            `Delete ${filePaths.length} prompts? This action cannot be undone.`,
            { modal: true },
            'Delete All'
        );

        if (confirm !== 'Delete All') {
            return result;
        }

        // Process each file
        for (const filePath of filePaths) {
            try {
                await this.closeEditorsForFile(filePath);
                await fs.unlink(filePath);
                result.successful.push(filePath);
                this.logger.info(`Batch deleted: ${filePath}`);
            } catch (error: any) {
                result.failed.push({
                    filePath,
                    error: error.message
                });
                this.logger.error(`Failed to batch delete ${filePath}:`, error);
            }
        }

        // Clean up empty directories
        const uniqueDirectories = [...new Set(filePaths.map(fp => path.dirname(fp)))];
        for (const dir of uniqueDirectories) {
            await this.cleanupEmptyDirectories(dir);
        }

        return result;
    }

    /**
     * Batch move prompts to a new category
     */
    async batchMovePrompts(filePaths: string[], targetCategory: string): Promise<BatchOperationResult> {
        const result: BatchOperationResult = {
            successful: [],
            failed: []
        };

        for (const filePath of filePaths) {
            try {
                const moveResult = await this.movePrompt(filePath, targetCategory);
                if (moveResult.success) {
                    result.successful.push(moveResult.filePath || filePath);
                } else {
                    result.failed.push({
                        filePath,
                        error: moveResult.error || 'Unknown error'
                    });
                }
            } catch (error: any) {
                result.failed.push({
                    filePath,
                    error: error.message
                });
            }
        }

        return result;
    }

    /**
     * Export prompts to various formats
     */
    async exportPrompts(filePaths: string[], format: 'json' | 'zip'): Promise<FileOperationResult> {
        try {
            const exportData = [];

            for (const filePath of filePaths) {
                const prompt = await this.promptManager.loadPrompt(filePath);
                exportData.push({
                    metadata: prompt.metadata,
                    content: prompt.content,
                    filePath: prompt.filePath
                });
            }

            if (format === 'json') {
                const exportPath = await vscode.window.showSaveDialog({
                    defaultUri: vscode.Uri.file('prompts-export.json'),
                    filters: {
                        'JSON files': ['json']
                    }
                });

                if (exportPath) {
                    await fs.writeFile(exportPath.fsPath, JSON.stringify(exportData, null, 2), 'utf8');
                    return {
                        success: true,
                        filePath: exportPath.fsPath
                    };
                }
            }

            return { success: false, error: 'Export cancelled' };

        } catch (error: any) {
            this.logger.error('Failed to export prompts:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Private helper methods

    private async generatePromptPath(name: string, category?: string): Promise<string> {
        const config = this.configManager.getConfig();
        const sanitizedName = this.sanitizeFileName(name);
        const fileName = sanitizedName.endsWith('.md') ? sanitizedName : `${sanitizedName}.md`;

        if (category) {
            const sanitizedCategory = this.sanitizeFileName(category);
            return path.join(config.rootDirectory, sanitizedCategory, fileName);
        }

        return path.join(config.rootDirectory, fileName);
    }

    private async generatePromptContent(options: NewPromptOptions): Promise<string> {
        const metadata: PromptMetadata = {
            title: options.name,
            description: '',
            category: options.category,
            tags: [],
            ...options.metadata
        };

        let content = '';

        // Add frontmatter if metadata exists
        if (Object.keys(metadata).length > 0) {
            content += '---\n';
            content += yaml.stringify(metadata);
            content += '---\n\n';
        }

        // Add template content
        if (options.template) {
            // content += await this.templateManager.loadTemplate(options.template);
            content += `# {{title}}\n\n`;
            content += '{{description}}\n\n';
            content += '## Parameters\n\n';
            content += '{{#each parameters}}\n';
            content += '- **{{name}}**: {{description}}\n';
            content += '{{/each}}\n\n';
            content += '## Usage\n\n';
            content += '{{usage}}\n';
        } else {
            content += `# ${options.name}\n\n`;
            content += 'Your prompt content goes here...\n\n';
            content += '## Parameters\n\n';
            content += '- **param1**: Description of parameter\n\n';
            content += '## Usage\n\n';
            content += 'Describe how to use this prompt...\n';
        }

        return content;
    }

    private sanitizeFileName(name: string): string {
        return name
            .replace(/[^a-zA-Z0-9\s\-_]/g, '') // Remove invalid characters
            .replace(/\s+/g, '-') // Replace spaces with hyphens
            .toLowerCase() // Convert to lowercase
            .replace(/-+/g, '-') // Remove duplicate hyphens
            .replace(/^-|-$/g, ''); // Remove leading/trailing hyphens
    }

    private async fileExists(filePath: string): Promise<boolean> {
        try {
            await fs.access(filePath);
            return true;
        } catch {
            return false;
        }
    }

    private async ensureDirectoryExists(dirPath: string): Promise<void> {
        try {
            await fs.mkdir(dirPath, { recursive: true });
        } catch (error: any) {
            this.logger.error(`Failed to create directory ${dirPath}:`, error);
            throw error;
        }
    }

    private async closeEditorsForFile(filePath: string): Promise<void> {
        const editors = vscode.window.visibleTextEditors;

        for (const editor of editors) {
            if (editor.document.uri.fsPath === filePath) {
                await vscode.window.showTextDocument(editor.document, editor.viewColumn);
                await vscode.commands.executeCommand('workbench.action.closeActiveEditor');
            }
        }
    }

    private async cleanupEmptyDirectories(dirPath: string): Promise<void> {
        const config = this.configManager.getConfig();

        // Don't delete the root directory
        if (dirPath === config.rootDirectory) { return; }

        try {
            const entries = await fs.readdir(dirPath);

            // If directory is empty, delete it
            if (entries.length === 0) {
                await fs.rmdir(dirPath);

                // Recursively clean up parent directories
                await this.cleanupEmptyDirectories(path.dirname(dirPath));
            }
        } catch (error) {
            // Ignore errors - directory might not be empty or might not exist
        }
    }

    /**
     * Dispose resources
     */
    dispose(): void {
        // Clean up any resources if needed
        this.logger.info('FileOperationManager disposed');
    }
}
