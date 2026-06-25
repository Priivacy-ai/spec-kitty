"""WP04 / FR-004 (#2107): ``map-requirements`` must read WP ``tasks/*.md`` off PRIMARY.

The squad-found missed read site (research.md Decision 3): ``map_requirements``
resolved the WP ``tasks/*.md`` glob off the topology-routed ``feature_dir``
(``_map_requirements_feature_dir`` → coord). On a coord-topology mission the
materialised ``-coord`` husk holds an EMPTY ``tasks/`` while the real WP prompt
files live on PRIMARY (WORK_PACKAGE_TASK is a PRIMARY-partition kind). The command
then reported the operator's WP as unknown ("Unknown WP IDs") because it globbed an
empty coord ``tasks/``.

This is a **behavioral** red-first test driven through the REAL ``map-requirements``
CLI entry point with a composed ``<slug>-<mid8>`` fixture (NFR-002):

* PRE-FIX (``tasks_dir = feature_dir / "tasks"`` → coord): the WP is not found in
  the empty coord ``tasks/`` → exit 1, "Unknown WP IDs" — the RED.
* POST-FIX (``tasks_dir`` resolved via the kind-aware seam with
  ``kind=WORK_PACKAGE_TASK`` → primary): the WP file is found and the mapping is
  recorded → exit 0 — the GREEN.

Red-first evidence (run against pre-WP04 ``tasks.py``): the test fails with the
"Unknown WP IDs" error because the pre-fix glob ignores the seam-resolved primary
``tasks/`` and reads the empty coord ``tasks/``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.tasks import app as tasks_app

pytestmark = [pytest.mark.fast]


# Real 26-char ULID; uppercase mid8 disambiguator; composed ``<slug>-<mid8>`` dir
# name (NFR-002 — production-shaped identity, not a hand-crafted short slug).
MISSION_ID = "01KVW9B0Z6QH4F7K2M8R5T3D9C"
MID8 = MISSION_ID[:8]  # "01KVW9B0"
MISSION_SLUG = f"gate-read-surface-completion-{MID8}"

SPEC_MD_TEXT = "# Spec\n\n- **FR-001**: Do the thing.\n"
WP01_PROMPT = (
    "---\n"
    "work_package_id: WP01\n"
    "owned_files: []\n"
    "requirement_refs: []\n"
    "---\n"
    "# WP01\n"
)


def _write_primary(repo_root: Path) -> Path:
    """PRIMARY mission dir: spec.md + the real WP ``tasks/WP01-*.md`` prompt file."""
    primary_dir = repo_root / "kitty-specs" / MISSION_SLUG
    (primary_dir / "tasks").mkdir(parents=True)
    (primary_dir / "spec.md").write_text(SPEC_MD_TEXT, encoding="utf-8")
    (primary_dir / "tasks" / "WP01-do-the-thing.md").write_text(WP01_PROMPT, encoding="utf-8")
    return primary_dir


def _write_coord_empty_tasks(repo_root: Path) -> Path:
    """COORD husk: spec.md present but an EMPTY ``tasks/`` (the #2107 trap)."""
    coord_dir = repo_root / ".worktrees" / f"{MISSION_SLUG}-coord" / "kitty-specs" / MISSION_SLUG
    (coord_dir / "tasks").mkdir(parents=True)
    (coord_dir / "spec.md").write_text(SPEC_MD_TEXT, encoding="utf-8")
    return coord_dir


def _patch_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    repo_root: Path,
    coord_dir: Path,
    primary_dir: Path,
) -> None:
    """Patch the resolution boundaries so the real CLI runs against fixture dirs.

    The coord-aware ``feature_dir`` is forced to the coord husk (the buggy input).
    The PRIMARY anchor (spec.md read) and the kind-aware seam (the read under test)
    both resolve to the primary dir — so the ONLY way the WP files are found is when
    the production code routes the ``tasks/*.md`` read through the seam, not off the
    coord ``feature_dir``.
    """
    mod = "specify_cli.cli.commands.agent.tasks"
    monkeypatch.setattr(f"{mod}.locate_project_root", lambda: repo_root)
    monkeypatch.setattr(f"{mod}._emit_sparse_session_warning", lambda *a, **k: None)
    monkeypatch.setattr(
        f"{mod}._find_mission_slug",
        lambda *a, **k: MISSION_SLUG,
    )
    monkeypatch.setattr(
        f"{mod}._ensure_target_branch_checked_out",
        lambda *a, **k: (repo_root, "feat/gate-read-surface-completion"),
    )
    monkeypatch.setattr(f"{mod}.get_auto_commit_default", lambda *a, **k: False)
    # Coord-aware ``feature_dir`` → coord husk (empty ``tasks/``).
    monkeypatch.setattr(
        f"{mod}._map_requirements_feature_dir",
        lambda *a, **k: coord_dir,
    )
    # PRIMARY anchor used for the spec.md read (unchanged) → primary dir.
    monkeypatch.setattr(
        "specify_cli.missions._read_path_resolver.primary_feature_dir_for_mission",
        lambda *a, **k: primary_dir,
    )
    # The kind-aware seam (the read surface under test). POST-FIX the production
    # code calls this for ``kind=WORK_PACKAGE_TASK``; force it to the primary dir.
    monkeypatch.setattr(
        f"{mod}.resolve_planning_read_dir",
        lambda *a, **k: primary_dir,
    )


def test_map_requirements_reads_wp_tasks_off_primary_under_coord_topology(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The WP ``tasks/*.md`` read resolves PRIMARY, not the empty coord ``tasks/``.

    RED on pre-WP04 ``tasks.py`` (globs the empty coord ``tasks/`` → "Unknown WP
    IDs"); GREEN once the read routes through the ``kind=WORK_PACKAGE_TASK`` seam.
    """
    repo_root = tmp_path
    primary_dir = _write_primary(repo_root)
    coord_dir = _write_coord_empty_tasks(repo_root)
    _patch_boundaries(monkeypatch, repo_root, coord_dir, primary_dir)

    result = CliRunner().invoke(
        tasks_app,
        [
            "map-requirements",
            "--mission",
            MISSION_SLUG,
            "--wp",
            "WP01",
            "--refs",
            "FR-001",
            "--json",
            "--no-auto-commit",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"] == "success"
    assert payload["mapped"] == {"WP01": ["FR-001"]}
    # The mapping was persisted onto the PRIMARY WP prompt file, never the coord husk.
    wp_text = (primary_dir / "tasks" / "WP01-do-the-thing.md").read_text(encoding="utf-8")
    assert "FR-001" in wp_text
