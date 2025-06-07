import logging
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from mcp_tools.yaml_tools import YamlToolBase, load_yaml_tools
from mcp_tools.plugin_config import config

FIXTURES = Path(__file__).parent / "fixtures"


def read_yaml(name: str):
    path = FIXTURES / name
    text = path.read_text()
    return yaml.safe_load(text) if text else {}


def test_load_yaml_from_locations_valid(tmp_path):
    tool = YamlToolBase()
    with patch.object(config, "get_yaml_tool_paths", return_value=[FIXTURES]):
        data = tool._load_yaml_from_locations("valid_tools.yaml")
    assert "tools" in data
    assert data["tools"]["echo"]["description"] == "Echo a message"


def test_load_yaml_from_locations_malformed(caplog):
    tool = YamlToolBase()
    with patch.object(config, "get_yaml_tool_paths", return_value=[FIXTURES]):
        caplog.set_level(logging.ERROR)
        data = tool._load_yaml_from_locations("malformed.yaml")
    assert data == {}
    assert any("YAML parsing error" in r.message for r in caplog.records)


def test_load_yaml_from_locations_empty():
    tool = YamlToolBase()
    with patch.object(config, "get_yaml_tool_paths", return_value=[FIXTURES]):
        data = tool._load_yaml_from_locations("empty.yaml")
    assert data == {}


def test_load_yaml_from_locations_missing_section():
    tool = YamlToolBase()
    with patch.object(config, "get_yaml_tool_paths", return_value=[FIXTURES]):
        data = tool._load_yaml_from_locations("no_tools_section.yaml")
    assert "tools" not in data


def test_load_yaml_from_locations_invalid_types():
    tool = YamlToolBase()
    with patch.object(config, "get_yaml_tool_paths", return_value=[FIXTURES]):
        data = tool._load_yaml_from_locations("invalid_types.yaml")
    assert data["tools"]["bad_tool_1"]["description"] == 123


@pytest.fixture
def patch_register_tool():
    with patch("mcp_tools.yaml_tools.register_tool", lambda **kw: (lambda cls: cls)):
        yield


def test_load_yaml_tools_valid(monkeypatch, patch_register_tool):
    yaml_data = read_yaml("valid_tools.yaml")
    monkeypatch.setattr(config, "register_yaml_tools", True)
    with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
        classes = load_yaml_tools()
    assert len(classes) == len(yaml_data["tools"])
    for cls in classes:
        inst = cls()
        assert isinstance(inst, YamlToolBase)


@pytest.mark.parametrize(
    "fname,expected",
    [
        ("missing_fields.yaml", 0),
        ("invalid_types.yaml", 1),
    ],
)
def test_load_yaml_tools_invalid(fname, expected, monkeypatch, patch_register_tool, caplog):
    yaml_data = read_yaml(fname)
    monkeypatch.setattr(config, "register_yaml_tools", True)
    with patch.object(
        YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data
    ):
        caplog.set_level(logging.ERROR)
        classes = load_yaml_tools()
    assert len(classes) == expected
    if expected == 0:
        assert any("validation" in r.message.lower() for r in caplog.records)


def test_load_yaml_tools_no_tools(monkeypatch, patch_register_tool):
    yaml_data = read_yaml("no_tools_section.yaml")
    monkeypatch.setattr(config, "register_yaml_tools", True)
    with patch.object(YamlToolBase, "_load_yaml_from_locations", return_value=yaml_data):
        classes = load_yaml_tools()
    assert classes == []

