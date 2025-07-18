import logging
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any

import yaml

from mcp_tools.plugin_config import config

logger = logging.getLogger(__name__)

# Path to plugin configuration YAML
REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_CONFIG_PATH = REPO_ROOT / "plugin_config.yaml"

# Directory where external plugins are installed
EXTERNAL_PLUGINS_ROOT = REPO_ROOT / "plugins_external"

# Directory containing built in plugins
BUILTIN_PLUGINS_ROOT = REPO_ROOT / "plugins"


def load_plugin_config() -> List[Dict[str, Any]]:
    """Load plugin configuration from YAML."""
    if not PLUGIN_CONFIG_PATH.exists():
        logger.info("Plugin config not found, skipping load")
        return []

    with open(PLUGIN_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("plugins", [])


def _clone_or_update(repo: str, dest: Path) -> None:
    """Clone repo if dest does not exist, otherwise update with git pull."""
    url = f"https://github.com/{repo}.git"
    if dest.exists():
        try:
            subprocess.run([
                "git",
                "-C",
                str(dest),
                "pull",
                "--ff-only",
            ], check=True)
            return
        except Exception as e:
            logger.warning(f"Failed to update {repo}: {e}, recloning")
            shutil.rmtree(dest)
    subprocess.run(["git", "clone", url, str(dest)], check=True)


def refresh_plugins(force_clean: bool = False) -> List[Path]:
    """Refresh plugins based on plugin config.

    Args:
        force_clean: If True, remove all external plugins before reinstalling.

    Returns:
        List of plugin root paths after refresh.
    """
    plugins = load_plugin_config()

    if force_clean and EXTERNAL_PLUGINS_ROOT.exists():
        shutil.rmtree(EXTERNAL_PLUGINS_ROOT)
    EXTERNAL_PLUGINS_ROOT.mkdir(parents=True, exist_ok=True)

    desired_repos = {}
    plugin_roots = [BUILTIN_PLUGINS_ROOT]

    for entry in plugins:
        repo = entry.get("plugin_repo")
        if not repo:
            continue
        repo_name = repo.split("/")[-1]
        dest_dir = EXTERNAL_PLUGINS_ROOT / repo_name
        _clone_or_update(repo, dest_dir)
        sub_dir = entry.get("sub_dir")
        plugin_root = dest_dir / sub_dir if sub_dir else dest_dir
        plugin_roots.append(plugin_root)
        desired_repos[repo_name] = dest_dir

    # Remove extraneous plugin directories
    for item in EXTERNAL_PLUGINS_ROOT.iterdir():
        if item.is_dir() and item.name not in desired_repos:
            shutil.rmtree(item)

    # Update plugin roots in configuration
    config.plugin_roots = plugin_roots
    return plugin_roots
