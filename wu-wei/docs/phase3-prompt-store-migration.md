# Phase 3: Prompt Store Migration

## Overview

Update the `PromptStoreProvider` to use the shared `PromptService` interface while ensuring all existing functionality remains unchanged. This phase completes the backend migration and prepares the foundation for agent panel integration.

## Objectives

1. Migrate `PromptStoreProvider` to use `PromptService` interface
2. Maintain 100% user-facing functionality and UI behavior
3. Optimize performance through shared service benefits
4. Validate seamless operation with existing configurations
5. Prepare foundation for Phase 4 agent panel enhancements

## Current State Analysis

### PromptStoreProvider Dependencies
- Direct instantiation and usage of `PromptManager`
- Configuration management through VS Code settings
- Webview message handling for prompt operations
- File operation management integration
- Event handling for prompt changes

### UI Components Affected
- Prompt list rendering and organization
- Search and filter functionality
- File operations (create, delete, rename)
- Configuration management interface
- Real-time updates and refresh

## Technical Specification

### 1. Service Integration Strategy

#### Dependency Injection Pattern
```typescript
export class PromptStoreProvider implements vscode.WebviewViewProvider {
  private promptService: PromptService
  private fileOperationManager: FileOperationManager
  private webview?: vscode.Webview
  private _view?: vscode.WebviewView

  constructor(
    private readonly extensionUri: vscode.Uri,
    context: vscode.ExtensionContext
  ) {
    // Use shared service factory instead of direct PromptManager instantiation
    this.promptService = PromptServiceFactory.createService(context)
    this.fileOperationManager = new FileOperationManager(
      new ConfigurationManager(), 
      this.promptService // Pass service instead of manager
    )

    // Set up event listeners for the shared service
    this.setupServiceEventHandlers()
  }

  private setupServiceEventHandlers(): void {
    // Replace direct PromptManager event handlers
    this.promptService.onPromptsChanged(this.handlePromptsChanged.bind(this))
    this.promptService.onConfigChanged(this.handleConfigChanged.bind(this))
    
    // New event for prompt selection (future agent panel integration)
    this.promptService.onPromptSelected(this.handlePromptSelected.bind(this))
  }

  private async handlePromptsChanged(prompts: Prompt[]): Promise<void> {
    // Existing behavior maintained
    this.sendPromptsToWebview(prompts)
  }

  private async handlePromptSelected(context: PromptUsageContext): Promise<void> {
    // New handler for future agent integration
    // For now, just log or provide feedback
    console.log(`Prompt selected for use: ${context.prompt.metadata.title}`)
  }
}
```

#### Async Method Migration
```typescript
export class PromptStoreProvider {
  // Update all synchronous operations to async
  private async loadAndDisplayPrompts(): Promise<void> {
    try {
      this.showLoading()
      const prompts = await this.promptService.getAllPrompts()
      this.sendPromptsToWebview(prompts)
    } catch (error) {
      this.handleError('Failed to load prompts', error)
    } finally {
      this.hideLoading()
    }
  }

  private async handleSearchPrompts(query: string, filters?: SearchFilter): Promise<void> {
    try {
      const results = await this.promptService.searchPrompts(query, filters)
      this.sendPromptsToWebview(results)
    } catch (error) {
      this.handleError('Search failed', error)
    }
  }

  private async handleSelectPrompt(promptId: string): Promise<void> {
    try {
      const usageContext = await this.promptService.selectPromptForUse(promptId)
      
      // Send usage context to webview for display
      this.sendPromptUsageContext(usageContext)
      
      // Future: Could trigger agent panel integration here
    } catch (error) {
      this.handleError('Failed to select prompt', error)
    }
  }
}
```

### 2. FileOperationManager Integration

#### Service-Based File Operations
```typescript
export class FileOperationManager {
  private promptService: PromptService
  private configManager: ConfigurationManager

  constructor(configManager: ConfigurationManager, promptService: PromptService) {
    this.configManager = configManager
    this.promptService = promptService
  }

  async createNewPrompt(options: NewPromptOptions): Promise<FileOperationResult> {
    try {
      // Create the prompt file
      const result = await this.createPromptFile(options)
      
      if (result.success) {
        // Refresh the service to pick up the new prompt
        await this.promptService.refreshPrompts()
        
        // Get the created prompt for additional processing
        const prompts = await this.promptService.getAllPrompts()
        const newPrompt = prompts.find(p => p.filePath === result.filePath)
        
        if (newPrompt) {
          // Generate usage context for immediate use
          const usageContext = await this.promptService.selectPromptForUse(newPrompt.id)
          return {
            ...result,
            usageContext
          }
        }
      }

      return result
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
      }
    }
  }

  async deletePrompt(promptId: string): Promise<FileOperationResult> {
    try {
      const prompt = await this.promptService.getPrompt(promptId)
      if (!prompt) {
        return {
          success: false,
          error: 'Prompt not found'
        }
      }

      // Delete the file
      await this.deletePromptFile(prompt.filePath)
      
      // Refresh the service
      await this.promptService.refreshPrompts()

      return {
        success: true,
        filePath: prompt.filePath
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
      }
    }
  }
}
```

### 3. Enhanced Webview Communication

#### New Message Types for Enhanced Functionality
```typescript
interface EnhancedWebviewMessage extends WebviewMessage {
  type: 'webviewReady' | 'configureDirectory' | 'openPrompt' | 'createNewPrompt' | 
        'refreshStore' | 'getPrompts' | 'searchPrompts' | 'selectPrompt' | 
        'refreshPrompts' | 'updateConfig' | 'deletePrompt' | 'renamePrompt' | 
        'duplicatePrompt' | 'selectPromptForUse' | 'renderPromptWithVariables'
  payload?: any
  promptId?: string
  variables?: Record<string, any>
}

interface EnhancedWebviewResponse extends WebviewResponse {
  type: 'updatePrompts' | 'updateConfig' | 'showLoading' | 'hideLoading' | 
        'showError' | 'promptsLoaded' | 'promptSelected' | 'error' | 
        'configUpdated' | 'promptUsageContext' | 'promptRendered'
  payload?: any
  prompts?: Prompt[]
  config?: PromptStoreConfig
  error?: string
  usageContext?: PromptUsageContext
  renderedContent?: string
}
```

#### Message Handling Updates
```typescript
async onDidReceiveMessage(message: EnhancedWebviewMessage): Promise<void> {
  switch (message.type) {
    case 'selectPromptForUse':
      await this.handleSelectPromptForUse(message.promptId!)
      break

    case 'renderPromptWithVariables':
      await this.handleRenderPrompt(message.promptId!, message.variables!)
      break

    case 'searchPrompts':
      await this.handleSearchPrompts(message.payload.query, message.payload.filters)
      break

    case 'getPrompts':
      await this.loadAndDisplayPrompts()
      break

    // Existing handlers remain unchanged...
    case 'openPrompt':
      await this.handleOpenPrompt(message.path!)
      break

    case 'createNewPrompt':
      await this.createNewPrompt()
      break

    default:
      console.warn('Unknown message type:', message.type)
  }
}

private async handleSelectPromptForUse(promptId: string): Promise<void> {
  try {
    const usageContext = await this.promptService.selectPromptForUse(promptId)
    
    this.sendToWebview({
      type: 'promptUsageContext',
      usageContext
    })
  } catch (error) {
    this.handleError('Failed to select prompt for use', error)
  }
}

private async handleRenderPrompt(promptId: string, variables: Record<string, any>): Promise<void> {
  try {
    const renderedContent = await this.promptService.renderPromptWithVariables(promptId, variables)
    
    this.sendToWebview({
      type: 'promptRendered',
      renderedContent
    })
  } catch (error) {
    this.handleError('Failed to render prompt', error)
  }
}
```

### 4. Performance Optimizations

#### Lazy Loading and Caching
```typescript
export class PromptStoreProvider {
  private promptCache: Map<string, Prompt> = new Map()
  private lastRefreshTime: number = 0
  private readonly CACHE_DURATION = 30000 // 30 seconds

  private async getPromptsWithCache(): Promise<Prompt[]> {
    const now = Date.now()
    
    // Use cache if recent
    if (now - this.lastRefreshTime < this.CACHE_DURATION && this.promptCache.size > 0) {
      return Array.from(this.promptCache.values())
    }

    // Refresh from service
    const prompts = await this.promptService.getAllPrompts()
    
    // Update cache
    this.promptCache.clear()
    prompts.forEach(prompt => this.promptCache.set(prompt.id, prompt))
    this.lastRefreshTime = now

    return prompts
  }

  private async invalidateCache(): Promise<void> {
    this.promptCache.clear()
    this.lastRefreshTime = 0
    await this.loadAndDisplayPrompts()
  }
}
```

## Implementation Tasks

### Week 1: Analysis and Setup

#### Day 1: Integration Point Analysis
- [ ] Map all PromptManager usage in PromptStoreProvider
- [ ] Identify async/sync conversion requirements
- [ ] Document webview message flow changes
- [ ] Create migration checklist

#### Day 2: Service Integration Design
- [ ] Design dependency injection pattern
- [ ] Plan async method migration strategy
- [ ] Design enhanced webview communication
- [ ] Create testing strategy for UI validation

#### Day 3: FileOperationManager Updates
- [ ] Refactor to use PromptService interface
- [ ] Update file operation workflows
- [ ] Add usage context generation
- [ ] Test file operations with new service

#### Day 4-5: Implementation Setup
- [ ] Create feature branch
- [ ] Set up UI testing framework
- [ ] Create webview message validation
- [ ] Implement service integration foundation

### Week 2: Implementation and Testing

#### Day 1-2: Core Provider Migration
- [ ] Replace PromptManager with PromptService
- [ ] Update constructor and initialization
- [ ] Migrate all prompt operations to async
- [ ] Update event handling system

#### Day 3: Webview Communication Enhancement
- [ ] Implement enhanced message types
- [ ] Add new message handlers
- [ ] Update webview JavaScript integration
- [ ] Test bidirectional communication

#### Day 4: Performance Optimization
- [ ] Implement caching strategies
- [ ] Add progressive loading for large collections
- [ ] Optimize refresh operations
- [ ] Performance testing and tuning

#### Day 5: Integration Testing
- [ ] Full UI testing with real data
- [ ] Cross-browser webview testing
- [ ] Configuration migration testing
- [ ] Performance validation

## Quality Gates

### Functional Requirements
- [ ] All existing prompt store features work unchanged
- [ ] UI responsiveness matches or exceeds current performance
- [ ] Search and filtering functionality preserved
- [ ] File operations work with new service architecture
- [ ] Configuration management remains seamless

### Performance Requirements
- [ ] Initial load time <2 seconds for 100 prompts
- [ ] Search results appear <500ms
- [ ] Cache improves repeat operations by >50%
- [ ] Memory usage increase <10MB
- [ ] No memory leaks in long-running sessions

### Integration Requirements
- [ ] Webview communication protocol works reliably
- [ ] Event propagation maintains existing behavior
- [ ] Error handling provides clear user feedback
- [ ] Configuration changes apply immediately
- [ ] File watcher integration continues to work

## Success Criteria

- [ ] All existing prompt store functionality works unchanged
- [ ] Performance meets or exceeds current benchmarks
- [ ] UI responsiveness improved for large collections
- [ ] New prompt selection capabilities available
- [ ] Zero user-facing breaking changes
- [ ] Foundation ready for Phase 4 agent panel integration

## Next Phase Preparation

This phase prepares for Phase 4 by:
- Providing stable shared service foundation
- Establishing enhanced webview communication patterns
- Creating usage context generation capabilities
- Validating performance with real-world data
- Setting up integration points for agent panel enhancement 