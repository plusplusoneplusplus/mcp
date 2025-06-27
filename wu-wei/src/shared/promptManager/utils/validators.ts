import { ValidationError, PromptParameter } from '../types';

export class PromptValidators {
    /**
     * Validate prompt content structure
     */
    static validatePromptContent(content: string): ValidationError[] {
        const errors: ValidationError[] = [];

        if (!content || content.trim().length === 0) {
            errors.push({
                field: 'content',
                message: 'Prompt content cannot be empty',
                severity: 'error'
            });
            return errors;
        }

        // Check for balanced variable brackets
        const openBrackets = (content.match(/\{\{/g) || []).length;
        const closeBrackets = (content.match(/\}\}/g) || []).length;

        if (openBrackets !== closeBrackets) {
            errors.push({
                field: 'content',
                message: 'Unbalanced variable brackets in prompt content',
                severity: 'error'
            });
        }

        // Check for nested variables (not supported)
        const nestedPattern = /\{\{[^}]*\{\{/g;
        if (nestedPattern.test(content)) {
            errors.push({
                field: 'content',
                message: 'Nested variables are not supported',
                severity: 'error'
            });
        }

        // Check for empty variables
        const emptyVarPattern = /\{\{\s*\}\}/g;
        if (emptyVarPattern.test(content)) {
            errors.push({
                field: 'content',
                message: 'Empty variable names are not allowed',
                severity: 'error'
            });
        }

        // Check for invalid variable names
        const invalidVarPattern = /\{\{([^}]*[^a-zA-Z0-9_][^}]*)\}\}/g;
        const invalidMatches = content.matchAll(invalidVarPattern);
        for (const match of invalidMatches) {
            errors.push({
                field: 'content',
                message: `Invalid variable name '${match[1]}'. Use only letters, numbers, and underscores`,
                severity: 'error'
            });
        }

        return errors;
    }

    /**
     * Validate prompt parameters configuration
     */
    static validatePromptParameters(parameters: PromptParameter[]): ValidationError[] {
        const errors: ValidationError[] = [];
        const paramNames = new Set<string>();

        for (const param of parameters) {
            // Check for duplicate parameter names
            if (paramNames.has(param.name)) {
                errors.push({
                    field: `parameters.${param.name}`,
                    message: `Duplicate parameter name '${param.name}'`,
                    severity: 'error'
                });
            }
            paramNames.add(param.name);

            // Validate parameter name
            if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(param.name)) {
                errors.push({
                    field: `parameters.${param.name}`,
                    message: `Invalid parameter name '${param.name}'. Must start with letter or underscore, contain only letters, numbers, and underscores`,
                    severity: 'error'
                });
            }

            // Validate select type parameters
            if (param.type === 'select') {
                if (!param.options || param.options.length === 0) {
                    errors.push({
                        field: `parameters.${param.name}`,
                        message: `Select parameter '${param.name}' must have options`,
                        severity: 'error'
                    });
                }

                if (param.defaultValue && param.options && !param.options.includes(String(param.defaultValue))) {
                    errors.push({
                        field: `parameters.${param.name}`,
                        message: `Default value for '${param.name}' must be one of the available options`,
                        severity: 'error'
                    });
                }
            }

            // Validate number type parameters
            if (param.type === 'number') {
                if (param.defaultValue !== undefined && !Number.isFinite(Number(param.defaultValue))) {
                    errors.push({
                        field: `parameters.${param.name}`,
                        message: `Default value for number parameter '${param.name}' must be a valid number`,
                        severity: 'error'
                    });
                }

                if (param.validation) {
                    if (param.validation.min !== undefined && param.validation.max !== undefined) {
                        if (param.validation.min > param.validation.max) {
                            errors.push({
                                field: `parameters.${param.name}`,
                                message: `Minimum value cannot be greater than maximum value for '${param.name}'`,
                                severity: 'error'
                            });
                        }
                    }
                }
            }

            // Validate boolean type parameters
            if (param.type === 'boolean') {
                if (param.defaultValue !== undefined &&
                    typeof param.defaultValue !== 'boolean' &&
                    param.defaultValue !== 'true' &&
                    param.defaultValue !== 'false') {
                    errors.push({
                        field: `parameters.${param.name}`,
                        message: `Default value for boolean parameter '${param.name}' must be a boolean or 'true'/'false' string`,
                        severity: 'error'
                    });
                }
            }

            // Validate string validation rules
            if (param.validation) {
                if (param.validation.minLength !== undefined && param.validation.minLength < 0) {
                    errors.push({
                        field: `parameters.${param.name}`,
                        message: `Minimum length cannot be negative for '${param.name}'`,
                        severity: 'error'
                    });
                }

                if (param.validation.maxLength !== undefined && param.validation.maxLength < 0) {
                    errors.push({
                        field: `parameters.${param.name}`,
                        message: `Maximum length cannot be negative for '${param.name}'`,
                        severity: 'error'
                    });
                }

                if (param.validation.minLength !== undefined &&
                    param.validation.maxLength !== undefined &&
                    param.validation.minLength > param.validation.maxLength) {
                    errors.push({
                        field: `parameters.${param.name}`,
                        message: `Minimum length cannot be greater than maximum length for '${param.name}'`,
                        severity: 'error'
                    });
                }

                if (param.validation.pattern) {
                    try {
                        new RegExp(param.validation.pattern);
                    } catch (error) {
                        errors.push({
                            field: `parameters.${param.name}`,
                            message: `Invalid regex pattern for '${param.name}': ${error instanceof Error ? error.message : String(error)}`,
                            severity: 'error'
                        });
                    }
                }
            }
        }

        return errors;
    }

    /**
     * Validate that prompt content matches its parameter definitions
     */
    static validatePromptContentMatchesParameters(
        content: string,
        parameters: PromptParameter[]
    ): ValidationError[] {
        const errors: ValidationError[] = [];

        // Extract variables from content
        const variablePattern = /\{\{(\w+)\}\}/g;
        const contentVariables = new Set<string>();
        const matches = content.matchAll(variablePattern);

        for (const match of matches) {
            contentVariables.add(match[1]);
        }

        // Check for parameters without corresponding variables
        const parameterNames = new Set(parameters.map(p => p.name));
        for (const paramName of parameterNames) {
            if (!contentVariables.has(paramName)) {
                errors.push({
                    field: `parameters.${paramName}`,
                    message: `Parameter '${paramName}' is defined but not used in prompt content`,
                    severity: 'warning'
                });
            }
        }

        // Check for variables without corresponding parameters
        for (const varName of contentVariables) {
            if (!parameterNames.has(varName)) {
                errors.push({
                    field: 'content',
                    message: `Variable '${varName}' is used in content but not defined as a parameter`,
                    severity: 'warning'
                });
            }
        }

        return errors;
    }

    /**
     * Comprehensive prompt validation
     */
    static validatePrompt(
        content: string,
        parameters: PromptParameter[] = []
    ): ValidationError[] {
        const errors: ValidationError[] = [];

        // Validate content
        errors.push(...this.validatePromptContent(content));

        // Validate parameters
        errors.push(...this.validatePromptParameters(parameters));

        // Validate content-parameter consistency
        errors.push(...this.validatePromptContentMatchesParameters(content, parameters));

        return errors;
    }
} 