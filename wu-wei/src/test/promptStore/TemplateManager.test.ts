/**
 * Unit tests for TemplateManager
 * Testing wu wei principle: simple, flexible templates that flow naturally
 */

import assert from 'assert';
import * as vscode from 'vscode';
import { TemplateManager } from '../../promptStore/TemplateManager';
import { PromptTemplate } from '../../promptStore/types';

suite('TemplateManager Tests', () => {
    let templateManager: TemplateManager;

    setup(() => {
        templateManager = new TemplateManager();
    });

    teardown(() => {
        templateManager.dispose();
    });

    suite('Initialization', () => {
        test('Should create TemplateManager instance', () => {
            assert(templateManager instanceof TemplateManager);
        });

        test('Should have built-in templates', () => {
            const templates = templateManager.getTemplates();
            assert(Array.isArray(templates));
            assert(templates.length > 0);
        });

        test('Should have basic prompt template', () => {
            const template = templateManager.getTemplate('basic-prompt');
            assert(template);
            assert.strictEqual(template.id, 'basic-prompt');
            assert.strictEqual(template.name, 'Basic Prompt');
            assert(template.content.length > 0);
        });

        test('Should have expected built-in templates', () => {
            const templates = templateManager.getTemplates();
            const templateIds = templates.map(t => t.id);

            assert(templateIds.includes('basic-prompt'));
            assert(templateIds.includes('meeting-notes'));
            assert(templateIds.includes('code-review'));
            assert(templateIds.includes('documentation'));
            assert(templateIds.includes('analysis'));
        });
    });

    suite('Template Retrieval', () => {
        test('Should get template by ID', () => {
            const template = templateManager.getTemplate('meeting-notes');
            assert(template);
            assert.strictEqual(template.id, 'meeting-notes');
            assert.strictEqual(template.name, 'Meeting Notes');
            assert(template.content.includes('{{meeting_title}}'));
        });

        test('Should return undefined for non-existent template', () => {
            const template = templateManager.getTemplate('non-existent');
            assert.strictEqual(template, undefined);
        });

        test('Should get all templates', () => {
            const templates = templateManager.getTemplates();
            assert(Array.isArray(templates));
            assert(templates.length >= 5); // At least 5 built-in templates

            // Check template structure
            templates.forEach(template => {
                assert(typeof template.id === 'string');
                assert(typeof template.name === 'string');
                assert(typeof template.description === 'string');
                assert(typeof template.content === 'string');
                assert(typeof template.metadata === 'object');
            });
        });
    });

    suite('Template Loading', () => {
        test('Should load template content', async () => {
            const content = await templateManager.loadTemplate('basic-prompt');
            assert(typeof content === 'string');
            assert(content.length > 0);
            assert(content.includes('{{title}}'));
        });

        test('Should return empty string for non-existent template', async () => {
            const content = await templateManager.loadTemplate('non-existent');
            assert.strictEqual(content, '');
        });
    });

    suite('Template Rendering', () => {
        test('Should render template with parameters', async () => {
            const parameters = {
                title: 'Test Prompt',
                description: 'A test description'
            };

            const rendered = await templateManager.renderTemplate('basic-prompt', parameters);
            assert(rendered.includes('Test Prompt'));
            assert(!rendered.includes('{{title}}')); // Should be replaced
        });

        test('Should handle missing parameters gracefully', async () => {
            const parameters = { title: 'Test Prompt' };

            const rendered = await templateManager.renderTemplate('basic-prompt', parameters);
            assert(rendered.includes('Test Prompt'));
            // Missing parameters should remain as placeholders or be handled gracefully
        });

        test('Should render built-in variables', async () => {
            const rendered = await templateManager.renderTemplate('basic-prompt', {});

            // Check that built-in variables are replaced
            assert(!rendered.includes('{{current_date}}'));
            assert(!rendered.includes('{{current_time}}'));
            assert(!rendered.includes('{{current_datetime}}'));
        });

        test('Should handle complex template with multiple variables', async () => {
            const parameters = {
                meeting_title: 'Sprint Planning',
                date: '2023-12-01',
                duration: '60',
                attendees: 'Alice, Bob, Carol',
                agenda_item_1: 'Review last sprint',
                agenda_item_2: 'Plan next sprint',
                agenda_item_3: 'Assign tasks'
            };

            const rendered = await templateManager.renderTemplate('meeting-notes', parameters);

            assert(rendered.includes('Sprint Planning'));
            assert(rendered.includes('2023-12-01'));
            assert(rendered.includes('60 minutes'));
            assert(rendered.includes('Alice, Bob, Carol'));
            assert(rendered.includes('Review last sprint'));
        });

        test('Should throw error for non-existent template', async () => {
            try {
                await templateManager.renderTemplate('non-existent', {});
                assert.fail('Should have thrown error');
            } catch (error: any) {
                assert(error.message.includes('not found'));
            }
        });

        test('Should handle special characters in parameters', async () => {
            const parameters = {
                title: 'Test with "quotes" and <tags>',
                content: 'Content with & special chars'
            };

            const rendered = await templateManager.renderTemplate('basic-prompt', parameters);
            assert(rendered.includes('Test with "quotes" and <tags>'));
        });

        test('Should handle whitespace in template variables', async () => {
            // Create a template that might have whitespace around variables
            const testTemplate: PromptTemplate = {
                id: 'whitespace-test',
                name: 'Whitespace Test',
                description: 'Test whitespace handling',
                content: '{{ title }} and {{description}} and {{  spaced  }}',
                metadata: { category: 'test' }
            };

            // Add template temporarily
            const templates = templateManager.getTemplates();
            templates.push(testTemplate);

            const parameters = {
                title: 'Title',
                description: 'Description',
                spaced: 'Spaced'
            };

            try {
                const rendered = await templateManager.renderTemplate('whitespace-test', parameters);
                assert(rendered.includes('Title'));
                assert(rendered.includes('Description'));
                assert(rendered.includes('Spaced'));
            } finally {
                // Remove test template
                templates.pop();
            }
        });
    });

    suite('Built-in Variables', () => {
        test('Should replace current_date with current date', async () => {
            const testTemplate: PromptTemplate = {
                id: 'date-test',
                name: 'Date Test',
                description: 'Test date variable',
                content: 'Today is {{current_date}}',
                metadata: { category: 'test' }
            };

            const templates = templateManager.getTemplates();
            templates.push(testTemplate);

            try {
                const rendered = await templateManager.renderTemplate('date-test', {});
                const today = new Date().toISOString().split('T')[0];
                assert(rendered.includes(today));
            } finally {
                templates.pop();
            }
        });

        test('Should replace current_time with current time', async () => {
            const testTemplate: PromptTemplate = {
                id: 'time-test',
                name: 'Time Test',
                description: 'Test time variable',
                content: 'Current time: {{current_time}}',
                metadata: { category: 'test' }
            };

            const templates = templateManager.getTemplates();
            templates.push(testTemplate);

            try {
                const rendered = await templateManager.renderTemplate('time-test', {});
                assert(!rendered.includes('{{current_time}}'));
                assert(rendered.includes('Current time:'));
            } finally {
                templates.pop();
            }
        });

        test('Should replace current_datetime with ISO datetime', async () => {
            const testTemplate: PromptTemplate = {
                id: 'datetime-test',
                name: 'DateTime Test',
                description: 'Test datetime variable',
                content: 'Timestamp: {{current_datetime}}',
                metadata: { category: 'test' }
            };

            const templates = templateManager.getTemplates();
            templates.push(testTemplate);

            try {
                const rendered = await templateManager.renderTemplate('datetime-test', {});
                assert(!rendered.includes('{{current_datetime}}'));
                assert(rendered.includes('Timestamp:'));
                // Should contain ISO format (contains T and Z)
                assert(rendered.includes('T') && rendered.includes('Z'));
            } finally {
                templates.pop();
            }
        });
    });

    suite('Custom Templates', () => {
        test('Should create template from prompt', async () => {
            const promptContent = `---
title: Custom Template
category: custom
---

# {{title}}

Custom prompt content with {{parameter}}.`;

            const template = await templateManager.createTemplateFromPrompt(
                promptContent,
                'custom-test',
                'Custom Test Template',
                'A custom template for testing'
            );

            assert.strictEqual(template.id, 'custom-test');
            assert.strictEqual(template.name, 'Custom Test Template');
            assert.strictEqual(template.description, 'A custom template for testing');
            assert.strictEqual(template.content, promptContent);
            assert.strictEqual(template.metadata.category, 'custom');
            assert(template.metadata.tags?.includes('user-created'));
        });

        test('Should add custom template to available templates', async () => {
            await templateManager.createTemplateFromPrompt(
                '# {{title}}',
                'added-template',
                'Added Template',
                'Test adding template'
            );

            const templates = templateManager.getTemplates();
            const addedTemplate = templates.find(t => t.id === 'added-template');

            assert(addedTemplate);
            assert.strictEqual(addedTemplate.name, 'Added Template');
        });
    });

    suite('Template Metadata', () => {
        test('Should have proper metadata structure', () => {
            const templates = templateManager.getTemplates();

            templates.forEach(template => {
                assert(template.metadata);
                assert(typeof template.metadata.category === 'string');
                assert(Array.isArray(template.metadata.tags));
            });
        });

        test('Should categorize built-in templates correctly', () => {
            const basicPrompt = templateManager.getTemplate('basic-prompt');
            assert.strictEqual(basicPrompt?.metadata.category, 'general');

            const meetingNotes = templateManager.getTemplate('meeting-notes');
            assert.strictEqual(meetingNotes?.metadata.category, 'productivity');

            const codeReview = templateManager.getTemplate('code-review');
            assert.strictEqual(codeReview?.metadata.category, 'development');

            const documentation = templateManager.getTemplate('documentation');
            assert.strictEqual(documentation?.metadata.category, 'development');

            const analysis = templateManager.getTemplate('analysis');
            assert.strictEqual(analysis?.metadata.category, 'research');
        });

        test('Should have appropriate tags for templates', () => {
            const basicPrompt = templateManager.getTemplate('basic-prompt');
            assert(basicPrompt?.metadata.tags?.includes('basic'));
            assert(basicPrompt?.metadata.tags?.includes('template'));

            const codeReview = templateManager.getTemplate('code-review');
            assert(codeReview?.metadata.tags?.includes('code-review'));
            assert(codeReview?.metadata.tags?.includes('development'));
        });
    });

    suite('Template Content Validation', () => {
        test('Should have proper content structure in built-in templates', () => {
            const templates = templateManager.getTemplates();

            templates.forEach(template => {
                assert(template.content.length > 0);

                // Basic templates should have title placeholder
                if (template.id === 'basic-prompt') {
                    assert(template.content.includes('{{title}}'));
                }

                // Meeting notes should have meeting-specific placeholders
                if (template.id === 'meeting-notes') {
                    assert(template.content.includes('{{meeting_title}}'));
                    assert(template.content.includes('{{attendees}}'));
                    assert(template.content.includes('{{date}}'));
                }

                // Code review should have code-specific placeholders
                if (template.id === 'code-review') {
                    assert(template.content.includes('{{component_name}}'));
                    assert(template.content.includes('{{language}}'));
                    assert(template.content.includes('{{code_snippet}}'));
                }
            });
        });

        test('Should have markdown structure in templates', () => {
            const templates = templateManager.getTemplates();

            templates.forEach(template => {
                // Should have at least one markdown header
                assert(/^#+ /.test(template.content) || template.content.includes('\n# '));
            });
        });
    });

    suite('Error Handling', () => {
        test('Should handle template rendering with undefined parameters', async () => {
            const parameters = {
                title: undefined,
                description: null
            } as any;

            const rendered = await templateManager.renderTemplate('basic-prompt', parameters);
            assert(typeof rendered === 'string');
            // Should handle undefined/null values gracefully
        });

        test('Should handle empty template content', async () => {
            const emptyTemplate: PromptTemplate = {
                id: 'empty-test',
                name: 'Empty Template',
                description: 'Empty content test',
                content: '',
                metadata: { category: 'test' }
            };

            const templates = templateManager.getTemplates();
            templates.push(emptyTemplate);

            try {
                const rendered = await templateManager.renderTemplate('empty-test', { title: 'Test' });
                assert.strictEqual(rendered, '');
            } finally {
                templates.pop();
            }
        });

        test('Should handle template with no variables', async () => {
            const staticTemplate: PromptTemplate = {
                id: 'static-test',
                name: 'Static Template',
                description: 'No variables test',
                content: '# Static Content\n\nThis has no variables.',
                metadata: { category: 'test' }
            };

            const templates = templateManager.getTemplates();
            templates.push(staticTemplate);

            try {
                const rendered = await templateManager.renderTemplate('static-test', {});
                assert.strictEqual(rendered, '# Static Content\n\nThis has no variables.');
            } finally {
                templates.pop();
            }
        });
    });
}); 