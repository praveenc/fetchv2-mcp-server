"""Release metadata consistency tests."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
SERVER_NAME = "io.github.praveenc/fetchv2-mcp-server"


def test_release_metadata_is_consistent():
    """Package and Registry metadata must identify the same release."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    server = json.loads((ROOT / "server.json").read_text())
    package = server["packages"][0]
    readme = (ROOT / "README.md").read_text()

    assert server["name"] == SERVER_NAME
    assert f"mcp-name: {SERVER_NAME}" in readme
    assert package["registryType"] == "pypi"
    assert package["identifier"] == project["project"]["name"]
    assert package["transport"] == {"type": "stdio"}
    assert package["version"] == server["version"] == project["project"]["version"]
