/**
 * Unit tests for SessionStateManager
 * Testing wu wei principle: minimal state, natural persistence
 */

import assert from 'assert';
import * as vscode from 'vscode';
import { SessionStateManager, SessionState, SearchFilters, SortPreferences, UIState } from '../../promptStore/SessionStateManager';

suite('SessionStateManager Tests', () => {
    let sessionManager: SessionStateManager;
    let mockContext: vscode.ExtensionContext;
    let workspaceState: Map<string, any>;
    let globalState: Map<string, any>;

    setup(() => {
        // Create mock storage maps
        workspaceState = new Map();
        globalState = new Map();

        // Create mock context
        mockContext = {
            subscriptions: [],
            workspaceState: {
                get: (key: string) => workspaceState.get(key),
                update: async (key: string, value: any) => {
                    if (value === undefined) {
                        workspaceState.delete(key);
                    } else {
                        workspaceState.set(key, value);
                    }
                }
            },
            globalState: {
                get: (key: string) => globalState.get(key),
                update: async (key: string, value: any) => {
                    if (value === undefined) {
                        globalState.delete(key);
                    } else {
                        globalState.set(key, value);
                    }
                }
            }
        } as any;

        sessionManager = new SessionStateManager(mockContext);
    });

    teardown(() => {
        sessionManager.dispose();
    });

    suite('Initialization', () => {
        test('Should create SessionStateManager instance', () => {
            assert(sessionManager instanceof SessionStateManager);
        });

        test('Should provide default state when no stored state exists', () => {
            const state = sessionManager.getState();

            assert(typeof state === 'object');
            assert(Array.isArray(state.expandedFolders));
            assert(typeof state.searchFilters === 'object');
            assert(typeof state.sortPreferences === 'object');
            assert(typeof state.uiState === 'object');
            assert(Array.isArray(state.recentPrompts));
            assert(Array.isArray(state.favoritePrompts));
        });

        test('Should have proper default values', () => {
            const state = sessionManager.getState();

            assert.strictEqual(state.expandedFolders.length, 0);
            assert.strictEqual(state.sortPreferences.field, 'name');
            assert.strictEqual(state.sortPreferences.direction, 'asc');
            assert.strictEqual(state.uiState.viewMode, 'list');
            assert.strictEqual(state.uiState.showPreview, true);
            assert.strictEqual(state.uiState.showMetadata, true);
            assert.strictEqual(state.uiState.groupBy, 'none');
            assert.strictEqual(state.recentPrompts.length, 0);
            assert.strictEqual(state.favoritePrompts.length, 0);
        });
    });

    suite('State Updates', () => {
        test('Should update state with partial updates', async () => {
            const updates: Partial<SessionState> = {
                lastRootDirectory: '/test/path',
                expandedFolders: ['folder1', 'folder2']
            };

            await sessionManager.updateState(updates);
            const state = sessionManager.getState();

            assert.strictEqual(state.lastRootDirectory, '/test/path');
            assert.deepStrictEqual(state.expandedFolders, ['folder1', 'folder2']);
        });

        test('Should preserve existing state when updating', async () => {
            // Set initial state
            await sessionManager.updateState({
                lastRootDirectory: '/initial/path',
                recentPrompts: ['prompt1']
            });

            // Update only part of the state
            await sessionManager.updateState({
                lastRootDirectory: '/new/path'
            });

            const state = sessionManager.getState();
            assert.strictEqual(state.lastRootDirectory, '/new/path');
            assert.deepStrictEqual(state.recentPrompts, ['prompt1']);
        });

        test('Should update lastSession timestamp on updates', async () => {
            const beforeUpdate = new Date();

            await sessionManager.updateState({ lastRootDirectory: '/test' });

            const state = sessionManager.getState();
            assert(state.lastSession);
            assert(state.lastSession.timestamp >= beforeUpdate);
            assert.strictEqual(state.lastSession.version, '1.0.0');
        });
    });

    suite('Search Filters', () => {
        test('Should update search filters', async () => {
            const filters: SearchFilters = {
                query: 'test query',
                category: 'development',
                tags: ['tag1', 'tag2']
            };

            await sessionManager.updateSearchFilters(filters);
            const state = sessionManager.getState();

            assert.deepStrictEqual(state.searchFilters, filters);
        });

        test('Should handle empty search filters', async () => {
            await sessionManager.updateSearchFilters({});
            const state = sessionManager.getState();

            assert(typeof state.searchFilters === 'object');
            assert.strictEqual(Object.keys(state.searchFilters).length, 0);
        });
    });

    suite('Sort Preferences', () => {
        test('Should update sort preferences', async () => {
            const sortPrefs: SortPreferences = {
                field: 'modified',
                direction: 'desc'
            };

            await sessionManager.updateSortPreferences(sortPrefs);
            const state = sessionManager.getState();

            assert.deepStrictEqual(state.sortPreferences, sortPrefs);
        });

        test('Should validate sort field values', async () => {
            const validSortPrefs: SortPreferences = {
                field: 'category',
                direction: 'asc'
            };

            await sessionManager.updateSortPreferences(validSortPrefs);
            const state = sessionManager.getState();

            assert.strictEqual(state.sortPreferences.field, 'category');
            assert.strictEqual(state.sortPreferences.direction, 'asc');
        });
    });

    suite('UI State', () => {
        test('Should update UI state partially', async () => {
            await sessionManager.updateUIState({
                viewMode: 'grid',
                showPreview: false
            });

            const state = sessionManager.getState();
            assert.strictEqual(state.uiState.viewMode, 'grid');
            assert.strictEqual(state.uiState.showPreview, false);
            assert.strictEqual(state.uiState.showMetadata, true); // Should preserve existing
        });

        test('Should update individual UI state properties', async () => {
            await sessionManager.updateUIState({ sidebarWidth: 300 });
            await sessionManager.updateUIState({ selectedPromptId: 'prompt123' });
            await sessionManager.updateUIState({ groupBy: 'category' });

            const state = sessionManager.getState();
            assert.strictEqual(state.uiState.sidebarWidth, 300);
            assert.strictEqual(state.uiState.selectedPromptId, 'prompt123');
            assert.strictEqual(state.uiState.groupBy, 'category');
        });
    });

    suite('Expanded Folders', () => {
        test('Should expand folder', async () => {
            await sessionManager.expandFolder('/path/folder1');
            await sessionManager.expandFolder('/path/folder2');

            const state = sessionManager.getState();
            assert(state.expandedFolders.includes('/path/folder1'));
            assert(state.expandedFolders.includes('/path/folder2'));
        });

        test('Should not duplicate expanded folders', async () => {
            await sessionManager.expandFolder('/path/folder1');
            await sessionManager.expandFolder('/path/folder1'); // Duplicate

            const state = sessionManager.getState();
            const count = state.expandedFolders.filter(f => f === '/path/folder1').length;
            assert.strictEqual(count, 1);
        });

        test('Should collapse folder', async () => {
            await sessionManager.expandFolder('/path/folder1');
            await sessionManager.expandFolder('/path/folder2');
            await sessionManager.collapseFolder('/path/folder1');

            const state = sessionManager.getState();
            assert(!state.expandedFolders.includes('/path/folder1'));
            assert(state.expandedFolders.includes('/path/folder2'));
        });

        test('Should check if folder is expanded', async () => {
            await sessionManager.expandFolder('/path/folder1');

            assert(sessionManager.isFolderExpanded('/path/folder1'));
            assert(!sessionManager.isFolderExpanded('/path/folder2'));
        });
    });

    suite('Recent Prompts', () => {
        test('Should add recent prompt', async () => {
            await sessionManager.addRecentPrompt('prompt1');
            await sessionManager.addRecentPrompt('prompt2');

            const recentPrompts = sessionManager.getRecentPrompts();
            assert.deepStrictEqual(recentPrompts, ['prompt2', 'prompt1']);
        });

        test('Should move existing prompt to top when re-added', async () => {
            await sessionManager.addRecentPrompt('prompt1');
            await sessionManager.addRecentPrompt('prompt2');
            await sessionManager.addRecentPrompt('prompt1'); // Re-add

            const recentPrompts = sessionManager.getRecentPrompts();
            assert.deepStrictEqual(recentPrompts, ['prompt1', 'prompt2']);
        });

        test('Should limit recent prompts to maximum count', async () => {
            // Add more than the maximum (20)
            for (let i = 0; i < 25; i++) {
                await sessionManager.addRecentPrompt(`prompt${i}`);
            }

            const recentPrompts = sessionManager.getRecentPrompts();
            assert.strictEqual(recentPrompts.length, 20);
            assert.strictEqual(recentPrompts[0], 'prompt24'); // Most recent
            assert.strictEqual(recentPrompts[19], 'prompt5'); // Oldest kept
        });
    });

    suite('Favorite Prompts', () => {
        test('Should add prompt to favorites', async () => {
            await sessionManager.toggleFavoritePrompt('prompt1');

            const favoritePrompts = sessionManager.getFavoritePrompts();
            assert(favoritePrompts.includes('prompt1'));
            assert(sessionManager.isPromptFavorite('prompt1'));
        });

        test('Should remove prompt from favorites when toggled again', async () => {
            await sessionManager.toggleFavoritePrompt('prompt1');
            await sessionManager.toggleFavoritePrompt('prompt1'); // Toggle off

            const favoritePrompts = sessionManager.getFavoritePrompts();
            assert(!favoritePrompts.includes('prompt1'));
            assert(!sessionManager.isPromptFavorite('prompt1'));
        });

        test('Should handle multiple favorite prompts', async () => {
            await sessionManager.toggleFavoritePrompt('prompt1');
            await sessionManager.toggleFavoritePrompt('prompt2');
            await sessionManager.toggleFavoritePrompt('prompt3');

            const favoritePrompts = sessionManager.getFavoritePrompts();
            assert.strictEqual(favoritePrompts.length, 3);
            assert(favoritePrompts.includes('prompt1'));
            assert(favoritePrompts.includes('prompt2'));
            assert(favoritePrompts.includes('prompt3'));
        });
    });

    suite('Root Directory', () => {
        test('Should set last root directory', async () => {
            await sessionManager.setLastRootDirectory('/test/directory');

            const state = sessionManager.getState();
            assert.strictEqual(state.lastRootDirectory, '/test/directory');
        });

        test('Should update root directory', async () => {
            await sessionManager.setLastRootDirectory('/initial/directory');
            await sessionManager.setLastRootDirectory('/new/directory');

            const state = sessionManager.getState();
            assert.strictEqual(state.lastRootDirectory, '/new/directory');
        });
    });

    suite('State Persistence', () => {
        test('Should store state in workspace and global storage', async () => {
            await sessionManager.updateState({
                lastRootDirectory: '/workspace/path',
                recentPrompts: ['prompt1', 'prompt2'],
                favoritePrompts: ['fav1']
            });

            // Check workspace state (directory should be there)
            const workspaceData = workspaceState.get('promptStoreState');
            assert(workspaceData);
            assert.strictEqual(workspaceData.lastRootDirectory, '/workspace/path');

            // Check global state (favorites should be there)
            const globalData = globalState.get('promptStoreGlobalState');
            assert(globalData);
            assert.deepStrictEqual(globalData.favoritePrompts, ['fav1']);
        });

        test('Should load existing state from storage', () => {
            // Pre-populate storage
            workspaceState.set('promptStoreState', {
                lastRootDirectory: '/stored/path',
                expandedFolders: ['folder1']
            });
            globalState.set('promptStoreGlobalState', {
                recentPrompts: ['stored1', 'stored2'],
                favoritePrompts: ['fav1']
            });

            // Create new manager to test loading
            const newManager = new SessionStateManager(mockContext);
            const state = newManager.getState();

            assert.strictEqual(state.lastRootDirectory, '/stored/path');
            assert.deepStrictEqual(state.expandedFolders, ['folder1']);
            assert.deepStrictEqual(state.recentPrompts, ['stored1', 'stored2']);
            assert.deepStrictEqual(state.favoritePrompts, ['fav1']);

            newManager.dispose();
        });

        test('Should clear all state', async () => {
            // Add some state
            await sessionManager.updateState({
                lastRootDirectory: '/test/path',
                recentPrompts: ['prompt1'],
                favoritePrompts: ['fav1']
            });

            // Clear state
            await sessionManager.clearState();

            // Check storage is cleared
            assert.strictEqual(workspaceState.get('promptStoreState'), undefined);
            assert.strictEqual(globalState.get('promptStoreGlobalState'), undefined);
        });
    });

    suite('State Management', () => {
        test('Should export state for backup', async () => {
            await sessionManager.updateState({
                lastRootDirectory: '/export/test',
                recentPrompts: ['prompt1'],
                favoritePrompts: ['fav1'],
                expandedFolders: ['folder1']
            });

            const exportedState = sessionManager.exportState();

            assert.strictEqual(exportedState.lastRootDirectory, '/export/test');
            assert.deepStrictEqual(exportedState.recentPrompts, ['prompt1']);
            assert.deepStrictEqual(exportedState.favoritePrompts, ['fav1']);
            assert.deepStrictEqual(exportedState.expandedFolders, ['folder1']);
        });

        test('Should import state from backup', async () => {
            const importState: SessionState = {
                lastRootDirectory: '/imported/path',
                expandedFolders: ['imported1', 'imported2'],
                searchFilters: { query: 'imported query' },
                sortPreferences: { field: 'modified', direction: 'desc' },
                uiState: {
                    viewMode: 'grid',
                    showPreview: false,
                    showMetadata: true,
                    groupBy: 'category'
                },
                recentPrompts: ['imported1', 'imported2'],
                favoritePrompts: ['importedFav'],
                lastSession: {
                    timestamp: new Date(),
                    version: '1.0.0'
                }
            };

            await sessionManager.importState(importState);
            const state = sessionManager.getState();

            assert.strictEqual(state.lastRootDirectory, '/imported/path');
            assert.deepStrictEqual(state.expandedFolders, ['imported1', 'imported2']);
            assert.strictEqual(state.searchFilters.query, 'imported query');
            assert.strictEqual(state.sortPreferences.field, 'modified');
            assert.strictEqual(state.uiState.viewMode, 'grid');
            assert.deepStrictEqual(state.recentPrompts, ['imported1', 'imported2']);
            assert.deepStrictEqual(state.favoritePrompts, ['importedFav']);
        });

        test('Should validate imported state', async () => {
            const invalidState = {
                lastRootDirectory: 123, // Invalid type
                expandedFolders: 'not an array', // Invalid type
                recentPrompts: 'not an array', // Invalid type
                favoritePrompts: ['valid'],
                searchFilters: 'not an object', // Invalid type
                sortPreferences: null, // Invalid
                uiState: 'not an object' // Invalid type
            } as any;

            await sessionManager.importState(invalidState);
            const state = sessionManager.getState();

            // Should fall back to defaults for invalid values
            assert(Array.isArray(state.expandedFolders));
            assert(Array.isArray(state.recentPrompts));
            assert.deepStrictEqual(state.favoritePrompts, ['valid']); // Valid value preserved
            assert(typeof state.searchFilters === 'object');
            assert(typeof state.sortPreferences === 'object');
            assert(typeof state.uiState === 'object');
        });
    });

    suite('State Cleanup', () => {
        test('Should cleanup state by trimming recent prompts', async () => {
            // Add more than maximum recent prompts
            const manyPrompts = Array.from({ length: 25 }, (_, i) => `prompt${i}`);
            await sessionManager.updateState({ recentPrompts: manyPrompts });

            await sessionManager.cleanupState();

            const state = sessionManager.getState();
            assert.strictEqual(state.recentPrompts.length, 20);
        });

        test('Should not modify state if cleanup not needed', async () => {
            const initialState = {
                recentPrompts: ['prompt1', 'prompt2'],
                favoritePrompts: ['fav1']
            };
            await sessionManager.updateState(initialState);

            await sessionManager.cleanupState();

            const state = sessionManager.getState();
            assert.deepStrictEqual(state.recentPrompts, ['prompt1', 'prompt2']);
            assert.deepStrictEqual(state.favoritePrompts, ['fav1']);
        });
    });

    suite('Error Handling', () => {
        test('Should handle storage errors gracefully', async () => {
            // Create context that throws on update
            const errorContext = {
                workspaceState: {
                    get: () => undefined,
                    update: async () => { throw new Error('Storage error'); }
                },
                globalState: {
                    get: () => undefined,
                    update: async () => { throw new Error('Storage error'); }
                }
            } as any;

            const errorManager = new SessionStateManager(errorContext);

            // Should throw error but not crash
            try {
                await errorManager.updateState({ lastRootDirectory: '/test' });
                assert.fail('Should have thrown error');
            } catch (error: any) {
                assert(error.message.includes('Storage error'));
            }

            errorManager.dispose();
        });

        test('Should handle corrupted storage data gracefully', () => {
            // Set corrupted data in storage
            workspaceState.set('promptStoreState', 'corrupted string instead of object');
            globalState.set('promptStoreGlobalState', null);

            const newManager = new SessionStateManager(mockContext);
            const state = newManager.getState();

            // Should provide defaults when storage is corrupted
            assert(typeof state === 'object');
            assert(Array.isArray(state.expandedFolders));
            assert(Array.isArray(state.recentPrompts));

            newManager.dispose();
        });
    });
}); 