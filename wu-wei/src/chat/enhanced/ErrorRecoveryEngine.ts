import * as vscode from 'vscode';
import { logger } from '../../logger';
import {
    ToolError,
    ToolParticipantConfig,
    ToolCallContext,
    PromptTemplate
} from './types';

/**
 * Error types for classification and recovery strategy selection
 */
export enum ErrorType {
    TOOL_NOT_FOUND = 'tool_not_found',
    PERMISSION_DENIED = 'permission_denied',
    TIMEOUT = 'timeout',
    INVALID_PARAMETERS = 'invalid_parameters',
    NETWORK_ERROR = 'network_error',
    RATE_LIMIT = 'rate_limit',
    MODEL_ERROR = 'model_error',
    PARSING_ERROR = 'parsing_error',
    RESOURCE_EXHAUSTED = 'resource_exhausted',
    UNKNOWN = 'unknown'
}

/**
 * Recovery strategy types
 */
export enum RecoveryStrategy {
    RETRY = 'retry',
    FALLBACK_TOOL = 'fallback_tool',
    PARAMETER_CORRECTION = 'parameter_correction',
    GRACEFUL_DEGRADATION = 'graceful_degradation',
    USER_INTERVENTION = 'user_intervention',
    ABORT = 'abort'
}

/**
 * Error classification result
 */
export interface ErrorClassification {
    type: ErrorType;
    severity: 'low' | 'medium' | 'high' | 'critical';
    recoverable: boolean;
    suggestedStrategy: RecoveryStrategy;
    confidence: number;
    details: Record<string, any>;
}

/**
 * Recovery action to be taken
 */
export interface RecoveryAction {
    strategy: RecoveryStrategy;
    description: string;
    parameters: Record<string, any>;
    retryable: boolean;
    timeoutMs?: number;
    fallbackOptions?: string[];
}

/**
 * Recovery attempt result
 */
export interface RecoveryResult {
    success: boolean;
    action: RecoveryAction;
    newError?: ToolError;
    alternativeApproach?: string;
    userMessage?: string;
    shouldContinue: boolean;
}

/**
 * Comprehensive error recovery engine for the Wu Wei tool calling framework
 */
export class ErrorRecoveryEngine {
    private config: ToolParticipantConfig;
    private recoveryHistory: Map<string, RecoveryResult[]> = new Map();
    private errorPatterns: Map<string, ErrorClassification> = new Map();

    constructor(config: ToolParticipantConfig) {
        this.config = config;
        this.initializeErrorPatterns();
    }

    /**
     * Classify an error to determine appropriate recovery strategy
     */
    classifyError(error: ToolError, context: ToolCallContext): ErrorClassification {
        const errorMessage = error.error.toLowerCase();
        const toolName = error.toolName;

        // Check for cached classifications first
        const cacheKey = `${toolName}:${errorMessage}`;
        if (this.errorPatterns.has(cacheKey)) {
            return this.errorPatterns.get(cacheKey)!;
        }

        let classification: ErrorClassification;

        // Classify based on error patterns
        if (this.isToolNotFoundError(errorMessage)) {
            classification = {
                type: ErrorType.TOOL_NOT_FOUND,
                severity: 'medium',
                recoverable: true,
                suggestedStrategy: RecoveryStrategy.FALLBACK_TOOL,
                confidence: 0.9,
                details: { toolName, availableTools: context.availableTools.map(t => t.name) }
            };
        } else if (this.isPermissionError(errorMessage)) {
            classification = {
                type: ErrorType.PERMISSION_DENIED,
                severity: 'high',
                recoverable: false,
                suggestedStrategy: RecoveryStrategy.USER_INTERVENTION,
                confidence: 0.85,
                details: { requiresUserAction: true }
            };
        } else if (this.isTimeoutError(errorMessage)) {
            classification = {
                type: ErrorType.TIMEOUT,
                severity: 'medium',
                recoverable: true,
                suggestedStrategy: RecoveryStrategy.RETRY,
                confidence: 0.8,
                details: { retryCount: error.retryCount, maxRetries: this.config.errorRetryAttempts }
            };
        } else if (this.isParameterError(errorMessage)) {
            classification = {
                type: ErrorType.INVALID_PARAMETERS,
                severity: 'low',
                recoverable: true,
                suggestedStrategy: RecoveryStrategy.PARAMETER_CORRECTION,
                confidence: 0.7,
                details: { parameterValidation: true }
            };
        } else if (this.isNetworkError(errorMessage)) {
            classification = {
                type: ErrorType.NETWORK_ERROR,
                severity: 'medium',
                recoverable: true,
                suggestedStrategy: RecoveryStrategy.RETRY,
                confidence: 0.75,
                details: { networkIssue: true }
            };
        } else if (this.isRateLimitError(errorMessage)) {
            classification = {
                type: ErrorType.RATE_LIMIT,
                severity: 'low',
                recoverable: true,
                suggestedStrategy: RecoveryStrategy.RETRY,
                confidence: 0.9,
                details: { rateLimited: true, suggestedDelay: 5000 }
            };
        } else if (this.isModelError(errorMessage)) {
            classification = {
                type: ErrorType.MODEL_ERROR,
                severity: 'high',
                recoverable: true,
                suggestedStrategy: RecoveryStrategy.GRACEFUL_DEGRADATION,
                confidence: 0.8,
                details: { modelIssue: true }
            };
        } else {
            classification = {
                type: ErrorType.UNKNOWN,
                severity: 'medium',
                recoverable: false,
                suggestedStrategy: RecoveryStrategy.GRACEFUL_DEGRADATION,
                confidence: 0.5,
                details: { unknownError: true }
            };
        }

        // Cache the classification
        this.errorPatterns.set(cacheKey, classification);

        logger.debug('ErrorRecoveryEngine: Error classified', {
            toolName,
            errorType: classification.type,
            severity: classification.severity,
            recoverable: classification.recoverable,
            strategy: classification.suggestedStrategy,
            confidence: classification.confidence
        });

        return classification;
    }

    /**
     * Generate a recovery action based on error classification
     */
    generateRecoveryAction(
        classification: ErrorClassification,
        error: ToolError,
        context: ToolCallContext
    ): RecoveryAction {
        const { type, suggestedStrategy, details } = classification;

        switch (suggestedStrategy) {
            case RecoveryStrategy.RETRY:
                return this.createRetryAction(error, details);

            case RecoveryStrategy.FALLBACK_TOOL:
                return this.createFallbackToolAction(error, context, details);

            case RecoveryStrategy.PARAMETER_CORRECTION:
                return this.createParameterCorrectionAction(error, context, details);

            case RecoveryStrategy.GRACEFUL_DEGRADATION:
                return this.createGracefulDegradationAction(error, context, details);

            case RecoveryStrategy.USER_INTERVENTION:
                return this.createUserInterventionAction(error, details);

            case RecoveryStrategy.ABORT:
            default:
                return this.createAbortAction(error, details);
        }
    }

    /**
     * Execute a recovery action
     */
    async executeRecovery(
        action: RecoveryAction,
        error: ToolError,
        context: ToolCallContext
    ): Promise<RecoveryResult> {
        const startTime = Date.now();

        try {
            logger.info('ErrorRecoveryEngine: Executing recovery action', {
                strategy: action.strategy,
                toolName: error.toolName,
                description: action.description
            });

            let result: RecoveryResult;

            switch (action.strategy) {
                case RecoveryStrategy.RETRY:
                    result = await this.executeRetry(action, error, context);
                    break;

                case RecoveryStrategy.FALLBACK_TOOL:
                    result = await this.executeFallbackTool(action, error, context);
                    break;

                case RecoveryStrategy.PARAMETER_CORRECTION:
                    result = await this.executeParameterCorrection(action, error, context);
                    break;

                case RecoveryStrategy.GRACEFUL_DEGRADATION:
                    result = await this.executeGracefulDegradation(action, error, context);
                    break;

                case RecoveryStrategy.USER_INTERVENTION:
                    result = this.executeUserIntervention(action, error, context);
                    break;

                default:
                    result = this.executeAbort(action, error, context);
            }

            // Record the recovery attempt
            this.recordRecoveryAttempt(error.toolName, result);

            logger.info('ErrorRecoveryEngine: Recovery action completed', {
                strategy: action.strategy,
                success: result.success,
                executionTime: Date.now() - startTime
            });

            return result;

        } catch (recoveryError) {
            logger.error('ErrorRecoveryEngine: Recovery action failed', {
                strategy: action.strategy,
                originalError: error.error,
                recoveryError: recoveryError instanceof Error ? recoveryError.message : 'Unknown error'
            });

            return {
                success: false,
                action,
                newError: {
                    toolName: error.toolName,
                    callId: error.callId,
                    error: `Recovery failed: ${recoveryError instanceof Error ? recoveryError.message : 'Unknown error'}`,
                    timestamp: Date.now(),
                    retryCount: error.retryCount + 1
                },
                shouldContinue: false,
                userMessage: 'Error recovery failed. Please try a different approach.'
            };
        }
    }

    /**
     * Get recovery suggestions for user-facing error messages
     */
    getRecoverySuggestions(
        classification: ErrorClassification,
        error: ToolError,
        context: ToolCallContext
    ): string[] {
        const suggestions: string[] = [];

        switch (classification.type) {
            case ErrorType.TOOL_NOT_FOUND:
                suggestions.push(
                    `The tool "${error.toolName}" is not available.`,
                    'Try using an alternative tool or check if required extensions are installed.',
                    'Available tools: ' + context.availableTools.map(t => t.name).join(', ')
                );
                break;

            case ErrorType.PERMISSION_DENIED:
                suggestions.push(
                    'Permission denied. Please check:',
                    '• File/folder access permissions',
                    '• VS Code workspace trust settings',
                    '• Extension permissions in VS Code settings'
                );
                break;

            case ErrorType.TIMEOUT:
                suggestions.push(
                    'The operation timed out.',
                    'This might be due to:',
                    '• Large files or complex operations',
                    '• Network connectivity issues',
                    '• System resource constraints'
                );
                break;

            case ErrorType.INVALID_PARAMETERS:
                suggestions.push(
                    'Invalid parameters provided to the tool.',
                    'Please check:',
                    '• Parameter names and types',
                    '• Required vs optional parameters',
                    '• Parameter value formats'
                );
                break;

            case ErrorType.NETWORK_ERROR:
                suggestions.push(
                    'Network connectivity issue detected.',
                    'Please check:',
                    '• Internet connection',
                    '• Proxy settings',
                    '• Firewall configuration'
                );
                break;

            case ErrorType.RATE_LIMIT:
                suggestions.push(
                    'Rate limit exceeded.',
                    'Please wait a moment before trying again.',
                    'Consider reducing the frequency of requests.'
                );
                break;

            case ErrorType.MODEL_ERROR:
                suggestions.push(
                    'Language model error occurred.',
                    'This might be temporary.',
                    'Try rephrasing your request or try again in a moment.'
                );
                break;

            default:
                suggestions.push(
                    'An unexpected error occurred.',
                    'Please try rephrasing your request or check the error details.',
                    'If the problem persists, please report it.'
                );
        }

        return suggestions;
    }

    /**
     * Check if we should continue workflow execution after an error
     */
    shouldContinueWorkflow(
        error: ToolError,
        context: ToolCallContext,
        totalErrors: number
    ): boolean {
        const classification = this.classifyError(error, context);

        // Don't continue for critical errors
        if (classification.severity === 'critical') {
            return false;
        }

        // Don't continue if too many errors accumulated
        if (totalErrors > this.config.maxToolRounds) {
            return false;
        }

        // Don't continue for non-recoverable errors
        if (!classification.recoverable) {
            return false;
        }

        // Check if we've exceeded retry attempts for this specific tool
        const toolHistory = this.recoveryHistory.get(error.toolName) || [];
        const recentFailures = toolHistory.filter(
            result => !result.success && (Date.now() - (result as any).timestamp < 300000) // 5 minutes
        );

        if (recentFailures.length > this.config.errorRetryAttempts) {
            return false;
        }

        return true;
    }

    /**
     * Generate error recovery prompt for the language model
     */
    generateErrorRecoveryPrompt(
        error: ToolError,
        classification: ErrorClassification,
        context: ToolCallContext,
        recoverySuggestions: string[]
    ): string {
        const basePrompt = `⚠️ **Tool Error Recovery Mode**

The tool "${error.toolName}" encountered an error: ${error.error}

**Error Analysis:**
- Type: ${classification.type}
- Severity: ${classification.severity}
- Recoverable: ${classification.recoverable ? 'Yes' : 'No'}
- Confidence: ${Math.round(classification.confidence * 100)}%

**Recovery Suggestions:**
${recoverySuggestions.map(s => `- ${s}`).join('\n')}

**Available Alternative Tools:**
${context.availableTools.filter(t => t.name !== error.toolName).map(t => `- ${t.name}: ${t.description}`).join('\n')}

**Instructions:**
Please acknowledge this error and either:
1. Try an alternative approach using different tools
2. Modify your strategy to work around this limitation
3. Provide a helpful response without using the failed tool

Do not retry the same tool with the same parameters. Focus on delivering value to the user despite this setback.`;

        return basePrompt;
    }

    // Private helper methods for error classification

    private isToolNotFoundError(errorMessage: string): boolean {
        const patterns = [
            'tool not found',
            'unknown tool',
            'tool does not exist',
            'no such tool',
            'tool unavailable',
            'not available'
        ];
        return patterns.some(pattern => errorMessage.includes(pattern));
    }

    private isPermissionError(errorMessage: string): boolean {
        const patterns = [
            'permission denied',
            'access denied',
            'unauthorized',
            'forbidden',
            'eacces',
            'eperm'
        ];
        return patterns.some(pattern => errorMessage.includes(pattern));
    }

    private isTimeoutError(errorMessage: string): boolean {
        const patterns = [
            'timeout',
            'timed out',
            'deadline exceeded',
            'time limit',
            'took too long'
        ];
        return patterns.some(pattern => errorMessage.includes(pattern));
    }

    private isParameterError(errorMessage: string): boolean {
        const patterns = [
            'invalid parameter',
            'invalid argument',
            'bad request',
            'schema validation',
            'missing required',
            'parameter error'
        ];
        return patterns.some(pattern => errorMessage.includes(pattern));
    }

    private isNetworkError(errorMessage: string): boolean {
        const patterns = [
            'network error',
            'connection failed',
            'host unreachable',
            'dns',
            'enotfound',
            'econnrefused'
        ];
        return patterns.some(pattern => errorMessage.includes(pattern));
    }

    private isRateLimitError(errorMessage: string): boolean {
        const patterns = [
            'rate limit',
            'too many requests',
            'quota exceeded',
            'throttled',
            'rate exceeded'
        ];
        return patterns.some(pattern => errorMessage.includes(pattern));
    }

    private isModelError(errorMessage: string): boolean {
        const patterns = [
            'model error',
            'language model',
            'ai service',
            'openai error',
            'copilot error',
            'model unavailable'
        ];
        return patterns.some(pattern => errorMessage.includes(pattern));
    }

    // Private helper methods for creating recovery actions

    private createRetryAction(error: ToolError, details: Record<string, any>): RecoveryAction {
        const delay = details.suggestedDelay || Math.pow(2, error.retryCount) * 1000;
        
        return {
            strategy: RecoveryStrategy.RETRY,
            description: `Retry tool execution after ${delay}ms delay`,
            parameters: { delay, retryCount: error.retryCount + 1 },
            retryable: true,
            timeoutMs: this.config.toolTimeout * 1.5 // Increase timeout for retry
        };
    }

    private createFallbackToolAction(
        error: ToolError,
        context: ToolCallContext,
        details: Record<string, any>
    ): RecoveryAction {
        const availableTools = context.availableTools.filter(t => t.name !== error.toolName);
        const similarTools = this.findSimilarTools(error.toolName, availableTools);

        return {
            strategy: RecoveryStrategy.FALLBACK_TOOL,
            description: `Use alternative tool instead of ${error.toolName}`,
            parameters: { originalTool: error.toolName },
            retryable: false,
            fallbackOptions: similarTools.map(t => t.name)
        };
    }

    private createParameterCorrectionAction(
        error: ToolError,
        context: ToolCallContext,
        details: Record<string, any>
    ): RecoveryAction {
        return {
            strategy: RecoveryStrategy.PARAMETER_CORRECTION,
            description: 'Correct tool parameters and retry',
            parameters: { validationRequired: true },
            retryable: true
        };
    }

    private createGracefulDegradationAction(
        error: ToolError,
        context: ToolCallContext,
        details: Record<string, any>
    ): RecoveryAction {
        return {
            strategy: RecoveryStrategy.GRACEFUL_DEGRADATION,
            description: 'Continue workflow without this tool',
            parameters: { skipTool: error.toolName },
            retryable: false
        };
    }

    private createUserInterventionAction(error: ToolError, details: Record<string, any>): RecoveryAction {
        return {
            strategy: RecoveryStrategy.USER_INTERVENTION,
            description: 'Requires user action to resolve',
            parameters: { userActionRequired: true },
            retryable: false
        };
    }

    private createAbortAction(error: ToolError, details: Record<string, any>): RecoveryAction {
        return {
            strategy: RecoveryStrategy.ABORT,
            description: 'Cannot recover from this error',
            parameters: { abortReason: error.error },
            retryable: false
        };
    }

    // Private helper methods for executing recovery actions

    private async executeRetry(
        action: RecoveryAction,
        error: ToolError,
        context: ToolCallContext
    ): Promise<RecoveryResult> {
        const delay = action.parameters.delay || 1000;
        
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, delay));

        return {
            success: true,
            action,
            shouldContinue: true,
            userMessage: `Retrying ${error.toolName} after ${delay}ms delay...`
        };
    }

    private async executeFallbackTool(
        action: RecoveryAction,
        error: ToolError,
        context: ToolCallContext
    ): Promise<RecoveryResult> {
        const fallbackOptions = action.fallbackOptions || [];

        if (fallbackOptions.length === 0) {
            return {
                success: false,
                action,
                shouldContinue: false,
                userMessage: `No alternative tools available for ${error.toolName}`
            };
        }

        return {
            success: true,
            action,
            shouldContinue: true,
            alternativeApproach: `I'll try using ${fallbackOptions[0]} instead of ${error.toolName}`,
            userMessage: `Switching to alternative tool: ${fallbackOptions[0]}`
        };
    }

    private async executeParameterCorrection(
        action: RecoveryAction,
        error: ToolError,
        context: ToolCallContext
    ): Promise<RecoveryResult> {
        return {
            success: true,
            action,
            shouldContinue: true,
            alternativeApproach: `I'll adjust the parameters for ${error.toolName} and try again`,
            userMessage: 'Correcting tool parameters and retrying...'
        };
    }

    private async executeGracefulDegradation(
        action: RecoveryAction,
        error: ToolError,
        context: ToolCallContext
    ): Promise<RecoveryResult> {
        return {
            success: true,
            action,
            shouldContinue: true,
            alternativeApproach: `I'll continue without using ${error.toolName} and provide the best assistance possible`,
            userMessage: `Continuing without ${error.toolName} tool`
        };
    }

    private executeUserIntervention(
        action: RecoveryAction,
        error: ToolError,
        context: ToolCallContext
    ): RecoveryResult {
        return {
            success: false,
            action,
            shouldContinue: false,
            userMessage: `The ${error.toolName} tool requires your attention to resolve permission or configuration issues`
        };
    }

    private executeAbort(
        action: RecoveryAction,
        error: ToolError,
        context: ToolCallContext
    ): RecoveryResult {
        return {
            success: false,
            action,
            shouldContinue: false,
            userMessage: `Unable to recover from error in ${error.toolName}: ${error.error}`
        };
    }

    // Helper methods

    private findSimilarTools(
        toolName: string,
        availableTools: vscode.LanguageModelToolInformation[]
    ): vscode.LanguageModelToolInformation[] {
        // Simple similarity based on name and description
        const similar = availableTools.filter(tool => {
            const nameSimilarity = this.calculateStringSimilarity(toolName, tool.name);
            const descriptionSimilarity = tool.description ? 
                this.calculateStringSimilarity(toolName, tool.description) : 0;
            
            return nameSimilarity > 0.5 || descriptionSimilarity > 0.3;
        });

        return similar.slice(0, 3); // Return top 3 similar tools
    }

    private calculateStringSimilarity(str1: string, str2: string): number {
        const longer = str1.length > str2.length ? str1 : str2;
        const shorter = str1.length > str2.length ? str2 : str1;
        
        if (longer.length === 0) return 1.0;
        
        const editDistance = this.levenshteinDistance(longer, shorter);
        return (longer.length - editDistance) / longer.length;
    }

    private levenshteinDistance(str1: string, str2: string): number {
        const matrix = Array(str2.length + 1).fill(null).map(() => Array(str1.length + 1).fill(null));
        
        for (let i = 0; i <= str1.length; i++) matrix[0][i] = i;
        for (let j = 0; j <= str2.length; j++) matrix[j][0] = j;
        
        for (let j = 1; j <= str2.length; j++) {
            for (let i = 1; i <= str1.length; i++) {
                const substitutionCost = str1[i - 1] === str2[j - 1] ? 0 : 1;
                matrix[j][i] = Math.min(
                    matrix[j][i - 1] + 1,
                    matrix[j - 1][i] + 1,
                    matrix[j - 1][i - 1] + substitutionCost
                );
            }
        }
        
        return matrix[str2.length][str1.length];
    }

    private recordRecoveryAttempt(toolName: string, result: RecoveryResult): void {
        if (!this.recoveryHistory.has(toolName)) {
            this.recoveryHistory.set(toolName, []);
        }
        
        const history = this.recoveryHistory.get(toolName)!;
        history.push({
            ...result,
            timestamp: Date.now()
        } as any);
        
        // Keep only recent history (last 10 attempts)
        if (history.length > 10) {
            history.splice(0, history.length - 10);
        }
    }

    private initializeErrorPatterns(): void {
        // Pre-populate common error patterns for faster classification
        // This could be extended with machine learning or user feedback
    }

    /**
     * Get recovery statistics for monitoring
     */
    getRecoveryStatistics(): {
        totalRecoveryAttempts: number;
        successfulRecoveries: number;
        recoveryStrategies: Record<RecoveryStrategy, number>;
        toolsWithMostErrors: Array<{ toolName: string; errorCount: number }>;
    } {
        let totalAttempts = 0;
        let successfulRecoveries = 0;
        const strategyCount: Record<RecoveryStrategy, number> = {} as any;
        const toolErrorCounts: Record<string, number> = {};

        for (const [toolName, history] of this.recoveryHistory) {
            totalAttempts += history.length;
            toolErrorCounts[toolName] = history.length;

            for (const result of history) {
                if (result.success) {
                    successfulRecoveries++;
                }

                const strategy = result.action.strategy;
                strategyCount[strategy] = (strategyCount[strategy] || 0) + 1;
            }
        }

        const toolsWithMostErrors = Object.entries(toolErrorCounts)
            .map(([toolName, errorCount]) => ({ toolName, errorCount }))
            .sort((a, b) => b.errorCount - a.errorCount)
            .slice(0, 5);

        return {
            totalRecoveryAttempts: totalAttempts,
            successfulRecoveries,
            recoveryStrategies: strategyCount,
            toolsWithMostErrors
        };
    }

    /**
     * Clear recovery history (useful for testing or reset)
     */
    clearRecoveryHistory(): void {
        this.recoveryHistory.clear();
        this.errorPatterns.clear();
    }
}
