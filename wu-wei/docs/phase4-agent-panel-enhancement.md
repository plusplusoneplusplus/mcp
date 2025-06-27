# Phase 4: Agent Panel Enhancement

## Overview

Enhance the agent panel with prompt selection and integration capabilities, creating a seamless workflow from prompt selection to agent execution. This phase delivers the core user-facing integration between prompts and agents.

## Objectives

1. Add prompt selection interface to the agent panel
2. Implement variable input forms for prompt parameters
3. Create prompt preview and rendering capabilities
4. Enhance agent request processing with prompt context
5. Provide seamless user experience for prompt-to-agent workflows

## Current State Analysis

### Agent Panel Current Capabilities
- Agent selection dropdown with capabilities display
- Method selection based on agent capabilities
- Parameter input (currently free-form text/JSON)
- Request execution and response display
- Message history with collapsible interface

### Integration Points for Enhancement
- Parameter input area expansion for prompt integration
- Webview communication protocol extension
- Agent request processing enhancement
- UI layout modifications for prompt selection

## Technical Specification

### 1. UI Architecture Enhancement

#### Enhanced Agent Panel Layout
```typescript
interface AgentPanelState {
  // Existing state
  selectedAgent: string
  selectedMethod: string
  customMessage: string
  messageHistory: AgentMessage[]

  // New prompt-related state
  selectedPrompt?: PromptUsageContext
  promptVariables: Record<string, any>
  promptMode: 'custom' | 'prompt' | 'combined'
  showPromptSelector: boolean
  showVariableEditor: boolean
  availablePrompts: Prompt[]
}

interface AgentPanelUI {
  // Existing components
  agentSelector: HTMLSelectElement
  methodSelector: HTMLSelectElement
  paramsInput: HTMLTextAreaElement

  // New prompt components
  promptModeSelector: HTMLSelectElement
  promptSelector: HTMLSelectElement
  promptPreview: HTMLDivElement
  variableEditor: HTMLDivElement
  combinedMessageArea: HTMLTextAreaElement
}
```

#### Prompt Integration Modes
```typescript
enum PromptMode {
  CUSTOM = 'custom',     // Traditional free-form input
  PROMPT = 'prompt',     // Prompt-only with variables
  COMBINED = 'combined'  // Prompt + additional message
}

interface PromptModeConfig {
  mode: PromptMode
  showPromptSelector: boolean
  showVariableEditor: boolean
  showCustomInput: boolean
  placeholder: string
}
```

### 2. Prompt Selector Component

#### Prompt Search and Selection
```typescript
class PromptSelector {
  private promptService: PromptService
  private searchInput: HTMLInputElement
  private promptList: HTMLSelectElement
  private selectedPrompt?: PromptUsageContext

  constructor(promptService: PromptService) {
    this.promptService = promptService
    this.setupUI()
    this.setupEventHandlers()
  }

  private setupUI(): void {
    // Create search interface
    this.searchInput = this.createElement('input', {
      type: 'text',
      placeholder: 'Search prompts...',
      class: 'prompt-search'
    })

    // Create prompt list
    this.promptList = this.createElement('select', {
      class: 'prompt-list',
      size: '5'
    })

    // Setup container
    const container = document.getElementById('promptSelector')
    container.appendChild(this.searchInput)
    container.appendChild(this.promptList)
  }

  private setupEventHandlers(): void {
    // Search functionality
    this.searchInput.addEventListener('input', 
      this.debounce(this.handleSearch.bind(this), 300)
    )

    // Prompt selection
    this.promptList.addEventListener('change', this.handlePromptSelection.bind(this))
  }

  private async handleSearch(event: Event): Promise<void> {
    const query = (event.target as HTMLInputElement).value
    
    try {
      const prompts = await this.promptService.searchPrompts(query)
      this.updatePromptList(prompts)
    } catch (error) {
      console.error('Prompt search failed:', error)
      this.showError('Failed to search prompts')
    }
  }

  private async handlePromptSelection(event: Event): Promise<void> {
    const promptId = (event.target as HTMLSelectElement).value
    
    if (!promptId) {
      this.selectedPrompt = undefined
      this.notifySelectionChange()
      return
    }

    try {
      this.selectedPrompt = await this.promptService.selectPromptForUse(promptId)
      this.notifySelectionChange()
    } catch (error) {
      console.error('Prompt selection failed:', error)
      this.showError('Failed to select prompt')
    }
  }

  private updatePromptList(prompts: Prompt[]): void {
    this.promptList.innerHTML = '<option value="">Select a prompt...</option>'
    
    prompts.forEach(prompt => {
      const option = document.createElement('option')
      option.value = prompt.id
      option.textContent = `${prompt.metadata.title} (${prompt.metadata.category || 'General'})`
      this.promptList.appendChild(option)
    })
  }

  private notifySelectionChange(): void {
    const event = new CustomEvent('promptSelected', {
      detail: this.selectedPrompt
    })
    document.dispatchEvent(event)
  }
}
```

### 3. Variable Editor Component

#### Dynamic Form Generation
```typescript
class VariableEditor {
  private container: HTMLDivElement
  private parameters: PromptParameter[] = []
  private values: Record<string, any> = {}

  constructor(container: HTMLDivElement) {
    this.container = container
  }

  setParameters(parameters: PromptParameter[]): void {
    this.parameters = parameters
    this.values = {}
    this.renderForm()
  }

  private renderForm(): void {
    this.container.innerHTML = ''

    if (this.parameters.length === 0) {
      this.container.innerHTML = '<p class="no-variables">This prompt has no variables.</p>'
      return
    }

    const form = document.createElement('div')
    form.className = 'variable-form'

    this.parameters.forEach(param => {
      const fieldContainer = this.createField(param)
      form.appendChild(fieldContainer)
    })

    this.container.appendChild(form)
  }

  private createField(param: PromptParameter): HTMLElement {
    const container = document.createElement('div')
    container.className = 'variable-field'

    // Label
    const label = document.createElement('label')
    label.textContent = param.name
    if (param.required) {
      label.classList.add('required')
    }
    
    // Description
    if (param.description) {
      const description = document.createElement('small')
      description.textContent = param.description
      description.className = 'field-description'
      label.appendChild(document.createElement('br'))
      label.appendChild(description)
    }

    // Input
    const input = this.createInput(param)
    
    container.appendChild(label)
    container.appendChild(input)

    return container
  }

  private createInput(param: PromptParameter): HTMLElement {
    switch (param.type) {
      case 'string':
        return this.createTextInput(param)
      case 'multiline':
        return this.createTextArea(param)
      case 'number':
        return this.createNumberInput(param)
      case 'boolean':
        return this.createCheckbox(param)
      case 'select':
        return this.createSelect(param)
      case 'file':
        return this.createFileInput(param)
      default:
        return this.createTextInput(param)
    }
  }

  private createTextInput(param: PromptParameter): HTMLInputElement {
    const input = document.createElement('input')
    input.type = 'text'
    input.name = param.name
    input.placeholder = param.placeholder || `Enter ${param.name}...`
    input.required = param.required || false
    
    if (param.defaultValue) {
      input.value = String(param.defaultValue)
      this.values[param.name] = param.defaultValue
    }

    input.addEventListener('input', (e) => {
      this.values[param.name] = (e.target as HTMLInputElement).value
      this.notifyValueChange()
    })

    return input
  }

  private createTextArea(param: PromptParameter): HTMLTextAreaElement {
    const textarea = document.createElement('textarea')
    textarea.name = param.name
    textarea.placeholder = param.placeholder || `Enter ${param.name}...`
    textarea.required = param.required || false
    textarea.rows = 3

    if (param.defaultValue) {
      textarea.value = String(param.defaultValue)
      this.values[param.name] = param.defaultValue
    }

    textarea.addEventListener('input', (e) => {
      this.values[param.name] = (e.target as HTMLTextAreaElement).value
      this.notifyValueChange()
    })

    return textarea
  }

  private createSelect(param: PromptParameter): HTMLSelectElement {
    const select = document.createElement('select')
    select.name = param.name
    select.required = param.required || false

    // Add empty option if not required
    if (!param.required) {
      const emptyOption = document.createElement('option')
      emptyOption.value = ''
      emptyOption.textContent = `Select ${param.name}...`
      select.appendChild(emptyOption)
    }

    // Add options
    param.options?.forEach(option => {
      const optionElement = document.createElement('option')
      optionElement.value = option
      optionElement.textContent = option
      select.appendChild(optionElement)
    })

    if (param.defaultValue) {
      select.value = String(param.defaultValue)
      this.values[param.name] = param.defaultValue
    }

    select.addEventListener('change', (e) => {
      const value = (e.target as HTMLSelectElement).value
      this.values[param.name] = value || undefined
      this.notifyValueChange()
    })

    return select
  }

  getValues(): Record<string, any> {
    return { ...this.values }
  }

  validateValues(): ValidationError[] {
    const errors: ValidationError[] = []

    this.parameters.forEach(param => {
      const value = this.values[param.name]

      // Check required fields
      if (param.required && (value === undefined || value === '')) {
        errors.push({
          field: param.name,
          message: `${param.name} is required`,
          severity: 'error'
        })
      }

      // Type validation
      if (value !== undefined && value !== '') {
        switch (param.type) {
          case 'number':
            if (isNaN(Number(value))) {
              errors.push({
                field: param.name,
                message: `${param.name} must be a number`,
                severity: 'error'
              })
            }
            break
        }
      }

      // Custom validation
      if (param.validation && value !== undefined) {
        if (param.validation.pattern && !new RegExp(param.validation.pattern).test(String(value))) {
          errors.push({
            field: param.name,
            message: `${param.name} format is invalid`,
            severity: 'error'
          })
        }

        if (param.validation.minLength && String(value).length < param.validation.minLength) {
          errors.push({
            field: param.name,
            message: `${param.name} must be at least ${param.validation.minLength} characters`,
            severity: 'error'
          })
        }
      }
    })

    return errors
  }

  private notifyValueChange(): void {
    const event = new CustomEvent('variablesChanged', {
      detail: this.getValues()
    })
    document.dispatchEvent(event)
  }
}
```

### 4. Prompt Preview Component

#### Real-time Prompt Rendering
```typescript
class PromptPreview {
  private container: HTMLDivElement
  private promptContent: string = ''
  private variables: Record<string, any> = {}

  constructor(container: HTMLDivElement) {
    this.container = container
  }

  setPrompt(prompt: PromptUsageContext): void {
    this.promptContent = prompt.prompt.content
    this.render()
  }

  setVariables(variables: Record<string, any>): void {
    this.variables = variables
    this.render()
  }

  private render(): void {
    if (!this.promptContent) {
      this.container.innerHTML = '<p class="no-preview">Select a prompt to see preview</p>'
      return
    }

    try {
      const rendered = this.renderWithVariables(this.promptContent, this.variables)
      
      this.container.innerHTML = `
        <div class="prompt-preview">
          <h4>Prompt Preview</h4>
          <div class="preview-content">${this.formatPreview(rendered)}</div>
        </div>
      `
    } catch (error) {
      this.container.innerHTML = `
        <div class="prompt-preview error">
          <h4>Preview Error</h4>
          <p class="error-message">${error.message}</p>
        </div>
      `
    }
  }

  private renderWithVariables(content: string, variables: Record<string, any>): string {
    const variablePattern = /\{\{(\w+)\}\}/g
    
    return content.replace(variablePattern, (match, variableName) => {
      if (variables.hasOwnProperty(variableName)) {
        return String(variables[variableName])
      }
      return `<span class="undefined-variable">${match}</span>`
    })
  }

  private formatPreview(content: string): string {
    // Convert markdown to basic HTML for preview
    return content
      .replace(/^# (.*$)/gm, '<h1>$1</h1>')
      .replace(/^## (.*$)/gm, '<h2>$1</h2>')
      .replace(/^### (.*$)/gm, '<h3>$1</h3>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>')
  }
}
```

### 5. Enhanced Agent Panel Integration

#### Updated AgentPanelProvider
```typescript
export class AgentPanelProvider extends BaseWebviewProvider {
  private promptService: PromptService
  private selectedPromptContext?: PromptUsageContext

  constructor(context: vscode.ExtensionContext) {
    super(context)
    
    // Initialize prompt service
    this.promptService = PromptServiceFactory.createService(context)
    this.setupPromptEventHandlers()
  }

  private setupPromptEventHandlers(): void {
    this.promptService.onPromptsChanged(this.handlePromptsChanged.bind(this))
    this.promptService.onPromptSelected(this.handlePromptSelected.bind(this))
  }

  private async handlePromptsChanged(prompts: Prompt[]): Promise<void> {
    if (this._view) {
      this._view.webview.postMessage({
        command: 'updateAvailablePrompts',
        prompts: prompts.map(p => ({
          id: p.id,
          title: p.metadata.title,
          category: p.metadata.category,
          description: p.metadata.description,
          tags: p.metadata.tags
        }))
      })
    }
  }

  private async handlePromptSelected(context: PromptUsageContext): Promise<void> {
    this.selectedPromptContext = context
    
    if (this._view) {
      this._view.webview.postMessage({
        command: 'promptSelected',
        promptContext: {
          id: context.prompt.id,
          title: context.prompt.metadata.title,
          content: context.prompt.content,
          parameters: context.metadata.parameters || [],
          usageInstructions: context.metadata.usageInstructions
        }
      })
    }
  }

  // Enhanced message handling
  protected async handleMessage(message: any): Promise<void> {
    switch (message.command) {
      case 'selectPrompt':
        await this.handleSelectPrompt(message.promptId)
        break

      case 'renderPromptWithVariables':
        await this.handleRenderPrompt(message.promptId, message.variables)
        break

      case 'sendAgentRequestWithPrompt':
        await this.handleAgentRequestWithPrompt(
          message.agentName,
          message.method,
          message.params,
          message.promptContext
        )
        break

      // Existing handlers...
      case 'sendAgentRequest':
        await this.handleAgentRequest(message.agentName, message.method, message.params)
        break

      default:
        await super.handleMessage(message)
    }
  }

  private async handleSelectPrompt(promptId: string): Promise<void> {
    try {
      const context = await this.promptService.selectPromptForUse(promptId)
      this.selectedPromptContext = context
      
      this._view?.webview.postMessage({
        command: 'promptSelected',
        promptContext: context
      })
    } catch (error) {
      this._view?.webview.postMessage({
        command: 'error',
        error: `Failed to select prompt: ${error.message}`
      })
    }
  }

  private async handleRenderPrompt(promptId: string, variables: Record<string, any>): Promise<void> {
    try {
      const rendered = await this.promptService.renderPromptWithVariables(promptId, variables)
      
      this._view?.webview.postMessage({
        command: 'promptRendered',
        rendered
      })
    } catch (error) {
      this._view?.webview.postMessage({
        command: 'error',
        error: `Failed to render prompt: ${error.message}`
      })
    }
  }

  private async handleAgentRequestWithPrompt(
    agentName: string,
    method: string,
    params: any,
    promptContext?: any
  ): Promise<void> {
    try {
      const agent = this._agentRegistry.getAgent(agentName)
      if (!agent) {
        throw new Error(`Agent '${agentName}' not found`)
      }

      // Enhance parameters with prompt context
      const enhancedParams = await this.enhanceParamsWithPrompt(params, promptContext, agent)

      // Process the request
      const request: AgentRequest = {
        id: this.generateMessageId(),
        method,
        params: enhancedParams,
        timestamp: new Date()
      }

      const response = await agent.processRequest(request)
      
      // Add to message history
      this.addMessageToHistory({
        id: request.id,
        timestamp: request.timestamp,
        type: 'request',
        method: request.method,
        params: request.params
      })

      this.addMessageToHistory({
        id: response.id,
        timestamp: response.timestamp,
        type: 'response',
        result: response.result,
        error: response.error
      })

    } catch (error) {
      this.addMessageToHistory({
        id: this.generateMessageId(),
        timestamp: new Date(),
        type: 'error',
        error: {
          code: -32603,
          message: 'Request failed',
          data: error instanceof Error ? error.message : String(error)
        }
      })
    }
  }

  private async enhanceParamsWithPrompt(
    params: any,
    promptContext: any,
    agent: AbstractAgent
  ): Promise<any> {
    if (!promptContext) {
      return params
    }

    const capabilities = agent.getCapabilities()
    const promptSupport = capabilities.metadata?.promptSupport

    if (promptSupport?.supportsPrompts) {
      const promptParam = promptSupport.promptParameterName || 'prompt'
      
      // Render the prompt with variables
      const rendered = await this.promptService.renderPromptWithVariables(
        promptContext.promptId,
        promptContext.variables
      )

      return {
        ...params,
        [promptParam]: rendered,
        ...(promptSupport.variableResolution ? { variables: promptContext.variables } : {})
      }
    }

    return params
  }
}
```

## Implementation Tasks

### Week 1: UI Foundation

#### Day 1-2: Layout Design and HTML Structure
- [ ] Design enhanced agent panel layout
- [ ] Create prompt mode selector UI
- [ ] Add prompt selector component container
- [ ] Implement variable editor container
- [ ] Add prompt preview area

#### Day 3-4: Prompt Selector Implementation
- [ ] Implement prompt search functionality
- [ ] Create prompt list with filtering
- [ ] Add prompt selection handling
- [ ] Integrate with prompt service for real-time updates

#### Day 5: Mode Switching Logic
- [ ] Implement prompt mode selector
- [ ] Add toggle between custom/prompt/combined modes
- [ ] Update UI visibility based on mode selection
- [ ] Test mode switching functionality

### Week 2: Variable Editor and Preview

#### Day 1-2: Dynamic Form Generation
- [ ] Implement PromptParameter-based form generation
- [ ] Add support for different input types
- [ ] Implement validation for required fields
- [ ] Add real-time validation feedback

#### Day 3-4: Prompt Preview Component
- [ ] Implement real-time prompt rendering
- [ ] Add variable substitution preview
- [ ] Handle rendering errors gracefully
- [ ] Style preview for readability

#### Day 5: Integration Testing
- [ ] Test end-to-end prompt selection workflow
- [ ] Validate variable editing and preview
- [ ] Test different prompt types and parameters
- [ ] Performance testing with complex prompts

### Week 3: Agent Integration and Polish

#### Day 1-2: Enhanced Agent Processing
- [ ] Update agent request handling for prompt context
- [ ] Implement prompt-aware parameter enhancement
- [ ] Add support for agent prompt capabilities
- [ ] Test with different agent types

#### Day 3-4: Webview Communication Enhancement
- [ ] Implement new message types for prompt operations
- [ ] Update JavaScript for enhanced communication
- [ ] Add error handling for prompt operations
- [ ] Test bidirectional communication

#### Day 5: Polish and User Experience
- [ ] Add loading states for prompt operations
- [ ] Implement error recovery and user feedback
- [ ] Add tooltips and help text
- [ ] Final UI polish and responsive design

## Testing Strategy

### Component Testing
```typescript
describe('PromptSelector Component', () => {
  test('searches prompts correctly', async () => {
    const promptSelector = new PromptSelector(mockPromptService)
    
    // Simulate search
    await promptSelector.handleSearch({ target: { value: 'test' } })
    
    expect(mockPromptService.searchPrompts).toHaveBeenCalledWith('test')
  })

  test('handles prompt selection', async () => {
    const promptSelector = new PromptSelector(mockPromptService)
    
    await promptSelector.handlePromptSelection({ target: { value: 'prompt-id' } })
    
    expect(mockPromptService.selectPromptForUse).toHaveBeenCalledWith('prompt-id')
  })
})

describe('VariableEditor Component', () => {
  test('generates form for prompt parameters', () => {
    const editor = new VariableEditor(document.createElement('div'))
    
    const parameters: PromptParameter[] = [
      { name: 'title', type: 'string', required: true },
      { name: 'category', type: 'select', options: ['general', 'specific'] }
    ]

    editor.setParameters(parameters)
    
    expect(editor.container.querySelectorAll('.variable-field')).toHaveLength(2)
  })

  test('validates required fields', () => {
    const editor = new VariableEditor(document.createElement('div'))
    
    editor.setParameters([
      { name: 'required', type: 'string', required: true }
    ])

    const errors = editor.validateValues()
    
    expect(errors).toContainEqual({
      field: 'required',
      message: 'required is required',
      severity: 'error'
    })
  })
})
```

### Integration Testing
```typescript
describe('Agent Panel Prompt Integration', () => {
  test('enhances agent request with prompt context', async () => {
    const agentPanel = new AgentPanelProvider(mockContext)
    
    const promptContext = {
      promptId: 'test-prompt',
      variables: { title: 'Test Title' }
    }

    await agentPanel.handleAgentRequestWithPrompt(
      'github-copilot',
      'ask',
      { question: 'Test question' },
      promptContext
    )

    expect(mockAgent.processRequest).toHaveBeenCalledWith({
      id: expect.any(String),
      method: 'ask',
      params: {
        question: 'Test question',
        prompt: 'Rendered prompt content with Test Title',
        variables: { title: 'Test Title' }
      },
      timestamp: expect.any(Date)
    })
  })
})
```

### User Experience Testing
- Test complete workflow from prompt selection to agent execution
- Validate error handling and recovery scenarios
- Test with different prompt types and complexity levels
- Cross-browser compatibility testing
- Performance testing with large prompt collections

## Quality Gates

### Functional Requirements
- [ ] Prompt selection works seamlessly with search and filtering
- [ ] Variable editor generates correct forms for all parameter types
- [ ] Prompt preview renders accurately with variable substitution
- [ ] Agent requests are enhanced correctly with prompt context
- [ ] Error handling provides clear feedback to users

### User Experience Requirements
- [ ] Workflow feels natural and intuitive
- [ ] Response times are acceptable (<500ms for UI updates)
- [ ] Error messages are helpful and actionable
- [ ] UI is responsive and works on different screen sizes
- [ ] Keyboard navigation and accessibility support

### Integration Requirements
- [ ] Works with all existing agents without modification
- [ ] Prompt service integration is stable and performant
- [ ] Webview communication is reliable
- [ ] Configuration and settings are preserved
- [ ] No conflicts with existing agent panel functionality

## Success Criteria

- [ ] Users can select and use prompts in agent panel within 3 clicks
- [ ] Variable forms are intuitive and validate correctly
- [ ] Prompt preview provides immediate feedback
- [ ] Agent integration works seamlessly with enhanced parameters
- [ ] Performance remains acceptable with prompt integration
- [ ] Zero regression in existing agent panel functionality

## Next Phase Preparation

This phase prepares for Phase 5 by:
- Providing stable prompt-agent integration foundation
- Creating extensible patterns for agent enhancement
- Establishing user workflows for prompt-aware agents
- Validating integration patterns with existing agents
- Documenting integration capabilities for new agents 