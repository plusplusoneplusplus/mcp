"""
Unit tests for the hierarchical configuration system using existing EnvironmentManager.

Tests cover configuration schema validation, hierarchical resolution logic,
YAML parsing, environment variable handling, and integration with EnvironmentManager.
"""

import os
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

from ..schemas import (
    TruncationConfig,
    TruncationStrategy,
    DEFAULT_SYSTEM_CONFIG,
    parse_env_config
)
from .. import (
    get_config_manager,
    reset_config_manager,
    resolve_truncation_config
)


class TestTruncationConfig:
    """Test cases for TruncationConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TruncationConfig()

        assert config.strategy == TruncationStrategy.HEAD_TAIL
        assert config.max_chars == 50000
        assert config.max_lines == 1000
        assert config.head_lines == 100
        assert config.tail_lines == 100
        assert config.preserve_errors is True
        assert config.preserve_warnings is True
        assert config.content_detection is True

    def test_validation_positive_max_chars(self):
        """Test validation of positive max_chars."""
        with pytest.raises(ValueError, match="max_chars must be positive"):
            TruncationConfig(max_chars=0)

    def test_from_dict_valid(self):
        """Test creating config from valid dictionary."""
        data = {
            'strategy': 'smart_summary',
            'max_chars': 30000,
            'max_lines': 800,
        }

        config = TruncationConfig.from_dict(data)

        assert config.strategy == TruncationStrategy.SMART_SUMMARY
        assert config.max_chars == 30000
        assert config.max_lines == 800

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = TruncationConfig(
            strategy=TruncationStrategy.NONE,
            max_chars=15000,
            preserve_errors=False
        )

        result = config.to_dict()

        expected = {
            'strategy': 'none',
            'max_chars': 15000,
            'max_lines': 1000,
            'head_lines': 100,
            'tail_lines': 100,
            'preserve_errors': False,
            'preserve_warnings': True,
            'content_detection': True
        }

        assert result == expected

    def test_merge_with_partial_override(self):
        """Test merging with partial configuration override."""
        base_config = TruncationConfig(
            strategy=TruncationStrategy.HEAD_TAIL,
            max_chars=25000,
            preserve_errors=True,
            preserve_warnings=False
        )

        # Override only some fields
        override_config = TruncationConfig(
            strategy=TruncationStrategy.SMART_SUMMARY,
            max_chars=35000
            # preserve_errors and preserve_warnings use defaults
        )

        result = base_config.merge_with(override_config)

        # Override values should be used
        assert result.strategy == TruncationStrategy.SMART_SUMMARY
        assert result.max_chars == 35000
        # Other values come from override's defaults, not base
        assert result.preserve_errors is True  # override default
        assert result.preserve_warnings is True  # override default


class TestParseEnvConfig:
    """Test cases for environment variable parsing."""

    def test_no_env_vars(self):
        """Test when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            result = parse_env_config()
            assert result is None

    def test_strategy_env_var(self):
        """Test parsing strategy from environment variable."""
        with patch.dict(os.environ, {'MCP_TRUNCATION_STRATEGY': 'smart_summary'}):
            result = parse_env_config()
            assert result is not None
            assert result.strategy == TruncationStrategy.SMART_SUMMARY

    def test_all_env_vars(self):
        """Test parsing all environment variables."""
        env_vars = {
            'MCP_TRUNCATION_STRATEGY': 'size_limit',
            'MCP_TRUNCATION_MAX_CHARS': '30000',
            'MCP_TRUNCATION_MAX_LINES': '800',
            'MCP_TRUNCATION_HEAD_LINES': '80',
            'MCP_TRUNCATION_TAIL_LINES': '80',
            'MCP_TRUNCATION_PRESERVE_ERRORS': 'false',
            'MCP_TRUNCATION_PRESERVE_WARNINGS': 'true',
            'MCP_TRUNCATION_CONTENT_DETECTION': '1'
        }

        with patch.dict(os.environ, env_vars):
            result = parse_env_config()
            assert result is not None
            assert result.strategy == TruncationStrategy.SIZE_LIMIT
            assert result.max_chars == 30000
            assert result.max_lines == 800
            assert result.head_lines == 80
            assert result.tail_lines == 80
            assert result.preserve_errors is False
            assert result.preserve_warnings is True
            assert result.content_detection is True


class TestEnvironmentManagerIntegration:
    """Test cases for integration with existing EnvironmentManager."""

    def test_get_config_manager(self):
        """Test that get_config_manager returns the environment manager."""
        manager = get_config_manager()
        assert manager is not None
        # Should be the existing EnvironmentManager instance
        from config import env_manager
        assert manager is env_manager

    def test_resolve_truncation_config_default(self):
        """Test resolving truncation config with defaults."""
        config = resolve_truncation_config()

        # Should return system defaults when no specific config is set
        assert config.strategy == DEFAULT_SYSTEM_CONFIG.strategy
        assert config.max_chars == DEFAULT_SYSTEM_CONFIG.max_chars
        assert config.max_lines == DEFAULT_SYSTEM_CONFIG.max_lines

    def test_resolve_truncation_config_with_tool(self):
        """Test resolving truncation config with tool-specific settings."""
        manager = get_config_manager()

        # Add a tool configuration
        tool_data = {
            'name': 'test_tool',
            'truncation': {
                'strategy': 'size_limit',
                'max_chars': 25000
            }
        }

        manager.add_truncation_tool_config('test_tool', tool_data)

        # Resolve for the specific tool
        config = resolve_truncation_config(tool_name='test_tool')

        assert config.strategy == TruncationStrategy.SIZE_LIMIT
        assert config.max_chars == 25000

    def test_resolve_truncation_config_with_task(self):
        """Test resolving truncation config with task-specific settings."""
        manager = get_config_manager()

        # Add a task configuration
        task_config = TruncationConfig(
            strategy=TruncationStrategy.NONE,
            max_chars=10000
        )

        manager.add_truncation_task_config('test_task', task_config)

        # Resolve for the specific task
        config = resolve_truncation_config(task_id='test_task')

        assert config.strategy == TruncationStrategy.NONE
        assert config.max_chars == 10000

    @patch.dict(os.environ, {
        'MCP_TRUNCATION_STRATEGY': 'smart_summary',
        'MCP_TRUNCATION_MAX_CHARS': '40000'
    })
    def test_hierarchy_integration(self):
        """Test complete hierarchy with environment, tool, and task configs."""
        manager = get_config_manager()

        # Add tool config
        tool_data = {
            'truncation': {
                'strategy': 'head_tail',
                'max_chars': 30000,
                'preserve_warnings': False
            }
        }
        manager.add_truncation_tool_config('hierarchy_tool', tool_data)

        # Add task config
        task_config = TruncationConfig(
            strategy=TruncationStrategy.SIZE_LIMIT,
            max_chars=20000,
            head_lines=50
        )
        manager.add_truncation_task_config('hierarchy_task', task_config)

        # Test resolution at different levels

        # Environment level only
        config = resolve_truncation_config()
        assert config.strategy == TruncationStrategy.SMART_SUMMARY  # from env
        assert config.max_chars == 40000  # from env

        # Environment + Tool level
        config = resolve_truncation_config(tool_name='hierarchy_tool')
        assert config.strategy == TruncationStrategy.HEAD_TAIL  # from tool
        assert config.max_chars == 30000  # from tool
        assert config.preserve_warnings is False  # from tool

        # Environment + Tool + Task level (highest priority)
        config = resolve_truncation_config(tool_name='hierarchy_tool', task_id='hierarchy_task')
        assert config.strategy == TruncationStrategy.SIZE_LIMIT  # from task
        assert config.max_chars == 20000  # from task
        assert config.head_lines == 50  # from task

    def test_yaml_loading_integration(self):
        """Test loading YAML configurations through EnvironmentManager."""
        manager = get_config_manager()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a YAML file with truncation configuration
            yaml_content = """
name: yaml_test_tool
description: Test tool with truncation config
truncation:
  strategy: smart_summary
  max_chars: 75000
  max_lines: 1500
  preserve_errors: true
  preserve_warnings: false
"""

            yaml_file = Path(temp_dir) / "test_tool.yaml"
            with open(yaml_file, 'w') as f:
                f.write(yaml_content)

            # Load the configuration
            manager.load_truncation_tool_config_from_file(yaml_file)

            # Test the loaded configuration
            config = resolve_truncation_config(tool_name='yaml_test_tool')
            assert config.strategy == TruncationStrategy.SMART_SUMMARY
            assert config.max_chars == 75000
            assert config.max_lines == 1500
            assert config.preserve_errors is True
            assert config.preserve_warnings is False

    def test_config_summary(self):
        """Test getting configuration summary from EnvironmentManager."""
        manager = get_config_manager()

        # Add some configurations
        tool_data = {
            'truncation': {
                'strategy': 'head_tail',
                'max_chars': 25000
            }
        }
        manager.add_truncation_tool_config('summary_tool', tool_data)

        task_config = TruncationConfig(strategy=TruncationStrategy.NONE)
        manager.add_truncation_task_config('summary_task', task_config)

        # Get summary
        summary = manager.get_truncation_config_summary()

        assert summary['available'] is True
        assert 'system_config' in summary
        assert 'tool_configs' in summary
        assert 'task_configs' in summary

        # Check that our configurations are included
        assert 'summary_tool' in summary['tool_configs']
        assert 'summary_task' in summary['task_configs']

        # Verify the tool config
        tool_config = summary['tool_configs']['summary_tool']
        assert tool_config['strategy'] == 'head_tail'
        assert tool_config['max_chars'] == 25000

        # Verify the task config
        task_config_dict = summary['task_configs']['summary_task']
        assert task_config_dict['strategy'] == 'none'
