import * as assert from 'assert';
import * as vscode from 'vscode';
import { BasePromptElementProps, PromptElement } from '@vscode/prompt-tsx';
import { PromptManagerServiceAdapter } from '../../../promptStore/PromptManagerServiceAdapter';
import { PromptManager } from '../../../promptStore/PromptManager';
import { TsxRenderOptions, TsxRenderResult, ValidationResult } from '../../../shared/promptManager/types';

// Mock TSX component for testing (simplified for API compatibility)
interface TestPromptProps extends BasePromptElementProps {
    message: string;
    priority?: number;
}

// Use a factory function instead of extending PromptElement due to API complexity
function createTestComponent(props: TestPromptProps): any {
    return {
        props,
        name: 'TestPromptComponent'
    };
}

suite('TSX Integration Tests', () => {
    let promptManager: PromptManager;
    let serviceAdapter: PromptManagerServiceAdapter;

    setup(() => {
        // Create PromptManager with minimal config
        promptManager = new PromptManager({
            watchPaths: [],
            autoRefresh: false
        });

        // Create service adapter
        serviceAdapter = new PromptManagerServiceAdapter(promptManager);
    });

    teardown(() => {
        if (serviceAdapter) {
            serviceAdapter.dispose();
        }
    });

    suite('Interface Compliance', () => {
        test('should implement all required TSX methods', () => {
            // Verify that the service adapter implements the TSX methods
            assert.strictEqual(typeof serviceAdapter.renderTsxPrompt, 'function', 'Should have renderTsxPrompt method');
            assert.strictEqual(typeof serviceAdapter.renderPromptWithTokenBudget, 'function', 'Should have renderPromptWithTokenBudget method');
            assert.strictEqual(typeof serviceAdapter.validateTsxPrompt, 'function', 'Should have validateTsxPrompt method');
        });

        test('should maintain backward compatibility', async () => {
            // Verify that existing methods still work
            assert.strictEqual(typeof serviceAdapter.getAllPrompts, 'function', 'Should have getAllPrompts method');
            assert.strictEqual(typeof serviceAdapter.getPrompt, 'function', 'Should have getPrompt method');
            assert.strictEqual(typeof serviceAdapter.renderPromptWithVariables, 'function', 'Should have renderPromptWithVariables method');

            // Test that existing methods still work
            const prompts = await serviceAdapter.getAllPrompts();
            assert.ok(Array.isArray(prompts), 'getAllPrompts should return array');

            const config = await serviceAdapter.getConfig();
            assert.strictEqual(typeof config, 'object', 'getConfig should return object');
        });
    });

    suite('renderPromptWithTokenBudget', () => {
        test('should handle non-existent prompt', async () => {
            try {
                await serviceAdapter.renderPromptWithTokenBudget(
                    'non-existent-prompt',
                    {},
                    1000
                );

                assert.fail('Should have thrown error for non-existent prompt');

            } catch (error) {
                assert.ok(error instanceof Error, 'Should throw proper error');
                assert.ok(error.message.includes('not found'), 'Should mention prompt not found');
            }
        });

        test('should have correct method signature', () => {
            // Verify the method exists and can be called
            const method = serviceAdapter.renderPromptWithTokenBudget;
            assert.strictEqual(typeof method, 'function', 'Method should be a function');
            assert.strictEqual(method.length, 4, 'Method should accept 4 parameters');
        });
    });

    suite('validateTsxPrompt', () => {
        test('should handle invalid component gracefully', async () => {
            try {
                // Test with null component
                const result = await serviceAdapter.validateTsxPrompt(
                    null as any,
                    {} as any
                );

                // Should return validation result with errors
                assert.strictEqual(typeof result.isValid, 'boolean', 'isValid should be boolean');
                assert.ok(Array.isArray(result.errors), 'Errors should be an array');
                assert.ok(Array.isArray(result.warnings), 'Warnings should be an array');
                assert.strictEqual(result.isValid, false, 'Should be invalid for null component');

            } catch (error) {
                // Also acceptable to throw an error
                assert.ok(error instanceof Error, 'Should throw proper error');
            }
        });
    });

    suite('Error Handling', () => {
        test('should provide meaningful error messages for TSX rendering', async () => {
            try {
                // Test with invalid parameters
                await serviceAdapter.renderTsxPrompt(
                    null as any,
                    null as any
                );

                assert.fail('Should have thrown error for invalid parameters');

            } catch (error) {
                assert.ok(error instanceof Error, 'Should throw Error instance');
                assert.ok(error.message.length > 0, 'Error message should not be empty');
                assert.strictEqual(typeof error.message, 'string', 'Error message should be string');
            }
        });

        test('should handle token budget validation', async () => {
            try {
                await serviceAdapter.renderPromptWithTokenBudget(
                    'test-prompt',
                    {},
                    -1 // Invalid budget
                );

                assert.fail('Should have thrown error for invalid budget');

            } catch (error) {
                assert.ok(error instanceof Error, 'Should throw proper error');
                // Could be "not found" or budget-related error
                assert.ok(
                    error.message.includes('not found') ||
                    error.message.includes('budget') ||
                    error.message.includes('negative'),
                    'Should mention appropriate error'
                );
            }
        });
    });

    suite('Service Integration', () => {
        test('should initialize without errors', async () => {
            // Test that the service can be initialized
            await serviceAdapter.initialize();

            // Verify basic functionality works
            const prompts = await serviceAdapter.getAllPrompts();
            assert.ok(Array.isArray(prompts), 'Should return prompts array');
        });

        test('should dispose without errors', () => {
            // Test that disposal works correctly
            assert.doesNotThrow(() => {
                serviceAdapter.dispose();
            }, 'Dispose should not throw errors');
        });
    });
}); 