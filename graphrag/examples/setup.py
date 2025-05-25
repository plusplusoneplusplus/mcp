#!/usr/bin/env python3
"""
GraphRAG Examples Setup Script

This script helps you set up the environment for running GraphRAG examples.
It checks dependencies, validates configuration, and provides helpful guidance.
Supports both OpenAI and Azure OpenAI.
"""

import os
import subprocess
import sys
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def check_package_installed(package_name):
    """Check if a Python package is installed."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def install_package(package_name):
    """Install a Python package using uv."""
    try:
        subprocess.check_call([sys.executable, "-m", "uv", "add", package_name])
        return True
    except subprocess.CalledProcessError:
        # Fallback to pip if uv is not available
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            return True
        except subprocess.CalledProcessError:
            return False


def check_dependencies():
    """Check and install required dependencies."""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        ("graphrag", "graphrag"),
        ("yaml", "PyYAML"),
        ("pathlib", None),  # Built-in, no install needed
    ]
    
    missing_packages = []
    
    for package_name, install_name in required_packages:
        if install_name is None:  # Built-in package
            print(f"✅ {package_name} (built-in)")
            continue
            
        if check_package_installed(package_name):
            print(f"✅ {package_name}")
        else:
            print(f"❌ {package_name} (missing)")
            missing_packages.append(install_name)
    
    if missing_packages:
        print(f"\n📥 Installing missing packages: {', '.join(missing_packages)}")
        for package in missing_packages:
            print(f"   Installing {package}...")
            if install_package(package):
                print(f"   ✅ {package} installed successfully")
            else:
                print(f"   ❌ Failed to install {package}")
                return False
    
    return True


def check_environment_variables():
    """Check if required environment variables are set."""
    print("\n🔑 Checking environment variables...")
    
    provider = os.getenv("GRAPHRAG_PROVIDER", "openai").lower()
    
    if provider == "azure_openai":
        required_vars = [
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_LLM_DEPLOYMENT",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        ]
        optional_vars = [
            ("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            ("AZURE_OPENAI_MAX_TOKENS", "4000"),
            ("AZURE_OPENAI_TEMPERATURE", "0.0"),
            ("GRAPHRAG_DATA_DIR", "./graphrag_data"),
        ]
        provider_name = "Azure OpenAI"
    else:
        required_vars = ["OPENAI_API_KEY"]
        optional_vars = [
            ("OPENAI_MODEL", "gpt-4-turbo-preview"),
            ("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            ("GRAPHRAG_DATA_DIR", "./graphrag_data"),
            ("OPENAI_MAX_TOKENS", "4000"),
            ("OPENAI_TEMPERATURE", "0.0"),
        ]
        provider_name = "OpenAI"
    
    missing_required = []
    
    print(f"   Provider: {provider} ({provider_name})")
    
    # Check required variables
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if "API_KEY" in var:
                print(f"✅ {var}: {'*' * 20}...{value[-4:]}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")
            missing_required.append(var)
    
    # Check optional variables
    for var, default in optional_vars:
        value = os.getenv(var, default)
        print(f"ℹ️  {var}: {value}")
    
    if missing_required:
        print(f"\n⚠️  Missing required {provider_name} environment variables:")
        for var in missing_required:
            print(f"   export {var}='your-value-here'")
        return False
    
    return True


def create_sample_config():
    """Create a sample configuration file."""
    config_path = Path("config.yaml")
    
    if config_path.exists():
        print(f"ℹ️  Configuration file already exists: {config_path}")
        return
    
    print(f"\n📝 Creating sample configuration file: {config_path}")
    
    provider = os.getenv("GRAPHRAG_PROVIDER", "openai").lower()
    
    if provider == "azure_openai":
        config_content = """# GraphRAG Configuration - Azure OpenAI
provider: "azure_openai"

llm:
  api_key: "${AZURE_OPENAI_API_KEY}"
  azure_endpoint: "${AZURE_OPENAI_ENDPOINT}"
  azure_deployment: "${AZURE_OPENAI_LLM_DEPLOYMENT}"
  api_version: "2024-02-15-preview"
  max_tokens: 4000
  temperature: 0.0

embeddings:
  api_key: "${AZURE_OPENAI_API_KEY}"
  azure_endpoint: "${AZURE_OPENAI_ENDPOINT}"
  azure_deployment: "${AZURE_OPENAI_EMBEDDING_DEPLOYMENT}"
  api_version: "2024-02-15-preview"

chunk_size: 1200
chunk_overlap: 100
data_dir: "./graphrag_data"
"""
    else:
        config_content = """# GraphRAG Configuration - OpenAI
provider: "openai"

llm:
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4-turbo-preview"
  max_tokens: 4000
  temperature: 0.0

embeddings:
  api_key: "${OPENAI_API_KEY}"
  model: "text-embedding-3-small"

chunk_size: 1200
chunk_overlap: 100
data_dir: "./graphrag_data"
"""
    
    try:
        with open(config_path, "w") as f:
            f.write(config_content)
        print(f"✅ Created {config_path}")
    except Exception as e:
        print(f"❌ Failed to create {config_path}: {e}")


def show_next_steps():
    """Show next steps to the user."""
    print("\n🚀 Setup Complete! Next Steps:")
    print("=" * 50)
    
    provider = os.getenv("GRAPHRAG_PROVIDER", "openai").lower()
    
    if provider == "azure_openai":
        print("\n1. Set your Azure OpenAI environment variables (if not already set):")
        print("   export AZURE_OPENAI_API_KEY='your-azure-api-key'")
        print("   export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com/'")
        print("   export AZURE_OPENAI_LLM_DEPLOYMENT='your-gpt-deployment-name'")
        print("   export AZURE_OPENAI_EMBEDDING_DEPLOYMENT='your-embedding-deployment-name'")
        print("   export GRAPHRAG_PROVIDER='azure_openai'")
    else:
        print("\n1. Set your OpenAI API key (if not already set):")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        print("   export GRAPHRAG_PROVIDER='openai'  # Optional, this is the default")
    
    print("\n2. Run the basic example:")
    print("   python basic_example.py")
    
    print("\n3. Or run the environment-based example:")
    print("   python env_config_example.py")
    
    print("\n4. Customize the configuration:")
    print("   - Edit config.yaml for file-based configuration")
    print("   - Or set environment variables for env-based configuration")
    
    print("\n📚 Available examples:")
    examples_dir = Path(".")
    for example_file in examples_dir.glob("*example.py"):
        print(f"   - {example_file.name}")
    
    print("\n🔄 To switch providers:")
    print("   - For OpenAI: export GRAPHRAG_PROVIDER='openai'")
    print("   - For Azure OpenAI: export GRAPHRAG_PROVIDER='azure_openai'")


def main():
    """Main setup function."""
    print("🔧 GraphRAG Examples Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check and install dependencies
    if not check_dependencies():
        print("\n❌ Failed to install required dependencies")
        sys.exit(1)
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    # Create sample configuration
    create_sample_config()
    
    # Show next steps
    show_next_steps()
    
    if not env_ok:
        provider = os.getenv("GRAPHRAG_PROVIDER", "openai").lower()
        if provider == "azure_openai":
            print("\n⚠️  Note: Set your Azure OpenAI environment variables before running examples!")
        else:
            print("\n⚠️  Note: Set your OPENAI_API_KEY before running examples!")


if __name__ == "__main__":
    main() 