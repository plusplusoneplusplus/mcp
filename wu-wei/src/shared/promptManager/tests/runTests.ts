/**
 * Simple test runner for shared prompt manager utilities
 * This provides basic smoke tests without external testing dependencies or VS Code modules
 */

import { VariableResolver } from '../utils/variableResolver';
import { PromptRenderer } from '../utils/promptRenderer';
import { PromptValidators } from '../utils/validators';

class TestRunner {
    private tests: Array<{ name: string; fn: () => Promise<void> | void }> = [];
    private passCount = 0;
    private failCount = 0;

    test(name: string, fn: () => Promise<void> | void) {
        this.tests.push({ name, fn });
    }

    private assert(condition: boolean, message: string) {
        if (!condition) {
            throw new Error(`Assertion failed: ${message}`);
        }
    }

    private assertEqual<T>(actual: T, expected: T, message?: string) {
        const actualStr = JSON.stringify(actual);
        const expectedStr = JSON.stringify(expected);
        if (actualStr !== expectedStr) {
            throw new Error(`Assertion failed: ${message || ''}\nExpected: ${expectedStr}\nActual: ${actualStr}`);
        }
    }

    async run(): Promise<void> {
        console.log(`🧪 Running ${this.tests.length} tests...\n`);

        for (const test of this.tests) {
            try {
                console.log(`  ▶ ${test.name}`);
                await test.fn();
                console.log(`    ✅ PASS`);
                this.passCount++;
            } catch (error) {
                console.log(`    ❌ FAIL: ${error instanceof Error ? error.message : String(error)}`);
                this.failCount++;
            }
        }

        console.log(`\n📊 Results: ${this.passCount} passed, ${this.failCount} failed`);

        if (this.failCount > 0) {
            throw new Error(`${this.failCount} tests failed`);
        }
    }

    // Test helper methods
    private testVariableResolver() {
        this.test('VariableResolver - Basic variable resolution', () => {
            const resolver = new VariableResolver();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John', place: 'Paris' };

            const result = resolver.resolve(content, variables);
            this.assertEqual(result, 'Hello John, welcome to Paris!');
        });

        this.test('VariableResolver - Missing variables', () => {
            const resolver = new VariableResolver();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John' };

            const result = resolver.resolve(content, variables);
            this.assertEqual(result, 'Hello John, welcome to !');
        });

        this.test('VariableResolver - Extract variables', () => {
            const resolver = new VariableResolver();
            const content = 'Hello {{name}}, welcome to {{place}}!';

            const variables = resolver.extractVariables(content);
            this.assertEqual(variables, ['name', 'place']);
        });

        this.test('VariableResolver - Default values', () => {
            const resolver = new VariableResolver();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John' };
            const options = { defaultValues: { place: 'World' } };

            const result = resolver.resolve(content, variables, options);
            this.assertEqual(result, 'Hello John, welcome to World!');
        });

        this.test('VariableResolver - Strict mode throws error', () => {
            const resolver = new VariableResolver();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John' };
            const options = { strictMode: true };

            try {
                resolver.resolve(content, variables, options);
                throw new Error('Should have thrown error in strict mode');
            } catch (error) {
                this.assert(
                    error instanceof Error && error.message.includes('Undefined variable: place'),
                    'Should throw error about undefined variable'
                );
            }
        });
    }

    private testPromptRenderer() {
        this.test('PromptRenderer - Basic rendering', async () => {
            const renderer = new PromptRenderer();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John', place: 'Paris' };

            const result = await renderer.render(content, variables);
            this.assertEqual(result, 'Hello John, welcome to Paris!');
        });

        this.test('PromptRenderer - Preview with missing variables', () => {
            const renderer = new PromptRenderer();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John' };

            const result = renderer.previewRender(content, variables);
            this.assertEqual(result.preview, 'Hello John, welcome to [place]!');
            this.assertEqual(result.missingVariables, ['place']);
        });

        this.test('PromptRenderer - Extract variables', () => {
            const renderer = new PromptRenderer();
            const content = 'Hello {{name}}, welcome to {{place}}!';

            const variables = renderer.extractVariables(content);
            this.assertEqual(variables, ['name', 'place']);
        });

        this.test('PromptRenderer - Batch rendering', async () => {
            const renderer = new PromptRenderer();
            const prompts = [
                { content: 'Hello {{name}}!', variables: { name: 'John' } },
                { content: 'Welcome {{user}}!', variables: { user: 'Jane' } }
            ];

            const results = await renderer.batchRender(prompts);
            this.assertEqual(results, ['Hello John!', 'Welcome Jane!']);
        });
    }

    private testPromptValidators() {
        this.test('PromptValidators - Valid content', () => {
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const errors = PromptValidators.validatePromptContent(content);
            this.assertEqual(errors.length, 0);
        });

        this.test('PromptValidators - Empty content', () => {
            const content = '';
            const errors = PromptValidators.validatePromptContent(content);
            this.assert(errors.length > 0, 'Should have validation errors for empty content');
            this.assert(errors[0].severity === 'error', 'Should be an error');
        });

        this.test('PromptValidators - Unbalanced brackets', () => {
            const content = 'Hello {{name}, welcome!';
            const errors = PromptValidators.validatePromptContent(content);
            this.assert(errors.length > 0, 'Should have validation errors for unbalanced brackets');
            this.assert(
                errors.some(e => e.message.includes('Unbalanced variable brackets')),
                'Should detect unbalanced brackets'
            );
        });

        this.test('PromptValidators - Invalid variable names', () => {
            const content = 'Hello {{name-invalid}}, welcome!';
            const errors = PromptValidators.validatePromptContent(content);
            this.assert(errors.length > 0, 'Should have validation errors for invalid variable names');
        });
    }

    setupTests() {
        this.testVariableResolver();
        this.testPromptRenderer();
        this.testPromptValidators();
    }
}

// Export function to run tests
export async function runSharedPromptManagerTests(): Promise<void> {
    const runner = new TestRunner();
    runner.setupTests();
    await runner.run();
}

// If this file is run directly
if (require.main === module) {
    runSharedPromptManagerTests()
        .then(() => {
            console.log('✅ All tests passed!');
            process.exit(0);
        })
        .catch((error) => {
            console.error('❌ Tests failed:', error);
            process.exit(1);
        });
} 