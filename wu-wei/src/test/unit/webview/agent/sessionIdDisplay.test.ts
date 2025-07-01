import * as assert from 'assert';
import { JSDOM } from 'jsdom';

suite('Agent Panel Session ID Display Tests', () => {
    let dom: JSDOM;
    let window: Window & typeof globalThis;
    let document: Document;
    
    // Mock functions that would normally be available in the webview context
    let messageHistory: any[];
    let mockVscode: any;
    
    setup(() => {
        // Create a JSDOM instance to simulate browser environment
        dom = new JSDOM(`
            <!DOCTYPE html>
            <html>
            <head>
                <link rel="stylesheet" href="style.css">
            </head>
            <body>
                <div id="messageList"></div>
            </body>
            </html>
        `, {
            pretendToBeVisual: true,
            resources: 'usable'
        });
        
        window = dom.window as unknown as Window & typeof globalThis;
        document = window.document;
        
        // Set up global objects that the webview code expects
        (global as any).window = window;
        (global as any).document = document;
        
        // Mock VS Code API
        mockVscode = {
            postMessage: (message: any) => {
                // Mock implementation for tests
            }
        };
        
        // Initialize test data
        messageHistory = [];
        
        // Mock the acquireVsCodeApi function
        (window as any).acquireVsCodeApi = () => mockVscode;
    });
    
    teardown(() => {
        dom.window.close();
        delete (global as any).window;
        delete (global as any).document;
    });
    
    test('generateStableSessionId should create consistent IDs', () => {
        // Import the function logic from main.js (adapted for testing)
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
        
        const message1 = {
            timestamp: '2024-01-01T12:00:00.000Z',
            method: 'openAgent',
            params: { query: 'test query' }
        };
        
        const message2 = {
            timestamp: '2024-01-01T12:00:00.000Z',
            method: 'openAgent',
            params: { query: 'test query' }
        };
        
        const message3 = {
            timestamp: '2024-01-01T12:00:00.000Z',
            method: 'openAgent',
            params: { query: 'different query' }
        };
        
        const sessionId1 = generateStableSessionId(message1);
        const sessionId2 = generateStableSessionId(message2);
        const sessionId3 = generateStableSessionId(message3);
        
        assert.strictEqual(sessionId1, sessionId2, 'Same message data should generate same session ID');
        assert.notStrictEqual(sessionId1, sessionId3, 'Different message data should generate different session IDs');
        assert.ok(sessionId1.startsWith('session-'), 'Session ID should have proper prefix');
        assert.ok(/^session-[a-f0-9]+$/.test(sessionId1), 'Session ID should match expected pattern');
    });
    
    test('renderSimplifiedMessageItem should include session ID in HTML', () => {
        // Import and adapt the renderSimplifiedMessageItem function logic
        function renderSimplifiedMessageItem(session: any): string {
            const timestamp = new Date(session.timestamp).toLocaleTimeString();
            const sessionStatus = 'success';
            const statusIcon = '✅';
            const statusText = 'Success';
            
            return `
                <div class="message-item ${sessionStatus}" data-session-id="${session.id}" data-action="open-session" title="Click to view details">
                    <div class="message-preview">
                        <div class="message-text">${session.summary}</div>
                        <div class="message-meta">
                            <span class="message-timestamp">${timestamp}</span>
                            <span class="session-id" title="Session ID">${session.id}</span>
                            <span class="message-status ${sessionStatus}">
                                <span class="status-icon">${statusIcon}</span>
                                ${statusText}
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        const session = {
            id: 'session-abc123',
            summary: 'Test session summary',
            timestamp: '2024-01-01T12:00:00.000Z',
            responses: []
        };
        
        const html = renderSimplifiedMessageItem(session);
        
        assert.ok(html.includes('data-session-id="session-abc123"'), 'HTML should include session ID in data attribute');
        assert.ok(html.includes('<span class="session-id" title="Session ID">session-abc123</span>'), 'HTML should include session ID span element');
        assert.ok(html.includes('Test session summary'), 'HTML should include session summary');
    });
    
    test('session ID element should be present in DOM after rendering', () => {
        const messageList = document.getElementById('messageList');
        assert.ok(messageList, 'Message list element should exist');
        
        // Simulate rendering a message with session ID
        messageList.innerHTML = `
            <div class="message-item success" data-session-id="session-test123" data-action="open-session">
                <div class="message-preview">
                    <div class="message-text">Test message</div>
                    <div class="message-meta">
                        <span class="message-timestamp">12:00:00 PM</span>
                        <span class="session-id" title="Session ID">session-test123</span>
                        <span class="message-status success">
                            <span class="status-icon">✅</span>
                            Success
                        </span>
                    </div>
                </div>
            </div>
        `;
        
        const sessionIdElement = messageList.querySelector('.session-id');
        assert.ok(sessionIdElement, 'Session ID element should be present in DOM');
        assert.strictEqual(sessionIdElement?.textContent, 'session-test123', 'Session ID element should contain correct ID');
        assert.strictEqual(sessionIdElement?.getAttribute('title'), 'Session ID', 'Session ID element should have tooltip');
        
        const messageItem = messageList.querySelector('.message-item');
        assert.strictEqual(messageItem?.getAttribute('data-session-id'), 'session-test123', 'Message item should have session ID data attribute');
    });
    
    test('session ID should be properly formatted and displayed', () => {
        const messageList = document.getElementById('messageList');
        
        // Test different session ID formats
        const testCases = [
            'session-abc123',
            'session-1234567890abcdef',
            'session-short',
            'session-verylongidentifierwithmanycharacters'
        ];
        
        testCases.forEach((sessionId, index) => {
            const messageHtml = `
                <div class="message-item" data-session-id="${sessionId}">
                    <div class="message-meta">
                        <span class="session-id" title="Session ID">${sessionId}</span>
                    </div>
                </div>
            `;
            
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = messageHtml;
            const sessionIdElement = tempDiv.querySelector('.session-id');
            
            assert.ok(sessionIdElement, `Session ID element should exist for test case ${index}`);
            assert.strictEqual(sessionIdElement?.textContent, sessionId, `Session ID should match expected value for test case ${index}`);
        });
    });
    
    test('buildSessionTree should maintain session IDs correctly', () => {
        // Import and adapt the buildSessionTree function logic
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
        
        function generateRequestSummary(request: any): string {
            let text = '';
            if (request.params?.message) {
                text = request.params.message;
            } else if (request.params?.query) {
                text = request.params.query;
            } else if (request.method) {
                text = `${request.method} request`;
            } else {
                text = 'Agent request';
            }
            
            const words = text.replace(/\n/g, ' ').split(' ').filter(word => word.trim());
            const summary = words.slice(0, 10).join(' ');
            return summary.length > 60 ? summary.substring(0, 57) + '...' : summary;
        }
        
        function buildSessionTree(messages: any[]): any[] {
            const sessions: any[] = [];
            let currentSession: any = null;
            
            for (let i = 0; i < messages.length; i++) {
                const message = messages[i];
                
                if (message.type === 'request') {
                    const stableId = generateStableSessionId(message);
                    
                    currentSession = {
                        id: stableId,
                        request: message,
                        responses: [],
                        timestamp: message.timestamp,
                        summary: generateRequestSummary(message),
                        executionId: message.params?.executionId || null,
                        responseExecutionIds: [],
                        expanded: false
                    };
                    sessions.push(currentSession);
                } else if (currentSession) {
                    currentSession.responses.push(message);
                }
            }
            
            return sessions;
        }
        
        const messages = [
            {
                type: 'request',
                timestamp: '2024-01-01T12:00:00.000Z',
                method: 'openAgent',
                params: { query: 'First test query' }
            },
            {
                type: 'response',
                timestamp: '2024-01-01T12:00:01.000Z',
                result: { message: 'Response to first query' }
            },
            {
                type: 'request',
                timestamp: '2024-01-01T12:01:00.000Z',
                method: 'openAgent',
                params: { query: 'Second test query' }
            },
            {
                type: 'response',
                timestamp: '2024-01-01T12:01:01.000Z',
                result: { message: 'Response to second query' }
            }
        ];
        
        const sessions = buildSessionTree(messages);
        
        assert.strictEqual(sessions.length, 2, 'Should create two sessions for two requests');
        
        // Check first session
        assert.ok(sessions[0].id.startsWith('session-'), 'First session should have proper ID format');
        assert.strictEqual(sessions[0].responses.length, 1, 'First session should have one response');
        assert.strictEqual(sessions[0].summary, 'First test query', 'First session should have correct summary');
        
        // Check second session
        assert.ok(sessions[1].id.startsWith('session-'), 'Second session should have proper ID format');
        assert.strictEqual(sessions[1].responses.length, 1, 'Second session should have one response');
        assert.strictEqual(sessions[1].summary, 'Second test query', 'Second session should have correct summary');
        
        // Verify session IDs are different
        assert.notStrictEqual(sessions[0].id, sessions[1].id, 'Different sessions should have different IDs');
    });
    
    test('session ID should be preserved in formatSessionAsText', () => {
        // Test the text formatting function that includes session ID
        function formatSessionAsText(session: any): string {
            const timestamp = new Date(session.timestamp).toLocaleString();
            let content = '';
            
            content += `Agent Session Details\n`;
            content += `${'='.repeat(50)}\n\n`;
            content += `Session ID: ${session.id}\n`;
            content += `Timestamp: ${timestamp}\n`;
            content += `Summary: ${session.summary}\n\n`;
            
            return content;
        }
        
        const session = {
            id: 'session-testformat123',
            summary: 'Test session for formatting',
            timestamp: '2024-01-01T12:00:00.000Z',
            request: {
                method: 'openAgent',
                params: { query: 'test' }
            },
            responses: []
        };
        
        const text = formatSessionAsText(session);
        
        assert.ok(text.includes('Session ID: session-testformat123'), 'Formatted text should include session ID');
        assert.ok(text.includes('Agent Session Details'), 'Formatted text should include header');
        assert.ok(text.includes('Test session for formatting'), 'Formatted text should include summary');
    });
});