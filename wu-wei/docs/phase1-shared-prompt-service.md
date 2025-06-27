# Phase 1: Shared Prompt Service Foundation

## Overview

Create the foundational shared prompt management infrastructure that will serve both the prompt store and agent panel. This phase establishes the core abstractions and service contracts without modifying existing functionality.

## Objectives

1. Design and implement a clean `PromptService` interface
2. Create shared types and utilities for prompt operations
3. Establish service factory pattern for dependency injection
4. Build comprehensive unit tests for core functionality
5. Prepare foundation for seamless integration in subsequent phases

## Technical Specification

### 1. Directory Structure

```
src/shared/
├── promptManager/
│   ├── index.ts                 # Main exports
│   ├── PromptService.ts         # Core service interface
│   ├── VsCodePromptService.ts   # VS Code implementation
│   ├── PromptServiceFactory.ts  # Dependency injection factory
│   ├── types.ts                 # Shared types and interfaces
│   ├── utils/
│   │   ├── variableResolver.ts  # Variable substitution logic
│   │   ├── promptRenderer.ts    # Prompt rendering utilities
│   │   └── validators.ts        # Prompt validation utilities
│   └── tests/
│       ├── PromptService.test.ts
│       ├── variableResolver.test.ts
│       └── promptRenderer.test.ts
```

### 2. Core Interfaces

#### PromptService Interface
```typescript
export interface PromptService {
  // Core Operations
  getAllPrompts(): Promise<Prompt[]>
  getPrompt(id: string): Promise<Prompt | null>
  searchPrompts(query: string, filters?: SearchFilter): Promise<Prompt[]>
  
  // Prompt Usage
  selectPromptForUse(promptId: string): Promise<PromptUsageContext>
  renderPromptWithVariables(
    promptId: string, 
    variables: Record<string, any>
  ): Promise<string>
  
  // Configuration
  getConfig(): Promise<PromptStoreConfig>
  updateConfig(config: Partial<PromptStoreConfig>): Promise<void>
  
  // Events
  onPromptsChanged: Event<Prompt[]>
  onPromptSelected: Event<PromptUsageContext>
  onConfigChanged: Event<PromptStoreConfig>
  
  // Lifecycle
  initialize(): Promise<void>
  dispose(): void
}
```

#### Enhanced Types
```typescript
export interface PromptUsageContext {
  prompt: Prompt
  renderedContent: string
  variables: Record<string, any>
  metadata: PromptMetadata & {
    parameters?: PromptParameter[]
    usageInstructions?: string
    category?: string
    tags?: string[]
  }
  renderingErrors?: ValidationError[]
}

export interface PromptParameter {
  name: string
  type: 'string' | 'number' | 'boolean' | 'select' | 'multiline' | 'file'
  description?: string
  required?: boolean
  defaultValue?: any
  options?: string[] // for select type
  placeholder?: string
  validation?: {
    pattern?: string
    minLength?: number
    maxLength?: number
    min?: number
    max?: number
  }
}

export interface VariableResolutionOptions {
  strictMode?: boolean
  allowUndefined?: boolean
  defaultValues?: Record<string, any>
  resolver?: (variable: string) => any
}
```

### 3. Implementation Details

#### VsCodePromptService
```typescript
export class VsCodePromptService implements PromptService {
  private context: vscode.ExtensionContext
  private promptManager: PromptManager // Existing implementation
  private eventEmitter: vscode.EventEmitter<any>
  private variableResolver: VariableResolver
  private promptRenderer: PromptRenderer

  constructor(context: vscode.ExtensionContext) {
    this.context = context
    this.setupPromptManager()
    this.setupEventHandlers()
  }

  async getAllPrompts(): Promise<Prompt[]> {
    return this.promptManager.getAllPrompts()
  }

  async selectPromptForUse(promptId: string): Promise<PromptUsageContext> {
    const prompt = await this.getPrompt(promptId)
    if (!prompt) {
      throw new Error(`Prompt not found: ${promptId}`)
    }

    const parameters = this.extractParameters(prompt)
    const usageContext: PromptUsageContext = {
      prompt,
      renderedContent: prompt.content,
      variables: {},
      metadata: {
        ...prompt.metadata,
        parameters
      }
    }

    this.eventEmitter.fire('promptSelected', usageContext)
    return usageContext
  }

  async renderPromptWithVariables(
    promptId: string,
    variables: Record<string, any>
  ): Promise<string> {
    const prompt = await this.getPrompt(promptId)
    if (!prompt) {
      throw new Error(`Prompt not found: ${promptId}`)
    }

    return this.promptRenderer.render(prompt.content, variables)
  }
}
```

#### Variable Resolver
```typescript
export class VariableResolver {
  static readonly VARIABLE_PATTERN = /\{\{(\w+)\}\}/g

  resolve(
    content: string, 
    variables: Record<string, any>,
    options: VariableResolutionOptions = {}
  ): string {
    const { strictMode = false, allowUndefined = false, defaultValues = {} } = options

    return content.replace(this.VARIABLE_PATTERN, (match, variableName) => {
      if (variables.hasOwnProperty(variableName)) {
        return String(variables[variableName])
      }

      if (defaultValues.hasOwnProperty(variableName)) {
        return String(defaultValues[variableName])
      }

      if (options.resolver) {
        const resolved = options.resolver(variableName)
        if (resolved !== undefined) {
          return String(resolved)
        }
      }

      if (strictMode) {
        throw new Error(`Undefined variable: ${variableName}`)
      }

      return allowUndefined ? match : ''
    })
  }

  extractVariables(content: string): string[] {
    const variables: string[] = []
    const matches = content.matchAll(this.VARIABLE_PATTERN)
    
    for (const match of matches) {
      if (!variables.includes(match[1])) {
        variables.push(match[1])
      }
    }

    return variables
  }

  validateVariables(
    content: string,
    variables: Record<string, any>,
    parameters: PromptParameter[]
  ): ValidationError[] {
    const errors: ValidationError[] = []
    const requiredVars = parameters.filter(p => p.required).map(p => p.name)
    const extractedVars = this.extractVariables(content)

    // Check for missing required variables
    for (const required of requiredVars) {
      if (!variables.hasOwnProperty(required)) {
        errors.push({
          field: required,
          message: `Required variable '${required}' is missing`,
          severity: 'error'
        })
      }
    }

    // Check for unused variables
    for (const provided of Object.keys(variables)) {
      if (!extractedVars.includes(provided)) {
        errors.push({
          field: provided,
          message: `Variable '${provided}' is not used in the prompt`,
          severity: 'warning'
        })
      }
    }

    return errors
  }
}
```

### 4. Service Factory

```typescript
export class PromptServiceFactory {
  private static instance: PromptService | null = null

  static createService(context: vscode.ExtensionContext): PromptService {
    if (!this.instance) {
      this.instance = new VsCodePromptService(context)
    }
    return this.instance
  }

  static getInstance(): PromptService | null {
    return this.instance
  }

  static dispose(): void {
    if (this.instance) {
      this.instance.dispose()
      this.instance = null
    }
  }
}
```

## Implementation Tasks

### Week 1: Core Infrastructure

#### Day 1-2: Project Setup
- [ ] Create shared directory structure
- [ ] Set up TypeScript configuration
- [ ] Define core interfaces in types.ts
- [ ] Create basic PromptService interface

#### Day 3-4: Variable Resolution
- [ ] Implement VariableResolver class
- [ ] Add pattern matching for {{variable}} syntax
- [ ] Support for default values and strict mode
- [ ] Comprehensive unit tests for variable resolution

#### Day 5: Prompt Rendering
- [ ] Implement PromptRenderer class
- [ ] Integration with VariableResolver
- [ ] Error handling for rendering failures
- [ ] Unit tests for rendering logic

### Week 2: Service Implementation

#### Day 1-2: VsCodePromptService
- [ ] Implement core PromptService methods
- [ ] Integration with existing PromptManager
- [ ] Event system setup
- [ ] Parameter extraction from prompt metadata

#### Day 3-4: Service Factory
- [ ] Implement PromptServiceFactory
- [ ] Singleton pattern with proper disposal
- [ ] Context management
- [ ] Integration tests

#### Day 5: Testing & Documentation
- [ ] Complete test suite (>90% coverage)
- [ ] API documentation
- [ ] Usage examples
- [ ] Performance benchmarking

## Testing Strategy

### Unit Tests
- Variable resolution with various patterns
- Prompt rendering with complex variables
- Parameter extraction and validation
- Error handling for edge cases

### Integration Tests
- Service factory initialization
- Event propagation
- Configuration management
- Memory leak prevention

### Performance Tests
- Variable resolution latency (<10ms for typical prompts)
- Memory usage tracking
- Large prompt collection handling

## Quality Gates

### Code Quality
- [ ] TypeScript strict mode compliance
- [ ] ESLint validation
- [ ] 100% type coverage
- [ ] No circular dependencies

### Testing
- [ ] >90% code coverage
- [ ] All integration tests passing
- [ ] Performance benchmarks met
- [ ] Memory leak tests passing

### Documentation
- [ ] Complete API documentation
- [ ] Usage examples provided
- [ ] Architecture decision records
- [ ] Migration notes prepared

## Deliverables

1. **Shared Service Package**
   - Complete PromptService interface and implementation
   - Variable resolution and rendering utilities
   - Service factory with dependency injection

2. **Test Suite**
   - Comprehensive unit and integration tests
   - Performance benchmarks
   - Test utilities for future phases

3. **Documentation**
   - API documentation
   - Architecture overview
   - Usage examples and best practices

4. **Configuration**
   - TypeScript configuration
   - Build scripts
   - Quality gate automation

## Success Criteria

- [ ] All interfaces compile without errors
- [ ] Test suite passes with >90% coverage
- [ ] Performance requirements met
- [ ] Zero dependencies on existing prompt store implementation
- [ ] Clean, documented API ready for Phase 2 integration

## Risk Mitigation

### Technical Risks
1. **Complex Variable Resolution**: Start with simple patterns, iterate
2. **Performance Impact**: Benchmark early, optimize incrementally
3. **Type Safety**: Use strict TypeScript, comprehensive type definitions

### Integration Risks
1. **Interface Misalignment**: Regular validation with existing codebase
2. **Breaking Changes**: Maintain strict backward compatibility
3. **Scope Creep**: Focus only on foundation, defer enhancements

## Next Phase Preparation

This phase prepares for Phase 2 by:
- Establishing clear interfaces for PromptManager integration
- Providing migration utilities and patterns
- Creating test frameworks for validation
- Documenting integration points and requirements 