# Step 5: Basic Configuration Management

## Overview
Implement configuration management for the Prompt Store, including user settings, directory selection, and session persistence.

## Objectives
- Handle VS Code workspace settings
- Persist user configuration across sessions
- Provide directory selection UI
- Validate configuration values
- Support configuration migration and defaults

## Tasks

### 5.1 Configuration Interface
Define configuration structure and management:

```typescript
interface PromptStoreConfig {
    rootDirectory: string;
    autoRefresh: boolean;
    showMetadataTooltips: boolean;
    enableTemplates: boolean;
    metadataSchema: MetadataSchemaConfig;
    fileWatcher: FileWatcherConfig;
}

class ConfigurationManager {
    getConfig(): PromptStoreConfig
    updateConfig(config: Partial<PromptStoreConfig>): Promise<void>
    resetToDefaults(): Promise<void>
    validateConfig(config: PromptStoreConfig): ValidationResult
    migrateConfig(oldVersion: string): Promise<void>
}
```

### 5.2 VS Code Settings Integration
- Define settings contribution in `package.json`
- Handle workspace vs user settings
- Provide setting descriptions and defaults
- Support setting validation and enum values
- React to setting changes

### 5.3 Directory Selection
Implement directory selection workflow:
- Native OS directory picker
- Validation of selected directory
- Permission checking
- Path normalization
- Relative path support

### 5.4 Session Persistence
- Store configuration in workspace state
- Remember last used directories
- Persist UI state (expanded folders, filters)
- Handle workspace changes
- Clean up old state data

### 5.5 Configuration Validation
Validate configuration values:
- Directory existence and permissions
- File watcher settings ranges
- Boolean flag validation
- Schema configuration validation
- Migration compatibility checks

## Implementation Details

### 5.5.1 Settings Contribution (package.json)
```json
{
  "contributes": {
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
        }
      }
    }
  }
}
```

### 5.5.2 Configuration Manager Implementation
```typescript
class ConfigurationManager {
    private context: vscode.ExtensionContext;
    private disposables: vscode.Disposable[] = [];
    
    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.setupConfigurationWatcher();
    }
    
    getConfig(): PromptStoreConfig {
        const config = vscode.workspace.getConfiguration('wu-wei.promptStore');
        
        return {
            rootDirectory: this.resolveRootDirectory(config.get('rootDirectory', '')),
            autoRefresh: config.get('autoRefresh', true),
            showMetadataTooltips: config.get('showMetadataTooltips', true),
            enableTemplates: config.get('enableTemplates', true),
            metadataSchema: this.getMetadataSchemaConfig(config),
            fileWatcher: this.getFileWatcherConfig(config)
        };
    }
    
    private setupConfigurationWatcher(): void {
        const disposable = vscode.workspace.onDidChangeConfiguration((event) => {
            if (event.affectsConfiguration('wu-wei.promptStore')) {
                this.onConfigurationChanged();
            }
        });
        
        this.disposables.push(disposable);
    }
}
```

### 5.5.3 Directory Selection
```typescript
async selectDirectory(): Promise<string | undefined> {
    const result = await vscode.window.showOpenDialog({
        canSelectFiles: false,
        canSelectFolders: true,
        canSelectMany: false,
        title: 'Select Prompt Store Directory',
        openLabel: 'Select Directory'
    });
    
    if (result && result[0]) {
        const selectedPath = result[0].fsPath;
        
        // Validate directory
        const validation = await this.validateDirectory(selectedPath);
        if (!validation.isValid) {
            vscode.window.showErrorMessage(
                `Invalid directory: ${validation.errors.join(', ')}`
            );
            return undefined;
        }
        
        return selectedPath;
    }
    
    return undefined;
}

private async validateDirectory(dirPath: string): Promise<ValidationResult> {
    const errors: string[] = [];
    
    try {
        const stats = await fs.stat(dirPath);
        
        if (!stats.isDirectory()) {
            errors.push('Path is not a directory');
        }
        
        // Test read permissions
        await fs.access(dirPath, fs.constants.R_OK);
        
        // Test write permissions
        await fs.access(dirPath, fs.constants.W_OK);
        
    } catch (error) {
        if (error.code === 'ENOENT') {
            errors.push('Directory does not exist');
        } else if (error.code === 'EACCES') {
            errors.push('Insufficient permissions');
        } else {
            errors.push(`Access error: ${error.message}`);
        }
    }
    
    return {
        isValid: errors.length === 0,
        errors
    };
}
```

### 5.5.4 Session State Management
```typescript
interface SessionState {
    lastRootDirectory?: string;
    expandedFolders: string[];
    searchFilters: SearchFilters;
    sortPreferences: SortPreferences;
    uiState: UIState;
}

class SessionStateManager {
    private readonly STATE_KEY = 'promptStoreState';
    
    getState(): SessionState {
        return this.context.workspaceState.get(this.STATE_KEY, {
            expandedFolders: [],
            searchFilters: {},
            sortPreferences: { field: 'name', direction: 'asc' },
            uiState: {}
        });
    }
    
    async updateState(updates: Partial<SessionState>): Promise<void> {
        const currentState = this.getState();
        const newState = { ...currentState, ...updates };
        await this.context.workspaceState.update(this.STATE_KEY, newState);
    }
}
```

## Configuration Commands

### 5.6 Command Implementation
```typescript
// Register configuration commands
const selectDirectoryCommand = vscode.commands.registerCommand(
    'wu-wei.promptStore.selectDirectory',
    async () => {
        const directory = await this.configManager.selectDirectory();
        if (directory) {
            await this.configManager.setRootDirectory(directory);
            vscode.window.showInformationMessage(
                `Prompt store directory set to: ${directory}`
            );
        }
    }
);

const resetConfigCommand = vscode.commands.registerCommand(
    'wu-wei.promptStore.resetConfig',
    async () => {
        const confirm = await vscode.window.showWarningMessage(
            'Reset prompt store configuration to defaults?',
            'Reset', 'Cancel'
        );
        
        if (confirm === 'Reset') {
            await this.configManager.resetToDefaults();
            vscode.window.showInformationMessage('Configuration reset to defaults');
        }
    }
);
```

## Error Handling

### 5.7 Configuration Errors
Handle common configuration issues:
- Invalid directory paths
- Permission denied errors
- Network drive connectivity
- Configuration corruption
- Migration failures

### 5.8 User-Friendly Messages
```typescript
private getConfigErrorMessage(error: ConfigError): string {
    switch (error.type) {
        case 'DIRECTORY_NOT_FOUND':
            return 'The selected directory no longer exists. Please choose a new directory.';
        case 'PERMISSION_DENIED':
            return 'Cannot access the directory. Please check permissions or select a different directory.';
        case 'NETWORK_ERROR':
            return 'Network drive is not accessible. Please ensure the drive is connected.';
        default:
            return `Configuration error: ${error.message}`;
    }
}
```

## Testing Requirements

### 5.9 Unit Tests
Test scenarios for:
- Configuration loading and validation
- Directory selection and validation
- Session state persistence
- Configuration change handling
- Error scenarios and recovery

### 5.10 Integration Tests
- Settings contribution integration
- Command registration and execution
- Workspace state persistence
- Configuration migration
- Cross-platform directory handling

## Acceptance Criteria
- [ ] VS Code settings are properly registered and functional
- [ ] Directory selection workflow works on all platforms
- [ ] Configuration persists across VS Code sessions
- [ ] Invalid configurations are handled gracefully
- [ ] Configuration changes trigger appropriate updates
- [ ] Commands are registered and accessible
- [ ] Session state is maintained properly
- [ ] All unit and integration tests pass
- [ ] User receives clear feedback for configuration issues

## Dependencies
- **Steps 1-4**: Core infrastructure must be completed
- VS Code Extension API for settings and commands
- Node.js file system operations
- Proper error handling patterns

## Estimated Effort
**3-4 hours**

## Files to Implement
1. `src/promptStore/ConfigurationManager.ts` (main implementation)
2. `src/promptStore/SessionStateManager.ts` (session persistence)
3. `package.json` (settings contributions and commands)
4. `test/promptStore/ConfigurationManager.test.ts` (unit tests)
5. `test/promptStore/integration/configuration.test.ts` (integration tests)

## Next Step
Proceed to **Step 6: Basic Webview UI** to create the user interface foundation.
