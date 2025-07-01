import * as assert from 'assert';
import * as vscode from 'vscode';
import { EnhancedToolParticipant } from '../../chat/enhanced/EnhancedToolParticipant';
import { ToolResultManager } from '../../chat/enhanced/ToolResultManager';
import { PromptTemplateEngine } from '../../chat/enhanced/PromptTemplateEngine';
import { DEFAULT_TOOL_PARTICIPANT_CONFIG } from '../../chat/enhanced/types';

suite('Enhanced Tool Calling Performance Tests', () => {
    let participant: EnhancedToolParticipant;
    let resultManager: ToolResultManager;
    let templateEngine: PromptTemplateEngine;

    setup(() => {
        participant = new EnhancedToolParticipant({
            ...DEFAULT_TOOL_PARTICIPANT_CONFIG,
            enableCaching: true,
            enableParallelExecution: true,
            debugMode: false // Disable debug mode for performance tests
        });

        resultManager = new ToolResultManager(true);
        templateEngine = new PromptTemplateEngine();
    });

    teardown(() => {
        participant.clearCache();
        resultManager.clearCache();
    });

    suite('Initialization Performance', () => {
        test('should initialize quickly', () => {
            const startTime = Date.now();

            const newParticipant = new EnhancedToolParticipant(DEFAULT_TOOL_PARTICIPANT_CONFIG);

            const initTime = Date.now() - startTime;

            // Should initialize in under 100ms
            assert.ok(initTime < 100, `Initialization took ${initTime}ms, expected < 100ms`);

            newParticipant.clearCache();
        });

        test('should initialize components efficiently', () => {
            const startTime = Date.now();

            const manager = new ToolResultManager(true);
            const engine = new PromptTemplateEngine();

            const initTime = Date.now() - startTime;

            // Component initialization should be fast
            assert.ok(initTime < 50, `Component initialization took ${initTime}ms, expected < 50ms`);

            manager.clearCache();
        });
    });

    suite('Cache Performance', () => {
        test('should handle cache operations efficiently', () => {
            const startTime = Date.now();

            // Perform multiple cache operations
            for (let i = 0; i < 100; i++) {
                const toolName = `test-tool-${i}`;
                const input = { query: `test-input-${i}` };
                const result = { content: [`test-data-${i}`] } as unknown as vscode.LanguageModelToolResult;

                resultManager.cacheResult(toolName, input, result);
                resultManager.getCachedResult(toolName, input);
            }

            const operationTime = Date.now() - startTime;

            // 100 cache operations should complete quickly
            assert.ok(operationTime < 200, `Cache operations took ${operationTime}ms, expected < 200ms`);

            const stats = resultManager.getCacheStats();
            assert.strictEqual(stats.size, 100);
        });

        test('should provide fast cache statistics', () => {
            const startTime = Date.now();

            // Get stats multiple times
            for (let i = 0; i < 100; i++) {
                resultManager.getCacheStats();
            }

            const statsTime = Date.now() - startTime;

            // Getting stats should be very fast
            assert.ok(statsTime < 20, `Stats retrieval took ${statsTime}ms, expected < 20ms`);
        });

        test('should clear cache efficiently', () => {
            // Add some data to cache first
            for (let i = 0; i < 50; i++) {
                const toolName = `cache-test-${i}`;
                const input = { data: i };
                const result = { content: [`result-${i}`] } as unknown as vscode.LanguageModelToolResult;

                resultManager.cacheResult(toolName, input, result);
            }

            const startTime = Date.now();

            resultManager.clearCache();

            const clearTime = Date.now() - startTime;

            // Cache clear should be fast
            assert.ok(clearTime < 50, `Cache clear took ${clearTime}ms, expected < 50ms`);

            const stats = resultManager.getCacheStats();
            assert.strictEqual(stats.size, 0);
        });
    });

    suite('Prompt Template Performance', () => {
        test('should generate prompts efficiently', () => {
            const mockTools: vscode.LanguageModelToolInformation[] = [
                { name: 'tool1', description: 'Test tool 1', inputSchema: {}, tags: [] },
                { name: 'tool2', description: 'Test tool 2', inputSchema: {}, tags: [] },
                { name: 'tool3', description: 'Test tool 3', inputSchema: {}, tags: [] }
            ];

            const mockContext = {
                userIntent: 'analyze code',
                availableTools: mockTools,
                conversationHistory: [],
                previousResults: {},
                roundNumber: 1
            };

            const startTime = Date.now();

            // Generate multiple prompts
            for (let i = 0; i < 50; i++) {
                templateEngine.generateToolAwareSystemPrompt(
                    'Base system prompt',
                    mockTools,
                    { ...mockContext, userIntent: `request ${i}` }
                );
            }

            const promptTime = Date.now() - startTime;

            // Prompt generation should be fast
            assert.ok(promptTime < 200, `Prompt generation took ${promptTime}ms, expected < 200ms`);
        });

        test('should analyze user intent efficiently', () => {
            const mockTools: vscode.LanguageModelToolInformation[] = [
                { name: 'fileReader', description: 'Reads files', inputSchema: {}, tags: [] },
                { name: 'codeAnalyzer', description: 'Analyzes code', inputSchema: {}, tags: [] }
            ];

            const startTime = Date.now();

            // Analyze multiple user intents
            const testPrompts = [
                'analyze this file',
                'read the contents of config.json',
                'find bugs in the code',
                'optimize the performance',
                'refactor this class'
            ];

            for (const prompt of testPrompts) {
                templateEngine.analyzeUserIntentForTools(prompt, mockTools);
            }

            const analysisTime = Date.now() - startTime;

            // Intent analysis should be fast
            assert.ok(analysisTime < 100, `Intent analysis took ${analysisTime}ms, expected < 100ms`);
        });
    });

    suite('Configuration Performance', () => {
        test('should handle configuration updates efficiently', () => {
            const startTime = Date.now();

            // Update configuration many times
            for (let i = 0; i < 100; i++) {
                participant.updateConfig({
                    maxToolRounds: i % 10 + 1,
                    debugMode: i % 2 === 0,
                    toolTimeout: (i % 5 + 1) * 1000
                });
            }

            const updateTime = Date.now() - startTime;

            // Config updates should be fast
            assert.ok(updateTime < 100, `Config updates took ${updateTime}ms, expected < 100ms`);
        });

        test('should handle concurrent configuration updates', () => {
            const startTime = Date.now();

            // Multiple rapid config updates
            const updates = [];

            for (let i = 0; i < 20; i++) {
                updates.push(() => {
                    participant.updateConfig({
                        maxToolRounds: i % 5 + 1,
                        debugMode: i % 3 === 0
                    });
                });
            }

            // Execute all updates
            updates.forEach(update => update());

            const updateTime = Date.now() - startTime;

            // Should handle rapid updates efficiently
            assert.ok(updateTime < 50, `Config updates took ${updateTime}ms, expected < 50ms`);

            // Final config should be valid
            const finalConfig = participant.getConfig();
            assert.ok(typeof finalConfig.maxToolRounds === 'number');
            assert.ok(typeof finalConfig.debugMode === 'boolean');
        });
    });

    suite('Scalability', () => {
        test('should scale with large tool sets', () => {
            // Create a large number of mock tools
            const largeToolSet: vscode.LanguageModelToolInformation[] = [];

            for (let i = 0; i < 100; i++) {
                largeToolSet.push({
                    name: `tool-${i}`,
                    description: `Tool number ${i} for testing scalability`,
                    inputSchema: { type: 'object', properties: { param: { type: 'string' } } },
                    tags: [`category-${i % 10}`, `type-${i % 5}`]
                });
            }

            const startTime = Date.now();

            // Analyze intent with large tool set
            const analysis = templateEngine.analyzeUserIntentForTools(
                'analyze the codebase and find issues',
                largeToolSet
            );

            const analysisTime = Date.now() - startTime;

            // Should handle large tool sets efficiently
            assert.ok(analysisTime < 300, `Large tool set analysis took ${analysisTime}ms, expected < 300ms`);
            assert.ok(analysis.selectedTools.length > 0);
            assert.ok(analysis.confidence > 0);
        });

        test('should maintain performance with large conversation history', () => {
            // Create a large conversation history
            const largeHistory: vscode.LanguageModelChatMessage[] = [];

            for (let i = 0; i < 50; i++) {
                largeHistory.push(vscode.LanguageModelChatMessage.User(`User message ${i}`));
                largeHistory.push(vscode.LanguageModelChatMessage.Assistant(`Assistant response ${i}`));
            }

            const mockContext = {
                userIntent: 'complex analysis task',
                availableTools: [
                    { name: 'analyzer', description: 'Analyzes code', inputSchema: {}, tags: [] }
                ],
                conversationHistory: largeHistory,
                previousResults: {},
                roundNumber: 10
            };

            const startTime = Date.now();

            // Generate prompt with large history
            const prompt = templateEngine.generateToolAwareSystemPrompt(
                'Base system prompt',
                mockContext.availableTools,
                mockContext
            );

            const promptTime = Date.now() - startTime;

            // Should handle large history efficiently
            assert.ok(promptTime < 200, `Large history prompt generation took ${promptTime}ms, expected < 200ms`);
            assert.ok(prompt.length > 0);
        });
    });

    suite('Resource Cleanup', () => {
        test('should cleanup resources efficiently', () => {
            const startTime = Date.now();

            // Cleanup
            participant.clearCache();
            resultManager.clearCache();

            const cleanupTime = Date.now() - startTime;

            // Cleanup should be fast
            assert.ok(cleanupTime < 50, `Resource cleanup took ${cleanupTime}ms, expected < 50ms`);

            // Resources should be cleared
            const stats = participant.getCacheStatistics();
            assert.strictEqual(stats.size, 0);
        });

        test('should handle repeated cleanup operations', () => {
            const startTime = Date.now();

            // Multiple cleanup operations
            for (let i = 0; i < 10; i++) {
                participant.clearCache();
                resultManager.clearCache();
            }

            const cleanupTime = Date.now() - startTime;

            // Multiple cleanups should not cause performance issues
            assert.ok(cleanupTime < 100, `Multiple cleanups took ${cleanupTime}ms, expected < 100ms`);
        });
    });

    suite('Memory Management', () => {
        test('should handle large template sets efficiently', () => {
            const startTime = Date.now();

            // Add many custom templates
            for (let i = 0; i < 50; i++) {
                templateEngine.addTemplate({
                    id: `perf-template-${i}`,
                    name: `Performance Template ${i}`,
                    template: `Template content for testing ${i}`,
                    variables: ['intent', 'tools'],
                    toolSpecific: false
                });
            }

            const templateTime = Date.now() - startTime;

            // Adding templates should be efficient
            assert.ok(templateTime < 100, `Template addition took ${templateTime}ms, expected < 100ms`);

            const templates = templateEngine.getAvailableTemplates();
            assert.ok(templates.length >= 50);
        });

        test('should maintain performance across operations', () => {
            const startTime = Date.now();

            // Perform various operations
            for (let i = 0; i < 20; i++) {
                participant.updateConfig({ maxToolRounds: i % 5 + 1 });
                participant.getCacheStatistics();
                templateEngine.analyzeUserIntentForTools(`test query ${i}`, [
                    { name: 'test-tool', description: 'Test', inputSchema: {}, tags: [] }
                ]);
            }

            const operationTime = Date.now() - startTime;

            // Mixed operations should be efficient
            assert.ok(operationTime < 200, `Mixed operations took ${operationTime}ms, expected < 200ms`);
        });
    });
});
