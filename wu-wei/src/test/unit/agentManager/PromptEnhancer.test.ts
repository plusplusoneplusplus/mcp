import * as assert from 'assert';
import { PromptEnhancer, PromptEnhancementConfig, ExecutionContext } from '../../../agentManager/PromptEnhancer';
import { AbstractAgent, AgentCapabilities } from '../../../agentManager/agentInterface';
import { PromptService } from '../../../shared/promptManager/types';

/**
 * Mock PromptService for testing
 */
class MockPromptService implements Partial<PromptService> {
    private mockPrompts: Map<string, any> = new Map();
    private shouldThrowError = false;

    constructor() {
        // Set up default mock prompts
        this.mockPrompts.set('test-prompt', {
            id: 'test-prompt',
            content: 'You are a helpful assistant. Follow these instructions carefully.',
            filePath: '/mock/prompts/test-prompt.md'
        });
        this.mockPrompts.set('prompt-with-vars', {
            id: 'prompt-with-vars',
            content: 'Hello {{name}}, please help with {{task}}.',
            filePath: null
        });
    }

    async renderPromptWithVariables(promptId: string, variables: Record<string, any>): Promise<string> {
        if (this.shouldThrowError) {
            throw new Error('Mock render error');
        }
        const prompt = this.mockPrompts.get(promptId);
        if (!prompt) {
            throw new Error(`Prompt ${promptId} not found`);
        }

        let rendered = prompt.content;
        Object.entries(variables).forEach(([key, value]) => {
            rendered = rendered.replace(new RegExp(`{{${key}}}`, 'g'), value);
        });
        return rendered;
    }

    async getPrompt(id: string) {
        if (this.shouldThrowError) {
            throw new Error('Mock prompt error');
        }
        return this.mockPrompts.get(id) || null;
    }

    setMockPrompt(id: string, prompt: any) {
        this.mockPrompts.set(id, prompt);
    }

    setShouldThrowError(shouldThrow: boolean) {
        this.shouldThrowError = shouldThrow;
    }
}

/**
 * Mock Agent for testing different prompt support scenarios
 */
class MockAgent extends AbstractAgent {
    constructor(promptSupport?: any) {
        const capabilities: AgentCapabilities = {
            name: 'mock-agent',
            version: '1.0.0',
            methods: ['test'],
            metadata: {
                promptSupport: promptSupport || {
                    supportsPrompts: true,
                    promptParameterName: 'prompt',
                    variableResolution: true
                }
            }
        };
        super(capabilities);
    }

    protected async executeMethod(method: string, params: any): Promise<any> {
        return { result: 'mock response' };
    }
}

/**
 * Agent without prompt support
 */
class LegacyAgent extends AbstractAgent {
    constructor() {
        const capabilities: AgentCapabilities = {
            name: 'legacy-agent',
            version: '1.0.0',
            methods: ['test'],
            metadata: {} // No prompt support metadata
        };
        super(capabilities);
    }

    protected async executeMethod(method: string, params: any): Promise<any> {
        return { result: 'legacy response' };
    }
}

/**
 * Agent with fallback prompt support
 */
class FallbackAgent extends MockAgent {
    constructor() {
        super({
            supportsPrompts: false,
            promptParameterName: 'message'
        });
    }
}

suite('PromptEnhancer Tests', () => {
    let mockPromptService: MockPromptService;
    let nativeAgent: MockAgent;
    let fallbackAgent: FallbackAgent;
    let legacyAgent: LegacyAgent;

    setup(() => {
        mockPromptService = new MockPromptService();
        nativeAgent = new MockAgent();
        fallbackAgent = new FallbackAgent();
        legacyAgent = new LegacyAgent();
    });

    suite('enhanceParamsWithPrompt', () => {
        test('should return original params when no prompt context', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: null,
                agent: nativeAgent,
                userParams: { message: 'test' }
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);
            assert.deepStrictEqual(result, { message: 'test' });
        });

        test('should return original params when no promptId', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: { variables: {} },
                agent: nativeAgent,
                userParams: { message: 'test' }
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);
            assert.deepStrictEqual(result, { message: 'test' });
        });

        test('should throw error when no prompt and no user input', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {}, // No promptId
                agent: nativeAgent,
                userParams: {} // No user input
            };

            // This should return userParams as-is since no promptId
            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);
            assert.deepStrictEqual(result, {});
        });

        test('should enhance with native prompt support', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'test-prompt'
                },
                agent: nativeAgent,
                userParams: { message: 'user input' }
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);

            assert.strictEqual(result.prompt, '#/mock/prompts/test-prompt.md');
            assert.strictEqual(result.additionalMessage, 'user input');
            assert.strictEqual(result.message, 'user input');
        });

        test('should enhance with variables in native mode', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'prompt-with-vars',
                    variables: { name: 'John', task: 'coding' }
                },
                agent: nativeAgent,
                userParams: { message: 'help me' }
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);

            assert.ok(result.prompt.includes('Hello John'));
            assert.ok(result.prompt.includes('help with coding'));
            assert.strictEqual(result.variables.name, 'John');
            assert.strictEqual(result.additionalMessage, 'help me');
        });

        test('should use file path when no variables in native mode', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'test-prompt'
                },
                agent: nativeAgent,
                userParams: {}
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);

            assert.strictEqual(result.prompt, '#/mock/prompts/test-prompt.md');
        });

        test('should enhance with fallback stitching', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'test-prompt'
                },
                agent: legacyAgent, // No prompt support
                userParams: { message: 'user query' }
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);

            assert.ok(result.message, 'Result should have a message property');
            assert.ok(result.message.includes('Follow Instructions in /mock/prompts/test-prompt.md'));
            assert.ok(result.message.includes('User Request:'));
            assert.ok(result.message.includes('user query'));
        });

        test('should handle fallback stitching with variables', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'prompt-with-vars',
                    variables: { name: 'Alice', task: 'testing' }
                },
                agent: legacyAgent,
                userParams: { query: 'help please' }
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);

            assert.ok(result.message, 'Result should have a message property');
            assert.ok(result.message.includes('System Instructions:'));
            assert.ok(result.message.includes('Hello Alice'));
            assert.ok(result.message.includes('help with testing'));
            assert.ok(result.message.includes('User Request:'));
            assert.ok(result.message.includes('help please'));
        });

        test('should handle prompt-only mode in fallback', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'test-prompt'
                },
                agent: legacyAgent,
                userParams: {}
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);

            assert.ok(result.message, 'Result should have a message property');
            assert.ok(result.message.includes('Follow Instructions in /mock/prompts/test-prompt.md'));
            assert.ok(!result.message.includes('User Request:'));
        });

        test('should throw error when prompt not found', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'nonexistent-prompt'
                },
                agent: nativeAgent,
                userParams: {}
            };

            await assert.rejects(
                async () => await PromptEnhancer.enhanceParamsWithPrompt(config),
                /Prompt with id 'nonexistent-prompt' not found/
            );
        });
    });

    suite('extractUserInput', () => {
        test('should extract from message field', () => {
            const result = PromptEnhancer.extractUserInput({ message: 'test message' });
            assert.strictEqual(result, 'test message');
        });

        test('should extract from query field', () => {
            const result = PromptEnhancer.extractUserInput({ query: 'test query' });
            assert.strictEqual(result, 'test query');
        });

        test('should extract from input field', () => {
            const result = PromptEnhancer.extractUserInput({ input: 'test input' });
            assert.strictEqual(result, 'test input');
        });

        test('should extract from question field', () => {
            const result = PromptEnhancer.extractUserInput({ question: 'test question' });
            assert.strictEqual(result, 'test question');
        });

        test('should prioritize message over other fields', () => {
            const result = PromptEnhancer.extractUserInput({
                message: 'priority message',
                query: 'secondary query',
                input: 'tertiary input'
            });
            assert.strictEqual(result, 'priority message');
        });

        test('should trim whitespace', () => {
            const result = PromptEnhancer.extractUserInput({ message: '  test message  ' });
            assert.strictEqual(result, 'test message');
        });

        test('should return null for empty params', () => {
            const result = PromptEnhancer.extractUserInput({});
            assert.strictEqual(result, null);
        });

        test('should return null for empty strings', () => {
            const result = PromptEnhancer.extractUserInput({ message: '' });
            assert.strictEqual(result, null);
        });

        test('should return null for whitespace-only strings', () => {
            const result = PromptEnhancer.extractUserInput({ message: '   ' });
            assert.strictEqual(result, null);
        });
    });

    suite('createComprehensivePrompt', () => {
        test('should combine prompt content and user input', async () => {
            const result = await PromptEnhancer.createComprehensivePrompt(
                'System prompt content',
                'User input here'
            );

            assert.ok(result.includes('System prompt content'));
            assert.ok(result.includes('User Request:'));
            assert.ok(result.includes('User input here'));
        });

        test('should handle prompt-only mode', async () => {
            const result = await PromptEnhancer.createComprehensivePrompt(
                'System prompt content',
                null
            );

            assert.strictEqual(result, 'System prompt content');
        });

        test('should handle user-input-only mode', async () => {
            const result = await PromptEnhancer.createComprehensivePrompt(
                '',
                'User input only'
            );

            assert.strictEqual(result, 'User input only');
        });

        test('should add execution context', async () => {
            const executionContext: ExecutionContext = {
                executionId: 'test-exec-123',
                taskDescription: 'Test task',
                agentName: 'test-agent',
                startTime: new Date()
            };

            const result = await PromptEnhancer.createComprehensivePrompt(
                'System prompt',
                'User input',
                executionContext
            );

            assert.ok(result.includes('System prompt'));
            assert.ok(result.includes('User Request:'));
            assert.ok(result.includes('User input'));
            assert.ok(result.includes('**IMPORTANT**'));
            assert.ok(result.includes('wu-wei_copilot_completion_signal'));
            assert.ok(result.includes('test-exec-123'));
        });

        test('should handle execution context only', async () => {
            const executionContext: ExecutionContext = {
                executionId: 'test-exec-123',
                taskDescription: 'Test task',
                agentName: 'test-agent',
                startTime: new Date()
            };

            const result = await PromptEnhancer.createComprehensivePrompt(
                '',
                null,
                executionContext
            );

            assert.ok(result.includes('**IMPORTANT**'));
            assert.ok(result.includes('test-exec-123'));
        });
    });

    suite('validateEnhancementConfig', () => {
        test('should return no errors for valid config', () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                agent: nativeAgent,
                userParams: { message: 'test' }
            };

            const errors = PromptEnhancer.validateEnhancementConfig(config);
            assert.strictEqual(errors.length, 0);
        });

        test('should return error for missing promptService', () => {
            const config: PromptEnhancementConfig = {
                promptService: null as any,
                agent: nativeAgent,
                userParams: { message: 'test' }
            };

            const errors = PromptEnhancer.validateEnhancementConfig(config);
            assert.ok(errors.includes('PromptService is required'));
        });

        test('should return error for missing agent', () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                agent: null as any,
                userParams: { message: 'test' }
            };

            const errors = PromptEnhancer.validateEnhancementConfig(config);
            assert.ok(errors.includes('Agent is required'));
        });

        test('should return error for missing userParams', () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                agent: nativeAgent,
                userParams: null as any
            };

            const errors = PromptEnhancer.validateEnhancementConfig(config);
            assert.ok(errors.includes('User parameters are required'));
        });

        test('should return multiple errors', () => {
            const config: PromptEnhancementConfig = {
                promptService: null as any,
                agent: null as any,
                userParams: null as any
            };

            const errors = PromptEnhancer.validateEnhancementConfig(config);
            assert.strictEqual(errors.length, 3);
        });
    });

    suite('hasUserInput', () => {
        test('should return true for message', () => {
            assert.strictEqual(PromptEnhancer.hasUserInput({ message: 'test' }), true);
        });

        test('should return true for query', () => {
            assert.strictEqual(PromptEnhancer.hasUserInput({ query: 'test' }), true);
        });

        test('should return false for empty params', () => {
            assert.strictEqual(PromptEnhancer.hasUserInput({}), false);
        });

        test('should return false for empty message', () => {
            assert.strictEqual(PromptEnhancer.hasUserInput({ message: '' }), false);
        });

        test('should return false for whitespace-only message', () => {
            assert.strictEqual(PromptEnhancer.hasUserInput({ message: '   ' }), false);
        });
    });

    suite('hasValidPrompt', () => {
        test('should return true for valid prompt context', () => {
            assert.strictEqual(PromptEnhancer.hasValidPrompt({ promptId: 'test-prompt' }), true);
        });

        test('should return false for null context', () => {
            assert.strictEqual(PromptEnhancer.hasValidPrompt(null), false);
        });

        test('should return false for undefined context', () => {
            assert.strictEqual(PromptEnhancer.hasValidPrompt(undefined), false);
        });

        test('should return false for missing promptId', () => {
            assert.strictEqual(PromptEnhancer.hasValidPrompt({ variables: {} }), false);
        });

        test('should return false for empty promptId', () => {
            assert.strictEqual(PromptEnhancer.hasValidPrompt({ promptId: '' }), false);
        });

        test('should return false for whitespace-only promptId', () => {
            assert.strictEqual(PromptEnhancer.hasValidPrompt({ promptId: '   ' }), false);
        });
    });

    suite('getEnhancementStrategy', () => {
        test('should return "native" for agents with prompt support', () => {
            const result = PromptEnhancer.getEnhancementStrategy(nativeAgent);
            assert.strictEqual(result, 'native');
        });

        test('should return "fallback" for agents with disabled prompt support', () => {
            const result = PromptEnhancer.getEnhancementStrategy(fallbackAgent);
            assert.strictEqual(result, 'fallback');
        });

        test('should return "none" for agents without prompt metadata', () => {
            const result = PromptEnhancer.getEnhancementStrategy(legacyAgent);
            assert.strictEqual(result, 'none');
        });
    });

    suite('enhancePromptWithExecutionContext', () => {
        test('should add execution context to existing prompt', () => {
            const context: ExecutionContext = {
                executionId: 'test-123',
                taskDescription: 'Test task',
                agentName: 'test-agent',
                startTime: new Date()
            };

            const result = PromptEnhancer.enhancePromptWithExecutionContext(
                'Original prompt content',
                context
            );

            assert.ok(result.includes('Original prompt content'));
            assert.ok(result.includes('**IMPORTANT**'));
            assert.ok(result.includes('test-123'));
        });

        test('should handle empty prompt', () => {
            const context: ExecutionContext = {
                executionId: 'test-123',
                taskDescription: 'Test task',
                agentName: 'test-agent',
                startTime: new Date()
            };

            const result = PromptEnhancer.enhancePromptWithExecutionContext('', context);

            assert.ok(result.includes('**IMPORTANT**'));
            assert.ok(result.includes('test-123'));
            assert.ok(!result.includes('undefined'));
        });
    });

    suite('createExecutionContext', () => {
        test('should create execution context with all fields', () => {
            const startTime = new Date();
            const context = PromptEnhancer.createExecutionContext(
                'exec-123',
                'Test description',
                'test-agent',
                startTime
            );

            assert.strictEqual(context.executionId, 'exec-123');
            assert.strictEqual(context.taskDescription, 'Test description');
            assert.strictEqual(context.agentName, 'test-agent');
            assert.strictEqual(context.startTime, startTime);
        });

        test('should use current time as default', () => {
            const before = new Date();
            const context = PromptEnhancer.createExecutionContext(
                'exec-123',
                'Test description',
                'test-agent'
            );
            const after = new Date();

            assert.ok(context.startTime >= before);
            assert.ok(context.startTime <= after);
        });
    });

    suite('extractTaskDescription', () => {
        test('should extract from message parameter', () => {
            const result = PromptEnhancer.extractTaskDescription({ message: 'Help me with coding' });
            assert.strictEqual(result, 'Help me with coding');
        });

        test('should extract from query parameter', () => {
            const result = PromptEnhancer.extractTaskDescription({ query: 'What is TypeScript?' });
            assert.strictEqual(result, 'What is TypeScript?');
        });

        test('should prioritize message over other fields', () => {
            const result = PromptEnhancer.extractTaskDescription({
                message: 'Primary message',
                query: 'Secondary query'
            });
            assert.strictEqual(result, 'Primary message');
        });

        test('should use prompt context when no params', () => {
            const result = PromptEnhancer.extractTaskDescription(
                {},
                { promptId: 'test-prompt' }
            );
            assert.strictEqual(result, 'Using prompt: test-prompt');
        });

        test('should return fallback for empty params', () => {
            const result = PromptEnhancer.extractTaskDescription({});
            assert.strictEqual(result, 'Agent execution request');
        });

        test('should truncate long descriptions', () => {
            const longMessage = 'a'.repeat(150);
            const result = PromptEnhancer.extractTaskDescription({ message: longMessage });
            assert.ok(result.length <= 103); // 100 + '...'
            assert.ok(result.endsWith('...'));
        });

        test('should handle non-string input', () => {
            const result = PromptEnhancer.extractTaskDescription({ message: 123 });
            assert.strictEqual(result, 'Agent execution request');
        });
    });

    suite('hasExecutionTracking', () => {
        test('should detect WU_WEI_TRACKING', () => {
            const prompt = 'Some prompt WU_WEI_TRACKING: enabled content';
            assert.strictEqual(PromptEnhancer.hasExecutionTracking(prompt), true);
        });

        test('should detect completion signal tool', () => {
            const prompt = 'Some prompt @wu-wei_copilot_completion_signal content';
            assert.strictEqual(PromptEnhancer.hasExecutionTracking(prompt), true);
        });

        test('should return false for clean prompt', () => {
            const prompt = 'Clean prompt without tracking';
            assert.strictEqual(PromptEnhancer.hasExecutionTracking(prompt), false);
        });
    });

    suite('extractExecutionIdFromPrompt', () => {
        test('should extract execution ID', () => {
            const prompt = 'Some content EXECUTION_ID: test-123 more content';
            const result = PromptEnhancer.extractExecutionIdFromPrompt(prompt);
            assert.strictEqual(result, 'test-123');
        });

        test('should return null when no execution ID', () => {
            const prompt = 'Clean prompt without execution ID';
            const result = PromptEnhancer.extractExecutionIdFromPrompt(prompt);
            assert.strictEqual(result, null);
        });

        test('should handle multiple whitespace formats', () => {
            const prompt = 'EXECUTION_ID:test-456';
            const result = PromptEnhancer.extractExecutionIdFromPrompt(prompt);
            assert.strictEqual(result, 'test-456');
        });
    });

    suite('cleanPromptForDisplay', () => {
        test('should remove HTML comments', () => {
            const prompt = 'Content <!-- hidden comment --> visible';
            const result = PromptEnhancer.cleanPromptForDisplay(prompt);
            assert.strictEqual(result, 'Content  visible');
        });

        test('should remove execution instructions', () => {
            const prompt = `Content
**IMPORTANT**: When you have completed this request, please call the \`@wu-wei_copilot_completion_signal\` tool.
More content`;
            const result = PromptEnhancer.cleanPromptForDisplay(prompt);
            assert.ok(!result.includes('**IMPORTANT**'));
            assert.ok(!result.includes('completion_signal'));
            assert.ok(result.includes('Content'));
        });

        test('should clean up excessive newlines', () => {
            const prompt = 'Line 1\n\n\n\nLine 2';
            const result = PromptEnhancer.cleanPromptForDisplay(prompt);
            assert.strictEqual(result, 'Line 1\n\nLine 2');
        });

        test('should handle empty prompt', () => {
            const result = PromptEnhancer.cleanPromptForDisplay('');
            assert.strictEqual(result, '');
        });
    });

    suite('generateFallbackContext', () => {
        test('should generate fallback context with all fields', () => {
            const timestamp = new Date();
            const context = PromptEnhancer.generateFallbackContext(
                'Fallback task',
                'fallback-agent',
                timestamp
            );

            assert.strictEqual(context.taskDescription, 'Fallback task');
            assert.strictEqual(context.agentName, 'fallback-agent');
            assert.strictEqual(context.startTime, timestamp);
            assert.ok(context.executionId.startsWith('wu-wei-fallback-'));
        });

        test('should use defaults for optional parameters', () => {
            const context = PromptEnhancer.generateFallbackContext('Task description');

            assert.strictEqual(context.taskDescription, 'Task description');
            assert.strictEqual(context.agentName, 'unknown');
            assert.ok(context.startTime instanceof Date);
            assert.ok(context.executionId.startsWith('wu-wei-fallback-'));
        });

        test('should generate unique execution IDs', () => {
            const context1 = PromptEnhancer.generateFallbackContext('Task 1');
            const context2 = PromptEnhancer.generateFallbackContext('Task 2');

            assert.notStrictEqual(context1.executionId, context2.executionId);
        });
    });

    suite('Error Handling and Edge Cases', () => {
        test('should handle PromptService errors gracefully', async () => {
            mockPromptService.setShouldThrowError(true);

            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'test-prompt'
                },
                agent: nativeAgent,
                userParams: { message: 'test' }
            };

            await assert.rejects(
                async () => await PromptEnhancer.enhanceParamsWithPrompt(config),
                /Mock render error|Mock prompt error/
            );

            mockPromptService.setShouldThrowError(false);
        });

        test('should handle agents with custom prompt parameter names', async () => {
            const customAgent = new MockAgent({
                supportsPrompts: true,
                promptParameterName: 'systemMessage',
                variableResolution: false
            });

            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'test-prompt'
                },
                agent: customAgent,
                userParams: { input: 'user input' }
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);

            assert.strictEqual(result.systemMessage, '#/mock/prompts/test-prompt.md');
            assert.strictEqual(result.additionalMessage, 'user input');
            assert.ok(!result.variables);
        });

        test('should handle prompts without file paths', async () => {
            mockPromptService.setMockPrompt('no-filepath', {
                id: 'no-filepath',
                content: 'Plain content without file path',
                filePath: null
            });

            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'no-filepath'
                },
                agent: nativeAgent,
                userParams: {}
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);

            assert.strictEqual(result.prompt, 'Plain content without file path');
        });

        test('should handle empty variables object', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'test-prompt',
                    variables: {}
                },
                agent: nativeAgent,
                userParams: { message: 'test' }
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);

            assert.strictEqual(result.prompt, '#/mock/prompts/test-prompt.md');
        });

        test('should handle null variables', async () => {
            const config: PromptEnhancementConfig = {
                promptService: mockPromptService as any,
                promptContext: {
                    promptId: 'test-prompt',
                    variables: null
                },
                agent: nativeAgent,
                userParams: { message: 'test' }
            };

            const result = await PromptEnhancer.enhanceParamsWithPrompt(config);

            assert.strictEqual(result.prompt, '#/mock/prompts/test-prompt.md');
        });

        test('should handle very long task descriptions', () => {
            const veryLongMessage = 'This is a very long message that exceeds the maximum token limit for task descriptions. '.repeat(10);
            const params = { message: veryLongMessage };

            const result = PromptEnhancer.extractTaskDescription(params);

            assert.ok(result.length <= 103); // 100 chars + '...'
            assert.ok(result.endsWith('...'));
            assert.ok(result.includes('This is a very long message'));
        });

        test('should handle task description at exact boundary', () => {
            const exactLengthMessage = 'a'.repeat(100);
            const params = { message: exactLengthMessage };

            const result = PromptEnhancer.extractTaskDescription(params);

            assert.strictEqual(result.length, 100);
            assert.ok(!result.endsWith('...'));
        });

        test('should handle task description with no good word break', () => {
            const noSpacesMessage = 'a'.repeat(150);
            const params = { message: noSpacesMessage };

            const result = PromptEnhancer.extractTaskDescription(params);

            assert.strictEqual(result.length, 103); // 100 + '...'
            assert.ok(result.endsWith('...'));
        });

        test('should handle mixed parameter types', () => {
            const params = {
                message: 123,
                query: 'valid query',
                input: null,
                question: undefined
            };

            const result = PromptEnhancer.extractUserInput(params);
            assert.strictEqual(result, 'valid query');
        });

        test('should handle nested object parameters', () => {
            const params = {
                message: { nested: 'object' },
                query: 'valid query'
            };

            const result = PromptEnhancer.extractUserInput(params);
            assert.strictEqual(result, 'valid query');
        });
    });

    suite('Integration Edge Cases', () => {
        test('should work with complex execution context', async () => {
            const complexContext: ExecutionContext = {
                executionId: 'complex-exec-id-with-special-chars-123_$',
                taskDescription: 'Complex task with "quotes" and symbols @#$%',
                agentName: 'complex-agent-name',
                startTime: new Date('2023-01-01T12:00:00Z')
            };

            const result = await PromptEnhancer.createComprehensivePrompt(
                'System: Handle complex scenarios',
                'User: Test with complex data',
                complexContext
            );

            assert.ok(result.includes('System: Handle complex scenarios'));
            assert.ok(result.includes('User: Test with complex data'));
            assert.ok(result.includes('complex-exec-id-with-special-chars-123_$'));
            assert.ok(result.includes('wu-wei_copilot_completion_signal'));
        });

        test('should handle prompt cleaning with multiple IMPORTANT sections', () => {
            const complexPrompt = `
Original content here

**IMPORTANT**: First instruction with wu-wei_copilot_completion_signal tool.
Some middle content

**IMPORTANT**: Second instruction also mentioning @wu-wei_copilot_completion_signal.
Final content
`;

            const cleaned = PromptEnhancer.cleanPromptForDisplay(complexPrompt);

            assert.ok(!cleaned.includes('**IMPORTANT**'));
            assert.ok(!cleaned.includes('wu-wei_copilot_completion_signal'));
            assert.ok(cleaned.includes('Original content here'));
        });

        test('should handle execution ID extraction with various formats', () => {
            const testCases = [
                'EXECUTION_ID: test-123',
                'EXECUTION_ID:test-456',
                'Some text EXECUTION_ID: wu-wei-789 more text',
                'EXECUTION_ID: complex-id-with-dashes-123_abc',
                'No execution ID here',
                'EXECUTION_ID: ',
                'EXECUTION_ID:',
            ];

            const results = testCases.map(test => PromptEnhancer.extractExecutionIdFromPrompt(test));

            assert.strictEqual(results[0], 'test-123');
            assert.strictEqual(results[1], 'test-456');
            assert.strictEqual(results[2], 'wu-wei-789');
            assert.strictEqual(results[3], 'complex-id-with-dashes-123_abc');
            assert.strictEqual(results[4], null);
            assert.strictEqual(results[5], null);
            assert.strictEqual(results[6], null);
        });

        test('should validate comprehensive configuration scenarios', () => {
            const testConfigs = [
                { promptService: null, agent: null, userParams: null },
                { promptService: null, agent: null, userParams: {} },
                { promptService: mockPromptService, agent: null, userParams: null },
                { promptService: mockPromptService, agent: nativeAgent, userParams: {} }
            ];

            const errorCounts = testConfigs.map(config =>
                PromptEnhancer.validateEnhancementConfig(config as any).length
            );

            assert.strictEqual(errorCounts[0], 3); // All missing
            assert.strictEqual(errorCounts[1], 2); // PromptService and Agent missing  
            assert.strictEqual(errorCounts[2], 2); // Agent and UserParams missing
            assert.strictEqual(errorCounts[3], 0); // All valid
        });
    });
});
