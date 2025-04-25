import os
import pytest
from pathlib import Path
from unittest import mock
from server.environment import Environment, RepositoryInfo, get_git_root, get_workspace_folder, get_project_name, get_path, get_private_tool_root, env

# Fixture to reset the singleton before each test
@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the Environment singleton before each test"""
    # Store the original instance
    original_instance = Environment._instance
    # Reset the singleton
    Environment._instance = None
    # Run the test
    yield
    # Restore the original instance after the test
    Environment._instance = original_instance

class TestEnvironment:
    def test_singleton_pattern(self):
        """Test that Environment class follows singleton pattern"""
        env1 = Environment()
        env2 = Environment()
        assert env1 is env2

    def test_initialization(self):
        """Test that environment is initialized with default values"""
        with mock.patch.dict(os.environ, {}, clear=True):
            env = Environment()
            env._instance = None  # Reset singleton for testing
            env = Environment()
            
            assert isinstance(env.repository_info, RepositoryInfo)
            assert env.repository_info.git_root is None
            assert env.repository_info.workspace_folder is None
            assert env.repository_info.project_name is None
            assert env.repository_info.additional_paths == {}
            assert env.repository_info.private_tool_root is None

    def test_load_from_env_variables(self):
        """Test loading repository information from environment variables"""
        test_env = {
            "GIT_ROOT": "/path/to/git",
            "WORKSPACE_FOLDER": "/path/to/workspace",
            "PROJECT_NAME": "test-project",
            "MCP_PATH_SRC": "/path/to/src",
            "MCP_PATH_TESTS": "/path/to/tests",
            "PRIVATE_TOOL_ROOT": "/path/to/private/tools",
            "OTHER_VAR": "other-value"
        }
        
        with mock.patch.dict(os.environ, test_env, clear=True):
            env = Environment()
            env._instance = None  # Reset singleton for testing
            env = Environment()
            env.load()  # Explicitly load environment variables
            
            assert env.repository_info.git_root == "/path/to/git"
            assert env.repository_info.workspace_folder == "/path/to/workspace"
            assert env.repository_info.project_name == "test-project"
            assert env.repository_info.additional_paths["src"] == "/path/to/src"
            assert env.repository_info.additional_paths["tests"] == "/path/to/tests"
            assert env.repository_info.private_tool_root == "/path/to/private/tools"
            assert "OTHER_VAR" in env.env_variables
            assert env.env_variables["OTHER_VAR"] == "other-value"

    def test_provider_registration(self):
        """Test provider registration and data integration"""
        def mock_provider():
            return {
                "repository": {
                    "git_root": "/provider/git",
                    "workspace_folder": "/provider/workspace",
                    "project_name": "provider-project",
                    "private_tool_root": "/provider/private/tools",
                    "additional_paths": {
                        "data": "/provider/data"
                    }
                }
            }
        
        with mock.patch.dict(os.environ, {}, clear=True):
            env = Environment()
            env._instance = None  # Reset singleton for testing
            env = Environment()
            
            # Register and load the provider
            env.register_provider(mock_provider)
            env.load()
            
            # Verify the provider data was integrated
            assert env.repository_info.git_root == "/provider/git"
            assert env.repository_info.workspace_folder == "/provider/workspace"
            assert env.repository_info.project_name == "provider-project"
            assert env.repository_info.private_tool_root == "/provider/private/tools"
            assert env.repository_info.additional_paths["data"] == "/provider/data"

    def test_provider_exception_handling(self):
        """Test that exceptions from providers are properly handled"""
        def failing_provider():
            raise Exception("Provider failure")
        
        with mock.patch.dict(os.environ, {}, clear=True):
            env = Environment()
            env._instance = None  # Reset singleton for testing
            env = Environment()
            
            # Register the failing provider
            env.register_provider(failing_provider)
            
            # Should not raise exception
            try:
                env.load()
                assert True  # If we get here, no exception was raised
            except Exception:
                assert False, "Exception was not properly handled"

    def test_get_parameter_dict(self):
        """Test parameter dictionary generation"""
        test_env = {
            "GIT_ROOT": "/path/to/git",
            "WORKSPACE_FOLDER": "/path/to/workspace",
            "PROJECT_NAME": "test-project",
            "PRIVATE_TOOL_ROOT": "/path/to/private/tools",
            "MCP_PATH_SRC": "/path/to/src"
        }
        
        with mock.patch.dict(os.environ, test_env, clear=True):
            env = Environment()
            env._instance = None  # Reset singleton for testing
            env = Environment()
            env.load()  # Explicitly load environment variables
            
            params = env.get_parameter_dict()
            
            assert params["git_root"] == "/path/to/git"
            assert params["workspace_folder"] == "/path/to/workspace"
            assert params["project_name"] == "test-project"
            assert params["private_tool_root"] == "/path/to/private/tools"
            assert params["path_src"] == "/path/to/src"

class TestHelperFunctions:
    """Test helper functions that access the Environment singleton"""
    
    def test_get_git_root(self):
        """Test get_git_root helper function"""
        with mock.patch.dict(os.environ, {"GIT_ROOT": "/test/git"}, clear=True):
            # Create a new singleton instance
            Environment._instance = None
            new_env = Environment()
            new_env.load()  # Explicitly load environment variables
            
            # Update the global env reference used by helper functions
            import server.environment
            server.environment.env = new_env
            
            assert get_git_root() == "/test/git"
    
    def test_get_workspace_folder(self):
        """Test get_workspace_folder helper function"""
        with mock.patch.dict(os.environ, {"WORKSPACE_FOLDER": "/test/workspace"}, clear=True):
            # Create a new singleton instance
            Environment._instance = None
            new_env = Environment()
            new_env.load()  # Explicitly load environment variables
            
            # Update the global env reference used by helper functions
            import server.environment
            server.environment.env = new_env
            
            assert get_workspace_folder() == "/test/workspace"
    
    def test_get_project_name(self):
        """Test get_project_name helper function"""
        with mock.patch.dict(os.environ, {"PROJECT_NAME": "test-project"}, clear=True):
            # Create a new singleton instance
            Environment._instance = None
            new_env = Environment()
            new_env.load()  # Explicitly load environment variables
            
            # Update the global env reference used by helper functions
            import server.environment
            server.environment.env = new_env
            
            assert get_project_name() == "test-project"
    
    def test_get_path(self):
        """Test get_path helper function"""
        with mock.patch.dict(os.environ, {"MCP_PATH_CONFIG": "/test/config"}, clear=True):
            # Create a new singleton instance
            Environment._instance = None
            new_env = Environment()
            new_env.load()  # Explicitly load environment variables
            
            # Update the global env reference used by helper functions
            import server.environment
            server.environment.env = new_env
            
            assert get_path("config") == "/test/config"
            assert get_path("nonexistent") is None
    
    def test_get_private_tool_root(self):
        """Test get_private_tool_root helper function"""
        with mock.patch.dict(os.environ, {"PRIVATE_TOOL_ROOT": "/test/private/tools"}, clear=True):
            # Create a new singleton instance
            Environment._instance = None
            new_env = Environment()
            new_env.load()  # Explicitly load environment variables
            
            # Update the global env reference used by helper functions
            import server.environment
            server.environment.env = new_env
            
            assert get_private_tool_root() == "/test/private/tools"

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 