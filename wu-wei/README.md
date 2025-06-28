# Wu Wei - Effortless Work Automation

*无为而治* - "Govern by doing nothing that goes against nature"

## Philosophy

Wu Wei (無為) represents the Taoist concept of "effortless action" - achieving maximum results with minimal effort by working in harmony with natural flow rather than against it. This VS Code extension embodies this philosophy by providing seamless work automation that feels natural and unobtrusive.

## Vision

Transform your daily work through automation that:
- **Flows naturally** with your existing workflow
- **Reduces friction** in repetitive tasks
- **Enhances productivity** without complexity
- **Adapts effortlessly** to your work patterns

## Features

### Current
- Basic extension foundation with Wu Wei principles
- **Wu Wei Chat Interface**: Natural conversation flow for automation guidance
- **VS Code Chat Participant**: Use `@wu-wei` in VS Code chat for effortless assistance
- **Prompt TSX Support**: Advanced prompt composition using Microsoft's @vscode/prompt-tsx package
- Configuration system for automation preferences
- Extensible architecture for future automation modules

### Prompt TSX Integration

Wu Wei now supports sophisticated prompt composition using Microsoft's `@vscode/prompt-tsx` package:

- **Intelligent Prioritization**: Components have priority levels for context window management
- **Flexible Text Handling**: Dynamic content adaptation to available token budget
- **Type-Safe Components**: Full TypeScript support for prompt elements
- **Async Preparation**: Support for asynchronous data gathering before prompt rendering

For detailed information, see [Prompt TSX Setup Documentation](./docs/prompt-tsx-setup.md).

### Planned Automation Areas
- **File & Document Operations**: Batch processing, organization, templates
- **Communication**: Email templates, meeting notes, status reports
- **Development Workflow**: Code patterns, project setup, deployment
- **Data Processing**: Format conversion, report generation
- **Personal Productivity**: Task management, time tracking, workflow optimization

## Installation

1. Clone or download this extension
2. Open in VS Code
3. Press `F5` to run in development mode
4. Test the commands:
   - `Ctrl+Shift+P` → "Wu Wei: Hello World"
   - `Ctrl+Shift+P` → "Wu Wei: Open Chat" (Start natural conversation)
   - Open VS Code Chat (Ctrl+Shift+I or View → Chat) and type `@wu-wei hello` for effortless assistance

## Using Wu Wei Chat Participant

The Wu Wei chat participant embodies the philosophy of effortless action. Simply:

1. Open VS Code Chat panel (`Ctrl+Shift+I` or `View → Chat`)
2. Type `@wu-wei` followed by your question or request
3. Experience thoughtful, gentle guidance that flows naturally

**Example interactions:**
- `@wu-wei Tell me about Wu Wei philosophy`
- `@wu-wei Help me with my current workspace`
- `@wu-wei Show me the way of effortless coding`
- `@wu-wei How can I work more harmoniously?`

The assistant provides wise, concise responses that flow naturally without forcing solutions.

## Development

### Prerequisites
- Node.js 16+
- VS Code 1.74+

### Setup
```bash
cd wu-wei
npm install
npm run compile
```

### Development Workflow
```bash
npm run watch    # Auto-compile on changes
# Press F5 in VS Code to launch extension host
```

### Building the Extension

The extension uses esbuild for bundling to optimize performance and reduce file count:

```bash
# Development build with source maps
npm run esbuild

# Watch mode for development
npm run esbuild-watch

# Production build (minified)
npm run package
```

### Bundling

The extension is bundled using esbuild to significantly reduce the number of files and improve performance:
- **Before bundling**: 360 files (275 JavaScript files)
- **After bundling**: Single `extension.js` file (~250KB)

External dependencies like `chokidar` are excluded from bundling to avoid issues with native binaries.

### Packaging

```bash
# Create VSIX package
vsce package
```

The GitHub workflow automatically builds and packages the extension using the bundled approach for optimal performance.

## Configuration

Access settings via `Ctrl+,` → Search "Wu Wei"

- `wu-wei.enableAutomation`: Enable/disable automation features

## Philosophy in Practice

This extension follows Wu Wei principles:

1. **Minimal Intervention**: Automation works behind the scenes
2. **Natural Flow**: Features integrate seamlessly with existing workflows
3. **Adaptive Intelligence**: The system learns and adapts to your patterns
4. **Effortless Scaling**: Simple actions produce disproportionate results

## Contributing

Contributions should align with Wu Wei philosophy:
- Solve real problems with minimal complexity
- Enhance natural workflow rather than disrupting it
- Focus on user experience and effortless interaction
- Build sustainable, maintainable solutions

## License

MIT License - Use freely, improve naturally

---

*"The sage does not attempt anything very big, and thus achieves greatness."* - Tao Te Ching
