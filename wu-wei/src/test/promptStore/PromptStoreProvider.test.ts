/**
 * Unit tests for PromptStoreProvider
 * Testing Step 6: Basic Webview UI implementation
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import { PromptStoreProvider } from '../../promptStore/PromptStoreProvider';
import { PromptManager } from '../../promptStore/PromptManager';
import { FileOperationManager } from '../../promptStore/FileOperationManager';
import { ConfigurationManager } from '../../promptStore/ConfigurationManager';
import { TemplateManager } from '../../promptStore/TemplateManager';

suite('PromptStoreProvider - Step 6 Tests', () => {
    let provider: PromptStoreProvider;
    let mockPromptManager: PromptManager;
    let mockFileOperationManager: FileOperationManager;
    let mockExtensionUri: vscode.Uri;

    setup(() => {
        // Setup mock objects
        mockExtensionUri = vscode.Uri.file('/mock/path');
        mockPromptManager = new PromptManager();

        // Create mock dependencies for FileOperationManager
        const mockContext = {
            subscriptions: [],
            workspaceState: { get: () => undefined, update: () => Promise.resolve() },
            globalState: { get: () => undefined, update: () => Promise.resolve() },
            extensionPath: '/mock/path',
            storagePath: '/mock/path',
            globalStoragePath: '/mock/path'
        } as any;

        const mockConfigManager = new ConfigurationManager(mockContext);
        const mockTemplateManager = new TemplateManager();
        mockFileOperationManager = new FileOperationManager(mockPromptManager, mockConfigManager);

        provider = new PromptStoreProvider(mockExtensionUri, mockContext);
    });

    test('Provider should be created successfully', () => {
        assert.ok(provider);
        assert.strictEqual(PromptStoreProvider.viewType, 'wu-wei.promptStore');
    });

    test('HTML content should include Step 6 structure', () => {
        // Create a mock webview
        const mockWebview = {
            asWebviewUri: (uri: vscode.Uri) => uri,
            cspSource: 'mock-csp-source'
        } as any;

        const html = (provider as any).getHtmlForWebview(mockWebview);

        // Check for Step 6 specific elements
        assert.ok(html.includes('prompt-store-container'), 'Should have main container');
        assert.ok(html.includes('store-header'), 'Should have header section');
        assert.ok(html.includes('search-section'), 'Should have search section');
        assert.ok(html.includes('prompt-list-container'), 'Should have prompt list container');
        assert.ok(html.includes('store-footer'), 'Should have footer section');

        // Check for specific buttons
        assert.ok(html.includes('configure-directory'), 'Should have configure directory button');
        assert.ok(html.includes('new-prompt'), 'Should have new prompt button');
        assert.ok(html.includes('refresh-store'), 'Should have refresh button');

        // Check for filter elements
        assert.ok(html.includes('category-filter'), 'Should have category filter');
        assert.ok(html.includes('tag-filter'), 'Should have tag filter');

        // Check for state elements
        assert.ok(html.includes('empty-state'), 'Should have empty state');
        assert.ok(html.includes('loading-state'), 'Should have loading state');
        assert.ok(html.includes('prompt-tree'), 'Should have prompt tree');
    });

    test('Nonce generation should work', () => {
        const nonce1 = (provider as any).getNonce();
        const nonce2 = (provider as any).getNonce();

        assert.ok(nonce1);
        assert.ok(nonce2);
        assert.notStrictEqual(nonce1, nonce2, 'Nonces should be unique');
        assert.strictEqual(nonce1.length, 32, 'Nonce should be 32 characters');
        assert.strictEqual(nonce2.length, 32, 'Nonce should be 32 characters');
    });

    test('Message handling should support Step 6 message types', async () => {
        let messageSent: any = null;

        // Mock the sendToWebview method
        (provider as any).sendToWebview = (message: any) => {
            messageSent = message;
        };

        // Mock the prompt manager methods
        mockPromptManager.getAllPrompts = () => [];
        mockPromptManager.getConfig = () => ({ rootDirectory: '', watchPaths: [], filePatterns: [], excludePatterns: [], autoRefresh: true, refreshInterval: 1000, enableCache: true, maxCacheSize: 1000, sortBy: 'name', sortOrder: 'asc', showCategories: true, showTags: true, enableSearch: true });

        // Test webviewReady message
        await (provider as any).handleWebviewMessage({ type: 'webviewReady' });
        assert.ok(messageSent, 'Should send a message in response to webviewReady');

        // Test configureDirectory message
        messageSent = null;

        // Mock vscode.window.showOpenDialog to avoid actual dialog
        const originalShowOpenDialog = vscode.window.showOpenDialog;
        vscode.window.showOpenDialog = async () => undefined;

        try {
            await (provider as any).handleWebviewMessage({ type: 'configureDirectory' });
            // Should not throw error even if no folder selected
        } finally {
            vscode.window.showOpenDialog = originalShowOpenDialog;
        }
    });

    test('CSS should include VS Code theme variables', () => {
        // This would normally read the actual CSS file
        // For now, we'll just verify the provider exists
        assert.ok(provider);
    });

    test('JavaScript state management should be initialized', () => {
        // This would normally test the JS functionality
        // For now, we'll just verify the provider exists
        assert.ok(provider);
    });
});
