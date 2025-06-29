import * as vscode from 'vscode';
import { logger } from '../../logger';
import {
    ToolWorkflowResult,
    ToolCallRound,
    ToolWorkflowMetadata,
    ToolError,
    ToolParticipantConfig,
    DEFAULT_TOOL_PARTICIPANT_CONFIG
} from './types';
import { ToolResultManager } from './ToolResultManager';
import { PromptTemplateEngine } from './PromptTemplateEngine';
import { ErrorRecoveryEngine } from './ErrorRecoveryEngine';

/**
 * Orchestrates complex tool calling workflows
 */
export class ToolCallOrchestrator {
    private config: ToolParticipantConfig;
    private toolResultManager: ToolResultManager;
    private promptTemplateEngine: PromptTemplateEngine;
    private errorRecoveryEngine: ErrorRecoveryEngine;

    constructor(
        config: Partial<ToolParticipantConfig> = {},
        toolResultManager?: ToolResultManager,
        promptTemplateEngine?: PromptTemplateEngine
    ) {
        this.config = { ...DEFAULT_TOOL_PARTICIPANT_CONFIG, ...config };
        this.toolResultManager = toolResultManager || new ToolResultManager(this.config.enableCaching);
        this.promptTemplateEngine = promptTemplateEngine || new PromptTemplateEngine();
        this.errorRecoveryEngine = new ErrorRecoveryEngine(this.config);
    }

    /**
     * Execute a complete tool workflow
     */
    async executeWorkflow(
        model: vscode.LanguageModelChat,
        messages: vscode.LanguageModelChatMessage[],
        options: vscode.LanguageModelChatRequestOptions,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken,
        userIntent: string
    ): Promise<ToolWorkflowResult> {
        const startTime = Date.now();
        const toolCallRounds: ToolCallRound[] = [];
        const toolCallResults: Record<string, vscode.LanguageModelToolResult> = {};
        const errors: ToolError[] = [];

        logger.info('ToolCallOrchestrator: Starting workflow execution', {
            userIntent,
            maxRounds: this.config.maxToolRounds,
            toolsAvailable: options.tools?.length || 0
        });

        try {
            let currentRound = 0;
            let shouldContinue = true;

            while (shouldContinue && currentRound < this.config.maxToolRounds) {
                currentRound++;

                const roundResult = await this.executeRound(
                    model,
                    messages,
                    options,
                    stream,
                    token,
                    currentRound,
                    userIntent,
                    toolCallResults,
                    errors
                );

                if (roundResult.toolCalls.length > 0) {
                    toolCallRounds.push(roundResult);

                    // Build context for error recovery
                    const toolCallContext = {
                        userIntent,
                        availableTools: (options.tools || []).map(tool => ({
                            name: tool.name,
                            description: tool.description,
                            inputSchema: tool.inputSchema || {},
                            tags: []
                        })),
                        conversationHistory: messages,
                        previousResults: toolCallResults,
                        roundNumber: currentRound
                    };

                    // Process tool calls with enhanced error recovery
                    const roundResults = await this.processToolCalls(
                        roundResult.toolCalls,
                        stream,
                        errors,
                        toolCallContext
                    );

                    // Merge results
                    Object.assign(toolCallResults, roundResults);

                    // Add tool results to conversation
                    this.addToolResultsToMessages(messages, roundResults);

                    // Check if we should continue
                    shouldContinue = this.shouldContinueExecution(
                        currentRound,
                        toolCallResults,
                        errors,
                        roundResult.response,
                        toolCallContext
                    );
                } else {
                    // No tools called, workflow complete
                    shouldContinue = false;

                    if (currentRound === 1) {
                        // First round with no tools - add the response as a round
                        toolCallRounds.push(roundResult);
                    }
                }
            }

            // Generate final summary
            const conversationSummary = this.generateConversationSummary(
                toolCallRounds,
                toolCallResults,
                userIntent
            );

            // Extract metadata
            const metadata = this.toolResultManager.extractMetadata(
                toolCallRounds,
                toolCallResults,
                errors,
                startTime
            );

            logger.info('ToolCallOrchestrator: Workflow completed', {
                totalRounds: currentRound,
                toolCallsExecuted: Object.keys(toolCallResults).length,
                errors: errors.length,
                executionTime: Date.now() - startTime
            });

            return {
                toolCallRounds,
                toolCallResults,
                conversationSummary,
                metadata
            };

        } catch (error) {
            logger.error('ToolCallOrchestrator: Workflow execution failed', { error });

            const errorDetails: ToolError = {
                toolName: 'workflow',
                callId: 'orchestrator',
                error: error instanceof Error ? error.message : 'Unknown error',
                timestamp: Date.now(),
                retryCount: 0
            };
            errors.push(errorDetails);

            // Return partial results
            return {
                toolCallRounds,
                toolCallResults,
                conversationSummary: 'Workflow execution failed',
                metadata: this.toolResultManager.extractMetadata(
                    toolCallRounds,
                    toolCallResults,
                    errors,
                    startTime
                )
            };
        }
    }

    /**
     * Execute a single round of tool calling
     */
    private async executeRound(
        model: vscode.LanguageModelChat,
        messages: vscode.LanguageModelChatMessage[],
        options: vscode.LanguageModelChatRequestOptions,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken,
        roundNumber: number,
        userIntent: string,
        previousResults: Record<string, vscode.LanguageModelToolResult>,
        errors: ToolError[]
    ): Promise<ToolCallRound> {
        const roundId = `round-${roundNumber}-${Date.now()}`;

        logger.debug(`ToolCallOrchestrator: Executing round ${roundNumber}`, {
            roundId,
            previousResults: Object.keys(previousResults).length,
            errors: errors.length
        });

        // Add contextual prompt if this is not the first round
        if (roundNumber > 1) {
            const contextPrompt = this.promptTemplateEngine.generateMultiRoundPrompt(
                roundNumber,
                previousResults,
                {
                    userIntent,
                    availableTools: (options.tools || []).map(tool => ({
                        name: tool.name,
                        description: tool.description,
                        inputSchema: tool.inputSchema || {},
                        tags: []
                    })),
                    conversationHistory: messages,
                    previousResults,
                    roundNumber
                }
            );

            messages.push(vscode.LanguageModelChatMessage.User(contextPrompt));
        }

        try {
            // Send request to language model
            const response = await model.sendRequest(messages, options, token);

            // Process response stream
            const toolCalls: vscode.LanguageModelToolCallPart[] = [];
            let responseText = '';

            for await (const part of response.stream) {
                if (part instanceof vscode.LanguageModelTextPart) {
                    stream.markdown(part.value);
                    responseText += part.value;
                } else if (part instanceof vscode.LanguageModelToolCallPart) {
                    toolCalls.push(part);

                    // Show tool usage to user
                    const toolSummary = this.summarizeToolCall(part);
                    stream.markdown(`\n🔧 **Using tool: ${part.name}** (${toolSummary})\n`);
                }
            }

            return {
                response: responseText,
                toolCalls,
                timestamp: Date.now(),
                roundId
            };

        } catch (error) {
            logger.error(`ToolCallOrchestrator: Round ${roundNumber} execution failed`, { error });

            const errorDetails: ToolError = {
                toolName: 'round-execution',
                callId: roundId,
                error: error instanceof Error ? error.message : 'Unknown error',
                timestamp: Date.now(),
                retryCount: 0
            };
            errors.push(errorDetails);

            // Return empty round
            return {
                response: '',
                toolCalls: [],
                timestamp: Date.now(),
                roundId
            };
        }
    }

    /**
     * Process tool calls with caching and enhanced error handling
     */
    private async processToolCalls(
        toolCalls: vscode.LanguageModelToolCallPart[],
        stream: vscode.ChatResponseStream,
        errors: ToolError[],
        context?: any
    ): Promise<Record<string, vscode.LanguageModelToolResult>> {
        const results: Record<string, vscode.LanguageModelToolResult> = {};

        if (this.config.enableParallelExecution && toolCalls.length > 1) {
            // Execute tools in parallel
            const promises = toolCalls.map(toolCall =>
                this.executeToolCallWithRetry(toolCall, errors, context)
            );

            const parallelResults = await Promise.allSettled(promises);

            for (let i = 0; i < toolCalls.length; i++) {
                const result = parallelResults[i];
                const toolCall = toolCalls[i];

                if (result.status === 'fulfilled' && result.value) {
                    results[toolCall.callId] = result.value;
                    this.showToolResult(stream, toolCall.name, result.value);
                } else {
                    logger.warn(`ToolCallOrchestrator: Parallel tool execution failed for ${toolCall.name}`);
                    
                    // Show user-friendly error message with recovery suggestions
                    if (this.config.enableAdvancedErrorRecovery && context) {
                        this.showErrorRecoveryMessage(stream, toolCall.name, errors, context);
                    }
                }
            }
        } else {
            // Execute tools sequentially
            for (const toolCall of toolCalls) {
                try {
                    const result = await this.executeToolCallWithRetry(toolCall, errors, context);
                    if (result) {
                        results[toolCall.callId] = result;
                        this.showToolResult(stream, toolCall.name, result);
                    } else {
                        // Show user-friendly error message with recovery suggestions
                        if (this.config.enableAdvancedErrorRecovery && context) {
                            this.showErrorRecoveryMessage(stream, toolCall.name, errors, context);
                        }
                    }
                } catch (error) {
                    logger.warn(`ToolCallOrchestrator: Sequential tool execution failed for ${toolCall.name}`, { error });
                    
                    // Show user-friendly error message
                    if (this.config.enableAdvancedErrorRecovery && context) {
                        this.showErrorRecoveryMessage(stream, toolCall.name, errors, context);
                    }
                }
            }
        }

        return results;
    }

    /**
     * Execute a single tool call with enhanced retry logic, caching, and error recovery
     */
    private async executeToolCallWithRetry(
        toolCall: vscode.LanguageModelToolCallPart,
        errors: ToolError[],
        context?: any
    ): Promise<vscode.LanguageModelToolResult | null> {
        // Check cache first
        const cachedResult = this.toolResultManager.getCachedResult(toolCall.name, toolCall.input);
        if (cachedResult) {
            logger.debug(`ToolCallOrchestrator: Using cached result for ${toolCall.name}`);
            return cachedResult;
        }

        let lastError: Error | null = null;
        let recoveryAttempts = 0;

        for (let attempt = 0; attempt < this.config.errorRetryAttempts; attempt++) {
            try {
                // Create a timeout promise
                const timeoutPromise = new Promise<never>((_, reject) => {
                    setTimeout(() => reject(new Error('Tool execution timeout')), this.config.toolTimeout);
                });

                // Execute tool with timeout
                const executionPromise = this.executeToolCall(toolCall);
                const result = await Promise.race([executionPromise, timeoutPromise]);

                // Cache successful result
                this.toolResultManager.cacheResult(toolCall.name, toolCall.input, result);

                return result;

            } catch (error) {
                lastError = error instanceof Error ? error : new Error('Unknown error');

                logger.warn(`ToolCallOrchestrator: Tool execution attempt ${attempt + 1} failed for ${toolCall.name}`, {
                    error: lastError.message,
                    attempt: attempt + 1,
                    maxAttempts: this.config.errorRetryAttempts
                });

                // Create tool error for advanced recovery analysis
                const toolError: ToolError = {
                    toolName: toolCall.name,
                    callId: toolCall.callId,
                    error: lastError.message,
                    timestamp: Date.now(),
                    retryCount: attempt + 1
                };

                // Try advanced error recovery if enabled
                if (this.config.enableAdvancedErrorRecovery && context && recoveryAttempts < this.config.maxRecoveryAttempts) {
                    const recoveryResult = await this.attemptErrorRecovery(toolError, context);
                    
                    if (recoveryResult.success && recoveryResult.shouldContinue) {
                        recoveryAttempts++;
                        
                        // If recovery suggests parameter correction, modify the tool call
                        if (recoveryResult.action.strategy === 'parameter_correction') {
                            // Note: In a real implementation, you might modify toolCall.input here
                            logger.info(`ToolCallOrchestrator: Attempting parameter correction for ${toolCall.name}`);
                        }
                        
                        // Continue with retry after recovery
                        continue;
                    } else if (!recoveryResult.shouldContinue) {
                        // Recovery suggests stopping
                        toolError.errorType = recoveryResult.action.strategy;
                        toolError.recoveryAttempts = recoveryAttempts;
                        errors.push(toolError);
                        return null;
                    }
                }

                // Standard exponential backoff before retry
                if (attempt < this.config.errorRetryAttempts - 1) {
                    await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                }
            }
        }

        // All attempts failed, record enhanced error details
        const finalError: ToolError = {
            toolName: toolCall.name,
            callId: toolCall.callId,
            error: lastError?.message || 'Unknown error',
            timestamp: Date.now(),
            retryCount: this.config.errorRetryAttempts,
            recoveryAttempts,
            severity: recoveryAttempts > 0 ? 'high' : 'medium'
        };

        errors.push(finalError);
        return null;
    }

    /**
     * Execute a single tool call (placeholder for actual VS Code API integration)
     */
    private async executeToolCall(
        toolCall: vscode.LanguageModelToolCallPart
    ): Promise<vscode.LanguageModelToolResult> {
        // This is a placeholder implementation
        // In the actual VS Code environment, this would integrate with the real tool execution API

        logger.debug(`ToolCallOrchestrator: Executing tool ${toolCall.name}`, {
            callId: toolCall.callId,
            inputKeys: Object.keys(toolCall.input || {})
        });

        // Simulate tool execution
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve({
                    content: `Tool ${toolCall.name} executed with input: ${JSON.stringify(toolCall.input)}`
                } as any);
            }, 100);
        });
    }

    /**
     * Add tool results to conversation messages
     */
    private addToolResultsToMessages(
        messages: vscode.LanguageModelChatMessage[],
        results: Record<string, vscode.LanguageModelToolResult>
    ): void {
        for (const [callId, result] of Object.entries(results)) {
            const resultSummary = this.toolResultManager.summarizeResults({ [callId]: result });
            messages.push(vscode.LanguageModelChatMessage.User(`Tool result (${callId}): ${resultSummary}`));
        }
    }

    /**
     * Determine if workflow should continue using enhanced error analysis
     */
    private shouldContinueExecution(
        currentRound: number,
        toolCallResults: Record<string, vscode.LanguageModelToolResult>,
        errors: ToolError[],
        lastResponse: string,
        context?: any
    ): boolean {
        // Don't continue if we've reached max rounds
        if (currentRound >= this.config.maxToolRounds) {
            logger.info('ToolCallOrchestrator: Max rounds reached, stopping workflow');
            return false;
        }

        // Enhanced error analysis with recovery engine
        if (this.config.enableAdvancedErrorRecovery && errors.length > 0 && context) {
            const recentErrors = errors.filter(e => Date.now() - e.timestamp < 60000); // Last minute
            
            for (const error of recentErrors) {
                const toolCallContext = {
                    userIntent: context.userIntent || '',
                    availableTools: context.availableTools || [],
                    conversationHistory: context.conversationHistory || [],
                    previousResults: toolCallResults,
                    roundNumber: currentRound
                };

                const shouldContinue = this.errorRecoveryEngine.shouldContinueWorkflow(
                    error,
                    toolCallContext,
                    errors.length
                );

                if (!shouldContinue) {
                    logger.warn('ToolCallOrchestrator: Error recovery engine suggests stopping workflow', {
                        toolName: error.toolName,
                        errorType: error.errorType,
                        totalErrors: errors.length
                    });
                    return false;
                }
            }
        } else {
            // Fallback to basic error checking
            if (errors.length > currentRound * 2) {
                logger.warn('ToolCallOrchestrator: Too many errors, stopping workflow');
                return false;
            }
        }

        // Continue if the response suggests more tool usage is needed
        const responseText = lastResponse.toLowerCase();
        const continueIndicators = ['let me', 'i need to', 'i should', 'next i will', 'i\'ll try'];

        return continueIndicators.some(indicator => responseText.includes(indicator));
    }

    /**
     * Generate conversation summary
     */
    private generateConversationSummary(
        toolCallRounds: ToolCallRound[],
        toolCallResults: Record<string, vscode.LanguageModelToolResult>,
        userIntent: string
    ): string {
        const totalTools = Object.keys(toolCallResults).length;
        const uniqueTools = new Set<string>();

        for (const round of toolCallRounds) {
            for (const toolCall of round.toolCalls) {
                uniqueTools.add(toolCall.name);
            }
        }

        return `Completed workflow for: ${userIntent}
- Executed ${toolCallRounds.length} rounds
- Used ${totalTools} tool calls
- Utilized ${uniqueTools.size} unique tools: ${Array.from(uniqueTools).join(', ')}`;
    }

    /**
     * Summarize a tool call for user display
     */
    private summarizeToolCall(toolCall: vscode.LanguageModelToolCallPart): string {
        try {
            const input = toolCall.input || {};
            const keys = Object.keys(input);

            if (keys.length === 0) {
                return 'no parameters';
            }

            if (keys.length === 1) {
                const value = (input as any)[keys[0]];
                if (typeof value === 'string' && value.length > 50) {
                    return `${keys[0]}: ${value.substring(0, 47)}...`;
                }
                return `${keys[0]}: ${value}`;
            }

            return `${keys.length} parameters`;
        } catch (error) {
            return 'complex parameters';
        }
    }

    /**
     * Show tool result to user
     */
    private showToolResult(
        stream: vscode.ChatResponseStream,
        toolName: string,
        result: vscode.LanguageModelToolResult
    ): void {
        try {
            const summary = this.toolResultManager.summarizeResults({ temp: result });
            stream.markdown(`📄 **${toolName} result:** ${summary}\n\n`);
        } catch (error) {
            stream.markdown(`📄 **${toolName} completed**\n\n`);
        }
    }

    /**
     * Show user-friendly error recovery message
     */
    private showErrorRecoveryMessage(
        stream: vscode.ChatResponseStream,
        toolName: string,
        errors: ToolError[],
        context: any
    ): void {
        const recentError = errors.find(e => e.toolName === toolName);
        
        if (!recentError) {
            stream.markdown(`⚠️ **${toolName} encountered an issue** - Continuing with alternative approach.\n\n`);
            return;
        }

        try {
            // Build tool call context
            const toolCallContext = {
                userIntent: context.userIntent || '',
                availableTools: context.availableTools || [],
                conversationHistory: context.conversationHistory || [],
                previousResults: context.previousResults || {},
                roundNumber: context.roundNumber || 1
            };

            // Get error classification and recovery suggestions
            const classification = this.errorRecoveryEngine.classifyError(recentError, toolCallContext);
            const suggestions = this.errorRecoveryEngine.getRecoverySuggestions(classification, recentError, toolCallContext);

            // Show contextual error message
            stream.markdown(`⚠️ **${toolName} Error Recovery**\n\n`);
            
            if (classification.recoverable) {
                stream.markdown(`The ${toolName} tool encountered an issue, but I can continue with an alternative approach.\n\n`);
                
                if (this.config.fallbackToolSuggestions && suggestions.length > 0) {
                    stream.markdown(`**What happened:** ${suggestions[0]}\n\n`);
                    if (suggestions.length > 1) {
                        stream.markdown(`**Alternative approach:** ${suggestions[1]}\n\n`);
                    }
                }
            } else {
                stream.markdown(`The ${toolName} tool is currently unavailable.\n\n`);
                suggestions.forEach(suggestion => {
                    stream.markdown(`• ${suggestion}\n`);
                });
                stream.markdown('\n');
            }

        } catch (error) {
            // Fallback to simple error message
            stream.markdown(`⚠️ **${toolName} is currently unavailable** - Continuing with alternative approach.\n\n`);
        }
    }

    /**
     * Attempt advanced error recovery for a failed tool call
     */
    private async attemptErrorRecovery(
        error: ToolError,
        context: any
    ): Promise<any> {
        try {
            // Build tool call context for error recovery
            const toolCallContext = {
                userIntent: context.userIntent || '',
                availableTools: context.availableTools || [],
                conversationHistory: context.conversationHistory || [],
                previousResults: context.previousResults || {},
                roundNumber: context.roundNumber || 1
            };

            // Classify the error
            const classification = this.errorRecoveryEngine.classifyError(error, toolCallContext);
            
            logger.info('ToolCallOrchestrator: Error classified for recovery', {
                toolName: error.toolName,
                errorType: classification.type,
                severity: classification.severity,
                recoverable: classification.recoverable,
                strategy: classification.suggestedStrategy
            });

            // Generate recovery action
            const recoveryAction = this.errorRecoveryEngine.generateRecoveryAction(
                classification,
                error,
                toolCallContext
            );

            // Execute recovery
            const recoveryResult = await this.errorRecoveryEngine.executeRecovery(
                recoveryAction,
                error,
                toolCallContext
            );

            return recoveryResult;

        } catch (recoveryError) {
            logger.error('ToolCallOrchestrator: Error recovery attempt failed', {
                originalError: error.error,
                recoveryError: recoveryError instanceof Error ? recoveryError.message : 'Unknown error'
            });

            // Return a failed recovery result
            return {
                success: false,
                shouldContinue: false,
                action: { strategy: 'abort', description: 'Recovery failed' }
            };
        }
    }

    /**
     * Get error recovery statistics
     */
    getErrorRecoveryStatistics(): any {
        return this.errorRecoveryEngine.getRecoveryStatistics();
    }

    /**
     * Clear error recovery history (useful for testing)
     */
    clearErrorRecoveryHistory(): void {
        this.errorRecoveryEngine.clearRecoveryHistory();
    }

    /**
     * Generate enhanced error summary for debugging
     */
    generateErrorSummary(errors: ToolError[]): string {
        if (errors.length === 0) {
            return 'No errors encountered during workflow execution.';
        }

        const errorsByTool: Record<string, ToolError[]> = {};
        const errorsByType: Record<string, number> = {};

        for (const error of errors) {
            // Group by tool
            if (!errorsByTool[error.toolName]) {
                errorsByTool[error.toolName] = [];
            }
            errorsByTool[error.toolName].push(error);

            // Count by type
            const errorType = error.errorType || 'unknown';
            errorsByType[errorType] = (errorsByType[errorType] || 0) + 1;
        }

        let summary = `**Error Summary** (${errors.length} total errors)\n\n`;

        // Tools with errors
        summary += '**Tools with Issues:**\n';
        for (const [toolName, toolErrors] of Object.entries(errorsByTool)) {
            const avgRetries = toolErrors.reduce((sum, e) => sum + e.retryCount, 0) / toolErrors.length;
            summary += `• ${toolName}: ${toolErrors.length} errors (avg ${avgRetries.toFixed(1)} retries)\n`;
        }

        // Error types
        summary += '\n**Error Types:**\n';
        for (const [errorType, count] of Object.entries(errorsByType)) {
            summary += `• ${errorType}: ${count}\n`;
        }

        return summary;
    }
}