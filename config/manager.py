from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Union
from config.types import RepositoryInfo
import shutil
import logging
import json
import subprocess


class EnvironmentManager:
    """
    Environment manager to handle repository and environment information
    that is passed from IDE to the server.
    """

    _instance = None

    # List of all settings that are paths
    PATH_SETTINGS = [
        "git_root",
        "private_tool_root",
        "tool_history_path",
        "job_history_storage_path",
        "browser_profile_path",
        "image_dir",
        "vector_store_path",
        "dataframe_persistent_storage_path",
    ]

    # Default settings with their types
    DEFAULT_SETTINGS = {
        # Repository info settings
        "git_root": (None, str),
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
        # Vector store settings
        "vector_store_path": (".vector_store", str),
        # Command executor periodic status reporting
        "periodic_status_enabled": (False, bool),
        "periodic_status_interval": (30.0, float),
        "periodic_status_max_command_length": (60, int),
        # Background job history persistence
        "job_history_persistence_enabled": (False, bool),
        "job_history_storage_backend": ("json", str),
        "job_history_storage_path": (".job_history.json", str),
        "job_history_max_entries": (1000, int),
        "job_history_max_age_days": (30, int),
        # DataFrame management settings
        "dataframe_max_memory_mb": (1024, int),
        "dataframe_default_ttl_seconds": (3600, int),
        "dataframe_cleanup_interval_seconds": (300, int),
        "dataframe_max_dataframes": (1000, int),
        "dataframe_storage_backend": ("memory", str),
        "dataframe_persistent_storage_path": (".dataframes", str),
        # Kusto DataFrame storage settings
        "kusto_dataframe_storage_enabled": (True, bool),
        "kusto_dataframe_threshold_mb": (10, int),
        "kusto_dataframe_auto_summarize": (True, bool),
        "kusto_dataframe_summary_type": ("auto", str),
    }

    # Default Azure repo settings with their types
    DEFAULT_AZREPO_SETTINGS = {
        # Azure DevOps authentication settings
        "bearer_token_command": ('az account get-access-token --scope "499b84ac-1321-427f-aa17-267ca6975798/.default"', str),
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
        self.logger = logging.getLogger(__name__)

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

            # Dump each probed env path to help user troubleshooting.
            print("Below env file paths have been tried:")
            for env_path in env_file_paths:
                print(f"  {env_path}")

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
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or (
                            value.startswith("'") and value.endswith("'")
                        ):
                            value = value[1:-1]

                        # Store in env_variables
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
                        # Handle GIT_ROOT_ prefixed variables for multiple git roots
                        elif key.startswith("GIT_ROOT_"):
                            project_name = key[9:].lower()  # Extract project name after GIT_ROOT_
                            self.repository_info.git_roots[project_name] = value
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
            # Handle GIT_ROOT_ prefixed variables for multiple git roots
            elif key.startswith("GIT_ROOT_"):
                project_name = key[9:].lower()  # Extract project name after GIT_ROOT_
                self.repository_info.git_roots[project_name] = value
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

        # Add individual git roots for command substitution
        for project_name, git_root in self.repository_info.git_roots.items():
            result[f"git_root_{project_name}"] = git_root

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
            "project_name",
            "private_tool_root",
        ]:
            self._sync_repo_to_settings()

        return self.settings.get(name, default)

    # Public getters for backwards compatibility
    def get_git_root(self, project_name: Optional[str] = None) -> Optional[str]:
        """Get git root directory for specific project or default"""
        if project_name:
            return self.repository_info.git_roots.get(project_name)
        # Return the default git_root or the first available git root from git_roots
        return self.get_setting("git_root") or next(iter(self.repository_info.git_roots.values()), None)

    def get_all_git_roots(self) -> Dict[str, str]:
        """Get all configured git roots"""
        result = {}
        # Add default git root if it exists
        if default_git_root := self.get_setting("git_root"):
            result["default"] = default_git_root
        # Add all named git roots
        result.update(self.repository_info.git_roots)
        return result

    def get_git_root_projects(self) -> List[str]:
        """Get list of all available git root project names"""
        projects = list(self.repository_info.git_roots.keys())
        # Add "default" if there's a default git root
        if self.get_setting("git_root"):
            projects.insert(0, "default")
        return projects

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
        """Get Azure repo parameters with defaults applied"""
        # Start with default values
        result = {}
        for key, (default_value, _) in self.DEFAULT_AZREPO_SETTINGS.items():
            result[key] = default_value

        # Override with configured values
        result.update(self.azrepo_parameters)

        return result

    def get_azrepo_parameter(self, name: str, default: Any = None) -> Any:
        """Get a specific Azure repo parameter"""
        # Use get_azrepo_parameters to ensure dynamic token resolution
        params = self.get_azrepo_parameters()
        return params.get(name, default)

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

    def get_vector_store_path(self) -> str:
        """Get the vector store persistence path"""
        return self.get_setting("vector_store_path", ".vector_store")

    # Configuration Management Methods for Web Interface
    def get_all_configuration(self) -> Dict[str, Any]:
        """Get all configuration settings for the web interface"""
        # Ensure settings are synced
        self._sync_repo_to_settings()

        # Convert DEFAULT_SETTINGS to JSON-serializable format
        default_settings_serializable = {}
        for key, (default_value, type_class) in self.DEFAULT_SETTINGS.items():
            default_settings_serializable[key] = {
                "default_value": default_value,
                "type": type_class.__name__
            }

        # Convert DEFAULT_AZREPO_SETTINGS to JSON-serializable format
        default_azrepo_settings_serializable = {}
        for key, (default_value, type_class) in self.DEFAULT_AZREPO_SETTINGS.items():
            default_azrepo_settings_serializable[key] = {
                "default_value": default_value,
                "type": type_class.__name__
            }

        return {
            "settings": dict(self.settings),
            "azrepo_parameters": dict(self.azrepo_parameters),
            "kusto_parameters": dict(self.kusto_parameters),
            "additional_paths": dict(self.repository_info.additional_paths),
            "git_roots": dict(self.repository_info.git_roots),
            "default_settings": default_settings_serializable,
            "default_azrepo_settings": default_azrepo_settings_serializable,
            "path_settings": list(self.PATH_SETTINGS),
            "env_mapping": dict(self.ENV_MAPPING)
        }

    def update_configuration(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration settings and return result"""
        try:
            restart_required = False
            updated_settings = []

            # Update regular settings
            if "settings" in updates:
                for key, value in updates["settings"].items():
                    if key in self.DEFAULT_SETTINGS:
                        # Convert value to correct type
                        _, target_type = self.DEFAULT_SETTINGS[key]
                        if target_type == bool and isinstance(value, str):
                            value = value.lower() in ('true', '1', 'yes', 'on')
                        elif target_type in (int, float) and isinstance(value, str):
                            value = target_type(value) if value else None

                        old_value = self.settings.get(key)
                        self.settings[key] = value
                        updated_settings.append(key)

                        # Check if restart is required for certain settings
                        if key in ["vector_store_path", "browser_profile_path", "browser_type", "client_type"]:
                            restart_required = True

            # Update Azure DevOps parameters
            if "azrepo_parameters" in updates:
                for key, value in updates["azrepo_parameters"].items():
                    self.azrepo_parameters[key] = value
                    updated_settings.append(f"azrepo_{key}")

            # Update Kusto parameters
            if "kusto_parameters" in updates:
                for key, value in updates["kusto_parameters"].items():
                    self.kusto_parameters[key] = value
                    updated_settings.append(f"kusto_{key}")

            # Sync settings to repository info
            self._sync_settings_to_repo()

            return {
                "success": True,
                "updated_settings": updated_settings,
                "restart_required": restart_required,
                "message": f"Updated {len(updated_settings)} settings successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to update configuration: {str(e)}"
            }

    def reset_setting(self, setting_name: str) -> Dict[str, Any]:
        """Reset a specific setting to its default value"""
        try:
            if setting_name.startswith("azrepo_"):
                param_name = setting_name[7:]
                if param_name in self.azrepo_parameters:
                    del self.azrepo_parameters[param_name]
                    # Check if there's a default value to show
                    default_msg = ""
                    if param_name in self.DEFAULT_AZREPO_SETTINGS:
                        default_value, _ = self.DEFAULT_AZREPO_SETTINGS[param_name]
                        default_msg = f" (default: {default_value})"
                    return {"success": True, "message": f"Reset {setting_name} to default{default_msg}"}
                elif param_name in self.DEFAULT_AZREPO_SETTINGS:
                    # Setting exists in defaults but not in current config, already at default
                    default_value, _ = self.DEFAULT_AZREPO_SETTINGS[param_name]
                    return {"success": True, "message": f"Setting {setting_name} is already at default value: {default_value}"}
                else:
                    return {"success": False, "error": f"Setting {setting_name} not found"}

            elif setting_name.startswith("kusto_"):
                param_name = setting_name[6:]
                if param_name in self.kusto_parameters:
                    del self.kusto_parameters[param_name]
                    return {"success": True, "message": f"Reset {setting_name} to default"}
                else:
                    return {"success": False, "error": f"Setting {setting_name} not found"}

            elif setting_name in self.DEFAULT_SETTINGS:
                default_value, _ = self.DEFAULT_SETTINGS[setting_name]
                self.settings[setting_name] = default_value
                self._sync_settings_to_repo()
                return {"success": True, "message": f"Reset {setting_name} to default value: {default_value}"}

            else:
                return {"success": False, "error": f"Unknown setting: {setting_name}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_env_file_content(self) -> Dict[str, Any]:
        """Get the content of the .env file"""
        try:
            env_file_paths = []

            # Check common .env file locations
            if self.repository_info.git_root:
                env_file_paths.append(Path(self.repository_info.git_root) / ".env")

            env_file_paths.append(Path.cwd() / ".env")

            # Try to find git root if not already set
            if not self.repository_info.git_root:
                git_root = self._get_git_root()
                if git_root:
                    env_file_paths.append(git_root / ".env")

            # Find the first existing .env file
            for env_path in env_file_paths:
                if env_path.exists() and env_path.is_file():
                    with open(env_path, 'r') as f:
                        content = f.read()
                    return {
                        "success": True,
                        "content": content,
                        "file_path": str(env_path),
                        "message": f"Loaded .env file from {env_path}"
                    }

            return {
                "success": False,
                "error": "No .env file found",
                "content": "",
                "file_path": None,
                "message": "No .env file found in common locations"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "file_path": None,
                "message": f"Error reading .env file: {str(e)}"
            }

    def save_env_file_content(self, content: str) -> Dict[str, Any]:
        """Save content to the .env file"""
        try:
            # Determine where to save the .env file
            env_file_path = None

            if self.repository_info.git_root:
                env_file_path = Path(self.repository_info.git_root) / ".env"
            else:
                git_root = self._get_git_root()
                if git_root:
                    env_file_path = git_root / ".env"
                else:
                    env_file_path = Path.cwd() / ".env"

            # Create backup if file exists
            if env_file_path.exists():
                backup_path = env_file_path.with_suffix('.env.backup')
                shutil.copy2(env_file_path, backup_path)

            # Write the new content
            with open(env_file_path, 'w') as f:
                f.write(content)

            return {
                "success": True,
                "file_path": str(env_file_path),
                "message": f"Successfully saved .env file to {env_file_path}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": None,
                "message": f"Error saving .env file: {str(e)}"
            }

    def validate_env_content(self, content: str) -> Dict[str, Any]:
        """Validate .env file content"""
        try:
            errors = []
            warnings = []
            valid_lines = 0
            total_lines = 0

            for line_num, line in enumerate(content.split('\n'), 1):
                total_lines += 1
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Check if line contains '='
                if '=' not in line:
                    errors.append(f"Line {line_num}: Invalid format, missing '=' separator")
                    continue

                # Split on first '=' only
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Validate key format
                if not key:
                    errors.append(f"Line {line_num}: Empty variable name")
                    continue

                if not key.replace('_', '').replace('-', '').isalnum():
                    warnings.append(f"Line {line_num}: Variable name '{key}' contains special characters")

                # Check for common issues
                if value.startswith(' ') or value.endswith(' '):
                    warnings.append(f"Line {line_num}: Value for '{key}' has leading/trailing spaces")

                valid_lines += 1

            return {
                "success": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "valid_lines": valid_lines,
                "total_lines": total_lines,
                "message": f"Validation complete: {valid_lines}/{total_lines} valid lines, {len(errors)} errors, {len(warnings)} warnings"
            }

        except Exception as e:
            return {
                "success": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "valid_lines": 0,
                "total_lines": 0,
                "message": f"Error validating .env content: {str(e)}"
            }

    def backup_env_file(self) -> Dict[str, Any]:
        """Create a backup of the current .env file"""
        try:
            env_file_paths = []

            # Check common .env file locations
            if self.repository_info.git_root:
                env_file_paths.append(Path(self.repository_info.git_root) / ".env")

            env_file_paths.append(Path.cwd() / ".env")

            # Try to find git root if not already set
            if not self.repository_info.git_root:
                git_root = self._get_git_root()
                if git_root:
                    env_file_paths.append(git_root / ".env")

            # Find the first existing .env file
            for env_path in env_file_paths:
                if env_path.exists() and env_path.is_file():
                    # Create backup with timestamp
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = env_path.with_name(f".env.backup_{timestamp}")

                    shutil.copy2(env_path, backup_path)

                    return {
                        "success": True,
                        "original_path": str(env_path),
                        "backup_path": str(backup_path),
                        "message": f"Successfully created backup at {backup_path}"
                    }

            return {
                "success": False,
                "error": "No .env file found to backup",
                "original_path": None,
                "backup_path": None,
                "message": "No .env file found in common locations"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "original_path": None,
                "backup_path": None,
                "message": f"Error creating backup: {str(e)}"
            }


# Create a global instance
env_manager = EnvironmentManager()
