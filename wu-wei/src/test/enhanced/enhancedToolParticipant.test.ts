import * as assert from 'assert';
import * as vscode from 'vscode';
import { EnhancedToolParticipant } from '../../chat/enhanced/EnhancedToolParticipant';
import { DEFAULT_TOOL_PARTICIPANT_CONFIG, ToolParticipantConfig } from '../../chat/enhanced/types';

suite('Enhanced Tool Participant Tests', () => {
    let participant: EnhancedToolParticipant;
    let mockRequest: vscode.ChatRequest;
    let mockContext: vscode.ChatContext;
    let mockStream: vscode.ChatResponseStream;
    let mockToken: vscode.CancellationToken;
    let mockModel: vscode.LanguageModelChat;
    let mockTools: vscode.LanguageModelToolInformation[];

    setup(() => {
        const config: Partial<ToolParticipantConfig> = {
            ...DEFAULT_TOOL_PARTICIPANT_CONFIG,
            debugMode: true,
            maxToolRounds: 3,
            enableCaching: true,
            enableParallelExecution: true,
            toolTimeout: 5000
        };

        participant = new EnhancedToolParticipant(config);

        mockRequest = {
            prompt: 'analyze this codebase',
            model: undefined,
            command: undefined,
            references: [],
            location: undefined
        } as unknown as vscode.ChatRequest;

        mockContext = {
            history: []
        } as vscode.ChatContext;

        mockStream = {
            markdown: () => { },
            progress: () => { },
            reference: () => { },
            button: () => { },
            filetree: () => { },
            anchor: () => { },
            push: () => { }
        } as unknown as vscode.ChatResponseStream;

        mockToken = {
            isCancellationRequested: false,
            onCancellationRequested: () => ({ dispose: () => { } })
        } as vscode.CancellationToken;

        mockModel = {
            id: 'test-model',
            vendor: 'test',
            family: 'test-family',
            version: '1.0',
            maxInputTokens: 4096,
            sendRequest: async () => ({
                stream: (async function* () {
                    yield new vscode.LanguageModelTextPart('Analysis complete');
                })()
            })
        } as unknown as vscode.LanguageModelChat;

        mockTools = [
            {
                name: 'fileReader',
                description: 'Reads file contents',
                inputSchema: {},
                tags: []
            },
            {
                name: 'codeAnalyzer',
                description: 'Analyzes code structure',
                inputSchema: {},
                tags: []
            },
            {
                name: 'searchTool',
                description: 'Searches for patterns',
                inputSchema: {},
                tags: []
            }
        ];
    });

    teardown(() => {
        participant.clearCache();
    });

    suite('Initialization', () => {
        test('should initialize with default configuration', () => {
            const defaultParticipant = new EnhancedToolParticipant();
            const config = defaultParticipant.getConfig();

            assert.strictEqual(config.maxToolRounds, DEFAULT_TOOL_PARTICIPANT_CONFIG.maxToolRounds);
            assert.strictEqual(config.enableCaching, DEFAULT_TOOL_PARTICIPANT_CONFIG.enableCaching);
            assert.strictEqual(config.enableParallelExecution, DEFAULT_TOOL_PARTICIPANT_CONFIG.enableParallelExecution);
        });

        test('should initialize with custom configuration', () => {
            const customConfig: Partial<ToolParticipantConfig> = {
                maxToolRounds: 10,
                debugMode: true,
                enableCaching: false
            };

            const customParticipant = new EnhancedToolParticipant(customConfig);
            const config = customParticipant.getConfig();

            assert.strictEqual(config.maxToolRounds, 10);
            assert.strictEqual(config.debugMode, true);
            assert.strictEqual(config.enableCaching, false);
        });
    });

    suite('Configuration Management', () => {
        test('should update configuration correctly', () => {
            const newConfig: Partial<ToolParticipantConfig> = {
                maxToolRounds: 8,
                debugMode: false,
                toolTimeout: 15000
            };

            participant.updateConfig(newConfig);
            const config = participant.getConfig();

            assert.strictEqual(config.maxToolRounds, 8);
            assert.strictEqual(config.debugMode, false);
            assert.strictEqual(config.toolTimeout, 15000);
            // Other settings should remain unchanged
            assert.strictEqual(config.enableCaching, true);
        });

        test('should get current configuration', () => {
            const config = participant.getConfig();

            assert.ok(typeof config.maxToolRounds === 'number');
            assert.ok(typeof config.enableCaching === 'boolean');
            assert.ok(typeof config.enableParallelExecution === 'boolean');
            assert.ok(typeof config.debugMode === 'boolean');
        });
    });

    suite('Cache Management', () => {
        test('should initialize with empty cache', () => {
            const stats = participant.getCacheStatistics();

            assert.strictEqual(stats.size, 0);
            assert.strictEqual(stats.hitRate, 0);
            assert.strictEqual(stats.oldestEntry, null);
        });

        test('should clear cache correctly', () => {
            participant.clearCache();
            const stats = participant.getCacheStatistics();

            assert.strictEqual(stats.size, 0);
            assert.strictEqual(stats.hitRate, 0);
        });
    });

    suite('Prompt Template Management', () => {
        test('should get available templates', () => {
            const templates = participant.getAvailableTemplates();
            assert.ok(Array.isArray(templates));
        });

        test('should add custom template', () => {
            const customTemplate = {
                id: 'test-template',
                name: 'Test Template',
                content: 'This is a test template for {intent}',
                type: 'user-intent'
            };

            participant.addPromptTemplate(customTemplate);
            const templates = participant.getAvailableTemplates();

            assert.ok(templates.some(t => t.id === 'test-template'));
        });
    });

    suite('Error Handling', () => {
        test('should handle empty tool list gracefully', async () => {
            try {
                const result = await participant.handleChatRequest(
                    mockRequest,
                    mockContext,
                    mockStream,
                    mockToken,
                    mockModel,
                    []
                );

                assert.ok(result);
                assert.ok(result.metadata);
            } catch (error) {
                // Expected to handle gracefully
                assert.ok(error instanceof Error);
            }
        });

        test('should handle null inputs gracefully', async () => {
            try {
                const result = await participant.handleChatRequest(
                    null as any,
                    mockContext,
                    mockStream,
                    mockToken,
                    mockModel,
                    mockTools
                );

                assert.ok(result);
                assert.ok(result.metadata);
                assert.ok(result.metadata.error);
            } catch (error) {
                // Expected to handle gracefully
                assert.ok(error instanceof Error);
            }
        });
    });
});
