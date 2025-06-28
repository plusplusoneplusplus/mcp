# @vscode/prompt-tsx Setup Documentation

## Overview

This document describes the configuration and setup of Microsoft's `@vscode/prompt-tsx` package in the Wu Wei VS Code extension. The package enables sophisticated prompt composition using TSX components instead of basic string concatenation.

## Installation

The `@vscode/prompt-tsx` package has been installed via npm:

```bash
npm install --save @vscode/prompt-tsx
```

**Current Version:** `^0.4.0-alpha.5`

## TypeScript Configuration

The `tsconfig.json` has been updated with the necessary configuration to support TSX compilation:

```json
{
  "compilerOptions": {
    "jsx": "react",
    "jsxFactory": "vscpp",
    "jsxFragmentFactory": "vscppf",
    // ... other options
  }
}
```

### Key Configuration Points

- **jsx**: Set to `"react"` (not `"react-jsx"`)
- **jsxFactory**: Set to `"vscpp"` (VS Code Prompt TSX factory)
- **jsxFragmentFactory**: Set to `"vscppf"` (VS Code Prompt TSX fragment factory)

## Basic Usage

### Creating Prompt Components

```tsx
import {
    BasePromptElementProps,
    PromptElement,
    SystemMessage,
    UserMessage,
    TextChunk
} from '@vscode/prompt-tsx';

export interface MyPromptProps extends BasePromptElementProps {
    userQuery: string;
    includeInstructions?: boolean;
}

export class MyPrompt extends PromptElement<MyPromptProps> {
    render() {
        return (
            <>
                {this.props.includeInstructions && (
                    <SystemMessage priority={100}>
                        You are Wu Wei, an AI assistant.
                    </SystemMessage>
                )}
                <UserMessage priority={50}>
                    {this.props.userQuery}
                </UserMessage>
            </>
        );
    }
}
```

### Advanced Features

#### Flexible Text Handling

```tsx
<UserMessage priority={75}>
    Context information:
    <br />
    <TextChunk priority={60} flexGrow={1}>
        {contextData}
    </TextChunk>
</UserMessage>
```

#### Async Preparation

```tsx
export class AsyncPrompt extends PromptElement<Props, State> {
    async prepare(): Promise<State> {
        // Async work here
        return {
            timestamp: new Date().toISOString(),
            systemInfo: await getSystemInfo()
        };
    }

    render(state: State, sizing: PromptSizing) {
        return (
            <SystemMessage>
                System: {state.systemInfo}
                <br />
                Timestamp: {state.timestamp}
            </SystemMessage>
        );
    }
}
```

## Testing

Basic test components have been created in `src/test/promptTsx/` to verify the configuration:

- **BasicTestPrompt**: Simple system/user message test
- **TestPromptWithFlex**: Demonstrates flexible text handling and priorities  
- **AsyncTestPrompt**: Shows async preparation with state management

To test the configuration:

```bash
npm run compile
node -e "const { testTsxCompilation } = require('./out/test/promptTsx/basicTsxTest.js'); console.log(testTsxCompilation());"
```

## Key Benefits

1. **Intelligent Prioritization**: Components can have priority levels that determine pruning order when context window limits are reached
2. **Flexible Text Handling**: `TextChunk` components can grow to fill available token budget
3. **Clean Composition**: TSX syntax makes prompt composition more readable than string concatenation
4. **Type Safety**: Full TypeScript support with proper component interfaces
5. **Async Support**: Components can perform async preparation work

## Integration with Wu Wei

The @vscode/prompt-tsx package is now ready for integration with Wu Wei's chat participant and prompt management system. Future implementations can leverage:

- Chat participant prompt generation
- Prompt store template rendering
- Context-aware prompt adaptation
- Token budget management

## References

- [VS Code Prompt TSX Documentation](https://code.visualstudio.com/api/extension-guides/prompt-tsx)
- [Package README](./node_modules/@vscode/prompt-tsx/README.md)
- [Example Components](./node_modules/@vscode/prompt-tsx/examples/)
