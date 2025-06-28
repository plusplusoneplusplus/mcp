import * as vscode from 'vscode';
import { BasePromptElementProps } from '@vscode/prompt-tsx';

/**
 * Priority-based content selection and management utility
 */
export class PriorityManager {
    /**
     * Sort items by priority (highest first)
     */
    sortByPriority<T extends { priority?: number }>(items: T[]): T[] {
        return [...items].sort((a, b) => {
            const priorityA = a.priority ?? 50; // Default priority
            const priorityB = b.priority ?? 50;
            return priorityB - priorityA; // Descending order (highest first)
        });
    }

    /**
     * Filter items by minimum priority threshold
     */
    filterByMinPriority<T extends { priority?: number }>(items: T[], minPriority: number): T[] {
        return items.filter(item => (item.priority ?? 50) >= minPriority);
    }

    /**
     * Get priority levels from a collection of items
     */
    extractPriorityLevels<T extends { priority?: number }>(items: T[]): number[] {
        const priorities = items.map(item => item.priority ?? 50);
        return [...new Set(priorities)].sort((a, b) => b - a); // Unique, descending
    }

    /**
     * Categorize items by priority ranges
     */
    categorizeByPriority<T extends { priority?: number }>(items: T[]): {
        critical: T[];    // 90-100
        high: T[];        // 70-89
        medium: T[];      // 50-69
        low: T[];         // 0-49
    } {
        const critical: T[] = [];
        const high: T[] = [];
        const medium: T[] = [];
        const low: T[] = [];

        for (const item of items) {
            const priority = item.priority ?? 50;

            if (priority >= 90) {
                critical.push(item);
            } else if (priority >= 70) {
                high.push(item);
            } else if (priority >= 50) {
                medium.push(item);
            } else {
                low.push(item);
            }
        }

        return { critical, high, medium, low };
    }

    /**
     * Select items that fit within a token budget, prioritizing by importance
     */
    selectByTokenBudget<T extends { priority?: number; tokenCount?: number }>(
        items: T[],
        tokenBudget: number,
        getTokenCount: (item: T) => number = (item) => item.tokenCount ?? 0
    ): { selected: T[]; excluded: T[]; totalTokens: number } {
        const sorted = this.sortByPriority(items);
        const selected: T[] = [];
        const excluded: T[] = [];
        let totalTokens = 0;

        for (const item of sorted) {
            const itemTokens = getTokenCount(item);

            if (totalTokens + itemTokens <= tokenBudget) {
                selected.push(item);
                totalTokens += itemTokens;
            } else {
                excluded.push(item);
            }
        }

        return { selected, excluded, totalTokens };
    }

    /**
     * Create a priority strategy with default values
     */
    createDefaultPriorityStrategy(): {
        systemInstructions: number;
        userQuery: number;
        conversationHistory: number;
        contextData: number;
    } {
        return {
            systemInstructions: 100, // Always included
            userQuery: 90,          // High importance
            conversationHistory: 80, // Medium importance
            contextData: 70         // Flexible, can be pruned
        };
    }

    /**
     * Apply priority-based pruning to messages
     */
    pruneMessagesByPriority(
        messages: Array<vscode.LanguageModelChatMessage & { priority?: number }>,
        tokenBudget: number,
        tokenCounter: (message: vscode.LanguageModelChatMessage) => number
    ): {
        kept: vscode.LanguageModelChatMessage[];
        pruned: vscode.LanguageModelChatMessage[];
        totalTokens: number;
    } {
        const messagesWithPriority = messages.map(msg => ({
            ...msg,
            priority: msg.priority ?? 50,
            tokenCount: tokenCounter(msg)
        }));

        const result = this.selectByTokenBudget(messagesWithPriority, tokenBudget, item => item.tokenCount);

        return {
            kept: result.selected,
            pruned: result.excluded,
            totalTokens: result.totalTokens
        };
    }

    /**
     * Validate priority values
     */
    validatePriority(priority: number): { isValid: boolean; message?: string } {
        if (typeof priority !== 'number') {
            return { isValid: false, message: 'Priority must be a number' };
        }

        if (priority < 0 || priority > 100) {
            return { isValid: false, message: 'Priority must be between 0 and 100' };
        }

        if (!Number.isInteger(priority)) {
            return { isValid: false, message: 'Priority should be an integer' };
        }

        return { isValid: true };
    }

    /**
     * Normalize priority to ensure it's within valid range
     */
    normalizePriority(priority?: number): number {
        if (priority === undefined || priority === null) {
            return 50; // Default priority
        }

        return Math.max(0, Math.min(100, Math.round(priority)));
    }
} 