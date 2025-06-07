"""
Unit tests for the hierarchical configuration system.

Tests cover configuration schema validation, hierarchical resolution logic,
YAML parsing, environment variable handling, and error conditions.
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
    ConfigLevel,
    ConfigSource,
    DEFAULT_SYSTEM_CONFIG,
    parse_env_config
)
from ..config import (
    ConfigurationManager,
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
    
    def test_validation_edge_case_max_lines_equals_head_tail_sum(self):
        """Test validation when max_lines equals head_lines + tail_lines."""
        # This should be valid (equal is allowed)
        config = TruncationConfig(max_lines=200, head_lines=100, tail_lines=100)
        assert config.max_lines == 200
        assert config.head_lines == 100
        assert config.tail_lines == 100
    
    def test_validation_zero_head_tail_lines(self):
        """Test validation with zero head/tail lines."""
        config = TruncationConfig(head_lines=0, tail_lines=0)
        assert config.head_lines == 0
        assert config.tail_lines == 0
    
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
    
    def test_from_dict_with_enum_strategy(self):
        """Test creating config from dict with TruncationStrategy enum."""
        data = {
            'strategy': TruncationStrategy.SIZE_LIMIT,
            'max_chars': 25000,
        }
        
        config = TruncationConfig.from_dict(data)
        assert config.strategy == TruncationStrategy.SIZE_LIMIT
        assert config.max_chars == 25000
    
    def test_from_dict_invalid_strategy_type(self):
        """Test error handling for invalid strategy type."""
        data = {'strategy': 123}  # Invalid type
        
        with pytest.raises(TypeError, match="Strategy must be string or TruncationStrategy enum"):
            TruncationConfig.from_dict(data)
    
    def test_from_dict_invalid_strategy(self):
        """Test error handling for invalid strategy."""
        data = {'strategy': 'invalid_strategy'}
        
        with pytest.raises(ValueError, match="Invalid truncation strategy: invalid_strategy"):
            TruncationConfig.from_dict(data)
    
    def test_from_dict_empty_dict(self):
        """Test creating config from empty dictionary (uses all defaults)."""
        config = TruncationConfig.from_dict({})
        
        # Should use all defaults
        assert config.strategy == TruncationStrategy.HEAD_TAIL
        assert config.max_chars == 50000
        assert config.max_lines == 1000
    
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


class TestConfigLevel:
    """Test cases for ConfigLevel class."""
    
    def test_valid_config_level(self):
        """Test creating valid config level."""
        config = TruncationConfig()
        level = ConfigLevel(
            name="test",
            priority=1,
            config=config,
            source="test_source"
        )
        
        assert level.name == "test"
        assert level.priority == 1
        assert level.config is config
        assert level.source == "test_source"
    
    def test_config_level_with_none_config(self):
        """Test creating config level with None config."""
        level = ConfigLevel(name="test", priority=1)
        
        assert level.name == "test"
        assert level.priority == 1
        assert level.config is None
        assert level.source is None
    
    def test_negative_priority(self):
        """Test validation of negative priority."""
        with pytest.raises(ValueError, match="Priority must be non-negative"):
            ConfigLevel(name="test", priority=-1)
    
    def test_zero_priority(self):
        """Test zero priority is valid."""
        level = ConfigLevel(name="test", priority=0)
        assert level.priority == 0


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
    
    def test_boolean_env_var_variations(self):
        """Test different boolean value formats."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('on', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False),
            ('no', False),
            ('off', False),
            ('anything_else', False),
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'MCP_TRUNCATION_PRESERVE_ERRORS': env_value}):
                result = parse_env_config()
                assert result is not None
                assert result.preserve_errors == expected, f"Failed for env_value: {env_value}"
    
    def test_invalid_numeric_env_vars(self):
        """Test error handling for invalid numeric environment variables."""
        invalid_cases = [
            ('MCP_TRUNCATION_MAX_CHARS', 'not_a_number'),
            ('MCP_TRUNCATION_MAX_LINES', 'invalid'),
            ('MCP_TRUNCATION_HEAD_LINES', '12.5'),
            ('MCP_TRUNCATION_TAIL_LINES', 'abc123'),
        ]
        
        for env_var, invalid_value in invalid_cases:
            with patch.dict(os.environ, {env_var: invalid_value}):
                with pytest.raises(ValueError, match=f"Invalid {env_var}"):
                    parse_env_config()
    
    def test_partial_env_vars(self):
        """Test parsing with only some environment variables set."""
        with patch.dict(os.environ, {'MCP_TRUNCATION_MAX_CHARS': '40000'}):
            result = parse_env_config()
            assert result is not None
            assert result.max_chars == 40000
            # Other values should be system defaults
            assert result.strategy == DEFAULT_SYSTEM_CONFIG.strategy
            assert result.max_lines == DEFAULT_SYSTEM_CONFIG.max_lines


class TestConfigurationManager:
    """Test cases for ConfigurationManager class."""
    
    manager: ConfigurationManager
    
    def setup_method(self):
        """Set up test environment."""
        reset_config_manager()
        self.manager = ConfigurationManager()
    
    def test_initialization(self):
        """Test manager initialization with default levels."""
        # Should have system level by default
        summary = self.manager.get_config_summary()
        assert summary["total_levels"] >= 1
        
        # Check system level exists
        system_levels = [level for level in summary["levels"] if level["name"] == "system"]
        assert len(system_levels) == 1
        assert system_levels[0]["priority"] == 0
    
    def test_initialization_with_env_vars(self):
        """Test manager initialization with environment variables."""
        with patch.dict(os.environ, {'MCP_TRUNCATION_STRATEGY': 'smart_summary'}):
            reset_config_manager()
            manager = ConfigurationManager()
            
            summary = manager.get_config_summary()
            user_levels = [level for level in summary["levels"] if level["name"] == "user"]
            assert len(user_levels) == 1
            assert user_levels[0]["priority"] == 1
            assert user_levels[0]["config"]["strategy"] == "smart_summary"
    
    def test_add_tool_config(self):
        """Test adding tool configuration."""
        tool_data = {
            'name': 'test_tool',
            'truncation': {
                'strategy': 'size_limit',
                'max_chars': 25000
            }
        }
        
        self.manager.add_tool_config('test_tool', tool_data)
        
        summary = self.manager.get_config_summary()
        tool_levels = [level for level in summary["levels"] if level["name"] == "tool_test_tool"]
        assert len(tool_levels) == 1
        assert tool_levels[0]["priority"] == 2
        assert tool_levels[0]["config"]["strategy"] == "size_limit"
        assert tool_levels[0]["config"]["max_chars"] == 25000
    
    def test_add_tool_config_replace_existing(self):
        """Test replacing existing tool configuration."""
        # Add initial config
        tool_data1 = {
            'truncation': {
                'strategy': 'head_tail',
                'max_chars': 20000
            }
        }
        self.manager.add_tool_config('test_tool', tool_data1)
        
        # Replace with new config
        tool_data2 = {
            'truncation': {
                'strategy': 'smart_summary',
                'max_chars': 30000
            }
        }
        self.manager.add_tool_config('test_tool', tool_data2)
        
        # Should only have one config for the tool
        summary = self.manager.get_config_summary()
        tool_levels = [level for level in summary["levels"] if level["name"] == "tool_test_tool"]
        assert len(tool_levels) == 1
        assert tool_levels[0]["config"]["strategy"] == "smart_summary"
        assert tool_levels[0]["config"]["max_chars"] == 30000
    
    def test_add_tool_config_invalid_truncation_data(self):
        """Test error handling for invalid tool truncation data."""
        tool_data = {
            'truncation': {
                'strategy': 'invalid_strategy'
            }
        }
        
        with pytest.raises(ValueError, match="Invalid truncation strategy"):
            self.manager.add_tool_config('test_tool', tool_data)
    
    def test_add_task_config_replace_existing(self):
        """Test replacing existing task configuration."""
        # Add initial config
        task_config1 = TruncationConfig(max_chars=15000)
        self.manager.add_task_config('task123', task_config1)
        
        # Replace with new config
        task_config2 = TruncationConfig(max_chars=25000)
        self.manager.add_task_config('task123', task_config2)
        
        # Should only have one config for the task
        summary = self.manager.get_config_summary()
        task_levels = [level for level in summary["levels"] if level["name"] == "task_task123"]
        assert len(task_levels) == 1
        assert task_levels[0]["config"]["max_chars"] == 25000
    
    def test_remove_nonexistent_task_config(self):
        """Test removing non-existent task configuration."""
        initial_count = len(self.manager._config_levels)
        
        # Should not raise error
        self.manager.remove_task_config('nonexistent_task')
        
        # Count should remain the same
        assert len(self.manager._config_levels) == initial_count
    
    def test_resolve_config_multiple_tools(self):
        """Test config resolution with multiple tools."""
        # Add configs for different tools
        tool_data1 = {
            'truncation': {
                'strategy': 'head_tail',
                'max_chars': 20000
            }
        }
        self.manager.add_tool_config('tool1', tool_data1)
        
        tool_data2 = {
            'truncation': {
                'strategy': 'smart_summary',
                'max_chars': 30000
            }
        }
        self.manager.add_tool_config('tool2', tool_data2)
        
        # Resolve for each tool
        config1 = self.manager.resolve_config(tool_name='tool1')
        assert config1.strategy == TruncationStrategy.HEAD_TAIL
        assert config1.max_chars == 20000
        
        config2 = self.manager.resolve_config(tool_name='tool2')
        assert config2.strategy == TruncationStrategy.SMART_SUMMARY
        assert config2.max_chars == 30000
        
        # Resolve for non-existent tool (should get system defaults)
        config3 = self.manager.resolve_config(tool_name='tool3')
        assert config3.strategy == DEFAULT_SYSTEM_CONFIG.strategy
        assert config3.max_chars == DEFAULT_SYSTEM_CONFIG.max_chars
    
    def test_resolve_config_multiple_tasks(self):
        """Test config resolution with multiple tasks."""
        # Add configs for different tasks
        task_config1 = TruncationConfig(strategy=TruncationStrategy.NONE, max_chars=10000)
        self.manager.add_task_config('task1', task_config1)
        
        task_config2 = TruncationConfig(strategy=TruncationStrategy.SIZE_LIMIT, max_chars=40000)
        self.manager.add_task_config('task2', task_config2)
        
        # Resolve for each task
        config1 = self.manager.resolve_config(task_id='task1')
        assert config1.strategy == TruncationStrategy.NONE
        assert config1.max_chars == 10000
        
        config2 = self.manager.resolve_config(task_id='task2')
        assert config2.strategy == TruncationStrategy.SIZE_LIMIT
        assert config2.max_chars == 40000
    
    def test_load_tool_config_from_nonexistent_file(self):
        """Test loading config from non-existent file."""
        # Should not raise error, just log
        self.manager.load_tool_config_from_file('/nonexistent/path/file.yaml')
        
        # No new configs should be added
        summary = self.manager.get_config_summary()
        tool_levels = [level for level in summary["levels"] if level["name"].startswith("tool_")]
        assert len(tool_levels) == 0
    
    def test_load_tool_config_invalid_yaml(self):
        """Test loading config from invalid YAML file."""
        invalid_yaml = "invalid: yaml: content: ["
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            f.flush()
            
            try:
                with pytest.raises(yaml.YAMLError):
                    self.manager.load_tool_config_from_file(f.name)
            finally:
                os.unlink(f.name)
    
    def test_load_tool_config_non_dict_yaml(self):
        """Test loading config from YAML file with non-dict content."""
        yaml_content = "- item1\n- item2\n"  # List instead of dict
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                # Should not raise error, just log and return
                self.manager.load_tool_config_from_file(f.name)
                
                # No new configs should be added
                summary = self.manager.get_config_summary()
                tool_levels = [level for level in summary["levels"] if level["name"].startswith("tool_")]
                assert len(tool_levels) == 0
                
            finally:
                os.unlink(f.name)
    
    def test_load_tool_configs_from_nonexistent_directory(self):
        """Test loading configs from non-existent directory."""
        # Should not raise error, just log warning
        self.manager.load_tool_configs_from_directory('/nonexistent/directory')
        
        # No new configs should be added
        summary = self.manager.get_config_summary()
        tool_levels = [level for level in summary["levels"] if level["name"].startswith("tool_")]
        assert len(tool_levels) == 0
    
    def test_load_tool_configs_from_file_not_directory(self):
        """Test loading configs from a file path instead of directory."""
        with tempfile.NamedTemporaryFile() as f:
            # Should not raise error, just log error
            self.manager.load_tool_configs_from_directory(f.name)
            
            # No new configs should be added
            summary = self.manager.get_config_summary()
            tool_levels = [level for level in summary["levels"] if level["name"].startswith("tool_")]
            assert len(tool_levels) == 0
    
    def test_validate_configuration_with_invalid_config(self):
        """Test configuration validation with invalid configurations."""
        # Add a valid config first
        valid_config = TruncationConfig(max_chars=25000)
        self.manager.add_task_config('valid_task', valid_config)
        
        # Manually add an invalid config by bypassing validation
        invalid_config = TruncationConfig()
        # Directly modify to make it invalid (bypassing __post_init__)
        invalid_config.__dict__['max_chars'] = -100
        
        self.manager._config_levels.append(ConfigLevel(
            name="invalid_test",
            priority=4,
            config=invalid_config,
            source="test"
        ))
        
        errors = self.manager.validate_configuration()
        assert len(errors) > 0
        assert "Invalid configuration in level 'invalid_test'" in errors[0]
        assert "max_chars must be positive" in errors[0]


class TestGlobalFunctions:
    """Test cases for global configuration functions."""
    
    def setup_method(self):
        """Set up test environment."""
        reset_config_manager()
    
    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns singleton."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is manager2
    
    def test_reset_config_manager(self):
        """Test resetting the global config manager."""
        manager1 = get_config_manager()
        
        # Add some config to the manager
        manager1.add_task_config('test', TruncationConfig())
        
        reset_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is not manager2
        
        # New manager should not have the old config
        summary = manager2.get_config_summary()
        task_levels = [level for level in summary["levels"] if level["name"] == "task_test"]
        assert len(task_levels) == 0
    
    def test_resolve_truncation_config_with_params(self):
        """Test convenience function with parameters."""
        manager = get_config_manager()
        
        # Add tool config
        tool_data = {
            'truncation': {
                'strategy': 'smart_summary',
                'max_chars': 35000
            }
        }
        manager.add_tool_config('test_tool', tool_data)
        
        # Test with tool name
        config = resolve_truncation_config(tool_name='test_tool')
        assert config.strategy == TruncationStrategy.SMART_SUMMARY
        assert config.max_chars == 35000
        
        # Test with both tool and task
        task_config = TruncationConfig(max_chars=20000)
        manager.add_task_config('test_task', task_config)
        
        config = resolve_truncation_config(tool_name='test_tool', task_id='test_task')
        assert config.max_chars == 20000  # Task should override tool


class TestIntegration:
    """Integration tests for the complete configuration system."""
    
    def setup_method(self):
        """Set up test environment."""
        reset_config_manager()
    
    @patch.dict(os.environ, {
        'MCP_TRUNCATION_STRATEGY': 'size_limit',
        'MCP_TRUNCATION_MAX_CHARS': '40000',
        'MCP_TRUNCATION_PRESERVE_ERRORS': 'false'
    })
    def test_full_hierarchy_integration(self):
        """Test complete hierarchy with all levels."""
        manager = get_config_manager()
        
        # Add tool config
        tool_data = {
            'truncation': {
                'strategy': 'smart_summary',
                'max_chars': 30000,
                'preserve_warnings': False
            }
        }
        manager.add_tool_config('integration_tool', tool_data)
        
        # Add task config
        task_config = TruncationConfig(
            strategy=TruncationStrategy.HEAD_TAIL,
            max_chars=20000,
            head_lines=50
        )
        manager.add_task_config('integration_task', task_config)
        
        # Test resolution at different levels
        
        # System + User level (no tool/task specified)
        config = manager.resolve_config()
        assert config.strategy == TruncationStrategy.SIZE_LIMIT  # from env
        assert config.max_chars == 40000  # from env
        assert config.preserve_errors is False  # from env
        
        # System + User + Tool level
        config = manager.resolve_config(tool_name='integration_tool')
        assert config.strategy == TruncationStrategy.SMART_SUMMARY  # from tool
        assert config.max_chars == 30000  # from tool
        assert config.preserve_warnings is False  # from tool
        
        # System + User + Tool + Task level (highest priority)
        config = manager.resolve_config(tool_name='integration_tool', task_id='integration_task')
        assert config.strategy == TruncationStrategy.HEAD_TAIL  # from task
        assert config.max_chars == 20000  # from task
        assert config.head_lines == 50  # from task
    
    def test_complex_yaml_loading(self):
        """Test loading multiple YAML files with complex configurations."""
        manager = get_config_manager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple YAML files with different configurations
            configs = [
                {
                    'filename': 'tool1.yaml',
                    'content': """
name: advanced_tool
description: Advanced tool with complex config
truncation:
  strategy: head_tail
  max_chars: 75000
  max_lines: 1500
  head_lines: 200
  tail_lines: 200
  preserve_errors: true
  preserve_warnings: false
  content_detection: true
"""
                },
                {
                    'filename': 'tool2.yml',
                    'content': """
name: simple_tool
truncation:
  strategy: none
  max_chars: 100000
"""
                },
                {
                    'filename': 'tool3.yaml',
                    'content': """
name: minimal_tool
truncation:
  strategy: size_limit
"""
                }
            ]
            
            # Write YAML files
            for config in configs:
                with open(Path(temp_dir) / config['filename'], 'w') as f:
                    f.write(config['content'])
            
            # Load all configs
            manager.load_tool_configs_from_directory(temp_dir)
            
            # Test each tool's configuration
            config1 = manager.resolve_config(tool_name='advanced_tool')
            assert config1.strategy == TruncationStrategy.HEAD_TAIL
            assert config1.max_chars == 75000
            assert config1.max_lines == 1500
            assert config1.head_lines == 200
            assert config1.tail_lines == 200
            assert config1.preserve_errors is True
            assert config1.preserve_warnings is False
            
            config2 = manager.resolve_config(tool_name='simple_tool')
            assert config2.strategy == TruncationStrategy.NONE
            assert config2.max_chars == 100000
            
            config3 = manager.resolve_config(tool_name='minimal_tool')
            assert config3.strategy == TruncationStrategy.SIZE_LIMIT
            # Other values should be defaults
            assert config3.max_chars == 50000  # default
    
    def test_priority_ordering_edge_cases(self):
        """Test priority ordering with edge cases."""
        manager = get_config_manager()
        
        # Add multiple configs with same priority (should not happen in normal use)
        # but test the sorting behavior
        
        # Add multiple tool configs
        for i in range(5):
            tool_data = {
                'truncation': {
                    'strategy': 'head_tail',
                    'max_chars': 10000 + (i * 1000)
                }
            }
            manager.add_tool_config(f'tool_{i}', tool_data)
        
        # Add multiple task configs
        for i in range(3):
            task_config = TruncationConfig(max_chars=50000 + (i * 5000))
            manager.add_task_config(f'task_{i}', task_config)
        
        # Test that the correct configs are applied
        config = manager.resolve_config(tool_name='tool_2', task_id='task_1')
        assert config.max_chars == 55000  # from task_1
        
        config = manager.resolve_config(tool_name='tool_3')
        assert config.max_chars == 13000  # from tool_3
    
    def test_configuration_summary_completeness(self):
        """Test that configuration summary includes all expected information."""
        manager = get_config_manager()
        
        # Add various configurations
        tool_data = {
            'truncation': {
                'strategy': 'smart_summary',
                'max_chars': 25000
            }
        }
        manager.add_tool_config('summary_tool', tool_data, '/path/to/tool.yaml')
        
        task_config = TruncationConfig(strategy=TruncationStrategy.NONE)
        manager.add_task_config('summary_task', task_config)
        
        summary = manager.get_config_summary()
        
        # Check structure
        assert 'levels' in summary
        assert 'total_levels' in summary
        assert isinstance(summary['levels'], list)
        assert isinstance(summary['total_levels'], int)
        
        # Check that all levels are included
        level_names = [level['name'] for level in summary['levels']]
        assert 'system' in level_names
        assert 'tool_summary_tool' in level_names
        assert 'task_summary_task' in level_names
        
        # Check level details
        for level in summary['levels']:
            assert 'name' in level
            assert 'priority' in level
            assert 'source' in level
            assert 'has_config' in level
            
            if level['has_config']:
                assert 'config' in level
                config = level['config']
                assert 'strategy' in config
                assert 'max_chars' in config
        
        # Check priority ordering (highest first)
        priorities = [level['priority'] for level in summary['levels']]
        assert priorities == sorted(priorities, reverse=True) 