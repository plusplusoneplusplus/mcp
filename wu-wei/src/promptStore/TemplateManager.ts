/**
 * Template Manager - Handles prompt templates and template processing
 * Following wu wei principles: simple, flexible templates that flow naturally
 */

import * as vscode from 'vscode';
import * as fs from 'fs/promises';
import * as path from 'path';
import { PromptTemplate, PromptMetadata } from './types';
import { WuWeiLogger } from '../logger';

export class TemplateManager {
    private logger: WuWeiLogger;
    private builtInTemplates: PromptTemplate[];

    constructor() {
        this.logger = WuWeiLogger.getInstance();
        this.builtInTemplates = this.initializeBuiltInTemplates();
    }

    /**
     * Get all available templates
     */
    getTemplates(): PromptTemplate[] {
        return this.builtInTemplates;
    }

    /**
     * Get a specific template by ID
     */
    getTemplate(id: string): PromptTemplate | undefined {
        return this.builtInTemplates.find(t => t.id === id);
    }

    /**
     * Load template content by ID
     */
    async loadTemplate(id: string): Promise<string> {
        const template = this.getTemplate(id);
        return template ? template.content : '';
    }

    /**
     * Render template with parameters
     */
    async renderTemplate(templateId: string, parameters: Record<string, any>): Promise<string> {
        const template = this.getTemplate(templateId);
        if (!template) {
            throw new Error(`Template '${templateId}' not found`);
        }

        let content = template.content;

        // Replace template variables
        for (const [key, value] of Object.entries(parameters)) {
            const regex = new RegExp(`{{\\s*${key}\\s*}}`, 'g');
            content = content.replace(regex, String(value));
        }

        // Replace built-in variables
        content = content.replace(/{{current_date}}/g, new Date().toISOString().split('T')[0]);
        content = content.replace(/{{current_time}}/g, new Date().toLocaleTimeString());
        content = content.replace(/{{current_datetime}}/g, new Date().toISOString());

        return content;
    }

    /**
     * Create a custom template from existing prompt
     */
    async createTemplateFromPrompt(promptContent: string, templateId: string, name: string, description: string): Promise<PromptTemplate> {
        const template: PromptTemplate = {
            id: templateId,
            name,
            description,
            content: promptContent,
            metadata: {
                category: 'custom',
                tags: ['user-created', 'template']
            }
        };

        // Add to built-in templates (in real implementation, save to user settings)
        this.builtInTemplates.push(template);

        this.logger.info(`Created custom template: ${templateId}`);
        return template;
    }

    /**
     * Save custom template to user settings
     */
    async saveCustomTemplate(template: PromptTemplate): Promise<void> {
        try {
            const config = vscode.workspace.getConfiguration('wu-wei.promptStore');
            const customTemplates = config.get<PromptTemplate[]>('customTemplates', []);

            // Remove existing template with same ID
            const filtered = customTemplates.filter(t => t.id !== template.id);
            filtered.push(template);

            await config.update('customTemplates', filtered, vscode.ConfigurationTarget.Global);
            this.logger.info(`Saved custom template: ${template.id}`);
        } catch (error: any) {
            this.logger.error('Failed to save custom template:', error);
            throw error;
        }
    }

    /**
     * Load custom templates from user settings
     */
    async loadCustomTemplates(): Promise<void> {
        try {
            const config = vscode.workspace.getConfiguration('wu-wei.promptStore');
            const customTemplates = config.get<PromptTemplate[]>('customTemplates', []);

            // Add custom templates to built-in templates
            for (const template of customTemplates) {
                const existingIndex = this.builtInTemplates.findIndex(t => t.id === template.id);
                if (existingIndex >= 0) {
                    this.builtInTemplates[existingIndex] = template;
                } else {
                    this.builtInTemplates.push(template);
                }
            }

            this.logger.info(`Loaded ${customTemplates.length} custom templates`);
        } catch (error: any) {
            this.logger.error('Failed to load custom templates:', error);
        }
    }

    /**
     * Delete a custom template
     */
    async deleteCustomTemplate(templateId: string): Promise<void> {
        try {
            const config = vscode.workspace.getConfiguration('wu-wei.promptStore');
            const customTemplates = config.get<PromptTemplate[]>('customTemplates', []);

            const filtered = customTemplates.filter(t => t.id !== templateId);
            await config.update('customTemplates', filtered, vscode.ConfigurationTarget.Global);

            // Remove from built-in templates array
            const builtInIndex = this.builtInTemplates.findIndex(t => t.id === templateId);
            if (builtInIndex >= 0) {
                this.builtInTemplates.splice(builtInIndex, 1);
            }

            this.logger.info(`Deleted custom template: ${templateId}`);
        } catch (error: any) {
            this.logger.error('Failed to delete custom template:', error);
            throw error;
        }
    }

    private initializeBuiltInTemplates(): PromptTemplate[] {
        return [
            {
                id: 'basic-prompt',
                name: 'Basic Prompt',
                description: 'A simple prompt template with basic structure',
                content: `# {{title}}

Your prompt content goes here...

## Context
Provide context for your prompt.

## Instructions
Clear instructions for what you want the AI to do.

## Expected Output
Describe the format or type of output you expect.
`,
                metadata: {
                    category: 'general',
                    tags: ['basic', 'template', 'general-purpose']
                }
            },
            {
                id: 'meeting-notes',
                name: 'Meeting Notes',
                description: 'Template for structured meeting documentation',
                content: `# Meeting Notes: {{meeting_title}}

**Date:** {{date}}
**Duration:** {{duration}} minutes
**Attendees:** {{attendees}}

## Agenda
1. {{agenda_item_1}}
2. {{agenda_item_2}}
3. {{agenda_item_3}}

## Discussion Points
{{discussion_points}}

## Action Items
- [ ] {{action_item_1}}
- [ ] {{action_item_2}}
- [ ] {{action_item_3}}

## Next Steps
{{next_steps}}

## Notes
{{additional_notes}}
`,
                metadata: {
                    category: 'productivity',
                    tags: ['meeting', 'documentation', 'template', 'business']
                }
            },
            {
                id: 'code-review',
                name: 'Code Review',
                description: 'Template for AI-assisted code review prompts',
                content: `# Code Review: {{component_name}}

## Context
{{context_description}}

## Code to Review
\`\`\`{{language}}
{{code_snippet}}
\`\`\`

## Review Criteria
- **Functionality**: Does the code work as intended?
- **Performance**: Are there any performance concerns?
- **Security**: Are there any security vulnerabilities?
- **Maintainability**: Is the code easy to understand and maintain?
- **Best Practices**: Does the code follow language/framework best practices?

## Specific Areas of Focus
{{focus_areas}}

## Questions
{{specific_questions}}
`,
                metadata: {
                    category: 'development',
                    tags: ['code-review', 'development', 'quality-assurance']
                }
            },
            {
                id: 'documentation',
                name: 'Documentation Generator',
                description: 'Template for generating documentation from code',
                content: `# {{title}} Documentation

## Overview
{{overview}}

## Purpose
{{purpose}}

## Usage
\`\`\`{{language}}
{{usage_example}}
\`\`\`

## Parameters
{{parameters_description}}

## Return Value
{{return_value_description}}

## Examples
{{examples}}

## Notes
{{additional_notes}}

## See Also
{{related_documentation}}
`,
                metadata: {
                    category: 'development',
                    tags: ['documentation', 'code', 'reference']
                }
            },
            {
                id: 'analysis',
                name: 'Analysis & Research',
                description: 'Template for analytical and research prompts',
                content: `# Analysis: {{topic}}

## Objective
{{objective}}

## Background
{{background_information}}

## Data Sources
{{data_sources}}

## Analysis Framework
{{analysis_framework}}

## Key Questions
1. {{question_1}}
2. {{question_2}}
3. {{question_3}}

## Expected Deliverables
{{expected_deliverables}}

## Timeline
{{timeline}}

## Success Criteria
{{success_criteria}}
`,
                metadata: {
                    category: 'research',
                    tags: ['analysis', 'research', 'investigation']
                }
            }
        ];
    }

    private isBuiltInVariable(name: string): boolean {
        const builtInVars = ['current_date', 'current_time', 'current_datetime'];
        return builtInVars.includes(name);
    }

    /**
     * Dispose resources
     */
    dispose(): void {
        // Clean up any resources if needed
        this.logger.info('TemplateManager disposed');
    }
}
