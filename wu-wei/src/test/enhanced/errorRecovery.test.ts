import * as assert from 'assert';
import * as vscode from 'vscode';
import { 
    ErrorRecoveryEngine, 
    ErrorType, 
    RecoveryStrategy,
    ErrorClassification,
    RecoveryAction,
    RecoveryResult 
} from '../../../src/chat/enhanced/ErrorRecoveryEngine';
import { 
    ToolError, 
    ToolCallContext, 
    ToolParticipantConfig,
    DEFAULT_TOOL_PARTICIPANT_CONFIG 
} from '../../../src/chat/enhanced/types';

suite('Error Recovery Engine Tests', () => {
    let engine: ErrorRecoveryEngine;
    let mockContext: ToolCallContext;

    setup(() => {
        const config: ToolParticipantConfig = {
            ...DEFAULT_TOOL_PARTICIPANT_CONFIG,
            enableAdvancedErrorRecovery: true,
            maxRecoveryAttempts: 2,
            errorRecoveryTimeout: 5000
        };
        
        engine = new ErrorRecoveryEngine(config);
        
        mockContext = {
            userIntent: 'analyze code',
            availableTools: [
                { name: 'codeAnalyzer', description: 'Analyzes code structure' },
                { name: 'fileReader', description: 'Reads file contents' },
                { name: 'searchTool', description: 'Searches for patterns' }
            ] as vscode.LanguageModelToolInformation[],
            conversationHistory: [],
            previousResults: {},
            roundNumber: 1
        };
    });

    teardown(() => {
        engine.clearRecoveryHistory();
    });

    suite('Error Classification', () => {
        test('should classify tool not found error correctly', () => {
            const error: ToolError = {
                toolName: 'unknownTool',
                callId: 'call-1',
                error: 'tool not found',
                timestamp: Date.now(),
                retryCount: 1
            };

            const classification = engine.classifyError(error, mockContext);

            assert.strictEqual(classification.type, ErrorType.TOOL_NOT_FOUND);
            assert.strictEqual(classification.severity, 'medium');
            assert.strictEqual(classification.recoverable, true);
            assert.strictEqual(classification.suggestedStrategy, RecoveryStrategy.FALLBACK_TOOL);
            assert.ok(classification.confidence > 0.8);
        });

        test('should classify permission error correctly', () => {
            const error: ToolError = {
                toolName: 'fileWriter',
                callId: 'call-2',
                error: 'permission denied: access denied to write file',
                timestamp: Date.now(),
                retryCount: 1
            };

            const classification = engine.classifyError(error, mockContext);

            assert.strictEqual(classification.type, ErrorType.PERMISSION_DENIED);
            assert.strictEqual(classification.severity, 'high');
            assert.strictEqual(classification.recoverable, false);
            assert.strictEqual(classification.suggestedStrategy, RecoveryStrategy.USER_INTERVENTION);
        });

        test('should classify timeout error correctly', () => {
            const error: ToolError = {
                toolName: 'slowTool',
                callId: 'call-3',
                error: 'operation timed out after 30 seconds',
                timestamp: Date.now(),
                retryCount: 2
            };

            const classification = engine.classifyError(error, mockContext);

            assert.strictEqual(classification.type, ErrorType.TIMEOUT);
            assert.strictEqual(classification.severity, 'medium');
            assert.strictEqual(classification.recoverable, true);
            assert.strictEqual(classification.suggestedStrategy, RecoveryStrategy.RETRY);
        });

        test('should classify parameter error correctly', () => {
            const error: ToolError = {
                toolName: 'validator',
                callId: 'call-4',
                error: 'invalid parameter: schema validation failed',
                timestamp: Date.now(),
                retryCount: 1
            };

            const classification = engine.classifyError(error, mockContext);

            assert.strictEqual(classification.type, ErrorType.INVALID_PARAMETERS);
            assert.strictEqual(classification.severity, 'low');
            assert.strictEqual(classification.recoverable, true);
            assert.strictEqual(classification.suggestedStrategy, RecoveryStrategy.PARAMETER_CORRECTION);
        });

        test('should classify rate limit error correctly', () => {
            const error: ToolError = {
                toolName: 'apiTool',
                callId: 'call-5',
                error: 'rate limit exceeded: too many requests',
                timestamp: Date.now(),
                retryCount: 0
            };

            const classification = engine.classifyError(error, mockContext);

            assert.strictEqual(classification.type, ErrorType.RATE_LIMIT);
            assert.strictEqual(classification.severity, 'low');
            assert.strictEqual(classification.recoverable, true);
            assert.strictEqual(classification.suggestedStrategy, RecoveryStrategy.RETRY);
            assert.ok(classification.details.rateLimited);
            assert.strictEqual(classification.details.suggestedDelay, 5000);
        });

        test('should classify unknown error with low confidence', () => {
            const error: ToolError = {
                toolName: 'mysterytool',
                callId: 'call-6',
                error: 'something went wrong in a mysterious way',
                timestamp: Date.now(),
                retryCount: 1
            };

            const classification = engine.classifyError(error, mockContext);

            assert.strictEqual(classification.type, ErrorType.UNKNOWN);
            assert.strictEqual(classification.severity, 'medium');
            assert.strictEqual(classification.recoverable, false);
            assert.strictEqual(classification.suggestedStrategy, RecoveryStrategy.GRACEFUL_DEGRADATION);
            assert.ok(classification.confidence <= 0.5);
        });
    });

    suite('Recovery Action Generation', () => {
        test('should generate retry action for timeout error', () => {
            const classification: ErrorClassification = {
                type: ErrorType.TIMEOUT,
                severity: 'medium',
                recoverable: true,
                suggestedStrategy: RecoveryStrategy.RETRY,
                confidence: 0.8,
                details: {}
            };

            const error: ToolError = {
                toolName: 'slowTool',
                callId: 'call-1',
                error: 'timeout',
                timestamp: Date.now(),
                retryCount: 1
            };

            const action = engine.generateRecoveryAction(classification, error, mockContext);

            assert.strictEqual(action.strategy, RecoveryStrategy.RETRY);
            assert.strictEqual(action.retryable, true);
            assert.ok(action.description.includes('retry'));
            assert.ok(action.parameters.delay > 0);
        });

        test('should generate fallback tool action for tool not found', () => {
            const classification: ErrorClassification = {
                type: ErrorType.TOOL_NOT_FOUND,
                severity: 'medium',
                recoverable: true,
                suggestedStrategy: RecoveryStrategy.FALLBACK_TOOL,
                confidence: 0.9,
                details: { availableTools: mockContext.availableTools.map(t => t.name) }
            };

            const error: ToolError = {
                toolName: 'missingTool',
                callId: 'call-2',
                error: 'tool not found',
                timestamp: Date.now(),
                retryCount: 1
            };

            const action = engine.generateRecoveryAction(classification, error, mockContext);

            assert.strictEqual(action.strategy, RecoveryStrategy.FALLBACK_TOOL);
            assert.strictEqual(action.retryable, false);
            assert.ok(action.description.includes('alternative tool'));
            assert.ok(action.fallbackOptions && action.fallbackOptions.length > 0);
        });

        test('should generate user intervention action for permission error', () => {
            const classification: ErrorClassification = {
                type: ErrorType.PERMISSION_DENIED,
                severity: 'high',
                recoverable: false,
                suggestedStrategy: RecoveryStrategy.USER_INTERVENTION,
                confidence: 0.85,
                details: { requiresUserAction: true }
            };

            const error: ToolError = {
                toolName: 'restrictedTool',
                callId: 'call-3',
                error: 'permission denied',
                timestamp: Date.now(),
                retryCount: 0
            };

            const action = engine.generateRecoveryAction(classification, error, mockContext);

            assert.strictEqual(action.strategy, RecoveryStrategy.USER_INTERVENTION);
            assert.strictEqual(action.retryable, false);
            assert.ok(action.description.includes('user action'));
            assert.ok(action.parameters.userActionRequired);
        });
    });

    suite('Recovery Execution', () => {
        test('should execute retry recovery successfully', async () => {
            const action: RecoveryAction = {
                strategy: RecoveryStrategy.RETRY,
                description: 'Retry after delay',
                parameters: { delay: 100, retryCount: 2 },
                retryable: true
            };

            const error: ToolError = {
                toolName: 'testTool',
                callId: 'call-1',
                error: 'timeout',
                timestamp: Date.now(),
                retryCount: 1
            };

            const result = await engine.executeRecovery(action, error, mockContext);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.shouldContinue, true);
            assert.ok(result.userMessage?.includes('Retrying'));
        });

        test('should execute fallback tool recovery', async () => {
            const action: RecoveryAction = {
                strategy: RecoveryStrategy.FALLBACK_TOOL,
                description: 'Use alternative tool',
                parameters: { originalTool: 'missingTool' },
                retryable: false,
                fallbackOptions: ['codeAnalyzer', 'fileReader']
            };

            const error: ToolError = {
                toolName: 'missingTool',
                callId: 'call-2',
                error: 'tool not found',
                timestamp: Date.now(),
                retryCount: 1
            };

            const result = await engine.executeRecovery(action, error, mockContext);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.shouldContinue, true);
            assert.ok(result.alternativeApproach?.includes('codeAnalyzer'));
            assert.ok(result.userMessage?.includes('alternative tool'));
        });

        test('should execute graceful degradation', async () => {
            const action: RecoveryAction = {
                strategy: RecoveryStrategy.GRACEFUL_DEGRADATION,
                description: 'Continue without tool',
                parameters: { skipTool: 'optionalTool' },
                retryable: false
            };

            const error: ToolError = {
                toolName: 'optionalTool',
                callId: 'call-3',
                error: 'service unavailable',
                timestamp: Date.now(),
                retryCount: 2
            };

            const result = await engine.executeRecovery(action, error, mockContext);

            assert.strictEqual(result.success, true);
            assert.strictEqual(result.shouldContinue, true);
            assert.ok(result.alternativeApproach?.includes('continue without'));
        });

        test('should handle user intervention requirement', async () => {
            const action: RecoveryAction = {
                strategy: RecoveryStrategy.USER_INTERVENTION,
                description: 'Requires user action',
                parameters: { userActionRequired: true },
                retryable: false
            };

            const error: ToolError = {
                toolName: 'permissionTool',
                callId: 'call-4',
                error: 'access denied',
                timestamp: Date.now(),
                retryCount: 0
            };

            const result = await engine.executeRecovery(action, error, mockContext);

            assert.strictEqual(result.success, false);
            assert.strictEqual(result.shouldContinue, false);
            assert.ok(result.userMessage?.includes('requires your attention'));
        });
    });

    suite('Workflow Continuation Logic', () => {
        test('should continue workflow for recoverable errors', () => {
            const error: ToolError = {
                toolName: 'recoverableTool',
                callId: 'call-1',
                error: 'timeout',
                timestamp: Date.now(),
                retryCount: 1
            };

            const shouldContinue = engine.shouldContinueWorkflow(error, mockContext, 1);
            assert.strictEqual(shouldContinue, true);
        });

        test('should stop workflow for critical errors', () => {
            const error: ToolError = {
                toolName: 'criticalTool',
                callId: 'call-1',
                error: 'permission denied',
                timestamp: Date.now(),
                retryCount: 0
            };

            const shouldContinue = engine.shouldContinueWorkflow(error, mockContext, 1);
            assert.strictEqual(shouldContinue, false);
        });

        test('should stop workflow when too many errors accumulate', () => {
            const error: ToolError = {
                toolName: 'problematicTool',
                callId: 'call-1',
                error: 'random failure',
                timestamp: Date.now(),
                retryCount: 1
            };

            const shouldContinue = engine.shouldContinueWorkflow(error, mockContext, 10);
            assert.strictEqual(shouldContinue, false);
        });

        test('should stop workflow after exceeding retry attempts for specific tool', () => {
            const error: ToolError = {
                toolName: 'retryTool',
                callId: 'call-1',
                error: 'timeout',
                timestamp: Date.now(),
                retryCount: 1
            };

            // Simulate multiple failed recoveries for the same tool
            for (let i = 0; i < 5; i++) {
                const action: RecoveryAction = {
                    strategy: RecoveryStrategy.RETRY,
                    description: 'Retry',
                    parameters: {},
                    retryable: true
                };

                const failedResult: RecoveryResult = {
                    success: false,
                    action,
                    shouldContinue: false
                };

                // Manually record failed attempts to simulate history
                (engine as any).recordRecoveryAttempt('retryTool', failedResult);
            }

            const shouldContinue = engine.shouldContinueWorkflow(error, mockContext, 1);
            assert.strictEqual(shouldContinue, false);
        });
    });

    suite('Recovery Suggestions', () => {
        test('should provide helpful suggestions for tool not found errors', () => {
            const classification: ErrorClassification = {
                type: ErrorType.TOOL_NOT_FOUND,
                severity: 'medium',
                recoverable: true,
                suggestedStrategy: RecoveryStrategy.FALLBACK_TOOL,
                confidence: 0.9,
                details: {}
            };

            const error: ToolError = {
                toolName: 'missingTool',
                callId: 'call-1',
                error: 'tool not found',
                timestamp: Date.now(),
                retryCount: 1
            };

            const suggestions = engine.getRecoverySuggestions(classification, error, mockContext);

            assert.ok(suggestions.length > 0);
            assert.ok(suggestions.some(s => s.includes('not available')));
            assert.ok(suggestions.some(s => s.includes('alternative tool')));
            assert.ok(suggestions.some(s => s.includes('Available tools')));
        });

        test('should provide permission error guidance', () => {
            const classification: ErrorClassification = {
                type: ErrorType.PERMISSION_DENIED,
                severity: 'high',
                recoverable: false,
                suggestedStrategy: RecoveryStrategy.USER_INTERVENTION,
                confidence: 0.85,
                details: {}
            };

            const error: ToolError = {
                toolName: 'restrictedTool',
                callId: 'call-2',
                error: 'permission denied',
                timestamp: Date.now(),
                retryCount: 0
            };

            const suggestions = engine.getRecoverySuggestions(classification, error, mockContext);

            assert.ok(suggestions.length > 0);
            assert.ok(suggestions.some(s => s.includes('Permission denied')));
            assert.ok(suggestions.some(s => s.includes('permissions')));
            assert.ok(suggestions.some(s => s.includes('workspace trust')));
        });

        test('should provide network error troubleshooting', () => {
            const classification: ErrorClassification = {
                type: ErrorType.NETWORK_ERROR,
                severity: 'medium',
                recoverable: true,
                suggestedStrategy: RecoveryStrategy.RETRY,
                confidence: 0.75,
                details: {}
            };

            const error: ToolError = {
                toolName: 'networkTool',
                callId: 'call-3',
                error: 'connection failed',
                timestamp: Date.now(),
                retryCount: 1
            };

            const suggestions = engine.getRecoverySuggestions(classification, error, mockContext);

            assert.ok(suggestions.length > 0);
            assert.ok(suggestions.some(s => s.includes('Network connectivity')));
            assert.ok(suggestions.some(s => s.includes('connection')));
            assert.ok(suggestions.some(s => s.includes('proxy')));
        });
    });

    suite('Recovery Statistics', () => {
        test('should track recovery statistics correctly', async () => {
            // Execute several recovery attempts
            const actions: RecoveryAction[] = [
                {
                    strategy: RecoveryStrategy.RETRY,
                    description: 'Retry 1',
                    parameters: {},
                    retryable: true
                },
                {
                    strategy: RecoveryStrategy.FALLBACK_TOOL,
                    description: 'Fallback 1',
                    parameters: {},
                    retryable: false,
                    fallbackOptions: ['alt1']
                },
                {
                    strategy: RecoveryStrategy.RETRY,
                    description: 'Retry 2',
                    parameters: {},
                    retryable: true
                }
            ];

            const errors: ToolError[] = [
                {
                    toolName: 'tool1',
                    callId: 'call-1',
                    error: 'timeout',
                    timestamp: Date.now(),
                    retryCount: 1
                },
                {
                    toolName: 'tool2',
                    callId: 'call-2',
                    error: 'not found',
                    timestamp: Date.now(),
                    retryCount: 1
                },
                {
                    toolName: 'tool1',
                    callId: 'call-3',
                    error: 'timeout',
                    timestamp: Date.now(),
                    retryCount: 2
                }
            ];

            // Execute recoveries
            for (let i = 0; i < actions.length; i++) {
                await engine.executeRecovery(actions[i], errors[i], mockContext);
            }

            const stats = engine.getRecoveryStatistics();

            assert.strictEqual(stats.totalRecoveryAttempts, 3);
            assert.strictEqual(stats.successfulRecoveries, 3); // All simulated as successful
            assert.strictEqual(stats.recoveryStrategies[RecoveryStrategy.RETRY], 2);
            assert.strictEqual(stats.recoveryStrategies[RecoveryStrategy.FALLBACK_TOOL], 1);
            assert.ok(stats.toolsWithMostErrors.length > 0);
            assert.strictEqual(stats.toolsWithMostErrors[0].toolName, 'tool1');
            assert.strictEqual(stats.toolsWithMostErrors[0].errorCount, 2);
        });

        test('should clear recovery history', () => {
            // Add some history first
            const action: RecoveryAction = {
                strategy: RecoveryStrategy.RETRY,
                description: 'Test',
                parameters: {},
                retryable: true
            };

            const error: ToolError = {
                toolName: 'testTool',
                callId: 'call-1',
                error: 'test error',
                timestamp: Date.now(),
                retryCount: 1
            };

            (engine as any).recordRecoveryAttempt('testTool', {
                success: true,
                action,
                shouldContinue: true
            });

            let stats = engine.getRecoveryStatistics();
            assert.ok(stats.totalRecoveryAttempts > 0);

            // Clear history
            engine.clearRecoveryHistory();

            stats = engine.getRecoveryStatistics();
            assert.strictEqual(stats.totalRecoveryAttempts, 0);
            assert.strictEqual(stats.successfulRecoveries, 0);
            assert.strictEqual(Object.keys(stats.recoveryStrategies).length, 0);
            assert.strictEqual(stats.toolsWithMostErrors.length, 0);
        });
    });

    suite('Error Recovery Prompts', () => {
        test('should generate detailed error recovery prompt', () => {
            const error: ToolError = {
                toolName: 'testTool',
                callId: 'call-1',
                error: 'connection timeout',
                timestamp: Date.now(),
                retryCount: 1
            };

            const classification: ErrorClassification = {
                type: ErrorType.TIMEOUT,
                severity: 'medium',
                recoverable: true,
                suggestedStrategy: RecoveryStrategy.RETRY,
                confidence: 0.8,
                details: {}
            };

            const suggestions = ['Operation timed out', 'Retry recommended'];

            const prompt = engine.generateErrorRecoveryPrompt(error, classification, mockContext, suggestions);

            assert.ok(prompt.includes('testTool'));
            assert.ok(prompt.includes('connection timeout'));
            assert.ok(prompt.includes('timeout'));
            assert.ok(prompt.includes('medium'));
            assert.ok(prompt.includes('80%'));
            assert.ok(prompt.includes('Alternative Tools'));
        });
    });

    suite('Edge Cases and Error Handling', () => {
        test('should handle empty available tools gracefully', () => {
            const emptyContext: ToolCallContext = {
                ...mockContext,
                availableTools: []
            };

            const error: ToolError = {
                toolName: 'anyTool',
                callId: 'call-1',
                error: 'tool not found',
                timestamp: Date.now(),
                retryCount: 1
            };

            const classification = engine.classifyError(error, emptyContext);
            const suggestions = engine.getRecoverySuggestions(classification, error, emptyContext);

            assert.ok(classification.type === ErrorType.TOOL_NOT_FOUND);
            assert.ok(suggestions.length > 0);
        });

        test('should handle malformed error messages', () => {
            const error: ToolError = {
                toolName: 'weirdTool',
                callId: 'call-1',
                error: '', // Empty error message
                timestamp: Date.now(),
                retryCount: 1
            };

            const classification = engine.classifyError(error, mockContext);

            assert.strictEqual(classification.type, ErrorType.UNKNOWN);
            assert.ok(classification.confidence <= 0.5);
        });

        test('should handle very old timestamps in recovery history', () => {
            const veryOldError: ToolError = {
                toolName: 'oldTool',
                callId: 'call-1',
                error: 'old error',
                timestamp: Date.now() - (24 * 60 * 60 * 1000), // 24 hours ago
                retryCount: 1
            };

            const shouldContinue = engine.shouldContinueWorkflow(veryOldError, mockContext, 1);
            
            // Should continue because old errors shouldn't affect current decision
            assert.strictEqual(shouldContinue, true);
        });

        test('should handle null or undefined inputs gracefully', () => {
            const invalidError = {
                toolName: '',
                callId: '',
                error: undefined as any,
                timestamp: Date.now(),
                retryCount: 0
            };

            // Should not throw an error
            assert.doesNotThrow(() => {
                engine.classifyError(invalidError, mockContext);
            });
        });
    });
});
