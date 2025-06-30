# Agent Manager

The Agent Manager module provides centralized orchestration and execution tracking for worker agents in the Wu Wei extension. This module combines agent interface definitions with execution management capabilities and UI integration.

## Components

### Agent Interfaces (`agentInterface.ts`)
- **Abstract agent interfaces**: Core interfaces for agent communication following MCP/A2A patterns
- **Agent implementations**: Concrete implementations like `GitHubCopilotAgent` and `WuWeiExampleAgent`
- **Agent registry**: Central registry for managing multiple agents

### Execution Registry (`ExecutionRegistry.ts`)
- **Execution tracking**: Maintains registry of active agent executions
- **Correlation strategies**: Multiple strategies for matching completion signals to executions
- **Timeout management**: Automatic cleanup of stale executions
- **Statistics and monitoring**: Execution performance tracking

### Prompt Enhancer (`PromptEnhancer.ts`)
- **Context injection**: Enhances user prompts with execution tracking metadata
- **Completion instructions**: Generates instructions for agents to signal completion
- **Task description extraction**: Extracts meaningful task descriptions from parameters

### Agent Panel Provider (`agentPanelProvider.ts`)
- **UI integration**: Webview provider for agent interaction panel
- **Execution lifecycle management**: Real-time tracking and UI updates for executions
- **Prompt integration**: Support for prompt templates and variable rendering
- **Message history**: Maintains conversation history and execution records
- **Completion signal handling**: Integration with CopilotCompletionSignalTool

## Usage

```typescript
import { 
    AbstractAgent, 
    AgentRegistry, 
    ExecutionRegistry, 
    PromptEnhancer,
    AgentPanelProvider 
} from './agentManager';

// Register and manage agents
const registry = new AgentRegistry();
const agent = new GitHubCopilotAgent();
registry.registerAgent(agent);

// Track executions
const executionRegistry = new ExecutionRegistry();
executionRegistry.registerExecution({
    executionId: 'unique-id',
    agentName: 'github-copilot',
    method: 'ask',
    taskDescription: 'Help me with code',
    startTime: new Date(),
    status: 'pending',
    originalParams: {}
});

// Enhance prompts with execution tracking
const enhancedPrompt = PromptEnhancer.enhancePromptWithExecutionContext(
    'Original user prompt',
    {
        executionId: 'unique-id',
        taskDescription: 'Help me with code',
        agentName: 'github-copilot',
        startTime: new Date()
    }
);

// Initialize UI provider
const agentPanelProvider = new AgentPanelProvider(context);
```

## Architecture

This module follows the orchestrator-worker pattern where:
- **Orchestrator**: The VS Code extension coordinates agent requests
- **Workers**: Individual agents (like GitHub Copilot) execute tasks
- **Execution Registry**: Tracks and correlates execution lifecycle
- **Prompt Enhancer**: Ensures proper execution tracking in agent communications
- **Agent Panel Provider**: Provides UI integration and real-time feedback

## Features

### Phase 1: Basic Agent Execution
- Agent registration and management
- Request/response handling
- Basic UI integration

### Phase 2: Execution Tracking
- Real-time execution status tracking
- Completion signal integration
- Execution history and analytics
- UI status updates and progress indicators

### Phase 3: Enhanced Correlation
- Smart execution correlation using multiple strategies
- Robust timeout handling and cleanup
- Comprehensive error handling and recovery
