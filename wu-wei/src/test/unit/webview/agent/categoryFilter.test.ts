/**
 * Unit tests for wu-wei agent panel category filter functionality
 * Tests the category filtering logic for prompt selection
 */

import * as assert from 'assert';

// Mock DOM environment for testing
class MockElement {
    value: string = '';
    innerHTML: string = '';
    style: { [key: string]: string } = {};
    textContent: string = '';
    classList: Set<string> = new Set();

    constructor(public tagName: string = 'div') {}

    querySelector(selector: string): MockElement | null {
        return new MockElement();
    }

    appendChild(child: MockElement): MockElement {
        return child;
    }

    createElement(tagName: string): MockElement {
        return new MockElement(tagName);
    }

    addEventListener(event: string, handler: Function): void {
        // Mock event listener
    }

    setAttribute(name: string, value: string): void {
        // Mock attribute setting
    }

    getAttribute(name: string): string | null {
        return null;
    }
}

// Mock global document
global.document = {
    getElementById: (id: string) => new MockElement(),
    createElement: (tagName: string) => new MockElement(tagName),
    addEventListener: (event: string, handler: Function) => {},
} as any;

// Test data
const mockPrompts = [
    {
        id: 'prompt1',
        title: 'Code Review Helper',
        description: 'Helps with code review tasks',
        category: 'Development',
        tags: ['code', 'review', 'quality'],
        content: 'Please review the following code: {{code}}',
        filePath: '/dev/code-review.md',
        fileName: 'code-review.md',
        lastModified: new Date(),
        isValid: true
    },
    {
        id: 'prompt2',
        title: 'Bug Report Template',
        description: 'Template for bug reports',
        category: 'Development', 
        tags: ['bug', 'issue', 'template'],
        content: 'Bug: {{title}}\nDescription: {{description}}',
        filePath: '/dev/bug-report.md',
        fileName: 'bug-report.md',
        lastModified: new Date(),
        isValid: true
    },
    {
        id: 'prompt3',
        title: 'Meeting Notes',
        description: 'Template for meeting notes',
        category: 'Documentation',
        tags: ['meeting', 'notes', 'template'],
        content: 'Meeting: {{title}}\nAttendees: {{attendees}}',
        filePath: '/docs/meeting-notes.md',
        fileName: 'meeting-notes.md',
        lastModified: new Date(),
        isValid: true
    },
    {
        id: 'prompt4',
        title: 'Project Planning',
        description: 'Template for project planning',
        category: 'Planning',
        tags: ['project', 'planning', 'roadmap'],
        content: 'Project: {{name}}\nGoals: {{goals}}',
        filePath: '/planning/project.md',
        fileName: 'project.md',
        lastModified: new Date(),
        isValid: true
    },
    {
        id: 'prompt5',
        title: 'Uncategorized Prompt',
        description: 'A prompt without category',
        category: '',
        tags: ['misc'],
        content: 'General purpose prompt: {{content}}',
        filePath: '/misc/general.md',
        fileName: 'general.md',
        lastModified: new Date(),
        isValid: true
    }
];

// Import and test the functions - we'll need to adapt the actual functions for testing
suite('Agent Panel Category Filter Tests', () => {

    suite('Category Discovery and Management', () => {
        test('getAvailableCategories extracts unique categories', () => {
            // Implementation of getAvailableCategories for testing
            function getAvailableCategories(prompts: typeof mockPrompts) {
                const categories = new Set<string>();
                prompts.forEach(prompt => {
                    if (prompt.category && prompt.category.trim()) {
                        categories.add(prompt.category.trim());
                    }
                });
                return Array.from(categories).sort();
            }

            const categories = getAvailableCategories(mockPrompts);
            assert.deepStrictEqual(categories, ['Development', 'Documentation', 'Planning']);
        });

        test('getAvailableCategories handles empty and undefined categories', () => {
            function getAvailableCategories(prompts: typeof mockPrompts) {
                const categories = new Set<string>();
                prompts.forEach(prompt => {
                    if (prompt.category && prompt.category.trim()) {
                        categories.add(prompt.category.trim());
                    }
                });
                return Array.from(categories).sort();
            }

            const promptsWithEmptyCategories = [
                { ...mockPrompts[0] },
                { ...mockPrompts[1], category: '' },
                { ...mockPrompts[2], category: '   ' }, // whitespace only
                { ...mockPrompts[3], category: undefined as any }
            ];

            const categories = getAvailableCategories(promptsWithEmptyCategories);
            assert.deepStrictEqual(categories, ['Development']);
        });

        test('getAvailableCategories handles duplicate categories', () => {
            function getAvailableCategories(prompts: typeof mockPrompts) {
                const categories = new Set<string>();
                prompts.forEach(prompt => {
                    if (prompt.category && prompt.category.trim()) {
                        categories.add(prompt.category.trim());
                    }
                });
                return Array.from(categories).sort();
            }

            const promptsWithDuplicates = [
                { ...mockPrompts[0], category: 'Development' },
                { ...mockPrompts[1], category: 'Development' },
                { ...mockPrompts[2], category: 'Development' },
            ];

            const categories = getAvailableCategories(promptsWithDuplicates);
            assert.deepStrictEqual(categories, ['Development']);
        });
    });

    suite('Prompt Grouping by Category', () => {
        test('groupPromptsByCategory creates correct groups', () => {
            function groupPromptsByCategory(prompts: typeof mockPrompts) {
                const grouped: { [key: string]: typeof prompts } = {};
                prompts.forEach(prompt => {
                    const category = prompt.category || 'Uncategorized';
                    if (!grouped[category]) {
                        grouped[category] = [];
                    }
                    grouped[category].push(prompt);
                });

                // Sort prompts within each category by title
                Object.keys(grouped).forEach(category => {
                    grouped[category].sort((a, b) => a.title.localeCompare(b.title));
                });

                return grouped;
            }

            const grouped = groupPromptsByCategory(mockPrompts);

            assert.strictEqual(Object.keys(grouped).length, 4);
            assert.ok(grouped['Development']);
            assert.ok(grouped['Documentation']);
            assert.ok(grouped['Planning']);
            assert.ok(grouped['Uncategorized']);

            assert.strictEqual(grouped['Development'].length, 2);
            assert.strictEqual(grouped['Documentation'].length, 1);
            assert.strictEqual(grouped['Planning'].length, 1);
            assert.strictEqual(grouped['Uncategorized'].length, 1);

            // Test sorting within categories
            assert.strictEqual(grouped['Development'][0].title, 'Bug Report Template');
            assert.strictEqual(grouped['Development'][1].title, 'Code Review Helper');
        });

        test('groupPromptsByCategory handles empty prompts array', () => {
            function groupPromptsByCategory(prompts: typeof mockPrompts) {
                const grouped: { [key: string]: typeof prompts } = {};
                prompts.forEach(prompt => {
                    const category = prompt.category || 'Uncategorized';
                    if (!grouped[category]) {
                        grouped[category] = [];
                    }
                    grouped[category].push(prompt);
                });
                return grouped;
            }

            const grouped = groupPromptsByCategory([]);
            assert.deepStrictEqual(grouped, {});
        });
    });

    suite('Prompt Filtering Logic', () => {
        test('handlePromptFiltering filters by category only', () => {
            function filterPrompts(prompts: typeof mockPrompts, searchQuery: string, selectedCategory: string) {
                return prompts.filter(prompt => {
                    // Category filter
                    const categoryMatch = !selectedCategory || prompt.category === selectedCategory;
                    
                    // Search filter
                    const searchMatch = !searchQuery || 
                        prompt.title.toLowerCase().includes(searchQuery) ||
                        (prompt.description && prompt.description.toLowerCase().includes(searchQuery)) ||
                        (prompt.category && prompt.category.toLowerCase().includes(searchQuery)) ||
                        (prompt.tags && prompt.tags.some(tag => tag.toLowerCase().includes(searchQuery)));

                    return categoryMatch && searchMatch;
                });
            }

            // Filter by Development category
            const devPrompts = filterPrompts(mockPrompts, '', 'Development');
            assert.strictEqual(devPrompts.length, 2);
            assert.ok(devPrompts.every(p => p.category === 'Development'));

            // Filter by Documentation category
            const docPrompts = filterPrompts(mockPrompts, '', 'Documentation');
            assert.strictEqual(docPrompts.length, 1);
            assert.strictEqual(docPrompts[0].category, 'Documentation');

            // Filter by non-existent category
            const noPrompts = filterPrompts(mockPrompts, '', 'NonExistent');
            assert.strictEqual(noPrompts.length, 0);
        });

        test('handlePromptFiltering filters by search query only', () => {
            function filterPrompts(prompts: typeof mockPrompts, searchQuery: string, selectedCategory: string) {
                return prompts.filter(prompt => {
                    const categoryMatch = !selectedCategory || prompt.category === selectedCategory;
                    const searchMatch = !searchQuery || 
                        prompt.title.toLowerCase().includes(searchQuery) ||
                        (prompt.description && prompt.description.toLowerCase().includes(searchQuery)) ||
                        (prompt.category && prompt.category.toLowerCase().includes(searchQuery)) ||
                        (prompt.tags && prompt.tags.some(tag => tag.toLowerCase().includes(searchQuery)));

                    return categoryMatch && searchMatch;
                });
            }

            // Search for "template"
            const templatePrompts = filterPrompts(mockPrompts, 'template', '');
            assert.strictEqual(templatePrompts.length, 3);
            assert.ok(templatePrompts.every(p => 
                p.title.toLowerCase().includes('template') ||
                p.description?.toLowerCase().includes('template') ||
                p.tags?.some(tag => tag.toLowerCase().includes('template'))
            ));

            // Search for "code"
            const codePrompts = filterPrompts(mockPrompts, 'code', '');
            assert.strictEqual(codePrompts.length, 1);
            assert.strictEqual(codePrompts[0].title, 'Code Review Helper');

            // Search for non-existent term
            const noPrompts = filterPrompts(mockPrompts, 'nonexistent', '');
            assert.strictEqual(noPrompts.length, 0);
        });

        test('handlePromptFiltering combines category and search filters', () => {
            function filterPrompts(prompts: typeof mockPrompts, searchQuery: string, selectedCategory: string) {
                return prompts.filter(prompt => {
                    const categoryMatch = !selectedCategory || prompt.category === selectedCategory;
                    const searchMatch = !searchQuery || 
                        prompt.title.toLowerCase().includes(searchQuery) ||
                        (prompt.description && prompt.description.toLowerCase().includes(searchQuery)) ||
                        (prompt.category && prompt.category.toLowerCase().includes(searchQuery)) ||
                        (prompt.tags && prompt.tags.some(tag => tag.toLowerCase().includes(searchQuery)));

                    return categoryMatch && searchMatch;
                });
            }

            // Search for "template" in Development category
            const devTemplates = filterPrompts(mockPrompts, 'template', 'Development');
            assert.strictEqual(devTemplates.length, 1);
            assert.strictEqual(devTemplates[0].title, 'Bug Report Template');
            assert.strictEqual(devTemplates[0].category, 'Development');

            // Search for "code" in Documentation category (should be empty)
            const docCode = filterPrompts(mockPrompts, 'code', 'Documentation');
            assert.strictEqual(docCode.length, 0);

            // Search for "planning" in Planning category  
            const planningItems = filterPrompts(mockPrompts, 'planning', 'Planning');
            assert.strictEqual(planningItems.length, 1);
        });

        test('handlePromptFiltering case insensitive search', () => {
            function filterPrompts(prompts: typeof mockPrompts, searchQuery: string, selectedCategory: string) {
                return prompts.filter(prompt => {
                    const categoryMatch = !selectedCategory || prompt.category === selectedCategory;
                    const searchMatch = !searchQuery || 
                        prompt.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        (prompt.description && prompt.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
                        (prompt.category && prompt.category.toLowerCase().includes(searchQuery.toLowerCase())) ||
                        (prompt.tags && prompt.tags.some((tag: string) => tag.toLowerCase().includes(searchQuery.toLowerCase())));

                    return categoryMatch && searchMatch;
                });
            }

            // Test different cases
            const upperCase = filterPrompts(mockPrompts, 'CODE', '');
            const lowerCase = filterPrompts(mockPrompts, 'code', '');
            const mixedCase = filterPrompts(mockPrompts, 'CoDe', '');

            assert.strictEqual(upperCase.length, 1);
            assert.strictEqual(lowerCase.length, 1);
            assert.strictEqual(mixedCase.length, 1);
            assert.strictEqual(upperCase[0].id, lowerCase[0].id);
            assert.strictEqual(lowerCase[0].id, mixedCase[0].id);
        });
    });

    suite('Filter Status and UI Updates', () => {
        test('updateFilterStatus generates correct count and filter text', () => {
            function updateFilterStatus(count: number, searchQuery: string, selectedCategory: string) {
                const status = {
                    countText: `${count} prompt${count !== 1 ? 's' : ''} available`,
                    hasActiveFilters: Boolean(searchQuery || selectedCategory),
                    filterText: ''
                };

                if (status.hasActiveFilters) {
                    let filterText = '';
                    if (searchQuery) {
                        filterText += `search: "${searchQuery}"`;
                    }
                    if (selectedCategory) {
                        filterText += (filterText ? ', ' : '') + `category: "${selectedCategory}"`;
                    }
                    status.countText += ` (filtered by ${filterText})`;
                    status.filterText = filterText;
                }

                return status;
            }

            // No filters
            let status = updateFilterStatus(5, '', '');
            assert.strictEqual(status.countText, '5 prompts available');
            assert.strictEqual(status.hasActiveFilters, false);

            // Single prompt
            status = updateFilterStatus(1, '', '');
            assert.strictEqual(status.countText, '1 prompt available');

            // Search filter only
            status = updateFilterStatus(2, 'template', '');
            assert.strictEqual(status.countText, '2 prompts available (filtered by search: "template")');
            assert.strictEqual(status.hasActiveFilters, true);

            // Category filter only
            status = updateFilterStatus(3, '', 'Development');
            assert.strictEqual(status.countText, '3 prompts available (filtered by category: "Development")');
            assert.strictEqual(status.hasActiveFilters, true);

            // Both filters
            status = updateFilterStatus(1, 'code', 'Development');
            assert.strictEqual(status.countText, '1 prompt available (filtered by search: "code", category: "Development")');
            assert.strictEqual(status.hasActiveFilters, true);

            // No results
            status = updateFilterStatus(0, 'nonexistent', '');
            assert.strictEqual(status.countText, '0 prompts available (filtered by search: "nonexistent")');
        });
    });

    suite('Clear Filters Functionality', () => {
        test('clearAllFilters resets search and category', () => {
            // Mock the filter state
            let searchValue = 'test search';
            let categoryValue = 'Development';

            function clearAllFilters() {
                searchValue = '';
                categoryValue = '';
                return { searchValue, categoryValue };
            }

            const result = clearAllFilters();
            assert.strictEqual(result.searchValue, '');
            assert.strictEqual(result.categoryValue, '');
        });
    });

    suite('Integration Tests', () => {
        test('Full filtering workflow', () => {
            // Simulate the complete filtering workflow
            function fullWorkflow(prompts: typeof mockPrompts, searchQuery: string, selectedCategory: string) {
                // 1. Filter prompts
                const filteredPrompts = prompts.filter(prompt => {
                    const categoryMatch = !selectedCategory || prompt.category === selectedCategory;
                    const searchMatch = !searchQuery || 
                        prompt.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        (prompt.description && prompt.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
                        (prompt.category && prompt.category.toLowerCase().includes(searchQuery.toLowerCase())) ||
                        (prompt.tags && prompt.tags.some((tag: string) => tag.toLowerCase().includes(searchQuery.toLowerCase())));
                    return categoryMatch && searchMatch;
                });

                // 2. Group by category
                const grouped: { [key: string]: typeof filteredPrompts } = {};
                filteredPrompts.forEach(prompt => {
                    const category = prompt.category || 'Uncategorized';
                    if (!grouped[category]) {
                        grouped[category] = [];
                    }
                    grouped[category].push(prompt);
                });

                // 3. Sort within groups
                Object.keys(grouped).forEach(category => {
                    grouped[category].sort((a, b) => a.title.localeCompare(b.title));
                });

                // 4. Generate status
                const hasActiveFilters = Boolean(searchQuery || selectedCategory);
                let statusText = `${filteredPrompts.length} prompt${filteredPrompts.length !== 1 ? 's' : ''} available`;
                if (hasActiveFilters) {
                    let filterText = '';
                    if (searchQuery) filterText += `search: "${searchQuery}"`;
                    if (selectedCategory) filterText += (filterText ? ', ' : '') + `category: "${selectedCategory}"`;
                    statusText += ` (filtered by ${filterText})`;
                }

                return {
                    filteredPrompts,
                    grouped,
                    statusText,
                    hasActiveFilters
                };
            }

            // Test case 1: Filter Development category with "template" search
            const result1 = fullWorkflow(mockPrompts, 'template', 'Development');
            assert.strictEqual(result1.filteredPrompts.length, 1);
            assert.strictEqual(result1.filteredPrompts[0].title, 'Bug Report Template');
            assert.strictEqual(result1.statusText, '1 prompt available (filtered by search: "template", category: "Development")');
            assert.strictEqual(result1.hasActiveFilters, true);

            // Test case 2: No filters
            const result2 = fullWorkflow(mockPrompts, '', '');
            assert.strictEqual(result2.filteredPrompts.length, 5);
            assert.strictEqual(Object.keys(result2.grouped).length, 4);
            assert.strictEqual(result2.statusText, '5 prompts available');
            assert.strictEqual(result2.hasActiveFilters, false);

            // Test case 3: Category filter only
            const result3 = fullWorkflow(mockPrompts, '', 'Documentation');
            assert.strictEqual(result3.filteredPrompts.length, 1);
            assert.strictEqual(result3.filteredPrompts[0].category, 'Documentation');
            assert.strictEqual(result3.statusText, '1 prompt available (filtered by category: "Documentation")');
        });
    });

    suite('Edge Cases and Error Handling', () => {
        test('Filtering with null/undefined values', () => {
            const promptsWithNulls = [
                { ...mockPrompts[0], category: null as any, tags: null as any },
                { ...mockPrompts[1], description: undefined as any },
                { ...mockPrompts[2] }
            ];

            function filterPrompts(prompts: any[], searchQuery: string, selectedCategory: string) {
                return prompts.filter(prompt => {
                    const categoryMatch = !selectedCategory || prompt.category === selectedCategory;
                    const searchMatch = !searchQuery || 
                        (prompt.title && prompt.title.toLowerCase().includes(searchQuery.toLowerCase())) ||
                        (prompt.description && prompt.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
                        (prompt.category && prompt.category.toLowerCase().includes(searchQuery.toLowerCase())) ||
                        (prompt.tags && Array.isArray(prompt.tags) && prompt.tags.some((tag: any) => tag && tag.toLowerCase().includes(searchQuery.toLowerCase())));
                    return categoryMatch && searchMatch;
                });
            }

            // Should not throw errors
            const result = filterPrompts(promptsWithNulls, 'template', '');
            assert.ok(Array.isArray(result));
        });

        test('Empty search query and category handling', () => {
            function filterPrompts(prompts: typeof mockPrompts, searchQuery: string, selectedCategory: string) {
                // Handle empty/whitespace strings
                const cleanSearchQuery = searchQuery?.trim() || '';
                const cleanCategory = selectedCategory?.trim() || '';

                return prompts.filter(prompt => {
                    const categoryMatch = !cleanCategory || prompt.category === cleanCategory;
                    const searchMatch = !cleanSearchQuery || 
                        prompt.title.toLowerCase().includes(cleanSearchQuery.toLowerCase());
                    return categoryMatch && searchMatch;
                });
            }

            // Test with whitespace-only strings
            const result1 = filterPrompts(mockPrompts, '   ', '   ');
            assert.strictEqual(result1.length, 5); // Should return all prompts

            // Test with empty strings
            const result2 = filterPrompts(mockPrompts, '', '');
            assert.strictEqual(result2.length, 5);
        });
    });
});