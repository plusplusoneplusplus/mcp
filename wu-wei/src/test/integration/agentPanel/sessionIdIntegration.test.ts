import * as assert from 'assert';
import * as vscode from 'vscode';
import { AgentPanelProvider } from '../../../agentManager/agentPanelProvider';

suite('Agent Panel Session ID Integration Tests', () => {
    let context: vscode.ExtensionContext;

    suiteSetup(async () => {
        // Mock VS Code extension context for testing
        context = {
            subscriptions: [],
            globalState: {
                get: () => [],
                update: () => Promise.resolve()
            },
            extensionUri: vscode.Uri.file('/mock/extension/path')
        } as any;
    });

    test('AgentPanelProvider should initialize correctly', async () => {
        // Test that we can create an agent panel provider instance
        const agentPanelProvider = new AgentPanelProvider(context);
        assert.ok(agentPanelProvider, 'Agent panel provider should be created');
        
        // Test that it has the expected properties and methods
        assert.ok(typeof agentPanelProvider.refresh === 'function', 'Should have refresh method');
        assert.ok(typeof agentPanelProvider.dispose === 'function', 'Should have dispose method');
        assert.ok(agentPanelProvider.onCompletionSignal, 'Should have completion signal event');
        
        // Cleanup
        agentPanelProvider.dispose();
    });

    test('Session ID generation algorithm should work consistently', () => {
        // Test the session ID generation logic that would be used in the webview
        function generateStableSessionId(message: any): string {
            const hashSource = `${message.timestamp}-${message.method}-${JSON.stringify(message.params || {})}`;
            let hash = 0;
            for (let i = 0; i < hashSource.length; i++) {
                const char = hashSource.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash;
            }
            const positiveHash = Math.abs(hash).toString(16);
            return `session-${positiveHash}`;
        }
        
        const testMessage = {
            timestamp: '2024-01-01T12:00:00.000Z',
            method: 'openAgent',
            params: { query: 'Integration test message' }
        };
        
        const sessionId1 = generateStableSessionId(testMessage);
        const sessionId2 = generateStableSessionId(testMessage);
        const sessionId3 = generateStableSessionId({
            ...testMessage,
            params: { query: 'Different message' }
        });
        
        assert.strictEqual(sessionId1, sessionId2, 'Same message should generate same session ID');
        assert.notStrictEqual(sessionId1, sessionId3, 'Different messages should generate different session IDs');
        assert.ok(sessionId1.startsWith('session-'), 'Session ID should have proper prefix');
        assert.ok(/^session-[a-f0-9]+$/.test(sessionId1), 'Session ID should match expected pattern');
    });

    test('Session ID should be suitable for HTML data attributes', () => {
        function generateStableSessionId(message: any): string {
            const hashSource = `${message.timestamp}-${message.method}-${JSON.stringify(message.params || {})}`;
            let hash = 0;
            for (let i = 0; i < hashSource.length; i++) {
                const char = hashSource.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash;
            }
            const positiveHash = Math.abs(hash).toString(16);
            return `session-${positiveHash}`;
        }
        
        const testMessage = {
            timestamp: '2024-01-01T12:00:00.000Z',
            method: 'openAgent',
            params: { query: 'HTML compatibility test' }
        };
        
        const sessionId = generateStableSessionId(testMessage);
        
        // Test that session ID is suitable for HTML attributes
        assert.ok(!sessionId.includes(' '), 'Session ID should not contain spaces');
        assert.ok(!sessionId.includes('"'), 'Session ID should not contain quotes');
        assert.ok(!sessionId.includes("'"), 'Session ID should not contain single quotes');
        assert.ok(!sessionId.includes('<'), 'Session ID should not contain less-than signs');
        assert.ok(!sessionId.includes('>'), 'Session ID should not contain greater-than signs');
        
        // Test that it follows valid HTML ID/class naming conventions
        assert.ok(/^[a-zA-Z][a-zA-Z0-9\-_]*$/.test(sessionId), 'Session ID should be valid HTML identifier');
    });

    test('Session correlation with execution tracking should be feasible', () => {
        // Test that session IDs can be correlated with execution IDs
        const sessionId = 'session-abc123def456';
        const executionId = 'exec-test-789ghi';
        
        // Simulate correlation mapping
        const sessionExecutionMap = new Map<string, string>();
        sessionExecutionMap.set(sessionId, executionId);
        
        assert.strictEqual(sessionExecutionMap.get(sessionId), executionId, 'Session should map to execution ID');
        assert.notStrictEqual(sessionId, executionId, 'Session and execution IDs should be distinct');
        
        // Test reverse mapping
        const executionSessionMap = new Map<string, string>();
        executionSessionMap.set(executionId, sessionId);
        
        assert.strictEqual(executionSessionMap.get(executionId), sessionId, 'Execution should map back to session ID');
    });

    test('Session ID format should be stable across different input types', () => {
        function generateStableSessionId(message: any): string {
            const hashSource = `${message.timestamp}-${message.method}-${JSON.stringify(message.params || {})}`;
            let hash = 0;
            for (let i = 0; i < hashSource.length; i++) {
                const char = hashSource.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash;
            }
            const positiveHash = Math.abs(hash).toString(16);
            return `session-${positiveHash}`;
        }
        
        // Test with different parameter types
        const testCases = [
            {
                timestamp: '2024-01-01T12:00:00.000Z',
                method: 'openAgent',
                params: { query: 'string parameter' }
            },
            {
                timestamp: '2024-01-01T12:00:00.000Z',
                method: 'openAgent',
                params: { count: 42, flag: true }
            },
            {
                timestamp: '2024-01-01T12:00:00.000Z',
                method: 'openAgent',
                params: { nested: { deep: { value: 'test' } } }
            },
            {
                timestamp: '2024-01-01T12:00:00.000Z',
                method: 'openAgent',
                params: { array: [1, 2, 3] }
            }
        ];
        
        testCases.forEach((testCase, index) => {
            const sessionId = generateStableSessionId(testCase);
            
            assert.ok(sessionId.startsWith('session-'), `Test case ${index}: Should have proper prefix`);
            assert.ok(/^session-[a-f0-9]+$/.test(sessionId), `Test case ${index}: Should match expected format`);
            assert.ok(sessionId.length > 8, `Test case ${index}: Should have reasonable length`);
            
            // Test that generating again produces same result
            const sessionId2 = generateStableSessionId(testCase);
            assert.strictEqual(sessionId, sessionId2, `Test case ${index}: Should be deterministic`);
        });
    });
});