import * as vscode from 'vscode';
import { ToolCallsMetadata, isWuWeiToolMetadata } from './types';

/**
 * Builds and manages chat messages and tool call metadata
 */
export class MessageBuilder {
    /**
     * Extract tool metadata from chat context
     */
    extractToolMetadata(context: vscode.ChatContext): ToolCallsMetadata {
        // Look for previous tool metadata in chat history
        for (const turn of context.history) {
            if (turn instanceof vscode.ChatRequestTurn) {
                // Try to access metadata if available (VS Code API may vary)
                const turnWithMetadata = turn as any;
                if (turnWithMetadata.metadata && isWuWeiToolMetadata(turnWithMetadata.metadata)) {
                    return turnWithMetadata.metadata.toolCallsMetadata;
                }
            }
        }
        return { toolCallRounds: [], toolCallResults: {} };
    }

    /**
     * Build complete message array for the language model
     */
    buildMessages(
        systemPrompt: string,
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        previousMetadata: ToolCallsMetadata
    ): vscode.LanguageModelChatMessage[] {
        const messages: vscode.LanguageModelChatMessage[] = [];

        // Add system message
        messages.push(vscode.LanguageModelChatMessage.User(systemPrompt));

        // Add chat history
        for (const turn of context.history) {
            if (turn instanceof vscode.ChatRequestTurn) {
                const commandText = turn.command ? `\n**Command:** ${turn.command}` : '';
                messages.push(vscode.LanguageModelChatMessage.User(`**User:** ${turn.prompt}${commandText}`));
            } else if (turn instanceof vscode.ChatResponseTurn) {
                const responseText = turn.response.map(part =>
                    part instanceof vscode.ChatResponseMarkdownPart ? part.value.value : ''
                ).join('');
                messages.push(vscode.LanguageModelChatMessage.Assistant(responseText));
            }
        }

        // Add tool call rounds from metadata
        for (const round of previousMetadata.toolCallRounds) {
            messages.push(vscode.LanguageModelChatMessage.Assistant(round.response));

            for (const toolCall of round.toolCalls) {
                const cachedResult = previousMetadata.toolCallResults[toolCall.callId];
                if (cachedResult) {
                    messages.push(vscode.LanguageModelChatMessage.User(`Tool result: ${cachedResult}`));
                }
            }
        }

        // Add current user message
        const commandText = request.command ? `\n**Command:** ${request.command}` : '';
        messages.push(vscode.LanguageModelChatMessage.User(`**User:** ${request.prompt}${commandText}`));

        return messages;
    }

    /**
     * Get enhanced system prompt with tool awareness
     */
    getEnhancedSystemPrompt(basePrompt: string, hasTools: boolean): string {
        if (!hasTools) {
            return basePrompt;
        }

        return `${basePrompt}

**TOOL USAGE GUIDELINES:**
- You have access to powerful VS Code development tools
- Use tools proactively to examine actual code when users ask about their codebase
- Always prefer tool results over generic advice
- When users ask about their code, files, or workspace, start by using appropriate tools to gather real information
- Tools available include: file reading, workspace searching, code analysis, and more`;
    }
}
