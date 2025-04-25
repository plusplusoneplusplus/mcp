import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.environment import Environment, get_private_tool_root

def setup_test_directory():
    """Set up a temporary directory with test configuration files"""
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory: {temp_dir}")
    
    # Create tools.yaml in the temporary directory
    tools_yaml = Path(temp_dir) / "tools.yaml"
    with open(tools_yaml, 'w') as f:
        f.write("""
tools:
  private_test_tool:
    name: Private Test Tool
    description: A private test tool loaded from PRIVATE_TOOL_ROOT
    type: script
    script: private_test_script.ps1
    inputSchema:
      type: object
      properties:
        param1:
          type: string
          description: Test parameter
      required:
        - param1

tasks:
  private_test_task:
    description: A private test task from PRIVATE_TOOL_ROOT
    commands:
      windows: echo This is a private task from PRIVATE_TOOL_ROOT
      linux: echo This is a private task from PRIVATE_TOOL_ROOT
      darwin: echo This is a private task from PRIVATE_TOOL_ROOT
""")
    
    # Create a test script
    test_script = Path(temp_dir) / "private_test_script.ps1"
    with open(test_script, 'w') as f:
        f.write("""
param (
    [string]$param1
)

Write-Output "Private test script executed with parameter: $param1"
""")
    
    # Create prompts.yaml in the temporary directory
    prompts_yaml = Path(temp_dir) / "prompts.yaml"
    with open(prompts_yaml, 'w') as f:
        f.write("""
prompts:
  private_test_prompt:
    name: Private Test Prompt
    description: A private test prompt loaded from PRIVATE_TOOL_ROOT
    arguments:
      - name: param1
        description: Test parameter
        required: true
    template: "This is a private prompt template with {param1}"
    enabled: true
""")
    
    return temp_dir

def test_private_tool_root():
    """Test loading tools from PRIVATE_TOOL_ROOT"""
    # Set up test directory
    temp_dir = setup_test_directory()
    
    try:
        # Set PRIVATE_TOOL_ROOT environment variable
        original_value = os.environ.get('PRIVATE_TOOL_ROOT')
        os.environ['PRIVATE_TOOL_ROOT'] = temp_dir
        
        # Reset the Environment singleton
        Environment._instance = None
        new_env = Environment()
        new_env.load()  # Explicitly load environment variables
        
        # Update the global env reference used by helper functions
        import server.environment
        server.environment.env = new_env
        
        # Verify the environment variable is loaded
        private_tool_root = get_private_tool_root()
        print(f"PRIVATE_TOOL_ROOT: {private_tool_root}")
        assert private_tool_root == temp_dir
        
        # Import and test tools loading
        # Only import these now after setting the environment variable
        from mcp_tools.tools import load_tools_from_yaml, load_tasks_from_yaml
        
        # Load tools and verify the private test tool is loaded
        tools = load_tools_from_yaml()
        print("\nLoaded tools:")
        for name, tool in tools.items():
            print(f"- {name}: {tool.get('description', 'No description')}")
        
        assert 'private_test_tool' in tools, "Private test tool not found"
        
        # Load tasks and verify the private test task is loaded
        tasks = load_tasks_from_yaml()
        print("\nLoaded tasks:")
        for name, task in tasks.items():
            print(f"- {name}: {task.get('description', 'No description')}")
        
        assert 'private_test_task' in tasks, "Private test task not found"
        
        # Test prompts loading
        from server.prompts import load_prompts_from_yaml
        
        # Load prompts and verify the private test prompt is loaded
        prompts = load_prompts_from_yaml()
        print("\nLoaded prompts:")
        for name, prompt in prompts.items():
            print(f"- {name}: {prompt.get('description', 'No description')}")
        
        assert 'private_test_prompt' in prompts, "Private test prompt not found"
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temporary directory: {temp_dir}")
        
        # Restore original environment variable
        if original_value:
            os.environ['PRIVATE_TOOL_ROOT'] = original_value
        else:
            if 'PRIVATE_TOOL_ROOT' in os.environ:
                del os.environ['PRIVATE_TOOL_ROOT']

if __name__ == "__main__":
    test_private_tool_root()
    print("\nTest completed successfully!") 