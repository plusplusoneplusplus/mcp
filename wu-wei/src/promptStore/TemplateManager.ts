/**
 * Template Manager - Handles prompt templates and template processing
 * Following wu wei principles: simple, flexible templates that flow naturally
 */

import * as vscode from 'vscode';
import * as fs from 'fs/promises';
import * as path from 'path';
import { PromptTemplate, ParameterDef, PromptMetadata } from './types';
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
            },
            parameters: this.extractParameters(promptContent)
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
                },
                parameters: [
                    { name: 'title', type: 'string', required: true, description: 'The title of the prompt' }
                ]
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
                },
                parameters: [
                    { name: 'meeting_title', type: 'string', required: true, description: 'Title of the meeting' },
                    { name: 'date', type: 'string', required: false, description: 'Meeting date', defaultValue: '{{current_date}}' },
                    { name: 'duration', type: 'number', required: false, description: 'Meeting duration in minutes', defaultValue: 60 },
                    { name: 'attendees', type: 'string', required: true, description: 'List of meeting attendees' },
                    { name: 'agenda_item_1', type: 'string', required: false, description: 'First agenda item' },
                    { name: 'agenda_item_2', type: 'string', required: false, description: 'Second agenda item' },
                    { name: 'agenda_item_3', type: 'string', required: false, description: 'Third agenda item' },
                    { name: 'discussion_points', type: 'string', required: false, description: 'Key discussion points' },
                    { name: 'action_item_1', type: 'string', required: false, description: 'First action item' },
                    { name: 'action_item_2', type: 'string', required: false, description: 'Second action item' },
                    { name: 'action_item_3', type: 'string', required: false, description: 'Third action item' },
                    { name: 'next_steps', type: 'string', required: false, description: 'Next steps and follow-ups' },
                    { name: 'additional_notes', type: 'string', required: false, description: 'Additional notes or comments' }
                ]
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
                },
                parameters: [
                    { name: 'component_name', type: 'string', required: true, description: 'Name of the component or file being reviewed' },
                    { name: 'context_description', type: 'string', required: true, description: 'Context about the code being reviewed' },
                    { name: 'language', type: 'string', required: true, description: 'Programming language of the code' },
                    { name: 'code_snippet', type: 'string', required: true, description: 'The actual code to be reviewed' },
                    { name: 'focus_areas', type: 'string', required: false, description: 'Specific areas to focus on during review' },
                    { name: 'specific_questions', type: 'string', required: false, description: 'Specific questions about the code' }
                ]
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
                },
                parameters: [
                    { name: 'title', type: 'string', required: true, description: 'Title of the documentation' },
                    { name: 'overview', type: 'string', required: true, description: 'High-level overview of the component' },
                    { name: 'purpose', type: 'string', required: true, description: 'Purpose and use case of the component' },
                    { name: 'language', type: 'string', required: true, description: 'Programming language' },
                    { name: 'usage_example', type: 'string', required: true, description: 'Basic usage example' },
                    { name: 'parameters_description', type: 'string', required: false, description: 'Description of parameters' },
                    { name: 'return_value_description', type: 'string', required: false, description: 'Description of return value' },
                    { name: 'examples', type: 'string', required: false, description: 'Additional examples' },
                    { name: 'additional_notes', type: 'string', required: false, description: 'Additional notes or caveats' },
                    { name: 'related_documentation', type: 'string', required: false, description: 'Links to related documentation' }
                ]
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
                },
                parameters: [
                    { name: 'topic', type: 'string', required: true, description: 'Topic of analysis' },
                    { name: 'objective', type: 'string', required: true, description: 'Objective of the analysis' },
                    { name: 'background_information', type: 'string', required: true, description: 'Background context' },
                    { name: 'data_sources', type: 'string', required: false, description: 'Available data sources' },
                    { name: 'analysis_framework', type: 'string', required: false, description: 'Framework or methodology to use' },
                    { name: 'question_1', type: 'string', required: false, description: 'First key question' },
                    { name: 'question_2', type: 'string', required: false, description: 'Second key question' },
                    { name: 'question_3', type: 'string', required: false, description: 'Third key question' },
                    { name: 'expected_deliverables', type: 'string', required: false, description: 'What output is expected' },
                    { name: 'timeline', type: 'string', required: false, description: 'Timeline for completion' },
                    { name: 'success_criteria', type: 'string', required: false, description: 'How to measure success' }
                ]
            }
        ];
    }

    private extractParameters(content: string): ParameterDef[] {
        const parameters: ParameterDef[] = [];
        const parameterRegex = /{{(\w+)}}/g;
        const matches = content.matchAll(parameterRegex);

        const foundParams = new Set<string>();

        for (const match of matches) {
            const paramName = match[1];
            if (!foundParams.has(paramName) && !this.isBuiltInVariable(paramName)) {
                foundParams.add(paramName);
                parameters.push({
                    name: paramName,
                    type: 'string',
                    required: true,
                    description: `Parameter: ${paramName}`
                });
            }
        }

        return parameters;
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
