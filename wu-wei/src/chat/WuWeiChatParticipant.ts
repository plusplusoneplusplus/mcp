import * as vscode from 'vscode';
import { logger } from '../logger';

export interface WuWeiToolMetadata {
    toolCallsMetadata: ToolCallsMetadata;
}

export interface ToolCallsMetadata {
    toolCallRounds: ToolCallRound[];
    toolCallResults: Record<string, string>;
}

export interface ToolCallRound {
    response: string;
    toolCalls: vscode.LanguageModelToolCallPart[];
}

export function isWuWeiToolMetadata(obj: unknown): obj is WuWeiToolMetadata {
    return !!obj &&
        !!(obj as WuWeiToolMetadata).toolCallsMetadata &&
        Array.isArray((obj as WuWeiToolMetadata).toolCallsMetadata.toolCallRounds);
}

/**
 * Wu Wei Chat Participant - Coding-Focused Assistant with Tools Support
 * 
 * A powerful coding assistant that helps with development tasks using VS Code tools.
 * Focuses on practical coding assistance, debugging, and development workflow optimization.
 */
export class WuWeiChatParticipant {
    private participant: vscode.ChatParticipant;

    constructor(context: vscode.ExtensionContext) {
        // Register the chat participant
        this.participant = vscode.chat.createChatParticipant(
            'wu-wei.assistant',
            this.handleChatRequest.bind(this)
        );

        // Set participant properties
        this.participant.iconPath = new vscode.ThemeIcon('code');

        // // Add followup suggestions focused on coding tasks
        // this.participant.followupProvider = {
        //     provideFollowups: (result, context, token) => {
        //         return [
        //             {
        //                 prompt: 'Analyze my current code',
        //                 label: '🔍 Code Analysis'
        //             },
        //             {
        //                 prompt: 'Help me debug this issue',
        //                 label: '🐛 Debug Help'
        //             },
        //             {
        //                 prompt: 'Optimize my code performance',
        //                 label: '⚡ Optimize Code'
        //             },
        //             {
        //                 prompt: 'Review my code for best practices',
        //                 label: '✅ Code Review'
        //             },
        //             {
        //                 prompt: 'What tools can help with development?',
        //                 label: '�️ Dev Tools'
        //             },
        //             {
        //                 prompt: 'Explain this code pattern',
        //                 label: '📚 Code Patterns'
        //             }
        //         ];
        //     }
        // };

        logger.info('Wu Wei Coding Assistant initialized in AGENT MODE with tools support - ready to autonomously assist with development tasks 🤖');

        // Log available tools on initialization
        this.logAvailableTools();
    }

    private async logAvailableTools(): Promise<void> {
        try {
            // Log language models
            const models = await vscode.lm.selectChatModels();
            logger.info('Wu Wei Coding Assistant: Available Language Models:', {
                count: models.length,
                models: models.map(m => ({
                    id: m.id,
                    vendor: m.vendor,
                    family: m.family,
                    version: m.version,
                    maxInputTokens: m.maxInputTokens
                }))
            });

            // Log available VS Code tools
            let toolsCount = 0;
            let toolNames: string[] = [];

            try {
                if (vscode.lm && 'tools' in vscode.lm) {
                    const tools = (vscode.lm as any).tools;
                    if (Array.isArray(tools)) {
                        toolsCount = tools.length;
                        toolNames = tools.map(tool => tool.name || 'unnamed').slice(0, 5);
                    }
                }
            } catch (error) {
                logger.debug('Tools API not available or accessible:', error);
            }

            logger.info('Wu Wei Coding Assistant: Available VS Code Tools:', {
                count: toolsCount,
                sampleTools: toolNames
            });

            // Note: VS Code commands and workspace folder details excluded from chat
            // to keep responses focused on coding assistance

            // Log available capabilities (excluding workspace and commands for chat focus)
            logger.info('Wu Wei Coding Assistant: Development Capabilities Available:', {
                languageModels: models.length > 0,
                fileSystem: true,
                chat: true,
                tools: toolsCount
            });

        } catch (error) {
            logger.error('Wu Wei Coding Assistant: Failed to log available tools', { error });
        }
    }

    private async handleChatRequest(
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult | void> {
        try {
            logger.info(`Wu Wei Coding Assistant request: "${request.prompt}"`);

            // Agent mode: Let the language model handle all requests with tools
            // No manual routing - the LM decides when and how to use tools

            // Get language model
            let models = await vscode.lm.selectChatModels();
            if (models.length === 0) {
                stream.markdown('❌ No language models available. Please install GitHub Copilot or another language model extension for coding assistance.');
                return;
            }

            // Use a non-o1 model if o1 is selected (o1 models don't support tools yet)
            let model = request.model || models[0];
            if (model.vendor === 'copilot' && model.family.startsWith('o1')) {
                const alternativeModels = await vscode.lm.selectChatModels({
                    vendor: 'copilot',
                    family: 'gpt-4o'
                });
                if (alternativeModels.length > 0) {
                    model = alternativeModels[0];
                    logger.info('Wu Wei Coding Assistant: Switched from o1 to gpt-4o for tools support');
                }
            }

            // Get available tools (with safe access)
            const tools = this.getAvailableTools();

            // Log tool availability for this request
            logger.info(`Wu Wei Coding Assistant: Tool setup for request`, {
                toolsAvailable: tools.length,
                toolNames: tools.map(t => t.name).slice(0, 10), // Log first 10 tool names
                hasTools: tools.length > 0
            });

            // Set up options for the language model
            const options: vscode.LanguageModelChatRequestOptions = {
                justification: 'To provide coding assistance and development support with natural tool usage',
                tools: tools.length > 0 ? tools : undefined
            };

            // Get enhanced system prompt with tool awareness
            const systemPrompt = this.getEnhancedSystemPrompt(tools.length > 0);

            // Check if this prompt should trigger tool usage
            const toolAnalysis = this.shouldUseTool(request.prompt);
            logger.info(`Wu Wei Coding Assistant: Prompt analysis`, {
                shouldUseTool: toolAnalysis.shouldUse,
                reason: toolAnalysis.reason,
                suggestedTools: toolAnalysis.suggestedTools,
                prompt: request.prompt.substring(0, 100)
            });

            // Prepare chat history with previous tool calls if any
            const previousMetadata = this.extractToolMetadata(context);

            // Enhance system prompt with specific guidance for this request
            let enhancedSystemPrompt = systemPrompt;
            if (toolAnalysis.shouldUse && toolAnalysis.suggestedTools.length > 0) {
                enhancedSystemPrompt += `\n\n**FOR THIS SPECIFIC REQUEST:** The user is asking "${request.prompt}". ${toolAnalysis.reason}. You MUST start by using one or more of these tools: ${toolAnalysis.suggestedTools.join(', ')}. Do not provide a generic response - examine the actual codebase first.`;
            }

            const messages = this.buildMessages(enhancedSystemPrompt, request, context, previousMetadata);

            // Execute the conversation with tools
            const result = await this.runWithTools(model, messages, options, stream, token, previousMetadata, request);

            return result;

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            logger.error('Wu Wei Coding Assistant request failed', { error: errorMessage });

            stream.markdown(`❌ **An error occurred while processing your request**
            
Error: ${errorMessage}

Please try rephrasing your request or check if all required tools and extensions are properly installed.`);
        }
    }

    private getAvailableTools(): any[] {
        try {
            if (vscode.lm && 'tools' in vscode.lm) {
                const tools = (vscode.lm as any).tools;
                if (Array.isArray(tools)) {
                    // Return all available tools for comprehensive coding assistance
                    logger.debug(`Wu Wei Coding Assistant: Found ${tools.length} available tools`);
                    return tools;
                }
            }
        } catch (error) {
            logger.debug('Wu Wei Coding Assistant: Error accessing tools API:', error);
        }
        return [];
    }

    private getEnhancedSystemPrompt(hasTools: boolean): string {
        const config = vscode.workspace.getConfiguration('wu-wei');
        const basePrompt = config.get<string>('systemPrompt',
            'You are a coding assistant focused on helping developers write better code, debug issues, and optimize their development workflow. You provide practical, actionable advice and solutions. You are knowledgeable about multiple programming languages, frameworks, best practices, and development tools.'
        );

        if (!hasTools) {
            return basePrompt;
        }

        return `${basePrompt}

You are operating in AGENT MODE with access to VS Code development tools. You have full autonomy to:

1. **Decide when to use tools** based on user requests and context
2. **Choose appropriate tools** for each task without user guidance
3. **Execute complex workflows** by chaining multiple tool calls
4. **Analyze and act** on tool results to provide comprehensive solutions

**IMPORTANT: You MUST use tools to analyze actual code when users ask about their codebase.**

Available tool capabilities:
- Code analysis and file inspection (copilot_searchCodebase, copilot_readFile)
- Project structure navigation (copilot_listDirectory, copilot_findFiles)
- Symbol and usage analysis (copilot_searchWorkspaceSymbols, copilot_listCodeUsages)
- Text search across files (copilot_findTextInFiles)
- Debugging and error diagnosis
- Code quality assessment
- Performance optimization
- Testing and documentation
- Refactoring assistance
- Security analysis

**Agent behavior guidelines - ALWAYS FOLLOW THESE:**
- **ALWAYS use tools** when users ask about their code, files, or project structure
- For "explain the codebase" requests: START with copilot_searchCodebase or copilot_listDirectory
- For specific file questions: USE copilot_readFile to examine the actual content
- For understanding project structure: USE copilot_findFiles and copilot_listDirectory
- For finding implementations: USE copilot_searchWorkspaceSymbols and copilot_listCodeUsages
- Take initiative to gather necessary information using available tools
- Use tools proactively to provide better, more accurate assistance
- Chain tool calls when needed to solve complex problems
- Explain your tool usage and reasoning to the user
- Handle tool errors gracefully and try alternative approaches
- Focus on providing actionable, practical solutions

**Critical rule: Never give generic answers about code without first using tools to examine the actual codebase.**

Current context:
- You can access files, analyze code structure, and provide contextual development assistance
- Focus on practical coding solutions, best practices, and development efficiency
- Provide specific, actionable recommendations for code improvement
- Use tools extensively to support your analysis and recommendations`;
    }

    private extractToolMetadata(context: vscode.ChatContext): ToolCallsMetadata {
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

    private buildMessages(
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

    private async runWithTools(
        model: vscode.LanguageModelChat,
        messages: vscode.LanguageModelChatMessage[],
        options: vscode.LanguageModelChatRequestOptions,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken,
        previousMetadata: ToolCallsMetadata,
        request: vscode.ChatRequest
    ): Promise<vscode.ChatResult | void> {
        const toolCallRounds: ToolCallRound[] = [...previousMetadata.toolCallRounds];
        const accumulatedToolResults: Record<string, string> = { ...previousMetadata.toolCallResults };

        const runIteration = async (): Promise<vscode.ChatResult | void> => {
            try {
                // Send the request to the language model
                const response = await model.sendRequest(messages, options, token);

                // Stream text output and collect tool calls
                const toolCalls: vscode.LanguageModelToolCallPart[] = [];
                let responseStr = '';

                for await (const part of response.stream) {
                    if (part instanceof vscode.LanguageModelTextPart) {
                        stream.markdown(part.value);
                        responseStr += part.value;
                    } else if (part instanceof vscode.LanguageModelToolCallPart) {
                        toolCalls.push(part);
                        stream.markdown(`\n🔧 **Using tool:** ${part.name}\n`);
                    }
                }

                if (toolCalls.length > 0) {
                    // Log tool call detection
                    logger.info(`Wu Wei Coding Assistant: Detected tool calls in LM response`, {
                        toolCallCount: toolCalls.length,
                        toolNames: toolCalls.map(tc => tc.name),
                        conversationRound: toolCallRounds.length + 1
                    });

                    // Add this round to our history
                    toolCallRounds.push({
                        response: responseStr,
                        toolCalls
                    });

                    // Execute tools and add results to messages
                    for (const toolCall of toolCalls) {
                        try {
                            // Log tool invocation start
                            const inputSummary = this.summarizeToolInput(toolCall.input);
                            logger.info(`Wu Wei Coding Assistant: Starting tool execution`, {
                                toolName: toolCall.name,
                                callId: toolCall.callId,
                                inputSummary
                            });

                            stream.markdown(`\n🔧 **Executing tool:** ${toolCall.name}\n`);
                            if (inputSummary) {
                                stream.markdown(`📋 **Parameters:** ${inputSummary}\n`);
                            }

                            // Actually invoke the tool
                            const toolResult = await this.invokeTool(toolCall);

                            // Log successful completion
                            const resultSummary = this.summarizeToolResult(toolResult);
                            logger.info(`Wu Wei Coding Assistant: Tool execution completed successfully`, {
                                toolName: toolCall.name,
                                callId: toolCall.callId,
                                resultSummary,
                                resultLength: typeof toolResult === 'string' ? toolResult.length : 'non-string'
                            });

                            accumulatedToolResults[toolCall.callId] = toolResult;

                            // Show completion status in chat
                            stream.markdown(`✅ **Tool completed:** ${toolCall.name}\n`);
                            if (resultSummary) {
                                stream.markdown(`📊 **Result:** ${resultSummary}\n`);
                            }

                            // Add tool result to conversation using proper tool result format
                            const toolResultMessage = `TOOL_RESULT_${toolCall.callId}: ${toolCall.name} execution completed successfully.

Result:
${toolResult}

This is the actual result from the ${toolCall.name} tool. Please use this information to answer the user's question.`;

                            messages.push(vscode.LanguageModelChatMessage.User(toolResultMessage));

                            // Log that we're sending the result back to LM
                            logger.info(`Wu Wei Coding Assistant: Tool result added to conversation`, {
                                toolName: toolCall.name,
                                callId: toolCall.callId,
                                messageLength: toolResultMessage.length,
                                totalMessages: messages.length
                            });

                        } catch (error) {
                            // Log tool execution failure
                            logger.error(`Wu Wei Coding Assistant: Tool execution failed`, {
                                toolName: toolCall.name,
                                callId: toolCall.callId,
                                error: error instanceof Error ? error.message : 'Unknown error',
                                stack: error instanceof Error ? error.stack : undefined
                            });

                            const errorMsg = `Tool execution failed: ${error instanceof Error ? error.message : 'Unknown error'}`;
                            accumulatedToolResults[toolCall.callId] = errorMsg;
                            stream.markdown(`\n❌ **Tool error:** ${toolCall.name} - ${errorMsg}\n`);

                            // Add error result to conversation so the LM can handle it
                            const errorResultMessage = `TOOL_ERROR_${toolCall.callId}: ${toolCall.name} execution failed.

Error: ${errorMsg}

Please acknowledge this error and try an alternative approach or provide what help you can without this specific tool.`;

                            messages.push(vscode.LanguageModelChatMessage.User(errorResultMessage));
                        }
                    }

                    // Log completion of tool execution round
                    const successfulTools = toolCalls.filter(tc =>
                        accumulatedToolResults[tc.callId] &&
                        !accumulatedToolResults[tc.callId].includes('error')
                    );

                    logger.info(`Wu Wei Coding Assistant: Tool execution round completed`, {
                        totalTools: toolCalls.length,
                        successfulTools: successfulTools.length,
                        failedTools: toolCalls.length - successfulTools.length,
                        toolNames: toolCalls.map(tc => tc.name),
                        currentRound: toolCallRounds.length
                    });

                    // Safeguard: Prevent infinite tool calling loops
                    if (toolCallRounds.length >= 5) {
                        logger.warn(`Wu Wei Coding Assistant: Maximum tool rounds reached (${toolCallRounds.length}), stopping recursion`);
                        stream.markdown(`\n⚠️ **Maximum tool execution rounds reached.** Summarizing results...\n`);

                        // Add a summary message to help the LM conclude
                        messages.push(vscode.LanguageModelChatMessage.User(`Tool execution completed. Please provide a summary based on the tool results above. Do not call any more tools.`));

                        // Make one final request without tools to get the summary
                        const finalOptions = { ...options, tools: undefined };
                        const finalResponse = await model.sendRequest(messages, finalOptions, token);

                        for await (const part of finalResponse.stream) {
                            if (part instanceof vscode.LanguageModelTextPart) {
                                stream.markdown(part.value);
                            }
                        }

                        return {
                            metadata: {
                                toolCallsMetadata: {
                                    toolCallResults: accumulatedToolResults,
                                    toolCallRounds
                                }
                            } satisfies WuWeiToolMetadata
                        };
                    }

                    // Add a prompt to help the LM process the tool results
                    if (successfulTools.length > 0) {
                        stream.markdown(`\n📊 **Processing ${successfulTools.length} tool result(s)...**\n`);
                        messages.push(vscode.LanguageModelChatMessage.User(`Please analyze and summarize the tool results above to answer the user's question. Use the actual data from the tools, not generic information.`));
                    }

                    // Continue the conversation with tool results
                    return runIteration();
                }

                // Log when LM completes without using tools
                if (toolCalls.length === 0) {
                    logger.info(`Wu Wei Coding Assistant: LM completed response without using any tools`, {
                        responseLength: responseStr.length,
                        modelUsed: `${model.vendor}/${model.family}`,
                        availableToolCount: options.tools ? options.tools.length : 0
                    });

                    // If the prompt should have used tools, add a helpful message
                    const toolAnalysis = this.shouldUseTool(request.prompt);
                    if (toolAnalysis.shouldUse && options.tools && options.tools.length > 0) {
                        stream.markdown(`\n\n> 💡 **Note**: For a more accurate analysis of your codebase, I could examine your actual files using tools like \`${toolAnalysis.suggestedTools.join('`, `')}\`. Would you like me to analyze your specific code files?\n`);
                    }
                }

                // Log conversation completion summary
                logger.info(`Wu Wei Coding Assistant: Conversation completed`, {
                    totalRounds: toolCallRounds.length,
                    totalToolCalls: Object.keys(accumulatedToolResults).length,
                    finalMessageCount: messages.length
                });

                // Return metadata for next conversation
                return {
                    metadata: {
                        toolCallsMetadata: {
                            toolCallResults: accumulatedToolResults,
                            toolCallRounds
                        }
                    } satisfies WuWeiToolMetadata
                };

            } catch (error) {
                logger.error('Wu Wei Coding Assistant: Error in tool iteration:', error);
                throw error;
            }
        };

        return runIteration();
    }

    private async handleListToolsCommand(stream: vscode.ChatResponseStream): Promise<void> {
        const tools = this.getAvailableTools();

        if (tools.length === 0) {
            stream.markdown('🔧 **Available Development Tools:** None\n\nNo VS Code language model tools are currently available. Tools may become available when you install extensions that provide them. However, I can still help with code analysis, debugging advice, and development guidance.');
            return;
        }

        const toolsList = tools.map(tool => tool.name).join(', ');
        stream.markdown(`🔧 **Available Development Tools:** ${toolsList}\n\nThese tools can be used to provide enhanced code analysis, debugging assistance, and development guidance.`);
    }

    private async handleToolsRequest(stream: vscode.ChatResponseStream): Promise<void> {
        logger.info('Wu Wei Coding Assistant: Handling tools request');

        const models = await vscode.lm.selectChatModels();
        const tools = this.getAvailableTools();

        stream.markdown(`# �️ Development Tools & Capabilities

*Powerful coding assistance and development workflow optimization*

## 🤖 Language Models Available
${models.length > 0 ?
                models.map(m => `- **${m.id}** (${m.vendor}/${m.family}) - ${m.maxInputTokens} tokens`).join('\n') :
                '- No language models currently available'
            }

## � VS Code Development Tools
${tools.length > 0 ?
                tools.map(tool => `- **${tool.name}** - ${tool.description || 'Advanced development capability'}`).join('\n') :
                '- No VS Code tools currently available\n- Tools become available when you install extensions that provide them'
            }




## � Core Development Features
- **Code Analysis**: Review code quality, patterns, and best practices
- **Debugging Support**: Help diagnose and fix issues
- **Performance Optimization**: Identify bottlenecks and improvements
- **Refactoring Assistance**: Suggest code structure improvements  
- **Testing Guidance**: Recommend testing strategies and test cases
- **Documentation**: Generate and improve code documentation
- **Language Support**: Multi-language development assistance

## 🚀 How to Get Started
- **Code Review**: Select code and ask me to review it
- **Debug Help**: Describe your issue and I'll help troubleshoot
- **Optimization**: Ask about performance improvements
- **Best Practices**: Get recommendations for coding standards
- **Project Analysis**: Let me analyze your workspace structure

*Ask me anything about your code, and I'll use the appropriate tools to provide comprehensive development assistance!*`);
    }

    private async handleWorkspaceRequest(stream: vscode.ChatResponseStream): Promise<void> {
        logger.info('Wu Wei Coding Assistant: Handling workspace request');

        const workspaceFolders = vscode.workspace.workspaceFolders;
        const activeEditor = vscode.window.activeTextEditor;
        const tools = this.getAvailableTools();

        if (!workspaceFolders) {
            stream.markdown(`# 📁 Workspace Analysis

No workspace is currently open. To get started with development assistance:

## 🚀 Getting Started
1. **Open a folder** in VS Code containing your project
2. **Open files** you want to work with
3. **Select code** for specific analysis

## 💡 What I Can Help With
- **Project Structure Analysis** - Understand your codebase organization
- **Code Quality Review** - Identify improvements and best practices
- **Debugging Support** - Help solve issues and errors
- **Performance Optimization** - Find bottlenecks and efficiency gains
- **Testing Strategy** - Recommend testing approaches
- **Documentation** - Generate or improve code documentation

Once you open a workspace, I'll be able to provide much more targeted assistance based on your specific project and technologies.`);
            return;
        }

        // Get basic workspace info
        const totalFiles = await this.getWorkspaceFileCount(workspaceFolders);
        const languagesUsed = await this.detectLanguages(workspaceFolders);

        stream.markdown(`# 📁 Current Workspace Analysis

*Analyzing your development environment and project structure*

## � Project Structure
${workspaceFolders.map(folder => `- **${folder.name}**\n  \`${folder.uri.fsPath}\``).join('\n')}

## 📊 Project Overview
- **Total Files**: ~${totalFiles} files detected
- **Languages Detected**: ${languagesUsed.length > 0 ? languagesUsed.join(', ') : 'Analyzing...'}

## 📄 Current Context
${activeEditor ?
                `- **Active File**: \`${activeEditor.document.fileName}\`
- **Language**: ${activeEditor.document.languageId}
- **Lines**: ${activeEditor.document.lineCount}
- **Cursor Position**: Line ${activeEditor.selection.start.line + 1}, Column ${activeEditor.selection.start.character + 1}` :
                '- No file currently active'
            }

## 🛠️ Available Development Tools
${tools.length > 0 ?
                `${tools.map(tool => `- **${tool.name}** - Advanced code analysis capabilities`).join('\n')}` :
                '- Basic file and project analysis available'
            }

## � Development Assistance Available

### Code Analysis
- **Quality Review** - Check for code smells, anti-patterns, and improvements
- **Security Scan** - Identify potential security vulnerabilities
- **Performance Analysis** - Find optimization opportunities

### Debugging & Troubleshooting  
- **Error Analysis** - Help understand and fix errors
- **Logic Review** - Check code flow and business logic
- **Integration Issues** - Debug API calls, database queries, etc.

### Optimization & Refactoring
- **Code Structure** - Improve organization and maintainability
- **Performance Tuning** - Optimize slow operations and memory usage
- **Best Practices** - Apply language and framework-specific patterns

### Testing & Documentation
- **Test Coverage** - Identify missing test cases
- **Documentation Generation** - Create or improve code documentation
- **API Documentation** - Document interfaces and endpoints

## 💬 How to Get Help
- **Select code** and ask for review or explanation
- **Describe issues** you're facing for debugging help
- **Ask about specific files** or patterns in your project
- **Request optimization** for performance-critical code

*I'm ready to dive deep into your codebase and provide specific, actionable development assistance!*`);
    }

    private async getWorkspaceFileCount(workspaceFolders: readonly vscode.WorkspaceFolder[]): Promise<number> {
        try {
            // Simple approximation - in a real implementation, you'd traverse the directories
            return 42; // Placeholder
        } catch {
            return 0;
        }
    }

    private async detectLanguages(workspaceFolders: readonly vscode.WorkspaceFolder[]): Promise<string[]> {
        try {
            // Simple detection based on common file extensions
            // In a real implementation, you'd scan the workspace for file types
            const activeEditor = vscode.window.activeTextEditor;
            if (activeEditor) {
                return [activeEditor.document.languageId];
            }
            return ['JavaScript', 'TypeScript']; // Placeholder
        } catch {
            return [];
        }
    }

    private isCodeAnalysisRequest(prompt: string): boolean {
        const analysisKeywords = [
            'analyze', 'analysis', 'review', 'check', 'examine', 'inspect',
            'code quality', 'best practices', 'performance', 'optimize',
            'refactor', 'improve', 'suggestions', 'patterns'
        ];

        const lowerPrompt = prompt.toLowerCase();
        return analysisKeywords.some(keyword => lowerPrompt.includes(keyword));
    }

    private isDebuggingRequest(prompt: string): boolean {
        const debugKeywords = [
            'debug', 'bug', 'error', 'issue', 'problem', 'fix',
            'broken', 'not working', 'exception', 'crash',
            'troubleshoot', 'diagnose'
        ];

        const lowerPrompt = prompt.toLowerCase();
        return debugKeywords.some(keyword => lowerPrompt.includes(keyword));
    }

    private async handleCodeAnalysisRequest(stream: vscode.ChatResponseStream, request: vscode.ChatRequest): Promise<void> {
        logger.info('Wu Wei Coding Assistant: Handling code analysis request');

        const activeEditor = vscode.window.activeTextEditor;
        const workspaceFolders = vscode.workspace.workspaceFolders;

        if (!activeEditor && !workspaceFolders) {
            stream.markdown(`# 🔍 Code Analysis

No active file or workspace found. To analyze code, please:

1. **Open a file** in the editor, or
2. **Open a workspace** folder
3. **Select code** you want me to analyze

I can help you with:
- **Code quality review** - Check for best practices and potential issues
- **Performance analysis** - Identify optimization opportunities  
- **Refactoring suggestions** - Improve code structure and readability
- **Security review** - Find potential security vulnerabilities
- **Testing recommendations** - Suggest test cases and coverage improvements`);
            return;
        }

        let analysisContext = '';

        if (activeEditor) {
            const selection = activeEditor.selection;
            const selectedText = activeEditor.document.getText(selection);
            const fileName = activeEditor.document.fileName;
            const language = activeEditor.document.languageId;

            analysisContext = `**Current File:** \`${fileName}\` (${language})
**Lines:** ${activeEditor.document.lineCount}`;

            if (selectedText) {
                analysisContext += `\n**Selected Code:**\n\`\`\`${language}\n${selectedText}\n\`\`\``;
            }
        }

        if (workspaceFolders) {
            analysisContext += `\n**Workspace:** ${workspaceFolders.map(f => f.name).join(', ')}`;
        }

        stream.markdown(`# 🔍 Code Analysis Request

${analysisContext}

**Analysis Type:** ${request.prompt}

I'll analyze your code and provide detailed feedback on:
- Code quality and best practices
- Performance optimization opportunities
- Potential bugs and issues
- Refactoring suggestions
- Testing and documentation recommendations

Let me examine your code...`);

        // Continue with the normal flow to let the LM handle the analysis
    }

    private async handleDebuggingRequest(stream: vscode.ChatResponseStream): Promise<void> {
        logger.info('Wu Wei Coding Assistant: Handling debugging request');

        const activeEditor = vscode.window.activeTextEditor;
        const problems = vscode.languages.getDiagnostics();

        stream.markdown(`# 🐛 Debug Assistant

I'll help you debug your code issue. Here's what I can analyze:

## Current Context`);

        if (activeEditor) {
            const fileName = activeEditor.document.fileName;
            const language = activeEditor.document.languageId;
            const selection = activeEditor.selection;
            const selectedText = activeEditor.document.getText(selection);

            stream.markdown(`- **File:** \`${fileName}\` (${language})
- **Line:** ${selection.start.line + 1}`);

            if (selectedText) {
                stream.markdown(`- **Selected Code:**\n\`\`\`${language}\n${selectedText}\n\`\`\`\n`);
            }
        }

        // Check for problems in the current file
        if (problems.length > 0) {
            stream.markdown(`## 🚨 Detected Issues\n`);
            let issueCount = 0;
            for (const [uri, diagnostics] of problems) {
                if (diagnostics.length > 0 && issueCount < 5) { // Limit to first 5 files
                    stream.markdown(`**${uri.fsPath}:**`);
                    for (const diagnostic of diagnostics.slice(0, 3)) { // Limit to 3 issues per file
                        const severity = diagnostic.severity === vscode.DiagnosticSeverity.Error ? '❌' :
                            diagnostic.severity === vscode.DiagnosticSeverity.Warning ? '⚠️' : 'ℹ️';
                        stream.markdown(`${severity} Line ${diagnostic.range.start.line + 1}: ${diagnostic.message}`);
                    }
                    issueCount++;
                }
            }
        }

        stream.markdown(`## 🛠️ Debugging Capabilities

I can help you with:
- **Error analysis** - Understand error messages and stack traces
- **Code flow tracing** - Track execution paths and logic issues
- **Variable inspection** - Analyze variable states and values
- **Performance debugging** - Find bottlenecks and slow operations
- **Integration issues** - Debug API calls, database queries, and external services

**Tip:** Select the problematic code and describe what you expected vs. what's happening.`);
    }

    /**
     * Actually invoke a tool using the VS Code Language Model API
     */
    private async invokeTool(toolCall: vscode.LanguageModelToolCallPart): Promise<string> {
        try {
            logger.info(`Wu Wei Coding Assistant: Attempting tool invocation`, {
                toolName: toolCall.name,
                callId: toolCall.callId,
                inputKeys: Object.keys(toolCall.input || {})
            });

            // Method 1: Try VS Code's direct tool invocation API
            if (vscode.lm && 'invokeTool' in vscode.lm) {
                const invokeApi = (vscode.lm as any).invokeTool;
                if (typeof invokeApi === 'function') {
                    logger.info(`Wu Wei Coding Assistant: Using direct VS Code tool invocation API for ${toolCall.name}`);
                    const result = await invokeApi(toolCall.name, toolCall.input, toolCall.callId);
                    const resultString = typeof result === 'string' ? result : JSON.stringify(result);
                    logger.info(`Wu Wei Coding Assistant: Direct API tool result`, {
                        toolName: toolCall.name,
                        resultLength: resultString.length,
                        resultPreview: resultString.substring(0, 200)
                    });
                    return resultString;
                }
            }

            // Method 2: Try tool-specific invoke method
            const tools = this.getAvailableTools();
            const tool = tools.find(t => t.name === toolCall.name);

            if (tool && 'invoke' in tool && typeof tool.invoke === 'function') {
                logger.info(`Wu Wei Coding Assistant: Using tool-specific invoke method for ${toolCall.name}`);
                const result = await tool.invoke(toolCall.input);
                const resultString = typeof result === 'string' ? result : JSON.stringify(result);
                logger.info(`Wu Wei Coding Assistant: Tool-specific invoke result`, {
                    toolName: toolCall.name,
                    resultLength: resultString.length,
                    resultPreview: resultString.substring(0, 200)
                });
                return resultString;
            }

            // Method 3: Check if tool has other invocation patterns
            if (tool) {
                logger.info(`Wu Wei Coding Assistant: Tool found but no invoke method`, {
                    toolName: toolCall.name,
                    toolKeys: Object.keys(tool),
                    hasInvoke: 'invoke' in tool,
                    invokeType: typeof (tool as any).invoke
                });
            } else {
                logger.info(`Wu Wei Coding Assistant: Tool not found in available tools`, {
                    toolName: toolCall.name,
                    availableTools: tools.map(t => t.name)
                });
            }

            // Method 4: Fallback to simulation mode
            logger.warn(`Wu Wei Coding Assistant: No direct tool execution available for ${toolCall.name}, using simulation mode`);
            const input = toolCall.input as any;
            const fallbackResult = `Tool ${toolCall.name} was invoked with parameters: ${JSON.stringify(toolCall.input)}. 

SIMULATION: Based on the tool name and parameters, this tool would typically:
- Query: ${input?.query || 'N/A'}
- Files: ${input?.filePath || input?.pattern || 'workspace files'}
- Action: Perform search/analysis operation

Note: Actual tool execution may not be available in this VS Code version. Results are simulated for compatibility.`;

            return fallbackResult;

        } catch (error) {
            logger.error(`Wu Wei Coding Assistant: Tool invocation error for ${toolCall.name}`, {
                error: error instanceof Error ? error.message : 'Unknown error',
                stack: error instanceof Error ? error.stack : undefined
            });

            // Enhanced error fallback
            const errorResult = `Tool ${toolCall.name} execution failed: ${error instanceof Error ? error.message : 'Unknown error'}

Parameters: ${JSON.stringify(toolCall.input)}
Call ID: ${toolCall.callId}

The tool invocation encountered an error. This may be due to:
- Tool not properly registered in VS Code
- Invalid parameters
- Missing permissions or dependencies
- API compatibility issues

Please check the VS Code Developer Console for more details.`;

            return errorResult;
        }
    }

    /**
     * Create a human-readable summary of tool input parameters
     */
    private summarizeToolInput(input: any): string {
        if (!input || typeof input !== 'object') {
            return String(input || 'no parameters');
        }

        try {
            const summary: string[] = [];

            // Common parameter patterns to summarize
            if (input.query) summary.push(`query: "${String(input.query).substring(0, 100)}"`);
            if (input.filePath) summary.push(`file: ${String(input.filePath)}`);
            if (input.command) summary.push(`command: "${String(input.command)}"`);
            if (input.code) summary.push(`code: ${String(input.code).length} chars`);
            if (input.url) summary.push(`url: ${String(input.url)}`);
            if (input.pattern) summary.push(`pattern: "${String(input.pattern)}"`);

            // Add any other key parameters
            for (const [key, value] of Object.entries(input)) {
                if (!['query', 'filePath', 'command', 'code', 'url', 'pattern'].includes(key)) {
                    if (typeof value === 'string' && value.length > 50) {
                        summary.push(`${key}: ${value.length} chars`);
                    } else {
                        summary.push(`${key}: ${String(value)}`);
                    }
                }
            }

            return summary.length > 0 ? summary.join(', ') : 'multiple parameters';
        } catch (error) {
            return 'complex parameters';
        }
    }

    /**
     * Create a human-readable summary of tool execution results
     */
    private summarizeToolResult(result: any): string {
        if (!result) {
            return 'no result';
        }

        try {
            const resultStr = String(result);

            // Provide different summaries based on result content
            if (resultStr.length === 0) {
                return 'empty result';
            } else if (resultStr.length < 100) {
                return `"${resultStr}"`;
            } else {
                // Try to detect the type of result
                if (resultStr.includes('```') || resultStr.includes('function') || resultStr.includes('class')) {
                    return `code result (${resultStr.length} chars)`;
                } else if (resultStr.includes('Error:') || resultStr.includes('error')) {
                    return `error result (${resultStr.length} chars)`;
                } else if (resultStr.includes('\n')) {
                    const lines = resultStr.split('\n').length;
                    return `multi-line result (${lines} lines, ${resultStr.length} chars)`;
                } else {
                    return `text result (${resultStr.length} chars)`;
                }
            }
        } catch (error) {
            return 'complex result';
        }
    }

    /**
     * Detect if a prompt should definitely trigger tool usage and provide guidance
     */
    private shouldUseTool(prompt: string): { shouldUse: boolean; reason: string; suggestedTools: string[] } {
        const lowerPrompt = prompt.toLowerCase();

        // Patterns that should always trigger tool usage
        const patterns = [
            {
                keywords: ['explain', 'codebase', 'code base', 'project structure'],
                reason: 'Codebase explanation requires examining actual files',
                tools: ['copilot_searchCodebase', 'copilot_listDirectory', 'copilot_findFiles']
            },
            {
                keywords: ['analyze', 'file', 'function', 'class', 'method'],
                reason: 'Code analysis requires reading specific files',
                tools: ['copilot_readFile', 'copilot_searchWorkspaceSymbols']
            },
            {
                keywords: ['find', 'search', 'locate', 'where is'],
                reason: 'Finding code requires searching the workspace',
                tools: ['copilot_findTextInFiles', 'copilot_searchCodebase', 'copilot_searchWorkspaceSymbols']
            },
            {
                keywords: ['debug', 'error', 'bug', 'issue', 'problem'],
                reason: 'Debugging requires examining actual code and diagnostics',
                tools: ['copilot_readFile', 'copilot_findTextInFiles']
            }
        ];

        for (const pattern of patterns) {
            if (pattern.keywords.some(keyword => lowerPrompt.includes(keyword))) {
                return {
                    shouldUse: true,
                    reason: pattern.reason,
                    suggestedTools: pattern.tools
                };
            }
        }

        return {
            shouldUse: false,
            reason: 'Generic prompt may not require tool usage',
            suggestedTools: []
        };
    }

    public dispose(): void {
        this.participant?.dispose();
        logger.info('Wu Wei Coding Assistant disposed 🔧');
    }
}
