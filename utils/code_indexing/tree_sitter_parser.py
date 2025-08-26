"""Tree-sitter based code parsing for multiple languages.

This module provides a unified interface for parsing code using tree-sitter
to extract function definitions, class definitions, and call relationships
across C++, Python, JavaScript, and Java.
"""

import os
import json
from typing import Dict, List, Any, Optional, Tuple, Iterator, Union
from tree_sitter import Parser, Query, Node, Language
import tree_sitter_cpp
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_java


class MultiLanguageParser:
    """A unified parser for multiple programming languages using tree-sitter."""

    def __init__(self):
        """Initialize parsers and queries for all supported languages."""
        self.languages = {
            "cpp": Language(tree_sitter_cpp.language()),
            "python": Language(tree_sitter_python.language()),
            "javascript": Language(tree_sitter_javascript.language()),
            "java": Language(tree_sitter_java.language()),
        }

        self.parsers = {
            lang: Parser(language) for lang, language in self.languages.items()
        }

        self._init_queries()

    def _init_queries(self):
        """Initialize tree-sitter queries for each language."""
        self.queries = {}

        # C++ queries
        self.queries["cpp"] = {
            "functions": Query(
                self.languages["cpp"],
                """
                (function_definition
                  declarator: (function_declarator declarator: (_) @func.name) @func.def)
                (declaration
                  declarator: (function_declarator declarator: (_) @func.name) @func.decl)
            """,
            ),
            "classes": Query(
                self.languages["cpp"],
                """
                (class_specifier name: (type_identifier) @class.name) @class.def
                (struct_specifier name: (type_identifier) @class.name) @class.def
            """,
            ),
            "calls": Query(
                self.languages["cpp"],
                """
                (call_expression (identifier) @callee)
                (call_expression (qualified_identifier) @callee)
                (call_expression (field_expression field: (field_identifier) @callee))
            """,
            ),
        }

        # Python queries
        self.queries["python"] = {
            "functions": Query(
                self.languages["python"],
                """
                (function_definition name: (identifier) @func.name) @func.def
            """,
            ),
            "classes": Query(
                self.languages["python"],
                """
                (class_definition name: (identifier) @class.name) @class.def
            """,
            ),
            "calls": Query(
                self.languages["python"],
                """
                (call (identifier) @callee)
                (call (attribute attribute: (identifier) @callee))
            """,
            ),
        }

        # JavaScript queries
        self.queries["javascript"] = {
            "functions": Query(
                self.languages["javascript"],
                """
                (function_declaration name: (identifier) @func.name) @func.def
                (method_definition name: (property_identifier) @func.name) @func.def
                (arrow_function) @func.def
                (function_expression name: (identifier) @func.name) @func.def
            """,
            ),
            "classes": Query(
                self.languages["javascript"],
                """
                (class_declaration name: (identifier) @class.name) @class.def
            """,
            ),
            "calls": Query(
                self.languages["javascript"],
                """
                (call_expression function: (identifier) @callee)
                (call_expression function: (member_expression property: (property_identifier) @callee))
            """,
            ),
        }

        # Java queries
        self.queries["java"] = {
            "functions": Query(
                self.languages["java"],
                """
                (method_declaration name: (identifier) @func.name) @func.def
                (constructor_declaration name: (identifier) @func.name) @func.def
            """,
            ),
            "classes": Query(
                self.languages["java"],
                """
                (class_declaration name: (identifier) @class.name) @class.def
                (interface_declaration name: (identifier) @class.name) @class.def
            """,
            ),
            "calls": Query(
                self.languages["java"],
                """
                (method_invocation name: (identifier) @callee)
                (method_invocation object: (_) name: (identifier) @callee)
            """,
            ),
        }

    def get_file_language(self, file_path: str) -> Optional[str]:
        """Determine the language of a file based on its extension."""
        ext = os.path.splitext(file_path)[1].lower()

        ext_to_lang = {
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".c++": "cpp",
            ".hpp": "cpp",
            ".hh": "cpp",
            ".h": "cpp",
            ".hxx": "cpp",
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "javascript",
            ".tsx": "javascript",
            ".java": "java",
        }

        return ext_to_lang.get(ext)

    def text(self, node: Node, src: bytes) -> str:
        """Extract text content from a tree-sitter node."""
        return src[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")

    def walk_files(self, root: str) -> Iterator[Tuple[str, bytes]]:
        """Walk through supported source files in a directory."""
        supported_extensions = {
            ".cpp",
            ".cc",
            ".cxx",
            ".c++",
            ".hpp",
            ".hh",
            ".h",
            ".hxx",
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".java",
        }

        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if any(filename.endswith(ext) for ext in supported_extensions):
                    file_path = os.path.join(dirpath, filename)
                    try:
                        with open(file_path, "rb") as f:
                            yield file_path, f.read()
                    except (IOError, OSError):
                        continue

    def parse_definitions(
        self, src: bytes, language: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Parse function and class definitions from source code."""
        if language not in self.parsers:
            return {"functions": [], "classes": []}

        parser = self.parsers[language]
        tree = parser.parse(src)

        result = {"functions": [], "classes": []}

        # Parse functions using manual traversal
        result["functions"] = self._extract_functions_manual(
            tree.root_node, src, language
        )

        # Parse classes using manual traversal
        result["classes"] = self._extract_classes_manual(tree.root_node, src, language)

        return result

    def _extract_functions_manual(
        self, node: Node, src: bytes, language: str
    ) -> List[Dict[str, Any]]:
        """Extract function definitions using manual tree traversal."""
        functions = []

        def traverse(node):
            # Check for function definitions based on language
            if self._is_function_node(node, language):
                name = self._get_function_name(node, language)
                if name:
                    functions.append(
                        {
                            "name": name,
                            "kind": "def",
                            "start_line": node.start_point[0] + 1,
                            "end_line": node.end_point[0] + 1,
                        }
                    )

            # Traverse children
            for child in node.children:
                traverse(child)

        traverse(node)
        functions.sort(key=lambda f: (f["start_line"], f["end_line"]))
        return functions

    def _extract_classes_manual(
        self, node: Node, src: bytes, language: str
    ) -> List[Dict[str, Any]]:
        """Extract class definitions using manual tree traversal."""
        classes = []

        def traverse(node):
            # Check for class definitions based on language
            if self._is_class_node(node, language):
                name = self._get_class_name(node, language)
                if name:
                    classes.append(
                        {
                            "name": name,
                            "kind": "class",
                            "start_line": node.start_point[0] + 1,
                            "end_line": node.end_point[0] + 1,
                        }
                    )

            # Traverse children
            for child in node.children:
                traverse(child)

        traverse(node)
        classes.sort(key=lambda c: (c["start_line"], c["end_line"]))
        return classes

    def _get_function_name(self, node: Node, language: str) -> Optional[str]:
        """Extract function name from a function definition node."""
        if language == "python":
            # For Python: (function_definition name: (identifier))
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode("utf-8", errors="ignore")

        elif language == "javascript":
            # For JavaScript: various function patterns
            if node.type == "function_declaration":
                for child in node.children:
                    if child.type == "identifier":
                        return child.text.decode("utf-8", errors="ignore")
            elif node.type == "method_definition":
                for child in node.children:
                    if child.type == "property_identifier":
                        return child.text.decode("utf-8", errors="ignore")

        elif language == "java":
            # For Java: (method_declaration name: (identifier))
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode("utf-8", errors="ignore")

        elif language == "cpp":
            # For C++: more complex due to declarators
            if node.type == "function_definition":
                # Look for function_declarator -> identifier or qualified_identifier
                for child in node.children:
                    if child.type == "function_declarator":
                        for subchild in child.children:
                            if subchild.type == "identifier":
                                return subchild.text.decode("utf-8", errors="ignore")
                            elif subchild.type == "qualified_identifier":
                                # For methods like Calculator::add, extract just the method name
                                parts = subchild.text.decode(
                                    "utf-8", errors="ignore"
                                ).split("::")
                                return parts[-1] if parts else None
                            elif subchild.type == "function_declarator":
                                # Nested declarators for constructors
                                for nested in subchild.children:
                                    if nested.type == "identifier":
                                        return nested.text.decode(
                                            "utf-8", errors="ignore"
                                        )
                                    elif nested.type == "qualified_identifier":
                                        parts = nested.text.decode(
                                            "utf-8", errors="ignore"
                                        ).split("::")
                                        return parts[-1] if parts else None
            elif node.type == "declaration":
                # Look for function declarations/prototypes
                for child in node.children:
                    if child.type == "function_declarator":
                        for subchild in child.children:
                            if subchild.type == "identifier":
                                return subchild.text.decode("utf-8", errors="ignore")
                            elif subchild.type == "qualified_identifier":
                                parts = subchild.text.decode(
                                    "utf-8", errors="ignore"
                                ).split("::")
                                return parts[-1] if parts else None
                            elif subchild.type == "function_declarator":
                                # Nested declarators
                                for nested in subchild.children:
                                    if nested.type == "identifier":
                                        return nested.text.decode(
                                            "utf-8", errors="ignore"
                                        )
                                    elif nested.type == "qualified_identifier":
                                        parts = nested.text.decode(
                                            "utf-8", errors="ignore"
                                        ).split("::")
                                        return parts[-1] if parts else None

        return None

    def _get_class_name(self, node: Node, language: str) -> Optional[str]:
        """Extract class name from a class definition node."""
        if language == "python":
            # For Python: (class_definition name: (identifier))
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode("utf-8", errors="ignore")

        elif language == "javascript":
            # For JavaScript: (class_declaration name: (identifier))
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode("utf-8", errors="ignore")

        elif language == "java":
            # For Java: class/interface declaration
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode("utf-8", errors="ignore")

        elif language == "cpp":
            # For C++: class_specifier/struct_specifier
            for child in node.children:
                if child.type == "type_identifier":
                    return child.text.decode("utf-8", errors="ignore")

        return None

    def _is_function_node(self, node: Node, language: str) -> bool:
        """Check if a node represents a function definition."""
        func_types = {
            "python": {"function_definition"},
            "javascript": {
                "function_declaration",
                "method_definition",
                "arrow_function",
                "function_expression",
            },
            "java": {"method_declaration", "constructor_declaration"},
            "cpp": {"function_definition", "declaration"},
        }
        return node.type in func_types.get(language, set())

    def _is_class_node(self, node: Node, language: str) -> bool:
        """Check if a node represents a class definition."""
        class_types = {
            "python": {"class_definition"},
            "javascript": {"class_declaration"},
            "java": {"class_declaration", "interface_declaration"},
            "cpp": {"class_specifier", "struct_specifier"},
        }
        return node.type in class_types.get(language, set())

    def parse_calls(self, src: bytes, language: str) -> List[Dict[str, Any]]:
        """Parse function calls from source code."""
        if language not in self.parsers:
            return []

        parser = self.parsers[language]
        tree = parser.parse(src)

        calls = []

        def traverse(node):
            # Check for function calls based on language
            if self._is_call_node(node, language):
                name = self._get_call_name(node, language)
                if name:
                    calls.append({"name": name, "line": node.start_point[0] + 1})

            # Traverse children
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return calls

    def _is_call_node(self, node: Node, language: str) -> bool:
        """Check if a node represents a function call."""
        call_types = {
            "python": {"call"},
            "javascript": {"call_expression"},
            "java": {"method_invocation"},
            "cpp": {"call_expression"},
        }
        return node.type in call_types.get(language, set())

    def _get_call_name(self, node: Node, language: str) -> Optional[str]:
        """Extract function call name from a call node."""
        if language == "python":
            # For Python: (call function: (identifier))
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode("utf-8", errors="ignore")
                elif child.type == "attribute":
                    # Handle method calls like obj.method()
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            return subchild.text.decode("utf-8", errors="ignore")

        elif language == "javascript":
            # For JavaScript: (call_expression function: (identifier))
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode("utf-8", errors="ignore")
                elif child.type == "member_expression":
                    # Handle method calls
                    for subchild in child.children:
                        if subchild.type == "property_identifier":
                            return subchild.text.decode("utf-8", errors="ignore")

        elif language == "java":
            # For Java: (method_invocation name: (identifier))
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode("utf-8", errors="ignore")

        elif language == "cpp":
            # For C++: (call_expression (identifier))
            for child in node.children:
                if child.type == "identifier":
                    return child.text.decode("utf-8", errors="ignore")
                elif child.type == "qualified_identifier":
                    return child.text.decode("utf-8", errors="ignore")
                elif child.type == "field_expression":
                    # Handle member function calls
                    for subchild in child.children:
                        if subchild.type == "field_identifier":
                            return subchild.text.decode("utf-8", errors="ignore")

        return None

    def find_enclosing_function(
        self, definitions: List[Dict[str, Any]], line: int
    ) -> Optional[Dict[str, Any]]:
        """Find the function that encloses a given line number."""
        # Find the smallest interval that contains the line
        candidates = [
            d for d in definitions if d["start_line"] <= line <= d["end_line"]
        ]
        if candidates:
            return min(candidates, key=lambda d: d["end_line"] - d["start_line"])

        # Fallback to nearest preceding function
        preceding = [d for d in definitions if d["start_line"] <= line]
        return max(preceding, key=lambda d: d["start_line"]) if preceding else None

    def build_call_graph(
        self, root: str
    ) -> Tuple[List[Tuple[str, Dict[str, Any]]], List[Dict[str, Any]]]:
        """Build a call graph from all supported files in a directory."""
        symbol_table = []
        edges = []

        for file_path, src in self.walk_files(root):
            language = self.get_file_language(file_path)
            if not language:
                continue

            # Parse definitions
            definitions = self.parse_definitions(src, language)
            all_defs = definitions["functions"] + definitions["classes"]
            symbol_table.append(
                (file_path, {"language": language, "definitions": all_defs})
            )

            # Parse calls and build edges
            calls = self.parse_calls(src, language)

            for call in calls:
                caller = self.find_enclosing_function(
                    definitions["functions"], call["line"]
                )
                if caller:
                    edges.append(
                        {
                            "from_file": file_path,
                            "from_func": caller["name"],
                            "site_line": call["line"],
                            "to_name": call["name"],
                            "language": language,
                        }
                    )

        return symbol_table, edges

    def resolve_calls(
        self,
        symbol_table: List[Tuple[str, Dict[str, Any]]],
        edges: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Resolve function calls to their definitions within the same file."""
        # Build a lookup table for definitions by file
        defs_by_file = {}
        for file_path, file_data in symbol_table:
            defs_by_file[file_path] = {d["name"] for d in file_data["definitions"]}

        # Add resolution information to edges
        for edge in edges:
            edge["resolved_same_file"] = edge["to_name"] in defs_by_file.get(
                edge["from_file"], set()
            )

        return edges


    def analyze_code(self, content: str, language: str) -> Dict[str, Any]:
        """Analyze code content and return structured information.

        Args:
            content: Source code content
            language: Programming language (cpp, python, javascript, java)

        Returns:
            Dictionary containing parsed functions, classes, and calls
        """
        try:
            # Convert content to bytes
            src = content.encode('utf-8')

            # Parse the code
            if language not in self.parsers:
                return {
                    "error": f"Unsupported language: {language}",
                    "functions": [],
                    "classes": [],
                    "calls": []
                }

            tree = self.parsers[language].parse(src)
            root = tree.root_node

            # Extract functions and classes
            functions, classes = self.parse_definitions(src, language)

            # Extract function calls
            calls = self.parse_calls(src, language)

            return {
                "functions": functions,
                "classes": classes,
                "calls": calls,
                "total_nodes": len(list(self._walk_tree(root)))
            }

        except Exception as e:
            return {
                "error": str(e),
                "functions": [],
                "classes": [],
                "calls": []
            }

    def _walk_tree(self, node: Node):
        """Walk the AST tree and yield all nodes."""
        yield node
        for child in node.children:
            yield from self._walk_tree(child)


def main():
    """Example usage of the MultiLanguageParser."""
    parser = MultiLanguageParser()

    # Build call graph for current directory
    symbol_table, edges = parser.build_call_graph(".")

    # Resolve calls
    resolved_edges = parser.resolve_calls(symbol_table, edges)

    # Print first 50 edges as JSON
    print(json.dumps(resolved_edges[:50], indent=2))


if __name__ == "__main__":
    main()
