# Phase 5: Prompt-Aware Agents

## Overview

Enhance existing agents to support prompt integration and create example prompt templates for common agent tasks. This phase completes the integration by making agents fully prompt-aware while maintaining backward compatibility.

## Objectives

1. Enhance existing agents with prompt support capabilities
2. Create comprehensive prompt templates for common agent workflows
3. Update agent capabilities interface to advertise prompt support
4. Provide documentation and examples for creating prompt-aware agents
5. Establish best practices for prompt-agent integration

## Current State Analysis

### Existing Agents
- **WuWeiExampleAgent**: Basic demonstration agent with echo, status, and execute methods
- **GitHubCopilotAgent**: Integration with GitHub Copilot for code assistance and opening agent panel

### Enhancement Opportunities
- Add prompt context to agent methods
- Create specialized prompt templates for each agent type
- Enhance agent capabilities to advertise prompt support
- Improve agent-specific parameter handling

## Technical Specification

### 1. Enhanced Agent Interface

#### Prompt-Aware Agent Capabilities
```typescript
export interface AgentPromptCapabilities {
  supportsPrompts: boolean
  promptParameterName?: string // e.g., 'systemPrompt', 'context', 'instructions'
  supportedPromptTypes?: string[] // e.g., ['system', 'user', 'instruction', 'template']
  variableResolution?: boolean
  promptTemplates?: string[] // IDs of recommended prompt templates
  maxPromptLength?: number
}

// Extended agent capabilities
export interface EnhancedAgentCapabilities extends AgentCapabilities {
  promptSupport?: AgentPromptCapabilities
  examples?: AgentMethodExample[]
}

export interface AgentMethodExample {
  method: string
  description: string
  parameters: any
  promptTemplate?: string
  expectedResult?: string
}
```

#### Prompt-Aware Method Processing
```typescript
export abstract class PromptAwareAgent extends AbstractAgent {
  protected promptResolver?: VariableResolver

  constructor(capabilities: EnhancedAgentCapabilities) {
    super(capabilities)
    
    if (capabilities.promptSupport?.variableResolution) {
      this.promptResolver = new VariableResolver()
    }
  }

  protected async executeMethodWithPrompt(
    method: string, 
    params: any, 
    promptContext?: string
  ): Promise<any> {
    // Default implementation - can be overridden by concrete agents
    if (promptContext && this.promptResolver) {
      // Extract variables from prompt if needed
      const variables = this.promptResolver.extractVariables(promptContext)
      
      // Enhanced parameters with prompt context
      const enhancedParams = {
        ...params,
        prompt: promptContext,
        variables
      }

      return this.executeMethod(method, enhancedParams)
    }

    return this.executeMethod(method, params)
  }

  // Helper method to validate prompt compatibility
  protected validatePromptContext(promptContext: string): ValidationResult {
    const errors: ValidationError[] = []
    const warnings: ValidationWarning[] = []

    const capabilities = this.getCapabilities() as EnhancedAgentCapabilities
    const promptSupport = capabilities.promptSupport

    if (!promptSupport?.supportsPrompts) {
      errors.push({
        field: 'promptSupport',
        message: 'This agent does not support prompt integration',
        severity: 'error'
      })
      return { isValid: false, errors, warnings }
    }

    if (promptSupport.maxPromptLength && promptContext.length > promptSupport.maxPromptLength) {
      errors.push({
        field: 'promptLength',
        message: `Prompt exceeds maximum length of ${promptSupport.maxPromptLength} characters`,
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

### 2. Enhanced GitHubCopilotAgent

#### Prompt-Aware GitHub Copilot Integration
```typescript
export class GitHubCopilotAgent extends PromptAwareAgent {
  constructor() {
    super({
      name: 'github-copilot',
      version: '2.0.0',
      methods: ['ask', 'openAgent', 'codeReview', 'explainCode', 'generateTests'],
      description: 'GitHub Copilot integration with prompt support for enhanced AI assistance',
      promptSupport: {
        supportsPrompts: true,
        promptParameterName: 'systemPrompt',
        supportedPromptTypes: ['system', 'instruction', 'template'],
        variableResolution: true,
        promptTemplates: [
          'github-copilot-code-review',
          'github-copilot-explain-code',
          'github-copilot-generate-tests',
          'github-copilot-debugging-assistant'
        ],
        maxPromptLength: 4000
      },
      examples: [
        {
          method: 'ask',
          description: 'Ask a question with custom context',
          parameters: {
            question: 'How do I implement error handling?',
            systemPrompt: 'You are a senior software engineer specializing in {{language}}. Focus on best practices and production-ready code.'
          },
          promptTemplate: 'github-copilot-code-review'
        },
        {
          method: 'codeReview',
          description: 'Review code with specific focus areas',
          parameters: {
            code: 'function processData(data) { return data.map(item => item.value); }',
            focusAreas: ['performance', 'error handling'],
            systemPrompt: 'Review this {{language}} code focusing on {{focusAreas}}. Provide specific suggestions for improvement.'
          },
          promptTemplate: 'github-copilot-code-review'
        }
      ]
    })
  }

  private async handleAskWithPrompt(params: any, hasPromptContext: boolean): Promise<any> {
    try {
      const vscode = await import('vscode')
      
      if (!params.question && !params.query) {
        throw new Error('Question or query parameter is required')
      }

      const query = params.question || params.query
      
      // Enhance the query with prompt context if available
      let enhancedQuery = query
      if (hasPromptContext) {
        const systemPrompt = params.systemPrompt || params.prompt
        enhancedQuery = `${systemPrompt}\n\nUser Question: ${query}`
        
        // Add variable context if available
        if (params.variables) {
          enhancedQuery += `\n\nContext Variables: ${JSON.stringify(params.variables, null, 2)}`
        }
      }

      // Execute the Copilot chat command with enhanced query
      await vscode.commands.executeCommand('github.copilot.interactiveEditor.explain', enhancedQuery)

      return {
        success: true,
        message: hasPromptContext ? 
          'Question sent to GitHub Copilot with custom prompt context' :
          'Question sent to GitHub Copilot',
        query: enhancedQuery,
        promptContext: hasPromptContext ? params.systemPrompt || params.prompt : undefined
      }
    } catch (error) {
      throw new Error(`Failed to ask GitHub Copilot: ${error.message}`)
    }
  }

  private async handleCodeReview(params: any, hasPromptContext: boolean): Promise<any> {
    try {
      const vscode = await import('vscode')

      if (!params.code && !params.selection) {
        throw new Error('Code or selection parameter is required for code review')
      }

      let reviewPrompt = 'Please review the following code:'
      
      if (hasPromptContext) {
        const systemPrompt = params.systemPrompt || params.prompt
        reviewPrompt = systemPrompt
      }

      const code = params.code || params.selection
      const focusAreas = params.focusAreas || []
      
      if (focusAreas.length > 0) {
        reviewPrompt += `\n\nFocus areas: ${focusAreas.join(', ')}`
      }

      const fullPrompt = `${reviewPrompt}\n\n\`\`\`\n${code}\n\`\`\``

      // Use Copilot chat for code review
      await vscode.commands.executeCommand('github.copilot.interactiveEditor.explain', fullPrompt)

      return {
        success: true,
        message: 'Code review request sent to GitHub Copilot',
        reviewPrompt,
        focusAreas,
        codeLength: code.length
      }
    } catch (error) {
      throw new Error(`Failed to initiate code review: ${error.message}`)
    }
  }
}
```

### 3. Prompt Template Library

#### GitHub Copilot Code Review Template
```yaml
---
title: GitHub Copilot Code Review Assistant
description: Comprehensive code review template with focus areas
category: github-copilot
tags: [code-review, quality, best-practices]
parameters:
  - name: language
    type: select
    options: [javascript, typescript, python, java, csharp, go, rust]
    required: true
    description: Programming language of the code
  - name: focusAreas
    type: select
    options: [performance, security, readability, maintainability, error-handling]
    required: false
    description: Specific areas to focus on during review
  - name: experience
    type: select
    options: [junior, mid-level, senior]
    required: false
    default: mid-level
    description: Target experience level for recommendations
---

# Code Review Assistant

You are an expert {{language}} developer and code reviewer. Your task is to review code with the expertise of a {{experience}} developer, focusing on {{focusAreas}}.

## Review Guidelines

Please analyze the code for:
- Code quality and best practices
- Potential bugs or issues
- Performance optimizations
- Security vulnerabilities
- Readability and maintainability

{{#if focusAreas}}
**Special Focus**: Pay particular attention to {{focusAreas}}.
{{/if}}

## Output Format

Provide your review in the following format:
1. **Summary**: Brief overview of the code quality
2. **Issues Found**: List any problems with severity levels
3. **Recommendations**: Specific suggestions for improvement
4. **Best Practices**: Relevant best practices for {{language}}

Remember to be constructive and provide actionable feedback suitable for a {{experience}} developer.
```

#### GitHub Copilot Code Explanation Template
```yaml
---
title: GitHub Copilot Code Explanation Assistant
description: Detailed code explanation with customizable detail level
category: github-copilot
tags: [explanation, learning, documentation]
parameters:
  - name: language
    type: select
    options: [javascript, typescript, python, java, csharp, go, rust]
    required: true
    description: Programming language of the code
  - name: detailLevel
    type: select
    options: [overview, detailed, step-by-step]
    required: false
    default: detailed
    description: Level of detail for the explanation
  - name: audience
    type: select
    options: [beginner, intermediate, advanced]
    required: false
    default: intermediate
    description: Target audience experience level
---

# Code Explanation Assistant

You are an expert {{language}} developer and technical writer. Explain the provided code clearly and thoroughly for an {{audience}} programmer.

## Explanation Style

{{#if detailLevel == "overview"}}
Provide a high-level overview of what the code does, its purpose, and key components.
{{/if}}

{{#if detailLevel == "detailed"}}
Provide a comprehensive explanation including:
- Purpose and functionality
- Key components and their roles
- Logic flow and algorithms used
- Important design decisions
{{/if}}

{{#if detailLevel == "step-by-step"}}
Provide a detailed step-by-step walkthrough:
- Break down the code line by line or section by section
- Explain the purpose of each part
- Describe the data flow and transformations
- Highlight any complex logic or algorithms
{{/if}}

## Audience Considerations

Adjust your explanation for an {{audience}} {{language}} developer:
- Use appropriate technical terminology
- Provide context for complex concepts
- Include relevant best practices or alternatives where helpful

Focus on clarity and educational value to help the reader understand both what the code does and why it's structured that way.
```

## Implementation Tasks

### Week 1: Agent Enhancement Foundation

#### Day 1-2: Enhanced Agent Interface
- [ ] Create PromptAwareAgent base class
- [ ] Define AgentPromptCapabilities interface
- [ ] Implement validation methods for prompt context
- [ ] Create helper utilities for variable resolution

#### Day 3-4: GitHubCopilotAgent Enhancement
- [ ] Refactor GitHubCopilotAgent to extend PromptAwareAgent
- [ ] Implement prompt-aware method handlers
- [ ] Add variable resolution for prompts
- [ ] Test integration with VS Code Copilot commands

#### Day 5: WuWeiExampleAgent Enhancement
- [ ] Enhance WuWeiExampleAgent with prompt capabilities
- [ ] Create demonstration methods for prompt patterns
- [ ] Implement template processing examples
- [ ] Add comprehensive test cases

### Week 2: Prompt Template Creation

#### Day 1-2: GitHub Copilot Templates
- [ ] Create code review prompt template
- [ ] Create code explanation prompt template
- [ ] Create test generation prompt template
- [ ] Create debugging assistant prompt template

#### Day 3-4: Wu Wei Example Templates
- [ ] Create echo formatting templates
- [ ] Create validation templates
- [ ] Create processing templates
- [ ] Create error handling templates

#### Day 5: Template Testing and Validation
- [ ] Test all templates with variable substitution
- [ ] Validate template parameters and types
- [ ] Test templates with real agent scenarios
- [ ] Create template usage documentation

### Week 3: Integration and Documentation

#### Day 1-2: Agent Registry Updates
- [ ] Update AgentRegistry to handle enhanced capabilities
- [ ] Add prompt template discovery and association
- [ ] Implement capability querying for prompt support
- [ ] Test agent registration and discovery

#### Day 3-4: Documentation and Examples
- [ ] Create comprehensive agent development guide
- [ ] Write prompt template creation guide
- [ ] Create example workflows and use cases
- [ ] Document best practices for prompt-agent integration

#### Day 5: Testing and Quality Assurance
- [ ] End-to-end testing of all enhanced agents
- [ ] Performance testing with complex prompts
- [ ] User acceptance testing of workflows
- [ ] Final integration validation

## Testing Strategy

### Agent Testing
```typescript
describe('Enhanced GitHubCopilotAgent', () => {
  test('handles prompt-aware code review', async () => {
    const agent = new GitHubCopilotAgent()
    
    const result = await agent.processRequest({
      id: 'test-1',
      method: 'codeReview',
      params: {
        code: 'function test() { return true; }',
        systemPrompt: 'Review this {{language}} code for {{focusAreas}}',
        variables: {
          language: 'javascript',
          focusAreas: 'performance'
        }
      },
      timestamp: new Date()
    })

    expect(result.result.success).toBe(true)
    expect(result.result.reviewPrompt).toContain('Review this javascript code for performance')
  })

  test('validates prompt capabilities', () => {
    const agent = new GitHubCopilotAgent()
    const capabilities = agent.getCapabilities() as EnhancedAgentCapabilities
    
    expect(capabilities.promptSupport?.supportsPrompts).toBe(true)
    expect(capabilities.promptSupport?.variableResolution).toBe(true)
    expect(capabilities.promptSupport?.promptTemplates).toContain('github-copilot-code-review')
  })
})
```

### Template Testing
```typescript
describe('Prompt Templates', () => {
  test('github-copilot-code-review template renders correctly', () => {
    const template = loadTemplate('github-copilot-code-review')
    const variables = {
      language: 'typescript',
      focusAreas: 'security',
      experience: 'senior'
    }

    const rendered = renderTemplate(template, variables)

    expect(rendered).toContain('expert typescript developer')
    expect(rendered).toContain('focusing on security')
    expect(rendered).toContain('suitable for a senior developer')
  })

  test('template parameter validation', () => {
    const template = loadTemplate('github-copilot-code-review')
    const errors = validateTemplateParameters(template, {})

    expect(errors).toContainEqual({
      field: 'language',
      message: 'language is required',
      severity: 'error'
    })
  })
})
```

## Quality Gates

### Agent Enhancement Requirements
- [ ] All existing agent methods work without prompt context
- [ ] Prompt-aware methods handle variable substitution correctly
- [ ] Agent capabilities accurately reflect prompt support
- [ ] Error handling for invalid prompts and variables
- [ ] Performance impact is minimal for non-prompt operations

### Template Quality Requirements
- [ ] All templates have valid metadata and parameters
- [ ] Variable substitution works correctly in all templates
- [ ] Templates provide clear, actionable guidance
- [ ] Parameter validation prevents invalid configurations
- [ ] Templates are well-documented with examples

### Integration Requirements
- [ ] Agents work seamlessly with enhanced agent panel
- [ ] Template selection and variable editing functions correctly
- [ ] Agent registry properly handles enhanced capabilities
- [ ] Performance is acceptable with complex templates
- [ ] No breaking changes to existing functionality

## Success Criteria

- [ ] All agents support prompt integration while maintaining backward compatibility
- [ ] Comprehensive template library covers common use cases
- [ ] Agent capabilities clearly communicate prompt support
- [ ] Developer documentation enables easy creation of new prompt-aware agents
- [ ] User workflows are intuitive and provide value over manual approaches
- [ ] Performance and reliability meet production standards

## Deliverables

1. **Enhanced Agents**
   - GitHubCopilotAgent with full prompt support
   - WuWeiExampleAgent demonstrating prompt patterns
   - PromptAwareAgent base class for future agents

2. **Prompt Template Library**
   - GitHub Copilot templates for common tasks
   - Wu Wei example templates for development
   - Template creation guidelines and best practices

3. **Documentation Package**
   - Agent development guide for prompt integration
   - Template creation and customization guide
   - User workflows and examples
   - API documentation for enhanced capabilities

4. **Testing Suite**
   - Comprehensive test coverage for all enhanced agents
   - Template validation and rendering tests
   - Integration tests for complete workflows
   - Performance benchmarks

## Conclusion

Phase 5 completes the prompt-agent integration by making agents fully prompt-aware while maintaining simplicity and backward compatibility. The enhanced agents provide powerful new capabilities for users while establishing patterns for future agent development.

The comprehensive template library and documentation ensure users can immediately benefit from the integration, while developers have clear guidance for creating new prompt-aware agents. This phase delivers on the promise of seamless prompt-to-agent workflows envisioned in the overall integration plan. 