import * as assert from 'assert';
import * as vscode from 'vscode';
import { WuWeiChatParticipant } from '../../chat/WuWeiChatParticipant';

suite('Wu Wei Chat Participant Integration Tests', () => {
    let participant: WuWeiChatParticipant;
    let mockContext: vscode.ExtensionContext;
    let originalGetConfiguration: any;

    setup(() => {
        // Mock vscode.workspace.getConfiguration
        originalGetConfiguration = vscode.workspace.getConfiguration;
        vscode.workspace.getConfiguration = (section?: string) => {
            return {
                get: (key: string, defaultValue?: any) => {
                    if (section === 'wu-wei') {
                        switch (key) {
                            case 'enhancedToolCalling':
                                return true; // Default to enabled for most tests
                            case 'debugMode':
                                return false;
                            case 'maxToolRounds':
                                return 5;
                            case 'enableToolCaching':
                                return true;
                            case 'enableParallelToolExecution':
                                return true;
                            default:
                                return defaultValue;
                        }
                    }
                    return defaultValue;
                },
                has: () => true,
                inspect: () => undefined,
                update: async () => { }
            } as any;
        };

        mockContext = {
            subscriptions: [],
            extensionPath: '/test/path',
            extensionUri: vscode.Uri.file('/test/path'),
            globalState: {
                get: () => undefined,
                update: async () => { },
                keys: () => []
            },
            workspaceState: {
                get: () => undefined,
                update: async () => { },
                keys: () => []
            },
            secrets: {
                get: async () => undefined,
                store: async () => { },
                delete: async () => { },
                onDidChange: () => ({ dispose: () => { } })
            },
            storageUri: vscode.Uri.file('/test/storage'),
            globalStorageUri: vscode.Uri.file('/test/global'),
            logUri: vscode.Uri.file('/test/logs'),
            extensionMode: vscode.ExtensionMode.Test,
            asAbsolutePath: (path: string) => `/test/path/${path}`,
            environmentVariableCollection: {
                persistent: true,
                description: '',
                replace: () => { },
                append: () => { },
                prepend: () => { },
                get: () => undefined,
                forEach: () => { },
                delete: () => { },
                clear: () => { },
                [Symbol.iterator]: function* () { }
            }
        } as unknown as vscode.ExtensionContext;

        participant = new WuWeiChatParticipant(mockContext);
    });

    teardown(() => {
        participant.dispose();
        // Restore original getConfiguration
        if (originalGetConfiguration) {
            vscode.workspace.getConfiguration = originalGetConfiguration;
        }
    });

    suite('Initialization', () => {
        test('should initialize successfully', () => {
            assert.ok(participant);
        });

        test('should expose enhanced mode management methods', () => {
            assert.ok(typeof participant.toggleEnhancedMode === 'function');
            assert.ok(typeof participant.getEnhancedModeStats === 'function');
            assert.ok(typeof participant.clearEnhancedCache === 'function');
            assert.ok(typeof participant.updateEnhancedConfig === 'function');
        });
    });

    suite('Enhanced Mode Management', () => {
        test('should toggle enhanced mode', () => {
            // Test enabling enhanced mode
            participant.toggleEnhancedMode(true);

            const stats = participant.getEnhancedModeStats();
            assert.strictEqual(stats.enabled, true);
            assert.ok(stats.config);
            assert.ok(stats.cacheStats);

            // Test disabling enhanced mode
            participant.toggleEnhancedMode(false);

            const statsDisabled = participant.getEnhancedModeStats();
            assert.strictEqual(statsDisabled.enabled, false);
        });

        test('should provide enhanced mode statistics', () => {
            participant.toggleEnhancedMode(true);

            const stats = participant.getEnhancedModeStats();

            assert.ok(typeof stats.enabled === 'boolean');
            assert.ok(stats.cacheStats);
            assert.ok(typeof stats.cacheStats.size === 'number');
            assert.ok(typeof stats.cacheStats.hitRate === 'number');
            assert.ok(stats.config);
            assert.ok(typeof stats.config.maxToolRounds === 'number');
        });

        test('should clear enhanced cache', () => {
            participant.toggleEnhancedMode(true);

            // Clear cache
            participant.clearEnhancedCache();

            const stats = participant.getEnhancedModeStats();
            assert.strictEqual(stats.cacheStats.size, 0);
        });

        test('should update enhanced configuration', () => {
            participant.toggleEnhancedMode(true);

            const newConfig = {
                maxToolRounds: 10,
                debugMode: true,
                toolTimeout: 20000
            };

            participant.updateEnhancedConfig(newConfig);

            const stats = participant.getEnhancedModeStats();
            assert.strictEqual(stats.config.maxToolRounds, 10);
            assert.strictEqual(stats.config.debugMode, true);
            assert.strictEqual(stats.config.toolTimeout, 20000);
        });
    });

    suite('Enhanced Mode Status', () => {
        test('should handle enhanced mode disabled state', () => {
            participant.toggleEnhancedMode(false);

            const stats = participant.getEnhancedModeStats();
            assert.strictEqual(stats.enabled, false);
            assert.strictEqual(stats.cacheStats, null);
            assert.strictEqual(stats.config, null);
        });

        test('should handle enhanced mode disabled from initialization', () => {
            // Create a new participant with disabled enhanced mode
            const originalGetConfiguration = vscode.workspace.getConfiguration;
            vscode.workspace.getConfiguration = (section?: string) => {
                return {
                    get: (key: string, defaultValue?: any) => {
                        if (section === 'wu-wei' && key === 'enhancedToolCalling') {
                            return false; // Disabled from start
                        }
                        return defaultValue;
                    },
                    has: () => true,
                    inspect: () => undefined,
                    update: async () => { }
                } as any;
            };

            const disabledParticipant = new WuWeiChatParticipant(mockContext);

            const stats = disabledParticipant.getEnhancedModeStats();
            assert.strictEqual(stats.enabled, false);
            assert.strictEqual(stats.cacheStats, null);
            assert.strictEqual(stats.config, null);

            disabledParticipant.dispose();

            // Restore original configuration
            vscode.workspace.getConfiguration = originalGetConfiguration;
        });

        test('should gracefully handle operations when enhanced mode is disabled', () => {
            participant.toggleEnhancedMode(false);

            // These should not throw errors
            assert.doesNotThrow(() => {
                participant.clearEnhancedCache();
                participant.updateEnhancedConfig({ maxToolRounds: 5 });
                participant.getEnhancedModeStats();
            });
        });
    });

    suite('Configuration Integration', () => {
        test('should respect workspace configuration for enhanced mode', () => {
            // This would typically read from vscode.workspace.getConfiguration
            // In a real test environment, we would mock this

            // Test that initialization respects configuration
            const newParticipant = new WuWeiChatParticipant(mockContext);

            // Should initialize with default enhanced mode settings
            const stats = newParticipant.getEnhancedModeStats();
            assert.ok(typeof stats.enabled === 'boolean');

            newParticipant.dispose();
        });

        test('should initialize enhanced participant with workspace settings', () => {
            participant.toggleEnhancedMode(true);

            const stats = participant.getEnhancedModeStats();

            // Should have valid configuration
            assert.ok(stats.config);
            assert.ok(typeof stats.config.maxToolRounds === 'number');
            assert.ok(typeof stats.config.enableCaching === 'boolean');
            assert.ok(typeof stats.config.enableParallelExecution === 'boolean');
        });
    });

    suite('Disposal and Cleanup', () => {
        test('should dispose cleanly', () => {
            participant.toggleEnhancedMode(true);

            // Should not throw when disposing
            assert.doesNotThrow(() => {
                participant.dispose();
            });
        });

        test('should handle multiple dispose calls', () => {
            // Should not throw when called multiple times
            assert.doesNotThrow(() => {
                participant.dispose();
                participant.dispose();
            });
        });
    });

    suite('Error Handling', () => {
        test('should handle invalid enhanced configuration gracefully', () => {
            participant.toggleEnhancedMode(true);

            // Test with invalid config
            const invalidConfig = {
                maxToolRounds: -1,  // Invalid
                debugMode: 'invalid' as any,  // Invalid type
                nonExistentProperty: 'value'
            };

            assert.doesNotThrow(() => {
                participant.updateEnhancedConfig(invalidConfig);
            });
        });

        test('should handle enhanced mode operations with uninitialized participant', () => {
            // Mock configuration to return disabled enhanced mode
            const originalGetConfiguration = vscode.workspace.getConfiguration;
            vscode.workspace.getConfiguration = (section?: string) => {
                return {
                    get: (key: string, defaultValue?: any) => {
                        if (section === 'wu-wei' && key === 'enhancedToolCalling') {
                            return false; // Start disabled
                        }
                        return defaultValue;
                    },
                    has: () => true,
                    inspect: () => undefined,
                    update: async () => { }
                } as any;
            };

            // Create participant with disabled enhanced mode from start
            const uninitializedParticipant = new WuWeiChatParticipant(mockContext);

            assert.doesNotThrow(() => {
                const stats = uninitializedParticipant.getEnhancedModeStats();
                assert.strictEqual(stats.enabled, false);
                assert.strictEqual(stats.cacheStats, null);
                assert.strictEqual(stats.config, null);
                uninitializedParticipant.clearEnhancedCache();
                uninitializedParticipant.updateEnhancedConfig({});
            });

            uninitializedParticipant.dispose();

            // Restore original configuration
            vscode.workspace.getConfiguration = originalGetConfiguration;
        });
    });

    suite('Performance and Resource Management', () => {
        test('should manage resources efficiently in enhanced mode', () => {
            participant.toggleEnhancedMode(true);

            // Get initial stats
            const initialStats = participant.getEnhancedModeStats();

            // Perform some operations
            participant.clearEnhancedCache();
            participant.updateEnhancedConfig({ maxToolRounds: 3 });

            // Check that operations complete without throwing
            const finalStats = participant.getEnhancedModeStats();
            assert.ok(finalStats.enabled);
            assert.strictEqual(finalStats.config.maxToolRounds, 3);
        });

        test('should handle rapid mode switching', () => {
            // Rapid toggle shouldn't cause issues
            for (let i = 0; i < 10; i++) {
                participant.toggleEnhancedMode(i % 2 === 0);
            }

            const finalStats = participant.getEnhancedModeStats();
            assert.strictEqual(finalStats.enabled, false); // Should end up disabled
        });
    });

    suite('Backward Compatibility', () => {
        test('should maintain standard mode functionality', () => {
            participant.toggleEnhancedMode(false);

            // Standard mode operations should still work
            const stats = participant.getEnhancedModeStats();
            assert.strictEqual(stats.enabled, false);

            // Should not have enhanced features but shouldn't throw
            assert.doesNotThrow(() => {
                participant.clearEnhancedCache();
                participant.updateEnhancedConfig({});
            });
        });

        test('should support legacy configurations', () => {
            // Test that the participant works with default settings
            const legacyParticipant = new WuWeiChatParticipant(mockContext);

            // Should initialize successfully
            assert.ok(legacyParticipant);

            // Should have some default enhanced mode state
            const stats = legacyParticipant.getEnhancedModeStats();
            assert.ok(typeof stats.enabled === 'boolean');

            legacyParticipant.dispose();
        });
    });
});
