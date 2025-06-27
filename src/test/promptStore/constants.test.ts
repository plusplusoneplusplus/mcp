/**
 * Unit tests for constants
 * Testing wu wei principle: ensuring configuration constants are well-formed
 */

import * as assert from 'assert';
import {
    DEFAULT_CONFIG,
    FILE_PATTERNS,
    VALIDATION_RULES,
    UI_CONFIG,
    WATCHER_CONFIG,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES
} from '../../promptStore/constants';

suite('Constants Tests', () => {
    suite('DEFAULT_CONFIG', () => {
        test('Should have required properties', () => {
            assert(typeof DEFAULT_CONFIG === 'object');
            assert(typeof DEFAULT_CONFIG.rootDirectory === 'string');
            assert(Array.isArray(DEFAULT_CONFIG.watchPaths));
            assert(Array.isArray(DEFAULT_CONFIG.filePatterns));
            assert(Array.isArray(DEFAULT_CONFIG.excludePatterns));
            assert(typeof DEFAULT_CONFIG.autoRefresh === 'boolean');
            assert(typeof DEFAULT_CONFIG.refreshInterval === 'number');
            assert(typeof DEFAULT_CONFIG.enableCache === 'boolean');
            assert(typeof DEFAULT_CONFIG.maxCacheSize === 'number');
        });

        test('Should have valid sort configuration', () => {
            assert(['name', 'modified', 'category'].includes(DEFAULT_CONFIG.sortBy));
            assert(['asc', 'desc'].includes(DEFAULT_CONFIG.sortOrder));
        });

        test('Should have reasonable default values', () => {
            assert(DEFAULT_CONFIG.refreshInterval > 0);
            assert(DEFAULT_CONFIG.maxCacheSize > 0);
            assert(DEFAULT_CONFIG.watchPaths.length > 0);
        });
    });

    suite('FILE_PATTERNS', () => {
        test('Should contain valid file pattern arrays', () => {
            assert(Array.isArray(FILE_PATTERNS.MARKDOWN));
            assert(Array.isArray(FILE_PATTERNS.TEXT));
            assert(Array.isArray(FILE_PATTERNS.ALL_SUPPORTED));

            assert(FILE_PATTERNS.MARKDOWN.length > 0);
            assert(FILE_PATTERNS.ALL_SUPPORTED.length > 0);
        });

        test('Should include expected markdown patterns', () => {
            assert(FILE_PATTERNS.MARKDOWN.includes('**/*.md'));
            assert(FILE_PATTERNS.ALL_SUPPORTED.includes('**/*.md'));
        });
    });

    suite('VALIDATION_RULES', () => {
        test('Should have title validation rules', () => {
            assert(typeof VALIDATION_RULES.TITLE === 'object');
            assert(typeof VALIDATION_RULES.TITLE.MIN_LENGTH === 'number');
            assert(typeof VALIDATION_RULES.TITLE.MAX_LENGTH === 'number');
            assert(VALIDATION_RULES.TITLE.PATTERN instanceof RegExp);
            assert(VALIDATION_RULES.TITLE.MIN_LENGTH > 0);
        });

        test('Should have description validation rules', () => {
            assert(typeof VALIDATION_RULES.DESCRIPTION === 'object');
            assert(typeof VALIDATION_RULES.DESCRIPTION.MAX_LENGTH === 'number');
            assert(VALIDATION_RULES.DESCRIPTION.MAX_LENGTH > 0);
        });

        test('Should have category validation rules', () => {
            assert(typeof VALIDATION_RULES.CATEGORY === 'object');
            assert(VALIDATION_RULES.CATEGORY.PATTERN instanceof RegExp);
            assert(typeof VALIDATION_RULES.CATEGORY.MAX_LENGTH === 'number');
        });

        test('Should have tag validation rules', () => {
            assert(typeof VALIDATION_RULES.TAG === 'object');
            assert(VALIDATION_RULES.TAG.PATTERN instanceof RegExp);
            assert(typeof VALIDATION_RULES.TAG.MAX_LENGTH === 'number');
            assert(typeof VALIDATION_RULES.TAG.MAX_COUNT === 'number');
        });
    });

    suite('UI_CONFIG', () => {
        test('Should have webview configuration', () => {
            assert(typeof UI_CONFIG.WEBVIEW === 'object');
            assert(typeof UI_CONFIG.WEBVIEW.TITLE === 'string');
            assert(typeof UI_CONFIG.WEBVIEW.ICON === 'string');
            assert(typeof UI_CONFIG.WEBVIEW.RETAIN_CONTEXT_WHEN_HIDDEN === 'boolean');
        });

        test('Should have search configuration', () => {
            assert(typeof UI_CONFIG.SEARCH === 'object');
            assert(typeof UI_CONFIG.SEARCH.DEBOUNCE_DELAY === 'number');
            assert(typeof UI_CONFIG.SEARCH.MIN_QUERY_LENGTH === 'number');
            assert(typeof UI_CONFIG.SEARCH.MAX_RESULTS === 'number');
            assert(UI_CONFIG.SEARCH.DEBOUNCE_DELAY > 0);
        });

        test('Should have pagination configuration', () => {
            assert(typeof UI_CONFIG.PAGINATION === 'object');
            assert(typeof UI_CONFIG.PAGINATION.DEFAULT_PAGE_SIZE === 'number');
            assert(typeof UI_CONFIG.PAGINATION.MAX_PAGE_SIZE === 'number');
            assert(UI_CONFIG.PAGINATION.DEFAULT_PAGE_SIZE > 0);
            assert(UI_CONFIG.PAGINATION.MAX_PAGE_SIZE >= UI_CONFIG.PAGINATION.DEFAULT_PAGE_SIZE);
        });
    });

    suite('WATCHER_CONFIG', () => {
        test('Should have valid watcher settings', () => {
            assert(typeof WATCHER_CONFIG === 'object');
            assert(Array.isArray(WATCHER_CONFIG.IGNORED));
            assert(typeof WATCHER_CONFIG.POLL_INTERVAL === 'number');
            assert(typeof WATCHER_CONFIG.USE_POLLING === 'boolean');
            assert(typeof WATCHER_CONFIG.DEBOUNCE_MS === 'number');
            assert(typeof WATCHER_CONFIG.MAX_DEPTH === 'number');
        });

        test('Should have reasonable timing values', () => {
            assert(WATCHER_CONFIG.POLL_INTERVAL > 0);
            assert(WATCHER_CONFIG.DEBOUNCE_MS > 0);
            assert(WATCHER_CONFIG.MAX_DEPTH > 0);
        });

        test('Should have ignored patterns as RegExp', () => {
            WATCHER_CONFIG.IGNORED.forEach(pattern => {
                assert(pattern instanceof RegExp);
            });
        });
    });

    suite('ERROR_MESSAGES', () => {
        test('Should contain required error messages', () => {
            assert(typeof ERROR_MESSAGES === 'object');
            assert(typeof ERROR_MESSAGES.FILE_NOT_FOUND === 'string');
            assert(typeof ERROR_MESSAGES.INVALID_FRONTMATTER === 'string');
            assert(typeof ERROR_MESSAGES.MISSING_TITLE === 'string');
            assert(typeof ERROR_MESSAGES.INVALID_METADATA === 'string');
        });

        test('Should have non-empty error messages', () => {
            Object.values(ERROR_MESSAGES).forEach(message => {
                assert(typeof message === 'string');
                assert(message.length > 0);
            });
        });
    });

    suite('SUCCESS_MESSAGES', () => {
        test('Should contain required success messages', () => {
            assert(typeof SUCCESS_MESSAGES === 'object');
            assert(typeof SUCCESS_MESSAGES.PROMPTS_LOADED === 'string');
            assert(typeof SUCCESS_MESSAGES.WATCHER_STARTED === 'string');
            assert(typeof SUCCESS_MESSAGES.CACHE_CLEARED === 'string');
        });

        test('Should have non-empty success messages', () => {
            Object.values(SUCCESS_MESSAGES).forEach(message => {
                assert(typeof message === 'string');
                assert(message.length > 0);
            });
        });
    });

    suite('Configuration Consistency', () => {
        test('Default config should use defined file patterns', () => {
            // Check that default config uses patterns from FILE_PATTERNS
            const hasMarkdownPattern = DEFAULT_CONFIG.filePatterns.some(pattern =>
                FILE_PATTERNS.MARKDOWN.includes(pattern)
            );
            assert(hasMarkdownPattern, 'Default config should include markdown patterns');
        });

        test('Validation rules should be self-consistent', () => {
            // Title min should be less than max
            assert(VALIDATION_RULES.TITLE.MIN_LENGTH < VALIDATION_RULES.TITLE.MAX_LENGTH);

            // Tag limits should be reasonable
            assert(VALIDATION_RULES.TAG.MAX_COUNT > 0);
            assert(VALIDATION_RULES.TAG.MAX_LENGTH > 0);
        });

        test('UI config should have reasonable limits', () => {
            // Search settings should be reasonable
            assert(UI_CONFIG.SEARCH.MIN_QUERY_LENGTH >= 1);
            assert(UI_CONFIG.SEARCH.MAX_RESULTS > UI_CONFIG.PAGINATION.DEFAULT_PAGE_SIZE);

            // Debounce should not be too long
            assert(UI_CONFIG.SEARCH.DEBOUNCE_DELAY < 1000);
        });
    });
}); 