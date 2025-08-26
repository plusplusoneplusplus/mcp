#!/usr/bin/env python3
"""
Pytest test cases for generate_ctags.py script.

This module tests the ctags generation functionality with various scenarios:
- Valid and invalid source directories
- Different programming languages
- Custom output files
- Additional ctags parameters
"""

import json
import os
import subprocess
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import from the parent package
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from utils.code_indexing import run_ctags
from utils.code_indexing.generator import main_generator


class TestGenerateCtags:
    """Test cases for generate_ctags module using pytest."""

    @pytest.fixture
    def temp_setup(self):
        """Set up temporary test environment."""
        test_dir = tempfile.mkdtemp()
        test_output = os.path.join(test_dir, "test_tags.json")
        yield test_dir, test_output

        # Cleanup
        if os.path.exists(test_output):
            os.remove(test_output)
        if os.path.exists(test_dir):
            os.rmdir(test_dir)

    def test_nonexistent_source_directory(self, temp_setup):
        """Test handling of non-existent source directory."""
        test_dir, test_output = temp_setup
        nonexistent_dir = "/path/that/does/not/exist"
        result = run_ctags(nonexistent_dir, test_output)
        assert result == 1

    @patch("subprocess.run")
    def test_successful_ctags_execution(self, mock_run, temp_setup):
        """Test successful ctags execution."""
        test_dir, test_output = temp_setup
        mock_run.return_value = MagicMock(returncode=0)

        result = run_ctags(test_dir, test_output)

        assert result == 0
        mock_run.assert_called_once()

        # Verify command structure - since we use shell=True, the command is a string
        called_args = mock_run.call_args[0][0]  # This is the shell command string
        assert "ctags" in called_args
        assert "-R" in called_args
        assert "--languages=C++" in called_args
        assert "--output-format=json" in called_args

    @patch("subprocess.run")
    def test_ctags_with_custom_languages(self, mock_run, temp_setup):
        """Test ctags with custom language specification."""
        test_dir, test_output = temp_setup
        mock_run.return_value = MagicMock(returncode=0)

        result = run_ctags(test_dir, test_output, languages="Python,Rust")

        assert result == 0
        called_args = mock_run.call_args[0][0]  # This is the shell command string
        assert "--languages=Python,Rust" in called_args

    @patch("subprocess.run")
    def test_ctags_with_additional_args(self, mock_run, temp_setup):
        """Test ctags with additional arguments."""
        test_dir, test_output = temp_setup
        mock_run.return_value = MagicMock(returncode=0)
        additional_args = ["--extras=+f", "--fields=+l"]

        result = run_ctags(test_dir, test_output, additional_args=additional_args)

        assert result == 0
        called_args = mock_run.call_args[0][0]  # This is the shell command string
        assert "--extras=+f" in called_args
        assert "--fields=+l" in called_args

    @patch("subprocess.run")
    def test_ctags_command_not_found(self, mock_run, temp_setup):
        """Test handling when ctags command is not found."""
        test_dir, test_output = temp_setup
        mock_run.side_effect = FileNotFoundError()

        result = run_ctags(test_dir, test_output)

        assert result == 1

    @patch("subprocess.run")
    def test_ctags_execution_error(self, mock_run, temp_setup):
        """Test handling of ctags execution errors."""
        test_dir, test_output = temp_setup
        mock_run.side_effect = subprocess.CalledProcessError(2, "ctags")

        result = run_ctags(test_dir, test_output)

        assert result == 2

    @patch("sys.argv", ["generate_ctags.py", "test_dir"])
    @patch("utils.code_indexing.generator.run_ctags")
    def test_main_basic_usage(self, mock_run_ctags):
        """Test main function with basic arguments."""
        mock_run_ctags.return_value = 0

        with patch("sys.exit") as mock_exit:
            main_generator()
            mock_exit.assert_called_with(0)

        mock_run_ctags.assert_called_once_with(
            source_dir="test_dir",
            output_file="tags.json",
            languages="C++",
            additional_args=None,
        )

    @patch(
        "sys.argv",
        [
            "generate_ctags.py",
            "src/",
            "-o",
            "custom.json",
            "--languages",
            "Python,Rust",
        ],
    )
    @patch("utils.code_indexing.generator.run_ctags")
    def test_main_with_options(self, mock_run_ctags):
        """Test main function with custom options."""
        mock_run_ctags.return_value = 0

        with patch("sys.exit") as mock_exit:
            main_generator()
            mock_exit.assert_called_with(0)

        mock_run_ctags.assert_called_once_with(
            source_dir="src/",
            output_file="custom.json",
            languages="Python,Rust",
            additional_args=None,
        )

    @patch(
        "sys.argv", ["generate_ctags.py", "code/", "--extras", "+f", "--fields", "+l"]
    )
    @patch("utils.code_indexing.generator.run_ctags")
    def test_main_with_extras_and_fields(self, mock_run_ctags):
        """Test main function with extras and fields options."""
        mock_run_ctags.return_value = 0

        with patch("sys.exit") as mock_exit:
            main_generator()
            mock_exit.assert_called_with(0)

        mock_run_ctags.assert_called_once_with(
            source_dir="code/",
            output_file="tags.json",
            languages="C++",
            additional_args=["--extras", "+f", "--fields", "+l"],
        )


class TestGenerateCtagsIntegration:
    """Integration tests that actually run ctags on test projects."""

    @pytest.fixture
    def temp_cpp_project(self):
        """Set up test environment with sample C++ code."""
        test_dir = tempfile.mkdtemp()
        test_output = os.path.join(test_dir, "integration_tags.json")

        # Create a simple C++ file for testing
        cpp_file = os.path.join(test_dir, "test.cpp")
        with open(cpp_file, "w") as f:
            f.write(
                """
class TestClass {
public:
    int publicMember;
    void publicMethod();
private:
    int privateMember;
};

struct TestStruct {
    int data;
    void process();
};

void globalFunction() {
    // Implementation
}
"""
            )

        yield test_dir, test_output, cpp_file

        # Cleanup
        if os.path.exists(cpp_file):
            os.remove(cpp_file)
        if os.path.exists(test_output):
            os.remove(test_output)
        if os.path.exists(test_dir):
            os.rmdir(test_dir)

    def test_integration_cpp_project(self, temp_cpp_project):
        """Test integration with actual C++ project."""
        test_dir, test_output, cpp_file = temp_cpp_project

        try:
            # Run ctags on test directory
            result = run_ctags(test_dir, test_output, languages="C++")

            # Check if ctags is available
            if result == 1 and not os.path.exists(test_output):
                pytest.skip("ctags not available in test environment")

            assert result == 0
            assert os.path.exists(test_output)

            # Verify JSON output contains expected tags
            with open(test_output, "r") as f:
                content = f.read()
                assert "TestClass" in content
                assert "TestStruct" in content

        except FileNotFoundError:
            pytest.skip("ctags not available in test environment")


@pytest.mark.parametrize(
    "languages,expected_lang",
    [
        ("C++", "--languages=C++"),
        ("Python", "--languages=Python"),
        ("Rust", "--languages=Rust"),
        ("C#", "--languages=C#"),
        ("Python,Rust", "--languages=Python,Rust"),
        ("C++,Python,Rust", "--languages=C++,Python,Rust"),
        ("C#,Python", "--languages=C#,Python"),
        ("C++,C#,Python,Rust", "--languages=C++,C#,Python,Rust"),
    ],
)
@patch("subprocess.run")
def test_parametrized_languages(mock_run, languages, expected_lang):
    """Test various language configurations using parametrized tests."""
    mock_run.return_value = MagicMock(returncode=0)
    test_dir = tempfile.mkdtemp()
    test_output = os.path.join(test_dir, "test_tags.json")

    try:
        result = run_ctags(test_dir, test_output, languages=languages)

        assert result == 0
        called_args = mock_run.call_args[0][0]  # This is the shell command string
        assert expected_lang in called_args
    finally:
        if os.path.exists(test_dir):
            os.rmdir(test_dir)


@pytest.mark.parametrize(
    "additional_args,expected_args",
    [
        (["--extras=+f"], ["--extras=+f"]),
        (["--fields=+l"], ["--fields=+l"]),
        (["--extras=+f", "--fields=+l"], ["--extras=+f", "--fields=+l"]),
        (["--tag-relative=never"], ["--tag-relative=never"]),
    ],
)
@patch("subprocess.run")
def test_parametrized_additional_args(mock_run, additional_args, expected_args):
    """Test various additional argument configurations."""
    mock_run.return_value = MagicMock(returncode=0)
    test_dir = tempfile.mkdtemp()
    test_output = os.path.join(test_dir, "test_tags.json")

    try:
        result = run_ctags(test_dir, test_output, additional_args=additional_args)

        assert result == 0
        called_args = mock_run.call_args[0][0]  # This is the shell command string
        for expected_arg in expected_args:
            assert expected_arg in called_args
    finally:
        if os.path.exists(test_dir):
            os.rmdir(test_dir)


@pytest.mark.integration
class TestCtagsCommands:
    """Integration tests that require actual ctags installation."""

    @pytest.fixture(scope="class")
    def check_ctags_available(self):
        """Check if ctags is available and skip tests if not."""
        try:
            result = subprocess.run(
                ["ctags", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                pytest.skip("ctags not available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("ctags not available")

    def test_ctags_version_check(self, check_ctags_available):
        """Test that ctags version can be retrieved."""
        result = subprocess.run(["ctags", "--version"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "ctags" in result.stdout.lower() or "universal" in result.stdout.lower()

    def test_ctags_help_command(self, check_ctags_available):
        """Test that ctags help command works."""
        result = subprocess.run(["ctags", "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "options" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
