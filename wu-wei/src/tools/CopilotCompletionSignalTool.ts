import * as vscode from 'vscode';
import { logger } from '../logger';
import { ExecutionTracker, CompletionRecord } from './ExecutionTracker';

export interface ICopilotCompletionParameters {
    executionId?: string;
    taskDescription: string;
    status?: 'success' | 'partial' | 'error';
    summary?: string;
    metadata?: {
        duration?: number;
        toolsUsed?: string[];
        filesModified?: string[];
    };
}

export class CopilotCompletionSignalTool implements vscode.LanguageModelTool<ICopilotCompletionParameters> {
    private static readonly TOOL_NAME = 'wu-wei_copilot_completion_signal';
    private executionTracker: ExecutionTracker;

    constructor() {
        this.executionTracker = new ExecutionTracker();
    }

    async prepareInvocation(
        options: vscode.LanguageModelToolInvocationPrepareOptions<ICopilotCompletionParameters>,
        _token: vscode.CancellationToken
    ) {
        const { input } = options;
        const statusIcon = this.getStatusIcon(input.status || 'success');

        const confirmationMessages = {
            title: 'Signal Copilot Completion',
            message: new vscode.MarkdownString(
                `${statusIcon} **Signal completion of Copilot execution**\n\n` +
                `**Task**: ${input.taskDescription}\n` +
                `**Status**: ${input.status || 'success'}\n` +
                (input.summary ? `**Summary**: ${input.summary}\n` : '') +
                `**Execution ID**: ${input.executionId || 'auto-generated'}\n\n` +
                `This will mark the Copilot execution as complete and record the completion details.`
            ),
        };

        return {
            invocationMessage: `Signaling completion: ${input.taskDescription}`,
            confirmationMessages,
        };
    }

    async invoke(
        options: vscode.LanguageModelToolInvocationOptions<ICopilotCompletionParameters>,
        _token: vscode.CancellationToken
    ): Promise<vscode.LanguageModelToolResult> {
        try {
            const params = options.input;
            const executionId = params.executionId || this.generateExecutionId();
            const timestamp = new Date();
            const status = params.status || 'success';

            // Record completion in execution tracker
            const completionRecord = await this.executionTracker.recordCompletion({
                executionId,
                taskDescription: params.taskDescription,
                status,
                summary: params.summary,
                metadata: params.metadata,
                timestamp,
            });

            // Log completion
            logger.info('Copilot execution completed', {
                executionId,
                taskDescription: params.taskDescription,
                status,
                timestamp: timestamp.toISOString(),
            });

            // Show completion notification if configured
            await this.showCompletionNotification(completionRecord);

            // Emit completion event for other systems
            await this.emitCompletionEvent(completionRecord);

            // Generate response based on status
            const statusIcon = this.getStatusIcon(status);
            const responseText = this.generateCompletionResponse(completionRecord, statusIcon);

            return new vscode.LanguageModelToolResult([
                new vscode.LanguageModelTextPart(responseText)
            ]);

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            logger.error('Failed to signal Copilot completion', { error: errorMessage });

            return new vscode.LanguageModelToolResult([
                new vscode.LanguageModelTextPart(
                    `❌ **Completion Signal Failed**\n\nError: ${errorMessage}\n\n` +
                    `The completion could not be recorded. Please check the Wu Wei logs for more details.`
                )
            ]);
        }
    }

    private generateExecutionId(): string {
        return `wu-wei-exec-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    private getStatusIcon(status: string): string {
        switch (status) {
            case 'success': return '✅';
            case 'partial': return '⚠️';
            case 'error': return '❌';
            default: return '📝';
        }
    }

    private generateCompletionResponse(record: CompletionRecord, statusIcon: string): string {
        const { taskDescription, status, summary, executionId, timestamp } = record;

        let response = `${statusIcon} **Copilot Execution Complete**\n\n`;
        response += `**Task**: ${taskDescription}\n`;
        response += `**Status**: ${status}\n`;
        response += `**Completed**: ${timestamp.toLocaleString()}\n`;
        response += `**Execution ID**: \`${executionId}\`\n`;

        if (summary) {
            response += `\n**Summary**: ${summary}\n`;
        }

        if (record.metadata) {
            response += '\n**Details**:\n';
            if (record.metadata.duration) {
                response += `- Duration: ${record.metadata.duration}ms\n`;
            }
            if (record.metadata.toolsUsed?.length) {
                response += `- Tools used: ${record.metadata.toolsUsed.join(', ')}\n`;
            }
            if (record.metadata.filesModified?.length) {
                response += `- Files modified: ${record.metadata.filesModified.length}\n`;
            }
        }

        response += '\n🧘 *Wu Wei execution flows like water - effortless and complete*';

        return response;
    }

    private async showCompletionNotification(record: CompletionRecord): Promise<void> {
        const config = vscode.workspace.getConfiguration('wu-wei');
        const showNotifications = config.get<boolean>('showCompletionNotifications', true);

        if (!showNotifications) {
            return;
        }

        const statusIcon = this.getStatusIcon(record.status);
        const message = `${statusIcon} Copilot completed: ${record.taskDescription}`;

        if (record.status === 'success') {
            vscode.window.showInformationMessage(message);
        } else if (record.status === 'partial') {
            vscode.window.showWarningMessage(message);
        } else {
            vscode.window.showErrorMessage(message);
        }
    }

    private async emitCompletionEvent(record: CompletionRecord): Promise<void> {
        // Emit custom event for other systems to listen to
        if (CopilotCompletionSignalTool.onCompletion) {
            const event = new vscode.EventEmitter<CompletionRecord>();
            CopilotCompletionSignalTool.onCompletion = event.event;
            event.fire(record);
        }
    }

    // Static event for external listeners
    static onCompletion: vscode.Event<CompletionRecord> | undefined;

    // Method to set context for dependency injection
    setContext(context: vscode.ExtensionContext): void {
        this.executionTracker.setContext(context);
    }

    dispose(): void {
        this.executionTracker.dispose();
    }
}
