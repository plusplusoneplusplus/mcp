import { BasePromptElementProps, PromptElement } from '@vscode/prompt-tsx';
import { ValidationError, ValidationResult } from '../types';

/**
 * TSX component validation utility
 */
export class TsxValidation {
    /**
     * Validate a TSX component class and props
     */
    validateComponent<T extends BasePromptElementProps>(
        component: new (props: T) => PromptElement<T>,
        props: T
    ): ValidationResult {
        const errors: ValidationError[] = [];
        const warnings: ValidationError[] = [];

        try {
            // Validate component constructor
            if (typeof component !== 'function') {
                errors.push({
                    field: 'component',
                    message: 'Component must be a constructor function',
                    severity: 'error'
                });
                return { isValid: false, errors, warnings };
            }

            // Validate props
            if (!props || typeof props !== 'object') {
                errors.push({
                    field: 'props',
                    message: 'Props must be a valid object',
                    severity: 'error'
                });
                return { isValid: false, errors, warnings };
            }

            // Try to instantiate the component
            let instance: PromptElement<T>;
            try {
                instance = new component(props);
            } catch (error) {
                errors.push({
                    field: 'instantiation',
                    message: `Failed to create component instance: ${error instanceof Error ? error.message : String(error)}`,
                    severity: 'error'
                });
                return { isValid: false, errors, warnings };
            }

            // Validate component has render method
            if (!instance || typeof instance.render !== 'function') {
                errors.push({
                    field: 'render',
                    message: 'Component must have a render method',
                    severity: 'error'
                });
            }

            // Validate common props
            this.validateCommonProps(props, errors, warnings);

            // Validate specific prop types
            this.validatePropTypes(props, errors, warnings);

        } catch (error) {
            errors.push({
                field: 'validation',
                message: `Validation failed: ${error instanceof Error ? error.message : String(error)}`,
                severity: 'error'
            });
        }

        return {
            isValid: errors.length === 0,
            errors,
            warnings
        };
    }

    /**
     * Validate common BasePromptElementProps
     */
    private validateCommonProps(
        props: BasePromptElementProps,
        errors: ValidationError[],
        warnings: ValidationError[]
    ): void {
        // Validate priority
        if (props.priority !== undefined) {
            if (typeof props.priority !== 'number') {
                errors.push({
                    field: 'priority',
                    message: 'Priority must be a number',
                    severity: 'error'
                });
            } else if (props.priority < 0 || props.priority > 100) {
                warnings.push({
                    field: 'priority',
                    message: 'Priority should be between 0 and 100',
                    severity: 'warning'
                });
            }
        }

        // Validate flexGrow
        if (props.flexGrow !== undefined) {
            if (typeof props.flexGrow !== 'number') {
                errors.push({
                    field: 'flexGrow',
                    message: 'flexGrow must be a number',
                    severity: 'error'
                });
            } else if (props.flexGrow < 0) {
                warnings.push({
                    field: 'flexGrow',
                    message: 'flexGrow should be non-negative',
                    severity: 'warning'
                });
            }
        }

        // Note: maxTokens validation is handled in specific prop validation
    }

    /**
     * Validate specific prop types based on common patterns
     */
    private validatePropTypes(
        props: any,
        errors: ValidationError[],
        warnings: ValidationError[]
    ): void {
        // Validate string props that shouldn't be empty
        const stringProps = ['systemPrompt', 'userInput', 'content'];
        for (const propName of stringProps) {
            if (propName in props) {
                if (typeof props[propName] !== 'string') {
                    errors.push({
                        field: propName,
                        message: `${propName} must be a string`,
                        severity: 'error'
                    });
                } else if (props[propName].trim().length === 0) {
                    warnings.push({
                        field: propName,
                        message: `${propName} should not be empty`,
                        severity: 'warning'
                    });
                }
            }
        }

        // Validate array props
        const arrayProps = ['conversationHistory', 'history'];
        for (const propName of arrayProps) {
            if (propName in props && props[propName] !== undefined) {
                if (!Array.isArray(props[propName])) {
                    errors.push({
                        field: propName,
                        message: `${propName} must be an array`,
                        severity: 'error'
                    });
                }
            }
        }

        // Validate boolean props
        const booleanProps = ['includeTimestamps', 'enforced'];
        for (const propName of booleanProps) {
            if (propName in props && props[propName] !== undefined) {
                if (typeof props[propName] !== 'boolean') {
                    errors.push({
                        field: propName,
                        message: `${propName} must be a boolean`,
                        severity: 'error'
                    });
                }
            }
        }

        // Validate number props that should be positive
        const positiveNumberProps = ['maxMessages', 'maxTokens'];
        for (const propName of positiveNumberProps) {
            if (propName in props && props[propName] !== undefined) {
                if (typeof props[propName] !== 'number') {
                    errors.push({
                        field: propName,
                        message: `${propName} must be a number`,
                        severity: 'error'
                    });
                } else if (props[propName] <= 0) {
                    errors.push({
                        field: propName,
                        message: `${propName} must be positive`,
                        severity: 'error'
                    });
                }
            }
        }
    }

    /**
     * Validate a collection of components
     */
    validateComponents<T extends BasePromptElementProps>(
        components: Array<{ component: new (props: T) => PromptElement<T>; props: T }>
    ): ValidationResult {
        const allErrors: ValidationError[] = [];
        const allWarnings: ValidationError[] = [];

        for (let i = 0; i < components.length; i++) {
            const { component, props } = components[i];
            const result = this.validateComponent(component, props);

            // Prefix field names with component index
            const prefixedErrors = result.errors.map(error => ({
                ...error,
                field: `component[${i}].${error.field}`
            }));

            const prefixedWarnings = result.warnings.map(warning => ({
                ...warning,
                field: `component[${i}].${warning.field}`
            }));

            allErrors.push(...prefixedErrors);
            allWarnings.push(...prefixedWarnings);
        }

        return {
            isValid: allErrors.length === 0,
            errors: allErrors,
            warnings: allWarnings
        };
    }

    /**
     * Create a simple validation result for success
     */
    createSuccessResult(): ValidationResult {
        return {
            isValid: true,
            errors: [],
            warnings: []
        };
    }

    /**
     * Create a validation result with a single error
     */
    createErrorResult(field: string, message: string): ValidationResult {
        return {
            isValid: false,
            errors: [{
                field,
                message,
                severity: 'error'
            }],
            warnings: []
        };
    }
} 