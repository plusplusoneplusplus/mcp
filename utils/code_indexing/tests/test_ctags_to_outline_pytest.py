#!/usr/bin/env python3
"""
Pytest test cases for ctags_to_outline.py script.

This module tests the ctags parsing and outline rendering functionality:
- JSON tag parsing
- Class and member indexing
- Text outline rendering
- PlantUML output generation
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

# Import from the parent package
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from utils.code_indexing import (
    access_mark,
    type_name,
    load_tags,
    build_index,
    render_text,
    render_plantuml,
    CLASS_KINDS,
    MEMBER_KINDS,
    METHOD_KINDS,
)
from utils.code_indexing.outline import main_outline


@pytest.fixture
def sample_tags():
    """Sample tags data for testing."""
    return [
        {
            "_type": "tag",
            "name": "MyClass",
            "kind": "class",
            "path": "/test/MyClass.cpp",
            "line": 5,
        },
        {
            "_type": "tag",
            "name": "publicMember",
            "kind": "member",
            "path": "/test/MyClass.cpp",
            "line": 7,
            "scope": "MyClass",
            "scopeKind": "class",
            "access": "public",
            "typeref": "typename:int",
        },
        {
            "_type": "tag",
            "name": "privateMember",
            "kind": "member",
            "path": "/test/MyClass.cpp",
            "line": 10,
            "scope": "MyClass",
            "scopeKind": "class",
            "access": "private",
            "type": "std::string",
        },
        {
            "_type": "tag",
            "name": "publicMethod",
            "kind": "method",
            "path": "/test/MyClass.cpp",
            "line": 8,
            "scope": "MyClass",
            "scopeKind": "class",
            "access": "public",
            "signature": "(int param)",
        },
        {
            "_type": "tag",
            "name": "protectedMethod",
            "kind": "method",
            "path": "/test/MyClass.cpp",
            "line": 11,
            "scope": "MyClass",
            "scopeKind": "class",
            "access": "protected",
            "signature": "()",
        },
        {
            "_type": "tag",
            "name": "AnotherClass",
            "kind": "struct",
            "path": "/test/Another.cpp",
            "line": 15,
        },
        {
            "_type": "tag",
            "name": "data",
            "kind": "member",
            "path": "/test/Another.cpp",
            "line": 17,
            "scope": "AnotherClass",
            "scopeKind": "struct",
            "typeref": "typename:double",
        },
    ]


class TestAccessMark:
    """Test access mark conversion functionality."""

    @pytest.mark.parametrize(
        "access,expected",
        [
            ("public", "+"),
            ("private", "-"),
            ("protected", "#"),
            ("", "~"),
            (None, "~"),
            ("unknown", "~"),
        ],
    )
    def test_access_mark_conversion(self, access, expected):
        """Test access mark conversion for various access levels."""
        assert access_mark(access) == expected


class TestTypeName:
    """Test type name extraction functionality."""

    @pytest.mark.parametrize(
        "typeref,expected",
        [
            ("typename:int", "int"),
            ("typename:std::string", "string"),  # Only gets last part after :
            ("typename:Foo::Bar::Baz", "Baz"),
            ("int", "int"),
            ("", None),
        ],
    )
    def test_type_name_string_input(self, typeref, expected):
        """Test type name extraction from string inputs."""
        assert type_name(typeref) == expected

    @pytest.mark.parametrize(
        "typeref,expected",
        [
            ({"name": "MyType"}, "MyType"),
            ({"other": "value"}, None),
            ({}, None),
        ],
    )
    def test_type_name_dict_input(self, typeref, expected):
        """Test type name extraction from dictionary inputs."""
        assert type_name(typeref) == expected

    @pytest.mark.parametrize(
        "typeref,fallback,expected",
        [
            (None, "fallback", "fallback"),
            ("", "fallback", "fallback"),
            ({"other": "value"}, "fallback", "fallback"),
            ("typename:int", "fallback", "int"),
        ],
    )
    def test_type_name_with_fallback(self, typeref, fallback, expected):
        """Test type name extraction with fallback values."""
        assert type_name(typeref, fallback) == expected


class TestLoadTags:
    """Test tag loading functionality."""

    def test_load_tags_from_file(self, sample_tags):
        """Test loading tags from NDJSON file."""
        # Create temporary file with test data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            for tag in sample_tags:
                f.write(json.dumps(tag) + "\n")
            # Add some invalid lines
            f.write("invalid json\n")
            f.write("\n")  # empty line
            temp_file = f.name

        try:
            tags = load_tags(temp_file)
            assert len(tags) == len(sample_tags)
            assert tags[0]["name"] == "MyClass"
            assert tags[1]["name"] == "publicMember"
        finally:
            Path(temp_file).unlink()

    def test_load_tags_empty_file(self):
        """Test loading tags from empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            tags = load_tags(temp_file)
            assert len(tags) == 0
        finally:
            Path(temp_file).unlink()

    def test_load_tags_malformed_json(self):
        """Test loading tags with malformed JSON lines."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"_type": "tag", "name": "ValidTag", "kind": "class"}\n')
            f.write("invalid json line\n")
            f.write('{"_type": "tag", "name": "AnotherTag"}\n')
            temp_file = f.name

        try:
            tags = load_tags(temp_file)
            assert len(tags) == 2
            assert tags[0]["name"] == "ValidTag"
            assert tags[1]["name"] == "AnotherTag"
        finally:
            Path(temp_file).unlink()


class TestBuildIndex:
    """Test index building functionality."""

    def test_build_index(self, sample_tags):
        """Test building class index from tags."""
        classes, by_class = build_index(sample_tags)

        # Should find two classes
        assert len(classes) == 2
        assert "MyClass" in classes
        assert "AnotherClass" in classes

        # Check MyClass members
        my_class_rows = by_class["MyClass"]
        assert len(my_class_rows) == 5  # class + 2 members + 2 methods

        # Check AnotherClass members
        another_class_rows = by_class["AnotherClass"]
        assert len(another_class_rows) == 2  # struct + 1 member

    def test_build_index_empty_tags(self):
        """Test building index from empty tag list."""
        classes, by_class = build_index([])

        assert len(classes) == 0
        assert len(by_class) == 0

    def test_build_index_no_classes(self):
        """Test building index from tags without class definitions."""
        function_tags = [
            {
                "_type": "tag",
                "name": "globalFunction",
                "kind": "function",
                "path": "/test/global.cpp",
                "line": 1,
            }
        ]

        classes, by_class = build_index(function_tags)
        assert len(classes) == 0


class TestRendering:
    """Test text and PlantUML rendering functionality."""

    def test_render_text_basic(self, sample_tags):
        """Test basic text rendering."""
        classes, by_class = build_index(sample_tags)
        output = render_text(classes, by_class)

        assert "class MyClass" in output
        assert "class AnotherClass" in output
        assert "+ publicMember: int" in output
        assert "- privateMember: std::string" in output
        assert "+ publicMethod(int param)" in output
        assert "# protectedMethod()" in output
        assert "~ data: double" in output

    def test_render_text_single_class(self, sample_tags):
        """Test text rendering for single class."""
        classes, by_class = build_index(sample_tags)
        output = render_text(classes, by_class, only="MyClass")

        assert "class MyClass" in output
        assert "class AnotherClass" not in output
        assert "+ publicMember: int" in output
        assert "+ publicMethod(int param)" in output

    def test_render_text_with_file_info(self, sample_tags):
        """Test text rendering with file information."""
        classes, by_class = build_index(sample_tags)
        output = render_text(classes, by_class, show_file=True)

        assert "~ file: /test/MyClass.cpp" in output
        assert "~ file: /test/Another.cpp" in output

    def test_render_plantuml_basic(self, sample_tags):
        """Test basic PlantUML rendering."""
        classes, by_class = build_index(sample_tags)
        output = render_plantuml(classes, by_class)

        assert "@startuml" in output
        assert "@enduml" in output
        assert "class MyClass {" in output
        assert "class AnotherClass {" in output
        assert "+ publicMember: int" in output
        assert "- privateMember: std::string" in output
        assert "+ publicMethod(int param)" in output

    def test_render_plantuml_single_class(self, sample_tags):
        """Test PlantUML rendering for single class."""
        classes, by_class = build_index(sample_tags)
        output = render_plantuml(classes, by_class, only="MyClass")

        assert "@startuml" in output
        assert "@enduml" in output
        assert "class MyClass {" in output
        assert "class AnotherClass {" not in output


class TestMainFunction:
    """Test main function with various command line options."""

    @patch("sys.argv", ["ctags_to_outline.py", "test_tags.json"])
    @patch("utils.code_indexing.outline.load_tags")
    def test_main_text_output(self, mock_load_tags, sample_tags):
        """Test main function with text output."""
        mock_load_tags.return_value = sample_tags

        with patch("builtins.print") as mock_print:
            main_outline()

        # Verify print was called with text output
        mock_print.assert_called()
        output = mock_print.call_args[0][0]
        assert "class MyClass" in output
        assert "@startuml" not in output

    @patch("sys.argv", ["ctags_to_outline.py", "test_tags.json", "--plantuml"])
    @patch("utils.code_indexing.outline.load_tags")
    def test_main_plantuml_output(self, mock_load_tags, sample_tags):
        """Test main function with PlantUML output."""
        mock_load_tags.return_value = sample_tags

        with patch("builtins.print") as mock_print:
            main_outline()

        # Verify print was called with PlantUML output
        mock_print.assert_called()
        output = mock_print.call_args[0][0]
        assert "@startuml" in output
        assert "@enduml" in output

    @patch("sys.argv", ["ctags_to_outline.py", "test_tags.json", "--only", "MyClass"])
    @patch("utils.code_indexing.outline.load_tags")
    def test_main_single_class(self, mock_load_tags, sample_tags):
        """Test main function with single class output."""
        mock_load_tags.return_value = sample_tags

        with patch("builtins.print") as mock_print:
            main_outline()

        # Verify print was called with single class output
        mock_print.assert_called()
        output = mock_print.call_args[0][0]
        assert "class MyClass" in output
        assert "class AnotherClass" not in output

    @patch("sys.argv", ["ctags_to_outline.py", "empty_tags.json"])
    @patch("utils.code_indexing.outline.load_tags")
    def test_main_no_tags(self, mock_load_tags):
        """Test main function with no tags."""
        mock_load_tags.return_value = []

        with patch("sys.exit") as mock_exit:
            main_outline()
            mock_exit.assert_called_with(1)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_malformed_tag_data(self):
        """Test handling of malformed tag data."""
        malformed_tags = [
            {"_type": "tag", "name": "Test"},  # missing kind
            {"_type": "tag", "kind": "class", "name": "ValidClass"},  # valid
            {"_type": "not_tag", "name": "Test", "kind": "class"},  # wrong type
            {},  # empty object
        ]

        classes, by_class = build_index(malformed_tags)
        # Should not crash, may have empty results
        assert isinstance(classes, list)
        assert isinstance(by_class, dict)
        # Should find the one valid class
        assert "ValidClass" in classes

    def test_complex_type_references(self):
        """Test complex type reference handling."""
        complex_tag = {
            "_type": "tag",
            "name": "complexMember",
            "kind": "member",
            "typeref": "typename:std::vector<std::pair<int, std::string>>",
        }

        type_result = type_name(complex_tag.get("typeref"))
        assert type_result == "string>>"

    def test_nested_class_scoping(self):
        """Test handling of nested class scoping."""
        nested_tags = [
            {
                "_type": "tag",
                "name": "OuterClass",
                "kind": "class",
                "path": "/test/nested.cpp",
            },
            {
                "_type": "tag",
                "name": "InnerClass",
                "kind": "class",
                "path": "/test/nested.cpp",
                "scope": "OuterClass",
                "scopeKind": "class",
            },
            {
                "_type": "tag",
                "name": "innerMember",
                "kind": "member",
                "path": "/test/nested.cpp",
                "scope": "InnerClass",
                "scopeKind": "class",
            },
        ]

        classes, by_class = build_index(nested_tags)
        assert "OuterClass" in classes
        assert "InnerClass" in classes


@pytest.mark.parametrize(
    "rendering_function,expected_content",
    [
        (lambda c, bc: render_text(c, bc), "class"),
        (lambda c, bc: render_plantuml(c, bc), "@startuml"),
    ],
)
def test_parametrized_rendering(sample_tags, rendering_function, expected_content):
    """Test different rendering functions with parametrized tests."""
    classes, by_class = build_index(sample_tags)
    output = rendering_function(classes, by_class)
    assert expected_content in output


@pytest.mark.parametrize(
    "class_kinds",
    [
        {"class"},
        {"struct"},
        {"interface"},
        {"class", "struct"},
        {"class", "struct", "interface"},
    ],
)
def test_parametrized_class_kinds(class_kinds):
    """Test with different combinations of class kinds."""
    from utils.code_indexing.outline import CLASS_KINDS

    # Temporarily modify CLASS_KINDS for testing
    original_kinds = CLASS_KINDS.copy()
    CLASS_KINDS.clear()
    CLASS_KINDS.update(class_kinds)

    try:
        test_tags = [
            {"_type": "tag", "name": "TestClass", "kind": "class"},
            {"_type": "tag", "name": "TestStruct", "kind": "struct"},
            {"_type": "tag", "name": "TestInterface", "kind": "interface"},
        ]

        classes, by_class = build_index(test_tags)

        # Check that only the configured kinds are recognized
        for tag in test_tags:
            if tag["kind"] in class_kinds:
                assert tag["name"] in classes
            else:
                assert tag["name"] not in classes
    finally:
        # Restore original CLASS_KINDS
        CLASS_KINDS.clear()
        CLASS_KINDS.update(original_kinds)


@pytest.mark.slow
class TestPerformance:
    """Performance tests for large datasets."""

    def test_large_tag_set_performance(self):
        """Test performance with a large number of tags."""
        large_tag_set = []

        # Generate a large number of test tags
        for i in range(1000):
            large_tag_set.append(
                {
                    "_type": "tag",
                    "name": f"Class{i}",
                    "kind": "class",
                    "path": f"/test/file{i}.cpp",
                    "line": i + 1,
                }
            )

            # Add some members for each class
            for j in range(5):
                large_tag_set.append(
                    {
                        "_type": "tag",
                        "name": f"member{j}",
                        "kind": "member",
                        "path": f"/test/file{i}.cpp",
                        "line": i + j + 2,
                        "scope": f"Class{i}",
                        "scopeKind": "class",
                    }
                )

        # This should complete in reasonable time
        classes, by_class = build_index(large_tag_set)

        assert len(classes) == 1000

        # Test rendering performance
        output = render_text(classes, by_class)
        assert len(output) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
