"""Release metadata checks."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def test_project_and_manifest_versions_match() -> None:
    """Keep HACS and Python release metadata on the same version."""
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    manifest = json.loads(
        (REPO_ROOT / "custom_components/perific/manifest.json").read_text()
    )

    project_version = project["project"]["version"]
    manifest_version = manifest["version"]

    assert project_version == manifest_version
    assert SEMVER_RE.fullmatch(project_version) is not None
