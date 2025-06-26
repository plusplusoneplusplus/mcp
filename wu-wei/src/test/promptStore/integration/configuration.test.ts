/**
 * Integration tests for Configuration Management
 * Testing the complete configuration flow
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs/promises';
import { ConfigurationManager } from '../../../promptStore/ConfigurationManager';
import { SessionStateManager } from '../../../promptStore/SessionStateManager';

suite('Configuration Integration Tests', () => {
    let configManager: ConfigurationManager;
    let sessionStateManager: SessionStateManager;
    let mockContext: vscode.ExtensionContext;
    let testDirectory: string;

    suiteSetup(async () => {
        // Create a test directory
        testDirectory = path.join(__dirname, '..', '..', '..', '..', 'test-prompts');
        try {
            await fs.mkdir(testDirectory, { recursive: true });

            // Create a test prompt file
            await fs.writeFile(
                path.join(testDirectory, 'test-prompt.md'),
                '---\ntitle: Test Prompt\ndescription: A test prompt for configuration testing\n---\n\nThis is a test prompt.'
            );
        } catch (error) {
            console.log('Test directory setup failed:', error);
        }
    });

    suiteTeardown(async () => {
        // Clean up test directory
        try {
            await fs.rmdir(testDirectory, { recursive: true });
        } catch (error) {
            console.log('Test directory cleanup failed:', error);
        }
    });

    setup(() => {
        // Create mock context
        mockContext = {
            subscriptions: [],
            workspaceState: {
                get: () => undefined,
                update: async () => { }
            },
            globalState: {
                get: () => undefined,
                update: async () => { }
            }
        } as any;

        configManager = new ConfigurationManager(mockContext);
        sessionStateManager = new SessionStateManager(mockContext);
    });

    teardown(() => {
        configManager.dispose();
        sessionStateManager.dispose();
    });

    test('Should integrate configuration and session state managers', async () => {
        // Test that both managers can be created and work together
        const config = configManager.getConfig();
        const sessionState = sessionStateManager.getState();

        assert(typeof config === 'object');
        assert(typeof sessionState === 'object');

        // Test that session state can store the last root directory
        if (testDirectory) {
            await sessionStateManager.setLastRootDirectory(testDirectory);
            const updatedState = sessionStateManager.getState();
            assert.strictEqual(updatedState.lastRootDirectory, testDirectory);
        }
    });

    test('Should validate directory structure', async () => {
        // Test directory validation with the test directory
        const validation = await configManager.validateConfig({
            rootDirectory: testDirectory,
            autoRefresh: true,
            showMetadataTooltips: true,
            enableTemplates: true,
            metadataSchema: {
                requireTitle: true,
                requireDescription: false,
                allowCustomFields: true,
                validateParameters: true
            },
            fileWatcher: {
                enabled: true,
                debounceMs: 500,
                maxDepth: 10,
                ignorePatterns: ['*.tmp'],
                usePolling: false,
                pollingInterval: 1000
            }
        });

        // Should be valid if test directory exists
        if (testDirectory) {
            assert.strictEqual(validation.isValid, true);
        }
    });

    test('Should handle session state persistence', async () => {
        // Test various session state operations
        await sessionStateManager.addRecentPrompt('test-prompt-1');
        await sessionStateManager.addRecentPrompt('test-prompt-2');

        const recentPrompts = sessionStateManager.getRecentPrompts();
        assert(recentPrompts.includes('test-prompt-1'));
        assert(recentPrompts.includes('test-prompt-2'));
        assert.strictEqual(recentPrompts[0], 'test-prompt-2'); // Most recent first

        // Test favorites
        await sessionStateManager.toggleFavoritePrompt('test-prompt-1');
        assert(sessionStateManager.isPromptFavorite('test-prompt-1'));

        await sessionStateManager.toggleFavoritePrompt('test-prompt-1');
        assert(!sessionStateManager.isPromptFavorite('test-prompt-1'));
    });

    test('Should handle folder expansion state', async () => {
        const testFolder = '/test/folder/path';

        // Initially not expanded
        assert(!sessionStateManager.isFolderExpanded(testFolder));

        // Expand folder
        await sessionStateManager.expandFolder(testFolder);
        assert(sessionStateManager.isFolderExpanded(testFolder));

        // Collapse folder
        await sessionStateManager.collapseFolder(testFolder);
        assert(!sessionStateManager.isFolderExpanded(testFolder));
    });

    test('Should handle UI state updates', async () => {
        await sessionStateManager.updateUIState({
            viewMode: 'grid',
            showPreview: false,
            groupBy: 'category'
        });

        const state = sessionStateManager.getState();
        assert.strictEqual(state.uiState.viewMode, 'grid');
        assert.strictEqual(state.uiState.showPreview, false);
        assert.strictEqual(state.uiState.groupBy, 'category');
    });

    test('Should handle search filters', async () => {
        await sessionStateManager.updateSearchFilters({
            query: 'test query',
            category: 'test',
            tags: ['tag1', 'tag2'],
            hasParameters: true
        });

        const state = sessionStateManager.getState();
        assert.strictEqual(state.searchFilters.query, 'test query');
        assert.strictEqual(state.searchFilters.category, 'test');
        assert(Array.isArray(state.searchFilters.tags));
        assert.strictEqual(state.searchFilters.hasParameters, true);
    });

    test('Should export and import state', async () => {
        // Set up some state
        await sessionStateManager.addRecentPrompt('export-test');
        await sessionStateManager.toggleFavoritePrompt('favorite-test');
        await sessionStateManager.expandFolder('/test/export');

        // Export state
        const exportedState = sessionStateManager.exportState();

        assert(exportedState.recentPrompts.includes('export-test'));
        assert(exportedState.favoritePrompts.includes('favorite-test'));
        assert(exportedState.expandedFolders.includes('/test/export'));

        // Clear and import
        await sessionStateManager.clearState();
        await sessionStateManager.importState(exportedState);

        // Verify import
        const importedState = sessionStateManager.getState();
        assert(importedState.recentPrompts.includes('export-test'));
        assert(importedState.favoritePrompts.includes('favorite-test'));
        assert(importedState.expandedFolders.includes('/test/export'));
    });
});
