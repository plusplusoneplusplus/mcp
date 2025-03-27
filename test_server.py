import pytest
from pathlib import Path
import yaml
from src.main import SentinelServer

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