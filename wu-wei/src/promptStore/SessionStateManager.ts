/**
 * Session State Manager for Wu Wei Prompt Store
 * Handles persistence of user state across VS Code sessions
 * Following wu wei principles: minimal state, natural persistence
 */

import * as vscode from 'vscode';
import { logger } from '../logger';

export interface SearchFilters {
    query?: string;
    category?: string;
    tags?: string[];
    author?: string;
    hasParameters?: boolean;
    modifiedAfter?: Date;
    modifiedBefore?: Date;
}

export interface SortPreferences {
    field: 'name' | 'modified' | 'category' | 'author' | 'created';
    direction: 'asc' | 'desc';
}

export interface UIState {
    sidebarWidth?: number;
    selectedPromptId?: string;
    viewMode?: 'list' | 'grid' | 'tree';
    showPreview?: boolean;
    showMetadata?: boolean;
    groupBy?: 'none' | 'category' | 'author' | 'tags';
}

export interface SessionState {
    lastRootDirectory?: string;
    expandedFolders: string[];
    searchFilters: SearchFilters;
    sortPreferences: SortPreferences;
    uiState: UIState;
    recentPrompts: string[];
    favoritePrompts: string[];
    lastSession?: {
        timestamp: Date;
        version: string;
    };
}

/**
 * Manages session state persistence for the Prompt Store
 */
export class SessionStateManager {
    private context: vscode.ExtensionContext;
    private readonly STATE_KEY = 'promptStoreState';
    private readonly GLOBAL_STATE_KEY = 'promptStoreGlobalState';
    private readonly MAX_RECENT_PROMPTS = 20;
    private readonly STATE_VERSION = '1.0.0';

    // Current session state cache
    private currentState: SessionState | null = null;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        logger.info('SessionStateManager initialized');
    }

    /**
     * Get the current session state
     */
    getState(): SessionState {
        if (this.currentState) {
            return this.currentState;
        }

        const workspaceState = this.context.workspaceState.get<SessionState>(this.STATE_KEY);
        const globalState = this.context.globalState.get<Partial<SessionState>>(this.GLOBAL_STATE_KEY);

        // Merge workspace and global state with defaults
        const defaultState: SessionState = {
            expandedFolders: [],
            searchFilters: {},
            sortPreferences: { field: 'name', direction: 'asc' },
            uiState: {
                viewMode: 'list',
                showPreview: true,
                showMetadata: true,
                groupBy: 'none'
            },
            recentPrompts: [],
            favoritePrompts: []
        };

        this.currentState = {
            ...defaultState,
            ...globalState,
            ...workspaceState,
            lastSession: {
                timestamp: new Date(),
                version: this.STATE_VERSION
            }
        };

        logger.info('Session state loaded', {
            hasWorkspaceState: !!workspaceState,
            hasGlobalState: !!globalState,
            expandedFolders: this.currentState.expandedFolders.length,
            recentPrompts: this.currentState.recentPrompts.length
        });

        return this.currentState;
    }

    /**
     * Update session state with partial updates
     */
    async updateState(updates: Partial<SessionState>): Promise<void> {
        try {
            const currentState = this.getState();
            const newState = {
                ...currentState,
                ...updates,
                lastSession: {
                    timestamp: new Date(),
                    version: this.STATE_VERSION
                }
            };

            this.currentState = newState;

            // Split state between workspace and global
            const workspaceState = this.extractWorkspaceState(newState);
            const globalState = this.extractGlobalState(newState);

            // Save to both workspace and global state
            await Promise.all([
                this.context.workspaceState.update(this.STATE_KEY, workspaceState),
                this.context.globalState.update(this.GLOBAL_STATE_KEY, globalState)
            ]);

            logger.info('Session state updated', {
                workspaceKeys: Object.keys(workspaceState),
                globalKeys: Object.keys(globalState)
            });
        } catch (error) {
            logger.error('Failed to update session state', error);
            throw error;
        }
    }

    /**
     * Update search filters
     */
    async updateSearchFilters(filters: SearchFilters): Promise<void> {
        await this.updateState({ searchFilters: filters });
    }

    /**
     * Update sort preferences
     */
    async updateSortPreferences(sort: SortPreferences): Promise<void> {
        await this.updateState({ sortPreferences: sort });
    }

    /**
     * Update UI state
     */
    async updateUIState(uiState: Partial<UIState>): Promise<void> {
        const currentState = this.getState();
        const newUIState = { ...currentState.uiState, ...uiState };
        await this.updateState({ uiState: newUIState });
    }

    /**
     * Add a folder to the expanded folders list
     */
    async expandFolder(folderPath: string): Promise<void> {
        const currentState = this.getState();
        const expandedFolders = [...new Set([...currentState.expandedFolders, folderPath])];
        await this.updateState({ expandedFolders });
    }

    /**
     * Remove a folder from the expanded folders list
     */
    async collapseFolder(folderPath: string): Promise<void> {
        const currentState = this.getState();
        const expandedFolders = currentState.expandedFolders.filter(path => path !== folderPath);
        await this.updateState({ expandedFolders });
    }

    /**
     * Add a prompt to the recent prompts list
     */
    async addRecentPrompt(promptId: string): Promise<void> {
        const currentState = this.getState();
        const recentPrompts = [
            promptId,
            ...currentState.recentPrompts.filter(id => id !== promptId)
        ].slice(0, this.MAX_RECENT_PROMPTS);

        await this.updateState({ recentPrompts });
    }

    /**
     * Add or remove a prompt from favorites
     */
    async toggleFavoritePrompt(promptId: string): Promise<void> {
        const currentState = this.getState();
        const favoritePrompts = currentState.favoritePrompts.includes(promptId)
            ? currentState.favoritePrompts.filter(id => id !== promptId)
            : [...currentState.favoritePrompts, promptId];

        await this.updateState({ favoritePrompts });
    }

    /**
     * Set the last used root directory
     */
    async setLastRootDirectory(directory: string): Promise<void> {
        await this.updateState({ lastRootDirectory: directory });
    }

    /**
     * Get recent prompts
     */
    getRecentPrompts(): string[] {
        return this.getState().recentPrompts;
    }

    /**
     * Get favorite prompts
     */
    getFavoritePrompts(): string[] {
        return this.getState().favoritePrompts;
    }

    /**
     * Check if a folder is expanded
     */
    isFolderExpanded(folderPath: string): boolean {
        return this.getState().expandedFolders.includes(folderPath);
    }

    /**
     * Check if a prompt is in favorites
     */
    isPromptFavorite(promptId: string): boolean {
        return this.getState().favoritePrompts.includes(promptId);
    }

    /**
     * Clear all state data
     */
    async clearState(): Promise<void> {
        try {
            await Promise.all([
                this.context.workspaceState.update(this.STATE_KEY, undefined),
                this.context.globalState.update(this.GLOBAL_STATE_KEY, undefined)
            ]);

            this.currentState = null;
            logger.info('Session state cleared');
        } catch (error) {
            logger.error('Failed to clear session state', error);
            throw error;
        }
    }

    /**
     * Migrate state from an older version
     */
    async migrateState(oldVersion: string): Promise<void> {
        try {
            logger.info('Migrating session state', { from: oldVersion, to: this.STATE_VERSION });

            // For now, no migration needed as this is the first version
            // Future versions would implement migration logic here

            await this.updateState({
                lastSession: {
                    timestamp: new Date(),
                    version: this.STATE_VERSION
                }
            });

            logger.info('Session state migration completed');
        } catch (error) {
            logger.error('Failed to migrate session state', error);
            throw error;
        }
    }

    /**
     * Clean up old state data (remove expired entries, etc.)
     */
    async cleanupState(): Promise<void> {
        try {
            const currentState = this.getState();

            // Remove non-existent folders from expanded folders
            // This would need to be called with actual folder validation

            // Trim recent prompts to max length
            const recentPrompts = currentState.recentPrompts.slice(0, this.MAX_RECENT_PROMPTS);

            if (recentPrompts.length !== currentState.recentPrompts.length) {
                await this.updateState({ recentPrompts });
                logger.info('Session state cleanup completed', {
                    trimmedRecentPrompts: currentState.recentPrompts.length - recentPrompts.length
                });
            }
        } catch (error) {
            logger.error('Failed to cleanup session state', error);
        }
    }

    /**
     * Export state for backup or debugging
     */
    exportState(): SessionState {
        return { ...this.getState() };
    }

    /**
     * Import state from backup
     */
    async importState(state: SessionState): Promise<void> {
        try {
            // Validate the imported state
            const validatedState = this.validateImportedState(state);
            await this.updateState(validatedState);
            logger.info('Session state imported successfully');
        } catch (error) {
            logger.error('Failed to import session state', error);
            throw error;
        }
    }

    /**
     * Extract workspace-specific state
     */
    private extractWorkspaceState(state: SessionState): Partial<SessionState> {
        return {
            lastRootDirectory: state.lastRootDirectory,
            expandedFolders: state.expandedFolders,
            searchFilters: state.searchFilters,
            sortPreferences: state.sortPreferences,
            uiState: state.uiState,
            lastSession: state.lastSession
        };
    }

    /**
     * Extract global state (persists across workspaces)
     */
    private extractGlobalState(state: SessionState): Partial<SessionState> {
        return {
            recentPrompts: state.recentPrompts,
            favoritePrompts: state.favoritePrompts
        };
    }

    /**
     * Validate imported state data
     */
    private validateImportedState(state: any): SessionState {
        const defaultState = this.getState();

        return {
            lastRootDirectory: typeof state.lastRootDirectory === 'string' ? state.lastRootDirectory : defaultState.lastRootDirectory,
            expandedFolders: Array.isArray(state.expandedFolders) ? state.expandedFolders : defaultState.expandedFolders,
            searchFilters: typeof state.searchFilters === 'object' ? state.searchFilters : defaultState.searchFilters,
            sortPreferences: typeof state.sortPreferences === 'object' ? state.sortPreferences : defaultState.sortPreferences,
            uiState: typeof state.uiState === 'object' ? state.uiState : defaultState.uiState,
            recentPrompts: Array.isArray(state.recentPrompts) ? state.recentPrompts : defaultState.recentPrompts,
            favoritePrompts: Array.isArray(state.favoritePrompts) ? state.favoritePrompts : defaultState.favoritePrompts,
            lastSession: {
                timestamp: new Date(),
                version: this.STATE_VERSION
            }
        };
    }

    /**
     * Dispose of resources
     */
    dispose(): void {
        // Clear current state cache
        this.currentState = null;
        logger.info('SessionStateManager disposed');
    }
}
