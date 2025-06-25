/**
 * Metadata Parser for extracting YAML frontmatter from prompt files
 * Following wu wei principles: gentle parsing that flows with the content
 */

import { parse as parseYaml } from 'yaml';
import { PromptMetadata, ValidationResult } from './types';
import { FRONTMATTER_DELIMITERS, DEFAULT_METADATA_SCHEMA, VALIDATION_RULES } from './constants';
import { WuWeiLogger } from '../logger';

export class MetadataParser {
    private logger: WuWeiLogger;

    constructor() {
        this.logger = WuWeiLogger.getInstance();
    }

    /**
     * Parse YAML frontmatter from markdown content
     */
    public parseMetadata(content: string): { metadata: PromptMetadata | null; content: string } {
        try {
            const { frontmatter, body } = this.extractFrontmatter(content);

            if (!frontmatter) {
                this.logger.info('No frontmatter found, using default metadata');
                return {
                    metadata: { ...DEFAULT_METADATA_SCHEMA } as PromptMetadata,
                    content: body
                };
            }

            const metadata = this.parseFrontmatter(frontmatter);
            return {
                metadata,
                content: body
            };
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to parse metadata', { error: errorMessage });
            return {
                metadata: null,
                content
            };
        }
    }

    /**
     * Validate parsed metadata
     */
    public validateMetadata(metadata: PromptMetadata): ValidationResult {
        const errors: any[] = [];
        const warnings: any[] = [];

        // Validate title
        if (!metadata.title || metadata.title.trim().length === 0) {
            errors.push({
                field: 'title',
                message: 'Title is required',
                severity: 'error'
            });
        } else if (metadata.title.length > VALIDATION_RULES.TITLE.MAX_LENGTH) {
            errors.push({
                field: 'title',
                message: `Title exceeds maximum length of ${VALIDATION_RULES.TITLE.MAX_LENGTH}`,
                severity: 'error'
            });
        }

        // Validate category
        if (metadata.category && !VALIDATION_RULES.CATEGORY.PATTERN.test(metadata.category)) {
            warnings.push({
                field: 'category',
                message: 'Category contains invalid characters',
                suggestion: 'Use only letters, numbers, spaces, hyphens, and underscores'
            });
        }

        // Validate tags
        if (metadata.tags && metadata.tags.length > VALIDATION_RULES.TAG.MAX_COUNT) {
            warnings.push({
                field: 'tags',
                message: `Too many tags (maximum ${VALIDATION_RULES.TAG.MAX_COUNT})`,
                suggestion: 'Reduce the number of tags'
            });
        }

        return {
            isValid: errors.length === 0,
            errors,
            warnings
        };
    }

    /**
     * Extract frontmatter and body from content
     */
    private extractFrontmatter(content: string): { frontmatter: string | null; body: string } {
        const lines = content.split('\n');

        if (lines[0] !== FRONTMATTER_DELIMITERS.START) {
            return { frontmatter: null, body: content };
        }

        let endIndex = -1;
        for (let i = 1; i < lines.length; i++) {
            if (lines[i] === FRONTMATTER_DELIMITERS.END) {
                endIndex = i;
                break;
            }
        }

        if (endIndex === -1) {
            return { frontmatter: null, body: content };
        }

        const frontmatter = lines.slice(1, endIndex).join('\n');
        const body = lines.slice(endIndex + 1).join('\n').trim();

        return { frontmatter, body };
    }

    /**
     * Parse YAML frontmatter
     */
    private parseFrontmatter(frontmatter: string): PromptMetadata {
        try {
            const parsed = parseYaml(frontmatter);

            // Merge with defaults and ensure proper types
            const metadata: PromptMetadata = {
                ...DEFAULT_METADATA_SCHEMA,
                ...parsed,
                created: parsed.created ? new Date(parsed.created) : new Date(),
                modified: parsed.modified ? new Date(parsed.modified) : new Date()
            };

            return metadata;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.warn('Failed to parse YAML frontmatter', { error: errorMessage });
            return { ...DEFAULT_METADATA_SCHEMA } as PromptMetadata;
        }
    }
}
