"""Unit tests for classify_wp_files() — no-event-log contract (T007 / FR-003).

Verifies that classify_wp_files() does not raise when no status.events.jsonl
exists (pre-3.0 / unfinalized missions). This is the "never raises" contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.audit.classifiers.wp_files import classify_wp_files

pytestmark = [pytest.mark.unit, pytest.mark.fast]


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
