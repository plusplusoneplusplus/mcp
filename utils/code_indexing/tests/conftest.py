#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for code indexing tests.

This module provides common fixtures, pytest configuration, and test utilities
used across multiple test modules.
"""

import os
import subprocess
import tempfile
import pytest
from pathlib import Path
import shutil


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may be slow)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "requires_ctags: marks tests that require ctags to be installed"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add integration marker to integration tests
        if "integration" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)

        # Add slow marker to performance tests
        if "performance" in item.nodeid.lower():
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.performance)

        # Add requires_ctags marker to tests that need ctags
        if any(keyword in item.nodeid.lower() for keyword in ["ctags", "integration"]):
            item.add_marker(pytest.mark.requires_ctags)


@pytest.fixture(scope="session")
def ctags_available():
    """Check if ctags is available for testing."""
    try:
        result = subprocess.run(
            ["ctags", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def ctags_info(ctags_available):
    """Get information about the available ctags installation."""
    if not ctags_available:
        pytest.skip("ctags not available")

    try:
        result = subprocess.run(
            ["ctags", "--version"],
            capture_output=True,
            text=True
        )
        version_info = result.stdout.strip()

        # Check for language support
        list_result = subprocess.run(
            ["ctags", "--list-languages"],
            capture_output=True,
            text=True
        )
        languages = set(list_result.stdout.strip().split('\n')) if list_result.returncode == 0 else set()

        return {
            "version": version_info,
            "languages": languages,
            "supports_cpp": "C++" in languages,
            "supports_rust": "Rust" in languages,
            "supports_python": "Python" in languages,
        }
    except subprocess.SubprocessError:
        return {"version": "unknown", "languages": set()}


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path

    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def temp_file():
    """Create a temporary file for tests."""
    fd, temp_path = tempfile.mkstemp()
    os.close(fd)
    temp_file_path = Path(temp_path)
    yield temp_file_path

    # Cleanup
    if temp_file_path.exists():
        temp_file_path.unlink()


@pytest.fixture(scope="module")
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="module")
def sample_cpp_project(project_root):
    """Get path to sample C++ project."""
    cpp_project = project_root / "tests" / "sample_cpp_project"
    if not cpp_project.exists():
        pytest.skip("C++ sample project not found")
    return cpp_project


@pytest.fixture(scope="module")
def sample_rust_project(project_root):
    """Get path to sample Rust project."""
    rust_project = project_root / "tests" / "sample_rust_project"
    if not rust_project.exists():
        pytest.skip("Rust sample project not found")
    return rust_project


@pytest.fixture
def minimal_cpp_code():
    """Provide minimal C++ code for testing."""
    return """
class MinimalClass {
public:
    MinimalClass();
    void publicMethod();
    int publicMember;

private:
    void privateMethod();
    int privateMember;

protected:
    void protectedMethod();
    int protectedMember;
};

struct MinimalStruct {
    int data;
    void process();
};

namespace TestNamespace {
    class NamespacedClass {
    public:
        void method();
    };
}
"""


@pytest.fixture
def minimal_rust_code():
    """Provide minimal Rust code for testing."""
    return """
pub struct MinimalStruct {
    pub public_field: i32,
    private_field: String,
}

impl MinimalStruct {
    pub fn new() -> Self {
        Self {
            public_field: 0,
            private_field: String::new(),
        }
    }

    pub fn public_method(&self) -> i32 {
        self.public_field
    }

    fn private_method(&mut self) {
        self.private_field.clear();
    }
}

pub enum MinimalEnum {
    Variant1,
    Variant2(i32),
    Variant3 { field: String },
}

pub trait MinimalTrait {
    fn trait_method(&self);
}

impl MinimalTrait for MinimalStruct {
    fn trait_method(&self) {
        println!("Implementation");
    }
}
"""


@pytest.fixture
def sample_tags():
    """Provide sample tag data for testing."""
    return [
        {
            "_type": "tag",
            "name": "TestClass",
            "kind": "class",
            "path": "/test/TestClass.cpp",
            "line": 5,
        },
        {
            "_type": "tag",
            "name": "publicMember",
            "kind": "member",
            "path": "/test/TestClass.cpp",
            "line": 7,
            "scope": "TestClass",
            "scopeKind": "class",
            "access": "public",
            "typeref": "typename:int",
        },
        {
            "_type": "tag",
            "name": "publicMethod",
            "kind": "method",
            "path": "/test/TestClass.cpp",
            "line": 8,
            "scope": "TestClass",
            "scopeKind": "class",
            "access": "public",
            "signature": "()",
        },
    ]


@pytest.fixture
def create_test_source_file():
    """Factory fixture to create test source files."""
    created_files = []

    def _create_file(content, filename, directory=None):
        if directory is None:
            directory = Path(tempfile.mkdtemp())
        else:
            directory = Path(directory)
            directory.mkdir(parents=True, exist_ok=True)

        file_path = directory / filename
        file_path.write_text(content)
        created_files.append(file_path)
        return file_path

    yield _create_file

    # Cleanup
    for file_path in created_files:
        if file_path.exists():
            file_path.unlink()
        # Try to remove parent directory if empty
        try:
            file_path.parent.rmdir()
        except OSError:
            pass  # Directory not empty or doesn't exist


class TestHelpers:
    """Helper utilities for tests."""

    @staticmethod
    def create_tag_file(tags, file_path):
        """Create a tag file from tag data."""
        import json
        with open(file_path, 'w') as f:
            for tag in tags:
                f.write(json.dumps(tag) + '\n')

    @staticmethod
    def assert_tag_exists(tags, name, kind=None):
        """Assert that a tag with given name (and optionally kind) exists."""
        matching_tags = [t for t in tags if t.get("name") == name]
        assert len(matching_tags) > 0, f"Tag '{name}' not found in tags"

        if kind:
            kind_matches = [t for t in matching_tags if t.get("kind") == kind]
            assert len(kind_matches) > 0, f"Tag '{name}' with kind '{kind}' not found"

    @staticmethod
    def assert_class_has_members(by_class, class_name, expected_members):
        """Assert that a class has expected members."""
        assert class_name in by_class, f"Class '{class_name}' not found in index"

        class_tags = by_class[class_name]
        member_names = {
            tag["name"] for tag in class_tags
            if tag.get("kind") in ("member", "method")
        }

        for member in expected_members:
            assert member in member_names, f"Member '{member}' not found in class '{class_name}'"


@pytest.fixture
def test_helpers():
    """Provide test helper utilities."""
    return TestHelpers


# Custom pytest markers for better test organization
pytestmark = [
    pytest.mark.filterwarnings("ignore:.*:DeprecationWarning"),
]


def pytest_runtest_setup(item):
    """Setup hook for individual tests."""
    # Skip integration tests if ctags is not available (unless forced)
    if item.get_closest_marker("requires_ctags"):
        if not _check_ctags_quick():
            pytest.skip("ctags not available")


def _check_ctags_quick():
    """Quick check if ctags is available."""
    try:
        result = subprocess.run(
            ["ctags", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False
