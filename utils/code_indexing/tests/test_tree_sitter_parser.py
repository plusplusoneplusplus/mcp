"""Comprehensive tests for the tree-sitter parser module.

This test file covers all 4 supported languages: C++, Python, JavaScript, and Java.
"""

import pytest
import tempfile
import os
from pathlib import Path
from utils.code_indexing.tree_sitter_parser import MultiLanguageParser


class TestMultiLanguageParser:
    """Test suite for the MultiLanguageParser class."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance for tests."""
        return MultiLanguageParser()

    @pytest.fixture
    def sample_files(self):
        """Create sample source files for testing."""
        samples = {}

        # C++ sample
        samples[
            "cpp"
        ] = """
// Sample C++ file
#include <iostream>
#include <vector>

class Calculator {
private:
    int value;

public:
    Calculator(int initial_value);
    int add(int x);
    int multiply(int x);
    void display() const;
};

Calculator::Calculator(int initial_value) : value(initial_value) {}

int Calculator::add(int x) {
    value += x;
    return value;
}

int Calculator::multiply(int x) {
    value *= x;
    return value;
}

void Calculator::display() const {
    std::cout << "Value: " << value << std::endl;
}

int global_function(int a, int b) {
    return a + b;
}

int main() {
    Calculator calc(10);
    calc.add(5);
    calc.multiply(2);
    calc.display();

    int result = global_function(3, 4);
    std::cout << "Result: " << result << std::endl;

    return 0;
}
"""

        # Python sample
        samples[
            "python"
        ] = '''
"""Sample Python file"""
import math
from typing import List, Optional

class MathProcessor:
    """A class for mathematical operations."""

    def __init__(self, initial_value: int = 0):
        self.value = initial_value
        self.history: List[int] = []

    def add(self, x: int) -> int:
        """Add a value to the current value."""
        self.value += x
        self.history.append(self.value)
        return self.value

    def multiply(self, x: int) -> int:
        """Multiply the current value."""
        self.value *= x
        self.history.append(self.value)
        return self.value

    def get_history(self) -> List[int]:
        """Get the history of operations."""
        return self.history.copy()

    def reset(self) -> None:
        """Reset the value and history."""
        self.value = 0
        self.history.clear()

def calculate_area(radius: float) -> float:
    """Calculate the area of a circle."""
    return math.pi * radius ** 2

def process_numbers(numbers: List[int]) -> Optional[int]:
    """Process a list of numbers."""
    if not numbers:
        return None

    processor = MathProcessor()
    total = 0

    for num in numbers:
        result = processor.add(num)
        total += result

    area = calculate_area(5.0)
    print(f"Circle area: {area}")

    return total

if __name__ == "__main__":
    nums = [1, 2, 3, 4, 5]
    result = process_numbers(nums)
    print(f"Final result: {result}")
'''

        # JavaScript sample
        samples[
            "javascript"
        ] = """
// Sample JavaScript file
class DataProcessor {
    constructor(initialValue = 0) {
        this.value = initialValue;
        this.operations = [];
    }

    add(x) {
        this.value += x;
        this.operations.push({op: 'add', value: x, result: this.value});
        return this.value;
    }

    multiply(x) {
        this.value *= x;
        this.operations.push({op: 'multiply', value: x, result: this.value});
        return this.value;
    }

    getOperations() {
        return [...this.operations];
    }

    reset() {
        this.value = 0;
        this.operations = [];
    }
}

function calculateSum(numbers) {
    return numbers.reduce((sum, num) => sum + num, 0);
}

const processData = (data) => {
    const processor = new DataProcessor(10);

    data.forEach(item => {
        processor.add(item);
    });

    const sum = calculateSum(data);
    console.log(`Sum: ${sum}`);

    return processor.getOperations();
};

function validateInput(input) {
    if (!Array.isArray(input)) {
        throw new Error("Input must be an array");
    }
    return input.filter(item => typeof item === 'number');
}

// Main execution
const numbers = [1, 2, 3, 4, 5];
const validNumbers = validateInput(numbers);
const operations = processData(validNumbers);
console.log("Operations:", operations);
"""

        # Java sample
        samples[
            "java"
        ] = """
// Sample Java file
import java.util.*;

public class NumberProcessor {
    private int value;
    private List<Operation> operations;

    public NumberProcessor(int initialValue) {
        this.value = initialValue;
        this.operations = new ArrayList<>();
    }

    public NumberProcessor() {
        this(0);
    }

    public int add(int x) {
        this.value += x;
        this.operations.add(new Operation("add", x, this.value));
        return this.value;
    }

    public int multiply(int x) {
        this.value *= x;
        this.operations.add(new Operation("multiply", x, this.value));
        return this.value;
    }

    public List<Operation> getOperations() {
        return new ArrayList<>(this.operations);
    }

    public void reset() {
        this.value = 0;
        this.operations.clear();
    }

    public int getValue() {
        return this.value;
    }
}

class Operation {
    private String type;
    private int operand;
    private int result;

    public Operation(String type, int operand, int result) {
        this.type = type;
        this.operand = operand;
        this.result = result;
    }

    public String getType() { return type; }
    public int getOperand() { return operand; }
    public int getResult() { return result; }
}

interface Calculator {
    int calculate(int a, int b);
}

class MathUtils {
    public static int sum(List<Integer> numbers) {
        return numbers.stream().mapToInt(Integer::intValue).sum();
    }

    public static double calculateArea(double radius) {
        return Math.PI * radius * radius;
    }

    public static void processNumbers(List<Integer> numbers) {
        NumberProcessor processor = new NumberProcessor(10);

        for (Integer num : numbers) {
            processor.add(num);
        }

        int total = sum(numbers);
        double area = calculateArea(5.0);

        System.out.println("Total: " + total);
        System.out.println("Area: " + area);
        System.out.println("Final value: " + processor.getValue());
    }
}
"""

        return samples

    def test_language_detection(self, parser):
        """Test language detection from file extensions."""
        test_cases = [
            ("file.cpp", "cpp"),
            ("file.cc", "cpp"),
            ("file.hpp", "cpp"),
            ("file.h", "cpp"),
            ("file.py", "python"),
            ("file.js", "javascript"),
            ("file.jsx", "javascript"),
            ("file.ts", "javascript"),
            ("file.tsx", "javascript"),
            ("file.java", "java"),
            ("file.txt", None),
            ("file", None),
        ]

        for filename, expected_lang in test_cases:
            assert parser.get_file_language(filename) == expected_lang

    def test_cpp_parsing(self, parser, sample_files):
        """Test C++ code parsing."""
        src = sample_files["cpp"].encode("utf-8")
        definitions = parser.parse_definitions(src, "cpp")

        # Check functions
        functions = definitions["functions"]
        function_names = [f["name"] for f in functions]

        assert "Calculator" in function_names  # Constructor
        assert "add" in function_names
        assert "multiply" in function_names
        assert "display" in function_names
        assert "global_function" in function_names
        assert "main" in function_names

        # Check classes
        classes = definitions["classes"]
        class_names = [c["name"] for c in classes]
        assert "Calculator" in class_names

        # Check function calls
        calls = parser.parse_calls(src, "cpp")
        call_names = [c["name"] for c in calls]
        assert "add" in call_names
        assert "multiply" in call_names
        assert "display" in call_names
        assert "global_function" in call_names

    def test_python_parsing(self, parser, sample_files):
        """Test Python code parsing."""
        src = sample_files["python"].encode("utf-8")
        definitions = parser.parse_definitions(src, "python")

        # Check functions
        functions = definitions["functions"]
        function_names = [f["name"] for f in functions]

        assert "__init__" in function_names
        assert "add" in function_names
        assert "multiply" in function_names
        assert "get_history" in function_names
        assert "reset" in function_names
        assert "calculate_area" in function_names
        assert "process_numbers" in function_names

        # Check classes
        classes = definitions["classes"]
        class_names = [c["name"] for c in classes]
        assert "MathProcessor" in class_names

        # Check function calls
        calls = parser.parse_calls(src, "python")
        call_names = [c["name"] for c in calls]
        assert "append" in call_names
        assert "copy" in call_names
        assert "clear" in call_names
        assert "calculate_area" in call_names
        assert "print" in call_names

    def test_javascript_parsing(self, parser, sample_files):
        """Test JavaScript code parsing."""
        src = sample_files["javascript"].encode("utf-8")
        definitions = parser.parse_definitions(src, "javascript")

        # Check functions
        functions = definitions["functions"]
        function_names = [f["name"] for f in functions]

        assert "constructor" in function_names
        assert "add" in function_names
        assert "multiply" in function_names
        assert "getOperations" in function_names
        assert "reset" in function_names
        assert "calculateSum" in function_names
        assert "validateInput" in function_names

        # Check classes
        classes = definitions["classes"]
        class_names = [c["name"] for c in classes]
        assert "DataProcessor" in class_names

        # Check function calls
        calls = parser.parse_calls(src, "javascript")
        call_names = [c["name"] for c in calls]
        assert "push" in call_names
        assert "reduce" in call_names
        assert "forEach" in call_names
        assert "calculateSum" in call_names
        assert "console" in call_names or "log" in call_names

    def test_java_parsing(self, parser, sample_files):
        """Test Java code parsing."""
        src = sample_files["java"].encode("utf-8")
        definitions = parser.parse_definitions(src, "java")

        # Check functions
        functions = definitions["functions"]
        function_names = [f["name"] for f in functions]

        assert "NumberProcessor" in function_names  # Constructor
        assert "add" in function_names
        assert "multiply" in function_names
        assert "getOperations" in function_names
        assert "reset" in function_names
        assert "getValue" in function_names
        assert "sum" in function_names
        assert "calculateArea" in function_names
        assert "processNumbers" in function_names

        # Check classes and interfaces
        classes = definitions["classes"]
        class_names = [c["name"] for c in classes]
        assert "NumberProcessor" in class_names
        assert "Operation" in class_names
        assert "Calculator" in class_names  # Interface
        assert "MathUtils" in class_names

        # Check function calls
        calls = parser.parse_calls(src, "java")
        call_names = [c["name"] for c in calls]
        assert "add" in call_names
        assert "clear" in call_names
        assert "sum" in call_names
        assert "calculateArea" in call_names
        assert "println" in call_names

    def test_enclosing_function_detection(self, parser, sample_files):
        """Test finding enclosing functions for call sites."""
        src = sample_files["python"].encode("utf-8")
        definitions = parser.parse_definitions(src, "python")
        functions = definitions["functions"]

        # Test a line inside the process_numbers function
        enclosing = parser.find_enclosing_function(
            functions, 50
        )  # Approximate line number
        assert enclosing is not None

        # Test a line outside any function
        enclosing = parser.find_enclosing_function(functions, 1)
        assert enclosing is None or enclosing["name"] in [
            "calculate_area",
            "process_numbers",
        ]

    def test_call_graph_building(self, parser, sample_files):
        """Test building call graphs from source files."""
        # Create temporary files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write sample files
            for lang, content in sample_files.items():
                ext_map = {
                    "cpp": ".cpp",
                    "python": ".py",
                    "javascript": ".js",
                    "java": ".java",
                }
                file_path = Path(tmpdir) / f"sample{ext_map[lang]}"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            # Build call graph
            symbol_table, edges = parser.build_call_graph(tmpdir)

            # Verify we have entries for all languages
            languages_found = {data["language"] for _, data in symbol_table}
            assert "cpp" in languages_found
            assert "python" in languages_found
            assert "javascript" in languages_found
            assert "java" in languages_found

            # Verify we have some edges (function calls)
            assert len(edges) > 0

            # Check that edges have required fields
            for edge in edges:
                assert "from_file" in edge
                assert "from_func" in edge
                assert "site_line" in edge
                assert "to_name" in edge
                assert "language" in edge

    def test_call_resolution(self, parser, sample_files):
        """Test resolving function calls to their definitions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write a simple Python file
            py_content = """
def helper_function():
    return 42

def main_function():
    result = helper_function()
    return result
"""
            file_path = Path(tmpdir) / "test.py"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(py_content)

            # Build call graph and resolve calls
            symbol_table, edges = parser.build_call_graph(tmpdir)
            resolved_edges = parser.resolve_calls(symbol_table, edges)

            # Find the call to helper_function
            helper_calls = [
                e for e in resolved_edges if e["to_name"] == "helper_function"
            ]
            assert len(helper_calls) > 0

            # Verify it's resolved within the same file
            assert helper_calls[0]["resolved_same_file"] is True

    def test_file_walking(self, parser):
        """Test walking through source files in a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_files = {
                "test.cpp": "// C++ file",
                "test.py": "# Python file",
                "test.js": "// JavaScript file",
                "test.java": "// Java file",
                "test.txt": "Text file",  # Should be ignored
                "README.md": "# Markdown file",  # Should be ignored
            }

            for filename, content in test_files.items():
                with open(Path(tmpdir) / filename, "w") as f:
                    f.write(content)

            # Walk files
            found_files = list(parser.walk_files(tmpdir))
            found_names = [os.path.basename(path) for path, _ in found_files]

            # Verify only source files are found
            assert "test.cpp" in found_names
            assert "test.py" in found_names
            assert "test.js" in found_names
            assert "test.java" in found_names
            assert "test.txt" not in found_names
            assert "README.md" not in found_names

    def test_empty_file_handling(self, parser):
        """Test handling of empty or invalid files."""
        # Test empty file
        empty_src = b""
        definitions = parser.parse_definitions(empty_src, "python")
        assert definitions["functions"] == []
        assert definitions["classes"] == []

        calls = parser.parse_calls(empty_src, "python")
        assert calls == []

    def test_unsupported_language(self, parser):
        """Test handling of unsupported languages."""
        src = b"some content"
        definitions = parser.parse_definitions(src, "unsupported")
        assert definitions["functions"] == []
        assert definitions["classes"] == []

        calls = parser.parse_calls(src, "unsupported")
        assert calls == []

    def test_text_extraction(self, parser):
        """Test text extraction from tree-sitter nodes."""
        src = b"function test() { return 42; }"
        tree = parser.parsers["javascript"].parse(src)

        # Use manual traversal to find function name
        def find_function_name(node):
            if node.type == "function_declaration":
                for child in node.children:
                    if child.type == "identifier":
                        return parser.text(child, src)
            for child in node.children:
                result = find_function_name(child)
                if result:
                    return result
            return None

        function_name = find_function_name(tree.root_node)
        assert function_name == "test"

    def test_line_numbers(self, parser, sample_files):
        """Test that line numbers are correctly reported."""
        src = sample_files["python"].encode("utf-8")
        definitions = parser.parse_definitions(src, "python")

        # Check that all definitions have valid line numbers
        for func in definitions["functions"]:
            assert func["start_line"] > 0
            assert func["end_line"] >= func["start_line"]

        for cls in definitions["classes"]:
            assert cls["start_line"] > 0
            assert cls["end_line"] >= cls["start_line"]

        # Check that calls have valid line numbers
        calls = parser.parse_calls(src, "python")
        for call in calls:
            assert call["line"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
