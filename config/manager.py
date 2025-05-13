from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Union
from config.types import RepositoryInfo


class EnvironmentManager:
    """
    Environment manager to handle repository and environment information
    that is passed from IDE to the server.
    """

    _instance = None

    # List of all settings that are paths
    PATH_SETTINGS = [
        "git_root",
        "workspace_folder",
        "private_tool_root",
        "tool_history_path",
        "browser_profile_path",
        "image_dir",
    ]

    # Default settings with their types
    DEFAULT_SETTINGS = {
        # Repository info settings
        "git_root": (None, str),
        "workspace_folder": (None, str),
        "project_name": (None, str),
        "private_tool_root": (None, str),
        # Tool history settings
        "tool_history_enabled": (True, bool),
        "tool_history_path": (".history", str),
        "browser_profile_path": (".browserprofile", str),
        "browser_type": ("chrome", str),
        "client_type": ("playwright", str),
        # Image serving
        "image_dir": (".images", str),
    }

    # Create mapping dynamically - each setting can be set via its uppercase env var
    ENV_MAPPING = {setting.upper(): setting for setting in DEFAULT_SETTINGS.keys()}

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
        self.azrepo_parameters: Dict[str, Any] = {}
        self.kusto_parameters: Dict[str, Any] = {}
        self.settings: Dict[str, Any] = {}

        # Initialize settings with default values
        for key, (default_value, _) in self.DEFAULT_SETTINGS.items():
            self.settings[key] = default_value

        self._load_from_env_file()
        self._sync_settings_to_repo()

        # Resolve all path settings to absolute paths relative to server/main.py
        server_main = Path(__file__).parent.parent / "server" / "main.py"
        server_root = (
            server_main.parent.resolve()
            if server_main.exists()
            else (Path(__file__).parent.parent / "server").resolve()
        )
        for key in getattr(self, "PATH_SETTINGS", []):
            value = self.settings.get(key)
            if value is not None:
                p = Path(value)
                if not p.is_absolute():
                    p = server_root / p
                self.settings[key] = str(p.resolve())

    def _sync_settings_to_repo(self):
        """Sync settings to repository info object"""
        repo_fields = [
            "git_root",
            "workspace_folder",
            "project_name",
            "private_tool_root",
        ]
        for field in repo_fields:
            if value := self.settings.get(field):
                setattr(self.repository_info, field, value)

    def _sync_repo_to_settings(self):
        """Sync repository info to settings dictionary"""
        repo_fields = [
            "git_root",
            "workspace_folder",
            "project_name",
            "private_tool_root",
        ]
        for field in repo_fields:
            value = getattr(self.repository_info, field)
            if value is not None:
                self.settings[field] = value

    def _get_git_root(self) -> Optional[Path]:
        """Try to determine the git root directory

        Returns:
            Path to the git root directory or None if not found
        """
        current_dir = Path.cwd()

        dir_to_check = current_dir
        for _ in range(10):  # Limit the search depth
            git_dir = dir_to_check / ".git"
            if git_dir.exists() and git_dir.is_dir():
                return dir_to_check

            parent_dir = dir_to_check.parent
            if parent_dir == dir_to_check:  # Reached the root
                break
            dir_to_check = parent_dir

        return None

    def _convert_value(self, value: str, target_type: type) -> Any:
        """Convert string value to target type"""
        if target_type == bool:
            return value.lower() == "true"
        return target_type(value)

    def _load_from_env_file(self):
        """Find and load variables from a .env file"""
        env_file_paths = []

        # Check workspace folder
        if self.repository_info.workspace_folder:
            env_file_paths.append(Path(self.repository_info.workspace_folder) / ".env")

        if self.repository_info.git_root:
            env_file_paths.append(Path(self.repository_info.git_root) / ".env")

        # Also check current directory
        env_file_paths.append(Path.cwd() / ".env")

        # Try additional common locations - safely handle home directory
        try:
            home_env = Path.home() / ".env"
            env_file_paths.append(home_env)
        except (RuntimeError, OSError):
            # Skip home directory if it can't be determined
            pass

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
            config_template_path = (
                git_root / "config" / "templates" / "env.template" if git_root else None
            )

            if config_template_path and config_template_path.exists():
                print(
                    f"No .env file found. Please create one using the template at: {config_template_path}"
                )
                print(f"Example: cp {config_template_path} .env")
            else:
                print("No .env file found. Create one to configure the environment.")

    def _parse_env_file(self, env_file_path: Path):
        """Parse a .env file and load variables into environment"""
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
                        if (value.startswith('"') and value.endswith('"')) or (
                            value.startswith("'") and value.endswith("'")
                        ):
                            value = value[1:-1]

                        # Update environment variables
                        self.env_variables[key] = value

                        # Update mapped settings
                        if key in self.ENV_MAPPING:
                            setting_name = self.ENV_MAPPING[key]

                            # Get the target type from default settings
                            for default_key, (
                                _,
                                target_type,
                            ) in self.DEFAULT_SETTINGS.items():
                                if setting_name == default_key:
                                    self.settings[setting_name] = self._convert_value(
                                        value, target_type
                                    )
                                    break

                        # Handle MCP_PATH_ prefixed variables
                        elif key.startswith("MCP_PATH_"):
                            path_name = key[9:].lower()
                            self.repository_info.additional_paths[path_name] = value
                        # Handle AZREPO_ prefixed variables
                        elif key.startswith("AZREPO_"):
                            param_name = key[7:].lower()
                            self.azrepo_parameters[param_name] = value
                        # Handle KUSTO_ prefixed variables
                        elif key.startswith("KUSTO_"):
                            param_name = key[6:].lower()
                            self.kusto_parameters[param_name] = value

            # Sync settings to repository info after loading all values
            self._sync_settings_to_repo()

        except Exception as e:
            print(f"Error parsing .env file {env_file_path}: {e}")

    def register_provider(self, provider: Callable[[], Dict[str, Any]]):
        """Register a provider function that returns additional environment data"""
        self._providers.append(provider)
        return self

    def load(self):
        """Load all environment information"""
        self._load_from_env_file()

        # Import os here to avoid circular imports
        import os

        # Load variables from OS environment
        for key, value in os.environ.items():
            self.env_variables[key] = value

            # Update mapped settings
            if key in self.ENV_MAPPING:
                setting_name = self.ENV_MAPPING[key]

                # Get the target type from default settings
                for default_key, (_, target_type) in self.DEFAULT_SETTINGS.items():
                    if setting_name == default_key:
                        self.settings[setting_name] = self._convert_value(
                            value, target_type
                        )
                        break

            # Handle MCP_PATH_ prefixed variables
            elif key.startswith("MCP_PATH_"):
                path_name = key[9:].lower()
                self.repository_info.additional_paths[path_name] = value
            # Handle AZREPO_ prefixed variables
            elif key.startswith("AZREPO_"):
                param_name = key[7:].lower()
                self.azrepo_parameters[param_name] = value
            # Handle KUSTO_ prefixed variables
            elif key.startswith("KUSTO_"):
                param_name = key[6:].lower()
                self.kusto_parameters[param_name] = value

        # Sync settings to repository info
        self._sync_settings_to_repo()

        # Call all registered providers
        for provider in self._providers:
            try:
                additional_data = provider()

                # Update repository info if provided
                repo_info = additional_data.get("repository", {})
                for field in [
                    "git_root",
                    "workspace_folder",
                    "project_name",
                    "private_tool_root",
                ]:
                    if value := repo_info.get(field):
                        self.settings[field] = value
                        setattr(self.repository_info, field, value)

                # Update additional paths
                for key, value in repo_info.get("additional_paths", {}).items():
                    self.repository_info.additional_paths[key] = value

                # Update azrepo parameters if provided
                if azrepo_params := additional_data.get("azrepo_parameters", {}):
                    for key, value in azrepo_params.items():
                        self.azrepo_parameters[key] = value

                # Update kusto parameters if provided
                if kusto_params := additional_data.get("kusto_parameters", {}):
                    for key, value in kusto_params.items():
                        self.kusto_parameters[key] = value

                # Update other settings
                if settings := additional_data.get("settings", {}):
                    for key, value in settings.items():
                        if key in self.settings:
                            self.settings[key] = value

            except Exception as e:
                print(f"Error from provider: {e}")

        # Final sync of settings to repository info
        self._sync_settings_to_repo()

        return self

    def get_parameter_dict(self) -> Dict[str, Any]:
        """Return environment as a dictionary for command substitution"""
        # Ensure repository info is reflected in settings
        self._sync_repo_to_settings()

        result = {}

        # Add all settings
        for key, value in self.settings.items():
            result[key] = value

        # Add all additional paths
        for key, value in self.repository_info.additional_paths.items():
            result[f"path_{key}"] = value

        # Add azrepo parameters
        for key, value in self.azrepo_parameters.items():
            result[f"azrepo_{key}"] = value

        # Add kusto parameters
        for key, value in self.kusto_parameters.items():
            result[key] = value

        return result

    def get_setting(self, name: str, default: Any = None) -> Any:
        """Get a setting value by name"""
        # If it's a repo setting, sync from repo first
        if name in [
            "git_root",
            "workspace_folder",
            "project_name",
            "private_tool_root",
        ]:
            self._sync_repo_to_settings()

        return self.settings.get(name, default)

    # Public getters for backwards compatibility
    def get_git_root(self) -> Optional[str]:
        """Get git root directory"""
        return self.get_setting("git_root")

    def get_workspace_folder(self) -> Optional[str]:
        """Get workspace folder"""
        return self.get_setting("workspace_folder")

    def get_project_name(self) -> Optional[str]:
        """Get project name"""
        return self.get_setting("project_name")

    def get_path(self, name: str) -> Optional[str]:
        """Get a specific path by name"""
        return self.repository_info.additional_paths.get(name)

    def get_private_tool_root(self) -> Optional[str]:
        """Get private tool root directory"""
        return self.get_setting("private_tool_root")

    def get_azrepo_parameters(self) -> Dict[str, Any]:
        """Get Azure repo parameters"""
        return self.azrepo_parameters

    def get_azrepo_parameter(self, name: str, default: Any = None) -> Any:
        """Get a specific Azure repo parameter"""
        return self.azrepo_parameters.get(name, default)

    def get_kusto_parameters(self) -> Dict[str, Any]:
        """Get Kusto parameters"""
        return self.kusto_parameters

    def get_kusto_parameter(self, name: str, default: Any = None) -> Any:
        """Get a specific Kusto parameter"""
        return self.kusto_parameters.get(name, default)

    def is_tool_history_enabled(self) -> bool:
        """Check if tool invoke history is enabled"""
        return self.get_setting("tool_history_enabled", True)

    def get_tool_history_path(self) -> str:
        """Get the path for storing tool invoke history"""
        return self.get_setting("tool_history_path", ".history")


# Create singleton instance
env_manager = EnvironmentManager()
