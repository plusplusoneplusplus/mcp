import { VariableResolutionOptions, ValidationError, PromptParameter } from '../types';

export class VariableResolver {
    static readonly VARIABLE_PATTERN = /\{\{(\w+)\}\}/g;

    resolve(
        content: string,
        variables: Record<string, any>,
        options: VariableResolutionOptions = {}
    ): string {
        const { strictMode = false, allowUndefined = false, defaultValues = {} } = options;

        return content.replace(VariableResolver.VARIABLE_PATTERN, (match, variableName) => {
            if (variables.hasOwnProperty(variableName)) {
                return String(variables[variableName]);
            }

            if (defaultValues.hasOwnProperty(variableName)) {
                return String(defaultValues[variableName]);
            }

            if (options.resolver) {
                const resolved = options.resolver(variableName);
                if (resolved !== undefined) {
                    return String(resolved);
                }
            }

            if (strictMode) {
                throw new Error(`Undefined variable: ${variableName}`);
            }

            return allowUndefined ? match : '';
        });
    }

    extractVariables(content: string): string[] {
        const variables: string[] = [];
        const matches = content.matchAll(VariableResolver.VARIABLE_PATTERN);

        for (const match of matches) {
            if (!variables.includes(match[1])) {
                variables.push(match[1]);
            }
        }

        return variables;
    }

    validateVariables(
        content: string,
        variables: Record<string, any>,
        parameters: PromptParameter[]
    ): ValidationError[] {
        const errors: ValidationError[] = [];
        const requiredVars = parameters.filter(p => p.required).map(p => p.name);
        const extractedVars = this.extractVariables(content);

        // Check for missing required variables
        for (const required of requiredVars) {
            if (!variables.hasOwnProperty(required)) {
                errors.push({
                    field: required,
                    message: `Required variable '${required}' is missing`,
                    severity: 'error'
                });
            }
        }

        // Check for unused variables
        for (const provided of Object.keys(variables)) {
            if (!extractedVars.includes(provided)) {
                errors.push({
                    field: provided,
                    message: `Variable '${provided}' is not used in the prompt`,
                    severity: 'warning'
                });
            }
        }

        // Validate parameter constraints
        for (const param of parameters) {
            const value = variables[param.name];
            if (value !== undefined) {
                const paramErrors = this.validateParameterValue(param, value);
                errors.push(...paramErrors);
            }
        }

        return errors;
    }

    private validateParameterValue(parameter: PromptParameter, value: any): ValidationError[] {
        const errors: ValidationError[] = [];
        const { name, type, validation } = parameter;

        // Type validation
        switch (type) {
            case 'number':
                if (typeof value !== 'number' && !Number.isFinite(Number(value))) {
                    errors.push({
                        field: name,
                        message: `Variable '${name}' must be a number`,
                        severity: 'error'
                    });
                    return errors; // Skip further validation if type is wrong
                }
                break;
            case 'boolean':
                if (typeof value !== 'boolean' && value !== 'true' && value !== 'false') {
                    errors.push({
                        field: name,
                        message: `Variable '${name}' must be a boolean`,
                        severity: 'error'
                    });
                    return errors;
                }
                break;
            case 'select':
                if (parameter.options && !parameter.options.includes(String(value))) {
                    errors.push({
                        field: name,
                        message: `Variable '${name}' must be one of: ${parameter.options.join(', ')}`,
                        severity: 'error'
                    });
                }
                break;
        }

        // Validation rules
        if (validation) {
            const stringValue = String(value);

            if (validation.pattern) {
                const regex = new RegExp(validation.pattern);
                if (!regex.test(stringValue)) {
                    errors.push({
                        field: name,
                        message: `Variable '${name}' does not match required pattern`,
                        severity: 'error'
                    });
                }
            }

            if (validation.minLength !== undefined && stringValue.length < validation.minLength) {
                errors.push({
                    field: name,
                    message: `Variable '${name}' must be at least ${validation.minLength} characters`,
                    severity: 'error'
                });
            }

            if (validation.maxLength !== undefined && stringValue.length > validation.maxLength) {
                errors.push({
                    field: name,
                    message: `Variable '${name}' must be no more than ${validation.maxLength} characters`,
                    severity: 'error'
                });
            }

            if (type === 'number') {
                const numValue = Number(value);
                if (validation.min !== undefined && numValue < validation.min) {
                    errors.push({
                        field: name,
                        message: `Variable '${name}' must be at least ${validation.min}`,
                        severity: 'error'
                    });
                }

                if (validation.max !== undefined && numValue > validation.max) {
                    errors.push({
                        field: name,
                        message: `Variable '${name}' must be no more than ${validation.max}`,
                        severity: 'error'
                    });
                }
            }
        }

        return errors;
    }
} 