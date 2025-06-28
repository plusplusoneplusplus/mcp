/**
 * Unit tests for shared prompt manager utilities
 * Tests pure JavaScript/TypeScript logic without VS Code dependencies
 */

import * as assert from 'assert';
import { VariableResolver } from '../../../shared/promptManager/utils/variableResolver';
import { PromptRenderer } from '../../../shared/promptManager/utils/promptRenderer';
import { PromptValidators } from '../../../shared/promptManager/utils/validators';

suite('Shared Prompt Manager Tests', () => {

    suite('VariableResolver', () => {
        test('Basic variable resolution', () => {
            const resolver = new VariableResolver();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John', place: 'Paris' };

            const result = resolver.resolve(content, variables);
            assert.strictEqual(result, 'Hello John, welcome to Paris!');
        });

        test('Missing variables', () => {
            const resolver = new VariableResolver();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John' };

            const result = resolver.resolve(content, variables);
            assert.strictEqual(result, 'Hello John, welcome to !');
        });

        test('Extract variables', () => {
            const resolver = new VariableResolver();
            const content = 'Hello {{name}}, welcome to {{place}}!';

            const variables = resolver.extractVariables(content);
            assert.deepStrictEqual(variables, ['name', 'place']);
        });

        test('Default values', () => {
            const resolver = new VariableResolver();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John' };
            const options = { defaultValues: { place: 'World' } };

            const result = resolver.resolve(content, variables, options);
            assert.strictEqual(result, 'Hello John, welcome to World!');
        });

        test('Strict mode throws error', () => {
            const resolver = new VariableResolver();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John' };
            const options = { strictMode: true };

            assert.throws(() => {
                resolver.resolve(content, variables, options);
            }, /Undefined variable: place/);
        });
    });

    suite('PromptRenderer', () => {
        test('Basic rendering', async () => {
            const renderer = new PromptRenderer();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John', place: 'Paris' };

            const result = await renderer.render(content, variables);
            assert.strictEqual(result, 'Hello John, welcome to Paris!');
        });

        test('Preview with missing variables', () => {
            const renderer = new PromptRenderer();
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const variables = { name: 'John' };

            const result = renderer.previewRender(content, variables);
            assert.strictEqual(result.preview, 'Hello John, welcome to [place]!');
            assert.deepStrictEqual(result.missingVariables, ['place']);
        });

        test('Extract variables', () => {
            const renderer = new PromptRenderer();
            const content = 'Hello {{name}}, welcome to {{place}}!';

            const variables = renderer.extractVariables(content);
            assert.deepStrictEqual(variables, ['name', 'place']);
        });

        test('Batch rendering', async () => {
            const renderer = new PromptRenderer();
            const prompts = [
                { content: 'Hello {{name}}!', variables: { name: 'John' } },
                { content: 'Welcome {{user}}!', variables: { user: 'Jane' } }
            ];

            const results = await renderer.batchRender(prompts);
            assert.deepStrictEqual(results, ['Hello John!', 'Welcome Jane!']);
        });
    });

    suite('PromptValidators', () => {
        test('Valid content', () => {
            const content = 'Hello {{name}}, welcome to {{place}}!';
            const errors = PromptValidators.validatePromptContent(content);
            assert.strictEqual(errors.length, 0);
        });

        test('Empty content', () => {
            const content = '';
            const errors = PromptValidators.validatePromptContent(content);
            assert.ok(errors.length > 0, 'Should have validation errors for empty content');
            assert.strictEqual(errors[0].severity, 'error', 'Should be an error');
        });

        test('Unbalanced brackets', () => {
            const content = 'Hello {{name}, welcome!';
            const errors = PromptValidators.validatePromptContent(content);
            assert.ok(errors.length > 0, 'Should have validation errors for unbalanced brackets');
            assert.ok(
                errors.some(e => e.message.includes('Unbalanced variable brackets')),
                'Should detect unbalanced brackets'
            );
        });

        test('Invalid variable names', () => {
            const content = 'Hello {{name-invalid}}, welcome!';
            const errors = PromptValidators.validatePromptContent(content);
            assert.ok(errors.length > 0, 'Should have validation errors for invalid variable names');
        });
    });
}); 