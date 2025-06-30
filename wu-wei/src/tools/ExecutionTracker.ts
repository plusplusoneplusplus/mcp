import * as vscode from 'vscode';
import { logger } from '../logger';

export interface CompletionRecord {
    executionId: string;
    taskDescription: string;
    status: 'success' | 'partial' | 'error';
    summary?: string;
    metadata?: {
        duration?: number;
        toolsUsed?: string[];
        filesModified?: string[];
    };
    timestamp: Date;
}

export class ExecutionTracker {
    private static readonly STORAGE_KEY = 'wu-wei.copilot.executions';
    private context?: vscode.ExtensionContext;
    private completionHistory: CompletionRecord[] = [];

    constructor(context?: vscode.ExtensionContext) {
        if (context) {
            this.context = context;
            this.loadHistory();
        }
    }

    setContext(context: vscode.ExtensionContext): void {
        this.context = context;
        this.loadHistory();
    }

    async recordCompletion(record: Omit<CompletionRecord, 'timestamp'> & { timestamp: Date }): Promise<CompletionRecord> {
        const completionRecord: CompletionRecord = {
            ...record,
            timestamp: record.timestamp,
        };

        // Add to memory
        this.completionHistory.push(completionRecord);

        // Persist to storage
        if (this.context) {
            await this.saveHistory();
        }

        logger.info('Recorded completion', {
            executionId: completionRecord.executionId,
            status: completionRecord.status
        });

        return completionRecord;
    }

    getCompletionHistory(limit?: number): CompletionRecord[] {
        const history = [...this.completionHistory].reverse(); // Most recent first
        return limit ? history.slice(0, limit) : history;
    }

    getCompletionById(executionId: string): CompletionRecord | undefined {
        return this.completionHistory.find(record => record.executionId === executionId);
    }

    getCompletionStats(): {
        total: number;
        successful: number;
        partial: number;
        errors: number;
        averageDuration?: number;
    } {
        const total = this.completionHistory.length;
        const successful = this.completionHistory.filter(r => r.status === 'success').length;
        const partial = this.completionHistory.filter(r => r.status === 'partial').length;
        const errors = this.completionHistory.filter(r => r.status === 'error').length;

        const durationsMs = this.completionHistory
            .map(r => r.metadata?.duration)
            .filter((d): d is number => d !== undefined);

        const averageDuration = durationsMs.length > 0
            ? durationsMs.reduce((a, b) => a + b, 0) / durationsMs.length
            : undefined;

        return {
            total,
            successful,
            partial,
            errors,
            averageDuration,
        };
    }

    async clearHistory(): Promise<void> {
        this.completionHistory = [];
        if (this.context) {
            await this.saveHistory();
        }
        logger.info('Cleared completion history');
    }

    private async loadHistory(): Promise<void> {
        if (!this.context) return;

        try {
            const stored = this.context.globalState.get<CompletionRecord[]>(ExecutionTracker.STORAGE_KEY, []);
            this.completionHistory = stored.map(record => ({
                ...record,
                timestamp: new Date(record.timestamp), // Ensure timestamp is Date object
            }));

            logger.debug(`Loaded ${this.completionHistory.length} completion records`);
        } catch (error) {
            logger.error('Failed to load completion history', { error });
            this.completionHistory = [];
        }
    }

    private async saveHistory(): Promise<void> {
        if (!this.context) return;

        try {
            // Keep only last 1000 records to prevent storage bloat
            const recordsToSave = this.completionHistory.slice(-1000);
            await this.context.globalState.update(ExecutionTracker.STORAGE_KEY, recordsToSave);

            logger.debug(`Saved ${recordsToSave.length} completion records`);
        } catch (error) {
            logger.error('Failed to save completion history', { error });
        }
    }

    dispose(): void {
        // Save history one final time before disposing
        if (this.context && this.completionHistory.length > 0) {
            this.saveHistory().catch(error => {
                logger.error('Failed to save completion history on dispose', { error });
            });
        }
    }
}
