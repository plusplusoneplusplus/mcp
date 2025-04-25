import os
import json
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from pydantic import BaseModel, Field

class RepositoryInfo(BaseModel):
    """Model representing repository information"""
    git_root: Optional[str] = None
    workspace_folder: Optional[str] = None
    project_name: Optional[str] = None
    additional_paths: Dict[str, str] = Field(default_factory=dict)
    private_tool_root: Optional[str] = None  # New field for private tool root

class Environment:
    """
    Environment class to handle repository and environment information
    that is passed from IDE to the server.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Environment, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize environment with default values"""
        self.repository_info = RepositoryInfo()
        self.env_variables: Dict[str, str] = {}
        self._providers: List[Callable[[], Dict[str, Any]]] = []
        self._load_from_env_variables()
    
    def _load_from_env_variables(self):
        """Load repository information from environment variables"""
        # Standard environment variables
        if git_root := os.environ.get("GIT_ROOT"):
            self.repository_info.git_root = git_root
        
        if workspace_folder := os.environ.get("WORKSPACE_FOLDER"):
            self.repository_info.workspace_folder = workspace_folder
        
        if project_name := os.environ.get("PROJECT_NAME"):
            self.repository_info.project_name = project_name
        
        # Load private tool root environment variable
        if private_tool_root := os.environ.get("PRIVATE_TOOL_ROOT"):
            self.repository_info.private_tool_root = private_tool_root
        
        # Load additional paths from MCP_PATHS_{NAME} environment variables
        for key, value in os.environ.items():
            if key.startswith("MCP_PATH_"):
                path_name = key[9:].lower()  # Remove MCP_PATH_ prefix
                self.repository_info.additional_paths[path_name] = value
        
        # Save all environment variables for access
        self.env_variables = dict(os.environ)
    
    def register_provider(self, provider: Callable[[], Dict[str, Any]]):
        """Register a provider function that returns additional environment data"""
        self._providers.append(provider)
        return self
    
    def load(self):
        """Load all environment information"""
        self._load_from_env_variables()
        
        # Call all registered providers
        for provider in self._providers:
            try:
                additional_data = provider()
                
                # Update repository info if provided
                repo_info = additional_data.get("repository", {})
                if git_root := repo_info.get("git_root"):
                    self.repository_info.git_root = git_root
                    
                if workspace_folder := repo_info.get("workspace_folder"):
                    self.repository_info.workspace_folder = workspace_folder
                    
                if project_name := repo_info.get("project_name"):
                    self.repository_info.project_name = project_name
                    
                # Update private tool root if provided
                if private_tool_root := repo_info.get("private_tool_root"):
                    self.repository_info.private_tool_root = private_tool_root
                    
                # Update additional paths
                for key, value in repo_info.get("additional_paths", {}).items():
                    self.repository_info.additional_paths[key] = value
                    
            except Exception as e:
                print(f"Error from provider: {e}")
        
        return self
    
    def get_parameter_dict(self) -> Dict[str, Any]:
        """Return environment as a dictionary for command substitution"""
        result = {
            "git_root": self.repository_info.git_root,
            "workspace_folder": self.repository_info.workspace_folder,
            "project_name": self.repository_info.project_name,
            "private_tool_root": self.repository_info.private_tool_root,  # Add private tool root
        }
        
        # Add all additional paths
        for key, value in self.repository_info.additional_paths.items():
            result[f"path_{key}"] = value
            
        return result


# Create singleton instance
env = Environment()


# Helper functions
def get_git_root() -> Optional[str]:
    """Get git root directory"""
    return env.repository_info.git_root


def get_workspace_folder() -> Optional[str]:
    """Get workspace folder"""
    return env.repository_info.workspace_folder


def get_project_name() -> Optional[str]:
    """Get project name"""
    return env.repository_info.project_name


def get_path(name: str) -> Optional[str]:
    """Get a specific path by name"""
    return env.repository_info.additional_paths.get(name)


def get_private_tool_root() -> Optional[str]:
    """Get private tool root directory"""
    return env.repository_info.private_tool_root