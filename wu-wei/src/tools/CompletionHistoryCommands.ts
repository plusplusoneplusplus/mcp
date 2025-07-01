import * as vscode from 'vscode';
import { ExecutionTracker } from './ExecutionTracker';
import { logger } from '../logger';

/**
 * Virtual document provider for completion history
 */
class CompletionHistoryDocumentProvider implements vscode.TextDocumentContentProvider {
    private _onDidChange = new vscode.EventEmitter<vscode.Uri>();
    public readonly onDidChange = this._onDidChange.event;

    private content: Map<string, string> = new Map();

    provideTextDocumentContent(uri: vscode.Uri): string {
        return this.content.get(uri.toString()) || '';
    }

    setContent(uri: vscode.Uri, content: string): void {
        this.content.set(uri.toString(), content);
        this._onDidChange.fire(uri);
    }

    dispose(): void {
        this._onDidChange.dispose();
    }
}

/**
 * Commands for managing and displaying Copilot completion history
 */
export class CompletionHistoryCommands {
    private executionTracker: ExecutionTracker;
    private disposables: vscode.Disposable[] = [];
    private documentProvider: CompletionHistoryDocumentProvider;

    constructor(executionTracker: ExecutionTracker) {
        this.executionTracker = executionTracker;
        this.documentProvider = new CompletionHistoryDocumentProvider();
    }

    /**
     * Register all completion history commands
     */
    public registerCommands(context: vscode.ExtensionContext): vscode.Disposable[] {
        // Register the virtual document provider
        const providerRegistration = vscode.workspace.registerTextDocumentContentProvider(
            'wu-wei-history',
            this.documentProvider
        );

        const showHistoryCommand = vscode.commands.registerCommand(
            'wu-wei.showCompletionHistory',
            this.showCompletionHistory.bind(this)
        );

        const clearHistoryCommand = vscode.commands.registerCommand(
            'wu-wei.clearCompletionHistory',
            this.clearCompletionHistory.bind(this)
        );

        this.disposables = [providerRegistration, showHistoryCommand, clearHistoryCommand];
        return this.disposables;
    }

    /**
     * Dispose of all registered commands
     */
    public dispose(): void {
        this.disposables.forEach(disposable => disposable.dispose());
        this.disposables = [];
        this.documentProvider.dispose();
    }

    /**
     * Show completion history in a new document
     */
    private async showCompletionHistory(): Promise<void> {
        logger.info('Show completion history command executed');

        try {
            const history = this.executionTracker.getCompletionHistory(50); // Get last 50 records
            const stats = this.executionTracker.getCompletionStats();

            logger.info('Completion history retrieved', {
                historyCount: history.length,
                statsTotal: stats.total
            });

            if (history.length === 0) {
                // Show more detailed debug info when no history is found
                logger.warn('No completion history found', {
                    executionTracker: !!this.executionTracker,
                    stats: stats
                });
                vscode.window.showInformationMessage('Wu Wei: No completion history found');
                return;
            }

            const historyDocument = this.formatHistoryDocument(history, stats);

            // Create a virtual document URI that won't trigger save prompts
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const uri = vscode.Uri.parse(`wu-wei-history:Wu Wei Completion History - ${timestamp}.md`);

            // Set the content for the virtual document
            this.documentProvider.setContent(uri, historyDocument);

            // Open the virtual document
            const doc = await vscode.workspace.openTextDocument(uri);
            await vscode.window.showTextDocument(doc, { preview: false });

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            logger.error('Failed to show completion history', { error: errorMessage });
            vscode.window.showErrorMessage(`Wu Wei: Failed to show completion history: ${errorMessage}`);
        }
    }

    /**
     * Clear completion history with user confirmation
     */
    private async clearCompletionHistory(): Promise<void> {
        logger.info('Clear completion history command executed');

        try {
            const confirmation = await vscode.window.showWarningMessage(
                'Clear all Copilot completion history?',
                { modal: true },
                'Clear'
            );

            if (confirmation === 'Clear') {
                await this.executionTracker.clearHistory();
                vscode.window.showInformationMessage('Wu Wei: Completion history cleared');
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            logger.error('Failed to clear completion history', { error: errorMessage });
            vscode.window.showErrorMessage(`Wu Wei: Failed to clear completion history: ${errorMessage}`);
        }
    }

    /**
     * Format completion history into a readable markdown document
     */
    private formatHistoryDocument(history: any[], stats: any): string {
        const headerSection = this.formatStatsSection(stats);
        const historySection = this.formatHistorySection(history);

        return `# Wu Wei - Copilot Completion History

${headerSection}

## Recent Executions

${historySection}

---
*Generated on ${new Date().toLocaleString()}*
`;
    }

    /**
     * Format statistics section
     */
    private formatStatsSection(stats: any): string {
        return `## Statistics

- **Total executions:** ${stats.total}
- **Successful:** ${stats.successful} (${this.calculatePercentage(stats.successful, stats.total)}%)
- **Partial:** ${stats.partial} (${this.calculatePercentage(stats.partial, stats.total)}%)
- **Errors:** ${stats.errors} (${this.calculatePercentage(stats.errors, stats.total)}%)
${stats.averageDuration ? `- **Average duration:** ${Math.round(stats.averageDuration)}ms` : ''}`;
    }

    /**
     * Format history section with individual completion records
     */
    private formatHistorySection(history: any[]): string {
        return history.map((record, index) => {
            const icon = this.getStatusIcon(record.status);
            const date = record.timestamp.toLocaleString();
            const duration = record.metadata?.duration ? ` (${record.metadata.duration}ms)` : '';

            return `### ${index + 1}. ${icon} ${record.taskDescription}

- **Execution ID:** \`${record.executionId}\`
- **Status:** ${record.status.charAt(0).toUpperCase() + record.status.slice(1)}
- **Timestamp:** ${date}${duration}
${record.summary ? `- **Summary:** ${record.summary}` : ''}
${this.formatMetadata(record.metadata)}`;
        }).join('\n\n');
    }

    /**
     * Format metadata section if present
     */
    private formatMetadata(metadata: any): string {
        if (!metadata) {
            return '';
        }

        const items: string[] = [];

        if (metadata.toolsUsed && metadata.toolsUsed.length > 0) {
            items.push(`- **Tools used:** ${metadata.toolsUsed.join(', ')}`);
        }

        if (metadata.filesModified && metadata.filesModified.length > 0) {
            items.push(`- **Files modified:** ${metadata.filesModified.join(', ')}`);
        }

        if (metadata.additionalInfo) {
            items.push(`- **Additional info:** ${metadata.additionalInfo}`);
        }

        return items.length > 0 ? '\n' + items.join('\n') : '';
    }

    /**
     * Get status icon for display
     */
    private getStatusIcon(status: string): string {
        switch (status) {
            case 'success': return '✅';
            case 'partial': return '⚠️';
            case 'error': return '❌';
            default: return '📝';
        }
    }

    /**
     * Calculate percentage with proper rounding
     */
    private calculatePercentage(part: number, total: number): number {
        if (total === 0) return 0;
        return Math.round((part / total) * 100);
    }
}
