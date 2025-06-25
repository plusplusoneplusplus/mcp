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
        """Set up test fixtures."""
        # Create a new instance for each test to avoid singleton issues
        EnvironmentManager._instance = None
        self.env_manager = EnvironmentManager()

        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()

        # Store original working directory
        self.original_cwd = os.getcwd()

    def tearDown(self):
        """Clean up after tests."""
        # Clean up temporary files
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Restore original working directory
        os.chdir(self.original_cwd)

    def create_env_file(self, content):
        """Create a temporary .env file with the given content."""
        env_file = Path(self.temp_dir) / ".env"
        env_file.write_text(content)
        return env_file

    def test_initialization(self):
        """Test that EnvironmentManager initializes correctly."""
        self.assertIsInstance(self.env_manager.repository_info, RepositoryInfo)
        self.assertIsInstance(self.env_manager.env_variables, dict)
        self.assertIsInstance(self.env_manager._providers, list)
        self.assertIsInstance(self.env_manager.azrepo_parameters, dict)
        self.assertIsInstance(self.env_manager.kusto_parameters, dict)
        self.assertIsInstance(self.env_manager.settings, dict)

        # Check default settings are loaded
        self.assertIn("git_root", self.env_manager.settings)
        self.assertIn("project_name", self.env_manager.settings)
        self.assertIn("tool_history_enabled", self.env_manager.settings)

    def test_singleton_pattern(self):
        """Test that EnvironmentManager follows singleton pattern."""
        # Reset singleton for this test
        EnvironmentManager._instance = None

        manager1 = EnvironmentManager()
        manager2 = EnvironmentManager()

        self.assertIs(manager1, manager2)

    def test_parse_env_file(self):
        """Test parsing an environment file."""
        # Create a test .env file
        env_content = """
        # Test environment file
        GIT_ROOT=/path/to/git
        PROJECT_NAME=test_project
        PRIVATE_TOOL_ROOT=/path/to/private/tools
        MCP_PATH_DATA=/path/to/data
        AZREPO_ORG=test-org
        KUSTO_CLUSTER=test-cluster
        KUSTO_DATABASE=test-db
        TOOL_HISTORY_ENABLED=false
        TOOL_HISTORY_PATH=/custom/history/path
        """
        env_file = self.create_env_file(env_content)

        # Parse the file
        self.env_manager._parse_env_file(env_file)

        # Check the values were set correctly
        self.assertEqual(self.env_manager.repository_info.git_root, "/path/to/git")
        self.assertEqual(self.env_manager.repository_info.project_name, "test_project")
        self.assertEqual(
            self.env_manager.repository_info.private_tool_root, "/path/to/private/tools"
        )
        self.assertEqual(
            self.env_manager.repository_info.additional_paths.get("data"),
            "/path/to/data",
        )
        self.assertEqual(self.env_manager.azrepo_parameters.get("org"), "test-org")
        self.assertEqual(
            self.env_manager.kusto_parameters.get("cluster"), "test-cluster"
        )
        self.assertEqual(self.env_manager.kusto_parameters.get("database"), "test-db")
        self.assertFalse(self.env_manager.settings["tool_history_enabled"])
        self.assertEqual(
            self.env_manager.settings["tool_history_path"], "/custom/history/path"
        )

    def test_parse_env_file_with_quotes(self):
        """Test parsing an environment file with quoted values."""
        # Create a test .env file with quoted values
        env_content = """
        GIT_ROOT="/path/with spaces/git"
        """
        env_file = self.create_env_file(env_content)

        # Parse the file
        self.env_manager._parse_env_file(env_file)

        # Check the values were set correctly (quotes should be removed)
        self.assertEqual(
            self.env_manager.repository_info.git_root, "/path/with spaces/git"
        )

    def test_register_provider(self):
        """Test registering a provider function."""
        # Create a mock provider function
        provider = mock.Mock(
            return_value={
                "repository": {
                    "git_root": "/provider/git",
                    "additional_paths": {"logs": "/provider/logs"},
                },
                "azrepo_parameters": {"org": "provider-org"},
                "kusto_parameters": {
                    "app_id": "provider-app-id",
                    "app_secret": "provider-app-secret",
                },
            }
        )

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
        self.assertEqual(
            self.env_manager.repository_info.additional_paths.get("logs"),
            "/provider/logs",
        )
        self.assertEqual(self.env_manager.azrepo_parameters.get("org"), "provider-org")
        self.assertEqual(
            self.env_manager.kusto_parameters.get("app_id"), "provider-app-id"
        )
        self.assertEqual(
            self.env_manager.kusto_parameters.get("app_secret"), "provider-app-secret"
        )

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
        self.env_manager.repository_info.project_name = "test_project"
        self.env_manager.repository_info.private_tool_root = "/test/private"
        self.env_manager.repository_info.additional_paths = {"data": "/test/data"}
        self.env_manager.azrepo_parameters = {"org": "test-org"}
        self.env_manager.kusto_parameters = {
            "cluster": "test-cluster",
            "database": "test-db",
        }

        # Get the parameter dictionary
        params = self.env_manager.get_parameter_dict()

        # Check the values
        self.assertEqual(params["git_root"], "/test/git")
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
        self.env_manager.repository_info.project_name = "test_project"
        self.env_manager.repository_info.private_tool_root = "/test/private"
        self.env_manager.repository_info.additional_paths = {"data": "/test/data"}
        self.env_manager.azrepo_parameters = {"org": "test-org"}
        self.env_manager.kusto_parameters = {
            "cluster": "test-cluster",
            "database": "test-db",
        }
        self.env_manager.settings["tool_history_enabled"] = False
        self.env_manager.settings["tool_history_path"] = "/custom/history"

        # Test the getters
        self.assertEqual(self.env_manager.get_git_root(), "/test/git")
        self.assertEqual(self.env_manager.get_project_name(), "test_project")
        self.assertEqual(self.env_manager.get_private_tool_root(), "/test/private")
        self.assertEqual(self.env_manager.get_path("data"), "/test/data")
        expected_azrepo_params = {
            "bearer_token_command": 'az account get-access-token --scope "499b84ac-1321-427f-aa17-267ca6975798/.default"',
            "org": "test-org"
        }
        self.assertEqual(self.env_manager.get_azrepo_parameters(), expected_azrepo_params)
        self.assertEqual(self.env_manager.get_azrepo_parameter("org"), "test-org")
        self.assertIsNone(self.env_manager.get_azrepo_parameter("nonexistent"))
        self.assertEqual(
            self.env_manager.get_azrepo_parameter("nonexistent", "default"), "default"
        )
        self.assertEqual(
            self.env_manager.get_kusto_parameters(),
            {"cluster": "test-cluster", "database": "test-db"},
        )
        self.assertEqual(
            self.env_manager.get_kusto_parameter("cluster"), "test-cluster"
        )
        self.assertEqual(self.env_manager.get_kusto_parameter("database"), "test-db")
        self.assertIsNone(self.env_manager.get_kusto_parameter("nonexistent"))
        self.assertEqual(
            self.env_manager.get_kusto_parameter("nonexistent", "default"), "default"
        )
        self.assertFalse(self.env_manager.is_tool_history_enabled())
        self.assertEqual(self.env_manager.get_tool_history_path(), "/custom/history")

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

        # Call the method
        self.env_manager._load_from_env_file()

        # Check that parse_env_file was called with one of the paths
        mock_parse.assert_called_once()

        # Get the argument it was called with
        call_arg = mock_parse.call_args[0][0]

        # Check it was called with one of the expected paths
        expected_paths = [
            Path("/test/git/.env"),
            Path("/mock/cwd/.env"),
        ]
        self.assertIn(call_arg, expected_paths)

    def test_get_parameter_dict_includes_tool_history(self):
        """Test that the parameter dictionary includes tool history settings."""
        # Set up tool history settings
        self.env_manager.settings["tool_history_enabled"] = False
        self.env_manager.settings["tool_history_path"] = "/custom/history/path"

        # Get the parameter dictionary
        params = self.env_manager.get_parameter_dict()

        # Check the tool history values are included
        self.assertFalse(params["tool_history_enabled"])
        self.assertEqual(params["tool_history_path"], "/custom/history/path")

    def test_env_mapping_dynamic_creation(self):
        """Test that ENV_MAPPING is created dynamically from DEFAULT_SETTINGS."""
        # Check that all DEFAULT_SETTINGS keys are in ENV_MAPPING as uppercase
        for key in EnvironmentManager.DEFAULT_SETTINGS:
            self.assertIn(key.upper(), EnvironmentManager.ENV_MAPPING)
            self.assertEqual(EnvironmentManager.ENV_MAPPING[key.upper()], key)

    def test_job_history_settings_exist(self):
        """Ensure new job history settings are present with defaults."""
        keys = [
            "job_history_persistence_enabled",
            "job_history_storage_backend",
            "job_history_storage_path",
            "job_history_max_entries",
            "job_history_max_age_days",
        ]
        for k in keys:
            self.assertIn(k, EnvironmentManager.DEFAULT_SETTINGS)

    def test_get_setting(self):
        """Test the get_setting method."""
        # Set values in settings
        self.env_manager.settings["test_setting"] = "test_value"
        self.env_manager.settings["empty_setting"] = None

        # Test getting existing setting
        self.assertEqual(self.env_manager.get_setting("test_setting"), "test_value")

        # Test getting setting with None value
        self.assertIsNone(self.env_manager.get_setting("empty_setting"))

        # Test getting non-existent setting with default
        self.assertEqual(
            self.env_manager.get_setting("nonexistent", "default"), "default"
        )

        # Test getting non-existent setting without default
        self.assertIsNone(self.env_manager.get_setting("nonexistent"))

    def test_sync_settings_to_repo(self):
        """Test syncing settings to repository info."""
        # Set values in settings
        self.env_manager.settings["git_root"] = "/settings/git"
        self.env_manager.settings["project_name"] = "settings_project"
        self.env_manager.settings["private_tool_root"] = "/settings/private"

        # Sync to repository info
        self.env_manager._sync_settings_to_repo()

        # Check repository info was updated
        self.assertEqual(self.env_manager.repository_info.git_root, "/settings/git")
        self.assertEqual(
            self.env_manager.repository_info.project_name, "settings_project"
        )
        self.assertEqual(
            self.env_manager.repository_info.private_tool_root, "/settings/private"
        )

    def test_sync_repo_to_settings(self):
        """Test syncing repository info to settings."""
        # Set values in repository info
        self.env_manager.repository_info.git_root = "/repo/git"
        self.env_manager.repository_info.project_name = "repo_project"
        self.env_manager.repository_info.private_tool_root = "/repo/private"

        # Sync to settings
        self.env_manager._sync_repo_to_settings()

        # Check settings were updated
        self.assertEqual(self.env_manager.settings["git_root"], "/repo/git")
        self.assertEqual(self.env_manager.settings["project_name"], "repo_project")
        self.assertEqual(
            self.env_manager.settings["private_tool_root"], "/repo/private"
        )

    def test_load_with_env_vars(self):
        """Test loading with environment variables."""
        # Mock os.environ
        with mock.patch.dict(
            "os.environ",
            {
                "GIT_ROOT": "/env/git",
                "PROJECT_NAME": "env_project",
                "TOOL_HISTORY_ENABLED": "false",
                "MCP_PATH_CUSTOM": "/env/custom",
                "AZREPO_ORG": "env-org",
                "KUSTO_CLUSTER": "env-cluster",
            },
        ):
            # Load environment
            self.env_manager.load()

            # Check values were loaded from environment variables
            self.assertEqual(self.env_manager.repository_info.git_root, "/env/git")
            self.assertEqual(
                self.env_manager.repository_info.project_name, "env_project"
            )
            self.assertFalse(self.env_manager.settings["tool_history_enabled"])
            self.assertEqual(
                self.env_manager.repository_info.additional_paths.get("custom"),
                "/env/custom",
            )
            self.assertEqual(self.env_manager.azrepo_parameters.get("org"), "env-org")
            self.assertEqual(
                self.env_manager.kusto_parameters.get("cluster"), "env-cluster"
            )

    def test_multiple_git_roots_parsing(self):
        """Test parsing multiple git root environment variables."""
        # Create a test .env file with multiple git roots
        env_content = """
        GIT_ROOT=/path/to/main/repo
        GIT_ROOT_PROJECT_A=/path/to/project-a
        GIT_ROOT_PROJECT_B=/path/to/project-b
        GIT_ROOT_MICROSERVICE_X=/path/to/microservice
        """
        env_file = self.create_env_file(env_content)

        # Parse the file
        self.env_manager._parse_env_file(env_file)

        # Check the default git root is set
        self.assertEqual(self.env_manager.repository_info.git_root, "/path/to/main/repo")

        # Check the multiple git roots are set
        expected_git_roots = {
            "project_a": "/path/to/project-a",
            "project_b": "/path/to/project-b",
            "microservice_x": "/path/to/microservice",
        }
        self.assertEqual(self.env_manager.repository_info.git_roots, expected_git_roots)

    def test_get_git_root_with_project_name(self):
        """Test getting git root for specific projects."""
        # Set up multiple git roots
        self.env_manager.repository_info.git_root = "/path/to/main"
        self.env_manager.repository_info.git_roots = {
            "project_a": "/path/to/project-a",
            "project_b": "/path/to/project-b",
        }

        # Test getting specific project git roots
        self.assertEqual(
            self.env_manager.get_git_root("project_a"), "/path/to/project-a"
        )
        self.assertEqual(
            self.env_manager.get_git_root("project_b"), "/path/to/project-b"
        )

        # Test getting non-existent project
        self.assertIsNone(self.env_manager.get_git_root("nonexistent"))

        # Test getting default git root (no project name)
        self.assertEqual(self.env_manager.get_git_root(), "/path/to/main")

    def test_get_git_root_fallback_to_git_roots(self):
        """Test that get_git_root falls back to git_roots when no default git_root."""
        # Set up only named git roots, no default
        self.env_manager.repository_info.git_root = None
        self.env_manager.repository_info.git_roots = {
            "project_a": "/path/to/project-a",
            "project_b": "/path/to/project-b",
        }
        self.env_manager.settings["git_root"] = None

        # Test getting default should return first available git root
        result = self.env_manager.get_git_root()
        self.assertIn(result, ["/path/to/project-a", "/path/to/project-b"])

    def test_get_all_git_roots(self):
        """Test getting all configured git roots."""
        # Set up both default and named git roots
        self.env_manager.repository_info.git_root = "/path/to/main"
        self.env_manager.repository_info.git_roots = {
            "project_a": "/path/to/project-a",
            "project_b": "/path/to/project-b",
        }
        self.env_manager.settings["git_root"] = "/path/to/main"

        # Get all git roots
        all_roots = self.env_manager.get_all_git_roots()

        # Check expected structure
        expected = {
            "default": "/path/to/main",
            "project_a": "/path/to/project-a",
            "project_b": "/path/to/project-b",
        }
        self.assertEqual(all_roots, expected)

    def test_get_all_git_roots_no_default(self):
        """Test getting all git roots when no default is set."""
        # Set up only named git roots
        self.env_manager.repository_info.git_root = None
        self.env_manager.repository_info.git_roots = {
            "project_a": "/path/to/project-a",
            "project_b": "/path/to/project-b",
        }
        self.env_manager.settings["git_root"] = None

        # Get all git roots
        all_roots = self.env_manager.get_all_git_roots()

        # Check expected structure (no default key)
        expected = {
            "project_a": "/path/to/project-a",
            "project_b": "/path/to/project-b",
        }
        self.assertEqual(all_roots, expected)

    def test_get_git_root_projects(self):
        """Test getting list of git root project names."""
        # Set up both default and named git roots
        self.env_manager.repository_info.git_root = "/path/to/main"
        self.env_manager.repository_info.git_roots = {
            "project_a": "/path/to/project-a",
            "project_b": "/path/to/project-b",
        }
        self.env_manager.settings["git_root"] = "/path/to/main"

        # Get project names
        projects = self.env_manager.get_git_root_projects()

        # Check expected list (default should be first)
        expected = ["default", "project_a", "project_b"]
        self.assertEqual(projects, expected)

    def test_get_git_root_projects_no_default(self):
        """Test getting project names when no default is set."""
        # Set up only named git roots
        self.env_manager.repository_info.git_root = None
        self.env_manager.repository_info.git_roots = {
            "project_a": "/path/to/project-a",
            "project_b": "/path/to/project-b",
        }
        self.env_manager.settings["git_root"] = None

        # Get project names
        projects = self.env_manager.get_git_root_projects()

        # Check expected list (no default)
        expected = ["project_a", "project_b"]
        self.assertEqual(projects, expected)

    def test_parameter_dict_includes_git_roots(self):
        """Test that parameter dictionary includes all git roots."""
        # Set up multiple git roots
        self.env_manager.repository_info.git_root = "/path/to/main"
        self.env_manager.repository_info.git_roots = {
            "project_a": "/path/to/project-a",
            "project_b": "/path/to/project-b",
        }
        self.env_manager.settings["git_root"] = "/path/to/main"

        # Get parameter dictionary
        params = self.env_manager.get_parameter_dict()

        # Check that individual git roots are included
        self.assertEqual(params["git_root"], "/path/to/main")
        self.assertEqual(params["git_root_project_a"], "/path/to/project-a")
        self.assertEqual(params["git_root_project_b"], "/path/to/project-b")

    def test_azrepo_default_settings(self):
        """Test that azrepo default settings are applied correctly."""
        # Clear any existing azrepo parameters
        self.env_manager.azrepo_parameters = {}

        # Get parameters should return defaults
        params = self.env_manager.get_azrepo_parameters()
        self.assertIn("bearer_token_command", params)
        self.assertEqual(
            params["bearer_token_command"],
            'az account get-access-token --scope "499b84ac-1321-427f-aa17-267ca6975798/.default"'
        )

        # Test that configured values override defaults
        self.env_manager.azrepo_parameters = {"bearer_token_command": "custom-command"}
        params = self.env_manager.get_azrepo_parameters()
        self.assertEqual(params["bearer_token_command"], "custom-command")

        # Test that other parameters still work with defaults
        self.env_manager.azrepo_parameters = {"org": "test-org"}
        params = self.env_manager.get_azrepo_parameters()
        self.assertEqual(params["org"], "test-org")
        self.assertEqual(
            params["bearer_token_command"],
            'az account get-access-token --scope "499b84ac-1321-427f-aa17-267ca6975798/.default"'
        )

    def test_backward_compatibility(self):
        """Test that existing functionality still works with only GIT_ROOT."""
        # Create a test .env file with only the traditional GIT_ROOT
        env_content = """
        GIT_ROOT=/path/to/traditional/git
        PROJECT_NAME=traditional_project
        """
        env_file = self.create_env_file(env_content)

        # Parse the file
        self.env_manager._parse_env_file(env_file)

        # Check traditional functionality still works
        self.assertEqual(self.env_manager.get_git_root(), "/path/to/traditional/git")
        self.assertEqual(self.env_manager.repository_info.git_root, "/path/to/traditional/git")

        # Check that git_roots is empty but doesn't break anything
        self.assertEqual(self.env_manager.repository_info.git_roots, {})

        # Check parameter dictionary includes the traditional git_root
        params = self.env_manager.get_parameter_dict()
        self.assertEqual(params["git_root"], "/path/to/traditional/git")


if __name__ == "__main__":
    unittest.main()
