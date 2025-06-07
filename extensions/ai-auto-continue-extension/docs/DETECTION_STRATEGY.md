# AI Agent Detection Strategy

## How the Extension Knows When to Continue

### Current Approach (Based on Original Gist)
The original extension uses a **simple polling approach**:
- Monitors the **active editor window only**
- Checks every 500ms for trigger text patterns
- Replaces trigger text when found

### Problem with Simple Approach
- **Limited Scope**: Only monitors the active text editor
- **Misses Chat Windows**: AI conversations often happen in separate panels/windows
- **False Positives**: May trigger on user-written code containing similar phrases

## Enhanced Detection Strategies

### 1. Multi-Window Monitoring
```
┌─────────────────┬─────────────────┐
│   Code Editor   │   AI Chat Panel │
│                 │                 │
│   // user code  │ AI: I've reached│
│                 │ my tool call    │
│                 │ limit of 25     │
│                 │                 │
│                 │ [AUTO-CONTINUE] │
└─────────────────┴─────────────────┘
```

**Strategy**: Monitor multiple window types:
- **Text Editors**: Main code editing windows
- **Terminal/Output Panels**: Where AI responses might appear
- **Webview Panels**: Chat interfaces in Cursor/Windsurf
- **Custom UI Elements**: AI-specific panels

### 2. Window Type Detection

#### A. Text Editor Windows
```typescript
// Monitor all open text editors
vscode.workspace.textDocuments.forEach(doc => {
    // Check for AI conversation patterns
    if (containsAIConversation(doc.getText())) {
        checkForTriggers(doc);
    }
});
```

#### B. Terminal/Output Windows
```typescript
// Monitor terminal output
vscode.window.terminals.forEach(terminal => {
    // Listen for terminal output containing AI responses
    terminal.processId.then(pid => {
        // Monitor terminal content for AI patterns
    });
});
```

#### C. Webview Panels (Cursor/Windsurf Chat)
```typescript
// Monitor webview panels where AI chat happens
vscode.window.onDidChangeActiveTextEditor(editor => {
    if (editor?.document.uri.scheme === 'webview') {
        // This is likely an AI chat panel
        monitorWebviewContent(editor);
    }
});
```

### 3. Smart Context Detection

#### Pattern Recognition
```typescript
const AI_CONTEXT_INDICATORS = [
    // Conversation starters
    /^(User:|Human:|Assistant:|AI:)/m,
    
    // AI model signatures
    /Claude|GPT|Copilot|Cursor|Windsurf/i,
    
    // Tool call patterns
    /tool_calls?|function_calls?|execute/i,
    
    // Conversation flow
    /```[\s\S]*```/g, // Code blocks in chat
];

function isAIConversationWindow(text: string): boolean {
    return AI_CONTEXT_INDICATORS.some(pattern => 
        pattern.test(text)
    );
}
```

#### Content Analysis
```typescript
function analyzeWindowContent(document: vscode.TextDocument) {
    const text = document.getText();
    
    // Check if this looks like an AI conversation
    const hasAIIndicators = isAIConversationWindow(text);
    const hasRecentActivity = wasRecentlyModified(document);
    const hasToolCallPatterns = containsToolCallPatterns(text);
    
    return {
        isAIWindow: hasAIIndicators,
        priority: calculatePriority(hasRecentActivity, hasToolCallPatterns),
        shouldMonitor: hasAIIndicators && hasRecentActivity
    };
}
```

### 4. Event-Driven Detection

#### Document Change Events
```typescript
vscode.workspace.onDidChangeTextDocument(event => {
    const document = event.document;
    
    // Only check recently changed documents
    if (isRecentChange(event) && isAIConversationWindow(document.getText())) {
        // Check for trigger patterns in the changes
        event.contentChanges.forEach(change => {
            checkForTriggersInText(change.text);
        });
    }
});
```

#### Window Focus Events
```typescript
vscode.window.onDidChangeActiveTextEditor(editor => {
    if (editor && isAIConversationWindow(editor.document.getText())) {
        // Start monitoring this window more frequently
        startIntensiveMonitoring(editor.document);
    }
});
```

### 5. IDE-Specific Detection

#### Cursor Detection
```typescript
function detectCursorAIPanel(): vscode.TextDocument | null {
    // Look for Cursor's specific AI chat patterns
    return vscode.workspace.textDocuments.find(doc => {
        const text = doc.getText();
        return text.includes('I\'ve reached my tool call limit') ||
               text.includes('Cursor AI') ||
               doc.uri.path.includes('cursor-chat');
    });
}
```

#### Windsurf Detection
```typescript
function detectWindsurfAIPanel(): vscode.TextDocument | null {
    // Look for Windsurf's specific patterns
    return vscode.workspace.textDocuments.find(doc => {
        const text = doc.getText();
        return text.includes('Windsurf') ||
               text.includes('I need to pause here due to limitations') ||
               doc.uri.scheme === 'windsurf-chat';
    });
}
```

## Recommended Implementation Strategy

### Phase 1: Multi-Document Monitoring
```typescript
class AIDetectionManager {
    private monitoredDocuments = new Set<string>();
    private checkInterval: NodeJS.Timeout;
    
    start() {
        // Monitor all documents, prioritize AI conversations
        this.checkInterval = setInterval(() => {
            this.scanAllDocuments();
        }, 500);
        
        // React to document changes immediately
        vscode.workspace.onDidChangeTextDocument(this.onDocumentChange);
    }
    
    private scanAllDocuments() {
        vscode.workspace.textDocuments.forEach(doc => {
            if (this.shouldMonitorDocument(doc)) {
                this.checkForTriggers(doc);
            }
        });
    }
    
    private shouldMonitorDocument(doc: vscode.TextDocument): boolean {
        // Check if document contains AI conversation
        const text = doc.getText();
        return isAIConversationWindow(text) && 
               wasRecentlyModified(doc);
    }
}
```

### Phase 2: Smart Prioritization
```typescript
interface DocumentPriority {
    document: vscode.TextDocument;
    priority: number;
    lastChecked: Date;
    isActive: boolean;
}

class SmartMonitoring {
    private documentPriorities: DocumentPriority[] = [];
    
    updatePriorities() {
        this.documentPriorities = vscode.workspace.textDocuments
            .map(doc => ({
                document: doc,
                priority: this.calculatePriority(doc),
                lastChecked: new Date(),
                isActive: doc === vscode.window.activeTextEditor?.document
            }))
            .sort((a, b) => b.priority - a.priority);
    }
    
    private calculatePriority(doc: vscode.TextDocument): number {
        let priority = 0;
        
        // Higher priority for active window
        if (doc === vscode.window.activeTextEditor?.document) priority += 100;
        
        // Higher priority for AI conversation windows
        if (isAIConversationWindow(doc.getText())) priority += 50;
        
        // Higher priority for recently modified
        if (wasRecentlyModified(doc)) priority += 25;
        
        return priority;
    }
}
```

### Phase 3: Performance Optimization
```typescript
class OptimizedDetection {
    private lastKnownContent = new Map<string, string>();
    
    checkForChanges(doc: vscode.TextDocument): boolean {
        const currentContent = doc.getText();
        const lastContent = this.lastKnownContent.get(doc.uri.toString());
        
        if (currentContent !== lastContent) {
            this.lastKnownContent.set(doc.uri.toString(), currentContent);
            
            // Only check the new content, not the entire document
            const newContent = this.extractNewContent(currentContent, lastContent);
            return this.checkTriggersInText(newContent);
        }
        
        return false;
    }
}
```

## Summary

The extension will:

1. **Monitor Multiple Windows**: Not just the active editor, but all open documents
2. **Smart Detection**: Identify which windows contain AI conversations
3. **Event-Driven**: React to document changes immediately, not just polling
4. **Performance Optimized**: Only check relevant windows and new content
5. **IDE-Specific**: Adapt to Cursor, Windsurf, and other AI IDE patterns

This approach ensures the extension catches AI pause messages regardless of which window or panel they appear in, while maintaining good performance and avoiding false positives. 