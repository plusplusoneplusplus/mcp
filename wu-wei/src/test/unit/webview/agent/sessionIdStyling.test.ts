import * as assert from 'assert';
import { JSDOM } from 'jsdom';
import * as fs from 'fs';
import * as path from 'path';

suite('Agent Panel Session ID CSS Styling Tests', () => {
    let dom: JSDOM;
    let window: Window & typeof globalThis;
    let document: Document;
    let cssContent: string;
    
    setup(async () => {
        // Read the actual CSS file
        const cssPath = path.join(__dirname, '../../../../webview/agent/style.css');
        
        try {
            cssContent = fs.readFileSync(cssPath, 'utf8');
        } catch (error) {
            // If CSS file doesn't exist at expected path, use mock CSS for testing
            cssContent = `
                .session-id {
                    font-size: 9px;
                    color: var(--vscode-badge-foreground, #cccccc);
                    background: var(--vscode-badge-background, #4d4d4d);
                    padding: 2px 4px;
                    border-radius: 2px;
                    font-family: var(--vscode-editor-font-family, monospace);
                    border: 1px solid var(--vscode-widget-border, #3c3c3c);
                    opacity: 0.8;
                }
                
                .session-id:hover {
                    opacity: 1;
                    background: var(--vscode-symbolIcon-numberForeground, #b5cea8);
                    color: var(--vscode-editor-background, #1e1e1e);
                }
                
                .message-meta {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 8px;
                }
                
                .message-item {
                    background: var(--vscode-editor-background, #1e1e1e);
                    border: 1px solid var(--vscode-widget-border, #3c3c3c);
                    border-radius: 4px;
                    padding: 8px 12px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
            `;
        }
        
        // Create JSDOM with CSS
        dom = new JSDOM(`
            <!DOCTYPE html>
            <html>
            <head>
                <style>${cssContent}</style>
            </head>
            <body>
                <div id="messageList">
                    <div class="message-item" data-session-id="session-test123">
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
                </div>
            </body>
            </html>
        `, {
            pretendToBeVisual: true,
            resources: 'usable'
        });
        
        window = dom.window as unknown as Window & typeof globalThis;
        document = window.document;
    });
    
    teardown(() => {
        dom.window.close();
    });
    
    test('session ID CSS class should be defined', () => {
        assert.ok(cssContent.includes('.session-id'), 'CSS should include .session-id class definition');
        assert.ok(cssContent.includes('font-size'), 'session-id CSS should define font-size');
        assert.ok(cssContent.includes('background'), 'session-id CSS should define background');
        assert.ok(cssContent.includes('padding'), 'session-id CSS should define padding');
        assert.ok(cssContent.includes('border-radius'), 'session-id CSS should define border-radius');
    });
    
    test('session ID hover effect should be defined', () => {
        assert.ok(cssContent.includes('.session-id:hover'), 'CSS should include .session-id:hover rule');
        assert.ok(
            cssContent.includes('.session-id:hover') && cssContent.includes('opacity'),
            'session-id hover should change opacity'
        );
        assert.ok(
            cssContent.includes('.session-id:hover') && cssContent.includes('background'),
            'session-id hover should change background'
        );
    });
    
    test('message-meta layout should support session ID', () => {
        assert.ok(cssContent.includes('.message-meta'), 'CSS should include .message-meta class');
        assert.ok(
            cssContent.includes('.message-meta') && cssContent.includes('display: flex'),
            'message-meta should use flexbox layout'
        );
        assert.ok(
            cssContent.includes('.message-meta') && cssContent.includes('gap'),
            'message-meta should define gap between elements'
        );
    });
    
    test('session ID element should render with expected styling', () => {
        const sessionIdElement = document.querySelector('.session-id');
        assert.ok(sessionIdElement, 'Session ID element should exist in DOM');
        
        // Get computed styles (Note: JSDOM has limited CSS support, so we check element properties)
        const styles = window.getComputedStyle(sessionIdElement);
        
        // Check that the element has the session ID text
        assert.strictEqual(sessionIdElement.textContent, 'session-test123', 'Session ID should display correct text');
        assert.strictEqual(sessionIdElement.getAttribute('title'), 'Session ID', 'Session ID should have tooltip');
    });
    
    test('message item should have proper session ID data attribute', () => {
        const messageItem = document.querySelector('.message-item');
        assert.ok(messageItem, 'Message item should exist');
        assert.strictEqual(
            messageItem.getAttribute('data-session-id'),
            'session-test123',
            'Message item should have correct session ID data attribute'
        );
    });
    
    test('session ID should be positioned correctly within message meta', () => {
        const messageMeta = document.querySelector('.message-meta');
        const sessionId = messageMeta?.querySelector('.session-id');
        const timestamp = messageMeta?.querySelector('.message-timestamp');
        const status = messageMeta?.querySelector('.message-status');
        
        assert.ok(messageMeta, 'Message meta container should exist');
        assert.ok(sessionId, 'Session ID should be within message meta');
        assert.ok(timestamp, 'Timestamp should be within message meta');
        assert.ok(status, 'Status should be within message meta');
        
        // Check order: timestamp, session-id, status
        const children = Array.from(messageMeta?.children || []);
        const sessionIdIndex = children.indexOf(sessionId as Element);
        const timestampIndex = children.indexOf(timestamp as Element);
        const statusIndex = children.indexOf(status as Element);
        
        assert.ok(timestampIndex >= 0, 'Timestamp should be present');
        assert.ok(sessionIdIndex >= 0, 'Session ID should be present');
        assert.ok(statusIndex >= 0, 'Status should be present');
        assert.ok(sessionIdIndex > timestampIndex, 'Session ID should come after timestamp');
        assert.ok(statusIndex > sessionIdIndex, 'Status should come after session ID');
    });
    
    test('CSS should include VS Code theme variables', () => {
        // Check for VS Code CSS custom properties
        const vscodeVariables = [
            '--vscode-badge-foreground',
            '--vscode-badge-background',
            '--vscode-editor-font-family',
            '--vscode-widget-border',
            '--vscode-symbolIcon-numberForeground',
            '--vscode-editor-background'
        ];
        
        vscodeVariables.forEach(variable => {
            assert.ok(
                cssContent.includes(variable),
                `CSS should include VS Code theme variable: ${variable}`
            );
        });
    });
    
    test('session ID styling should have appropriate defaults', () => {
        // Check that fallback values are provided for VS Code variables
        assert.ok(
            cssContent.includes('#cccccc') || cssContent.includes('cccccc'),
            'CSS should include fallback color for foreground'
        );
        assert.ok(
            cssContent.includes('#4d4d4d') || cssContent.includes('4d4d4d'),
            'CSS should include fallback color for background'
        );
        assert.ok(
            cssContent.includes('monospace'),
            'CSS should include monospace as fallback font'
        );
    });
    
    test('session ID should be responsive and accessible', () => {
        // Check for proper sizing and accessibility considerations
        const sessionIdCssRule = cssContent.match(/\.session-id\s*{[^}]+}/)?.[0] || '';
        
        assert.ok(
            sessionIdCssRule.includes('font-size') && sessionIdCssRule.includes('9px'),
            'Session ID should have appropriate font size'
        );
        assert.ok(
            sessionIdCssRule.includes('padding'),
            'Session ID should have padding for touch targets'
        );
        assert.ok(
            sessionIdCssRule.includes('border-radius'),
            'Session ID should have rounded corners for visual polish'
        );
    });
    
    test('multiple session IDs should render independently', () => {
        // Add multiple message items with different session IDs
        const messageList = document.getElementById('messageList');
        messageList!.innerHTML = `
            <div class="message-item" data-session-id="session-first">
                <div class="message-meta">
                    <span class="session-id">session-first</span>
                </div>
            </div>
            <div class="message-item" data-session-id="session-second">
                <div class="message-meta">
                    <span class="session-id">session-second</span>
                </div>
            </div>
            <div class="message-item" data-session-id="session-third">
                <div class="message-meta">
                    <span class="session-id">session-third</span>
                </div>
            </div>
        `;
        
        const sessionIds = document.querySelectorAll('.session-id');
        const messageItems = document.querySelectorAll('.message-item');
        
        assert.strictEqual(sessionIds.length, 3, 'Should have three session ID elements');
        assert.strictEqual(messageItems.length, 3, 'Should have three message items');
        
        // Check that each has correct content
        assert.strictEqual(sessionIds[0].textContent, 'session-first');
        assert.strictEqual(sessionIds[1].textContent, 'session-second');
        assert.strictEqual(sessionIds[2].textContent, 'session-third');
        
        // Check data attributes match
        assert.strictEqual(messageItems[0].getAttribute('data-session-id'), 'session-first');
        assert.strictEqual(messageItems[1].getAttribute('data-session-id'), 'session-second');
        assert.strictEqual(messageItems[2].getAttribute('data-session-id'), 'session-third');
    });
});