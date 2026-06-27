"""Regression: ``create_mission_core`` emits ``SpecifyStarted`` locally.

Issue #1067 requires the canonical lifecycle stream to record the
specify-phase entry point, not just its completion. Mission creation
already scaffolds an empty ``spec.md`` and opens the specify phase —
that is the canonical moment to emit ``SpecifyStarted``. Without it, a
fresh mission's ``status.events.jsonl`` skips straight from
``MissionCreated`` to ``SpecifyCompleted`` (emitted at setup-plan time),
leaving TeamSpace and the local dashboard blind to the in-progress
specify state.

This regression test was missing when #1067 was first closed; the
constant ``SPECIFY_STARTED`` was defined but never emitted. Reopening
fixed that gap and proved it stays fixed.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.core.mission_creation import create_mission_core


pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_CORE_MODULE = "specify_cli.core.mission_creation"


def _init_repo(repo: Path) -> None:
    (repo / ".kittify").mkdir(exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init", "--allow-empty"],
        cwd=repo,
        capture_output=True,
        check=True,
    )


def _mission_summary(slug: str) -> dict[str, str]:
    title = slug.replace("-", " ").title()
    return {
        "friendly_name": title,
        "purpose_tldr": f"Deliver {title} cleanly for the team.",
        "purpose_context": (
            f"This mission delivers {title} so product and engineering can move "
            "forward with a clear outcome and shared understanding."
        ),
    }


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def test_mission_create_appends_mission_created_and_specify_started(tmp_path: Path) -> None:
    """A fresh mission's canonical event log records both `MissionCreated` and `SpecifyStarted`."""
    _init_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch("specify_cli.status.fire_dossier_sync"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_mission_core(tmp_path, "lifecycle-stream-1067", **_mission_summary("lifecycle-stream-1067"))

    log = result.feature_dir / "status.events.jsonl"
    rows = _read_jsonl(log)
    event_types = [row.get("event_type") for row in rows]

    assert "MissionCreated" in event_types, f"MissionCreated missing from {log}: {event_types}"
    assert "SpecifyStarted" in event_types, (
        "SpecifyStarted must be emitted at mission-create time so the canonical "
        f"lifecycle is complete (#1067). Log contents: {event_types}"
    )
    # MissionCreated must precede SpecifyStarted on the canonical timeline.
    assert event_types.index("MissionCreated") < event_types.index("SpecifyStarted")


def test_mission_create_specify_started_payload_references_spec_md(tmp_path: Path) -> None:
    """The `SpecifyStarted` payload identifies the spec.md artifact."""
    _init_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch("specify_cli.status.fire_dossier_sync"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_mission_core(tmp_path, "lifecycle-stream-1067", **_mission_summary("lifecycle-stream-1067"))

    rows = _read_jsonl(result.feature_dir / "status.events.jsonl")
    specify = next(r for r in rows if r.get("event_type") == "SpecifyStarted")
    assert specify["payload"]["mission_slug"] == result.mission_slug
    artifact_path = specify["payload"].get("artifact_path") or ""
    assert artifact_path.endswith("spec.md"), specify


def test_mission_create_specify_started_is_idempotent(tmp_path: Path) -> None:
    """Re-running create_mission_core (e.g. ``--resume``) does not duplicate `SpecifyStarted`.

    ``emit_artifact_phase`` dedupes on ``(event_type, mission_slug, artifact_path)``.
    """
    _init_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch("specify_cli.status.fire_dossier_sync"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        first = create_mission_core(tmp_path, "lifecycle-stream-1067", **_mission_summary("lifecycle-stream-1067"))

        # Replay an emit at the same artifact_path; the dedupe key in
        # ``emit_artifact_phase`` should make this a no-op.
        from specify_cli.status.lifecycle_events import (
            SPECIFY_STARTED,
            emit_artifact_phase,
        )

        second = emit_artifact_phase(
            first.feature_dir,
            event_type=SPECIFY_STARTED,
            mission_slug=first.mission_slug,
            actor="spec-kitty mission create",
            artifact_path="spec.md",
        )

    rows = _read_jsonl(first.feature_dir / "status.events.jsonl")
    specify_events = [r for r in rows if r.get("event_type") == "SpecifyStarted"]
    assert len(specify_events) == 1, (
        f"SpecifyStarted must be idempotent on (mission_slug, artifact_path); "
        f"got {len(specify_events)} rows: {specify_events}"
    )
    assert second is None
