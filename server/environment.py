import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

class RepositoryInfo:
    """Information about the repository."""
    def __init__(self):
        self.git_root: Optional[str] = None
        self.workspace_folder: Optional[str] = None
        self.project_name: Optional[str] = None
        self.private_tool_root: Optional[str] = None
        self.additional_paths: Dict[str, str] = {}

class Environment:
    """Singleton class to hold environment variables and repository information."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Environment, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.repository_info = RepositoryInfo()
            self.env_variables: Dict[str, str] = {}
            self._providers: List[Callable] = []
            self._initialized = True
            self.load()  # Load environment variables immediately

    def register_provider(self, provider: Callable):
        """Register a provider function that returns environment data."""
        self._providers.append(provider)

    def load(self):
        """Load environment variables and repository information."""
        # Load from providers
        for provider in self._providers:
            try:
                data = provider()
                if isinstance(data, dict) and "repository" in data:
                    self._update_repository_info(data["repository"])
            except Exception as e:
                print(f"Error loading provider: {e}", file=sys.stderr)

        # Load from environment variables
        self.env_variables = dict(os.environ)
        self._update_repository_info_from_env()

    def _update_repository_info_from_env(self):
        """Update repository info from environment variables."""
        # Core repository information
        if "GIT_ROOT" in self.env_variables:
            self.repository_info.git_root = self.env_variables["GIT_ROOT"]
        if "WORKSPACE_FOLDER" in self.env_variables:
            self.repository_info.workspace_folder = self.env_variables["WORKSPACE_FOLDER"]
        if "PROJECT_NAME" in self.env_variables:
            self.repository_info.project_name = self.env_variables["PROJECT_NAME"]
        if "PRIVATE_TOOL_ROOT" in self.env_variables:
            self.repository_info.private_tool_root = self.env_variables["PRIVATE_TOOL_ROOT"]

        # Additional paths (format: MCP_PATH_XXX)
        path_prefix = "MCP_PATH_"
        for key, value in self.env_variables.items():
            if key.startswith(path_prefix):
                path_name = key[len(path_prefix):].lower()
                self.repository_info.additional_paths[path_name] = value

    def _update_repository_info(self, repo_data: Dict[str, Any]):
        """Update repository info from provider data."""
        if "git_root" in repo_data:
            self.repository_info.git_root = repo_data["git_root"]
        if "workspace_folder" in repo_data:
            self.repository_info.workspace_folder = repo_data["workspace_folder"]
        if "project_name" in repo_data:
            self.repository_info.project_name = repo_data["project_name"]
        if "private_tool_root" in repo_data:
            self.repository_info.private_tool_root = repo_data["private_tool_root"]
        if "additional_paths" in repo_data and isinstance(repo_data["additional_paths"], dict):
            self.repository_info.additional_paths.update(repo_data["additional_paths"])

    def get_parameter_dict(self) -> Dict[str, str]:
        """Get a dictionary of parameters for use in templates."""
        params = {
            "git_root": self.repository_info.git_root or "",
            "workspace_folder": self.repository_info.workspace_folder or "",
            "project_name": self.repository_info.project_name or "",
            "private_tool_root": self.repository_info.private_tool_root or "",
        }
        
        # Add additional paths with path_ prefix
        for key, value in self.repository_info.additional_paths.items():
            params[f"path_{key}"] = value
            
        return params


# Create a global environment instance
env = Environment()

# Helper functions to access the environment
def get_git_root() -> Optional[str]:
    """Get the git root directory."""
    return env.repository_info.git_root

def get_workspace_folder() -> Optional[str]:
    """Get the workspace folder."""
    return env.repository_info.workspace_folder

def get_project_name() -> Optional[str]:
    """Get the project name."""
    return env.repository_info.project_name

def get_path(name: str) -> Optional[str]:
    """Get a path from additional paths."""
    return env.repository_info.additional_paths.get(name)

def get_private_tool_root() -> Optional[str]:
    """Get the private tool root directory."""
    return env.repository_info.private_tool_root 