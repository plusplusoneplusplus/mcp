#!/usr/bin/env python3
"""
Example usage of the hierarchical configuration system.

This script demonstrates how to use the configuration manager to resolve
truncation settings across different priority levels.
"""

import os
import tempfile
from pathlib import Path

from utils.output_processor import (
    TruncationConfig,
    TruncationStrategy,
    get_config_manager,
    resolve_truncation_config,
    reset_config_manager
)


def main():
    """Demonstrate the hierarchical configuration system."""
    print("=== Hierarchical Configuration System Demo ===\n")
    
    # Reset to start fresh
    reset_config_manager()
    manager = get_config_manager()
    
    # 1. Show system defaults
    print("1. System defaults:")
    config = resolve_truncation_config()
    print(f"   Strategy: {config.strategy.value}")
    print(f"   Max chars: {config.max_chars}")
    print(f"   Max lines: {config.max_lines}")
    print()
    
    # 2. Add environment variable configuration
    print("2. Adding user-level configuration via environment variables:")
    os.environ['MCP_TRUNCATION_STRATEGY'] = 'smart_summary'
    os.environ['MCP_TRUNCATION_MAX_CHARS'] = '30000'
    
    # Reset to pick up environment variables
    reset_config_manager()
    manager = get_config_manager()
    
    config = resolve_truncation_config()
    print(f"   Strategy: {config.strategy.value}")
    print(f"   Max chars: {config.max_chars}")
    print()
    
    # 3. Add tool-level configuration
    print("3. Adding tool-level configuration:")
    tool_yaml_data = {
        'name': 'example_tool',
        'truncation': {
            'strategy': 'size_limit',
            'max_chars': 25000,
            'preserve_errors': False
        }
    }
    
    manager.add_tool_config('example_tool', tool_yaml_data)
    
    # Resolve for the specific tool
    config = resolve_truncation_config(tool_name='example_tool')
    print(f"   Strategy: {config.strategy.value}")
    print(f"   Max chars: {config.max_chars}")
    print(f"   Preserve errors: {config.preserve_errors}")
    print()
    
    # 4. Add task-level configuration (highest priority)
    print("4. Adding task-level configuration (highest priority):")
    task_config = TruncationConfig(
        strategy=TruncationStrategy.HEAD_TAIL,
        max_chars=15000,
        head_lines=50,
        tail_lines=50
    )
    
    manager.add_task_config('urgent_task', task_config)
    
    # Resolve for specific tool and task
    config = resolve_truncation_config(tool_name='example_tool', task_id='urgent_task')
    print(f"   Strategy: {config.strategy.value}")
    print(f"   Max chars: {config.max_chars}")
    print(f"   Head lines: {config.head_lines}")
    print(f"   Tail lines: {config.tail_lines}")
    print()
    
    # 5. Show configuration hierarchy
    print("5. Configuration hierarchy summary:")
    summary = manager.get_config_summary()
    print(f"   Total levels: {summary['total_levels']}")
    
    for level in summary['levels']:
        print(f"   - {level['name']} (priority: {level['priority']}, source: {level['source']})")
        if level['has_config']:
            config_info = level['config']
            print(f"     Strategy: {config_info['strategy']}, Max chars: {config_info['max_chars']}")
    print()
    
    # 6. Demonstrate YAML file loading
    print("6. Loading configuration from YAML file:")
    
    yaml_content = """
name: file_tool
description: Tool loaded from YAML file
truncation:
  strategy: none
  max_chars: 100000
  preserve_warnings: false
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        f.flush()
        
        try:
            manager.load_tool_config_from_file(f.name)
            
            config = resolve_truncation_config(tool_name='file_tool')
            print(f"   Strategy: {config.strategy.value}")
            print(f"   Max chars: {config.max_chars}")
            print(f"   Preserve warnings: {config.preserve_warnings}")
            
        finally:
            os.unlink(f.name)
    
    print()
    
    # 7. Validation
    print("7. Configuration validation:")
    errors = manager.validate_configuration()
    if errors:
        print("   Validation errors found:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("   All configurations are valid!")
    
    # Clean up environment variables
    os.environ.pop('MCP_TRUNCATION_STRATEGY', None)
    os.environ.pop('MCP_TRUNCATION_MAX_CHARS', None)
    
    print("\n=== Demo completed ===")


if __name__ == '__main__':
    main() 