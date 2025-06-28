import { PromptHelpers } from '../../../shared/promptManager/tsx/utils/promptHelpers';
import { ChatMessage, TokenBudget } from '../../../shared/promptManager/tsx/types';
import * as assert from 'assert';

suite('PromptHelpers Tests', () => {

    test('estimateTokenCount', () => {
        // Test empty/null inputs
        assert.strictEqual(PromptHelpers.estimateTokenCount(''), 0, 'Empty string should return 0 tokens');

        // Test basic estimation
        assert.strictEqual(PromptHelpers.estimateTokenCount('test'), 1, '4 character string should be 1 token');

        assert.strictEqual(PromptHelpers.estimateTokenCount('hello world'), 3, '11 character string should be 3 tokens');
    });

    test('truncateToTokenLimit', () => {
        // Test invalid inputs
        assert.strictEqual(PromptHelpers.truncateToTokenLimit('', 10), '', 'Empty string should remain empty');

        assert.strictEqual(PromptHelpers.truncateToTokenLimit('test', 0), '', 'Zero token limit should return empty string');

        // Test within limit
        const text = 'hello world';
        assert.strictEqual(PromptHelpers.truncateToTokenLimit(text, 10), text, 'Text within limit should be unchanged');

        // Test truncation
        const longText = 'a'.repeat(100);
        const truncated = PromptHelpers.truncateToTokenLimit(longText, 10);
        assert.ok(truncated.endsWith('...'), 'Truncated text should end with ...');
    });

    test('formatChatMessage', () => {
        const message: ChatMessage = {
            role: 'user',
            content: 'Hello, world!',
            timestamp: new Date('2023-01-01T12:00:00Z'),
            id: 'msg-1'
        };

        // Test without timestamp
        const result1 = PromptHelpers.formatChatMessage(message, false);
        assert.strictEqual(result1, 'USER: Hello, world!', `Expected 'USER: Hello, world!', got '${result1}'`);

        // Test with timestamp
        const result2 = PromptHelpers.formatChatMessage(message, true);
        assert.ok(result2.includes('USER'), 'Message with timestamp should contain role');
        assert.ok(result2.includes('Hello, world!'), 'Message with timestamp should contain content');
        assert.ok(result2.includes('['), 'Message with timestamp should contain timestamp bracket');
    });

    test('formatConversationHistory', () => {
        const messages: ChatMessage[] = [
            { role: 'user', content: 'Hello', id: '1' },
            { role: 'assistant', content: 'Hi there!', id: '2' },
            { role: 'user', content: 'How are you?', id: '3' }
        ];

        // Test empty history
        assert.strictEqual(PromptHelpers.formatConversationHistory([]), '', 'Empty history should return empty string');

        // Test all messages
        const result = PromptHelpers.formatConversationHistory(messages);
        assert.ok(result.includes('USER: Hello'), 'Formatted history should contain first message');
        assert.ok(result.includes('ASSISTANT: Hi there!'), 'Formatted history should contain assistant message');

        // Test message limit
        const limited = PromptHelpers.formatConversationHistory(messages, 2);
        const lines = limited.split('\n\n');
        assert.strictEqual(lines.length, 2, 'Limited history should respect maxMessages parameter');
    });

    test('calculateTokenBudget', () => {
        const budget = PromptHelpers.calculateTokenBudget(1000, 100, 50, 200, 300);

        assert.strictEqual(budget.total, 1000, 'Total tokens should match input');
        assert.strictEqual(budget.reserved, 150, 'Reserved tokens should be system + user');
        assert.strictEqual(budget.flexible, 850, 'Flexible tokens should be total - reserved');
    });

    test('validatePromptProps', () => {
        // Test valid props
        const validProps = { required1: 'value', required2: 'value' };
        const validResult = PromptHelpers.validatePromptProps(validProps, ['required1', 'required2']);
        assert.strictEqual(validResult.length, 0, 'Valid props should return no errors');

        // Test missing props
        const invalidProps = { required1: 'value' };
        const invalidResult = PromptHelpers.validatePromptProps(invalidProps, ['required1', 'required2']);
        assert.ok(invalidResult.length > 0, 'Missing props should return errors');
    });

    test('sanitizeContent', () => {
        // Test empty input
        assert.strictEqual(PromptHelpers.sanitizeContent(''), '', 'Empty string should remain empty');

        // Test line ending normalization
        assert.strictEqual(PromptHelpers.sanitizeContent('line1\r\nline2'), 'line1\nline2', 'Should normalize \\r\\n to \\n');

        // Test trimming
        assert.strictEqual(PromptHelpers.sanitizeContent('  content  '), 'content', 'Should trim whitespace');
    });

    test('generateId', () => {
        const id1 = PromptHelpers.generateId();
        const id2 = PromptHelpers.generateId();

        assert.notStrictEqual(id1, id2, 'Generated IDs should be unique');
        assert.ok(/^msg_\d+_[a-z0-9]+$/.test(id1), 'Generated ID should match expected pattern');
    });

}); 