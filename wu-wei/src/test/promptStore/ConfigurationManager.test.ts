/**
 * Unit tests for ConfigurationManager
 * Testing wu wei principle: thorough validation with minimal friction
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import * as fs from 'fs/promises';
import * as path from 'path';
import { ConfigurationManager, PromptStoreConfig, ValidationResult } from '../../promptStore/ConfigurationManager';

suite('ConfigurationManager Tests', () => {
    let configManager: ConfigurationManager;
    let mockContext: vscode.ExtensionContext;

    setup(() => {
        // Create a minimal mock context for testing
        mockContext = {
            subscriptions: [],
            workspaceState: {
                get: () => undefined,
                update: async () => { }
            },
            globalState: {
                get: () => undefined,
                update: async () => { }
            }
        } as any;

        // Note: Full mocking would require sinon or similar library
        // For now, we'll test what we can with the actual implementation
        configManager = new ConfigurationManager(mockContext);
    });

    teardown(() => {
        configManager.dispose();
    });

    suite('Configuration Loading', () => {
        test('Should create ConfigurationManager instance', () => {
            assert(configManager instanceof ConfigurationManager);
        });

        test('Should have getConfig method', () => {
            assert.strictEqual(typeof configManager.getConfig, 'function');
        });

        test('Should return configuration object with expected properties', () => {
            const config = configManager.getConfig();

            assert(typeof config === 'object');
            assert(typeof config.autoRefresh === 'boolean');
            assert(typeof config.showMetadataTooltips === 'boolean');
            assert(typeof config.enableTemplates === 'boolean');
            assert(typeof config.fileWatcher === 'object');
            assert(typeof config.metadataSchema === 'object');
        });
    });

    suite('Configuration Validation', () => {
        test('Should validate configuration structure', async () => {
            const validConfig: PromptStoreConfig = {
                rootDirectory: '',
                autoRefresh: true,
                showMetadataTooltips: true,
                enableTemplates: true,
                metadataSchema: {
                    requireTitle: true,
                    requireDescription: false,
                    allowCustomFields: true,
                    validateParameters: true
                },
                fileWatcher: {
                    enabled: true,
                    debounceMs: 500,
                    maxDepth: 10,
                    ignorePatterns: ['*.tmp'],
                    usePolling: false,
                    pollingInterval: 1000
                }
            };

            const result = await configManager.validateConfig(validConfig);

            assert(typeof result === 'object');
            assert(typeof result.isValid === 'boolean');
            assert(Array.isArray(result.errors));
            assert(Array.isArray(result.warnings));
        });

        test('Should detect invalid debounce values', async () => {
            const invalidConfig: PromptStoreConfig = {
                rootDirectory: '',
                autoRefresh: true,
                showMetadataTooltips: true,
                enableTemplates: true,
                metadataSchema: {
                    requireTitle: true,
                    requireDescription: false,
                    allowCustomFields: true,
                    validateParameters: true
                },
                fileWatcher: {
                    enabled: true,
                    debounceMs: 50, // Invalid - too low
                    maxDepth: 10,
                    ignorePatterns: [],
                    usePolling: false,
                    pollingInterval: 1000
                }
            };

            const result = await configManager.validateConfig(invalidConfig);

            assert.strictEqual(result.isValid, false);
            assert(result.errors.length > 0);
            assert(result.errors.some(error => error.includes('debounce')));
        });

        test('Should detect invalid max depth values', async () => {
            const invalidConfig: PromptStoreConfig = {
                rootDirectory: '',
                autoRefresh: true,
                showMetadataTooltips: true,
                enableTemplates: true,
                metadataSchema: {
                    requireTitle: true,
                    requireDescription: false,
                    allowCustomFields: true,
                    validateParameters: true
                },
                fileWatcher: {
                    enabled: true,
                    debounceMs: 500,
                    maxDepth: 100, // Invalid - too high
                    ignorePatterns: [],
                    usePolling: false,
                    pollingInterval: 1000
                }
            };

            const result = await configManager.validateConfig(invalidConfig);

            assert.strictEqual(result.isValid, false);
            assert(result.errors.some(error => error.includes('max depth')));
        });

        test('Should detect invalid polling interval', async () => {
            const invalidConfig: PromptStoreConfig = {
                rootDirectory: '',
                autoRefresh: true,
                showMetadataTooltips: true,
                enableTemplates: true,
                metadataSchema: {
                    requireTitle: true,
                    requireDescription: false,
                    allowCustomFields: true,
                    validateParameters: true
                },
                fileWatcher: {
                    enabled: true,
                    debounceMs: 500,
                    maxDepth: 10,
                    ignorePatterns: [],
                    usePolling: true,
                    pollingInterval: 50000 // Invalid - too high
                }
            };

            const result = await configManager.validateConfig(invalidConfig);

            assert.strictEqual(result.isValid, false);
            assert(result.errors.some(error => error.includes('interval')));
        });

        test('Should warn about missing root directory', async () => {
            const result = await configManager.validateConfig();

            assert(result.warnings.some(warning => warning.includes('No root directory')));
        });
    });

    suite('API Methods', () => {
        test('Should have updateConfig method', () => {
            assert.strictEqual(typeof configManager.updateConfig, 'function');
        });

        test('Should have resetToDefaults method', () => {
            assert.strictEqual(typeof configManager.resetToDefaults, 'function');
        });

        test('Should have selectDirectory method', () => {
            assert.strictEqual(typeof configManager.selectDirectory, 'function');
        });

        test('Should have setRootDirectory method', () => {
            assert.strictEqual(typeof configManager.setRootDirectory, 'function');
        });

        test('Should have onConfigurationChanged event', () => {
            assert.strictEqual(typeof configManager.onConfigurationChanged, 'object');
            // Test that it's a VS Code Event by checking it has the right structure
            assert.strictEqual(typeof configManager.onConfigurationChanged, 'function');
        });
    });

    suite('Disposal', () => {
        test('Should dispose without errors', () => {
            const manager = new ConfigurationManager(mockContext);

            // Should not throw
            assert.doesNotThrow(() => {
                manager.dispose();
            });
        });
    });
});
