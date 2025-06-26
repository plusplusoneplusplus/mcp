# Wu Wei Chat Participant MVP Design

## Overview

This document outlines a minimal viable product (MVP) design for adding a simple VS Code Chat Participant to the existing Wu Wei extension. This will be a "hello world" implementation that demonstrates basic chat participant functionality without complex tooling infrastructure.

## Current State Analysis

### Existing Wu Wei Architecture

The wu-wei extension currently features:
- `UnifiedChatProvider`: Webview-based chat interface
- Language model integration via VS Code's LM API
- Prompt management system
- Agent panel for GitHub Copilot integration

## Design Goals

### Philosophy: Wu Wei (无为而治) - Simplicity First
Following the principle of "effortless action," the MVP should:
- Be simple to implement and understand
- Provide immediate value with minimal complexity
- Serve as a foundation for future enhancements
- Coexist peacefully with existing chat functionality

### MVP Objectives
1. **Basic Chat Participant**: Simple @wu-wei participant that responds to messages
2. **Language Model Integration**: Reuse existing LM setup from UnifiedChatProvider
3. **Minimal Functionality**: Basic conversational AI without tools
4. **Foundation for Growth**: Clean architecture for future tool additions

## Architecture Design

### Simple MVP Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    VS Code Chat Interface                      │
│                         (@wu-wei)                              │
├─────────────────────────────────────────────────────────────────┤
│                  Wu Wei Chat Participant                       │
│              (WuWeiChatParticipant.ts)                        │
├─────────────────────────────────────────────────────────────────┤
│                    Existing Wu Wei Core                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Language Models │  │    Logger       │  │ Unified Chat    │ │
│  │   (Reused)      │  │   (Reused)      │  │  (Existing)     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Core Component

#### Wu Wei Chat Participant (MVP)

**Purpose**: Minimal chat participant that provides basic AI conversation

**Features**:
- Responds to @wu-wei mentions in VS Code chat
- Uses existing language model integration from UnifiedChatProvider
- Provides simple conversational AI responses
- Includes basic error handling and logging

## MVP Implementation

### Single File Implementation

The entire MVP can be implemented in a single file that integrates with the existing extension:

```typescript
// src/chat/WuWeiChatParticipant.ts
import * as vscode from 'vscode';
import { logger } from '../logger';

export class WuWeiChatParticipant {
    private participant: vscode.ChatParticipant;

    constructor(context: vscode.ExtensionContext) {
        // Register the chat participant
        this.participant = vscode.chat.createChatParticipant(
            'wu-wei.assistant', 
            this.handleChatRequest.bind(this)
        );
        
        // Set participant properties
        this.participant.iconPath = vscode.Uri.joinPath(
            context.extensionUri, 
            'assets/wu-wei-icon.png'
        );
        
        this.participant.followupProvider = {
            provideFollowups: (result, context, token) => {
                return [
                    {
                        prompt: 'Tell me about Wu Wei philosophy',
                        label: '🧘 Wu Wei Philosophy'
                    },
                    {
                        prompt: 'Help me with my current workspace',
                        label: '🏗️ Workspace Help'
                    }
                ];
            }
        };

        logger.info('Wu Wei Chat Participant initialized');
    }

    private async handleChatRequest(
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<void> {
        try {
            logger.info(`Chat request received: ${request.prompt}`);
            
            // Get language model (reuse existing logic from UnifiedChatProvider)
            const models = await vscode.lm.selectChatModels();
            if (models.length === 0) {
                stream.markdown('❌ No language models available. Please install GitHub Copilot or another language model extension.');
                return;
            }

            // Prepare system message with Wu Wei philosophy
            const systemMessage = vscode.LanguageModelChatMessage.User(
                'You are Wu Wei, an AI assistant that embodies the philosophy of 无为而治 (wu wei) - effortless action that flows naturally like water. You provide thoughtful, gentle guidance while maintaining harmony and balance. Your responses are wise, concise, and flow naturally without forcing solutions.'
            );

            // Prepare user message
            const userMessage = vscode.LanguageModelChatMessage.User(request.prompt);

            // Send request to language model
            const chatResponse = await models[0].sendRequest(
                [systemMessage, userMessage], 
                {}, 
                token
            );

            // Stream the response
            for await (const fragment of chatResponse.text) {
                stream.markdown(fragment);
            }

            logger.info('Chat response completed');

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            logger.error('Chat request failed', { error: errorMessage });
            stream.markdown(`❌ Error: ${errorMessage}`);
        }
    }

    public dispose(): void {
        // Cleanup if needed
        logger.info('Wu Wei Chat Participant disposed');
    }
}
```

### Integration with Extension

Add to `src/extension.ts`:

```typescript
// Add import
import { WuWeiChatParticipant } from './chat/WuWeiChatParticipant';

// In activate function, add:
export function activate(context: vscode.ExtensionContext) {
    // ...existing code...

    // Initialize chat participant
    const chatParticipant = new WuWeiChatParticipant(context);
    context.subscriptions.push(chatParticipant);

    // ...rest of existing code...
}
```

## Implementation Plan

### Single Phase Implementation (1 week)

**Day 1-2: Core Implementation**
- Create `WuWeiChatParticipant.ts` file
- Implement basic chat participant registration
- Add simple request/response handling
- Integrate with existing language model setup

**Day 3-4: Integration & Testing**
- Add participant to main extension activation
- Test with VS Code chat interface
- Basic error handling and logging
- Simple followup suggestions

**Day 5: Polish & Documentation**
- Add participant icon
- Update package.json if needed
- Basic user documentation
- Testing with different language models

### Configuration Changes

Update `package.json` to include chat participant contribution (if needed):

```json
{
  "contributes": {
    "chatParticipants": [
      {
        "id": "wu-wei.assistant",
        "name": "wu-wei",
        "description": "Wu Wei assistant for effortless development",
        "isSticky": true
      }
    ]
  }
}
```

## Testing the MVP

### Manual Testing Steps

1. **Basic Functionality**:
   - Open VS Code chat panel
   - Type `@wu-wei hello` and verify response
   - Test various prompts and questions
   - Verify Wu Wei personality in responses

2. **Error Handling**:
   - Test with no language models available
   - Test with network issues
   - Verify error messages are user-friendly

3. **Integration**:
   - Ensure existing webview chat still works
   - Verify both chat interfaces can coexist
   - Test with different language model extensions

### Success Criteria

- ✅ Chat participant appears in VS Code chat
- ✅ Responds to @wu-wei mentions
- ✅ Uses Wu Wei philosophy in responses
- ✅ Handles errors gracefully
- ✅ Doesn't break existing functionality
- ✅ Works with available language models

## Future Enhancements (Post-MVP)

Once the basic chat participant is working, future versions could add:

### Phase 2: Basic Tools (Optional)
- Simple workspace information (file count, project type)
- Basic prompt search integration
- Current file/selection context

### Phase 3: Advanced Features (Optional)
- Custom tool registration system
- Integration with existing Agent Panel
- Advanced context awareness

### Example Future Tool Integration

```typescript
// Future enhancement - not in MVP
private async handleSimpleCommands(prompt: string): Promise<string> {
    if (prompt.toLowerCase().includes('workspace info')) {
        const workspaceRoot = vscode.workspace.workspaceFolders?.[0];
        if (workspaceRoot) {
            return `📁 Workspace: ${workspaceRoot.name} at ${workspaceRoot.uri.fsPath}`;
        }
    }
    
    if (prompt.toLowerCase().includes('current file')) {
        const activeEditor = vscode.window.activeTextEditor;
        if (activeEditor) {
            return `📄 Current file: ${activeEditor.document.fileName}`;
        }
    }
    
    return null; // Fall back to AI response
}
```

## Benefits of the MVP Approach

### Immediate Value
- Users can interact with Wu Wei through native VS Code chat
- Provides familiar @mention experience
- Maintains Wu Wei's philosophical approach
- Works alongside existing webview chat

### Foundation for Growth
- Clean, simple architecture
- Easy to extend with tools later
- Reuses existing language model integration
- Follows VS Code's chat participant patterns

### Low Risk
- Minimal code changes to existing extension
- No breaking changes to current functionality
- Easy to remove or disable if needed
- Simple debugging and maintenance

## Conclusion

This MVP design provides a simple, effective way to add VS Code chat participant functionality to Wu Wei. By focusing on the core conversational experience and reusing existing infrastructure, we can deliver value quickly while maintaining the extension's philosophy of effortless action.

The implementation requires minimal code (approximately 100 lines) and can be completed in a week. It serves as a solid foundation for future enhancements while providing immediate benefits to users who prefer the native VS Code chat interface.
