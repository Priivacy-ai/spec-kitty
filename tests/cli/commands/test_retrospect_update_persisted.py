"""Guard: ``retrospect create --update`` reports/emits the PERSISTED record.

Fixed defect: #3320 — ``retrospect create --update`` used to report a result
and append a ``RetrospectiveCaptured`` event built from the PRE-MERGE
``record`` (the freshly generated ``ran_no_findings`` record), while
``write_gen_record(mode="update")`` (``src/specify_cli/retrospective/writer.py``)
MERGES that with the existing on-disk record and recomputes ``findings_status``
from the union — preserving any existing gap, so the persisted record stayed
``has_findings``. The CLI never read back the merged record, so ``--update``
reported ``ran_no_findings`` / zero gaps while the file on disk still said
``has_findings`` with its gap intact, and the emitted event carried the same
stale data.

Fix: ``create_cmd`` (``src/specify_cli/cli/commands/retrospect.py``) now reads
back the persisted record via ``read_gen_record(record_path)`` after
``write_gen_record`` succeeds, and builds the reported ``counts``/
``findings_status`` JSON *and* the ``emit_captured(...)`` argument from that
read-back record — never from the pre-merge ``record``.

This module pins **report ≡ event ≡ disk**: the JSON result, the record passed
to ``emit_captured``, and the actual on-disk YAML must all agree, for both the
merging ``--update`` path and the non-merging paths (read-back is a no-op
there since persisted == new).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import Result
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

pytestmark = [pytest.mark.unit, pytest.mark.fast]

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


def _seed_and_invoke_update(
    tmp_path: Path, *, emit_captured_replacement: MagicMock
) -> tuple[Path, Result]:
    """Seed an on-disk has_findings+1-gap record, then invoke `create --update`.

    Runs the REAL ``write_gen_record`` merge (not mocked); only mission
    resolution and generation collaborators are stubbed. The generator is
    stubbed to a real ``ran_no_findings`` record, exactly what the empty-
    mission generator would produce — the merge input that used to leak into
    the report/event before the #3320 fix.

    Returns (record_path, CliRunner result).
    """
    repo_root, _missions_dir, kitty_specs_dir = _setup_project(tmp_path)
    feature_dir = kitty_specs_dir / MISSION_SLUG_COMPLETED
    _write_kitty_meta(feature_dir, MISSION_ID_COMPLETED, MISSION_SLUG_COMPLETED)
    _write_status_events_all_done(feature_dir, MISSION_SLUG_COMPLETED)

    record_path = write_gen_record(
        _legacy_record_with_gap(), mode="overwrite", repo_root=repo_root
    )
    assert record_path.exists(), "sanity: existing record seeded on disk"

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
        patch(f"{_RETRO_MODULE}.emit_captured", emit_captured_replacement),
        patch(f"{_RETRO_MODULE}._maybe_auto_commit"),
    ):
        # NOTE: write_gen_record is intentionally NOT mocked — the real merge runs.
        result = RUNNER.invoke(
            retrospect_app,
            ["create", "--mission", MISSION_SLUG_COMPLETED, "--update", "--json"],
        )
    return record_path, result


def test_update_result_and_event_agree_with_persisted_record(tmp_path: Path) -> None:
    """report JSON must match the merged record actually written to disk.

    Pins the fix: reported findings_status/gap-count == on-disk values, not
    the pre-merge ran_no_findings/zero-gaps that the generator produced.
    """
    record_path, result = _seed_and_invoke_update(
        tmp_path, emit_captured_replacement=MagicMock(return_value=None)
    )

    assert result.exit_code == 0, result.output
    reported = json.loads(result.output)

    persisted = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    on_disk_status = persisted["findings_status"]
    on_disk_gap_count = len(persisted.get("gaps", []))

    # Sanity: the merge preserved the existing gap on disk.
    assert on_disk_status == "has_findings"
    assert on_disk_gap_count == 1

    assert reported["findings_status"] == on_disk_status, (
        "reported findings_status must match the persisted record; "
        f"reported={reported['findings_status']!r} on_disk={on_disk_status!r}"
    )
    assert reported.get("counts", {}).get("gaps") == on_disk_gap_count, (
        "reported gap count must match the persisted record; "
        f"reported={reported.get('counts', {}).get('gaps')} on_disk={on_disk_gap_count}"
    )


def test_emit_captured_spy_matches_persisted_record_on_disk(tmp_path: Path) -> None:
    """emit_captured must receive the PERSISTED record, not the pre-merge one.

    Non-fakeable guard (T002): a spy captures the exact record object passed
    to ``emit_captured`` (not the reported JSON — both could be
    wrong-and-equal). Its ``findings_status``/gap-count are asserted directly
    against the on-disk YAML at ``record_path``, independent of what the CLI
    reports.
    """
    spy = MagicMock(return_value=None)
    record_path, result = _seed_and_invoke_update(
        tmp_path, emit_captured_replacement=spy
    )

    assert result.exit_code == 0, result.output
    reported = json.loads(result.output)

    on_disk = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    on_disk_status = on_disk["findings_status"]
    on_disk_gap_count = len(on_disk.get("gaps", []))
    assert on_disk_status == "has_findings"
    assert on_disk_gap_count == 1

    # The spy must have been invoked exactly once, with the persisted record
    # as its first positional argument.
    spy.assert_called_once()
    emitted_record = spy.call_args.args[0]
    assert isinstance(emitted_record, GenRetrospectiveRecord)

    assert emitted_record.findings_status == on_disk_status, (
        "emit_captured must receive the persisted (merged) findings_status; "
        f"emitted={emitted_record.findings_status!r} on_disk={on_disk_status!r}"
    )
    assert len(emitted_record.gaps) == on_disk_gap_count, (
        "emit_captured must receive the persisted (merged) gap list; "
        f"emitted={len(emitted_record.gaps)} on_disk={on_disk_gap_count}"
    )

    # Also assert the reported JSON matches disk (report == event == disk).
    assert reported["findings_status"] == on_disk_status
    assert reported.get("counts", {}).get("gaps") == on_disk_gap_count
