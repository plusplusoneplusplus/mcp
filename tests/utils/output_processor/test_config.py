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
from unittest.mock import patch, mock_open

from utils.output_processor.schemas import (
    TruncationConfig,
    TruncationStrategy,
    ConfigLevel,
    ConfigSource,
    DEFAULT_SYSTEM_CONFIG,
    parse_env_config
)
from utils.output_processor.config import (
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
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = TruncationConfig(
            strategy=TruncationStrategy.SMART_SUMMARY,
            max_chars=25000,
            max_lines=500,
            head_lines=50,
            tail_lines=50,
            preserve_errors=False,
            preserve_warnings=False,
            content_detection=False
        )
        
        assert config.strategy == TruncationStrategy.SMART_SUMMARY
        assert config.max_chars == 25000
        assert config.max_lines == 500
        assert config.head_lines == 50
        assert config.tail_lines == 50
        assert config.preserve_errors is False
        assert config.preserve_warnings is False
        assert config.content_detection is False
    
    def test_validation_positive_max_chars(self):
        """Test validation of positive max_chars."""
        with pytest.raises(ValueError, match="max_chars must be positive"):
            TruncationConfig(max_chars=0)
        
        with pytest.raises(ValueError, match="max_chars must be positive"):
            TruncationConfig(max_chars=-100)
    
    def test_validation_positive_max_lines(self):
        """Test validation of positive max_lines."""
        with pytest.raises(ValueError, match="max_lines must be positive"):
            TruncationConfig(max_lines=0)
        
        with pytest.raises(ValueError, match="max_lines must be positive"):
            TruncationConfig(max_lines=-50)
    
    def test_validation_non_negative_head_tail_lines(self):
        """Test validation of non-negative head/tail lines."""
        with pytest.raises(ValueError, match="head_lines must be non-negative"):
            TruncationConfig(head_lines=-1)
        
        with pytest.raises(ValueError, match="tail_lines must be non-negative"):
            TruncationConfig(tail_lines=-1)
    
    def test_validation_head_tail_sum(self):
        """Test validation that head_lines + tail_lines <= max_lines."""
        with pytest.raises(ValueError, match="head_lines \\+ tail_lines cannot exceed max_lines"):
            TruncationConfig(max_lines=100, head_lines=60, tail_lines=50)
    
    def test_from_dict_valid(self):
        """Test creating config from valid dictionary."""
        data = {
            'strategy': 'smart_summary',
            'max_chars': 30000,
            'max_lines': 800,
            'head_lines': 80,
            'tail_lines': 80,
            'preserve_errors': False,
            'preserve_warnings': True,
            'content_detection': False
        }
        
        config = TruncationConfig.from_dict(data)
        
        assert config.strategy == TruncationStrategy.SMART_SUMMARY
        assert config.max_chars == 30000
        assert config.max_lines == 800
        assert config.head_lines == 80
        assert config.tail_lines == 80
        assert config.preserve_errors is False
        assert config.preserve_warnings is True
        assert config.content_detection is False
    
    def test_from_dict_partial(self):
        """Test creating config from partial dictionary (uses defaults)."""
        data = {
            'strategy': 'size_limit',
            'max_chars': 20000
        }
        
        config = TruncationConfig.from_dict(data)
        
        assert config.strategy == TruncationStrategy.SIZE_LIMIT
        assert config.max_chars == 20000
        assert config.max_lines == 1000  # default
        assert config.head_lines == 100  # default
    
    def test_from_dict_invalid_strategy(self):
        """Test error handling for invalid strategy."""
        data = {'strategy': 'invalid_strategy'}
        
        with pytest.raises(ValueError, match="Invalid truncation strategy: invalid_strategy"):
            TruncationConfig.from_dict(data)
    
    def test_from_dict_invalid_type(self):
        """Test error handling for invalid data type."""
        with pytest.raises(TypeError, match="Configuration data must be a dictionary"):
            TruncationConfig.from_dict("not a dict")
    
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
    
    def test_merge_with_none(self):
        """Test merging with None returns copy of original."""
        config = TruncationConfig(max_chars=25000)
        result = config.merge_with(None)
        
        assert result.max_chars == 25000
        assert result is not config  # Should be a new instance
    
    def test_merge_with_other(self):
        """Test merging with another config (other takes precedence)."""
        base_config = TruncationConfig(
            max_chars=25000,
            max_lines=500,
            preserve_errors=True
        )
        
        override_config = TruncationConfig(
            max_chars=35000,
            preserve_errors=False
        )
        
        result = base_config.merge_with(override_config)
        
        # Override values should be used
        assert result.max_chars == 35000
        assert result.preserve_errors is False
        # Non-overridden values should come from override (not base)
        assert result.max_lines == 1000  # from override's default


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
    
    def test_negative_priority(self):
        """Test validation of negative priority."""
        with pytest.raises(ValueError, match="Priority must be non-negative"):
            ConfigLevel(name="test", priority=-1)


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
    
    def test_numeric_env_vars(self):
        """Test parsing numeric environment variables."""
        env_vars = {
            'MCP_TRUNCATION_MAX_CHARS': '30000',
            'MCP_TRUNCATION_MAX_LINES': '800',
            'MCP_TRUNCATION_HEAD_LINES': '80',
            'MCP_TRUNCATION_TAIL_LINES': '80'
        }
        
        with patch.dict(os.environ, env_vars):
            result = parse_env_config()
            assert result is not None
            assert result.max_chars == 30000
            assert result.max_lines == 800
            assert result.head_lines == 80
            assert result.tail_lines == 80
    
    def test_boolean_env_vars(self):
        """Test parsing boolean environment variables."""
        env_vars = {
            'MCP_TRUNCATION_PRESERVE_ERRORS': 'false',
            'MCP_TRUNCATION_PRESERVE_WARNINGS': 'true',
            'MCP_TRUNCATION_CONTENT_DETECTION': '1'
        }
        
        with patch.dict(os.environ, env_vars):
            result = parse_env_config()
            assert result is not None
            assert result.preserve_errors is False
            assert result.preserve_warnings is True
            assert result.content_detection is True
    
    def test_invalid_numeric_env_var(self):
        """Test error handling for invalid numeric environment variables."""
        with patch.dict(os.environ, {'MCP_TRUNCATION_MAX_CHARS': 'not_a_number'}):
            with pytest.raises(ValueError, match="Invalid MCP_TRUNCATION_MAX_CHARS"):
                parse_env_config()


class TestConfigurationManager:
    """Test cases for ConfigurationManager class."""
    
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
    
    def test_add_tool_config_no_truncation(self):
        """Test adding tool config without truncation section."""
        tool_data = {'name': 'test_tool'}
        
        # Should not raise error, just log debug message
        self.manager.add_tool_config('test_tool', tool_data)
        
        summary = self.manager.get_config_summary()
        tool_levels = [level for level in summary["levels"] if level["name"] == "tool_test_tool"]
        assert len(tool_levels) == 0
    
    def test_add_task_config(self):
        """Test adding task configuration."""
        task_config = TruncationConfig(
            strategy=TruncationStrategy.NONE,
            max_chars=15000
        )
        
        self.manager.add_task_config('task123', task_config)
        
        summary = self.manager.get_config_summary()
        task_levels = [level for level in summary["levels"] if level["name"] == "task_task123"]
        assert len(task_levels) == 1
        assert task_levels[0]["priority"] == 3
        assert task_levels[0]["config"]["strategy"] == "none"
        assert task_levels[0]["config"]["max_chars"] == 15000
    
    def test_remove_task_config(self):
        """Test removing task configuration."""
        task_config = TruncationConfig(max_chars=15000)
        self.manager.add_task_config('task123', task_config)
        
        # Verify it was added
        summary = self.manager.get_config_summary()
        task_levels = [level for level in summary["levels"] if level["name"] == "task_task123"]
        assert len(task_levels) == 1
        
        # Remove it
        self.manager.remove_task_config('task123')
        
        # Verify it was removed
        summary = self.manager.get_config_summary()
        task_levels = [level for level in summary["levels"] if level["name"] == "task_task123"]
        assert len(task_levels) == 0
    
    def test_resolve_config_system_only(self):
        """Test config resolution with only system defaults."""
        config = self.manager.resolve_config()
        
        # Should return system defaults
        assert config.strategy == DEFAULT_SYSTEM_CONFIG.strategy
        assert config.max_chars == DEFAULT_SYSTEM_CONFIG.max_chars
    
    def test_resolve_config_hierarchy(self):
        """Test config resolution with full hierarchy."""
        # Add tool config
        tool_data = {
            'truncation': {
                'strategy': 'size_limit',
                'max_chars': 25000
            }
        }
        self.manager.add_tool_config('test_tool', tool_data)
        
        # Add task config
        task_config = TruncationConfig(
            strategy=TruncationStrategy.NONE,
            max_chars=15000
        )
        self.manager.add_task_config('task123', task_config)
        
        # Resolve for specific tool and task
        config = self.manager.resolve_config(tool_name='test_tool', task_id='task123')
        
        # Task config should have highest priority
        assert config.strategy == TruncationStrategy.NONE
        assert config.max_chars == 15000
    
    def test_resolve_config_tool_specific(self):
        """Test config resolution for specific tool."""
        # Add tool config
        tool_data = {
            'truncation': {
                'strategy': 'smart_summary',
                'max_chars': 30000
            }
        }
        self.manager.add_tool_config('test_tool', tool_data)
        
        # Resolve for specific tool
        config = self.manager.resolve_config(tool_name='test_tool')
        
        assert config.strategy == TruncationStrategy.SMART_SUMMARY
        assert config.max_chars == 30000
        
        # Resolve for different tool (should get system defaults)
        config = self.manager.resolve_config(tool_name='other_tool')
        
        assert config.strategy == DEFAULT_SYSTEM_CONFIG.strategy
        assert config.max_chars == DEFAULT_SYSTEM_CONFIG.max_chars
    
    def test_load_tool_config_from_file(self):
        """Test loading tool config from YAML file."""
        yaml_content = """
name: test_tool
description: A test tool
truncation:
  strategy: smart_summary
  max_chars: 35000
  preserve_errors: false
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                self.manager.load_tool_config_from_file(f.name)
                
                summary = self.manager.get_config_summary()
                tool_levels = [level for level in summary["levels"] if level["name"] == "tool_test_tool"]
                assert len(tool_levels) == 1
                assert tool_levels[0]["config"]["strategy"] == "smart_summary"
                assert tool_levels[0]["config"]["max_chars"] == 35000
                assert tool_levels[0]["config"]["preserve_errors"] is False
                
            finally:
                os.unlink(f.name)
    
    def test_load_tool_config_from_directory(self):
        """Test loading tool configs from directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test YAML files
            tool1_yaml = """
name: tool1
truncation:
  strategy: head_tail
  max_chars: 20000
"""
            
            tool2_yaml = """
name: tool2
truncation:
  strategy: size_limit
  max_lines: 500
"""
            
            with open(Path(temp_dir) / "tool1.yaml", 'w') as f:
                f.write(tool1_yaml)
            
            with open(Path(temp_dir) / "tool2.yml", 'w') as f:
                f.write(tool2_yaml)
            
            self.manager.load_tool_configs_from_directory(temp_dir)
            
            summary = self.manager.get_config_summary()
            
            # Check tool1 config
            tool1_levels = [level for level in summary["levels"] if level["name"] == "tool_tool1"]
            assert len(tool1_levels) == 1
            assert tool1_levels[0]["config"]["max_chars"] == 20000
            
            # Check tool2 config
            tool2_levels = [level for level in summary["levels"] if level["name"] == "tool_tool2"]
            assert len(tool2_levels) == 1
            assert tool2_levels[0]["config"]["max_lines"] == 500
    
    def test_validate_configuration(self):
        """Test configuration validation."""
        # Add valid config
        valid_config = TruncationConfig(max_chars=25000)
        self.manager.add_task_config('valid_task', valid_config)
        
        errors = self.manager.validate_configuration()
        assert len(errors) == 0
        
        # Add invalid config by directly manipulating the levels
        invalid_config = TruncationConfig()
        invalid_config.max_chars = -100  # Invalid value
        
        self.manager._config_levels.append(ConfigLevel(
            name="invalid_test",
            priority=4,
            config=invalid_config,
            source="test"
        ))
        
        errors = self.manager.validate_configuration()
        assert len(errors) > 0
        assert "Invalid configuration in level 'invalid_test'" in errors[0]


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
        reset_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is not manager2
    
    def test_resolve_truncation_config(self):
        """Test convenience function for config resolution."""
        config = resolve_truncation_config()
        
        # Should return system defaults
        assert config.strategy == DEFAULT_SYSTEM_CONFIG.strategy
        assert config.max_chars == DEFAULT_SYSTEM_CONFIG.max_chars
    
    @patch.dict(os.environ, {'MCP_TRUNCATION_STRATEGY': 'smart_summary'})
    def test_resolve_with_env_vars(self):
        """Test config resolution with environment variables."""
        reset_config_manager()  # Force re-initialization with env vars
        
        config = resolve_truncation_config()
        assert config.strategy == TruncationStrategy.SMART_SUMMARY


class TestIntegration:
    """Integration tests for the complete configuration system."""
    
    def setup_method(self):
        """Set up test environment."""
        reset_config_manager()
    
    @patch.dict(os.environ, {
        'MCP_TRUNCATION_STRATEGY': 'size_limit',
        'MCP_TRUNCATION_MAX_CHARS': '40000'
    })
    def test_full_hierarchy_integration(self):
        """Test complete hierarchy with all levels."""
        manager = get_config_manager()
        
        # Add tool config
        tool_data = {
            'truncation': {
                'strategy': 'smart_summary',
                'max_chars': 30000,
                'preserve_errors': False
            }
        }
        manager.add_tool_config('integration_tool', tool_data)
        
        # Add task config
        task_config = TruncationConfig(
            strategy=TruncationStrategy.HEAD_TAIL,
            max_chars=20000
        )
        manager.add_task_config('integration_task', task_config)
        
        # Test resolution at different levels
        
        # System + User level (no tool/task specified)
        config = manager.resolve_config()
        assert config.strategy == TruncationStrategy.SIZE_LIMIT  # from env
        assert config.max_chars == 40000  # from env
        
        # System + User + Tool level
        config = manager.resolve_config(tool_name='integration_tool')
        assert config.strategy == TruncationStrategy.SMART_SUMMARY  # from tool
        assert config.max_chars == 30000  # from tool
        assert config.preserve_errors is False  # from tool
        
        # System + User + Tool + Task level (highest priority)
        config = manager.resolve_config(tool_name='integration_tool', task_id='integration_task')
        assert config.strategy == TruncationStrategy.HEAD_TAIL  # from task
        assert config.max_chars == 20000  # from task
        # Other values should come from task's defaults, not lower levels
        assert config.preserve_errors is True  # task default
    
    def test_yaml_parsing_edge_cases(self):
        """Test YAML parsing with various edge cases."""
        manager = get_config_manager()
        
        # Test with minimal YAML
        minimal_yaml = """
truncation:
  strategy: none
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(minimal_yaml)
            f.flush()
            
            try:
                manager.load_tool_config_from_file(f.name)
                
                # Tool name should be derived from filename
                config = manager.resolve_config(tool_name=Path(f.name).stem)
                assert config.strategy == TruncationStrategy.NONE
                
            finally:
                os.unlink(f.name) 