from setuptools import setup, find_packages

setup(
    name="mcp-tools",
    version="0.1.0",
    description="Tools for Multi-Cloud Processor",
    author="MCP Team",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
        "psutil>=5.9.0",
        "selenium>=4.0.0",
        "webdriver-manager>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "isort>=5.0.0",
        ],
    },
    python_requires=">=3.8",
) 