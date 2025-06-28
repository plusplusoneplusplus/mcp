/**
 * Basic TSX Component Test
 * 
 * This file tests the basic @vscode/prompt-tsx configuration and TSX compilation.
 * It verifies that JSX elements can be created and that the import source is correctly configured.
 */

import {
    BasePromptElementProps,
    PromptElement,
    PromptSizing,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    TextChunk
} from '@vscode/prompt-tsx';

/**
 * Basic test prompt component that demonstrates @vscode/prompt-tsx functionality
 */
export interface BasicTestPromptProps extends BasePromptElementProps {
    userQuery?: string;
    includeInstructions?: boolean;
}

export class BasicTestPrompt extends PromptElement<BasicTestPromptProps> {
    render() {
        return (
            <>
                {this.props.includeInstructions && (
                    <SystemMessage priority={100}>
                        You are Wu Wei, an AI assistant that embodies the philosophy of 无为而治 (wu wei) - effortless action.
                    </SystemMessage>
                )}
                <UserMessage priority={50}>
                    {this.props.userQuery || "This is a basic test to verify @vscode/prompt-tsx configuration."}
                </UserMessage>
            </>
        );
    }
}

/**
 * More complex test component with flexible text handling
 */
export interface TestPromptWithFlexProps extends BasePromptElementProps {
    title?: string;
    instructions?: string;
    userQuery: string;
    contextData?: string;
}

export class TestPromptWithFlex extends PromptElement<TestPromptWithFlexProps> {
    render() {
        const title = this.props.title || "Wu Wei Test Prompt";
        const instructions = this.props.instructions || "Please assist with the following request:";
        
        return (
            <>
                <SystemMessage priority={100}>
                    {title}
                    <br />
                    {instructions}
                </SystemMessage>
                
                {this.props.contextData && (
                    <UserMessage priority={75}>
                        Context information:
                        <br />
                        <TextChunk priority={60} flexGrow={1}>
                            {this.props.contextData}
                        </TextChunk>
                    </UserMessage>
                )}
                
                <UserMessage priority={50}>
                    {this.props.userQuery}
                </UserMessage>
            </>
        );
    }
}

/**
 * Test component that demonstrates async preparation
 */
export interface AsyncTestPromptProps extends BasePromptElementProps {
    userQuery: string;
}

export interface AsyncTestPromptState {
    timestamp: string;
    systemInfo: string;
}

export class AsyncTestPrompt extends PromptElement<AsyncTestPromptProps, AsyncTestPromptState> {
    async prepare(): Promise<AsyncTestPromptState> {
        // Simulate async preparation work
        await new Promise(resolve => setTimeout(resolve, 1));
        
        return {
            timestamp: new Date().toISOString(),
            systemInfo: "Wu Wei VS Code Extension Test Environment"
        };
    }

    render(state: AsyncTestPromptState, sizing: PromptSizing) {
        return (
            <>
                <SystemMessage priority={100}>
                    System: {state.systemInfo}
                    <br />
                    Timestamp: {state.timestamp}
                    <br />
                    Available tokens: {sizing.tokenBudget}
                </SystemMessage>
                <UserMessage priority={50}>
                    {this.props.userQuery}
                </UserMessage>
            </>
        );
    }
}

/**
 * Test function to verify that TSX components can be instantiated
 * This tests basic TypeScript compilation without actually rendering
 */
export function testTsxCompilation(): boolean {
    try {
        // Test basic component - these are just type checks, not actual rendering
        const basicTest = BasicTestPrompt;
        const flexTest = TestPromptWithFlex;
        const asyncTest = AsyncTestPrompt;

        // If we reach here without TypeScript compilation errors, the configuration is working
        console.log('TSX compilation test passed for components:', {
            basic: basicTest.name,
            flex: flexTest.name,
            async: asyncTest.name
        });
        
        return true;
    } catch (error) {
        console.error('TSX compilation test failed:', error);
        return false;
    }
}

/**
 * Export a test configuration object with information about the setup
 */
export const tsxTestConfig = {
    packageName: '@vscode/prompt-tsx',
    version: '^0.4.0-alpha.5',
    jsxFactory: 'vscpp',
    jsxFragmentFactory: 'vscppf',
    testsStatus: 'configured',
    description: 'Basic TSX components for testing prompt-tsx configuration',
    components: {
        BasicTestPrompt: 'Simple system/user message test',
        TestPromptWithFlex: 'Demonstrates flexible text handling and priorities',
        AsyncTestPrompt: 'Shows async preparation with state management'
    }
};
