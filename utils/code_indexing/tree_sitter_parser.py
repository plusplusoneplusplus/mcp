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
                    class_info = {
                        "name": name,
                        "kind": "class",
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "members": self._extract_class_members(node, src, language)
                    }
                    classes.append(class_info)

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
                # Look for function_declarator -> identifier, field_identifier, or qualified_identifier
                for child in node.children:
                    if child.type == "function_declarator":
                        for subchild in child.children:
                            if subchild.type in ["identifier", "field_identifier"]:
                                return subchild.text.decode("utf-8", errors="ignore")
                            elif subchild.type == "destructor_name":
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
                                    if nested.type in ["identifier", "field_identifier"]:
                                        return nested.text.decode(
                                            "utf-8", errors="ignore"
                                        )
                                    elif nested.type == "destructor_name":
                                        return nested.text.decode("utf-8", errors="ignore")
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
                            elif subchild.type == "destructor_name":
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
                                    elif nested.type == "destructor_name":
                                        return nested.text.decode("utf-8", errors="ignore")
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

    def _extract_class_members(self, class_node: Node, src: bytes, language: str) -> List[Dict[str, Any]]:
        """Extract class members (methods, properties) from a class definition node."""
        members = []
        current_access = "public"  # Track current access level for C++
        class_name = self._get_class_name(class_node, language) or ""

        def traverse_class_body(node, access="public"):
            nonlocal current_access
            
            # Handle C++ access specifiers
            if language == "cpp" and node.type == "access_specifier":
                access_text = node.text.decode("utf-8", errors="ignore").strip()
                if access_text.startswith("public"):
                    current_access = "public"
                elif access_text.startswith("private"):
                    current_access = "private"
                elif access_text.startswith("protected"):
                    current_access = "protected"
                return  # Don't traverse children of access specifier nodes
            
            # Look for methods/functions inside class
            if self._is_function_node(node, language) or self._is_method_declaration(node, language):
                name = self._get_function_name(node, language) or self._get_method_declaration_name(node, language)
                if name:
                    # Determine member type
                    member_kind = "method"
                    
                    # Check for constructor
                    if language == "python" and name == "__init__":
                        member_kind = "constructor"
                    elif language == "java" and node.type == "constructor_declaration":
                        member_kind = "constructor"
                    elif language == "cpp":
                        # Constructor: same name as class (handle qualified names)
                        simple_class_name = class_name.split("::")[-1] if "::" in class_name else class_name
                        simple_method_name = name.split("::")[-1] if "::" in name else name
                        if simple_method_name == simple_class_name:
                            member_kind = "constructor"
                        # Destructor: starts with ~
                        elif name.startswith("~"):
                            member_kind = "destructor"
                    
                    # Check for storage class specifiers and virtual methods in C++
                    is_virtual = False
                    is_override = False
                    is_static = False
                    if language == "cpp":
                        # Look for virtual keyword, override specifier, and static keyword
                        full_text = node.text.decode("utf-8", errors="ignore")
                        if "virtual" in full_text:
                            is_virtual = True
                        if "override" in full_text:
                            is_override = True
                        if "static" in full_text:
                            is_static = True
                        
                        # Also check for storage_class_specifier nodes
                        def check_storage_specifiers(n):
                            nonlocal is_static
                            if n.type == "storage_class_specifier" and "static" in n.text.decode("utf-8", errors="ignore"):
                                is_static = True
                            for child in n.children:
                                check_storage_specifiers(child)
                        
                        check_storage_specifiers(node)

                    # Get signature if available
                    signature = self._get_function_signature(node, src, language) or self._get_method_signature(node, language)
                    
                    # Add static/virtual info to name prefix
                    prefix = ""
                    if is_static:
                        prefix = "static "
                    if is_virtual:
                        prefix = "virtual "
                    
                    members.append({
                        "name": f"{prefix}{name}",
                        "kind": member_kind,
                        "signature": signature or "",
                        "access": current_access,
                        "line": node.start_point[0] + 1,
                        "static": is_static,
                        "virtual": is_virtual,
                        "override": is_override
                    })

            # Look for field/property declarations
            elif self._is_field_node(node, language):
                field_names = self._get_field_names(node, language)
                for field_name in field_names:
                    # Get field type info if possible
                    field_type = self._get_field_type(node, language)
                    signature = f": {field_type}" if field_type else ""
                    
                    members.append({
                        "name": field_name,
                        "kind": "field",
                        "signature": signature,
                        "access": current_access,
                        "line": node.start_point[0] + 1
                    })

            # Look for enum declarations (especially important for C++)
            elif self._is_enum_node(node, language):
                enum_info = self._get_enum_info(node, language)
                if enum_info:
                    members.append({
                        "name": enum_info["name"],
                        "kind": "enum",
                        "signature": f"{{ {', '.join(enum_info['values'])} }}" if enum_info["values"] else "",
                        "access": current_access,
                        "line": node.start_point[0] + 1
                    })

            # Look for typedef or using declarations in C++
            elif language == "cpp" and node.type in ["alias_declaration", "type_definition"]:
                alias_name = self._get_alias_name(node, language)
                if alias_name:
                    members.append({
                        "name": alias_name,
                        "kind": "alias",
                        "signature": "",
                        "access": current_access,
                        "line": node.start_point[0] + 1
                    })

            # Traverse children with updated access level
            for child in node.children:
                traverse_class_body(child, current_access)

        traverse_class_body(class_node)

        # Also look for inherited members by examining base class list
        if language == "cpp":
            base_classes = self._get_base_classes(class_node, language)
            for base_class in base_classes:
                members.append({
                    "name": f"inherits from {base_class['name']}",
                    "kind": "inheritance",
                    "signature": base_class.get('access', 'public'),
                    "access": "public",
                    "line": class_node.start_point[0] + 1
                })

        # Sort members: constructors first, destructors, then methods, inheritance, enums, then fields
        def sort_key(member):
            order = {
                "constructor": 0, 
                "destructor": 1, 
                "method": 2, 
                "inheritance": 3,
                "enum": 4, 
                "alias": 5,
                "field": 6
            }
            return (order.get(member["kind"], 7), member["name"])

        members.sort(key=sort_key)
        return members

    def _get_function_signature(self, node: Node, src: bytes, language: str) -> Optional[str]:
        """Extract function signature from a function node."""
        try:
            if language == "python":
                # For Python: extract parameters from function definition
                for child in node.children:
                    if child.type == "parameters":
                        return child.text.decode("utf-8", errors="ignore")

            elif language == "javascript":
                # For JavaScript: extract parameters
                for child in node.children:
                    if child.type in ["formal_parameters", "parameter_list"]:
                        return child.text.decode("utf-8", errors="ignore")

            elif language == "java":
                # For Java: extract formal parameters
                for child in node.children:
                    if child.type == "formal_parameters":
                        return child.text.decode("utf-8", errors="ignore")

            elif language == "cpp":
                # For C++: extract parameter list from function declarator
                for child in node.children:
                    if child.type == "function_declarator":
                        for subchild in child.children:
                            if subchild.type == "parameter_list":
                                return subchild.text.decode("utf-8", errors="ignore")
                            elif subchild.type == "function_declarator":
                                # Nested declarators
                                for nested in subchild.children:
                                    if nested.type == "parameter_list":
                                        return nested.text.decode("utf-8", errors="ignore")
        except Exception:
            pass

        return None

    def _is_field_node(self, node: Node, language: str) -> bool:
        """Check if a node represents a field/property declaration."""
        field_types = {
            "python": {"assignment", "annotated_assignment"},
            "javascript": {"field_definition", "public_field_definition", "property_declaration"},
            "java": {"field_declaration", "variable_declarator"},
            "cpp": {"declaration", "field_declaration", "member_declaration"}
        }
        
        # For C++, we need to filter out function declarations 
        if language == "cpp" and node.type == "declaration":
            # Check if this declaration contains a function_declarator (which would make it a function declaration)
            has_function_declarator = False
            def check_for_function_declarator(n):
                nonlocal has_function_declarator
                if n.type == "function_declarator":
                    has_function_declarator = True
                    return
                for child in n.children:
                    check_for_function_declarator(child)
            
            check_for_function_declarator(node)
            if has_function_declarator:
                return False  # This is a function declaration, not a field
        
        return node.type in field_types.get(language, set())

    def _get_field_names(self, node: Node, language: str) -> List[str]:
        """Extract field names from a field declaration node."""
        field_names = []

        try:
            if language == "python":
                # Python assignments: x = value or x: type = value
                for child in node.children:
                    if child.type == "identifier":
                        field_names.append(child.text.decode("utf-8", errors="ignore"))

            elif language == "javascript":
                # JavaScript field definitions
                for child in node.children:
                    if child.type == "property_identifier":
                        field_names.append(child.text.decode("utf-8", errors="ignore"))

            elif language == "java":
                # Java field declarations
                def extract_identifiers(node):
                    if node.type == "identifier":
                        field_names.append(node.text.decode("utf-8", errors="ignore"))
                    for child in node.children:
                        extract_identifiers(child)
                extract_identifiers(node)

            elif language == "cpp":
                # C++ field declarations - handle various patterns
                if node.type == "declaration":
                    # Standard field declarations: int x; float y;
                    def extract_identifiers(node):
                        if node.type == "identifier":
                            field_names.append(node.text.decode("utf-8", errors="ignore"))
                        elif node.type == "init_declarator":
                            # Handle initialized fields: int x = 5;
                            for child in node.children:
                                if child.type == "identifier":
                                    field_names.append(child.text.decode("utf-8", errors="ignore"))
                        else:
                            for child in node.children:
                                extract_identifiers(child)
                    extract_identifiers(node)
                elif node.type == "field_declaration":
                    # Direct field declarations within struct/class - search recursively
                    def extract_field_identifiers(n):
                        if n.type == "field_identifier":
                            field_names.append(n.text.decode("utf-8", errors="ignore"))
                        elif n.type == "identifier" and n.parent and n.parent.type != "primitive_type":
                            # Avoid extracting type names like "int", "void", etc.
                            field_names.append(n.text.decode("utf-8", errors="ignore"))
                        else:
                            for child in n.children:
                                extract_field_identifiers(child)
                    
                    extract_field_identifiers(node)

        except Exception:
            pass

        return field_names

    def _get_field_type(self, node: Node, language: str) -> Optional[str]:
        """Extract field type from a field declaration node."""
        try:
            if language == "cpp":
                # Look for type information in the declaration
                def find_type(node):
                    # Common type nodes in C++
                    if node.type in ["primitive_type", "type_identifier", "qualified_identifier"]:
                        return node.text.decode("utf-8", errors="ignore")
                    elif node.type == "pointer_declarator":
                        # Handle pointer types
                        for child in node.children:
                            child_type = find_type(child)
                            if child_type:
                                return child_type + "*"
                    elif node.type == "reference_declarator":
                        # Handle reference types
                        for child in node.children:
                            child_type = find_type(child)
                            if child_type:
                                return child_type + "&"
                    else:
                        # Recursively search children
                        for child in node.children:
                            result = find_type(child)
                            if result:
                                return result
                    return None
                
                return find_type(node)
                
            elif language == "java":
                # Java field declarations have type information
                for child in node.children:
                    if child.type in ["type_identifier", "integral_type", "floating_point_type", "boolean_type"]:
                        return child.text.decode("utf-8", errors="ignore")
                    elif child.type == "generic_type":
                        return child.text.decode("utf-8", errors="ignore")
                        
            elif language == "python":
                # Python type annotations
                for child in node.children:
                    if child.type == "type":
                        return child.text.decode("utf-8", errors="ignore")
                        
        except Exception:
            pass
        
        return None

    def _get_alias_name(self, node: Node, language: str) -> Optional[str]:
        """Extract alias name from typedef/using declaration."""
        try:
            if language == "cpp":
                if node.type == "alias_declaration":
                    # using alias_name = type;
                    for child in node.children:
                        if child.type == "type_identifier":
                            return child.text.decode("utf-8", errors="ignore")
                elif node.type == "type_definition":
                    # typedef type alias_name;
                    identifiers = []
                    for child in node.children:
                        if child.type == "type_identifier":
                            identifiers.append(child.text.decode("utf-8", errors="ignore"))
                    # Last identifier is usually the alias name
                    return identifiers[-1] if identifiers else None
        except Exception:
            pass
        
        return None

    def _get_base_classes(self, class_node: Node, language: str) -> List[Dict[str, str]]:
        """Extract base classes from inheritance list."""
        base_classes = []
        
        try:
            if language == "cpp":
                # Look for base_class_clause
                for child in class_node.children:
                    if child.type == "base_class_clause":
                        # Parse base classes
                        for base_child in child.children:
                            if base_child.type == "access_specifier":
                                # Skip access specifiers in base class list
                                continue
                            elif base_child.type in ["type_identifier", "qualified_identifier"]:
                                base_name = base_child.text.decode("utf-8", errors="ignore")
                                # Determine access level (default is private for class, public for struct)
                                access = "private"  # Default for class inheritance
                                base_classes.append({"name": base_name, "access": access})
                            elif base_child.type == "base_class_clause":
                                # Handle nested base class structures
                                for nested in base_child.children:
                                    if nested.type in ["type_identifier", "qualified_identifier"]:
                                        base_name = nested.text.decode("utf-8", errors="ignore")
                                        base_classes.append({"name": base_name, "access": "public"})
            
            elif language == "java":
                # Java extends and implements
                for child in class_node.children:
                    if child.type == "superclass":
                        # extends SuperClass
                        for nested in child.children:
                            if nested.type == "type_identifier":
                                base_name = nested.text.decode("utf-8", errors="ignore")
                                base_classes.append({"name": base_name, "access": "extends"})
                    elif child.type == "super_interfaces":
                        # implements Interface1, Interface2
                        for nested in child.children:
                            if nested.type == "type_identifier":
                                base_name = nested.text.decode("utf-8", errors="ignore")
                                base_classes.append({"name": base_name, "access": "implements"})
                                
            elif language == "python":
                # Python class inheritance
                for child in class_node.children:
                    if child.type == "argument_list":
                        # class MyClass(BaseClass):
                        for nested in child.children:
                            if nested.type == "identifier":
                                base_name = nested.text.decode("utf-8", errors="ignore")
                                base_classes.append({"name": base_name, "access": "inherits"})
        
        except Exception:
            pass
            
        return base_classes

    def _is_method_declaration(self, node: Node, language: str) -> bool:
        """Check if a field_declaration node is actually a method declaration."""
        if language == "cpp" and node.type == "field_declaration":
            # Look for function_declarator in the field_declaration
            def has_function_declarator(n):
                if n.type == "function_declarator":
                    return True
                for child in n.children:
                    if has_function_declarator(child):
                        return True
                return False
            
            return has_function_declarator(node)
        
        return False

    def _get_method_declaration_name(self, node: Node, language: str) -> Optional[str]:
        """Extract method name from a field_declaration that's actually a method."""
        if language == "cpp" and node.type == "field_declaration":
            # Look for function_declarator and extract the identifier
            def find_function_name(n):
                if n.type == "function_declarator":
                    # Look for identifier types in the function_declarator
                    for child in n.children:
                        if child.type in ["identifier", "field_identifier"]:
                            return child.text.decode("utf-8", errors="ignore")
                        elif child.type == "destructor_name":
                            # Handle destructor
                            return child.text.decode("utf-8", errors="ignore")
                        elif child.type == "qualified_identifier":
                            # Handle qualified names
                            parts = child.text.decode("utf-8", errors="ignore").split("::")
                            return parts[-1] if parts else None
                for child in n.children:
                    result = find_function_name(child)
                    if result:
                        return result
                return None
            
            return find_function_name(node)
        
        return None

    def _get_method_signature(self, node: Node, language: str) -> Optional[str]:
        """Extract method signature from a field_declaration that's actually a method."""
        if language == "cpp" and node.type == "field_declaration":
            # Look for function_declarator and extract parameter_list
            def find_parameter_list(n):
                if n.type == "function_declarator":
                    for child in n.children:
                        if child.type == "parameter_list":
                            return child.text.decode("utf-8", errors="ignore")
                for child in n.children:
                    result = find_parameter_list(child)
                    if result:
                        return result
                return None
            
            return find_parameter_list(node)
        
        return None

    def _is_enum_node(self, node: Node, language: str) -> bool:
        """Check if a node represents an enum declaration."""
        enum_types = {
            "cpp": {"enum_specifier"},
            "java": {"enum_declaration"},
            "javascript": set(),  # JavaScript doesn't have native enums
            "python": set()  # Python uses classes for enums
        }
        return node.type in enum_types.get(language, set())

    def _get_enum_info(self, node: Node, language: str) -> Optional[Dict[str, Any]]:
        """Extract enum name and values from an enum declaration."""
        try:
            enum_name = ""
            enum_values = []

            if language == "cpp":
                # For C++: enum [name] { value1, value2, ... }
                for child in node.children:
                    if child.type == "type_identifier":
                        enum_name = child.text.decode("utf-8", errors="ignore")
                    elif child.type == "enumerator_list":
                        # Extract enum values
                        for enum_child in child.children:
                            if enum_child.type == "enumerator":
                                for identifier_child in enum_child.children:
                                    if identifier_child.type == "identifier":
                                        value_name = identifier_child.text.decode("utf-8", errors="ignore")
                                        enum_values.append(value_name)

                # Handle anonymous enums (common in C++)
                if not enum_name:
                    enum_name = "enum"

            elif language == "java":
                # For Java: enum Name { VALUE1, VALUE2, ... }
                for child in node.children:
                    if child.type == "identifier":
                        enum_name = child.text.decode("utf-8", errors="ignore")
                    elif child.type == "enum_body":
                        # Extract enum constants
                        for enum_child in child.children:
                            if enum_child.type == "enum_constant":
                                for identifier_child in enum_child.children:
                                    if identifier_child.type == "identifier":
                                        value_name = identifier_child.text.decode("utf-8", errors="ignore")
                                        enum_values.append(value_name)

            if enum_name or enum_values:
                return {
                    "name": enum_name or "enum",
                    "values": enum_values
                }

        except Exception:
            pass

        return None

    def _is_function_node(self, node: Node, language: str) -> bool:
        """Check if a node represents a function definition or declaration."""
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
            definitions = self.parse_definitions(src, language)
            functions = definitions["functions"]
            classes = definitions["classes"]

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
