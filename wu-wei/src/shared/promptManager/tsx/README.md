# TSX Prompt Components

This module provides reusable TSX components for composing prompts with priority-based message composition and token budgeting. These components replace the string concatenation approach with a more sophisticated prompt composition system.

## Overview

The TSX prompt components are built on top of `@vscode/prompt-tsx` and provide:

- **Priority-based composition**: Messages are ordered and pruned based on priority levels
- **Token budgeting**: Automatic token management to stay within limits
- **Type safety**: Full TypeScript support with proper interfaces
- **Reusability**: Modular components that can be composed together
- **Sanitization**: Built-in content sanitization and validation

## Components

### AgentPrompt

The main orchestrating component that combines all message types with intelligent token management.

```tsx
import { AgentPrompt } from '../promptManager/tsx';

// Basic usage
<AgentPrompt
    systemPrompt="You are a helpful assistant."
    userInput="How can I help you today?"
    maxTokens={4000}
/>

// With conversation history and context
<AgentPrompt
    systemPrompt="You are a helpful assistant."
    userInput="What's the weather like?"
    conversationHistory={[
        { role: 'user', content: 'Hello', id: '1' },
        { role: 'assistant', content: 'Hi there!', id: '2' }
    ]}
    contextData="Current location: San Francisco, CA"
    maxTokens={4000}
    priorityStrategy={{
        systemInstructions: 100,
        userQuery: 90,
        conversationHistory: 80,
        contextData: 70
    }}
/>
```

### SystemInstructionMessage

High-priority system prompts that are always included and cannot be pruned.

```tsx
import { SystemInstructionMessage } from '../promptManager/tsx';

<SystemInstructionMessage priority={100}>
    You are a helpful AI assistant specialized in software development.
    Always provide clear, accurate, and helpful responses.
</SystemInstructionMessage>
```

### UserQueryMessage

User input messages with high priority, rarely pruned from conversations.

```tsx
import { UserQueryMessage } from '../promptManager/tsx';

<UserQueryMessage 
    priority={90}
    timestamp={new Date()}
>
    How do I implement a binary search algorithm in Python?
</UserQueryMessage>
```

### ConversationHistoryMessages

Chat history with configurable priority and message limits.

```tsx
import { ConversationHistoryMessages } from '../promptManager/tsx';

<ConversationHistoryMessages
    history={conversationHistory}
    priority={80}
    maxMessages={5}
    includeTimestamps={true}
/>
```

### ContextDataMessage

Flexible context data with token allocation and labeling.

```tsx
import { ContextDataMessage } from '../promptManager/tsx';

<ContextDataMessage
    priority={70}
    flexGrow={1}
    label="Code Context"
    maxTokens={1000}
>
    {codeSnippet}
</ContextDataMessage>
```

## Priority Strategy

The priority system determines which messages are included when token limits are reached:

- **Priority 100**: System instructions (always included)
- **Priority 90**: Current user query (high importance)
- **Priority 80**: Recent conversation history (medium importance)
- **Priority 70**: Additional context data (flexible, can be pruned)

```typescript
const customPriorities: PriorityStrategy = {
    systemInstructions: 100,
    userQuery: 95,
    conversationHistory: 85,
    contextData: 60
};
```

## Token Management

The components automatically manage token budgets:

1. **Reserved tokens**: System prompts and user queries (high priority)
2. **Flexible tokens**: History and context data (can be pruned/truncated)
3. **Smart allocation**: Distributes available tokens based on priorities

```typescript
// Token budget is calculated automatically
const tokenBudget = {
    total: 4000,
    reserved: 500,  // System + user query
    flexible: 3500  // Available for history + context
};
```

## Usage Examples

### Basic Agent Interaction

```tsx
import { AgentPrompt } from '../promptManager/tsx';

function createBasicPrompt(userQuery: string) {
    return (
        <AgentPrompt
            systemPrompt="You are a helpful assistant."
            userInput={userQuery}
            maxTokens={2000}
        />
    );
}
```

### Advanced Conversation

```tsx
import { AgentPrompt, ChatMessage } from '../promptManager/tsx';

function createConversationPrompt(
    userQuery: string,
    history: ChatMessage[],
    codeContext?: string
) {
    return (
        <AgentPrompt
            systemPrompt="You are an expert software developer. Help with coding questions."
            userInput={userQuery}
            conversationHistory={history}
            contextData={codeContext}
            maxTokens={8000}
            priorityStrategy={{
                systemInstructions: 100,
                userQuery: 95,
                conversationHistory: 80,
                contextData: 65
            }}
        />
    );
}
```

### Custom Component Composition

```tsx
import { 
    SystemInstructionMessage, 
    UserQueryMessage, 
    ContextDataMessage 
} from '../promptManager/tsx';

function createCustomPrompt() {
    return (
        <>
            <SystemInstructionMessage priority={100}>
                You are a code review assistant.
            </SystemInstructionMessage>
            
            <ContextDataMessage 
                priority={80}
                label="Code to Review"
                maxTokens={2000}
            >
                {sourceCode}
            </ContextDataMessage>
            
            <UserQueryMessage priority={90}>
                Please review this code for potential issues.
            </UserQueryMessage>
        </>
    );
}
```

## Utilities

### PromptHelpers

Utility functions for token management and content processing:

```typescript
import { PromptHelpers } from '../promptManager/tsx';

// Estimate token count
const tokens = PromptHelpers.estimateTokenCount(text);

// Truncate to fit token limit
const truncated = PromptHelpers.truncateToTokenLimit(text, 500);

// Format conversation history
const formatted = PromptHelpers.formatConversationHistory(messages, 5);

// Validate component props
const errors = PromptHelpers.validatePromptProps(props, ['required1', 'required2']);

// Sanitize content
const clean = PromptHelpers.sanitizeContent(userInput);
```

## Integration with Existing Code

### Replacing String Concatenation

**Before:**
```typescript
const prompt = `System: ${systemPrompt}\n\nUser: ${userInput}`;
```

**After:**
```tsx
<AgentPrompt
    systemPrompt={systemPrompt}
    userInput={userInput}
/>
```

### Agent Panel Provider Integration

```typescript
import { AgentPrompt, ChatMessage } from '../shared/promptManager/tsx';

class AgentPanelProvider {
    private createPrompt(userInput: string, context?: string): JSX.Element {
        return (
            <AgentPrompt
                systemPrompt={this.getSystemPrompt()}
                userInput={userInput}
                conversationHistory={this._messageHistory}
                contextData={context}
                maxTokens={4000}
            />
        );
    }
}
```

## Testing

The PromptHelpers functionality is tested using Mocha unit tests. To run the tests:

```bash
npm run test:unit
```

The tests are located in `src/test/unit/shared/promptHelpers.test.ts` and cover all utility functions including token estimation, text truncation, message formatting, and content validation.

## Best Practices

1. **Use appropriate priorities**: Reserve high priorities for critical content
2. **Set reasonable token limits**: Consider your model's context window
3. **Validate props**: Use built-in validation for required properties
4. **Sanitize content**: Always sanitize user input and external data
5. **Test token budgets**: Verify your prompts fit within expected limits

## Migration Guide

To migrate from string concatenation to TSX components:

1. Replace concatenated strings with component composition
2. Define priority strategies for your use cases
3. Set appropriate token limits based on your models
4. Add proper TypeScript types for better development experience
5. Test with various input sizes to ensure proper token management

## Future Enhancements

- Dynamic priority adjustment based on content importance
- Advanced token estimation using actual model tokenizers
- Support for streaming and incremental prompt composition
- Integration with VS Code's language model APIs
- Performance optimizations for large conversation histories 