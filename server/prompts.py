import os
from pathlib import Path
import yaml

from mcp.types import (
    TextContent,
    Prompt,
    PromptArgument,
    GetPromptResult,
    PromptMessage
)

from config import env

def load_prompts_from_yaml() -> dict:
    """Load prompts from the prompts.yaml file."""
    yaml_data = {}
    
    # Priority 1: Load from PRIVATE_TOOL_ROOT if set
    private_tool_root = env.get_private_tool_root()
    if private_tool_root:
        private_root_path = Path(private_tool_root)
        private_yaml_path = private_root_path / "prompts.yaml"
        if private_yaml_path.exists():
            print(f"Loading prompts.yaml from PRIVATE_TOOL_ROOT: {private_yaml_path}")
            try:
                with open(private_yaml_path, 'r') as file:
                    yaml_data = yaml.safe_load(file)
                    prompts = yaml_data.get('prompts', {})
                    # Filter out disabled prompts
                    prompts = {k: v for k, v in prompts.items() if v.get('enabled', True)}
                    return prompts
            except Exception as e:
                print(f"Error loading prompts from PRIVATE_TOOL_ROOT: {e}")
    
    # Priority 2: Load from private directory in server folder
    private_yaml_path = Path(__file__).resolve().parent / ".private" / "prompts.yaml"
    if private_yaml_path.exists():
        print(f"Loading prompts.yaml from private directory: {private_yaml_path}")
        try:
            with open(private_yaml_path, 'r') as file:
                yaml_data = yaml.safe_load(file)
                prompts = yaml_data.get('prompts', {})
                # Filter out disabled prompts
                prompts = {k: v for k, v in prompts.items() if v.get('enabled', True)}
                return prompts
        except Exception as e:
            print(f"Error loading prompts from private directory: {e}")
    
    # Priority 3: Fallback to default location
    yaml_path = Path(__file__).resolve().parent / "prompts.yaml"
    if yaml_path.exists():
        print(f"Loading prompts.yaml from default location: {yaml_path}")
        try:
            with open(yaml_path, 'r') as file:
                yaml_data = yaml.safe_load(file)
        except Exception as e:
            print(f"Error loading prompts from default location: {e}")
    
    prompts = yaml_data.get('prompts', {})
    # Filter out disabled prompts
    prompts = {k: v for k, v in prompts.items() if v.get('enabled', True)}
    return prompts

def convert_yaml_to_prompts(yaml_prompts: dict) -> dict:
    """Convert YAML prompt definitions to Prompt objects."""
    prompts = {}
    
    for key, prompt_data in yaml_prompts.items():
        arguments = []
        if 'arguments' in prompt_data:
            for arg in prompt_data['arguments']:
                arguments.append(
                    PromptArgument(
                        name=arg.get('name', ''),
                        description=arg.get('description', ''),
                        required=arg.get('required', False)
                    )
                )
        
        prompts[key] = Prompt(
            name=prompt_data.get('name', key),
            description=prompt_data.get('description', ''),
            arguments=arguments
        )
    
    return prompts

# Load prompts from YAML
yaml_prompts = load_prompts_from_yaml()
PROMPTS = convert_yaml_to_prompts(yaml_prompts)

def get_prompts() -> list[Prompt]:
    """Return a list of available prompts."""
    return list(PROMPTS.values())

def get_prompt(name: str, arguments: dict) -> GetPromptResult:
    """Get a prompt by name with the provided arguments."""
    if name not in PROMPTS:
        raise ValueError(f"Prompt not found: {name}")

    # For prompts loaded from YAML that have a template
    yaml_prompts_dict = load_prompts_from_yaml()
    if name in yaml_prompts_dict and 'template' in yaml_prompts_dict[name]:
        template = yaml_prompts_dict[name]['template']
        # Replace placeholders with argument values
        for arg_name, arg_value in arguments.items():
            template = template.replace(f"{{{arg_name}}}", str(arg_value))
        
        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=template
                    )
                )
            ]
        )
    
    # Handle any prompts that need custom logic beyond templates
    # (No custom prompts currently)
    
    # Fallback error if prompt is found but has no template or custom handler
    raise ValueError(f"No template or handler found for prompt: {name}") 