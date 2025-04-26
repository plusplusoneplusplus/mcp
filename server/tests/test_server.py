import pytest
from pathlib import Path
import yaml
from server.main import starlette_app, tools_adapter, server

@pytest.fixture
def test_config():
    return {
        'server': {
            'host': 'localhost',
            'port': 5000,
            'debug': True,
            'allowed_commands': ['echo', 'pwd']
        },
        'vector_db': {
            'type': 'chroma',
            'persistence_directory': './test_data/vectordb',
            'collection_name': 'test_collection',
            'embedding_function': 'sentence-transformers/all-mpnet-base-v2'
        },
        'logging': {
            'level': 'DEBUG',
            'format': '{time} | {level} | {message}',
            'file': './test_logs/test.log'
        }
    }

@pytest.fixture
def server(test_config, tmp_path):
    # Create test config file
    config_path = tmp_path / "test_config.yaml"
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, 'w') as f:
        yaml.dump(test_config, f)
    
    return SentinelServer(str(config_path))

@pytest.mark.asyncio
async def test_handle_command_allowed(server):
    result = await server.handle_command("echo test")
    assert result["success"] is True
    assert "test" in result["output"]

@pytest.mark.asyncio
async def test_handle_command_not_allowed(server):
    result = await server.handle_command("ls")
    assert result["success"] is False
    assert "not in allowed commands list" in result["error"]

@pytest.mark.asyncio
async def test_handle_semantic_search(server):
    # First, we need to add some test data to the vector database
    server.vector_db.add(
        documents=["This is a test document"],
        ids=["test1"]
    )
    
    result = await server.handle_semantic_search("test document")
    assert result["success"] is True
    assert len(result["results"]) > 0

@pytest.mark.asyncio
async def test_list_tools():
    """Test that the server can list tools"""
    # The decorator in main.py is @server.list_tools(), so use that function name
    tools = await server.list_tools()
    assert len(tools) > 0
    # Verify at least one tool has required attributes
    tool = tools[0]
    assert hasattr(tool, 'name')
    assert hasattr(tool, 'description')
    assert hasattr(tool, 'inputSchema')

@pytest.mark.asyncio
async def test_tool_adapter():
    """Test that the tools adapter returns tools"""
    tools = tools_adapter.get_tools()
    assert len(tools) > 0
    # Basic check on the first tool
    assert hasattr(tools[0], 'name')
    assert hasattr(tools[0], 'description')
    assert hasattr(tools[0], 'inputSchema')

@pytest.mark.asyncio
async def test_starlette_app():
    """Test the Starlette app configuration"""
    # Check that the app has routes
    assert hasattr(starlette_app, 'routes')
    assert len(starlette_app.routes) > 0 