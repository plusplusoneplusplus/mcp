import * as vscode from 'vscode';
import { logger } from '../../logger';
import { CachedToolResult, ToolWorkflowMetadata, ToolError } from './types';
import * as crypto from 'crypto';

/**
 * Manages tool results, caching, and context preservation
 */
export class ToolResultManager {
    private cache: Map<string, CachedToolResult> = new Map();
    private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes
    private readonly MAX_CACHE_SIZE = 100;

    constructor(private enableCaching: boolean = true) {
        // Clean up expired cache entries every minute
        setInterval(() => this.cleanupExpiredCache(), 60 * 1000);
    }

    /**
     * Cache a tool result for reuse
     */
    cacheResult(
        toolName: string,
        input: any,
        result: vscode.LanguageModelToolResult
    ): void {
        if (!this.enableCaching) return;

        try {
            const inputHash = this.hashInput(input);
            const cacheKey = `${toolName}:${inputHash}`;

            const cachedResult: CachedToolResult = {
                result,
                timestamp: Date.now(),
                inputHash,
                expiresAt: Date.now() + this.CACHE_TTL
            };

            // Manage cache size
            if (this.cache.size >= this.MAX_CACHE_SIZE) {
                this.evictOldestCacheEntry();
            }

            this.cache.set(cacheKey, cachedResult);

            logger.debug(`ToolResultManager: Cached result for ${toolName}`, {
                cacheKey,
                cacheSize: this.cache.size
            });
        } catch (error) {
            logger.warn('ToolResultManager: Failed to cache result', {
                toolName,
                error: error instanceof Error ? error.message : 'Unknown error'
            });
        }
    }

    /**
     * Retrieve a cached tool result
     */
    getCachedResult(toolName: string, input: any): vscode.LanguageModelToolResult | null {
        if (!this.enableCaching) return null;

        try {
            const inputHash = this.hashInput(input);
            const cacheKey = `${toolName}:${inputHash}`;
            const cached = this.cache.get(cacheKey);

            if (cached && cached.expiresAt > Date.now()) {
                logger.debug(`ToolResultManager: Cache hit for ${toolName}`, { cacheKey });
                return cached.result;
            }

            if (cached && cached.expiresAt <= Date.now()) {
                this.cache.delete(cacheKey);
                logger.debug(`ToolResultManager: Expired cache entry removed for ${toolName}`, { cacheKey });
            }

            return null;
        } catch (error) {
            logger.warn('ToolResultManager: Failed to retrieve cached result', {
                toolName,
                error: error instanceof Error ? error.message : 'Unknown error'
            });
            return null;
        }
    }

    /**
     * Summarize tool results for context preservation
     */
    summarizeResults(results: Record<string, vscode.LanguageModelToolResult>): string {
        const summaries: string[] = [];

        for (const [callId, result] of Object.entries(results)) {
            try {
                const summary = this.summarizeSingleResult(result);
                summaries.push(`${callId}: ${summary}`);
            } catch (error) {
                logger.warn(`ToolResultManager: Failed to summarize result for ${callId}`, { error });
                summaries.push(`${callId}: [Summarization failed]`);
            }
        }

        return summaries.length > 0 ? summaries.join('\n') : 'No tool results available';
    }

    /**
     * Extract metadata from tool execution
     */
    extractMetadata(
        toolCallRounds: any[],
        toolCallResults: Record<string, vscode.LanguageModelToolResult>,
        errors: ToolError[],
        startTime: number
    ): ToolWorkflowMetadata {
        const toolsUsed = new Set<string>();

        // Extract unique tools used across all rounds
        for (const round of toolCallRounds) {
            if (round.toolCalls) {
                for (const toolCall of round.toolCalls) {
                    toolsUsed.add(toolCall.name);
                }
            }
        }

        const cacheHits = this.getCacheHitCount();

        return {
            totalRounds: toolCallRounds.length,
            toolsUsed: Array.from(toolsUsed),
            executionTime: Date.now() - startTime,
            errors,
            cacheHits
        };
    }

    /**
     * Format tool results for display
     */
    formatResultsForDisplay(results: Record<string, vscode.LanguageModelToolResult>): string {
        const formattedResults: string[] = [];

        for (const [callId, result] of Object.entries(results)) {
            try {
                const formatted = this.formatSingleResult(callId, result);
                formattedResults.push(formatted);
            } catch (error) {
                logger.warn(`ToolResultManager: Failed to format result for ${callId}`, { error });
                formattedResults.push(`**${callId}**: [Formatting failed]`);
            }
        }

        return formattedResults.join('\n\n');
    }

    /**
     * Clear all cached results
     */
    clearCache(): void {
        this.cache.clear();
        logger.debug('ToolResultManager: Cache cleared');
    }

    /**
     * Get cache statistics
     */
    getCacheStats(): { size: number; hitRate: number; oldestEntry: number | null } {
        let oldestTimestamp: number | null = null;

        for (const cached of this.cache.values()) {
            if (oldestTimestamp === null || cached.timestamp < oldestTimestamp) {
                oldestTimestamp = cached.timestamp;
            }
        }

        return {
            size: this.cache.size,
            hitRate: this.getCacheHitCount(), // This is a simplified metric
            oldestEntry: oldestTimestamp
        };
    }

    /**
     * Hash input parameters for cache key generation
     */
    private hashInput(input: any): string {
        try {
            const inputString = JSON.stringify(input, Object.keys(input).sort());
            return crypto.createHash('md5').update(inputString).digest('hex');
        } catch (error) {
            // Fallback for non-serializable inputs
            return crypto.createHash('md5').update(String(input)).digest('hex');
        }
    }

    /**
 * Summarize a single tool result
 */
    private summarizeSingleResult(result: vscode.LanguageModelToolResult): string {
        try {
            // Handle different result types
            if (result && typeof result === 'object') {
                if ('content' in result && typeof (result as any).content === 'string') {
                    const content = (result as any).content as string;
                    if (content.length <= 100) {
                        return content;
                    }
                    return content.substring(0, 97) + '...';
                }

                // Handle structured results
                const resultStr = JSON.stringify(result);
                if (resultStr.length <= 100) {
                    return resultStr;
                }
                return resultStr.substring(0, 97) + '...';
            }

            const resultStr = String(result);
            if (resultStr.length <= 100) {
                return resultStr;
            }
            return resultStr.substring(0, 97) + '...';
        } catch (error) {
            return '[Complex result - summarization failed]';
        }
    }

    /**
 * Format a single result for display
 */
    private formatSingleResult(callId: string, result: vscode.LanguageModelToolResult): string {
        try {
            if (result && typeof result === 'object' && 'content' in result) {
                return `**${callId}**: ${(result as any).content}`;
            }

            return `**${callId}**: ${JSON.stringify(result, null, 2)}`;
        } catch (error) {
            return `**${callId}**: [Result formatting failed]`;
        }
    }

    /**
     * Clean up expired cache entries
     */
    private cleanupExpiredCache(): void {
        const now = Date.now();
        let removedCount = 0;

        for (const [key, cached] of this.cache.entries()) {
            if (cached.expiresAt <= now) {
                this.cache.delete(key);
                removedCount++;
            }
        }

        if (removedCount > 0) {
            logger.debug(`ToolResultManager: Cleaned up ${removedCount} expired cache entries`);
        }
    }

    /**
     * Evict the oldest cache entry to make room
     */
    private evictOldestCacheEntry(): void {
        let oldestKey: string | null = null;
        let oldestTimestamp = Date.now();

        for (const [key, cached] of this.cache.entries()) {
            if (cached.timestamp < oldestTimestamp) {
                oldestTimestamp = cached.timestamp;
                oldestKey = key;
            }
        }

        if (oldestKey) {
            this.cache.delete(oldestKey);
            logger.debug(`ToolResultManager: Evicted oldest cache entry: ${oldestKey}`);
        }
    }

    /**
     * Get cache hit count (simplified metric)
     */
    private getCacheHitCount(): number {
        // This is a simplified implementation
        // In a production system, you'd track actual hit/miss ratios
        return this.cache.size;
    }
} 