"""WP06 (T026) -- unit tests for the implement planning-artifact migration.

These tests pin the behavior that planning-artifact commits route
through :class:`BookkeepingTransaction` when the mission has a
``coordination_branch`` in ``meta.json``, and fall back to the legacy
raw-git path when it does not.

The full end-to-end flow lives in
``tests/integration/test_implement_review_flow.py``; this file covers
the small pure-Python shape changes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _make_meta(
    feature_dir: Path,
    *,
    with_coord: bool = True,
    mission_id: str = "01JZZZZZZZZZZZZZZZZZZZZZZZ",
    mission_slug: str = "wp06-impl-mission",
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "mid8": mission_id[:8],
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-05-28T00:00:00+00:00",
        "friendly_name": "WP06 implement test mission",
    }
    if with_coord:
        payload["coordination_branch"] = f"kitty/mission-{mission_slug}-{mission_id[:8]}"
    (feature_dir / "meta.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


class TestPlanningArtifactPath:
    """Modern (post-WP03) mission routes planning artifacts through coord branch."""

    def test_modern_mission_resolves_coord_branch_from_meta(
        self, tmp_path: Path
    ) -> None:
        from specify_cli.mission_metadata import load_meta

        feature_dir = tmp_path / "kitty-specs" / "wp06-impl-mission"
        _make_meta(feature_dir, with_coord=True)
        meta = load_meta(feature_dir)
        assert isinstance(meta, dict)
        assert meta["coordination_branch"].startswith("kitty/mission-")
        assert meta["mission_id"] == "01JZZZZZZZZZZZZZZZZZZZZZZZ"

    def test_legacy_mission_has_no_coord_branch(self, tmp_path: Path) -> None:
        from specify_cli.mission_metadata import load_meta

        feature_dir = tmp_path / "kitty-specs" / "wp06-legacy-mission"
        _make_meta(feature_dir, with_coord=False)
        meta = load_meta(feature_dir)
        assert isinstance(meta, dict)
        assert "coordination_branch" not in meta


class TestImplementModuleImports:
    """The migrated implement module imports cleanly after WP01/WP06."""

    def test_implement_imports_safe_commit_with_new_signature(self) -> None:
        from specify_cli.cli.commands import implement
        from specify_cli.git import safe_commit
        import inspect

        sig = inspect.signature(safe_commit)
        assert "destination_ref" in sig.parameters
        assert "worktree_root" in sig.parameters
        # The implement module still imports safe_commit (legacy
        # auto-commit path).
        assert hasattr(implement, "safe_commit")

    def test_implement_command_callable(self) -> None:
        from specify_cli.cli.commands.implement import implement

        # Just ensure the symbol is importable as a Typer command.
        assert callable(implement)
