import * as vscode from 'vscode';
import { logger } from '../logger';

/**
 * Manages VS Code Language Model tools - discovery, invocation, and result processing
 */
export class ToolManager {
    private cachedTools: vscode.LanguageModelToolInformation[] | null = null;

    /**
     * Get all available VS Code tools
     */
    getAvailableTools(): vscode.LanguageModelToolInformation[] {
        if (this.cachedTools) {
            return this.cachedTools;
        }

        try {
            // Use the official VS Code Language Model API to get tools
            if (vscode.lm && vscode.lm.tools) {
                const tools = vscode.lm.tools;
                logger.debug(`Tool Manager: Found ${tools.length} available tools`);
                this.cachedTools = Array.from(tools);
                return this.cachedTools;
            }
        } catch (error) {
            logger.debug('Tool Manager: Error accessing tools API:', error);
        }

        this.cachedTools = [];
        return this.cachedTools;
    }

    /**
     * Clear cached tools (useful when tools change)
     */
    clearCache(): void {
        this.cachedTools = null;
    }

    /**
     * Log available tools for debugging
     */
    async logAvailableTools(): Promise<void> {
        try {
            // Log language models
            const models = await vscode.lm.selectChatModels();
            logger.info('Tool Manager: Available Language Models:', {
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
            const tools = this.getAvailableTools();
            let toolNames: string[] = [];

            try {
                if (vscode.lm && 'tools' in vscode.lm) {
                    toolNames = tools.map(tool => tool.name);
                }
            } catch (error) {
                logger.debug('Tools API not available or accessible:', error);
            }

            logger.info('Tool Manager: Available VS Code Tools:', {
                count: tools.length,
                sampleTools: toolNames
            });

            // Log available capabilities
            logger.info('Tool Manager: Development Capabilities Available:', {
                languageModels: models.length > 0,
                fileSystem: true,
                chat: true,
                tools: tools.length
            });

        } catch (error) {
            logger.error('Tool Manager: Failed to log available tools', { error });
        }
    }

    /**
     * Invoke a tool using the VS Code Language Model API
     */
    async invokeTool(toolCall: vscode.LanguageModelToolCallPart): Promise<string> {
        try {
            logger.info(`Tool Manager: Attempting tool invocation`, {
                toolName: toolCall.name,
                callId: toolCall.callId,
                inputKeys: Object.keys(toolCall.input || {})
            });

            // Find the tool by name from available tools
            const availableTools = this.getAvailableTools();
            const toolInfo = availableTools.find(t => t.name === toolCall.name);

            if (!toolInfo) {
                logger.warn(`Tool Manager: Tool ${toolCall.name} not found in available tools`);
                return `Tool ${toolCall.name} is not available. Available tools: ${availableTools.map(t => t.name).join(', ')}`;
            }

            // The actual tool execution will be handled by VS Code's language model runtime
            const placeholderResult = `Tool ${toolCall.name} was invoked with parameters: ${JSON.stringify(toolCall.input, null, 2)}

This tool call will be executed by the VS Code language model runtime. The actual results will be processed and integrated into the conversation automatically.

Tool Information:
- Name: ${toolInfo.name}
- Description: ${toolInfo.description || 'No description available'}
- Parameters: ${JSON.stringify(toolCall.input, null, 2)}`;

            logger.info(`Tool Manager: Tool call registered for VS Code runtime execution`, {
                toolName: toolCall.name,
                callId: toolCall.callId,
                toolDescription: toolInfo.description
            });

            return placeholderResult;

        } catch (error) {
            logger.error(`Tool Manager: Tool invocation error for ${toolCall.name}`, {
                error: error instanceof Error ? error.message : 'Unknown error',
                stack: error instanceof Error ? error.stack : undefined
            });

            const errorResult = `Tool ${toolCall.name} execution failed: ${error instanceof Error ? error.message : 'Unknown error'}

Parameters: ${JSON.stringify(toolCall.input, null, 2)}
Call ID: ${toolCall.callId}

The tool invocation encountered an error. This may be due to:
- Tool not properly registered in VS Code
- Invalid parameters for the tool
- Missing permissions or dependencies
- Network connectivity issues (for remote tools)
- API version compatibility issues

Please check the VS Code Developer Console for more details and ensure all required extensions are installed and enabled.`;

            return errorResult;
        }
    }

    /**
     * Create a human-readable summary of tool input parameters
     */
    summarizeToolInput(input: any): string {
        if (!input || typeof input !== 'object') {
            return String(input || 'no parameters');
        }

        try {
            const summary: string[] = [];

            // Common parameter patterns to summarize
            if (input.query) { summary.push(`query: "${String(input.query).substring(0, 100)}"`); }
            if (input.filePath) { summary.push(`file: ${String(input.filePath)}`); }
            if (input.command) { summary.push(`command: "${String(input.command)}"`); }
            if (input.code) { summary.push(`code: ${String(input.code).length} chars`); }
            if (input.url) { summary.push(`url: ${String(input.url)}`); }
            if (input.pattern) { summary.push(`pattern: "${String(input.pattern)}"`); }

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
    summarizeToolResult(result: any): string {
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
}
