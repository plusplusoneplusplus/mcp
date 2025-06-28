# Webview Resource Management System

## Overview

The Wu Wei extension uses a robust, named resource mapping system for managing CSS and JavaScript resources in webviews. This system prevents common errors and makes resource management more maintainable.

## Key Benefits

1. **Type Safety**: TypeScript interfaces ensure correct configuration
2. **Self-Documenting**: Resource mappings are explicit and clear
3. **Error Prevention**: No more hardcoded indices or mismatched placeholders
4. **Maintainable**: Easy to add, remove, or modify resources
5. **Debugging**: Clear logging and error messages

## Architecture

### WebviewResourceConfig Interface

```typescript
interface WebviewResourceConfig {
    htmlFile: string;
    cssResources?: Record<string, string>;
    jsResources?: Record<string, string>;
}
```

### Resource Mapping

Resources are mapped using placeholder names that correspond to placeholders in HTML files:

```typescript
const config: WebviewResourceConfig = {
    htmlFile: 'agent/index.html',
    cssResources: {
        'BASE_CSS_URI': 'shared/base.css',           // {{BASE_CSS_URI}}
        'COMPONENTS_CSS_URI': 'shared/components.css', // {{COMPONENTS_CSS_URI}}
        'AGENT_CSS_URI': 'agent/style.css'          // {{AGENT_CSS_URI}}
    },
    jsResources: {
        'UTILS_JS_URI': 'shared/utils.js',          // {{UTILS_JS_URI}}
        'AGENT_JS_URI': 'agent/main.js'             // {{AGENT_JS_URI}}
    }
};
```

## HTML Placeholder Format

HTML files should use double-brace placeholders:

```html
<!-- CSS Resources -->
<link rel="stylesheet" href="{{BASE_CSS_URI}}">
<link rel="stylesheet" href="{{COMPONENTS_CSS_URI}}">
<link rel="stylesheet" href="{{AGENT_CSS_URI}}">

<!-- JavaScript Resources -->
<script src="{{UTILS_JS_URI}}"></script>
<script src="{{AGENT_JS_URI}}"></script>
```

## Standard Placeholder Names

### CSS Placeholders
- `BASE_CSS_URI` - Base/global styles
- `COMPONENTS_CSS_URI` - Shared component styles
- `PROMPT_STORE_CSS_URI` - Prompt store specific styles
- `AGENT_CSS_URI` - Agent panel specific styles
- `DEBUG_CSS_URI` - Debug panel specific styles
- `CHAT_CSS_URI` - Chat panel specific styles

### JavaScript Placeholders
- `UTILS_JS_URI` - Shared utility functions
- `PROMPT_STORE_JS_URI` - Prompt store functionality
- `AGENT_JS_URI` - Agent panel functionality
- `DEBUG_JS_URI` - Debug panel functionality
- `CHAT_JS_URI` - Chat panel functionality

## Implementation Examples

### Basic Implementation

```typescript
export class MyWebviewProvider extends BaseWebviewProvider {
    resolveWebviewView(webviewView: vscode.WebviewView): void {
        this._view = webviewView;
        
        const config: WebviewResourceConfig = {
            htmlFile: 'my-panel/index.html',
            cssResources: {
                'BASE_CSS_URI': 'shared/base.css',
                'MY_PANEL_CSS_URI': 'my-panel/style.css'
            },
            jsResources: {
                'UTILS_JS_URI': 'shared/utils.js',
                'MY_PANEL_JS_URI': 'my-panel/main.js'
            }
        };
        
        webviewView.webview.html = this.getWebviewContent(webviewView.webview, config);
    }
}
```

### Using Helper Methods

```typescript
export class AgentPanelProvider extends BaseWebviewProvider {
    private getAgentPanelConfig(): WebviewResourceConfig {
        return {
            htmlFile: 'agent/index.html',
            cssResources: {
                'BASE_CSS_URI': 'shared/base.css',
                'COMPONENTS_CSS_URI': 'shared/components.css',
                'AGENT_CSS_URI': 'agent/style.css'
            },
            jsResources: {
                'UTILS_JS_URI': 'shared/utils.js',
                'AGENT_JS_URI': 'agent/main.js'
            }
        };
    }
    
    resolveWebviewView(webviewView: vscode.WebviewView): void {
        this._view = webviewView;
        webviewView.webview.html = this.getWebviewContent(webviewView.webview, this.getAgentPanelConfig());
    }
    
    public refresh(): void {
        if (this._view) {
            this._view.webview.html = this.getWebviewContent(this._view.webview, this.getAgentPanelConfig());
        }
    }
}
```

## Error Handling

The system includes robust error handling:

1. **Missing Resources**: Empty or missing resource paths are handled gracefully
2. **Unreplaced Placeholders**: Automatically removed from final HTML
3. **File Not Found**: Falls back to error HTML with helpful messages
4. **Logging**: Comprehensive debug logging for troubleshooting

## Migration from Legacy System

The legacy array-based system is still supported but deprecated:

```typescript
// OLD (Deprecated)
this.getWebviewContent(webview, 'agent/index.html', 
    ['shared/base.css', 'shared/components.css', 'agent/style.css'],
    ['shared/utils.js', 'agent/main.js']
);

// NEW (Recommended)
this.getWebviewContent(webview, {
    htmlFile: 'agent/index.html',
    cssResources: {
        'BASE_CSS_URI': 'shared/base.css',
        'COMPONENTS_CSS_URI': 'shared/components.css',
        'AGENT_CSS_URI': 'agent/style.css'
    },
    jsResources: {
        'UTILS_JS_URI': 'shared/utils.js',
        'AGENT_JS_URI': 'agent/main.js'
    }
});
```

## Best Practices

1. **Use Helper Methods**: Create configuration helper methods to avoid duplication
2. **Consistent Naming**: Follow the standard placeholder naming conventions
3. **Type Safety**: Always use the `WebviewResourceConfig` interface
4. **Resource Organization**: Group related resources logically
5. **Documentation**: Document custom placeholder names in your webview provider

## Debugging

### Enable Debug Logging

The system logs resource replacement operations. Enable debug logging to troubleshoot:

```typescript
// In your provider constructor
logger.setLevel('debug');
```

### Common Issues

1. **Placeholder Mismatch**: Ensure HTML placeholders match configuration keys exactly
2. **Case Sensitivity**: Placeholder names are case-sensitive
3. **Missing Files**: Check that resource files exist in the `out/webview` directory
4. **Build Process**: Ensure webview files are copied to the output directory

### Debugging Output

The system provides helpful debug output:

```
Replacing CSS placeholder {{BASE_CSS_URI}} with vscode-webview://...
Replacing JS placeholder {{UTILS_JS_URI}} with vscode-webview://...
Found unreplaced placeholders in HTML: ['{{UNKNOWN_PLACEHOLDER}}']
```

## File Structure

```
src/webview/
├── shared/
│   ├── base.css
│   ├── components.css
│   └── utils.js
├── agent/
│   ├── index.html
│   ├── style.css
│   └── main.js
├── prompt-store/
│   ├── index.html
│   ├── style.css
│   └── main.js
└── debug/
    ├── index.html
    ├── style.css
    └── main.js
```

## Future Enhancements

Potential improvements to consider:

1. **Resource Bundling**: Automatic bundling of CSS/JS resources
2. **Hot Reload**: Development-time hot reloading of webview resources
3. **Resource Validation**: Compile-time validation of resource existence
4. **Template Inheritance**: Support for HTML template inheritance
5. **Resource Optimization**: Automatic minification and optimization

## Conclusion

This resource management system provides a robust, maintainable foundation for webview development in the Wu Wei extension. By following these guidelines and best practices, developers can avoid common pitfalls and create reliable, well-structured webview experiences. 