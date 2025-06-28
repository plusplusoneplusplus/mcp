import { BasePromptElementProps, ValidationError, ValidationResult, PromptElement } from '../types';

/**
 * TSX Validation Utility - Validates TSX prompt components and their props
 */
export class TsxValidation {
    private static instance: TsxValidation | null = null;

    /**
     * Get singleton instance
     */
    static getInstance(): TsxValidation {
        if (!this.instance) {
            this.instance = new TsxValidation();
        }
        return this.instance;
    }

    /**
     * Validate a TSX prompt component
     */
    async validateComponent<T extends BasePromptElementProps>(
        componentClass: new (props: T) => PromptElement<T>,
        props: T,
        requiredProps: (keyof T)[] = []
    ): Promise<ValidationResult> {
        const errors: ValidationError[] = [];
        const warnings: ValidationError[] = [];

        try {
            // Validate required props
            for (const propName of requiredProps) {
                if (props[propName] === undefined || props[propName] === null) {
                    errors.push({
                        field: String(propName),
                        message: `Required property '${String(propName)}' is missing`,
                        severity: 'error'
                    });
                }
            }

            // Validate base prompt element props
            this.validateBaseProps(props, errors, warnings);

            // Try to instantiate the component
            const component = new componentClass(props);

            // Validate that render method exists and is callable
            if (typeof component.render !== 'function') {
                errors.push({
                    field: 'render',
                    message: 'Component must have a render() method',
                    severity: 'error'
                });
            } else {
                // Try to call render to catch any runtime errors
                try {
                    const rendered = component.render();
                    this.validateRenderedOutput(rendered, errors, warnings);
                } catch (renderError) {
                    errors.push({
                        field: 'render',
                        message: `Render method failed: ${renderError instanceof Error ? renderError.message : String(renderError)}`,
                        severity: 'error'
                    });
                }
            }

        } catch (instantiationError) {
            errors.push({
                field: 'constructor',
                message: `Component instantiation failed: ${instantiationError instanceof Error ? instantiationError.message : String(instantiationError)}`,
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
     * Validate base prompt element properties
     */
    private validateBaseProps(props: BasePromptElementProps, errors: ValidationError[], warnings: ValidationError[]): void {
        // Validate priority
        if (props.priority !== undefined) {
            if (typeof props.priority !== 'number') {
                errors.push({
                    field: 'priority',
                    message: 'Priority must be a number',
                    severity: 'error'
                });
            } else if (props.priority < 0 || props.priority > 100) {
                errors.push({
                    field: 'priority',
                    message: 'Priority must be between 0 and 100',
                    severity: 'error'
                });
            } else if (props.priority < 10) {
                warnings.push({
                    field: 'priority',
                    message: 'Very low priority may result in content being excluded',
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
                errors.push({
                    field: 'flexGrow',
                    message: 'flexGrow must be non-negative',
                    severity: 'error'
                });
            }
        }

        // Validate maxTokens
        if (props.maxTokens !== undefined) {
            if (typeof props.maxTokens !== 'number') {
                errors.push({
                    field: 'maxTokens',
                    message: 'maxTokens must be a number',
                    severity: 'error'
                });
            } else if (props.maxTokens <= 0) {
                errors.push({
                    field: 'maxTokens',
                    message: 'maxTokens must be positive',
                    severity: 'error'
                });
            } else if (props.maxTokens > 10000) {
                warnings.push({
                    field: 'maxTokens',
                    message: 'Very high maxTokens may exceed model limits',
                    severity: 'warning'
                });
            }
        }
    }

    /**
     * Validate the output of a component's render method
     */
    private validateRenderedOutput(rendered: any, errors: ValidationError[], warnings: ValidationError[]): void {
        if (rendered === null || rendered === undefined) {
            errors.push({
                field: 'render',
                message: 'Render method returned null or undefined',
                severity: 'error'
            });
            return;
        }

        // Check for circular references
        try {
            JSON.stringify(rendered);
        } catch (circularError) {
            errors.push({
                field: 'render',
                message: 'Rendered output contains circular references',
                severity: 'error'
            });
        }

        // Validate structure
        this.validateRenderStructure(rendered, errors, warnings);
    }

    /**
     * Validate the structure of rendered output
     */
    private validateRenderStructure(rendered: any, errors: ValidationError[], warnings: ValidationError[], depth: number = 0): void {
        if (depth > 10) {
            warnings.push({
                field: 'render',
                message: 'Render output has very deep nesting',
                severity: 'warning'
            });
            return;
        }

        if (Array.isArray(rendered)) {
            if (rendered.length === 0) {
                warnings.push({
                    field: 'render',
                    message: 'Render method returned empty array',
                    severity: 'warning'
                });
            }

            rendered.forEach((item, index) => {
                this.validateRenderStructure(item, errors, warnings, depth + 1);
            });
        } else if (rendered && typeof rendered === 'object') {
            // Validate object structure
            if (rendered.props) {
                this.validateRenderStructure(rendered.props, errors, warnings, depth + 1);
            }
            if (rendered.children) {
                this.validateRenderStructure(rendered.children, errors, warnings, depth + 1);
            }
        }
    }

    /**
     * Validate props against a simple schema (simplified implementation)
     */
    validatePropsSchema<T>(props: T, requiredProps: string[] = []): ValidationResult {
        const errors: ValidationError[] = [];
        const warnings: ValidationError[] = [];

        // Check required properties
        for (const propName of requiredProps) {
            if (!(propName in (props as any)) || (props as any)[propName] === undefined || (props as any)[propName] === null) {
                errors.push({
                    field: propName,
                    message: `Required property '${propName}' is missing`,
                    severity: 'error'
                });
            }
        }

        return {
            isValid: errors.length === 0,
            errors,
            warnings
        };
    }

    /**
     * Create a validation summary for multiple components
     */
    createValidationSummary(results: ValidationResult[]): {
        totalComponents: number;
        validComponents: number;
        totalErrors: number;
        totalWarnings: number;
        isAllValid: boolean;
    } {
        return {
            totalComponents: results.length,
            validComponents: results.filter(r => r.isValid).length,
            totalErrors: results.reduce((sum, r) => sum + r.errors.length, 0),
            totalWarnings: results.reduce((sum, r) => sum + r.warnings.length, 0),
            isAllValid: results.every(r => r.isValid)
        };
    }
}

export default TsxValidation; 