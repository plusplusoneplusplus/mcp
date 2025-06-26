/**
 * Metadata Parser for extracting YAML frontmatter from prompt files
 * Following wu wei principles: gentle parsing that flows with the content
 */

import * as fs from 'fs';
import * as path from 'path';
import { parse as parseYaml } from 'yaml';
import {
    PromptMetadata,
    ValidationResult,
    ValidationError,
    ValidationWarning,
    ParsedPrompt,
    ValidationRule,
    MetadataCacheEntry,
    Prompt
} from './types';
import {
    FRONTMATTER_DELIMITERS,
    DEFAULT_METADATA_SCHEMA,
    VALIDATION_RULES
} from './constants';
import { WuWeiLogger } from '../logger';

export class MetadataParser {
    private logger: WuWeiLogger;
    private cache: Map<string, MetadataCacheEntry> = new Map();

    constructor() {
        this.logger = WuWeiLogger.getInstance();
    }

    /**
     * Parse a prompt file and return complete parsing result
     */
    public async parseFile(filePath: string): Promise<ParsedPrompt> {
        try {
            // Check cache first
            const stats = await fs.promises.stat(filePath);
            const lastModified = stats.mtime.getTime();

            const cachedEntry = this.cache.get(filePath);
            if (cachedEntry && cachedEntry.lastModified === lastModified) {
                this.logger.debug('Using cached metadata for file', { filePath });
                return {
                    success: true,
                    metadata: cachedEntry.metadata,
                    content: cachedEntry.content,
                    errors: cachedEntry.errors,
                    warnings: cachedEntry.warnings
                };
            }

            // Read and parse file
            const content = await fs.promises.readFile(filePath, 'utf-8');
            const parseResult = this.parseContent(content);

            if (parseResult.success && parseResult.metadata) {
                // Enhance metadata with file information
                const enhancedMetadata = await this.enhanceMetadata(parseResult.metadata, filePath, stats);

                // Create prompt object
                const prompt: Prompt = {
                    id: this.generatePromptId(filePath),
                    filePath,
                    fileName: path.basename(filePath),
                    metadata: enhancedMetadata,
                    content: parseResult.content || '',
                    lastModified: stats.mtime,
                    isValid: parseResult.errors.length === 0,
                    validationErrors: parseResult.errors.map(e => e.message)
                };

                // Cache the result
                this.cache.set(filePath, {
                    metadata: enhancedMetadata,
                    content: parseResult.content || '',
                    lastModified,
                    filePath,
                    errors: parseResult.errors,
                    warnings: parseResult.warnings
                });

                return {
                    success: true,
                    prompt,
                    metadata: enhancedMetadata,
                    content: parseResult.content,
                    errors: parseResult.errors,
                    warnings: parseResult.warnings
                };
            }

            return parseResult;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to parse file', { filePath, error: errorMessage });

            return {
                success: false,
                errors: [{
                    field: 'file',
                    message: `Failed to parse file: ${errorMessage}`,
                    severity: 'error' as const
                }],
                warnings: []
            };
        }
    }

    /**
     * Parse content string and return metadata and content
     */
    public parseContent(content: string): ParsedPrompt {
        try {
            const { metadata: rawMetadata, content: bodyContent } = this.extractFrontmatter(content);

            let metadata: PromptMetadata;
            const errors: ValidationError[] = [];
            const warnings: ValidationWarning[] = [];

            if (rawMetadata) {
                try {
                    metadata = this.parseFrontmatter(rawMetadata);
                } catch (yamlError) {
                    const errorMessage = yamlError instanceof Error ? yamlError.message : String(yamlError);
                    errors.push({
                        field: 'frontmatter',
                        message: `Invalid YAML syntax: ${errorMessage}`,
                        severity: 'error'
                    });
                    metadata = this.getDefaultMetadata();
                }
            } else {
                metadata = this.getDefaultMetadata();
                this.logger.debug('No frontmatter found, using defaults');
            }

            // Validate metadata
            const validationResult = this.validateMetadata(metadata);
            errors.push(...validationResult.errors);
            warnings.push(...validationResult.warnings);

            return {
                success: errors.length === 0,
                metadata,
                content: bodyContent,
                errors,
                warnings
            };
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to parse content', { error: errorMessage });

            return {
                success: false,
                errors: [{
                    field: 'content',
                    message: `Failed to parse content: ${errorMessage}`,
                    severity: 'error' as const
                }],
                warnings: []
            };
        }
    }

    /**
     * Validate parsed metadata against schema and rules
     */
    public validateMetadata(metadata: PromptMetadata): ValidationResult {
        const errors: ValidationError[] = [];
        const warnings: ValidationWarning[] = [];

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
        } else if (!VALIDATION_RULES.TITLE.PATTERN.test(metadata.title)) {
            warnings.push({
                field: 'title',
                message: 'Title contains special characters that may cause issues',
                suggestion: 'Consider using only letters, numbers, spaces, and basic punctuation'
            });
        }

        // Validate description
        if (metadata.description && metadata.description.length > VALIDATION_RULES.DESCRIPTION.MAX_LENGTH) {
            warnings.push({
                field: 'description',
                message: `Description is very long (${metadata.description.length} characters)`,
                suggestion: `Consider keeping it under ${VALIDATION_RULES.DESCRIPTION.MAX_LENGTH} characters`
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
                message: `Too many tags (${metadata.tags.length}, maximum ${VALIDATION_RULES.TAG.MAX_COUNT})`,
                suggestion: 'Reduce the number of tags for better organization'
            });
        }

        if (metadata.tags) {
            metadata.tags.forEach((tag, index) => {
                if (!VALIDATION_RULES.TAG.PATTERN.test(tag)) {
                    warnings.push({
                        field: `tags[${index}]`,
                        message: `Tag "${tag}" contains invalid characters`,
                        suggestion: 'Tags should only contain letters, numbers, hyphens, and underscores'
                    });
                }
                if (tag.length > VALIDATION_RULES.TAG.MAX_LENGTH) {
                    warnings.push({
                        field: `tags[${index}]`,
                        message: `Tag "${tag}" is too long`,
                        suggestion: `Keep tags under ${VALIDATION_RULES.TAG.MAX_LENGTH} characters`
                    });
                }
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
    public extractFrontmatter(content: string): { metadata: string | null, content: string } {
        // Handle different line endings
        const normalizedContent = content.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        const lines = normalizedContent.split('\n');

        if (lines.length === 0 || lines[0] !== FRONTMATTER_DELIMITERS.START) {
            return { metadata: null, content: normalizedContent };
        }

        let endIndex = -1;
        for (let i = 1; i < lines.length; i++) {
            if (lines[i] === FRONTMATTER_DELIMITERS.END) {
                endIndex = i;
                break;
            }
        }

        if (endIndex === -1) {
            // Frontmatter started but never ended - treat as no frontmatter
            return { metadata: null, content: normalizedContent };
        }

        const frontmatter = lines.slice(1, endIndex).join('\n');
        const body = lines.slice(endIndex + 1).join('\n').trim();

        return { metadata: frontmatter, content: body };
    }

    /**
     * Get default metadata values
     */
    public getDefaultMetadata(): PromptMetadata {
        return {
            title: 'Untitled Prompt',
            description: '',
            category: 'General',
            tags: []
        };
    }

    /**
     * Generate a unique ID for a prompt based on its file path
     */
    private generatePromptId(filePath: string): string {
        const relativePath = path.relative(process.cwd(), filePath);
        return relativePath.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
    }

    /**
     * Enhance metadata with file system information
     */
    private async enhanceMetadata(
        metadata: PromptMetadata,
        filePath: string,
        stats: fs.Stats
    ): Promise<PromptMetadata> {
        const enhanced = { ...metadata };

        // Set title from filename if not provided
        if (!enhanced.title || enhanced.title === 'Untitled Prompt') {
            const baseName = path.basename(filePath, path.extname(filePath));
            enhanced.title = baseName
                .replace(/[-_]/g, ' ')
                .replace(/\b\w/g, l => l.toUpperCase());
        }

        return enhanced;
    }

    /**
     * Parse YAML frontmatter into metadata object
     */
    private parseFrontmatter(frontmatter: string): PromptMetadata {
        try {
            const parsed = parseYaml(frontmatter);

            if (!parsed || typeof parsed !== 'object') {
                this.logger.warn('Frontmatter is not a valid object');
                return this.getDefaultMetadata();
            }

            // Merge with defaults and ensure proper types
            const metadata: PromptMetadata = {
                ...this.getDefaultMetadata(),
                ...parsed
            };

            // Ensure arrays are arrays
            if (parsed.tags && !Array.isArray(parsed.tags)) {
                metadata.tags = [];
                this.logger.warn('Tags field is not an array, using empty array');
            }

            return metadata;
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : String(error);
            this.logger.error('Failed to parse YAML frontmatter', { error: errorMessage });
            throw error;
        }
    }

    /**
     * Clear the metadata cache
     */
    public clearCache(): void {
        this.cache.clear();
        this.logger.debug('Metadata cache cleared');
    }

    /**
     * Get cache statistics
     */
    public getCacheStats(): { size: number; entries: string[] } {
        return {
            size: this.cache.size,
            entries: Array.from(this.cache.keys())
        };
    }
}
