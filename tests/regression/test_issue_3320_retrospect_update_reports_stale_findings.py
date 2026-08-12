"""Red-first reproduction of #3320 — ``retrospect create --update`` reports a
result and appends an event that contradict the record it actually persisted.

Open P0: https://github.com/Priivacy-ai/spec-kitty/issues/3320

Root cause (verified against current source): in
``src/specify_cli/cli/commands/retrospect.py`` the ``create`` command builds its
JSON result (and the ``RetrospectiveCaptured`` event) from the PRE-MERGE
``record`` (the freshly generated ``ran_no_findings`` record), while
``write_gen_record(mode="update")`` (``src/specify_cli/retrospective/writer.py``)
MERGES that with the existing on-disk record and recomputes ``findings_status``
from the union — preserving the existing gap, so the persisted record stays
``has_findings``. The CLI never reads back the merged record, so ``--update``
reports ``ran_no_findings`` / zero gaps while the file on disk still says
``has_findings`` with its gap intact.

This drives the REAL ``retrospect create --update`` command through the REAL
merging writer (``write_gen_record`` is NOT mocked); only the mission-resolution
and generation collaborators are stubbed, and the generator is stubbed to a real
``ran_no_findings`` record exactly as the empty-mission generator would produce.

Desired post-fix outcome: ``--update`` reports from the merged record (or migrates
and rewrites so result/event agree with the record), or fails before mutating
anything — the reported ``findings_status`` / gap count must match what is
actually persisted.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from specify_cli.cli.commands.retrospect import app as retrospect_app
from specify_cli.retrospective.schema import GenFinding, GenRetrospectiveRecord
from specify_cli.retrospective.writer import write_gen_record

from tests.cli.commands.test_retrospect import (
    MISSION_ID_COMPLETED,
    MISSION_SLUG_COMPLETED,
    _build_resolved_mission,
    _make_minimal_gen_record,
    _setup_project,
    _write_kitty_meta,
    _write_status_events_all_done,
)

pytestmark = pytest.mark.regression

RUNNER = CliRunner()

_RETRO_MODULE = "specify_cli.cli.commands.retrospect"


def _legacy_record_with_gap() -> GenRetrospectiveRecord:
    """A completed mission's existing record: has_findings with one real gap."""
    base = _make_minimal_gen_record(findings_status="has_findings")
    base.gaps = [
        GenFinding(
            id="g-001",
            category="process",
            summary="lane bounced before approval",
        )
    ]
    return base


def test_update_result_and_event_agree_with_persisted_record(tmp_path: Path) -> None:
    repo_root, _missions_dir, kitty_specs_dir = _setup_project(tmp_path)
    feature_dir = kitty_specs_dir / MISSION_SLUG_COMPLETED
    _write_kitty_meta(feature_dir, MISSION_ID_COMPLETED, MISSION_SLUG_COMPLETED)
    _write_status_events_all_done(feature_dir, MISSION_SLUG_COMPLETED)

    # Seed the existing on-disk record (has_findings + one gap) via the real writer.
    record_path = write_gen_record(
        _legacy_record_with_gap(), mode="overwrite", repo_root=repo_root
    )
    assert record_path.exists(), "sanity: existing record seeded on disk"

    # The generator, on this artifact-poor mission, yields ran_no_findings — the
    # exact input that the CLI then reports from instead of the merged result.
    generated = _make_minimal_gen_record(findings_status="ran_no_findings")
    resolved = _build_resolved_mission(
        MISSION_ID_COMPLETED, MISSION_SLUG_COMPLETED, feature_dir
    )

    with (
        patch(f"{_RETRO_MODULE}.locate_project_root", return_value=repo_root),
        patch(f"{_RETRO_MODULE}._resolve_handle", return_value=resolved),
        patch(f"{_RETRO_MODULE}._check_mission_completed", return_value=[]),
        patch(f"{_RETRO_MODULE}.resolve_policy", return_value=(MagicMock(), {})),
        patch(f"{_RETRO_MODULE}.generate_retrospective", return_value=generated),
        patch(f"{_RETRO_MODULE}.emit_captured", return_value=None),
        patch(f"{_RETRO_MODULE}._maybe_auto_commit"),
    ):
        # NOTE: write_gen_record is intentionally NOT mocked — the real merge runs.
        result = RUNNER.invoke(
            retrospect_app,
            ["create", "--mission", MISSION_SLUG_COMPLETED, "--update", "--json"],
        )

    assert result.exit_code == 0, result.output
    reported = json.loads(result.output)

    persisted = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    on_disk_status = persisted["findings_status"]
    on_disk_gap_count = len(persisted.get("gaps", []))

    # Sanity: the merge preserved the existing gap on disk.
    assert on_disk_status == "has_findings"
    assert on_disk_gap_count == 1

    # RED today: the reported result contradicts the persisted record — the CLI
    # reports the pre-merge ran_no_findings/zero-gaps while disk is has_findings.
    assert reported["findings_status"] == on_disk_status, (
        "reported findings_status must match the persisted record; "
        f"reported={reported['findings_status']!r} on_disk={on_disk_status!r}"
    )
    assert reported.get("counts", {}).get("gaps") == on_disk_gap_count, (
        "reported gap count must match the persisted record; "
        f"reported={reported.get('counts', {}).get('gaps')} on_disk={on_disk_gap_count}"
    )
