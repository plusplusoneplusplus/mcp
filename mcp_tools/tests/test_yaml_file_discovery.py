import os
import yaml
from pathlib import Path
from mcp_tools.yaml_tools import YamlToolBase
from mcp_tools.plugin_config import config


def _write_yaml(path: Path, data: dict):
    path.write_text(yaml.safe_dump(data))


def test_get_yaml_tool_paths_env_order(monkeypatch, tmp_path):
    priv = tmp_path / "private"
    priv.mkdir()
    a = tmp_path / "a"
    a.mkdir()
    b = tmp_path / "b"
    b.mkdir()

    monkeypatch.setenv("PRIVATE_TOOL_ROOT", str(priv))
    monkeypatch.setenv("MCP_YAML_TOOL_PATHS", f"{a},{b}")

    paths = config.get_yaml_tool_paths()

    assert paths[0] == priv
    assert paths[1:] == [a, b]


def test_get_yaml_tool_paths_defaults(monkeypatch):
    monkeypatch.delenv("PRIVATE_TOOL_ROOT", raising=False)
    monkeypatch.delenv("MCP_YAML_TOOL_PATHS", raising=False)

    server_dir = Path(__file__).resolve().parent.parent.parent / "server"
    expected = [server_dir / ".private", server_dir, Path.cwd()]

    paths = config.get_yaml_tool_paths()

    assert paths == expected


def test_load_yaml_from_locations_priority(monkeypatch, tmp_path):
    p1 = tmp_path / "p1"
    p2 = tmp_path / "p2"
    p1.mkdir()
    p2.mkdir()
    _write_yaml(p1 / "tools.yaml", {"tools": {"t": {"description": "p1"}}})
    _write_yaml(p2 / "tools.yaml", {"tools": {"t": {"description": "p2"}}})

    tool = YamlToolBase()
    monkeypatch.setattr(config, "get_yaml_tool_paths", lambda: [p2, p1])

    data = tool._load_yaml_from_locations("tools.yaml")
    assert data["tools"]["t"]["description"] == "p2"


def test_load_yaml_from_locations_env(monkeypatch, tmp_path):
    priv = tmp_path / "private"
    priv.mkdir()
    _write_yaml(priv / "tools.yaml", {"tools": {"t": {"description": "env"}}})

    monkeypatch.setenv("PRIVATE_TOOL_ROOT", str(priv))
    monkeypatch.delenv("MCP_YAML_TOOL_PATHS", raising=False)

    tool = YamlToolBase()
    data = tool._load_yaml_from_locations("tools.yaml")
    assert data["tools"]["t"]["description"] == "env"


def test_load_yaml_from_locations_missing(monkeypatch, tmp_path, caplog):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(config, "get_yaml_tool_paths", lambda: [empty])

    tool = YamlToolBase()
    caplog.set_level("WARNING")
    data = tool._load_yaml_from_locations("tools.yaml")
    assert data == {}
    assert any("Could not find" in r.message for r in caplog.records)
