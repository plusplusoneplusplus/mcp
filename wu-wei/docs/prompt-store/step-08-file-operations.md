# Step 8: File Operations

## Overview
Implement core file operations for creating, editing, deleting, and managing prompt files through the extension interface.

## Objectives
- Create new prompt files with templates
- Open existing prompts in VS Code editor
- Handle file deletion and renaming
- Implement prompt duplication
- Support batch operations
- Integrate with VS Code's file system

## Tasks

### 8.1 File Operation Manager
Create comprehensive file operations handler:

```typescript
interface FileOperationResult {
    success: boolean;
    filePath?: string;
    error?: string;
}

interface NewPromptOptions {
    name: string;
    category?: string;
    template?: string;
    metadata?: Partial<PromptMetadata>;
}

class FileOperationManager {
    constructor(
        private promptManager: PromptManager,
        private configManager: ConfigurationManager,
        private logger: Logger
    ) {}
    
    async createNewPrompt(options: NewPromptOptions): Promise<FileOperationResult>
    async openPrompt(filePath: string): Promise<void>
    async deletePrompt(filePath: string): Promise<FileOperationResult>
    async duplicatePrompt(filePath: string, newName: string): Promise<FileOperationResult>
    async renamePrompt(filePath: string, newName: string): Promise<FileOperationResult>
    async movePrompt(filePath: string, newCategory: string): Promise<FileOperationResult>
    async exportPrompts(filePaths: string[], format: 'json' | 'zip'): Promise<FileOperationResult>
    async importPrompts(importPath: string): Promise<FileOperationResult>
}
```

### 8.2 New Prompt Creation
Implement prompt creation with templates:

```typescript
async createNewPrompt(options: NewPromptOptions): Promise<FileOperationResult> {
    try {
        const config = this.configManager.getConfig();
        
        if (!config.rootDirectory) {
            return {
                success: false,
                error: 'No prompt directory configured'
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
        
    } catch (error) {
        this.logger.error('Failed to create new prompt:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

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
        created: new Date(),
        updated: new Date(),
        author: await this.getDefaultAuthor(),
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
        content += await this.loadTemplate(options.template);
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
```

### 8.3 File Opening Integration
Integrate with VS Code editor:

```typescript
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
        
    } catch (error) {
        this.logger.error('Failed to open prompt:', error);
        vscode.window.showErrorMessage(`Failed to open prompt: ${error.message}`);
    }
}

async openPromptInPreview(filePath: string): Promise<void> {
    try {
        const document = await vscode.workspace.openTextDocument(filePath);
        await vscode.window.showTextDocument(document, {
            preview: true,
            preserveFocus: true,
            viewColumn: vscode.ViewColumn.Beside
        });
        
    } catch (error) {
        this.logger.error('Failed to open prompt in preview:', error);
    }
}
```

### 8.4 Deletion and Cleanup
Implement safe file deletion:

```typescript
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
        
    } catch (error) {
        this.logger.error('Failed to delete prompt:', error);
        return {
            success: false,
            error: error.message
        };
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
    if (dirPath === config.rootDirectory) return;
    
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
```

### 8.5 Duplication and Renaming
Implement file duplication and renaming:

```typescript
async duplicatePrompt(filePath: string, newName: string): Promise<FileOperationResult> {
    try {
        // Load original prompt
        const originalPrompt = await this.promptManager.loadPrompt(filePath);
        
        // Generate new file path
        const newFilePath = await this.generatePromptPath(newName, originalPrompt.metadata.category);
        
        // Check if new file already exists
        if (await this.fileExists(newFilePath)) {
            return {
                success: false,
                error: `Prompt '${newName}' already exists`
            };
        }
        
        // Update metadata for duplicate
        const newMetadata: PromptMetadata = {
            ...originalPrompt.metadata,
            title: newName,
            created: new Date(),
            updated: new Date(),
            version: '1.0.0' // Reset version for duplicate
        };
        
        // Generate new content
        const newPrompt: Prompt = {
            ...originalPrompt,
            filePath: newFilePath,
            metadata: newMetadata
        };
        
        // Save duplicate
        await this.promptManager.savePrompt(newPrompt);
        
        this.logger.info(`Duplicated prompt: ${filePath} -> ${newFilePath}`);
        
        return {
            success: true,
            filePath: newFilePath
        };
        
    } catch (error) {
        this.logger.error('Failed to duplicate prompt:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

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
            title: newName,
            updated: new Date()
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
        
    } catch (error) {
        this.logger.error('Failed to rename prompt:', error);
        return {
            success: false,
            error: error.message
        };
    }
}
```

### 8.6 Batch Operations
Support batch file operations:

```typescript
interface BatchOperationResult {
    successful: string[];
    failed: Array<{ filePath: string; error: string }>;
}

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
            await fs.unlink(filePath);
            result.successful.push(filePath);
            this.logger.info(`Batch deleted: ${filePath}`);
        } catch (error) {
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
        } catch (error) {
            result.failed.push({
                filePath,
                error: error.message
            });
        }
    }
    
    return result;
}
```

### 8.7 Template System
Implement prompt templates:

```typescript
interface PromptTemplate {
    id: string;
    name: string;
    description: string;
    content: string;
    metadata: Partial<PromptMetadata>;
    parameters: ParameterDef[];
}

class TemplateManager {
    private builtInTemplates: PromptTemplate[] = [
        {
            id: 'meeting-notes',
            name: 'Meeting Notes',
            description: 'Template for structured meeting documentation',
            content: `# Meeting Notes: {{meeting_title}}

**Date:** {{date}}
**Duration:** {{duration}} minutes
**Attendees:** {{attendees}}

## Agenda
1. 
2. 
3. 

## Discussion Points

## Action Items
- [ ] 
- [ ] 

## Next Steps
`,
            metadata: {
                category: 'productivity',
                tags: ['meeting', 'documentation', 'template']
            },
            parameters: [
                { name: 'meeting_title', type: 'string', required: true },
                { name: 'date', type: 'string', default: '{{current_date}}' },
                { name: 'duration', type: 'number', default: 60 },
                { name: 'attendees', type: 'array', required: true }
            ]
        }
        // Add more built-in templates...
    ];
    
    getTemplates(): PromptTemplate[] {
        return this.builtInTemplates;
    }
    
    getTemplate(id: string): PromptTemplate | undefined {
        return this.builtInTemplates.find(t => t.id === id);
    }
    
    async loadTemplate(id: string): Promise<string> {
        const template = this.getTemplate(id);
        return template ? template.content : '';
    }
}
```

## Command Integration

### 8.8 VS Code Commands
Register file operation commands:

```typescript
// In extension.ts activation
const fileOperations = new FileOperationManager(promptManager, configManager, logger);

const newPromptCommand = vscode.commands.registerCommand('wu-wei.promptStore.newPrompt', async () => {
    const name = await vscode.window.showInputBox({
        prompt: 'Enter prompt name',
        validateInput: (value) => {
            if (!value.trim()) return 'Name cannot be empty';
            if (!/^[a-zA-Z0-9\s\-_]+$/.test(value)) return 'Name contains invalid characters';
            return undefined;
        }
    });
    
    if (name) {
        const result = await fileOperations.createNewPrompt({ name });
        if (result.success) {
            await fileOperations.openPrompt(result.filePath!);
        } else {
            vscode.window.showErrorMessage(result.error!);
        }
    }
});

const deletePromptCommand = vscode.commands.registerCommand('wu-wei.promptStore.deletePrompt', async (filePath: string) => {
    const result = await fileOperations.deletePrompt(filePath);
    if (!result.success) {
        vscode.window.showErrorMessage(result.error!);
    }
});

const duplicatePromptCommand = vscode.commands.registerCommand('wu-wei.promptStore.duplicatePrompt', async (filePath: string) => {
    const originalName = path.basename(filePath, path.extname(filePath));
    const newName = await vscode.window.showInputBox({
        prompt: 'Enter name for duplicate',
        value: `${originalName} (Copy)`
    });
    
    if (newName) {
        const result = await fileOperations.duplicatePrompt(filePath, newName);
        if (result.success) {
            await fileOperations.openPrompt(result.filePath!);
        } else {
            vscode.window.showErrorMessage(result.error!);
        }
    }
});
```

## Testing Requirements

### 8.9 Unit Tests
Test scenarios for:
- New prompt creation with various options
- File opening and editor integration
- Deletion with cleanup
- Duplication and renaming
- Batch operations
- Template system
- Error handling

### 8.10 Integration Tests
- End-to-end file operations
- VS Code editor integration
- File system error scenarios
- Command registration and execution
- Template rendering

## Acceptance Criteria
- [ ] New prompts can be created with templates
- [ ] Existing prompts open correctly in VS Code editor
- [ ] File deletion works with confirmation and cleanup
- [ ] Duplication preserves content and updates metadata
- [ ] Renaming updates both file and metadata
- [ ] Batch operations handle multiple files efficiently
- [ ] Templates provide useful starting points
- [ ] All operations integrate with VS Code commands
- [ ] Error handling provides clear user feedback
- [ ] File system changes are properly monitored

## Dependencies
- **Steps 1-7**: All previous infrastructure must be completed
- VS Code editor integration
- File system operations
- Template system
- Command registration

## Estimated Effort
**8-10 hours**

## Files to Implement
1. `src/promptStore/FileOperationManager.ts` (main implementation)
2. `src/promptStore/TemplateManager.ts` (template system)
3. `src/promptStore/commands.ts` (VS Code commands)
4. `test/promptStore/FileOperationManager.test.ts` (unit tests)
5. `test/promptStore/integration/fileOperations.test.ts` (integration tests)

## Next Step
Proceed to **Step 9: Extension Integration** to integrate all components with the main extension.
