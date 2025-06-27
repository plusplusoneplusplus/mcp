# Phase 2: PromptManager Refactoring

## Overview

Refactor the existing `PromptManager` to implement the shared `PromptService` interface while maintaining full backward compatibility. This phase bridges the gap between the current implementation and the new shared service architecture.

## Objectives

1. Refactor `PromptManager` to implement `PromptService` interface
2. Maintain 100% backward compatibility with existing functionality
3. Create adapter patterns for seamless migration
4. Establish integration tests to validate compatibility
5. Prepare for prompt store migration in Phase 3

## Current State Analysis

### Existing PromptManager Capabilities
- File system watching and prompt loading
- Metadata parsing and validation
- Search and filtering functionality
- Configuration management
- Event system for prompt changes

### Integration Points
- `PromptStoreProvider` uses `PromptManager` directly
- Configuration system through VS Code settings
- File watcher integration
- Metadata parser and validation

## Technical Specification

### 1. Refactoring Strategy

#### Adapter Pattern Implementation
```typescript
// Legacy support wrapper
export class PromptManagerServiceAdapter implements PromptService {
  private promptManager: PromptManager
  private sharedEventEmitter: vscode.EventEmitter<any>

  constructor(promptManager: PromptManager) {
    this.promptManager = promptManager
    this.setupEventBridge()
  }

  // Bridge existing events to new interface
  private setupEventBridge(): void {
    this.promptManager.onPromptsChanged((prompts) => {
      this.sharedEventEmitter.fire('promptsChanged', prompts)
    })
  }

  // Implement PromptService interface by delegating to PromptManager
  async getAllPrompts(): Promise<Prompt[]> {
    return this.promptManager.getAllPrompts()
  }

  async getPrompt(id: string): Promise<Prompt | null> {
    return this.promptManager.getPrompt(id) || null
  }

  // New methods with enhanced functionality
  async selectPromptForUse(promptId: string): Promise<PromptUsageContext> {
    const prompt = await this.getPrompt(promptId)
    if (!prompt) {
      throw new Error(`Prompt not found: ${promptId}`)
    }

    return this.createUsageContext(prompt)
  }
}
```

#### Enhanced PromptManager
```typescript
export class PromptManager implements PromptService {
  // Existing private members...
  private variableResolver: VariableResolver
  private promptRenderer: PromptRenderer
  private sharedEventEmitter: vscode.EventEmitter<any>

  // Enhanced constructor
  constructor(config?: Partial<PromptStoreConfig>) {
    // Existing initialization...
    this.variableResolver = new VariableResolver()
    this.promptRenderer = new PromptRenderer(this.variableResolver)
    this.setupSharedEventSystem()
  }

  // Existing methods remain unchanged...

  // New PromptService interface methods
  async selectPromptForUse(promptId: string): Promise<PromptUsageContext> {
    const prompt = this.getPrompt(promptId)
    if (!prompt) {
      throw new Error(`Prompt not found: ${promptId}`)
    }

    const parameters = this.extractPromptParameters(prompt)
    const usageContext: PromptUsageContext = {
      prompt,
      renderedContent: prompt.content,
      variables: {},
      metadata: {
        ...prompt.metadata,
        parameters,
        usageInstructions: this.generateUsageInstructions(parameters)
      }
    }

    this.sharedEventEmitter.fire('promptSelected', usageContext)
    return usageContext
  }

  async renderPromptWithVariables(
    promptId: string,
    variables: Record<string, any>
  ): Promise<string> {
    const prompt = this.getPrompt(promptId)
    if (!prompt) {
      throw new Error(`Prompt not found: ${promptId}`)
    }

    const parameters = this.extractPromptParameters(prompt)
    const validationErrors = this.variableResolver.validateVariables(
      prompt.content,
      variables,
      parameters
    )

    if (validationErrors.some(e => e.severity === 'error')) {
      throw new Error(`Variable validation failed: ${validationErrors.map(e => e.message).join(', ')}`)
    }

    return this.promptRenderer.render(prompt.content, variables, {
      defaultValues: this.getDefaultVariableValues(parameters)
    })
  }

  // Enhanced event system
  get onPromptsChanged(): vscode.Event<Prompt[]> {
    return this.sharedEventEmitter.event('promptsChanged')
  }

  get onPromptSelected(): vscode.Event<PromptUsageContext> {
    return this.sharedEventEmitter.event('promptSelected')
  }

  get onConfigChanged(): vscode.Event<PromptStoreConfig> {
    return this.sharedEventEmitter.event('configChanged')
  }
}
```

### 2. Parameter Extraction Enhancement

#### Metadata-Based Parameters
```typescript
private extractPromptParameters(prompt: Prompt): PromptParameter[] {
  const parameters: PromptParameter[] = []

  // Extract from metadata if defined
  if (prompt.metadata.parameters) {
    return prompt.metadata.parameters as PromptParameter[]
  }

  // Auto-extract from content
  const variables = this.variableResolver.extractVariables(prompt.content)
  
  for (const variable of variables) {
    parameters.push({
      name: variable,
      type: 'string',
      required: true,
      description: `Parameter for ${variable}`,
      placeholder: `Enter value for ${variable}...`
    })
  }

  return parameters
}

private generateUsageInstructions(parameters: PromptParameter[]): string {
  if (parameters.length === 0) {
    return 'This prompt has no variables and can be used directly.'
  }

  const required = parameters.filter(p => p.required)
  const optional = parameters.filter(p => !p.required)

  let instructions = 'This prompt requires the following variables:\n\n'
  
  if (required.length > 0) {
    instructions += 'Required:\n'
    required.forEach(p => {
      instructions += `- ${p.name}: ${p.description || 'No description'}\n`
    })
  }

  if (optional.length > 0) {
    instructions += '\nOptional:\n'
    optional.forEach(p => {
      instructions += `- ${p.name}: ${p.description || 'No description'}\n`
    })
  }

  return instructions
}
```

### 3. Backward Compatibility Layer

#### Legacy Method Preservation
```typescript
export class PromptManager implements PromptService {
  // Existing public methods maintained exactly as-is
  public getAllPrompts(): Prompt[] {
    // Existing implementation unchanged
  }

  public getPrompt(id: string): Prompt | undefined {
    // Existing implementation unchanged
  }

  public async refreshPrompts(): Promise<void> {
    // Existing implementation unchanged
  }

  // New async versions for PromptService compliance
  async getAllPromptsAsync(): Promise<Prompt[]> {
    return Promise.resolve(this.getAllPrompts())
  }

  async getPromptAsync(id: string): Promise<Prompt | null> {
    return Promise.resolve(this.getPrompt(id) || null)
  }

  // Alias methods for seamless transition
  getAllPrompts(): Promise<Prompt[]> {
    return this.getAllPromptsAsync()
  }

  getPrompt(id: string): Promise<Prompt | null> {
    return this.getPromptAsync(id)
  }
}
```

### 4. Migration Utilities

#### Configuration Bridge
```typescript
export class ConfigurationBridge {
  static migrateConfig(
    oldConfig: any, 
    newInterface: PromptService
  ): PromptStoreConfig {
    // Handle any configuration format changes
    return {
      ...oldConfig,
      // Add any new required fields with defaults
      variableResolution: {
        strictMode: false,
        allowUndefined: true
      }
    }
  }

  static validateMigration(
    oldManager: PromptManager,
    newService: PromptService
  ): ValidationResult {
    // Compare functionality to ensure no regressions
    const errors: ValidationError[] = []
    const warnings: ValidationWarning[] = []

    // Validate prompt count matches
    const oldPrompts = oldManager.getAllPrompts()
    const newPrompts = await newService.getAllPrompts()

    if (oldPrompts.length !== newPrompts.length) {
      errors.push({
        field: 'promptCount',
        message: `Prompt count mismatch: ${oldPrompts.length} vs ${newPrompts.length}`,
        severity: 'error'
      })
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    }
  }
}
```

## Implementation Tasks

### Week 1: Analysis and Planning

#### Day 1: Current State Analysis
- [ ] Map all existing PromptManager public methods
- [ ] Identify all integration points with PromptStoreProvider
- [ ] Document current event system and dependencies
- [ ] Create compatibility test suite baseline

#### Day 2: Interface Implementation Plan
- [ ] Design adapter pattern for seamless transition
- [ ] Plan method signature migrations (sync to async)
- [ ] Design event system bridge
- [ ] Create migration validation strategy

#### Day 3: Parameter Extraction Design
- [ ] Design metadata-based parameter extraction
- [ ] Plan auto-detection for existing prompts
- [ ] Design usage instruction generation
- [ ] Create validation framework for parameters

#### Day 4-5: Implementation Setup
- [ ] Create branch for refactoring work
- [ ] Set up migration test framework
- [ ] Create backwards compatibility validation
- [ ] Implement configuration bridge utilities

### Week 2: Implementation and Testing

#### Day 1-2: Core Interface Implementation
- [ ] Implement PromptService interface in PromptManager
- [ ] Add async method variants
- [ ] Implement parameter extraction logic
- [ ] Create usage context generation

#### Day 3: Event System Bridge
- [ ] Implement shared event emitter
- [ ] Bridge existing events to new interface
- [ ] Maintain existing event signatures
- [ ] Test event propagation

#### Day 4: Variable Resolution Integration
- [ ] Integrate VariableResolver into PromptManager
- [ ] Implement renderPromptWithVariables method
- [ ] Add validation for variable resolution
- [ ] Test with existing prompt content

#### Day 5: Testing and Validation
- [ ] Run full regression test suite
- [ ] Validate all existing functionality works
- [ ] Performance testing with large prompt collections
- [ ] Memory leak testing

## Testing Strategy

### Regression Testing
```typescript
describe('PromptManager Backward Compatibility', () => {
  test('existing getAllPrompts method works unchanged', () => {
    // Validate exact same behavior as before
  })

  test('existing event system continues to work', () => {
    // Ensure PromptStoreProvider still receives events
  })

  test('configuration loading remains compatible', () => {
    // Verify settings still load correctly
  })
})

describe('New PromptService Features', () => {
  test('selectPromptForUse creates valid usage context', () => {
    // Test new functionality
  })

  test('variable resolution works with existing prompts', () => {
    // Test enhanced capabilities
  })
})
```

### Integration Testing
- Test with actual PromptStoreProvider
- Validate file watcher continues to work
- Test configuration changes propagate correctly
- Verify memory usage remains stable

### Performance Testing
- Benchmark prompt loading times
- Test variable resolution performance
- Validate large collection handling
- Memory usage profiling

## Quality Gates

### Backward Compatibility
- [ ] All existing PromptStoreProvider functionality works
- [ ] No breaking changes to public API
- [ ] Event system maintains existing behavior
- [ ] Configuration loading unchanged

### New Functionality
- [ ] PromptService interface fully implemented
- [ ] Parameter extraction works for all prompt types
- [ ] Variable resolution handles edge cases
- [ ] Usage context generation is accurate

### Performance
- [ ] No regression in prompt loading speed
- [ ] Variable resolution adds <5ms overhead
- [ ] Memory usage increase <5MB
- [ ] Large collection performance maintained

## Migration Validation

### Automated Checks
```typescript
class MigrationValidator {
  async validateMigration(): Promise<ValidationResult> {
    const results: ValidationResult = {
      isValid: true,
      errors: [],
      warnings: []
    }

    // Test prompt loading
    await this.validatePromptLoading(results)
    
    // Test search functionality
    await this.validateSearchCapabilities(results)
    
    // Test configuration
    await this.validateConfiguration(results)
    
    // Test event system
    await this.validateEventSystem(results)

    return results
  }

  private async validatePromptLoading(results: ValidationResult): Promise<void> {
    // Compare old vs new prompt loading
    const oldPrompts = this.oldManager.getAllPrompts()
    const newPrompts = await this.newManager.getAllPrompts()

    if (oldPrompts.length !== newPrompts.length) {
      results.errors.push({
        field: 'promptLoading',
        message: 'Prompt count changed after migration',
        severity: 'error'
      })
    }

    // Validate each prompt matches
    for (let i = 0; i < oldPrompts.length; i++) {
      const oldPrompt = oldPrompts[i]
      const newPrompt = newPrompts.find(p => p.id === oldPrompt.id)
      
      if (!newPrompt) {
        results.errors.push({
          field: 'promptLoading',
          message: `Prompt ${oldPrompt.id} missing after migration`,
          severity: 'error'
        })
      }
    }
  }
}
```

## Risk Mitigation

### Technical Risks
1. **Breaking Changes**: Comprehensive test suite validates all existing functionality
2. **Performance Regression**: Benchmark testing with rollback capability
3. **Event System Issues**: Careful bridge implementation with fallback

### Integration Risks
1. **PromptStoreProvider Compatibility**: Direct testing with existing UI
2. **Configuration Migration**: Gradual migration with validation
3. **Memory Leaks**: Proper disposal patterns for new event system

## Deliverables

1. **Refactored PromptManager**
   - Full PromptService interface implementation
   - 100% backward compatibility maintained
   - Enhanced parameter extraction capabilities

2. **Migration Utilities**
   - Configuration bridge for seamless transition
   - Validation framework for migration success
   - Rollback capability for issues

3. **Test Suite**
   - Comprehensive regression tests
   - New functionality tests
   - Performance benchmarks
   - Integration validation

4. **Documentation**
   - Migration guide for Phase 3
   - API changes documentation
   - Troubleshooting guide

## Success Criteria

- [ ] All existing PromptStoreProvider functionality unchanged
- [ ] PromptService interface fully implemented and tested
- [ ] Zero performance regression in existing workflows
- [ ] Migration validation passes all checks
- [ ] Ready for Phase 3 prompt store migration

## Next Phase Preparation

This phase prepares for Phase 3 by:
- Providing validated PromptService implementation
- Creating migration utilities and validation framework
- Establishing test patterns for UI component updates
- Documenting integration requirements for prompt store UI 