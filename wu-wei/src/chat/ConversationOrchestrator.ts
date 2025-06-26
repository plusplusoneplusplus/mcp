import * as vscode from 'vscode';
import { logger } from '../logger';
import { PromptTemplateLoader } from './PromptTemplateLoader';
import { ToolManager } from './ToolManager';
import { MessageBuilder } from './MessageBuilder';
import { ToolCallRound, ToolCallsMetadata, WuWeiToolMetadata } from './types';

/**
 * Orchestrates tool execution and conversation flow with the language model
 */
export class ConversationOrchestrator {
    constructor(
        private toolManager: ToolManager,
        private messageBuilder: MessageBuilder
    ) { }

    /**
     * Run conversation with tools support, handling iterative tool calls
     */
    async runWithTools(
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

                        // Show tool usage to user
                        const inputSummary = this.toolManager.summarizeToolInput(part.input);
                        stream.markdown(`\n🔧 **Using tool: ${part.name}** (${inputSummary})\n`);
                    }
                }

                if (toolCalls.length > 0) {
                    // Store this round
                    toolCallRounds.push({
                        response: responseStr,
                        toolCalls: toolCalls
                    });

                    // Execute tools
                    for (const toolCall of toolCalls) {
                        const result = await this.toolManager.invokeTool(toolCall);
                        accumulatedToolResults[toolCall.callId] = result;

                        // Add tool result to messages for next iteration
                        messages.push(vscode.LanguageModelChatMessage.User(`Tool result: ${result}`));

                        // Show tool result summary to user
                        const resultSummary = this.toolManager.summarizeToolResult(result);
                        stream.markdown(`📄 **Tool result:** ${resultSummary}\n\n`);
                    }

                    // Log completion of tool execution round
                    const successfulTools = toolCalls.filter(tc =>
                        accumulatedToolResults[tc.callId] &&
                        !accumulatedToolResults[tc.callId].includes('error')
                    );

                    logger.info(`Conversation Orchestrator: Tool execution round completed`, {
                        totalTools: toolCalls.length,
                        successfulTools: successfulTools.length,
                        failedTools: toolCalls.length - successfulTools.length,
                        toolNames: toolCalls.map(tc => tc.name),
                        currentRound: toolCallRounds.length
                    });

                    // Safeguard: Prevent infinite tool calling loops
                    if (toolCallRounds.length >= 5) {
                        logger.warn(`Conversation Orchestrator: Maximum tool rounds reached (${toolCallRounds.length}), stopping recursion`);
                        stream.markdown(PromptTemplateLoader.getMaxRoundsReachedMessage());

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
                        stream.markdown(PromptTemplateLoader.getProcessingResultsMessage(successfulTools.length));
                        messages.push(vscode.LanguageModelChatMessage.User(`Please analyze and summarize the tool results above to answer the user's question. Use the actual data from the tools, not generic information.`));
                    }

                    // Continue the conversation with tool results
                    return runIteration();
                }

                // Log when LM completes without using tools
                if (toolCalls.length === 0) {
                    logger.info(`Conversation Orchestrator: LM completed response without using any tools`, {
                        responseLength: responseStr.length,
                        modelUsed: `${model.vendor}/${model.family}`,
                        availableToolCount: options.tools ? options.tools.length : 0
                    });
                }

                // Log conversation completion summary
                logger.info(`Conversation Orchestrator: Conversation completed`, {
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
                logger.error('Conversation Orchestrator: Error in tool iteration:', error);
                throw error;
            }
        };

        return runIteration();
    }
}
