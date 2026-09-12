"""Regression tests for the dashboard charter presence/body split (FR-003, #3150).

C-001: ``charter.yaml`` is the deterministic, schema-guarded presence
authority and takes precedence for every presence decision; ``charter.md``
stays a readable secondary prose source and is never an override. This
module pins:

* the presence probe survives ``charter.md`` deletion -- the #3150 bug
  (NFR-001: the presence fixture seeds ONLY ``charter.yaml``), and
* the body path keeps reading ``charter.md`` when both files exist -- a
  distinct both-files no-regression case, never the presence proof.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.dashboard.charter_path import (
    resolve_project_charter_path,
    resolve_project_charter_presence,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)


def _seed_charter_yaml(project_dir: Path) -> Path:
    charter_dir = project_dir / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_yaml = charter_dir / "charter.yaml"
    charter_yaml.write_text("schema_version: '2.0.0'\n", encoding="utf-8")
    return charter_yaml


def _seed_charter_md(project_dir: Path, body: str) -> Path:
    charter_dir = project_dir / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_md = charter_dir / "charter.md"
    charter_md.write_text(body, encoding="utf-8")
    return charter_md


@pytest.fixture(autouse=True)
def _clear_resolver_cache():
    """Reset the canonical-root LRU cache so tmp_path fixtures stay isolated."""
    from charter.resolution import resolve_canonical_repo_root

    resolve_canonical_repo_root.cache_clear()
    yield
    resolve_canonical_repo_root.cache_clear()


def test_presence_probe_survives_charter_md_deletion(tmp_path: Path) -> None:
    """#3150: presence keys on charter.yaml and survives charter.md deletion.

    NFR-001: the presence fixture seeds ONLY charter.yaml -- charter.md is
    never created -- guarding against a fixture-seeds-both fake-green.
    """
    _init_git_repo(tmp_path)
    charter_yaml = _seed_charter_yaml(tmp_path)
    charter_md = tmp_path / ".kittify" / "charter" / "charter.md"
    assert not charter_md.exists(), "fixture must not create charter.md"

    presence = resolve_project_charter_presence(tmp_path)

    assert presence is not None, "presence probe must report present when charter.yaml exists"
    assert presence == charter_yaml


def test_presence_probe_reports_present_when_only_charter_md_exists(tmp_path: Path) -> None:
    """Landing-fold regression: charter.md-only (pre-compile) projects still

    report present. The #3150 fix made presence key solely on charter.yaml
    to survive charter.md deletion, but that silently regressed the far
    more common opposite case -- a project that has authored charter.md and
    has not yet run ``charter sync``/compile to produce charter.yaml. This
    mirrors the yaml-or-md presence gate in ``charter.activation.context`` (C-003) and
    the md-only fallback added to ``_status_collectors.py`` in the same PR.
    """
    _init_git_repo(tmp_path)
    charter_md = _seed_charter_md(tmp_path, body="# Authored Charter\n")
    charter_yaml = tmp_path / ".kittify" / "charter" / "charter.yaml"
    assert not charter_yaml.exists(), "fixture must not seed charter.yaml"

    presence = resolve_project_charter_presence(tmp_path)

    assert presence is not None, "presence probe must report present when only charter.md exists"
    assert presence == charter_md


def test_presence_probe_absent_when_neither_file_exists(tmp_path: Path) -> None:
    """Sanity companion: genuinely no charter -> presence probe reports absent."""
    _init_git_repo(tmp_path)

    assert resolve_project_charter_presence(tmp_path) is None


def test_body_path_still_reads_charter_md_when_both_files_present(tmp_path: Path) -> None:
    """Both-files no-regression pin (C-001), distinct from the presence proof.

    Presence still resolves via charter.yaml AND the served body still
    reads charter.md -- the prose reader is never retargeted to yaml.
    """
    _init_git_repo(tmp_path)
    _seed_charter_yaml(tmp_path)
    charter_md = _seed_charter_md(tmp_path, body="# Real Prose Body\n")

    presence = resolve_project_charter_presence(tmp_path)
    body_path = resolve_project_charter_path(tmp_path)

    assert presence is not None
    assert body_path is not None
    assert body_path == charter_md
    assert body_path.read_text(encoding="utf-8") == "# Real Prose Body\n"
