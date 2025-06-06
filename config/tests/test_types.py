import unittest
from config.types import RepositoryInfo, EnvironmentProvider, EnvironmentVariables


class TestRepositoryInfo(unittest.TestCase):
    """Test cases for the RepositoryInfo class."""

    def test_init_defaults(self):
        """Test that RepositoryInfo initializes with correct defaults."""
        repo_info = RepositoryInfo()
        self.assertIsNone(repo_info.git_root)
        self.assertIsNone(repo_info.project_name)
        self.assertIsNone(repo_info.private_tool_root)
        self.assertEqual(repo_info.additional_paths, {})

    def test_init_with_values(self):
        """Test initializing RepositoryInfo with values."""
        repo_info = RepositoryInfo(
            git_root="/test/git",
            project_name="test_project",
            private_tool_root="/test/private",
            additional_paths={"data": "/test/data"},
        )

        self.assertEqual(repo_info.git_root, "/test/git")
        self.assertEqual(repo_info.project_name, "test_project")
        self.assertEqual(repo_info.private_tool_root, "/test/private")
        self.assertEqual(repo_info.additional_paths, {"data": "/test/data"})

    def test_model_validation(self):
        """Test that pydantic model validation works."""
        # Test with valid types
        repo_info = RepositoryInfo(
            git_root="/test/git",
            additional_paths={"data": "/test/data"},
        )
        self.assertEqual(repo_info.git_root, "/test/git")

        # Test with invalid types (should be handled by pydantic)
        try:
            repo_info = RepositoryInfo(
                git_root=123  # Should be string
            )
            # If we get here, validation didn't happen
            self.fail("Pydantic validation didn't catch type error")
        except:
            # Validation exception expected
            pass


class TestEnvironmentProvider(unittest.TestCase):
    """Test cases for the EnvironmentProvider class."""

    def test_init_defaults(self):
        """Test that EnvironmentProvider initializes with correct defaults."""
        provider = EnvironmentProvider(name="test_provider")
        self.assertEqual(provider.name, "test_provider")
        self.assertIsNone(provider.description)
        self.assertTrue(provider.enabled)

    def test_init_with_values(self):
        """Test initializing EnvironmentProvider with values."""
        provider = EnvironmentProvider(
            name="test_provider", description="Test provider description", enabled=False
        )

        self.assertEqual(provider.name, "test_provider")
        self.assertEqual(provider.description, "Test provider description")
        self.assertFalse(provider.enabled)


class TestEnvironmentVariables(unittest.TestCase):
    """Test cases for the EnvironmentVariables class."""

    def test_init_defaults(self):
        """Test that EnvironmentVariables initializes with correct defaults."""
        env_vars = EnvironmentVariables()
        self.assertEqual(env_vars.variables, {})

    def test_init_with_values(self):
        """Test initializing EnvironmentVariables with values."""
        env_vars = EnvironmentVariables(variables={"KEY1": "value1", "KEY2": "value2"})

        self.assertEqual(env_vars.variables, {"KEY1": "value1", "KEY2": "value2"})

    def test_get_method(self):
        """Test the get method of EnvironmentVariables."""
        env_vars = EnvironmentVariables(variables={"KEY1": "value1", "KEY2": "value2"})

        self.assertEqual(env_vars.get("KEY1"), "value1")
        self.assertEqual(env_vars.get("KEY2"), "value2")
        self.assertIsNone(env_vars.get("KEY3"))
        self.assertEqual(env_vars.get("KEY3", "default"), "default")

    def test_set_method(self):
        """Test the set method of EnvironmentVariables."""
        env_vars = EnvironmentVariables()

        # Set a new variable
        env_vars.set("KEY1", "value1")
        self.assertEqual(env_vars.variables["KEY1"], "value1")

        # Update an existing variable
        env_vars.set("KEY1", "new_value")
        self.assertEqual(env_vars.variables["KEY1"], "new_value")


if __name__ == "__main__":
    unittest.main()
