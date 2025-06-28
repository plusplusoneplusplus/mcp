/**
 * Test suite for PromptManagerServiceAdapter
 * Validates Phase 2 refactoring - backward compatibility and PromptService interface implementation
 */

import assert from 'assert';
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs/promises';
import { PromptManager } from '../../../promptStore/PromptManager';
import { PromptManagerServiceAdapter } from '../../../promptStore/PromptManagerServiceAdapter';
import { PromptService } from '../../../shared/promptManager/types';

suite('PromptManagerServiceAdapter Tests', () => {
    let tempDir: string;
    let promptManager: PromptManager;
    let serviceAdapter: PromptManagerServiceAdapter;
    let promptService: PromptService;

    suiteSetup(async () => {
        // Create temporary directory for test files
        tempDir = path.join(__dirname, '..', '..', '..', 'test-prompts-adapter');
        try {
            await fs.mkdir(tempDir, { recursive: true });
        } catch (error) {
            // Directory might already exist
        }
    });

    setup(async () => {
        // Clean the temp directory
        try {
            const files = await fs.readdir(tempDir);
            await Promise.all(files.map(file => fs.unlink(path.join(tempDir, file))));
        } catch (error) {
            // Directory might be empty
        }

        // Create PromptManager with test configuration
        promptManager = new PromptManager({
            watchPaths: [tempDir],
            autoRefresh: false,
            excludePatterns: ['node_modules/**', '.git/**']
        });

        // Create service adapter
        serviceAdapter = new PromptManagerServiceAdapter(promptManager);
        promptService = serviceAdapter; // Test through interface

        // Initialize the service
        await serviceAdapter.initialize();
    });

    teardown(async () => {
        if (serviceAdapter) {
            serviceAdapter.dispose();
        }
    });

    suiteTeardown(async () => {
        // Clean up temp directory
        try {
            await fs.rmdir(tempDir, { recursive: true });
        } catch (error) {
            // Ignore cleanup errors
        }
    });

    suite('PromptService Interface Compliance', () => {
        test('Should implement PromptService interface', () => {
            assert(serviceAdapter instanceof PromptManagerServiceAdapter);
            // Test that it has all required methods
            assert(typeof serviceAdapter.getAllPrompts === 'function');
            assert(typeof serviceAdapter.getPrompt === 'function');
            assert(typeof serviceAdapter.searchPrompts === 'function');
            assert(typeof serviceAdapter.selectPromptForUse === 'function');
            assert(typeof serviceAdapter.renderPromptWithVariables === 'function');
            assert(typeof serviceAdapter.getConfig === 'function');
            assert(typeof serviceAdapter.updateConfig === 'function');
            assert(typeof serviceAdapter.initialize === 'function');
            assert(typeof serviceAdapter.dispose === 'function');
        });

        test('Should have required events', () => {
            assert(serviceAdapter.onPromptsChanged);
            assert(serviceAdapter.onPromptSelected);
            assert(serviceAdapter.onConfigChanged);
        });

        test('Should return async results', async () => {
            const prompts = await promptService.getAllPrompts();
            assert(Array.isArray(prompts));

            const config = await promptService.getConfig();
            assert(typeof config === 'object');
        });
    });

    suite('Backward Compatibility', () => {
        test('Should work with existing PromptManager API', async () => {
            // Create test prompt
            const testPromptContent = `---
title: Test Prompt
description: A test prompt for adapter validation
category: testing
tags: [test, adapter]
---

# Test Prompt

This is a test prompt with a variable: {{testVariable}}`;

            const promptPath = path.join(tempDir, 'test-prompt.md');
            await fs.writeFile(promptPath, testPromptContent, 'utf8');

            // Refresh through the underlying manager
            await promptManager.refreshPrompts();

            // Test through both interfaces
            const managerPrompts = promptManager.getAllPrompts();
            const servicePrompts = await serviceAdapter.getAllPrompts();

            assert.strictEqual(managerPrompts.length, servicePrompts.length);
            assert.strictEqual(managerPrompts[0].metadata.title, servicePrompts[0].metadata.title);
        });

        test('Should maintain event compatibility', (done) => {
            let eventReceived = false;

            // Listen to events through adapter
            serviceAdapter.onPromptsChanged(() => {
                eventReceived = true;
                assert(eventReceived, 'Should receive prompts changed event');
                done();
            });

            // Trigger event through manager
            promptManager.refreshPrompts();
        });
    });

    suite('Enhanced Functionality', () => {
        test('Should provide enhanced prompt selection', async () => {
            // Create test prompt with variables
            const testPromptContent = `---
title: Enhanced Prompt
description: A prompt with variables
category: testing
tags: [enhanced]
---

# Enhanced Prompt

Hello {{name}}, welcome to {{place}}!`;

            const promptPath = path.join(tempDir, 'enhanced-prompt.md');
            await fs.writeFile(promptPath, testPromptContent, 'utf8');
            await promptManager.refreshPrompts();

            const prompts = await serviceAdapter.getAllPrompts();
            const prompt = prompts[0];

            // Test enhanced selection
            const usageContext = await serviceAdapter.selectPromptForUse(prompt.id);

            assert(usageContext.prompt);
            assert(usageContext.metadata);
            assert(usageContext.metadata.parameters);
            assert(usageContext.metadata.usageInstructions);
            assert.strictEqual(usageContext.metadata.parameters.length, 2);
            assert(usageContext.metadata.parameters.some(p => p.name === 'name'));
            assert(usageContext.metadata.parameters.some(p => p.name === 'place'));
        });

        test('Should render prompts with variables', async () => {
            // Create test prompt with variables
            const testPromptContent = `---
title: Variable Prompt
---

# Hello {{name}}

Your score is {{score}}.`;

            const promptPath = path.join(tempDir, 'variable-prompt.md');
            await fs.writeFile(promptPath, testPromptContent, 'utf8');
            await promptManager.refreshPrompts();

            const prompts = await serviceAdapter.getAllPrompts();
            const prompt = prompts[0];

            // Test variable rendering
            const rendered = await serviceAdapter.renderPromptWithVariables(prompt.id, {
                name: 'Alice',
                score: 95
            });

            assert(rendered.includes('Hello Alice'));
            assert(rendered.includes('Your score is 95'));
        });

        test('Should validate variables', async () => {
            // Create test prompt
            const testPromptContent = `---
title: Validation Prompt
---

# Hello {{name}}`;

            const promptPath = path.join(tempDir, 'validation-prompt.md');
            await fs.writeFile(promptPath, testPromptContent, 'utf8');
            await promptManager.refreshPrompts();

            const prompts = await serviceAdapter.getAllPrompts();
            const prompt = prompts[0];

            // Test with missing variable - should throw error
            try {
                await serviceAdapter.renderPromptWithVariables(prompt.id, {});
                assert.fail('Should have thrown validation error');
            } catch (error) {
                assert(error instanceof Error);
                assert(error.message.includes('validation failed'));
            }
        });

        test('Should extract prompt variables', async () => {
            // Create test prompt with multiple variables
            const testPromptContent = `---
title: Multi Variable Prompt
---

# {{title}}: {{description}}

Author: {{author}}
Date: {{date}}`;

            const promptPath = path.join(tempDir, 'multi-var-prompt.md');
            await fs.writeFile(promptPath, testPromptContent, 'utf8');
            await promptManager.refreshPrompts();

            const prompts = await serviceAdapter.getAllPrompts();
            const prompt = prompts[0];

            const variables = await serviceAdapter.getPromptVariables(prompt.id);

            assert.strictEqual(variables.length, 4);
            assert(variables.includes('title'));
            assert(variables.includes('description'));
            assert(variables.includes('author'));
            assert(variables.includes('date'));
        });

        test('Should provide prompt preview', async () => {
            // Create test prompt
            const testPromptContent = `---
title: Preview Prompt
---

# Hello {{name}}

Your age is {{age}}.`;

            const promptPath = path.join(tempDir, 'preview-prompt.md');
            await fs.writeFile(promptPath, testPromptContent, 'utf8');
            await promptManager.refreshPrompts();

            const prompts = await serviceAdapter.getAllPrompts();
            const prompt = prompts[0];

            // Test preview with partial variables
            const preview = await serviceAdapter.previewPromptRender(prompt.id, {
                name: 'Bob'
            });

            assert(preview.preview.includes('Hello Bob'));
            assert(preview.preview.includes('[age]')); // Missing variable placeholder
            assert.strictEqual(preview.missingVariables.length, 1);
            assert(preview.missingVariables.includes('age'));
        });
    });

    suite('Configuration Management', () => {
        test('Should handle async configuration updates', async () => {
            const originalConfig = await serviceAdapter.getConfig();

            await serviceAdapter.updateConfig({
                autoRefresh: !originalConfig.autoRefresh
            });

            const updatedConfig = await serviceAdapter.getConfig();
            assert.strictEqual(updatedConfig.autoRefresh, !originalConfig.autoRefresh);
        });

        test('Should fire config change events', (done) => {
            serviceAdapter.onConfigChanged((config) => {
                assert(config);
                assert(typeof config.autoRefresh === 'boolean');
                done();
            });

            serviceAdapter.updateConfig({ autoRefresh: true });
        });
    });

    suite('Error Handling', () => {
        test('Should handle non-existent prompt gracefully', async () => {
            try {
                await serviceAdapter.getPrompt('non-existent-id');
                // Should return null, not throw
            } catch (error) {
                assert.fail('Should not throw for non-existent prompt');
            }

            const result = await serviceAdapter.getPrompt('non-existent-id');
            assert.strictEqual(result, null);
        });

        test('Should throw for invalid prompt operations', async () => {
            try {
                await serviceAdapter.selectPromptForUse('non-existent-id');
                assert.fail('Should throw for non-existent prompt');
            } catch (error) {
                assert(error instanceof Error);
                assert(error.message.includes('not found'));
            }
        });
    });
}); 