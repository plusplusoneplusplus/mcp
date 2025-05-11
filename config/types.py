from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class RepositoryInfo(BaseModel):
    """Model representing repository information"""

    git_root: Optional[str] = None
    workspace_folder: Optional[str] = None
    project_name: Optional[str] = None
    additional_paths: Dict[str, str] = Field(default_factory=dict)
    private_tool_root: Optional[str] = None  # Path for private tool root


class EnvironmentProvider(BaseModel):
    """Model representing an environment data provider"""

    name: str
    description: Optional[str] = None
    enabled: bool = True


class EnvironmentVariables(BaseModel):
    """Model representing environment variables"""

    variables: Dict[str, str] = Field(default_factory=dict)

    def get(self, name: str, default: Any = None) -> Any:
        """Get an environment variable value"""
        return self.variables.get(name, default)

    def set(self, name: str, value: str) -> None:
        """Set an environment variable value"""
        self.variables[name] = value
