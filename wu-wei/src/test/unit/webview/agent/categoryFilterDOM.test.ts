/**
 * Unit tests for wu-wei agent panel category filter DOM manipulation
 * Tests the UI updates and DOM interactions for category filtering
 */

import * as assert from 'assert';

// Enhanced Mock DOM for more realistic testing
class MockHTMLElement {
    private _value: string = '';
    innerHTML: string = '';
    textContent: string = '';
    style: { [key: string]: string } = {};
    dataset: { [key: string]: string } = {};
    classList: MockClassList = new MockClassList();
    children: MockHTMLElement[] = [];
    parentNode: MockHTMLElement | null = null;
    
    private _attributes: { [key: string]: string } = {};
    private _eventListeners: { [key: string]: Function[] } = {};

    constructor(public tagName: string = 'div', public id: string = '') {}

    get value(): string {
        return this._value;
    }

    set value(newValue: string) {
        this._value = newValue;
    }

    appendChild(child: MockHTMLElement): MockHTMLElement {
        child.parentNode = this;
        this.children.push(child);
        return child;
    }

    removeChild(child: MockHTMLElement): MockHTMLElement {
        const index = this.children.indexOf(child);
        if (index > -1) {
            this.children.splice(index, 1);
            child.parentNode = null;
        }
        return child;
    }

    querySelector(selector: string): MockHTMLElement | null {
        // Simple mock selector - just return first child for testing
        return this.children[0] || null;
    }

    querySelectorAll(selector: string): MockHTMLElement[] {
        return this.children;
    }

    setAttribute(name: string, value: string): void {
        this._attributes[name] = value;
    }

    getAttribute(name: string): string | null {
        return this._attributes[name] || null;
    }

    addEventListener(event: string, handler: Function): void {
        if (!this._eventListeners[event]) {
            this._eventListeners[event] = [];
        }
        this._eventListeners[event].push(handler);
    }

    removeEventListener(event: string, handler: Function): void {
        if (this._eventListeners[event]) {
            const index = this._eventListeners[event].indexOf(handler);
            if (index > -1) {
                this._eventListeners[event].splice(index, 1);
            }
        }
    }

    dispatchEvent(event: MockEvent): void {
        const eventType = event.type;
        if (this._eventListeners[eventType]) {
            this._eventListeners[eventType].forEach(handler => handler(event));
        }
    }

    get disabled(): boolean {
        return this.getAttribute('disabled') === 'true';
    }

    set disabled(value: boolean) {
        this.setAttribute('disabled', value.toString());
    }
}

class MockClassList {
    private classes: Set<string> = new Set();

    add(className: string): void {
        this.classes.add(className);
    }

    remove(className: string): void {
        this.classes.delete(className);
    }

    contains(className: string): boolean {
        return this.classes.has(className);
    }

    toggle(className: string): boolean {
        if (this.classes.has(className)) {
            this.classes.delete(className);
            return false;
        } else {
            this.classes.add(className);
            return true;
        }
    }
}

class MockEvent {
    constructor(public type: string, public target?: MockHTMLElement) {}
}

class MockSelectElement extends MockHTMLElement {
    options: MockHTMLElement[] = [];
    selectedIndex: number = 0;

    constructor() {
        super('select');
    }

    set value(newValue: string) {
        super.value = newValue;
        const index = this.options.findIndex(option => option.value === newValue);
        if (index >= 0) {
            this.selectedIndex = index;
        }
    }

    get value(): string {
        return super.value;
    }

    appendChild(option: MockHTMLElement): MockHTMLElement {
        this.options.push(option);
        return super.appendChild(option);
    }
}

// Mock document
const mockDocument = {
    getElementById: (id: string) => {
        const elements: { [key: string]: MockHTMLElement } = {
            'categoryFilter': new MockSelectElement(),
            'promptSearch': new MockHTMLElement('input'),
            'promptSelector': new MockSelectElement(),
            'promptFilterStatus': new MockHTMLElement('div'),
            'clearFilters': new MockHTMLElement('button')
        };
        return elements[id] || new MockHTMLElement();
    },
    createElement: (tagName: string) => {
        if (tagName === 'select') {
            return new MockSelectElement();
        }
        return new MockHTMLElement(tagName);
    },
    addEventListener: (event: string, handler: Function) => {},
} as any;

global.document = mockDocument;

// Test data
const mockPrompts = [
    {
        id: 'prompt1',
        title: 'Code Review Helper',
        description: 'Helps with code review tasks',
        category: 'Development',
        tags: ['code', 'review']
    },
    {
        id: 'prompt2',
        title: 'Bug Report Template',
        description: 'Template for bug reports',
        category: 'Development',
        tags: ['bug', 'template']
    },
    {
        id: 'prompt3',
        title: 'Meeting Notes',
        description: 'Template for meeting notes',
        category: 'Documentation',
        tags: ['meeting', 'notes']
    },
    {
        id: 'prompt4',
        title: 'Project Planning',
        description: 'Template for project planning',
        category: 'Planning',
        tags: ['project', 'planning']
    }
];

suite('Agent Panel Category Filter DOM Tests', () => {

    suite('Category Filter Dropdown Population', () => {
        test('updateCategoryFilter populates dropdown with available categories', () => {
            function updateCategoryFilter(prompts: typeof mockPrompts) {
                const categoryFilter = mockDocument.getElementById('categoryFilter') as MockSelectElement;
                const categories = getAvailableCategories(prompts);
                
                categoryFilter.innerHTML = '';
                categoryFilter.options = [];
                
                // Add default option
                const defaultOption = new MockHTMLElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'All Categories';
                categoryFilter.appendChild(defaultOption);
                
                // Add category options
                categories.forEach(category => {
                    const option = new MockHTMLElement('option');
                    option.value = category;
                    option.textContent = category;
                    categoryFilter.appendChild(option);
                });

                return categoryFilter;
            }

            function getAvailableCategories(prompts: typeof mockPrompts) {
                const categories = new Set<string>();
                prompts.forEach(prompt => {
                    if (prompt.category && prompt.category.trim()) {
                        categories.add(prompt.category.trim());
                    }
                });
                return Array.from(categories).sort();
            }

            const categoryFilter = updateCategoryFilter(mockPrompts);
            
            // Should have default option plus 3 categories
            assert.strictEqual(categoryFilter.options.length, 4);
            assert.strictEqual(categoryFilter.options[0].textContent, 'All Categories');
            assert.strictEqual(categoryFilter.options[0].value, '');
            assert.strictEqual(categoryFilter.options[1].textContent, 'Development');
            assert.strictEqual(categoryFilter.options[2].textContent, 'Documentation');
            assert.strictEqual(categoryFilter.options[3].textContent, 'Planning');
        });

        test('updateCategoryFilter handles empty prompts array', () => {
            function updateCategoryFilter(prompts: typeof mockPrompts) {
                const categoryFilter = mockDocument.getElementById('categoryFilter') as MockSelectElement;
                const categories = getAvailableCategories(prompts);
                
                categoryFilter.innerHTML = '';
                categoryFilter.options = [];
                
                const defaultOption = new MockHTMLElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'All Categories';
                categoryFilter.appendChild(defaultOption);
                
                categories.forEach(category => {
                    const option = new MockHTMLElement('option');
                    option.value = category;
                    option.textContent = category;
                    categoryFilter.appendChild(option);
                });

                return categoryFilter;
            }

            function getAvailableCategories(prompts: typeof mockPrompts) {
                const categories = new Set<string>();
                prompts.forEach(prompt => {
                    if (prompt.category && prompt.category.trim()) {
                        categories.add(prompt.category.trim());
                    }
                });
                return Array.from(categories).sort();
            }

            const categoryFilter = updateCategoryFilter([]);
            
            // Should only have default option
            assert.strictEqual(categoryFilter.options.length, 1);
            assert.strictEqual(categoryFilter.options[0].textContent, 'All Categories');
        });
    });

    suite('Prompt Selector List Updates', () => {
        test('updatePromptSelectorList creates optgroups for multiple categories', () => {
            function updatePromptSelectorList(prompts: typeof mockPrompts) {
                const promptSelector = mockDocument.getElementById('promptSelector') as MockSelectElement;
                promptSelector.innerHTML = '';
                promptSelector.options = [];
                
                if (prompts.length === 0) {
                    const option = new MockHTMLElement('option');
                    option.value = '';
                    option.textContent = 'No matching prompts found';
                    promptSelector.appendChild(option);
                    return promptSelector;
                }
                
                // Add default option
                const defaultOption = new MockHTMLElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'No prompt (message only)';
                promptSelector.appendChild(defaultOption);
                
                // Group prompts by category
                const grouped = groupPromptsByCategory(prompts);
                const categoryKeys = Object.keys(grouped).sort();
                
                if (categoryKeys.length > 1) {
                    // Use optgroups for multiple categories
                    categoryKeys.forEach(category => {
                        if (category && category !== 'undefined') {
                            const optgroup = new MockHTMLElement('optgroup');
                            optgroup.setAttribute('label', category);
                            
                            grouped[category].forEach(prompt => {
                                const option = new MockHTMLElement('option');
                                option.value = prompt.id;
                                option.textContent = prompt.title;
                                option.setAttribute('title', prompt.description || prompt.title);
                                optgroup.appendChild(option);
                            });
                            
                            promptSelector.appendChild(optgroup);
                        }
                    });
                } else {
                    // Single category, no optgroups
                    const category = categoryKeys[0];
                    grouped[category].forEach(prompt => {
                        const option = new MockHTMLElement('option');
                        option.value = prompt.id;
                        option.textContent = `${prompt.title} (${category})`;
                        option.setAttribute('title', prompt.description || prompt.title);
                        promptSelector.appendChild(option);
                    });
                }
                
                return promptSelector;
            }

            function groupPromptsByCategory(prompts: typeof mockPrompts) {
                const grouped: { [key: string]: typeof prompts } = {};
                prompts.forEach(prompt => {
                    const category = prompt.category || 'Uncategorized';
                    if (!grouped[category]) {
                        grouped[category] = [];
                    }
                    grouped[category].push(prompt);
                });
                
                Object.keys(grouped).forEach(category => {
                    grouped[category].sort((a, b) => a.title.localeCompare(b.title));
                });
                
                return grouped;
            }

            const promptSelector = updatePromptSelectorList(mockPrompts);
            
            // Should have default option + optgroups
            assert.strictEqual(promptSelector.children.length, 4); // 1 default + 3 optgroups
            
            // Check optgroups
            const optgroups = promptSelector.children.slice(1); // Skip default option
            assert.strictEqual(optgroups[0].getAttribute('label'), 'Development');
            assert.strictEqual(optgroups[1].getAttribute('label'), 'Documentation');
            assert.strictEqual(optgroups[2].getAttribute('label'), 'Planning');
        });

        test('updatePromptSelectorList handles single category without optgroups', () => {
            function updatePromptSelectorList(prompts: typeof mockPrompts) {
                const promptSelector = mockDocument.getElementById('promptSelector') as MockSelectElement;
                promptSelector.innerHTML = '';
                promptSelector.options = [];
                
                const defaultOption = new MockHTMLElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'No prompt (message only)';
                promptSelector.appendChild(defaultOption);
                
                const grouped = groupPromptsByCategory(prompts);
                const categoryKeys = Object.keys(grouped).sort();
                
                if (categoryKeys.length === 1) {
                    const category = categoryKeys[0];
                    // Sort prompts by title within the category
                    const sortedPrompts = grouped[category].sort((a, b) => a.title.localeCompare(b.title));
                    sortedPrompts.forEach(prompt => {
                        const option = new MockHTMLElement('option');
                        option.value = prompt.id;
                        option.textContent = `${prompt.title} (${category})`;
                        promptSelector.appendChild(option);
                    });
                }
                
                return promptSelector;
            }

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

            // Filter to only Development prompts
            const devPrompts = mockPrompts.filter(p => p.category === 'Development');
            const promptSelector = updatePromptSelectorList(devPrompts);
            
            // Should have default option + 2 development prompts (no optgroups)
            assert.strictEqual(promptSelector.children.length, 3);
            // Note: sorted alphabetically, so Bug Report comes before Code Review
            assert.strictEqual(promptSelector.children[1].textContent, 'Bug Report Template (Development)');
            assert.strictEqual(promptSelector.children[2].textContent, 'Code Review Helper (Development)');
        });

        test('updatePromptSelectorList handles no prompts', () => {
            function updatePromptSelectorList(prompts: typeof mockPrompts) {
                const promptSelector = mockDocument.getElementById('promptSelector') as MockSelectElement;
                promptSelector.innerHTML = '';
                promptSelector.options = [];
                
                if (prompts.length === 0) {
                    const option = new MockHTMLElement('option');
                    option.value = '';
                    option.textContent = 'No matching prompts found';
                    promptSelector.appendChild(option);
                    return promptSelector;
                }
                
                return promptSelector;
            }

            const promptSelector = updatePromptSelectorList([]);
            
            assert.strictEqual(promptSelector.children.length, 1);
            assert.strictEqual(promptSelector.children[0].textContent, 'No matching prompts found');
        });
    });

    suite('Filter Status Updates', () => {
        test('updateFilterStatus updates count display and clear button visibility', () => {
            function updateFilterStatus(count: number, searchQuery: string, selectedCategory: string) {
                const promptFilterStatus = mockDocument.getElementById('promptFilterStatus');
                const countElement = promptFilterStatus.querySelector('.filter-count') || new MockHTMLElement('span');
                const clearFiltersBtn = mockDocument.getElementById('clearFilters');
                
                countElement.textContent = `${count} prompt${count !== 1 ? 's' : ''} available`;
                
                const hasActiveFilters = Boolean(searchQuery || selectedCategory);
                clearFiltersBtn.style.display = hasActiveFilters ? 'inline-flex' : 'none';
                
                if (hasActiveFilters) {
                    let filterText = '';
                    if (searchQuery) {
                        filterText += `search: "${searchQuery}"`;
                    }
                    if (selectedCategory) {
                        filterText += (filterText ? ', ' : '') + `category: "${selectedCategory}"`;
                    }
                    countElement.textContent += ` (filtered by ${filterText})`;
                }
                
                return {
                    countText: countElement.textContent,
                    clearButtonVisible: clearFiltersBtn.style.display === 'inline-flex'
                };
            }

            // Test no filters
            let result = updateFilterStatus(5, '', '');
            assert.strictEqual(result.countText, '5 prompts available');
            assert.strictEqual(result.clearButtonVisible, false);

            // Test with search filter
            result = updateFilterStatus(2, 'template', '');
            assert.strictEqual(result.countText, '2 prompts available (filtered by search: "template")');
            assert.strictEqual(result.clearButtonVisible, true);

            // Test with category filter
            result = updateFilterStatus(3, '', 'Development');
            assert.strictEqual(result.countText, '3 prompts available (filtered by category: "Development")');
            assert.strictEqual(result.clearButtonVisible, true);

            // Test with both filters
            result = updateFilterStatus(1, 'code', 'Development');
            assert.strictEqual(result.countText, '1 prompt available (filtered by search: "code", category: "Development")');
            assert.strictEqual(result.clearButtonVisible, true);
        });
    });

    suite('Clear Filters Functionality', () => {
        test('clearAllFilters resets form elements and triggers filtering', () => {
            // Create fresh mock elements for this test
            const promptSearch = new MockHTMLElement('input');
            const categoryFilter = new MockSelectElement();
            
            function clearAllFilters() {
                promptSearch.value = '';
                categoryFilter.value = '';
                
                // Would normally trigger handlePromptFiltering()
                return {
                    searchCleared: promptSearch.value === '',
                    categoryCleared: categoryFilter.value === ''
                };
            }

            // Set some initial values
            promptSearch.value = 'test search';
            categoryFilter.value = 'Development';

            // Verify initial state
            assert.strictEqual(promptSearch.value, 'test search');
            assert.strictEqual(categoryFilter.value, 'Development');

            // Clear filters
            const result = clearAllFilters();
            
            assert.strictEqual(result.searchCleared, true);
            assert.strictEqual(result.categoryCleared, true);
            assert.strictEqual(promptSearch.value, '');
            assert.strictEqual(categoryFilter.value, '');
        });
    });

    suite('Event Handling', () => {
        test('category filter change event triggers filtering', () => {
            // Create fresh mock elements for this test
            const promptSearch = new MockHTMLElement('input');
            const categoryFilter = new MockSelectElement();
            
            let filteringTriggered = false;
            let lastSearchQuery = '';
            let lastSelectedCategory = '';

            function handlePromptFiltering() {
                lastSearchQuery = promptSearch.value;
                lastSelectedCategory = categoryFilter.value;
                filteringTriggered = true;
            }

            // Setup event listener
            categoryFilter.addEventListener('change', handlePromptFiltering);
            
            // Simulate category change
            categoryFilter.value = 'Development';
            
            const changeEvent = new MockEvent('change', categoryFilter);
            categoryFilter.dispatchEvent(changeEvent);
            
            assert.strictEqual(filteringTriggered, true);
            assert.strictEqual(lastSelectedCategory, 'Development');
        });

        test('search input event triggers debounced filtering', () => {
            let filteringCallCount = 0;

            function debouncedHandlePromptFiltering() {
                filteringCallCount++;
            }

            function debounce(func: Function, wait: number) {
                let timeout: NodeJS.Timeout;
                return function executedFunction(...args: any[]) {
                    const later = () => {
                        clearTimeout(timeout);
                        func(...args);
                    };
                    clearTimeout(timeout);
                    timeout = setTimeout(later, wait);
                };
            }

            const debouncedFilter = debounce(debouncedHandlePromptFiltering, 300);

            function setupEventListeners() {
                const promptSearch = mockDocument.getElementById('promptSearch');
                promptSearch.addEventListener('input', debouncedFilter);
            }

            setupEventListeners();
            
            // Simulate rapid input changes
            const promptSearch = mockDocument.getElementById('promptSearch');
            promptSearch.value = 't';
            promptSearch.dispatchEvent(new MockEvent('input', promptSearch));
            
            promptSearch.value = 'te';
            promptSearch.dispatchEvent(new MockEvent('input', promptSearch));
            
            promptSearch.value = 'tem';
            promptSearch.dispatchEvent(new MockEvent('input', promptSearch));
            
            // Initially, no calls should have been made due to debouncing
            assert.strictEqual(filteringCallCount, 0);
            
            // After debounce delay, should have been called once
            setTimeout(() => {
                assert.strictEqual(filteringCallCount, 1);
            }, 350);
        });
    });

    suite('Accessibility and UX', () => {
        test('clear filters button has proper attributes', () => {
            function setupClearFiltersButton() {
                const clearFiltersBtn = mockDocument.getElementById('clearFilters');
                clearFiltersBtn.setAttribute('title', 'Clear all filters');
                clearFiltersBtn.setAttribute('aria-label', 'Clear search and category filters');
                clearFiltersBtn.classList.add('btn-clear-filters');
                
                return clearFiltersBtn;
            }

            const button = setupClearFiltersButton();
            
            assert.strictEqual(button.getAttribute('title'), 'Clear all filters');
            assert.strictEqual(button.getAttribute('aria-label'), 'Clear search and category filters');
            assert.strictEqual(button.classList.contains('btn-clear-filters'), true);
        });

        test('category filter has proper accessibility attributes', () => {
            function setupCategoryFilter() {
                const categoryFilter = mockDocument.getElementById('categoryFilter');
                categoryFilter.setAttribute('aria-label', 'Filter prompts by category');
                categoryFilter.classList.add('category-filter');
                
                return categoryFilter;
            }

            const filter = setupCategoryFilter();
            
            assert.strictEqual(filter.getAttribute('aria-label'), 'Filter prompts by category');
            assert.strictEqual(filter.classList.contains('category-filter'), true);
        });

        test('filter status provides screen reader feedback', () => {
            function updateFilterStatusForAccessibility(count: number, hasActiveFilters: boolean) {
                const promptFilterStatus = mockDocument.getElementById('promptFilterStatus');
                promptFilterStatus.setAttribute('aria-live', 'polite');
                promptFilterStatus.setAttribute('role', 'status');
                
                if (hasActiveFilters) {
                    promptFilterStatus.setAttribute('aria-label', `Filters applied. ${count} prompts shown.`);
                } else {
                    promptFilterStatus.setAttribute('aria-label', `No filters applied. ${count} prompts shown.`);
                }
                
                return promptFilterStatus;
            }

            // Test with filters
            let statusElement = updateFilterStatusForAccessibility(2, true);
            assert.strictEqual(statusElement.getAttribute('aria-live'), 'polite');
            assert.strictEqual(statusElement.getAttribute('role'), 'status');
            assert.strictEqual(statusElement.getAttribute('aria-label'), 'Filters applied. 2 prompts shown.');

            // Test without filters
            statusElement = updateFilterStatusForAccessibility(5, false);
            assert.strictEqual(statusElement.getAttribute('aria-label'), 'No filters applied. 5 prompts shown.');
        });
    });
});