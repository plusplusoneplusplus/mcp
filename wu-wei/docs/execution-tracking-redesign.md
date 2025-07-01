# Wu Wei Execution Tracking Redesign

## Problem Analysis

The current execution tracking system has a fundamental flaw: there's no reliable way to correlate agent panel executions with completion signals from the Copilot Completion Signal Tool.

### Current Broken Flow:
1. Agent Panel generates `executionId: wu-wei-agent-exec-123`
2. Agent Panel injects `executionId` into agent parameters
3. GitHub Copilot processes the request but doesn't preserve/use the `executionId`
4. Copilot Completion Signal Tool gets called without any execution context
5. No way to match completion signal with the original execution

## New Design: Context Window & Temporal Correlation

### Core Principle: Correlation by Context and Time

Instead of relying on passing execution IDs through Copilot (which doesn't work), we'll use:

1. **Context Window Tracking**: Track what execution is "active" in a time window
2. **Prompt Injection**: Inject execution context into the user's prompt itself
3. **Temporal Correlation**: Match completions to executions based on timing
4. **Content Correlation**: Match completions to executions based on task description

### New Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Agent Panel Provider                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ handleAgentRequestWithPrompt()                          │   │
│  │ 1. Generate executionId                                 │   │
│  │ 2. Register active execution in ExecutionRegistry      │   │
│  │ 3. Inject execution context into prompt                 │   │
│  │ 4. Start execution with enhanced prompt                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Enhanced User Prompt                         │
│  Original Prompt + Hidden Execution Context:                   │
│                                                                 │
│  [USER REQUEST]                                                 │
│  Please help me refactor this code...                          │
│                                                                 │
│  [EXECUTION CONTEXT - HIDDEN FROM USER]                        │
│  <!--                                                           │
│  EXECUTION_ID: wu-wei-agent-exec-1719582625123-a1b2c3d4e       │
│  TASK_DESCRIPTION: Code refactoring request                    │
│  START_TIME: 2025-06-30T14:30:25.123Z                         │
│  AGENT: github-copilot                                         │
│  -->                                                            │
│                                                                 │
│  When you complete this request, please use the                │
│  @wu-wei_copilot_completion_signal tool with:                  │
│  - executionId: wu-wei-agent-exec-1719582625123-a1b2c3d4e      │
│  - taskDescription: "Code refactoring request"                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   GitHub Copilot Processing                    │
│  Copilot processes the request and eventually calls:           │
│  @wu-wei_copilot_completion_signal {                           │
│    "executionId": "wu-wei-agent-exec-1719582625123-a1b2c3d4e", │
│    "taskDescription": "Code refactoring request",              │
│    "status": "success",                                        │
│    "summary": "Successfully refactored code..."               │
│  }                                                             │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Copilot Completion Signal Tool                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ invoke()                                                │   │
│  │ 1. Receive executionId from Copilot                    │   │
│  │ 2. Look up execution in ExecutionRegistry              │   │
│  │ 3. Mark execution as completed                          │   │
│  │ 4. Emit completion event with correlation               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Agent Panel Provider                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ onCopilotCompletionSignal()                             │   │
│  │ 1. Receive completion event with executionId           │   │
│  │ 2. Update UI with completion status                     │   │
│  │ 3. Remove from pending executions                       │   │
│  │ 4. Add to message history                               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. ExecutionRegistry
Central registry for tracking active executions:

```typescript
interface ActiveExecution {
  executionId: string;
  agentName: string;
  method: string;
  taskDescription: string;
  startTime: Date;
  status: 'pending' | 'executing' | 'completed' | 'failed' | 'timeout';
  originalParams: any;
  timeoutHandle?: NodeJS.Timeout;
}

class ExecutionRegistry {
  private activeExecutions = new Map<string, ActiveExecution>();
  private static readonly EXECUTION_TIMEOUT = 10 * 60 * 1000; // 10 minutes

  registerExecution(execution: ActiveExecution): void {
    this.activeExecutions.set(execution.executionId, execution);
    
    // Set timeout for cleanup
    execution.timeoutHandle = setTimeout(() => {
      this.timeoutExecution(execution.executionId);
    }, ExecutionRegistry.EXECUTION_TIMEOUT);
  }

  completeExecution(executionId: string): ActiveExecution | null {
    const execution = this.activeExecutions.get(executionId);
    if (execution) {
      execution.status = 'completed';
      if (execution.timeoutHandle) {
        clearTimeout(execution.timeoutHandle);
      }
      this.activeExecutions.delete(executionId);
      return execution;
    }
    return null;
  }

  getActiveExecutions(): ActiveExecution[] {
    return Array.from(this.activeExecutions.values());
  }
}
```

#### 2. Enhanced Prompt Injection
Inject execution context directly into the user's prompt:

```typescript
private enhancePromptWithExecutionContext(
  originalPrompt: string, 
  executionId: string, 
  taskDescription: string
): string {
  const executionContext = `
<!--
EXECUTION_ID: ${executionId}
TASK_DESCRIPTION: ${taskDescription}
START_TIME: ${new Date().toISOString()}
AGENT: github-copilot
-->

When you complete this request, please use the @wu-wei_copilot_completion_signal tool with:
- executionId: ${executionId}
- taskDescription: "${taskDescription}"
- status: "success" (or "partial"/"error" as appropriate)
- summary: Brief description of what was accomplished

`;

  return originalPrompt + '\n\n' + executionContext;
}
```

#### 3. Fallback Correlation Strategies
For cases where Copilot doesn't call the completion tool with the execution ID:

```typescript
class CompletionCorrelator {
  // Strategy 1: Temporal correlation (most recent active execution)
  correlateByTime(): ActiveExecution | null {
    const activeExecutions = this.executionRegistry.getActiveExecutions();
    if (activeExecutions.length === 1) {
      return activeExecutions[0]; // Only one active, must be it
    }
    // Return most recent if multiple
    return activeExecutions.sort((a, b) => 
      b.startTime.getTime() - a.startTime.getTime()
    )[0] || null;
  }

  // Strategy 2: Content correlation (task description similarity)
  correlateByContent(completionTaskDescription: string): ActiveExecution | null {
    const activeExecutions = this.executionRegistry.getActiveExecutions();
    
    for (const execution of activeExecutions) {
      if (this.isSimilarTask(execution.taskDescription, completionTaskDescription)) {
        return execution;
      }
    }
    return null;
  }

  private isSimilarTask(original: string, completion: string): boolean {
    // Simple similarity check - could be enhanced with fuzzy matching
    const originalWords = original.toLowerCase().split(/\s+/);
    const completionWords = completion.toLowerCase().split(/\s+/);
    
    const commonWords = originalWords.filter(word => 
      completionWords.includes(word) && word.length > 3
    );
    
    return commonWords.length >= Math.min(originalWords.length, completionWords.length) * 0.4;
  }
}
```

### Benefits of New Design

1. **Reliable Correlation**: Multiple strategies ensure completion signals can be matched to executions
2. **Graceful Degradation**: Works even if Copilot doesn't preserve execution context
3. **Clear User Instructions**: Copilot gets explicit instructions to call the completion tool
4. **Timeout Handling**: Automatic cleanup of stale executions
5. **Multiple Execution Support**: Can track concurrent executions from different agents

### Implementation Changes Required

1. **ExecutionRegistry**: New central registry for active executions
2. **Enhanced Prompt Injection**: Modify prompt enhancement to include execution instructions
3. **Fallback Correlation**: Add correlation strategies to completion signal tool
4. **Timeout Management**: Add automatic cleanup of stale executions
5. **UI Updates**: Update agent panel to show execution states more reliably

### Migration Path

1. Implement ExecutionRegistry
2. Update AgentPanelProvider to use registry and enhanced prompts
3. Update CopilotCompletionSignalTool to support correlation strategies
4. Add timeout and cleanup mechanisms
5. Update UI to reflect new execution states
6. Add configuration for timeout values and correlation strategies

This design solves the fundamental correlation problem while maintaining the Wu Wei philosophy of natural, effortless operation.
