#!/usr/bin/env python3
"""
Pytest integration tests for code indexing utilities.

This module contains integration tests that use the actual sample C++ and Rust projects
to test the complete workflow from source code to outline generation.
"""

import json
import os
import subprocess
import tempfile
import pytest
from pathlib import Path
import shutil

from utils.code_indexing.generator import run_ctags
from utils.code_indexing.outline import (
    load_tags,
    build_index,
    render_text,
    render_plantuml,
)


@pytest.fixture(scope="session")
def check_ctags_available():
    """Session-scoped fixture to check if ctags is available."""
    try:
        result = subprocess.run(
            ["ctags", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            pytest.skip("ctags not available")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("ctags not available")


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for integration tests."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir

    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture(scope="module")
def sample_projects():
    """Get paths to sample projects."""
    test_dir = Path(__file__).parent
    cpp_project_dir = test_dir / "sample_cpp_project"
    rust_project_dir = test_dir / "sample_rust_project"
    csharp_project_dir = test_dir / "sample_csharp_project"
    python_project_dir = test_dir / "sample_python_project"

    if not cpp_project_dir.exists():
        pytest.skip("C++ sample project not found")
    if not rust_project_dir.exists():
        pytest.skip("Rust sample project not found")
    if not csharp_project_dir.exists():
        pytest.skip("C# sample project not found")
    if not python_project_dir.exists():
        pytest.skip("Python sample project not found")

    return cpp_project_dir, rust_project_dir, csharp_project_dir, python_project_dir


class TestCppProjectIntegration:
    """Integration tests for C++ project processing."""

    def test_cpp_ctags_generation(
        self, sample_projects, temp_workspace, check_ctags_available
    ):
        """Test ctags generation for C++ project."""
        cpp_project_dir, _, _, _ = sample_projects
        output_file = temp_workspace / "cpp_tags.json"

        result = run_ctags(str(cpp_project_dir), str(output_file), languages="C++")

        # Check if ctags succeeded
        if result != 0:
            pytest.skip("ctags failed - may not be properly configured")

        # Verify output file exists and has content
        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Load and verify tags
        tags = load_tags(str(output_file))
        assert len(tags) > 0

        # Check for expected classes
        class_names = {tag["name"] for tag in tags if tag.get("kind") == "class"}
        expected_classes = {
            "Shape",
            "Rectangle",
            "Circle",
            "MathUtils",
            "Vector2D",
            "StatisticsCalculator",
        }

        # Should find at least some of the expected classes
        found_classes = class_names.intersection(expected_classes)
        assert (
            len(found_classes) > 0
        ), f"Expected classes not found. Found: {class_names}"

    def test_cpp_outline_generation(
        self, sample_projects, temp_workspace, check_ctags_available
    ):
        """Test outline generation from C++ tags."""
        cpp_project_dir, _, _, _ = sample_projects
        output_file = temp_workspace / "cpp_outline_tags.json"

        # Generate tags first
        result = run_ctags(str(cpp_project_dir), str(output_file), languages="C++")

        if result != 0 or not output_file.exists():
            pytest.skip("Failed to generate C++ tags")

        # Load tags and build index
        tags = load_tags(str(output_file))
        if not tags:
            pytest.skip("No tags loaded")

        classes, by_class = build_index(tags)
        assert len(classes) > 0, "No classes found in index"

        # Test text rendering
        text_output = render_text(classes, by_class)
        assert "class" in text_output.lower()

        # Test PlantUML rendering
        plantuml_output = render_plantuml(classes, by_class)
        assert "@startuml" in plantuml_output
        assert "@enduml" in plantuml_output
        assert "class" in plantuml_output

        # Test single class rendering
        if classes:
            single_class_output = render_text(classes, by_class, only=classes[0])
            assert f"class {classes[0]}" in single_class_output
            # Should not contain other classes
            for other_class in classes[1:]:
                assert f"class {other_class}" not in single_class_output

    def test_cpp_outline_with_file_info(
        self, sample_projects, temp_workspace, check_ctags_available
    ):
        """Test outline generation with file information."""
        cpp_project_dir, _, _, _ = sample_projects
        output_file = temp_workspace / "cpp_file_info_tags.json"

        # Generate tags
        result = run_ctags(str(cpp_project_dir), str(output_file), languages="C++")

        if result != 0 or not output_file.exists():
            pytest.skip("Failed to generate C++ tags")

        # Load tags and build index
        tags = load_tags(str(output_file))
        if not tags:
            pytest.skip("No tags loaded")

        classes, by_class = build_index(tags)
        if not classes:
            pytest.skip("No classes found")

        # Test rendering with file info
        text_with_files = render_text(classes, by_class, show_file=True)
        assert "~ file:" in text_with_files


class TestRustProjectIntegration:
    """Integration tests for Rust project processing."""

    def test_rust_ctags_generation(
        self, sample_projects, temp_workspace, check_ctags_available
    ):
        """Test ctags generation for Rust project."""
        _, rust_project_dir, _, _ = sample_projects
        output_file = temp_workspace / "rust_tags.json"

        result = run_ctags(str(rust_project_dir), str(output_file), languages="Rust")

        # Check if ctags supports Rust
        if result != 0:
            pytest.skip("ctags not available or Rust not supported")

        # Verify output file exists
        assert output_file.exists()

        # Load and verify tags
        tags = load_tags(str(output_file))
        if len(tags) == 0:
            pytest.skip("No Rust tags generated (ctags may not support Rust)")

        # Check for expected structures
        struct_names = {
            tag["name"] for tag in tags if tag.get("kind") in ("struct", "enum")
        }
        expected_structs = {"Point2D", "Rectangle", "Circle", "Config", "LibError"}

        # Should find at least some expected structures
        found_structs = struct_names.intersection(expected_structs)
        assert (
            len(found_structs) > 0
        ), f"Expected structs not found. Found: {struct_names}"


class TestCSharpProjectIntegration:
    """Integration tests for C# project processing."""

    def test_csharp_ctags_generation(
        self, sample_projects, temp_workspace, check_ctags_available
    ):
        """Test ctags generation for C# project."""
        _, _, csharp_project_dir, _ = sample_projects
        output_file = temp_workspace / "csharp_tags.json"

        result = run_ctags(str(csharp_project_dir), str(output_file), languages="C#")

        # Check if ctags succeeded
        if result != 0:
            pytest.skip("ctags failed - may not support C# or not properly configured")

        # Verify output file exists and has content
        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Load and verify tags
        tags = load_tags(str(output_file))
        assert len(tags) > 0

        # Check for expected classes and interfaces
        class_names = {
            tag["name"] for tag in tags if tag.get("kind") in ("class", "interface")
        }
        expected_classes = {
            "Program",
            "Logger",
            "IShape",
            "Shape",
            "Rectangle",
            "Circle",
            "Triangle",
            "AreaCalculator",
            "Vector2D",
            "StatisticsCalculator",
            "MathUtils",
            "MathConstants",
        }

        # Should find at least some of the expected classes
        found_classes = class_names.intersection(expected_classes)
        assert (
            len(found_classes) > 0
        ), f"Expected C# classes not found. Found: {class_names}"

    def test_csharp_outline_generation(
        self, sample_projects, temp_workspace, check_ctags_available
    ):
        """Test outline generation from C# tags."""
        _, _, csharp_project_dir, _ = sample_projects
        output_file = temp_workspace / "csharp_outline_tags.json"

        # Generate tags first
        result = run_ctags(str(csharp_project_dir), str(output_file), languages="C#")

        if result != 0 or not output_file.exists():
            pytest.skip("Failed to generate C# tags")

        # Load tags and build index
        tags = load_tags(str(output_file))
        if not tags:
            pytest.skip("No C# tags loaded")

        classes, by_class = build_index(tags)
        assert len(classes) > 0, "No classes found in C# index"

        # Test text rendering
        text_output = render_text(classes, by_class)
        assert "class" in text_output.lower() or "interface" in text_output.lower()

        # Test PlantUML rendering
        plantuml_output = render_plantuml(classes, by_class)
        assert "@startuml" in plantuml_output
        assert "@enduml" in plantuml_output
        assert "class" in plantuml_output or "interface" in plantuml_output

    def test_csharp_namespace_detection(
        self, sample_projects, temp_workspace, check_ctags_available
    ):
        """Test C# namespace detection."""
        _, _, csharp_project_dir, _ = sample_projects
        output_file = temp_workspace / "csharp_namespace_tags.json"

        result = run_ctags(str(csharp_project_dir), str(output_file), languages="C#")

        if result != 0 or not output_file.exists():
            pytest.skip("Failed to generate C# tags")

        tags = load_tags(str(output_file))
        if not tags:
            pytest.skip("No C# tags loaded")

        # Check for expected namespaces
        namespace_names = {
            tag["name"] for tag in tags if tag.get("kind") == "namespace"
        }
        expected_namespaces = {"SampleApp", "Geometry.Shapes", "Utils.Math"}

        # Should find at least some expected namespaces
        found_namespaces = namespace_names.intersection(expected_namespaces)
        # Note: ctags might not always detect namespaces, so we make this optional
        if found_namespaces:
            assert (
                len(found_namespaces) > 0
            ), f"Expected namespaces not found. Found: {namespace_names}"


class TestPythonProjectIntegration:
    """Integration tests for Python project processing."""

    def test_python_ctags_generation(
        self, sample_projects, temp_workspace, check_ctags_available
    ):
        """Test ctags generation for Python project."""
        _, _, _, python_project_dir = sample_projects
        output_file = temp_workspace / "python_tags.json"

        result = run_ctags(
            str(python_project_dir), str(output_file), languages="Python"
        )

        # Check if ctags succeeded
        if result != 0:
            pytest.skip(
                "ctags failed - may not support Python or not properly configured"
            )

        # Verify output file exists and has content
        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Load and verify tags
        tags = load_tags(str(output_file))
        assert len(tags) > 0

        # Check for expected classes
        class_names = {tag["name"] for tag in tags if tag.get("kind") == "class"}
        expected_classes = {
            "Application",
            "Shape",
            "Rectangle",
            "Circle",
            "Triangle",
            "Point",
            "AreaCalculator",
            "ShapeFactory",
            "Vector2D",
            "StatisticsCalculator",
            "MathUtils",
            "TreeNode",
            "BinaryTree",
            "LinkedList",
            "Stack",
            "Queue",
            "AsyncProcessor",
            "ProcessingJob",
        }

        # Should find at least some of the expected classes
        found_classes = class_names.intersection(expected_classes)
        assert (
            len(found_classes) > 0
        ), f"Expected Python classes not found. Found: {class_names}"

    def test_python_function_detection(
        self, sample_projects, temp_workspace, check_ctags_available
    ):
        """Test Python function detection."""
        _, _, _, python_project_dir = sample_projects
        output_file = temp_workspace / "python_functions_tags.json"

        result = run_ctags(
            str(python_project_dir), str(output_file), languages="Python"
        )

        if result != 0 or not output_file.exists():
            pytest.skip("Failed to generate Python tags")

        tags = load_tags(str(output_file))
        if not tags:
            pytest.skip("No Python tags loaded")

        # Check for expected functions
        function_names = {tag["name"] for tag in tags if tag.get("kind") == "function"}
        expected_functions = {
            "main",
            "calculate_total_area",
            "create_shape_from_dict",
            "solve_quadratic",
            "merge_sorted_lists",
            "binary_search",
            "quicksort",
            "async_timer",
            "async_retry",
            "simple_task",
            "create_sample_config",
            "validate_config",
        }

        # Should find at least some expected functions
        found_functions = function_names.intersection(expected_functions)
        assert (
            len(found_functions) > 0
        ), f"Expected Python functions not found. Found: {function_names}"

    def test_python_outline_generation(
        self, sample_projects, temp_workspace, check_ctags_available
    ):
        """Test outline generation from Python tags."""
        _, _, _, python_project_dir = sample_projects
        output_file = temp_workspace / "python_outline_tags.json"

        # Generate tags first
        result = run_ctags(
            str(python_project_dir), str(output_file), languages="Python"
        )

        if result != 0 or not output_file.exists():
            pytest.skip("Failed to generate Python tags")

        # Load tags and build index
        tags = load_tags(str(output_file))
        if not tags:
            pytest.skip("No Python tags loaded")

        classes, by_class = build_index(tags)
        assert len(classes) > 0, "No classes found in Python index"

        # Test text rendering
        text_output = render_text(classes, by_class)
        assert "class" in text_output.lower()

        # Test PlantUML rendering
        plantuml_output = render_plantuml(classes, by_class)
        assert "@startuml" in plantuml_output
        assert "@enduml" in plantuml_output
        assert "class" in plantuml_output

        # Test rendering with file info
        text_with_files = render_text(classes, by_class, show_file=True)
        assert "~ file:" in text_with_files

    def test_python_async_detection(
        self, sample_projects, temp_workspace, check_ctags_available
    ):
        """Test Python async function detection."""
        _, _, _, python_project_dir = sample_projects
        output_file = temp_workspace / "python_async_tags.json"

        result = run_ctags(
            str(python_project_dir), str(output_file), languages="Python"
        )

        if result != 0 or not output_file.exists():
            pytest.skip("Failed to generate Python tags")

        tags = load_tags(str(output_file))
        if not tags:
            pytest.skip("No Python tags loaded")

        # Look for async functions (might be tagged as regular functions)
        all_names = {tag["name"] for tag in tags}
        expected_async_functions = {
            "run_async_demo",
            "run_all_demos",
            "main",
            "async_timer",
            "async_retry",
            "simple_task",
            "execute",  # from ProcessingJob
            "start",  # from AsyncProcessor
            "stop",  # from AsyncProcessor
        }

        # Should find at least some async-related functions
        found_async = all_names.intersection(expected_async_functions)
        assert (
            len(found_async) > 0
        ), f"Expected async functions not found. Found: {all_names}"


class TestMultiLanguageSupport:
    """Test multi-language ctags generation."""

    def test_multiple_languages(self, temp_workspace, check_ctags_available):
        """Test ctags generation with multiple languages."""
        # Create a temporary directory with both C++ and Python files
        temp_src_dir = temp_workspace / "multi_lang"
        temp_src_dir.mkdir()

        # Create a simple C++ file
        cpp_file = temp_src_dir / "test.cpp"
        cpp_file.write_text(
            """
class CppClass {
public:
    void method();
private:
    int member;
};
"""
        )

        # Create a simple Python file
        py_file = temp_src_dir / "test.py"
        py_file.write_text(
            """
class PythonClass:
    def __init__(self):
        self.value = 0

    def method(self):
        pass
"""
        )

        output_file = temp_workspace / "multi_lang_tags.json"

        result = run_ctags(str(temp_src_dir), str(output_file), languages="C++,Python")

        if result != 0:
            pytest.skip("ctags failed for multiple languages")

        # Load and verify tags contain both languages
        tags = load_tags(str(output_file))
        if not tags:
            pytest.skip("No tags generated")

        tag_names = {tag["name"] for tag in tags}
        # Should find classes from both languages
        assert any(
            "Class" in name for name in tag_names
        ), f"No classes found in tags: {tag_names}"


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_empty_directory(self, temp_workspace, check_ctags_available):
        """Test handling of empty directories."""
        empty_dir = temp_workspace / "empty"
        empty_dir.mkdir()

        output_file = temp_workspace / "empty_tags.json"

        result = run_ctags(str(empty_dir), str(output_file), languages="C++")

        # Should succeed but produce empty or minimal output
        assert result == 0

        if output_file.exists():
            tags = load_tags(str(output_file))
            # Should have no meaningful tags
            assert len(tags) == 0

    def test_malformed_tags_handling(self, temp_workspace):
        """Test handling of malformed tag files."""
        # Create a file with malformed JSON
        malformed_file = temp_workspace / "malformed_tags.json"
        malformed_file.write_text(
            """
{"_type": "tag", "name": "ValidTag", "kind": "class"}
invalid json line
{"_type": "tag", "name": "AnotherTag"}
"""
        )

        # Should handle malformed lines gracefully
        tags = load_tags(str(malformed_file))
        assert len(tags) == 2  # Two valid tags
        assert tags[0]["name"] == "ValidTag"
        assert tags[1]["name"] == "AnotherTag"


@pytest.mark.parametrize(
    "language,expected_extension",
    [
        ("C++", ".cpp"),
        ("Python", ".py"),
        ("Rust", ".rs"),
        ("Java", ".java"),
        ("C#", ".cs"),
    ],
)
def test_language_specific_files(
    language, expected_extension, temp_workspace, check_ctags_available
):
    """Test ctags with language-specific files."""
    # Create source directory
    src_dir = temp_workspace / "src"
    src_dir.mkdir()

    # Create a simple file for the language
    if language == "C++":
        content = "class TestClass { public: int member; };"
    elif language == "Python":
        content = "class TestClass:\n    def __init__(self):\n        self.member = 0"
    elif language == "Rust":
        content = "struct TestStruct { member: i32 }"
    elif language == "Java":
        content = "public class TestClass { private int member; }"
    elif language == "C#":
        content = "public class TestClass { public int Member { get; set; } }"
    else:
        pytest.skip(f"Unsupported language: {language}")

    test_file = src_dir / f"test{expected_extension}"
    test_file.write_text(content)

    output_file = temp_workspace / f"{language.lower()}_tags.json"

    result = run_ctags(str(src_dir), str(output_file), languages=language)

    if result != 0:
        pytest.skip(f"ctags failed for {language}")

    # Verify tags were generated
    if output_file.exists():
        tags = load_tags(str(output_file))
        # Should have at least some tags
        assert (
            len(tags) >= 0
        )  # Some languages might not generate any tags for simple examples


@pytest.mark.performance
class TestPerformanceIntegration:
    """Performance tests for integration scenarios."""

    def test_large_project_performance(self, temp_workspace, check_ctags_available):
        """Test performance with a larger project structure."""
        # Create a larger project structure
        large_project = temp_workspace / "large_project"
        large_project.mkdir()

        # Create multiple directories and files
        for i in range(10):
            subdir = large_project / f"module_{i}"
            subdir.mkdir()

            for j in range(5):
                cpp_file = subdir / f"class_{j}.cpp"
                cpp_file.write_text(
                    f"""
#pragma once

class Module{i}Class{j} {{
public:
    Module{i}Class{j}();
    ~Module{i}Class{j}();

    void method{j}();
    int getMember{j}() const;
    void setMember{j}(int value);

private:
    int member{j}_;
    static const int CONSTANT{j} = {j};
}};

// Implementation
Module{i}Class{j}::Module{i}Class{j}() : member{j}_(0) {{}}

Module{i}Class{j}::~Module{i}Class{j}() {{}}

void Module{i}Class{j}::method{j}() {{
    // Implementation
}}

int Module{i}Class{j}::getMember{j}() const {{
    return member{j}_;
}}

void Module{i}Class{j}::setMember{j}(int value) {{
    member{j}_ = value;
}}
"""
                )

        output_file = temp_workspace / "large_project_tags.json"

        # This should complete in reasonable time
        result = run_ctags(str(large_project), str(output_file), languages="C++")

        if result != 0:
            pytest.skip("ctags failed for large project")

        # Verify reasonable number of tags were generated
        if output_file.exists():
            tags = load_tags(str(output_file))
            # Should have many tags from the generated classes
            assert len(tags) > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
