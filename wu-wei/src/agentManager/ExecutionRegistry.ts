import * as vscode from 'vscode';
import { logger } from '../logger';

/**
 * Interface for tracking active agent executions
 */
export interface ActiveExecution {
    executionId: string;
    agentName: string;
    method: string;
    taskDescription: string;
    startTime: Date;
    status: 'pending' | 'executing' | 'completed' | 'failed' | 'timeout';
    originalParams: any;
    promptContext?: any;
    timeoutHandle?: NodeJS.Timeout;
}

/**
 * Serializable version of ActiveExecution for persistence
 */
interface SerializableExecution {
    executionId: string;
    agentName: string;
    method: string;
    taskDescription: string;
    startTime: string; // ISO string
    status: 'pending' | 'executing' | 'completed' | 'failed' | 'timeout';
    originalParams: any;
    promptContext?: any;
}

/**
 * Central registry for tracking active agent executions
 * 
 * This class provides reliable execution correlation by maintaining a registry
 * of all active executions and providing multiple strategies for matching
 * completion signals to their originating executions.
 * 
 * Supports persistence across VSCode sessions for completed executions.
 */
export class ExecutionRegistry {
    private static readonly EXECUTION_TIMEOUT = 10 * 60 * 1000; // 10 minutes
    private static readonly STORAGE_KEY = 'wu-wei.execution.registry.completed';
    private activeExecutions = new Map<string, ActiveExecution>();
    private completedExecutions: ActiveExecution[] = [];
    private readonly maxCompletedHistory = 100;
    private context?: vscode.ExtensionContext;

    constructor(context?: vscode.ExtensionContext) {
        if (context) {
            this.context = context;
            this.loadCompletedHistory();
        }
    }

    /**
     * Set the extension context for persistence
     */
    setContext(context: vscode.ExtensionContext): void {
        this.context = context;
        this.loadCompletedHistory();
    }

    /**
     * Register a new execution in the registry
     */
    registerExecution(execution: Omit<ActiveExecution, 'timeoutHandle'>): void {
        const fullExecution: ActiveExecution = {
            ...execution,
            timeoutHandle: setTimeout(() => {
                this.timeoutExecution(execution.executionId);
            }, ExecutionRegistry.EXECUTION_TIMEOUT)
        };

        this.activeExecutions.set(execution.executionId, fullExecution);

        logger.info('Execution registered', {
            executionId: execution.executionId,
            agentName: execution.agentName,
            taskDescription: execution.taskDescription
        });
    }

    /**
     * Mark an execution as completed and remove from active registry
     */
    completeExecution(executionId: string): ActiveExecution | null {
        const execution = this.activeExecutions.get(executionId);
        if (!execution) {
            logger.warn('Attempted to complete non-existent execution', { executionId });
            return null;
        }

        // Update status and clear timeout
        execution.status = 'completed';
        if (execution.timeoutHandle) {
            clearTimeout(execution.timeoutHandle);
        }

        // Move to completed history
        this.activeExecutions.delete(executionId);
        this.addToCompletedHistory(execution);
        this.saveCompletedHistory();

        logger.info('Execution completed', {
            executionId,
            duration: Date.now() - execution.startTime.getTime()
        });

        return execution;
    }

    /**
     * Mark an execution as failed
     */
    failExecution(executionId: string, error?: string): ActiveExecution | null {
        const execution = this.activeExecutions.get(executionId);
        if (!execution) {
            return null;
        }

        execution.status = 'failed';
        if (execution.timeoutHandle) {
            clearTimeout(execution.timeoutHandle);
        }

        this.activeExecutions.delete(executionId);
        this.addToCompletedHistory(execution);
        this.saveCompletedHistory();

        logger.error('Execution failed', { executionId, error });

        return execution;
    }

    /**
     * Handle execution timeout
     */
    private timeoutExecution(executionId: string): void {
        const execution = this.activeExecutions.get(executionId);
        if (!execution) {
            return;
        }

        execution.status = 'timeout';
        this.activeExecutions.delete(executionId);
        this.addToCompletedHistory(execution);
        this.saveCompletedHistory();

        logger.warn('Execution timed out', {
            executionId,
            duration: Date.now() - execution.startTime.getTime()
        });
    }

    /**
     * Get a specific active execution by ID
     */
    getActiveExecution(executionId: string): ActiveExecution | null {
        return this.activeExecutions.get(executionId) || null;
    }

    /**
     * Get all currently active executions
     */
    getActiveExecutions(): ActiveExecution[] {
        return Array.from(this.activeExecutions.values());
    }

    /**
     * Get recently completed executions
     */
    getCompletedExecutions(limit: number = 50): ActiveExecution[] {
        return this.completedExecutions.slice(-limit).reverse();
    }

    /**
     * Correlation Strategy 1: Find execution by exact ID match
     */
    correlateByExecutionId(executionId: string): ActiveExecution | null {
        return this.getActiveExecution(executionId);
    }

    /**
     * Correlation Strategy 2: Find most recent active execution (temporal correlation)
     */
    correlateByTime(): ActiveExecution | null {
        const activeExecutions = this.getActiveExecutions();

        if (activeExecutions.length === 0) {
            return null;
        }

        if (activeExecutions.length === 1) {
            return activeExecutions[0]; // Only one active, must be it
        }

        // Return most recent if multiple
        return activeExecutions.sort((a, b) =>
            b.startTime.getTime() - a.startTime.getTime()
        )[0];
    }

    /**
     * Correlation Strategy 3: Find execution by task description similarity
     */
    correlateByContent(completionTaskDescription: string): ActiveExecution | null {
        const activeExecutions = this.getActiveExecutions();

        // First try exact match
        for (const execution of activeExecutions) {
            if (execution.taskDescription === completionTaskDescription) {
                return execution;
            }
        }

        // Then try similarity match
        for (const execution of activeExecutions) {
            if (this.isSimilarTask(execution.taskDescription, completionTaskDescription)) {
                return execution;
            }
        }

        return null;
    }

    /**
     * Smart correlation: Try multiple strategies in order
     */
    smartCorrelate(executionId?: string, taskDescription?: string): ActiveExecution | null {
        // Strategy 1: Exact execution ID match (most reliable)
        if (executionId) {
            const execution = this.correlateByExecutionId(executionId);
            if (execution) {
                logger.debug('Correlated by execution ID', { executionId });
                return execution;
            }
        }

        // Strategy 2: Task description similarity (medium reliability)
        if (taskDescription) {
            const execution = this.correlateByContent(taskDescription);
            if (execution) {
                logger.debug('Correlated by content similarity', {
                    taskDescription,
                    correlatedWith: execution.taskDescription
                });
                return execution;
            }
        }

        // Strategy 3: Temporal correlation (fallback)
        const execution = this.correlateByTime();
        if (execution) {
            logger.debug('Correlated by time (most recent)', {
                executionId: execution.executionId
            });
            return execution;
        }

        logger.warn('Failed to correlate completion signal', {
            providedExecutionId: executionId,
            providedTaskDescription: taskDescription,
            activeExecutionsCount: this.getActiveExecutions().length
        });

        return null;
    }

    /**
     * Check if two task descriptions are similar
     */
    private isSimilarTask(original: string, completion: string): boolean {
        // Normalize strings
        const normalizeText = (text: string) =>
            text.toLowerCase().replace(/[^\w\s]/g, '').trim();

        const originalNorm = normalizeText(original);
        const completionNorm = normalizeText(completion);

        // Exact match after normalization
        if (originalNorm === completionNorm) {
            return true;
        }

        // Word-based similarity
        const originalWords = originalNorm.split(/\s+/).filter(w => w.length > 2);
        const completionWords = completionNorm.split(/\s+/).filter(w => w.length > 2);

        if (originalWords.length === 0 || completionWords.length === 0) {
            return false;
        }

        const commonWords = originalWords.filter(word =>
            completionWords.includes(word)
        );

        // Require at least 40% overlap
        const similarity = commonWords.length / Math.min(originalWords.length, completionWords.length);
        return similarity >= 0.4;
    }

    /**
     * Add execution to completed history with size limit
     */
    private addToCompletedHistory(execution: ActiveExecution): void {
        this.completedExecutions.push(execution);

        // Keep only recent completions
        if (this.completedExecutions.length > this.maxCompletedHistory) {
            this.completedExecutions = this.completedExecutions.slice(-this.maxCompletedHistory);
        }
    }

    /**
     * Get execution statistics
     */
    getStatistics(): {
        active: number;
        completed: number;
        failed: number;
        timeout: number;
        averageDuration: number;
    } {
        const active = this.activeExecutions.size;
        const completed = this.completedExecutions.filter(e => e.status === 'completed').length;
        const failed = this.completedExecutions.filter(e => e.status === 'failed').length;
        const timeout = this.completedExecutions.filter(e => e.status === 'timeout').length;

        const completedWithDuration = this.completedExecutions
            .filter(e => e.status === 'completed')
            .map(e => Date.now() - e.startTime.getTime());

        const averageDuration = completedWithDuration.length > 0
            ? completedWithDuration.reduce((sum, d) => sum + d, 0) / completedWithDuration.length
            : 0;

        return { active, completed, failed, timeout, averageDuration };
    }

    /**
     * Cancel a specific execution
     */
    cancelExecution(executionId: string): boolean {
        const execution = this.activeExecutions.get(executionId);
        if (!execution) {
            return false;
        }

        execution.status = 'failed';
        if (execution.timeoutHandle) {
            clearTimeout(execution.timeoutHandle);
        }

        this.activeExecutions.delete(executionId);
        this.addToCompletedHistory(execution);
        this.saveCompletedHistory();

        logger.info('Execution cancelled', { executionId });
        return true;
    }

    /**
     * Clear all completed execution history
     */
    clearHistory(): void {
        this.completedExecutions = [];
        this.saveCompletedHistory();
        logger.info('Execution history cleared');
    }

    /**
     * Dispose and cleanup all active executions
     */
    dispose(): void {
        // Save completed history before disposing
        this.saveCompletedHistory();

        // Clear all timeouts
        for (const execution of this.activeExecutions.values()) {
            if (execution.timeoutHandle) {
                clearTimeout(execution.timeoutHandle);
            }
        }

        this.activeExecutions.clear();
        this.completedExecutions = [];

        logger.info('ExecutionRegistry disposed');
    }

    /**
     * Load completed execution history from persistent storage
     */
    private loadCompletedHistory(): void {
        if (!this.context) return;

        try {
            const stored = this.context.globalState.get<SerializableExecution[]>(ExecutionRegistry.STORAGE_KEY, []);
            this.completedExecutions = stored.map(exec => ({
                ...exec,
                startTime: new Date(exec.startTime),
                // Don't restore timeout handles - they should not be persisted
                timeoutHandle: undefined
            }));

            logger.debug(`Loaded ${this.completedExecutions.length} completed executions from storage`);
        } catch (error) {
            logger.error('Failed to load completed execution history', { error });
            this.completedExecutions = [];
        }
    }

    /**
     * Save completed execution history to persistent storage
     */
    private saveCompletedHistory(): void {
        if (!this.context) return;

        try {
            // Convert to serializable format
            const serializableExecutions: SerializableExecution[] = this.completedExecutions.map(exec => ({
                executionId: exec.executionId,
                agentName: exec.agentName,
                method: exec.method,
                taskDescription: exec.taskDescription,
                startTime: exec.startTime.toISOString(),
                status: exec.status,
                originalParams: exec.originalParams,
                promptContext: exec.promptContext
            }));

            // Keep only last maxCompletedHistory records
            const recordsToSave = serializableExecutions.slice(-this.maxCompletedHistory);
            this.context.globalState.update(ExecutionRegistry.STORAGE_KEY, recordsToSave);

            logger.debug(`Saved ${recordsToSave.length} completed executions to storage`);
        } catch (error) {
            logger.error('Failed to save completed execution history', { error });
        }
    }
}
