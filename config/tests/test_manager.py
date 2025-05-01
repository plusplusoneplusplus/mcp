import os
import unittest
from unittest import mock
from pathlib import Path
import tempfile

from config.manager import EnvironmentManager
from config.types import RepositoryInfo


class TestEnvironmentManager(unittest.TestCase):
    """Test cases for the EnvironmentManager class."""

    def setUp(self):
        """Set up tests by creating a new EnvironmentManager instance."""
        # Create a mock for the singleton's __new__ method to allow multiple instances in tests
        self.original_new = EnvironmentManager.__new__
        EnvironmentManager.__new__ = lambda cls: object.__new__(cls)
        
        # Create a clean instance
        self.env_manager = EnvironmentManager()
        self.env_manager._initialize()
        
        # Create a temporary directory for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up after tests."""
        # Restore the original __new__ method
        EnvironmentManager.__new__ = self.original_new
        
        # Clean up the temporary directory
        self.temp_dir.cleanup()

    def create_env_file(self, content):
        """Create a .env file with the given content in the test directory."""
        env_file = self.test_dir / ".env"
        with open(env_file, "w") as f:
            f.write(content)
        return env_file

    def test_initialization(self):
        """Test that EnvironmentManager initializes correctly."""
        self.assertIsInstance(self.env_manager.repository_info, RepositoryInfo)
        self.assertIsInstance(self.env_manager.env_variables, dict)
        self.assertIsInstance(self.env_manager._providers, list)
        self.assertIsInstance(self.env_manager.azrepo_parameters, dict)
        self.assertIsInstance(self.env_manager.kusto_parameters, dict)

    def test_singleton_pattern(self):
        """Test that EnvironmentManager follows the singleton pattern."""
        # Reset to allow testing singleton behavior
        EnvironmentManager.__new__ = self.original_new
        
        # Get two instances
        instance1 = EnvironmentManager()
        instance2 = EnvironmentManager()
        
        # They should be the same object
        self.assertIs(instance1, instance2)

    def test_parse_env_file(self):
        """Test parsing an environment file."""
        # Create a test .env file
        env_content = """
        # Test environment file
        GIT_ROOT=/path/to/git
        WORKSPACE_FOLDER=/path/to/workspace
        PROJECT_NAME=test_project
        PRIVATE_TOOL_ROOT=/path/to/private/tools
        MCP_PATH_DATA=/path/to/data
        AZREPO_ORG=test-org
        KUSTO_CLUSTER=test-cluster
        KUSTO_DATABASE=test-db
        """
        env_file = self.create_env_file(env_content)
        
        # Parse the file
        self.env_manager._parse_env_file(env_file)
        
        # Check the values were set correctly
        self.assertEqual(self.env_manager.repository_info.git_root, "/path/to/git")
        self.assertEqual(self.env_manager.repository_info.workspace_folder, "/path/to/workspace")
        self.assertEqual(self.env_manager.repository_info.project_name, "test_project")
        self.assertEqual(self.env_manager.repository_info.private_tool_root, "/path/to/private/tools")
        self.assertEqual(self.env_manager.repository_info.additional_paths.get("data"), "/path/to/data")
        self.assertEqual(self.env_manager.azrepo_parameters.get("org"), "test-org")
        self.assertEqual(self.env_manager.kusto_parameters.get("cluster"), "test-cluster")
        self.assertEqual(self.env_manager.kusto_parameters.get("database"), "test-db")

    def test_parse_env_file_with_quotes(self):
        """Test parsing an environment file with quoted values."""
        # Create a test .env file with quoted values
        env_content = """
        GIT_ROOT="/path/with spaces/git"
        WORKSPACE_FOLDER='/path/with spaces/workspace'
        """
        env_file = self.create_env_file(env_content)
        
        # Parse the file
        self.env_manager._parse_env_file(env_file)
        
        # Check the values were set correctly (quotes should be removed)
        self.assertEqual(self.env_manager.repository_info.git_root, "/path/with spaces/git")
        self.assertEqual(self.env_manager.repository_info.workspace_folder, "/path/with spaces/workspace")

    def test_register_provider(self):
        """Test registering a provider function."""
        # Create a mock provider function
        provider = mock.Mock(return_value={
            "repository": {
                "git_root": "/provider/git",
                "workspace_folder": "/provider/workspace",
                "additional_paths": {"logs": "/provider/logs"}
            },
            "azrepo_parameters": {
                "token": "provider-token"
            },
            "kusto_parameters": {
                "app_id": "provider-app-id",
                "app_secret": "provider-app-secret"
            }
        })
        
        # Register the provider
        self.env_manager.register_provider(provider)
        
        # Check the provider was registered
        self.assertIn(provider, self.env_manager._providers)
        
        # Load from the provider
        self.env_manager.load()
        
        # Check the provider was called
        provider.assert_called_once()
        
        # Check the values were loaded
        self.assertEqual(self.env_manager.repository_info.git_root, "/provider/git")
        self.assertEqual(self.env_manager.repository_info.workspace_folder, "/provider/workspace")
        self.assertEqual(self.env_manager.repository_info.additional_paths.get("logs"), "/provider/logs")
        self.assertEqual(self.env_manager.azrepo_parameters.get("token"), "provider-token")
        self.assertEqual(self.env_manager.kusto_parameters.get("app_id"), "provider-app-id")
        self.assertEqual(self.env_manager.kusto_parameters.get("app_secret"), "provider-app-secret")

    def test_provider_exception_handling(self):
        """Test that exceptions from providers are handled gracefully."""
        # Create a provider that raises an exception
        def failing_provider():
            raise Exception("Provider failure test")
        
        # Register the provider
        self.env_manager.register_provider(failing_provider)
        
        # Load should not raise an exception
        try:
            self.env_manager.load()
        except Exception:
            self.fail("load() raised an exception from a failing provider")

    def test_get_parameter_dict(self):
        """Test getting a parameter dictionary."""
        # Set up repository info
        self.env_manager.repository_info.git_root = "/test/git"
        self.env_manager.repository_info.workspace_folder = "/test/workspace"
        self.env_manager.repository_info.project_name = "test_project"
        self.env_manager.repository_info.private_tool_root = "/test/private"
        self.env_manager.repository_info.additional_paths = {"data": "/test/data"}
        self.env_manager.azrepo_parameters = {"org": "test-org"}
        self.env_manager.kusto_parameters = {"cluster": "test-cluster", "database": "test-db"}
        
        # Get the parameter dictionary
        params = self.env_manager.get_parameter_dict()
        
        # Check the values
        self.assertEqual(params["git_root"], "/test/git")
        self.assertEqual(params["workspace_folder"], "/test/workspace")
        self.assertEqual(params["project_name"], "test_project")
        self.assertEqual(params["private_tool_root"], "/test/private")
        self.assertEqual(params["path_data"], "/test/data")
        self.assertEqual(params["azrepo_org"], "test-org")
        self.assertEqual(params["cluster"], "test-cluster")
        self.assertEqual(params["database"], "test-db")

    def test_get_methods(self):
        """Test the getter methods."""
        # Set up repository info
        self.env_manager.repository_info.git_root = "/test/git"
        self.env_manager.repository_info.workspace_folder = "/test/workspace"
        self.env_manager.repository_info.project_name = "test_project"
        self.env_manager.repository_info.private_tool_root = "/test/private"
        self.env_manager.repository_info.additional_paths = {"data": "/test/data"}
        self.env_manager.azrepo_parameters = {"org": "test-org"}
        self.env_manager.kusto_parameters = {"cluster": "test-cluster", "database": "test-db"}
        
        # Test the getters
        self.assertEqual(self.env_manager.get_git_root(), "/test/git")
        self.assertEqual(self.env_manager.get_workspace_folder(), "/test/workspace")
        self.assertEqual(self.env_manager.get_project_name(), "test_project")
        self.assertEqual(self.env_manager.get_private_tool_root(), "/test/private")
        self.assertEqual(self.env_manager.get_path("data"), "/test/data")
        self.assertEqual(self.env_manager.get_azrepo_parameters(), {"org": "test-org"})
        self.assertEqual(self.env_manager.get_azrepo_parameter("org"), "test-org")
        self.assertIsNone(self.env_manager.get_azrepo_parameter("nonexistent"))
        self.assertEqual(self.env_manager.get_azrepo_parameter("nonexistent", "default"), "default")
        self.assertEqual(self.env_manager.get_kusto_parameters(), {"cluster": "test-cluster", "database": "test-db"})
        self.assertEqual(self.env_manager.get_kusto_parameter("cluster"), "test-cluster")
        self.assertEqual(self.env_manager.get_kusto_parameter("database"), "test-db")
        self.assertIsNone(self.env_manager.get_kusto_parameter("nonexistent"))
        self.assertEqual(self.env_manager.get_kusto_parameter("nonexistent", "default"), "default")

    @mock.patch("config.manager.Path.exists")
    @mock.patch("config.manager.Path.is_file")
    @mock.patch("config.manager.Path.cwd")
    @mock.patch("config.manager.EnvironmentManager._parse_env_file")
    def test_load_from_env_file(self, mock_parse, mock_cwd, mock_is_file, mock_exists):
        """Test loading from an environment file."""
        # Set up mocks
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_cwd.return_value = Path("/mock/cwd")
        
        # Set up repository info
        self.env_manager.repository_info.git_root = "/test/git"
        self.env_manager.repository_info.workspace_folder = "/test/workspace"
        
        # Call the method
        self.env_manager._load_from_env_file()
        
        # Check that parse_env_file was called with one of the paths
        mock_parse.assert_called_once()
        
        # Get the argument it was called with
        call_arg = mock_parse.call_args[0][0]
        
        # Check it was called with one of the expected paths
        expected_paths = [
            Path("/test/workspace/.env"),
            Path("/test/git/.env"),
            Path("/mock/cwd/.env")
        ]
        self.assertIn(call_arg, expected_paths)


if __name__ == "__main__":
    unittest.main() 