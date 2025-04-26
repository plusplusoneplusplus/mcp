import os
import pytest
from pathlib import Path
from unittest import mock

from config import env, env_manager

class TestServerEnvironmentIntegration:
    """Test that server modules correctly use the config environment"""
    
    @pytest.fixture(autouse=True)
    def reset_environment(self):
        """Reset the environment manager for each test"""
        original_env = env_manager
        env_manager._initialize()
        yield
        # No need to restore as the singleton will persist
    
    def test_prompt_loading_uses_config(self):
        """Test that the prompts module uses the config environment"""
        # Create a temporary directory for testing
        with mock.patch.dict(os.environ, {"PRIVATE_TOOL_ROOT": "/mock/private/tools"}, clear=True):
            # Reload environment manager
            env_manager.load()
            
            # Verify the environment is set correctly
            assert env.get_private_tool_root() == "/mock/private/tools"
            
            # Mock the file existence and open function to simulate loading prompts
            with mock.patch("pathlib.Path.exists", return_value=True):
                with mock.patch("builtins.open", mock.mock_open(read_data="""
prompts:
  test_prompt:
    name: Test Prompt
    description: A test prompt loaded from mock
    enabled: true
""")):
                    # Import the prompts module
                    from server.prompts import load_prompts_from_yaml
                    
                    # Load prompts and verify they were loaded correctly
                    prompts = load_prompts_from_yaml()
                    
                    # Verify that the prompts were loaded
                    assert "test_prompt" in prompts
                    assert prompts["test_prompt"]["description"] == "A test prompt loaded from mock"
    
    def test_main_server_uses_config(self):
        """Test that the main server uses the config environment"""
        test_env = {
            "WORKSPACE_FOLDER": "/test/workspace",
            "GIT_ROOT": "/test/git",
            "PROJECT_NAME": "test-project",
        }
        
        with mock.patch.dict(os.environ, test_env, clear=True):
            # Reload environment
            env_manager.load()
            
            # Verify environment values
            assert env.get_workspace_folder() == "/test/workspace"
            assert env.get_git_root() == "/test/git"
            assert env.get_project_name() == "test-project"
            
            # Verify parameter dictionary
            params = env_manager.get_parameter_dict()
            assert params["workspace_folder"] == "/test/workspace"
            assert params["git_root"] == "/test/git"
            assert params["project_name"] == "test-project" 