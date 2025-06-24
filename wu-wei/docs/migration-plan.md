# Wu Wei Extension Structure Migration Plan

## Overview
Migrate the Wu Wei extension from embedded HTML templates to a modern, scalable structure with separate files for HTML, CSS, and JavaScript while maintaining backward compatibility.

## Current Structure Analysis
```
src/
├── extension.ts
├── logger.ts
├── unifiedChatProvider.ts
├── debugPanel.ts
├── agentPanel.ts
├── agentInterface.ts
└── templates/
    ├── unifiedChat.html        # Embedded CSS/JS
    ├── debugPanel.html         # Embedded CSS/JS
    └── agentPanel.html         # Embedded CSS/JS
```

## Target Structure
```
src/
├── extension.ts
├── logger.ts
├── providers/                  # Webview providers
│   ├── unifiedChatProvider.ts
│   ├── debugPanelProvider.ts
│   └── agentPanelProvider.ts
├── interfaces/                 # Business logic interfaces
│   └── agentInterface.ts
└── webview/                   # All webview assets
    ├── shared/                # Common styles and utilities
    │   ├── base.css          # Common VS Code theme variables
    │   ├── components.css    # Reusable component styles
    │   └── utils.js          # Shared JavaScript utilities
    ├── chat/
    │   ├── index.html
    │   ├── main.js
    │   └── style.css
    ├── debug/
    │   ├── index.html
    │   ├── main.js
    │   └── style.css
    ├── agent/
    │   ├── index.html
    │   ├── main.js
    │   └── style.css
```

## Migration Phases

### Phase 1: Infrastructure Setup (No Breaking Changes)
**Estimated Time: 2-3 hours**

#### 1.1 Create New Directory Structure
```bash
mkdir -p src/webview/{shared,chat,debug,agent}
mkdir -p src/providers
mkdir -p src/interfaces
```

#### 1.2 Extract Common Styles
- Create `src/webview/shared/base.css` with VS Code theme variables
- Create `src/webview/shared/components.css` with reusable components
- Create `src/webview/shared/utils.js` for shared JavaScript utilities

#### 1.3 Migration Utilities
Create helper functions to:
- Extract embedded CSS from HTML templates
- Extract embedded JavaScript from HTML templates
- Generate separate files while maintaining functionality

### Phase 2: Existing Components Migration (Maintain Compatibility)
**Estimated Time: 4-6 hours**

#### 2.1 Unified Chat Migration
1. **Extract from `templates/unifiedChat.html`:**
   - HTML structure → `webview/chat/index.html`
   - CSS styles → `webview/chat/style.css`
   - JavaScript code → `webview/chat/main.js`

2. **Update `unifiedChatProvider.ts`:**
   - Move to `src/providers/unifiedChatProvider.ts`
   - Update HTML loading logic to reference separate files
   - Add resource URI handling for CSS/JS files

#### 2.2 Debug Panel Migration
1. **Extract from `templates/debugPanel.html`:**
   - HTML structure → `webview/debug/index.html`
   - CSS styles → `webview/debug/style.css`
   - JavaScript code → `webview/debug/main.js`

2. **Update `debugPanel.ts`:**
   - Move to `src/providers/debugPanelProvider.ts`
   - Update template loading logic

#### 2.3 Agent Panel Migration
1. **Extract from `templates/agentPanel.html`:**
   - HTML structure → `webview/agent/index.html`
   - CSS styles → `webview/agent/style.css`
   - JavaScript code → `webview/agent/main.js`

2. **Update `agentPanel.ts`:**
   - Move to `src/providers/agentPanelProvider.ts`
   - Update template loading logic

#### 2.4 Business Logic Separation
- Move `agentInterface.ts` to `src/interfaces/agentInterface.ts`
- Update import paths throughout the codebase

### Phase 3: Cleanup and Optimization
**Estimated Time: 2-3 hours**

#### 3.1 Remove Legacy Files
- Delete `src/templates/` directory
- Clean up old template references
- Update build configuration if needed

#### 3.2 Shared Resources Optimization
- Consolidate common CSS variables
- Create reusable component library
- Optimize bundle sizes

## Detailed Migration Steps

### Step 1: Create Migration Script
```typescript
// scripts/migrate-templates.ts
import * as fs from 'fs';
import * as path from 'path';

interface ExtractedTemplate {
    html: string;
    css: string;
    js: string;
}

function extractTemplate(htmlContent: string): ExtractedTemplate {
    // Extract CSS between <style> tags
    const cssMatch = htmlContent.match(/<style[^>]*>([\s\S]*?)<\/style>/gi);
    const css = cssMatch ? cssMatch.map(match => 
        match.replace(/<\/?style[^>]*>/gi, '')
    ).join('\n') : '';

    // Extract JS between <script> tags
    const jsMatch = htmlContent.match(/<script[^>]*>([\s\S]*?)<\/script>/gi);
    const js = jsMatch ? jsMatch.map(match => 
        match.replace(/<\/?script[^>]*>/gi, '')
    ).join('\n') : '';

    // Clean HTML (remove style and script tags)
    const html = htmlContent
        .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
        .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
        .trim();

    return { html, css, js };
}
```

### Step 2: Update Provider Base Class
```typescript
// src/providers/BaseWebviewProvider.ts
export abstract class BaseWebviewProvider {
    protected getWebviewContent(
        webview: vscode.Webview,
        htmlFile: string,
        cssFile?: string,
        jsFile?: string
    ): string {
        const htmlPath = path.join(this.context.extensionPath, 'src', 'webview', htmlFile);
        let html = fs.readFileSync(htmlPath, 'utf8');

        if (cssFile) {
            const cssUri = webview.asWebviewUri(
                vscode.Uri.joinPath(this.context.extensionUri, 'src', 'webview', cssFile)
            );
            html = html.replace('{{CSS_URI}}', cssUri.toString());
        }

        if (jsFile) {
            const jsUri = webview.asWebviewUri(
                vscode.Uri.joinPath(this.context.extensionUri, 'src', 'webview', jsFile)
            );
            html = html.replace('{{JS_URI}}', jsUri.toString());
        }

        return html;
    }
}
```

### Step 3: Template Structure
```html
<!-- webview/chat/index.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="{{CSS_URI}}">
    <title>Wu Wei Chat</title>
</head>
<body>
    <!-- HTML content here -->
    <script src="{{JS_URI}}"></script>
</body>
</html>
```

## Risk Mitigation

### Backward Compatibility
1. **Gradual Migration**: Keep old templates until new structure is tested
2. **Feature Flags**: Allow switching between old/new implementations
3. **Fallback System**: Automatic fallback to embedded templates if file loading fails

### Testing Strategy
1. **Unit Tests**: Test each provider's HTML generation
2. **Integration Tests**: Test full webview functionality
3. **User Testing**: Verify no visual or functional regressions

### Rollback Plan
1. Keep original files in `templates-backup/` during migration
2. Maintain git branches for each migration phase
3. Document all changes for easy reversal

## Benefits After Migration

### Developer Experience
- Better IDE support with proper syntax highlighting
- Easier debugging and development
- Clear separation of concerns

### Maintainability
- Modular code structure
- Reusable components
- Easier to add new features

### Performance
- Better caching of static resources
- Potential for bundling and minification
- Reduced memory usage

### Scalability
- Easy to add new webview components
- Shared styling system
- Consistent user experience

## Timeline Summary
- **Phase 1**: 2-3 hours (Infrastructure)
- **Phase 2**: 4-6 hours (Existing migration)
- **Phase 3**: 2-3 hours (Cleanup)

**Total Estimated Time: 8-12 hours**

## Success Criteria
- [ ] All existing functionality works without regression
- [ ] Code is more maintainable and follows best practices
- [ ] Performance is maintained or improved
- [ ] Development experience is significantly improved
