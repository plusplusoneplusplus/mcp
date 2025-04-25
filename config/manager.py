import os
import json
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from config.types import RepositoryInfo

# Import interface
from mcp_tools.interfaces import EnvironmentManagerInterface

# NOTE: Removed the register_tool decorator to avoid circular imports

class EnvironmentManager(EnvironmentManagerInterface):
    """
    Environment manager to handle repository and environment information
    that is passed from IDE to the server.
    """
    _instance = None
    
    # Implement ToolInterface properties
    @property
    def name(self) -> str:
        """Get the tool name."""
        return "environment_manager"
        
    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Manage environment information and repository details"
        
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform (get_parameter_dict, get_git_root, etc.)",
                    "enum": ["get_parameter_dict", "get_git_root", "get_workspace_folder", "get_project_name", "get_path", "get_private_tool_root", "get_azrepo_parameters"]
                },
                "path_name": {
                    "type": "string",
                    "description": "Path name to retrieve (for get_path operation)",
                    "nullable": True
                }
            },
            "required": ["operation"]
        }
    
    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments.
        
        Args:
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Tool execution result
        """
        operation = arguments.get("operation", "")
        
        if operation == "get_parameter_dict":
            return {
                "success": True,
                "parameters": self.get_parameter_dict()
            }
        elif operation == "get_git_root":
            return {
                "success": True,
                "git_root": self.get_git_root()
            }
        elif operation == "get_workspace_folder":
            return {
                "success": True,
                "workspace_folder": self.get_workspace_folder()
            }
        elif operation == "get_project_name":
            return {
                "success": True,
                "project_name": self.get_project_name()
            }
        elif operation == "get_path":
            path_name = arguments.get("path_name", "")
            return {
                "success": True,
                "path": self.get_path(path_name)
            }
        elif operation == "get_private_tool_root":
            return {
                "success": True,
                "private_tool_root": self.get_private_tool_root()
            }
        elif operation == "get_azrepo_parameters":
            return {
                "success": True,
                "azrepo_parameters": self.get_azrepo_parameters()
            }
        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}"
            }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize environment with default values"""
        self.repository_info = RepositoryInfo()
        self.env_variables: Dict[str, str] = {}
        self._providers: List[Callable[[], Dict[str, Any]]] = []
        # Dictionary to store azrepo parameters
        self.azrepo_parameters: Dict[str, Any] = {}
        self._load_from_env_file()
    
    def _get_git_root(self) -> Optional[Path]:
        """Try to determine the git root directory
        
        Returns:
            Path to the git root directory or None if not found
        """
        # Start from the current directory
        current_dir = Path.cwd()
        
        # Traverse up to find .git directory
        dir_to_check = current_dir
        for _ in range(10):  # Limit the search depth
            git_dir = dir_to_check / ".git"
            if git_dir.exists() and git_dir.is_dir():
                return dir_to_check
            
            # Move up one directory
            parent_dir = dir_to_check.parent
            if parent_dir == dir_to_check:  # Reached the root
                break
            dir_to_check = parent_dir
        
        return None
    
    def _load_from_env_file(self):
        """Load environment configuration from .env file"""
        # Try to find .env file in workspace folder or git root
        env_file_paths = []
        
        if self.repository_info.workspace_folder:
            env_file_paths.append(Path(self.repository_info.workspace_folder) / ".env")
        
        if self.repository_info.git_root:
            env_file_paths.append(Path(self.repository_info.git_root) / ".env")
        
        # Also check current directory
        env_file_paths.append(Path.cwd() / ".env")
        
        # Try additional common locations
        env_file_paths.append(Path.home() / ".env")
        
        # Try to find git root if not already set
        if not self.repository_info.git_root:
            git_root = self._get_git_root()
            if git_root:
                env_file_paths.append(git_root / ".env")
                
                # Check if config directory exists in git root
                config_env_template = git_root / "config" / "templates" / "env.template"
                if config_env_template.exists() and config_env_template.is_file():
                    env_file_paths.append(config_env_template)
        
        # Check if module directory exists
        module_path = Path(__file__).parent
        module_template = module_path / "templates" / "env.template"
        if module_template.exists() and module_template.is_file():
            env_file_paths.append(module_template)
        
        # Load from the first .env file found
        env_file_found = False
        for env_path in env_file_paths:
            if env_path.exists() and env_path.is_file():
                print(f"Loading environment from: {env_path}")
                self._parse_env_file(env_path)
                env_file_found = True
                break
        
        if not env_file_found:
            git_root = self._get_git_root()
            config_template_path = git_root / "config" / "templates" / "env.template" if git_root else None
            
            if config_template_path and config_template_path.exists():
                print(f"No .env file found. Please create one using the template at: {config_template_path}")
                print(f"Example: cp {config_template_path} .env")
            else:
                print("No .env file found. Create one to configure the environment.")
    
    def _parse_env_file(self, env_file_path: Path):
        """Parse a .env file and load variables into environment
        
        Args:
            env_file_path: Path to the .env file
        """
        try:
            with open(env_file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    
                    # Parse KEY=VALUE format
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        
                        # Update environment variables
                        self.env_variables[key] = value
                        
                        # Update repository info if applicable
                        if key == "GIT_ROOT":
                            self.repository_info.git_root = value
                        elif key == "WORKSPACE_FOLDER":
                            self.repository_info.workspace_folder = value
                        elif key == "PROJECT_NAME":
                            self.repository_info.project_name = value
                        elif key == "PRIVATE_TOOL_ROOT":
                            self.repository_info.private_tool_root = value
                        # Handle MCP_PATH_ prefixed variables
                        elif key.startswith("MCP_PATH_"):
                            path_name = key[9:].lower()
                            self.repository_info.additional_paths[path_name] = value
                        # Handle AZREPO_ prefixed variables
                        elif key.startswith("AZREPO_"):
                            param_name = key[7:].lower()
                            self.azrepo_parameters[param_name] = value
        except Exception as e:
            print(f"Error parsing .env file {env_file_path}: {e}")
    
    def register_provider(self, provider: Callable[[], Dict[str, Any]]):
        """Register a provider function that returns additional environment data"""
        self._providers.append(provider)
        return self
    
    def load(self):
        """Load all environment information"""
        self._load_from_env_file()
        
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
                
                # Update azrepo parameters if provided
                if azrepo_params := additional_data.get("azrepo_parameters", {}):
                    for key, value in azrepo_params.items():
                        self.azrepo_parameters[key] = value
                    
            except Exception as e:
                print(f"Error from provider: {e}")
        
        return self
    
    def get_parameter_dict(self) -> Dict[str, Any]:
        """Return environment as a dictionary for command substitution"""
        result = {
            "git_root": self.repository_info.git_root,
            "workspace_folder": self.repository_info.workspace_folder,
            "project_name": self.repository_info.project_name,
            "private_tool_root": self.repository_info.private_tool_root,
        }
        
        # Add all additional paths
        for key, value in self.repository_info.additional_paths.items():
            result[f"path_{key}"] = value
        
        # Add azrepo parameters
        for key, value in self.azrepo_parameters.items():
            result[f"azrepo_{key}"] = value
            
        return result
    
    def get_git_root(self) -> Optional[str]:
        """Get git root directory"""
        return self.repository_info.git_root

    def get_workspace_folder(self) -> Optional[str]:
        """Get workspace folder"""
        return self.repository_info.workspace_folder

    def get_project_name(self) -> Optional[str]:
        """Get project name"""
        return self.repository_info.project_name

    def get_path(self, name: str) -> Optional[str]:
        """Get a specific path by name"""
        return self.repository_info.additional_paths.get(name)

    def get_private_tool_root(self) -> Optional[str]:
        """Get private tool root directory"""
        return self.repository_info.private_tool_root
    
    def get_azrepo_parameters(self) -> Dict[str, Any]:
        """Get Azure repo parameters
        
        Returns:
            Dictionary of Azure repo parameters loaded from environment
        """
        return self.azrepo_parameters
    
    def get_azrepo_parameter(self, name: str, default: Any = None) -> Any:
        """Get a specific Azure repo parameter
        
        Args:
            name: Parameter name
            default: Default value if parameter not found
            
        Returns:
            Parameter value or default if not found
        """
        return self.azrepo_parameters.get(name, default)


# Create singleton instance
env_manager = EnvironmentManager() 