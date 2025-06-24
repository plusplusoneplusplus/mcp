# Step 9: Extension Integration

## Overview
Integrate all Prompt Store components with the main Wu Wei extension, including registration, lifecycle management, and cross-feature integration.

## Objectives
- Register Prompt Store with VS Code extension host
- Integrate with existing Wu Wei extension architecture
- Implement proper lifecycle management
- Add Prompt Store to extension package.json
- Create seamless integration with other Wu Wei features
- Ensure proper cleanup and disposal

## Tasks

### 9.1 Extension Registration
Update main extension file to include Prompt Store:

```typescript
// In src/extension.ts
import { PromptStoreProvider } from './promptStore/PromptStoreProvider';
import { PromptStoreManager } from './promptStore/PromptStoreManager';
import { FileOperationManager } from './promptStore/FileOperationManager';
import { ConfigurationManager } from './promptStore/ConfigurationManager';

export function activate(context: vscode.ExtensionContext) {
    // ...existing code...

    // Initialize Prompt Store
    const promptStoreManager = initializePromptStore(context);
    
    // Register disposables
    context.subscriptions.push(promptStoreManager);
    
    // ...existing code...
}

function initializePromptStore(context: vscode.ExtensionContext): PromptStoreManager {
    try {
        logger.info('Initializing Wu Wei Prompt Store');
        
        // Create manager instances
        const configManager = new ConfigurationManager(context);
        const promptStoreManager = new PromptStoreManager(context, configManager, logger);
        
        // Register webview provider
        const promptStoreProvider = new PromptStoreProvider(
            context,
            promptStoreManager,
            configManager,
            logger
        );
        
        const webviewProvider = vscode.window.registerWebviewViewProvider(
            'wu-wei.promptStore',
            promptStoreProvider
        );
        
        // Register commands
        const commands = registerPromptStoreCommands(
            promptStoreManager,
            configManager,
            logger
        );
        
        // Add to subscriptions
        context.subscriptions.push(
            webviewProvider,
            ...commands,
            promptStoreManager,
            configManager
        );
        
        logger.info('Wu Wei Prompt Store initialized successfully');
        return promptStoreManager;
        
    } catch (error) {
        logger.error('Failed to initialize Prompt Store:', error);
        vscode.window.showErrorMessage('Wu Wei: Failed to initialize Prompt Store');
        throw error;
    }
}
```

### 9.2 Package.json Updates
Add Prompt Store contributions to package.json:

```json
{
  "contributes": {
    "views": {
      "wu-wei": [
        {
          "id": "wu-wei.promptStore",
          "name": "Prompt Store",
          "when": "true",
          "type": "webview"
        }
      ]
    },
    "commands": [
      {
        "command": "wu-wei.promptStore.selectDirectory",
        "title": "Select Prompt Directory",
        "category": "Wu Wei"
      },
      {
        "command": "wu-wei.promptStore.newPrompt",
        "title": "New Prompt",
        "category": "Wu Wei",
        "icon": "$(add)"
      },
      {
        "command": "wu-wei.promptStore.refreshStore",
        "title": "Refresh Prompt Store",
        "category": "Wu Wei",
        "icon": "$(refresh)"
      },
      {
        "command": "wu-wei.promptStore.openPrompt",
        "title": "Open Prompt",
        "category": "Wu Wei"
      },
      {
        "command": "wu-wei.promptStore.deletePrompt",
        "title": "Delete Prompt",
        "category": "Wu Wei"
      },
      {
        "command": "wu-wei.promptStore.duplicatePrompt",
        "title": "Duplicate Prompt",
        "category": "Wu Wei"
      },
      {
        "command": "wu-wei.promptStore.renamePrompt",
        "title": "Rename Prompt",
        "category": "Wu Wei"
      },
      {
        "command": "wu-wei.promptStore.exportPrompts",
        "title": "Export Prompts",
        "category": "Wu Wei"
      },
      {
        "command": "wu-wei.promptStore.importPrompts",
        "title": "Import Prompts",
        "category": "Wu Wei"
      }
    ],
    "menus": {
      "view/title": [
        {
          "command": "wu-wei.promptStore.selectDirectory",
          "when": "view == wu-wei.promptStore",
          "group": "navigation@1"
        },
        {
          "command": "wu-wei.promptStore.newPrompt",
          "when": "view == wu-wei.promptStore",
          "group": "navigation@2"
        },
        {
          "command": "wu-wei.promptStore.refreshStore",
          "when": "view == wu-wei.promptStore",
          "group": "navigation@3"
        }
      ],
      "commandPalette": [
        {
          "command": "wu-wei.promptStore.openPrompt",
          "when": "false"
        },
        {
          "command": "wu-wei.promptStore.deletePrompt",
          "when": "false"
        },
        {
          "command": "wu-wei.promptStore.duplicatePrompt",
          "when": "false"
        },
        {
          "command": "wu-wei.promptStore.renamePrompt",
          "when": "false"
        }
      ]
    },
    "configuration": {
      "title": "Wu Wei Prompt Store",
      "properties": {
        "wu-wei.promptStore.rootDirectory": {
          "type": "string",
          "default": "",
          "description": "Root directory for prompt collection",
          "scope": "window"
        },
        "wu-wei.promptStore.autoRefresh": {
          "type": "boolean",
          "default": true,
          "description": "Automatically refresh when files change"
        },
        "wu-wei.promptStore.showMetadataTooltips": {
          "type": "boolean",
          "default": true,
          "description": "Show metadata information in tooltips"
        },
        "wu-wei.promptStore.enableTemplates": {
          "type": "boolean",
          "default": true,
          "description": "Enable prompt templates with parameters"
        },
        "wu-wei.promptStore.fileWatcher.enabled": {
          "type": "boolean",
          "default": true,
          "description": "Enable file system monitoring"
        },
        "wu-wei.promptStore.fileWatcher.debounceMs": {
          "type": "number",
          "default": 500,
          "minimum": 100,
          "maximum": 5000,
          "description": "Debounce delay for file changes (ms)"
        },
        "wu-wei.promptStore.defaultTemplate": {
          "type": "string",
          "default": "basic",
          "enum": ["basic", "meeting-notes", "code-review", "feature-spec"],
          "description": "Default template for new prompts"
        }
      }
    }
  }
}
```

### 9.3 Centralized Manager Class
Create a centralized manager for all Prompt Store functionality:

```typescript
export class PromptStoreManager implements vscode.Disposable {
    private disposables: vscode.Disposable[] = [];
    private promptManager: PromptManager;
    private fileWatcher: PromptFileWatcher;
    private fileOperations: FileOperationManager;
    private templateManager: TemplateManager;
    private treeManager: PromptTreeManager;
    private isInitialized = false;
    
    constructor(
        private context: vscode.ExtensionContext,
        private configManager: ConfigurationManager,
        private logger: Logger
    ) {
        this.initialize();
    }
    
    private async initialize(): Promise<void> {
        try {
            // Initialize core components
            this.promptManager = new PromptManager(this.configManager, this.logger);
            this.fileWatcher = new PromptFileWatcher(this.logger);
            this.templateManager = new TemplateManager();
            this.treeManager = new PromptTreeManager();
            
            this.fileOperations = new FileOperationManager(
                this.promptManager,
                this.configManager,
                this.templateManager,
                this.logger
            );
            
            // Setup file watcher integration
            this.setupFileWatcherIntegration();
            
            // Setup configuration change handling
            this.setupConfigurationHandling();
            
            // Load initial data
            await this.loadInitialData();
            
            this.isInitialized = true;
            this.logger.info('PromptStoreManager initialized successfully');
            
        } catch (error) {
            this.logger.error('Failed to initialize PromptStoreManager:', error);
            throw error;
        }
    }
    
    private setupFileWatcherIntegration(): void {
        this.fileWatcher.on('fileAdded', async (filePath) => {
            try {
                const prompt = await this.promptManager.loadPrompt(filePath);
                this.notifyProvidersOfChange('promptAdded', prompt);
            } catch (error) {
                this.logger.error('Failed to handle file added event:', error);
            }
        });
        
        this.fileWatcher.on('fileChanged', async (filePath) => {
            try {
                const prompt = await this.promptManager.loadPrompt(filePath);
                this.notifyProvidersOfChange('promptUpdated', prompt);
            } catch (error) {
                this.logger.error('Failed to handle file changed event:', error);
            }
        });
        
        this.fileWatcher.on('fileDeleted', (filePath) => {
            this.notifyProvidersOfChange('promptDeleted', filePath);
        });
    }
    
    private setupConfigurationHandling(): void {
        const configWatcher = vscode.workspace.onDidChangeConfiguration((event) => {
            if (event.affectsConfiguration('wu-wei.promptStore')) {
                this.handleConfigurationChange();
            }
        });
        
        this.disposables.push(configWatcher);
    }
    
    private async handleConfigurationChange(): Promise<void> {
        const config = this.configManager.getConfig();
        
        // Restart file watcher if directory changed
        if (config.rootDirectory) {
            this.fileWatcher.stop();
            this.fileWatcher.start(config.rootDirectory);
            await this.loadInitialData();
        } else {
            this.fileWatcher.stop();
        }
        
        this.notifyProvidersOfChange('configChanged', config);
    }
    
    private async loadInitialData(): Promise<void> {
        const config = this.configManager.getConfig();
        
        if (config.rootDirectory) {
            try {
                const prompts = await this.promptManager.loadAllPrompts(config.rootDirectory);
                this.notifyProvidersOfChange('promptsLoaded', prompts);
                
                if (config.fileWatcher.enabled) {
                    this.fileWatcher.start(config.rootDirectory);
                }
            } catch (error) {
                this.logger.error('Failed to load initial prompts:', error);
                this.notifyProvidersOfChange('error', error.message);
            }
        }
    }
    
    // Provider registration and communication
    private providers: Set<PromptStoreProvider> = new Set();
    
    registerProvider(provider: PromptStoreProvider): void {
        this.providers.add(provider);
    }
    
    unregisterProvider(provider: PromptStoreProvider): void {
        this.providers.delete(provider);
    }
    
    private notifyProvidersOfChange(type: string, data: any): void {
        for (const provider of this.providers) {
            provider.handleDataChange(type, data);
        }
    }
    
    // Public API for providers
    async getAllPrompts(): Promise<Prompt[]> {
        const config = this.configManager.getConfig();
        if (!config.rootDirectory) return [];
        
        return await this.promptManager.loadAllPrompts(config.rootDirectory);
    }
    
    async createPrompt(options: NewPromptOptions): Promise<FileOperationResult> {
        return await this.fileOperations.createNewPrompt(options);
    }
    
    async openPrompt(filePath: string): Promise<void> {
        return await this.fileOperations.openPrompt(filePath);
    }
    
    async deletePrompt(filePath: string): Promise<FileOperationResult> {
        return await this.fileOperations.deletePrompt(filePath);
    }
    
    async duplicatePrompt(filePath: string, newName: string): Promise<FileOperationResult> {
        return await this.fileOperations.duplicatePrompt(filePath, newName);
    }
    
    getTemplates(): PromptTemplate[] {
        return this.templateManager.getTemplates();
    }
    
    buildTree(prompts: Prompt[]): TreeNode[] {
        return this.treeManager.buildTree(prompts);
    }
    
    filterTree(nodes: TreeNode[], query: string, filters: TreeFilters): TreeNode[] {
        return this.treeManager.filterTree(nodes, query, filters);
    }
    
    dispose(): void {
        this.fileWatcher.dispose();
        this.disposables.forEach(d => d.dispose());
        this.disposables = [];
        this.providers.clear();
        this.logger.info('PromptStoreManager disposed');
    }
}
```

### 9.4 Cross-Feature Integration
Integrate with existing Wu Wei features:

```typescript
// Integration with chat provider
export class ChatPromptIntegration {
    constructor(
        private chatProvider: UnifiedWuWeiChatProvider,
        private promptStoreManager: PromptStoreManager
    ) {}
    
    async insertPromptIntoChat(promptPath: string): Promise<void> {
        try {
            const prompt = await fs.readFile(promptPath, 'utf8');
            const content = this.extractPromptContent(prompt);
            
            // Insert into active chat session
            await this.chatProvider.insertText(content);
            
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to insert prompt: ${error.message}`);
        }
    }
    
    private extractPromptContent(fileContent: string): string {
        // Remove frontmatter and return just the prompt content
        const frontmatterRegex = /^---\r?\n[\s\S]*?\r?\n---\r?\n/;
        return fileContent.replace(frontmatterRegex, '').trim();
    }
    
    // Add command to insert prompts into chat
    registerChatIntegrationCommands(context: vscode.ExtensionContext): void {
        const insertPromptCommand = vscode.commands.registerCommand(
            'wu-wei.promptStore.insertIntoChat',
            async (promptPath: string) => {
                await this.insertPromptIntoChat(promptPath);
            }
        );
        
        context.subscriptions.push(insertPromptCommand);
    }
}

// Integration with agent panel
export class AgentPromptIntegration {
    constructor(
        private agentProvider: WuWeiAgentPanelProvider,
        private promptStoreManager: PromptStoreManager
    ) {}
    
    async usePromptWithAgent(promptPath: string, agentId: string): Promise<void> {
        try {
            const prompt = await fs.readFile(promptPath, 'utf8');
            const content = this.extractPromptContent(prompt);
            
            // Send to agent panel
            await this.agentProvider.sendRequest(agentId, content);
            
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to use prompt with agent: ${error.message}`);
        }
    }
}
```

### 9.5 Error Handling and Recovery
Implement comprehensive error handling:

```typescript
export class PromptStoreErrorHandler {
    constructor(private logger: Logger) {}
    
    handleError(error: Error, context: string): void {
        this.logger.error(`Prompt Store error in ${context}:`, error);
        
        // Categorize and handle different types of errors
        if (error.code === 'ENOENT') {
            this.handleFileNotFoundError(error, context);
        } else if (error.code === 'EACCES') {
            this.handlePermissionError(error, context);
        } else if (error.name === 'YAMLException') {
            this.handleYAMLError(error, context);
        } else {
            this.handleGenericError(error, context);
        }
    }
    
    private handleFileNotFoundError(error: Error, context: string): void {
        vscode.window.showErrorMessage(
            `File not found: ${error.message}. The prompt may have been moved or deleted.`,
            'Refresh Store'
        ).then(action => {
            if (action === 'Refresh Store') {
                vscode.commands.executeCommand('wu-wei.promptStore.refreshStore');
            }
        });
    }
    
    private handlePermissionError(error: Error, context: string): void {
        vscode.window.showErrorMessage(
            `Permission denied: ${error.message}. Please check file permissions.`,
            'Select Different Directory'
        ).then(action => {
            if (action === 'Select Different Directory') {
                vscode.commands.executeCommand('wu-wei.promptStore.selectDirectory');
            }
        });
    }
    
    private handleYAMLError(error: Error, context: string): void {
        vscode.window.showErrorMessage(
            `Invalid YAML metadata: ${error.message}. Please check the frontmatter format.`,
            'View Documentation'
        ).then(action => {
            if (action === 'View Documentation') {
                vscode.env.openExternal(vscode.Uri.parse('https://wu-wei-docs.com/prompt-store'));
            }
        });
    }
    
    private handleGenericError(error: Error, context: string): void {
        vscode.window.showErrorMessage(
            `Prompt Store error: ${error.message}`,
            'Show Logs'
        ).then(action => {
            if (action === 'Show Logs') {
                this.logger.show();
            }
        });
    }
}
```

### 9.6 Testing Integration
Create integration tests that verify cross-feature functionality:

```typescript
// Integration test suite
describe('Prompt Store Integration', () => {
    let extension: vscode.Extension<any>;
    let promptStoreManager: PromptStoreManager;
    
    beforeEach(async () => {
        extension = vscode.extensions.getExtension('wu-wei.extension')!;
        await extension.activate();
        
        // Access the prompt store manager from the extension
        promptStoreManager = extension.exports.promptStoreManager;
    });
    
    test('should integrate with chat provider', async () => {
        // Test chat integration functionality
    });
    
    test('should integrate with agent panel', async () => {
        // Test agent integration functionality
    });
    
    test('should handle configuration changes', async () => {
        // Test configuration change handling
    });
    
    test('should cleanup resources on deactivation', async () => {
        // Test proper cleanup
    });
});
```

## Documentation Updates

### 9.7 README Updates
Update the main README to include Prompt Store information:

```markdown
## Features

### 🗂️ Prompt Store
- **Directory-based Management**: Organize prompts in folders
- **Rich Metadata**: YAML frontmatter with tags, categories, and parameters
- **Smart Search**: Find prompts by content, metadata, or tags
- **Template System**: Pre-built templates for common use cases
- **Real-time Sync**: Automatic updates when files change
- **Editor Integration**: Seamless editing in VS Code
- **Batch Operations**: Efficiently manage multiple prompts

#### Getting Started with Prompt Store
1. Open the Wu Wei Prompt Store panel
2. Click "Configure Directory" to select your prompts folder
3. Start creating and organizing your prompt templates
4. Use search and filters to quickly find the right prompt
```

### 9.8 CHANGELOG Updates
Document the new feature:

```markdown
## [1.1.0] - 2025-06-23

### Added
- **Prompt Store**: Complete prompt management system
  - Directory-based prompt organization
  - YAML frontmatter metadata support
  - Hierarchical tree view with search and filtering
  - Template system for common prompt patterns
  - Real-time file system monitoring
  - Batch operations for efficient management
  - Integration with chat and agent features
```

## Acceptance Criteria
- [ ] Prompt Store is fully integrated with Wu Wei extension
- [ ] All commands are registered and functional
- [ ] Webview displays correctly in VS Code sidebar
- [ ] Configuration settings work properly
- [ ] File watcher integrates with extension lifecycle
- [ ] Cross-feature integration works (chat, agent)
- [ ] Error handling provides clear user feedback
- [ ] Resources are properly cleaned up on deactivation
- [ ] All integration tests pass
- [ ] Documentation is updated appropriately

## Dependencies
- **Steps 1-8**: All previous implementation steps must be completed
- Main Wu Wei extension architecture
- VS Code Extension API
- Existing chat and agent providers

## Estimated Effort
**4-6 hours**

## Files to Implement
1. `src/extension.ts` (update main extension file)
2. `src/promptStore/PromptStoreManager.ts` (centralized manager)
3. `src/promptStore/integrations/ChatIntegration.ts` (chat integration)
4. `src/promptStore/integrations/AgentIntegration.ts` (agent integration)
5. `src/promptStore/PromptStoreErrorHandler.ts` (error handling)
6. `package.json` (update contributions)
7. `README.md` (update documentation)
8. `CHANGELOG.md` (document changes)
9. `test/integration/promptStoreIntegration.test.ts` (integration tests)

## Next Step
Proceed to **Step 10: Testing and Polish** to finalize the implementation with comprehensive testing and user experience improvements.
