"""
Hierarchical configuration manager for output truncation system.

This module implements the configuration resolution logic that manages truncation
settings across different priority levels: task > tool > user > system.
"""

import yaml
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import logging

from .schemas import (
    TruncationConfig,
    ConfigLevel,
    ConfigSource,
    DEFAULT_SYSTEM_CONFIG,
    parse_env_config,
    TruncationStrategy
)

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Manages hierarchical configuration resolution for output truncation.
    
    The configuration hierarchy (highest to lowest priority):
    1. Task-level configuration (runtime overrides)
    2. Tool-level configuration (from YAML tool definitions)
    3. User-level configuration (environment variables)
    4. System-level configuration (defaults)
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._config_levels: List[ConfigLevel] = []
        self._initialize_default_levels()
    
    def _initialize_default_levels(self):
        """Initialize the default configuration levels."""
        # System level (lowest priority)
        self._config_levels.append(ConfigLevel(
            name="system",
            priority=0,
            config=DEFAULT_SYSTEM_CONFIG,
            source=ConfigSource.SYSTEM_DEFAULT
        ))
        
        # User level (environment variables)
        user_config = parse_env_config()
        if user_config:
            self._config_levels.append(ConfigLevel(
                name="user",
                priority=1,
                config=user_config,
                source=ConfigSource.USER_ENV
            ))
    
    def add_tool_config(self, tool_name: str, config_data: Dict[str, Any], 
                       source_path: Optional[str] = None):
        """
        Add tool-level configuration from YAML tool definition.
        
        Args:
            tool_name: Name of the tool
            config_data: Configuration data from YAML
            source_path: Path to the YAML file (optional)
        """
        try:
            truncation_data = config_data.get('truncation', {})
            if not truncation_data:
                logger.debug(f"No truncation config found for tool: {tool_name}")
                return
            
            tool_config = TruncationConfig.from_dict(truncation_data)
            
            # Remove existing tool config for this tool if it exists
            self._config_levels = [
                level for level in self._config_levels 
                if not (level.name == f"tool_{tool_name}" and level.source == ConfigSource.TOOL_YAML)
            ]
            
            # Add new tool config
            self._config_levels.append(ConfigLevel(
                name=f"tool_{tool_name}",
                priority=2,
                config=tool_config,
                source=source_path or ConfigSource.TOOL_YAML
            ))
            
            # Re-sort by priority
            self._config_levels.sort(key=lambda x: x.priority)
            
            logger.info(f"Added tool configuration for {tool_name} from {source_path or 'unknown source'}")
            
        except Exception as e:
            logger.error(f"Failed to parse tool configuration for {tool_name}: {e}")
            raise
    
    def add_task_config(self, task_id: str, config: TruncationConfig):
        """
        Add task-level configuration (highest priority).
        
        Args:
            task_id: Unique identifier for the task
            config: Task-specific truncation configuration
        """
        # Remove existing task config for this task if it exists
        self._config_levels = [
            level for level in self._config_levels 
            if not (level.name == f"task_{task_id}" and level.source == ConfigSource.TASK)
        ]
        
        # Add new task config
        self._config_levels.append(ConfigLevel(
            name=f"task_{task_id}",
            priority=3,
            config=config,
            source=ConfigSource.TASK
        ))
        
        # Re-sort by priority
        self._config_levels.sort(key=lambda x: x.priority)
        
        logger.info(f"Added task configuration for {task_id}")
    
    def remove_task_config(self, task_id: str):
        """
        Remove task-level configuration.
        
        Args:
            task_id: Unique identifier for the task
        """
        initial_count = len(self._config_levels)
        self._config_levels = [
            level for level in self._config_levels 
            if not (level.name == f"task_{task_id}" and level.source == ConfigSource.TASK)
        ]
        
        if len(self._config_levels) < initial_count:
            logger.info(f"Removed task configuration for {task_id}")
    
    def resolve_config(self, tool_name: Optional[str] = None, 
                      task_id: Optional[str] = None) -> TruncationConfig:
        """
        Resolve the effective configuration based on the hierarchy.
        
        Args:
            tool_name: Name of the tool (for tool-specific config)
            task_id: Task identifier (for task-specific config)
            
        Returns:
            Resolved TruncationConfig with highest priority settings
        """
        # Start with system defaults
        effective_config = DEFAULT_SYSTEM_CONFIG
        
        # Apply configurations in priority order (lowest to highest)
        for level in sorted(self._config_levels, key=lambda x: x.priority):
            if level.config is None:
                continue
            
            # Check if this level applies to the current context
            if self._level_applies(level, tool_name, task_id):
                effective_config = effective_config.merge_with(level.config)
                logger.debug(f"Applied config from level: {level.name} (priority: {level.priority})")
        
        return effective_config
    
    def _level_applies(self, level: ConfigLevel, tool_name: Optional[str], 
                      task_id: Optional[str]) -> bool:
        """
        Check if a configuration level applies to the current context.
        
        Args:
            level: Configuration level to check
            tool_name: Current tool name
            task_id: Current task ID
            
        Returns:
            True if the level applies, False otherwise
        """
        # System and user levels always apply
        if level.name in ["system", "user"]:
            return True
        
        # Tool-specific levels
        if level.name.startswith("tool_") and tool_name:
            expected_tool_name = level.name[5:]  # Remove "tool_" prefix
            return expected_tool_name == tool_name
        
        # Task-specific levels
        if level.name.startswith("task_") and task_id:
            expected_task_id = level.name[5:]  # Remove "task_" prefix
            return expected_task_id == task_id
        
        return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all configuration levels.
        
        Returns:
            Dictionary containing configuration summary
        """
        levels_list: List[Dict[str, Any]] = []
        
        for level in sorted(self._config_levels, key=lambda x: x.priority, reverse=True):
            level_info: Dict[str, Any] = {
                "name": level.name,
                "priority": level.priority,
                "source": level.source,
                "has_config": level.config is not None
            }
            
            if level.config:
                level_info["config"] = level.config.to_dict()
            
            levels_list.append(level_info)
        
        summary: Dict[str, Any] = {
            "levels": levels_list,
            "total_levels": len(self._config_levels)
        }
        
        return summary
    
    def load_tool_configs_from_directory(self, directory_path: Union[str, Path]):
        """
        Load tool configurations from YAML files in a directory.
        
        Args:
            directory_path: Path to directory containing YAML tool definitions
        """
        directory = Path(directory_path)
        
        if not directory.exists():
            logger.warning(f"Tool configuration directory does not exist: {directory}")
            return
        
        if not directory.is_dir():
            logger.error(f"Tool configuration path is not a directory: {directory}")
            return
        
        yaml_files = list(directory.glob("*.yaml")) + list(directory.glob("*.yml"))
        
        for yaml_file in yaml_files:
            try:
                self.load_tool_config_from_file(yaml_file)
            except Exception as e:
                logger.error(f"Failed to load tool config from {yaml_file}: {e}")
    
    def load_tool_config_from_file(self, file_path: Union[str, Path]):
        """
        Load tool configuration from a YAML file.
        
        Args:
            file_path: Path to YAML file containing tool definition
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"Tool configuration file does not exist: {file_path}")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                logger.error(f"Invalid YAML structure in {file_path}: expected dictionary")
                return
            
            # Extract tool name from filename or from YAML data
            tool_name = data.get('name', file_path.stem)
            
            self.add_tool_config(tool_name, data, str(file_path))
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading tool config from {file_path}: {e}")
            raise
    
    def validate_configuration(self) -> List[str]:
        """
        Validate all configurations and return any errors.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        for level in self._config_levels:
            if level.config is None:
                continue
            
            try:
                # Validation is performed in TruncationConfig.__post_init__
                # So we just need to ensure the config is valid
                level.config._validate()
            except Exception as e:
                errors.append(f"Invalid configuration in level '{level.name}': {e}")
        
        return errors


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """
    Get the global configuration manager instance.
    
    Returns:
        Global ConfigurationManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def reset_config_manager():
    """Reset the global configuration manager (mainly for testing)."""
    global _config_manager
    _config_manager = None


def resolve_truncation_config(tool_name: Optional[str] = None, 
                            task_id: Optional[str] = None) -> TruncationConfig:
    """
    Convenience function to resolve truncation configuration.
    
    Args:
        tool_name: Name of the tool (for tool-specific config)
        task_id: Task identifier (for task-specific config)
        
    Returns:
        Resolved TruncationConfig
    """
    return get_config_manager().resolve_config(tool_name, task_id) 