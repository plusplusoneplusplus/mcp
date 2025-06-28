import { PromptHelpers } from '../utils/promptHelpers';
import { ChatMessage, TokenBudget } from '../types';

/**
 * Simple test runner for PromptHelpers
 * This can be executed to verify functionality
 */
export class PromptHelpersTests {
    static runAllTests(): boolean {
        console.log('Running PromptHelpers tests...');

        const tests = [
            this.testEstimateTokenCount,
            this.testTruncateToTokenLimit,
            this.testFormatChatMessage,
            this.testFormatConversationHistory,
            this.testCalculateTokenBudget,
            this.testValidatePromptProps,
            this.testSanitizeContent,
            this.testGenerateId
        ];

        let passed = 0;
        let failed = 0;

        for (const test of tests) {
            try {
                test();
                console.log(`✓ ${test.name}`);
                passed++;
            } catch (error) {
                console.error(`✗ ${test.name}: ${error}`);
                failed++;
            }
        }

        console.log(`Tests completed: ${passed} passed, ${failed} failed`);
        return failed === 0;
    }

    static testEstimateTokenCount(): void {
        // Test empty/null inputs
        if (PromptHelpers.estimateTokenCount('') !== 0) {
            throw new Error('Empty string should return 0 tokens');
        }

        // Test basic estimation
        if (PromptHelpers.estimateTokenCount('test') !== 1) {
            throw new Error('4 character string should be 1 token');
        }

        if (PromptHelpers.estimateTokenCount('hello world') !== 3) {
            throw new Error('11 character string should be 3 tokens');
        }
    }

    static testTruncateToTokenLimit(): void {
        // Test invalid inputs
        if (PromptHelpers.truncateToTokenLimit('', 10) !== '') {
            throw new Error('Empty string should remain empty');
        }

        if (PromptHelpers.truncateToTokenLimit('test', 0) !== '') {
            throw new Error('Zero token limit should return empty string');
        }

        // Test within limit
        const text = 'hello world';
        if (PromptHelpers.truncateToTokenLimit(text, 10) !== text) {
            throw new Error('Text within limit should be unchanged');
        }

        // Test truncation
        const longText = 'a'.repeat(100);
        const truncated = PromptHelpers.truncateToTokenLimit(longText, 10);
        if (!truncated.endsWith('...')) {
            throw new Error('Truncated text should end with ...');
        }
    }

    static testFormatChatMessage(): void {
        const message: ChatMessage = {
            role: 'user',
            content: 'Hello, world!',
            timestamp: new Date('2023-01-01T12:00:00Z'),
            id: 'msg-1'
        };

        // Test without timestamp
        const result1 = PromptHelpers.formatChatMessage(message, false);
        if (result1 !== 'USER: Hello, world!') {
            throw new Error(`Expected 'USER: Hello, world!', got '${result1}'`);
        }

        // Test with timestamp
        const result2 = PromptHelpers.formatChatMessage(message, true);
        if (!result2.includes('USER') || !result2.includes('Hello, world!') || !result2.includes('[')) {
            throw new Error('Message with timestamp should contain role, content, and timestamp');
        }
    }

    static testFormatConversationHistory(): void {
        const messages: ChatMessage[] = [
            { role: 'user', content: 'Hello', id: '1' },
            { role: 'assistant', content: 'Hi there!', id: '2' },
            { role: 'user', content: 'How are you?', id: '3' }
        ];

        // Test empty history
        if (PromptHelpers.formatConversationHistory([]) !== '') {
            throw new Error('Empty history should return empty string');
        }

        // Test all messages
        const result = PromptHelpers.formatConversationHistory(messages);
        if (!result.includes('USER: Hello') || !result.includes('ASSISTANT: Hi there!')) {
            throw new Error('Formatted history should contain all messages');
        }

        // Test message limit
        const limited = PromptHelpers.formatConversationHistory(messages, 2);
        const lines = limited.split('\n\n');
        if (lines.length !== 2) {
            throw new Error('Limited history should respect maxMessages parameter');
        }
    }

    static testCalculateTokenBudget(): void {
        const budget = PromptHelpers.calculateTokenBudget(1000, 100, 50, 200, 300);

        if (budget.total !== 1000) {
            throw new Error('Total tokens should match input');
        }

        if (budget.reserved !== 150) {
            throw new Error('Reserved tokens should be system + user');
        }

        if (budget.flexible !== 850) {
            throw new Error('Flexible tokens should be total - reserved');
        }
    }

    static testValidatePromptProps(): void {
        // Test valid props
        const validProps = { required1: 'value', required2: 'value' };
        const validResult = PromptHelpers.validatePromptProps(validProps, ['required1', 'required2']);
        if (validResult.length !== 0) {
            throw new Error('Valid props should return no errors');
        }

        // Test missing props
        const invalidProps = { required1: 'value' };
        const invalidResult = PromptHelpers.validatePromptProps(invalidProps, ['required1', 'required2']);
        if (invalidResult.length === 0) {
            throw new Error('Missing props should return errors');
        }
    }

    static testSanitizeContent(): void {
        // Test empty input
        if (PromptHelpers.sanitizeContent('') !== '') {
            throw new Error('Empty string should remain empty');
        }

        // Test line ending normalization
        if (PromptHelpers.sanitizeContent('line1\r\nline2') !== 'line1\nline2') {
            throw new Error('Should normalize \\r\\n to \\n');
        }

        // Test trimming
        if (PromptHelpers.sanitizeContent('  content  ') !== 'content') {
            throw new Error('Should trim whitespace');
        }
    }

    static testGenerateId(): void {
        const id1 = PromptHelpers.generateId();
        const id2 = PromptHelpers.generateId();

        if (id1 === id2) {
            throw new Error('Generated IDs should be unique');
        }

        if (!/^msg_\d+_[a-z0-9]+$/.test(id1)) {
            throw new Error('Generated ID should match expected pattern');
        }
    }
} 