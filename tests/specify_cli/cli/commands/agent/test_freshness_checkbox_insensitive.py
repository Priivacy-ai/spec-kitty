"""WP06 T029 (FR-009) — regression guard: checkbox flips never invalidate an
analysis report; substantive tasks.md edits still do.

``analysis_report._normalize_tasks_md`` already strips ``[ ]``/``[x]`` markers
via ``_CHECKBOX_RE`` before hashing ``tasks.md`` (#1764) — this module adds NO
new normalization logic. It pins the existing behavior on BOTH consumer paths
that route through ``collect_input_artifact_hashes``:

* ``write_analysis_report`` (the write path) — persisting a report twice with
  only a checkbox flip between writes must record the SAME ``tasks.md`` hash.
* ``check_analysis_report_current`` (the implement-gate check path) — flipping
  a checkbox after a report is recorded must NOT report the report as stale.

A negative control (a substantive tasks.md edit — not just a checkbox flip)
proves the hashing mechanism is not simply inert: it DOES change the hash and
DOES flip the gate to stale.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.analysis_report import (
    check_analysis_report_current,
    collect_input_artifact_hashes,
    write_analysis_report,
)
from specify_cli.frontmatter import FrontmatterManager

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_TASKS_MD_UNCHECKED = """\
# Tasks

## WP01 — Build widget

- [ ] T001 Design the API (WP01)
- [ ] T002 Implement the handler (WP01)
"""

_TASKS_MD_ONE_CHECKED = """\
# Tasks

## WP01 — Build widget

- [x] T001 Design the API (WP01)
- [ ] T002 Implement the handler (WP01)
"""

_TASKS_MD_SUBSTANTIVE_CHANGE = """\
# Tasks

## WP01 — Build widget

- [x] T001 Design the API DIFFERENTLY (WP01)
- [ ] T002 Implement the handler (WP01)
- [ ] T003 A brand new subtask (WP01)
"""


def _write_required_artifacts(feature_dir: Path, tasks_md_text: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Spec\n\nFR-001.\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(tasks_md_text, encoding="utf-8")


def _tasks_md_hash(feature_dir: Path, repo_root: Path) -> str | None:
    return collect_input_artifact_hashes(feature_dir, repo_root)["tasks.md"]["sha256"]


class TestWritePathCheckboxInsensitivity:
    """``write_analysis_report`` records the same ``tasks.md`` hash across a
    checkbox-only flip (FR-009 write-path leg)."""

    def test_checkbox_flip_does_not_change_recorded_hash(self, tmp_path: Path) -> None:
        repo_root = tmp_path
        feature_dir = repo_root / "kitty-specs" / "sample-01KWCX"

        _write_required_artifacts(feature_dir, _TASKS_MD_UNCHECKED)
        baseline = write_analysis_report(
            feature_dir=feature_dir, repo_root=repo_root, body="# Report\n\nPASS\n"
        )
        baseline_hash = baseline.input_artifacts["tasks.md"]["sha256"]
        assert baseline_hash is not None

        # Simulate a dashboard progress tick: [ ] -> [x], no other edit.
        (feature_dir / "tasks.md").write_text(_TASKS_MD_ONE_CHECKED, encoding="utf-8")
        flipped = write_analysis_report(
            feature_dir=feature_dir, repo_root=repo_root, body="# Report\n\nPASS\n"
        )
        flipped_hash = flipped.input_artifacts["tasks.md"]["sha256"]

        assert flipped_hash == baseline_hash

    def test_substantive_edit_changes_recorded_hash(self, tmp_path: Path) -> None:
        """Negative control: a real content edit (not just a checkbox) DOES
        change the write-path hash — proving the mechanism is not inert."""
        repo_root = tmp_path
        feature_dir = repo_root / "kitty-specs" / "sample-01KWCY"

        _write_required_artifacts(feature_dir, _TASKS_MD_UNCHECKED)
        baseline = write_analysis_report(
            feature_dir=feature_dir, repo_root=repo_root, body="# Report\n\nPASS\n"
        )
        baseline_hash = baseline.input_artifacts["tasks.md"]["sha256"]

        (feature_dir / "tasks.md").write_text(
            _TASKS_MD_SUBSTANTIVE_CHANGE, encoding="utf-8"
        )
        changed = write_analysis_report(
            feature_dir=feature_dir, repo_root=repo_root, body="# Report\n\nPASS\n"
        )
        changed_hash = changed.input_artifacts["tasks.md"]["sha256"]

        assert changed_hash != baseline_hash


class TestGateCheckPathCheckboxInsensitivity:
    """``check_analysis_report_current`` never goes stale on a checkbox-only
    flip (FR-009 implement-gate-check-path leg), but DOES on a substantive
    edit (negative control)."""

    def test_checkbox_flip_after_recording_stays_current(self, tmp_path: Path) -> None:
        repo_root = tmp_path
        feature_dir = repo_root / "kitty-specs" / "sample-01KWCZ"

        _write_required_artifacts(feature_dir, _TASKS_MD_UNCHECKED)
        write_analysis_report(
            feature_dir=feature_dir, repo_root=repo_root, body="# Report\n\nPASS\n"
        )
        assert check_analysis_report_current(feature_dir, repo_root).ok is True

        # A tick on the dashboard (mark-status / move-task) flips a checkbox.
        (feature_dir / "tasks.md").write_text(_TASKS_MD_ONE_CHECKED, encoding="utf-8")

        freshness = check_analysis_report_current(feature_dir, repo_root)
        assert freshness.ok is True
        assert "tasks.md" not in freshness.mismatches

    def test_substantive_edit_after_recording_goes_stale(self, tmp_path: Path) -> None:
        """Negative control: a substantive tasks.md edit DOES flip the gate to
        stale — proving the checkbox-insensitivity isn't masking a broken
        hashing mechanism entirely."""
        repo_root = tmp_path
        feature_dir = repo_root / "kitty-specs" / "sample-01KWD0"

        _write_required_artifacts(feature_dir, _TASKS_MD_UNCHECKED)
        write_analysis_report(
            feature_dir=feature_dir, repo_root=repo_root, body="# Report\n\nPASS\n"
        )
        assert check_analysis_report_current(feature_dir, repo_root).ok is True

        (feature_dir / "tasks.md").write_text(
            _TASKS_MD_SUBSTANTIVE_CHANGE, encoding="utf-8"
        )

        freshness = check_analysis_report_current(feature_dir, repo_root)
        assert freshness.ok is False
        assert freshness.reason == "stale_analysis_report"
        assert "tasks.md" in freshness.mismatches


def test_persisted_report_frontmatter_hash_matches_direct_collector(
    tmp_path: Path,
) -> None:
    """Sanity cross-check: the hash ``write_analysis_report`` persists into the
    report frontmatter is exactly what ``collect_input_artifact_hashes`` (the
    shared entry point both paths route through) computes directly — proving
    there is one hashing seam, not two independently-drifting ones."""
    repo_root = tmp_path
    feature_dir = repo_root / "kitty-specs" / "sample-01KWD1"
    _write_required_artifacts(feature_dir, _TASKS_MD_ONE_CHECKED)

    result = write_analysis_report(
        feature_dir=feature_dir, repo_root=repo_root, body="# Report\n\nPASS\n"
    )

    frontmatter, _body = FrontmatterManager().read(
        feature_dir / "analysis-report.md"
    )
    persisted_hash = frontmatter["input_artifacts"]["tasks.md"]["sha256"]
    direct_hash = _tasks_md_hash(feature_dir, repo_root)

    assert persisted_hash == direct_hash == result.input_artifacts["tasks.md"]["sha256"]
