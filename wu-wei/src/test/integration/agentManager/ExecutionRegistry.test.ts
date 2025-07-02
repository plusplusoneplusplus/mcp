import * as assert from 'assert';
import * as vscode from 'vscode';
import { ExecutionRegistry, ActiveExecution } from '../../../agentManager/ExecutionRegistry';

/**
 * ExecutionRegistry Integration Tests
 * 
 * Tests the execution registry functionality including:
 * - In-memory execution tracking
 * - Persistent storage of completed executions
 * - Execution correlation strategies
 * - Session persistence across VSCode restarts
 */
suite('ExecutionRegistry Integration Tests', () => {
    let executionRegistry: ExecutionRegistry;
    let mockContext: vscode.ExtensionContext;
    let storedData: any = {};

    setup(() => {
        // Reset stored data for each test
        storedData = {};

        // Mock VSCode extension context
        mockContext = {
            subscriptions: [],
            globalState: {
                get: (key: string, defaultValue?: any) => storedData[key] || defaultValue,
                update: (key: string, value: any) => {
                    storedData[key] = value;
                    return Promise.resolve();
                }
            },
            extensionUri: vscode.Uri.file('/mock/extension/path')
        } as any;

        executionRegistry = new ExecutionRegistry(mockContext);
    });

    teardown(() => {
        executionRegistry.dispose();
    });

    suite('Initialization and Context Management', () => {
        test('should initialize without context', () => {
            const registry = new ExecutionRegistry();
            assert.ok(registry, 'Registry should initialize without context');
            
            const stats = registry.getStatistics();
            assert.strictEqual(stats.active, 0, 'Should have no active executions');
            assert.strictEqual(stats.completed, 0, 'Should have no completed executions');
            
            registry.dispose();
        });

        test('should set context and load history', () => {
            const registry = new ExecutionRegistry();
            registry.setContext(mockContext);
            
            const stats = registry.getStatistics();
            assert.strictEqual(stats.active, 0, 'Should have no active executions after setting context');
            
            registry.dispose();
        });

        test('should load existing completed history on initialization', () => {
            // Pre-populate storage with completed executions
            const existingHistory = [
                {
                    executionId: 'existing-exec-1',
                    agentName: 'test-agent',
                    method: 'test-method',
                    taskDescription: 'Existing test execution',
                    startTime: new Date().toISOString(),
                    status: 'completed' as const,
                    originalParams: {}
                }
            ];
            storedData['wu-wei.execution.registry.completed'] = existingHistory;

            const registry = new ExecutionRegistry(mockContext);
            const completedExecutions = registry.getCompletedExecutions();
            
            assert.strictEqual(completedExecutions.length, 1, 'Should load existing completed execution');
            assert.strictEqual(completedExecutions[0].executionId, 'existing-exec-1', 'Should load correct execution');
            assert.ok(completedExecutions[0].startTime instanceof Date, 'Should deserialize timestamps correctly');
            
            registry.dispose();
        });
    });

    suite('Execution Registration and Lifecycle', () => {
        test('should register new execution', () => {
            const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'test-exec-1',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Test execution',
                startTime: new Date(),
                status: 'pending',
                originalParams: { test: 'param' }
            };

            executionRegistry.registerExecution(execution);

            const activeExecutions = executionRegistry.getActiveExecutions();
            assert.strictEqual(activeExecutions.length, 1, 'Should have one active execution');
            assert.strictEqual(activeExecutions[0].executionId, 'test-exec-1', 'Should register correct execution');
            assert.ok(activeExecutions[0].timeoutHandle, 'Should set timeout handle');
        });

        test('should complete execution and move to history', () => {
            const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'test-exec-complete',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Test completion',
                startTime: new Date(),
                status: 'pending',
                originalParams: {}
            };

            executionRegistry.registerExecution(execution);
            assert.strictEqual(executionRegistry.getActiveExecutions().length, 1, 'Should have active execution');

            const completedExecution = executionRegistry.completeExecution('test-exec-complete');
            
            assert.ok(completedExecution, 'Should return completed execution');
            assert.strictEqual(completedExecution.status, 'completed', 'Should update status to completed');
            assert.strictEqual(executionRegistry.getActiveExecutions().length, 0, 'Should remove from active executions');
            assert.strictEqual(executionRegistry.getCompletedExecutions().length, 1, 'Should add to completed executions');
        });

        test('should fail execution and move to history', () => {
            const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'test-exec-fail',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Test failure',
                startTime: new Date(),
                status: 'pending',
                originalParams: {}
            };

            executionRegistry.registerExecution(execution);
            const failedExecution = executionRegistry.failExecution('test-exec-fail', 'Test error');
            
            assert.ok(failedExecution, 'Should return failed execution');
            assert.strictEqual(failedExecution.status, 'failed', 'Should update status to failed');
            assert.strictEqual(executionRegistry.getActiveExecutions().length, 0, 'Should remove from active executions');
            assert.strictEqual(executionRegistry.getCompletedExecutions().length, 1, 'Should add to completed executions');
        });

        test('should cancel execution', () => {
            const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'test-exec-cancel',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Test cancellation',
                startTime: new Date(),
                status: 'executing',
                originalParams: {}
            };

            executionRegistry.registerExecution(execution);
            const cancelled = executionRegistry.cancelExecution('test-exec-cancel');
            
            assert.strictEqual(cancelled, true, 'Should successfully cancel execution');
            assert.strictEqual(executionRegistry.getActiveExecutions().length, 0, 'Should remove from active executions');
            assert.strictEqual(executionRegistry.getCompletedExecutions().length, 1, 'Should add to completed executions');
        });

        test('should handle non-existent execution operations gracefully', () => {
            const completed = executionRegistry.completeExecution('non-existent');
            const failed = executionRegistry.failExecution('non-existent');
            const cancelled = executionRegistry.cancelExecution('non-existent');
            
            assert.strictEqual(completed, null, 'Should return null for non-existent completion');
            assert.strictEqual(failed, null, 'Should return null for non-existent failure');
            assert.strictEqual(cancelled, false, 'Should return false for non-existent cancellation');
        });
    });

    suite('Persistence Functionality', () => {
        test('should persist completed executions to storage', () => {
            const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'test-persist-1',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Test persistence',
                startTime: new Date(),
                status: 'pending',
                originalParams: { test: 'data' },
                promptContext: { context: 'test' }
            };

            executionRegistry.registerExecution(execution);
            executionRegistry.completeExecution('test-persist-1');

            // Verify data was saved to storage
            const storedExecutions = storedData['wu-wei.execution.registry.completed'];
            assert.ok(storedExecutions, 'Should save completed executions to storage');
            assert.strictEqual(storedExecutions.length, 1, 'Should save one execution');
            assert.strictEqual(storedExecutions[0].executionId, 'test-persist-1', 'Should save correct execution');
            assert.strictEqual(storedExecutions[0].status, 'completed', 'Should save correct status');
            assert.ok(typeof storedExecutions[0].startTime === 'string', 'Should serialize timestamps as strings');
        });

        test('should restore completed executions from storage', () => {
            // First, save some executions
            const execution1: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'restore-test-1',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Restore test 1',
                startTime: new Date('2024-01-01T10:00:00Z'),
                status: 'pending',
                originalParams: {}
            };

            executionRegistry.registerExecution(execution1);
            executionRegistry.completeExecution('restore-test-1');

            // Create new registry to test restoration
            const newRegistry = new ExecutionRegistry(mockContext);
            const restoredExecutions = newRegistry.getCompletedExecutions();

            assert.strictEqual(restoredExecutions.length, 1, 'Should restore completed executions');
            assert.strictEqual(restoredExecutions[0].executionId, 'restore-test-1', 'Should restore correct execution');
            assert.strictEqual(restoredExecutions[0].status, 'completed', 'Should restore correct status');
            assert.ok(restoredExecutions[0].startTime instanceof Date, 'Should deserialize timestamps as Date objects');

            newRegistry.dispose();
        });

        test('should handle storage limit correctly', () => {
            // Create more executions than the limit (100)
            for (let i = 0; i < 105; i++) {
                const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                    executionId: `limit-test-${i}`,
                    agentName: 'test-agent',
                    method: 'test-method',
                    taskDescription: `Limit test ${i}`,
                    startTime: new Date(),
                    status: 'pending',
                    originalParams: {}
                };

                executionRegistry.registerExecution(execution);
                executionRegistry.completeExecution(`limit-test-${i}`);
            }

            // Check that storage respects the limit
            const storedExecutions = storedData['wu-wei.execution.registry.completed'];
            assert.ok(storedExecutions.length <= 100, 'Should respect storage limit');
            assert.strictEqual(storedExecutions[storedExecutions.length - 1].executionId, 'limit-test-104', 'Should keep most recent executions');
        });

        test('should handle storage errors gracefully', () => {
            // Mock storage that throws errors
            const errorContext = {
                ...mockContext,
                globalState: {
                    get: () => { throw new Error('Storage read error'); },
                    update: () => { throw new Error('Storage write error'); }
                }
            } as any;

            // Should not throw during initialization
            assert.doesNotThrow(() => {
                const errorRegistry = new ExecutionRegistry(errorContext as any);
                errorRegistry.dispose();
            }, 'Should handle storage errors gracefully');
        });
    });

    suite('Execution Correlation Strategies', () => {
        test('should correlate by execution ID', () => {
            const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'correlation-test-1',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Correlation test',
                startTime: new Date(),
                status: 'executing',
                originalParams: {}
            };

            executionRegistry.registerExecution(execution);

            const correlated = executionRegistry.correlateByExecutionId('correlation-test-1');
            assert.ok(correlated, 'Should find execution by ID');
            assert.strictEqual(correlated.executionId, 'correlation-test-1', 'Should return correct execution');

            const notFound = executionRegistry.correlateByExecutionId('non-existent');
            assert.strictEqual(notFound, null, 'Should return null for non-existent ID');
        });

        test('should correlate by time (most recent)', () => {
            const execution1: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'time-test-1',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Time test 1',
                startTime: new Date(Date.now() - 1000),
                status: 'executing',
                originalParams: {}
            };

            const execution2: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'time-test-2',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Time test 2',
                startTime: new Date(),
                status: 'executing',
                originalParams: {}
            };

            executionRegistry.registerExecution(execution1);
            executionRegistry.registerExecution(execution2);

            const mostRecent = executionRegistry.correlateByTime();
            assert.ok(mostRecent, 'Should find most recent execution');
            assert.strictEqual(mostRecent.executionId, 'time-test-2', 'Should return most recent execution');
        });

        test('should correlate by content similarity', () => {
            const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'content-test-1',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Help me implement a new feature',
                startTime: new Date(),
                status: 'executing',
                originalParams: {}
            };

            executionRegistry.registerExecution(execution);

            // Exact match
            const exactMatch = executionRegistry.correlateByContent('Help me implement a new feature');
            assert.ok(exactMatch, 'Should find execution with exact content match');

            // Similar content (should match with 40% word overlap threshold)
            const similarMatch = executionRegistry.correlateByContent('implement new feature functionality');
            assert.ok(similarMatch, 'Should find execution with similar content');

            // Dissimilar content
            const noMatch = executionRegistry.correlateByContent('completely different task description');
            assert.strictEqual(noMatch, null, 'Should not match dissimilar content');
        });

        test('should use smart correlation with fallback strategies', () => {
            const execution1: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'smart-test-1',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Smart correlation test',
                startTime: new Date(Date.now() - 1000),
                status: 'executing',
                originalParams: {}
            };

            const execution2: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'smart-test-2',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Different task description',
                startTime: new Date(),
                status: 'executing',
                originalParams: {}
            };

            executionRegistry.registerExecution(execution1);
            executionRegistry.registerExecution(execution2);

            // Strategy 1: Exact ID match
            const exactIdMatch = executionRegistry.smartCorrelate('smart-test-1');
            assert.ok(exactIdMatch, 'Should find by exact ID');
            assert.strictEqual(exactIdMatch.executionId, 'smart-test-1', 'Should return correct execution by ID');

            // Strategy 2: Content similarity
            const contentMatch = executionRegistry.smartCorrelate(undefined, 'Smart correlation testing');
            assert.ok(contentMatch, 'Should find by content similarity');
            assert.strictEqual(contentMatch.executionId, 'smart-test-1', 'Should return execution with similar content');

            // Strategy 3: Temporal correlation (fallback)
            const temporalMatch = executionRegistry.smartCorrelate();
            assert.ok(temporalMatch, 'Should find by temporal correlation');
            assert.strictEqual(temporalMatch.executionId, 'smart-test-2', 'Should return most recent execution');
        });
    });

    suite('Statistics and History Management', () => {
        test('should provide accurate statistics', () => {
            // Add various executions with different states
            const executions = [
                { id: 'stats-1', complete: true, fail: false },
                { id: 'stats-2', complete: true, fail: false },
                { id: 'stats-3', complete: false, fail: true },
                { id: 'stats-4', complete: false, fail: false } // timeout
            ];

            executions.forEach(({ id, complete, fail }) => {
                const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                    executionId: id,
                    agentName: 'test-agent',
                    method: 'test-method',
                    taskDescription: `Statistics test ${id}`,
                    startTime: new Date(Date.now() - 1000),
                    status: 'pending',
                    originalParams: {}
                };

                executionRegistry.registerExecution(execution);
                
                if (complete) {
                    executionRegistry.completeExecution(id);
                } else if (fail) {
                    executionRegistry.failExecution(id);
                } else {
                    // Simulate timeout by directly calling the private method
                    (executionRegistry as any).timeoutExecution(id);
                }
            });

            const stats = executionRegistry.getStatistics();
            assert.strictEqual(stats.active, 0, 'Should have no active executions');
            assert.strictEqual(stats.completed, 2, 'Should have 2 completed executions');
            assert.strictEqual(stats.failed, 1, 'Should have 1 failed execution');
            assert.strictEqual(stats.timeout, 1, 'Should have 1 timed out execution');
            assert.ok(stats.averageDuration >= 0, 'Should calculate average duration');
        });

        test('should clear history', () => {
            // Add some completed executions
            const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'clear-test-1',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Clear test',
                startTime: new Date(),
                status: 'pending',
                originalParams: {}
            };

            executionRegistry.registerExecution(execution);
            executionRegistry.completeExecution('clear-test-1');

            assert.strictEqual(executionRegistry.getCompletedExecutions().length, 1, 'Should have completed execution');

            executionRegistry.clearHistory();
            
            assert.strictEqual(executionRegistry.getCompletedExecutions().length, 0, 'Should clear completed executions');
            
            // Verify storage was also cleared
            const storedExecutions = storedData['wu-wei.execution.registry.completed'];
            assert.deepStrictEqual(storedExecutions, [], 'Should clear storage');
        });
    });

    suite('Integration and Disposal', () => {
        test('should save data on disposal', () => {
            const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'disposal-test-1',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Disposal test',
                startTime: new Date(),
                status: 'pending',
                originalParams: {}
            };

            executionRegistry.registerExecution(execution);
            executionRegistry.completeExecution('disposal-test-1');

            // Dispose should save the completed execution
            executionRegistry.dispose();

            // Verify data was saved
            const storedExecutions = storedData['wu-wei.execution.registry.completed'];
            assert.ok(storedExecutions, 'Should save data on disposal');
            assert.strictEqual(storedExecutions.length, 1, 'Should save completed execution');
        });

        test('should cleanup timeouts on disposal', () => {
            const execution: Omit<ActiveExecution, 'timeoutHandle'> = {
                executionId: 'timeout-cleanup-test',
                agentName: 'test-agent',
                method: 'test-method',
                taskDescription: 'Timeout cleanup test',
                startTime: new Date(),
                status: 'executing',
                originalParams: {}
            };

            executionRegistry.registerExecution(execution);
            
            const activeExecution = executionRegistry.getActiveExecution('timeout-cleanup-test');
            assert.ok(activeExecution?.timeoutHandle, 'Should have timeout handle');

            // Disposal should clean up timeouts
            executionRegistry.dispose();
            
            // After disposal, should have no active executions
            assert.strictEqual(executionRegistry.getActiveExecutions().length, 0, 'Should clear active executions on disposal');
        });
    });
});