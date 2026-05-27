"""Unit tests for classify_wp_files() — event-log lane reading (T007 / FR-003).

Covers the event-log lane reading branches: no event log (else path), event log
present with known WP (try path), and TOCTOU race where get_wp_lane raises after
has_event_log returned True (except path).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.audit.classifiers.wp_files import classify_wp_files
from specify_cli.status.lane_reader import CanonicalStatusNotFoundError

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_VALID_ULID = "01KQHRB8GCFJAX7HM4ZY52AQGR"

_BASE_EVENT: dict[str, Any] = {
    "actor": "finalize-tasks",
    "at": "2026-05-01T12:00:00+00:00",
    "event_id": _VALID_ULID,
    "evidence": None,
    "execution_mode": "worktree",
    "force": False,
    "from_lane": "planned",
    "mission_id": _VALID_ULID,
    "mission_slug": "test-mission",
    "policy_metadata": None,
    "reason": None,
    "review_ref": None,
    "to_lane": "planned",
    "wp_id": "WP01",
}


def test_classify_wp_files_does_not_raise_without_event_log(tmp_path: Path) -> None:
    """classify_wp_files() must not raise for pre-3.0 / unfinalized missions.

    When no status.events.jsonl exists in the mission directory, the function
    must return a list (possibly empty, possibly with non-lane findings) without
    raising CanonicalStatusNotFoundError or any other exception.
    """
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()

    # WP file with frontmatter that includes lane — simulating a pre-3.0 mission
    wp_file = tasks_dir / "WP01-test-task.md"
    wp_file.write_text(
        "---\ntitle: Test\nwork_package_id: WP01\nlane: in_progress\n---\n\n# Body\n",
        encoding="utf-8",
    )
    # No status.events.jsonl created — simulates unfinalized / pre-3.0 mission

    # Must not raise CanonicalStatusNotFoundError or any other exception
    result = classify_wp_files(tmp_path)
    assert result is not None
    assert isinstance(result, list)


def test_classify_wp_files_does_not_raise_terminal_lane_without_event_log(
    tmp_path: Path,
) -> None:
    """classify_wp_files() must not raise even when frontmatter shows a terminal lane.

    For missions without an event log, the lane check is skipped entirely.
    No MISSING_EVIDENCE finding should be emitted via the frontmatter path.
    """
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()

    wp_file = tasks_dir / "WP01-done-task.md"
    wp_file.write_text(
        "---\ntitle: Done task\nwork_package_id: WP01\nlane: done\n---\n\n# Body\n",
        encoding="utf-8",
    )
    # No status.events.jsonl — terminal lane in frontmatter is ignored in Phase-2

    result = classify_wp_files(tmp_path)
    assert isinstance(result, list)
    # MISSING_EVIDENCE must NOT be emitted via frontmatter in Phase-2
    codes = [f.code for f in result]
    assert "MISSING_EVIDENCE" not in codes, (
        "classify_wp_files() must not emit MISSING_EVIDENCE from frontmatter lane "
        "when no event log is present (Phase-2 invariant)."
    )


def test_classify_wp_files_reads_lane_from_event_log(tmp_path: Path) -> None:
    """classify_wp_files() reads lane via get_wp_lane when event log exists (try branch).

    Covers the try: lane = str(get_wp_lane(...)) path. WP01 in non-terminal
    lane → no MISSING_EVIDENCE emitted.
    """
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\ndependencies: []\n---\n\n# Body\n",
        encoding="utf-8",
    )
    event_log = tmp_path / "status.events.jsonl"
    event_log.write_text(
        json.dumps({**_BASE_EVENT, "to_lane": "in_progress", "from_lane": "planned"}) + "\n",
        encoding="utf-8",
    )
    result = classify_wp_files(tmp_path)
    assert isinstance(result, list)
    assert "MISSING_EVIDENCE" not in [f.code for f in result]


def test_classify_wp_files_handles_get_wp_lane_race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """classify_wp_files() handles TOCTOU race where get_wp_lane raises after
    has_event_log returned True (except CanonicalStatusNotFoundError branch).
    """
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\ndependencies: []\n---\n\n# Body\n",
        encoding="utf-8",
    )
    # Minimal event log so has_event_log() returns True
    (tmp_path / "status.events.jsonl").write_text(
        json.dumps(_BASE_EVENT) + "\n", encoding="utf-8"
    )

    def _raise(*_args: object) -> None:
        raise CanonicalStatusNotFoundError("simulated race: file deleted")

    monkeypatch.setattr("specify_cli.audit.classifiers.wp_files.get_wp_lane", _raise)

    result = classify_wp_files(tmp_path)
    assert isinstance(result, list)
    assert "MISSING_EVIDENCE" not in [f.code for f in result]
