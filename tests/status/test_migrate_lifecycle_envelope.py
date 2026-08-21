"""F2-T1: migration of legacy lifecycle envelopes to F1's strict shape.

Test IDs map to F2.md section 4: MIG1-5, COMPAT2, COMPAT6 (stub validator --
``spec_kitty_events.strict`` does not exist yet at the pinned events package
version 6.1.0; F2.md section 4's COMPAT6 row explicitly allows "a pinned
stub of the same 14-key/presence rule if sequencing requires this test to
exist before F1-T1 merges"). The stub lives ONLY in this test file, never in
production code -- STRICT_ENVELOPE_KEYS is F1's authority
(ARCHITECTURE.md section 0, single canonical authority), not something
F2-T1 invents production-side.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _git_init(path: Path) -> None:
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(path)],
        check=True,
        capture_output=True,
    )


from specify_cli.status.lifecycle_events import (
    emit_wp_created_local,
    mission_event_log_path,
    project_event_log_path,
    read_lifecycle_events,
)
from specify_cli.status.doctor import check_reviewer_self_approval
from specify_cli.status.emit import emit_status_transition
import specify_cli.status.migrate_lifecycle_envelope as migrate_lifecycle_envelope_module
from specify_cli.status.migrate_lifecycle_envelope import migrate_lifecycle_envelope
from specify_cli.status.models import TransitionRequest
from specify_cli.status.reducer import materialize_snapshot, materialize_to_json
from specify_cli.status.store import StoreError

from tests.status.conftest import seed_wp_to_planned as _seed_planned

_MISSION_SLUG = "migrate-lifecycle-envelope"

# ---------------------------------------------------------------------------
# COMPAT6 stub -- pinned local approximation of F1's strict.py, test-only.
# ---------------------------------------------------------------------------

_STUB_STRICT_ENVELOPE_KEYS = frozenset({
    "event_id", "event_type", "aggregate_id", "payload", "timestamp",
    "build_id", "node_id", "lamport_clock", "causation_id", "project_uuid",
    "project_slug", "correlation_id", "schema_version", "data_tier",
})


def _stub_validate_strict_envelope(record: dict) -> tuple[str, ...]:
    """Pinned stub of F1's 14-key/presence rule (COMPAT6 fallback)."""
    errors = []
    missing = _STUB_STRICT_ENVELOPE_KEYS - record.keys()
    if missing:
        errors.append(f"missing keys: {sorted(missing)}")
    extra = record.keys() - _STUB_STRICT_ENVELOPE_KEYS
    if extra:
        errors.append(f"extra keys: {sorted(extra)}")
    if record.get("schema_version") != "3.0.0":
        errors.append("schema_version must be 3.0.0")
    return tuple(errors)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _git_init(tmp_path)
    (tmp_path / ".kittify").mkdir()
    return tmp_path


@pytest.fixture()
def feature_dir(repo: Path) -> Path:
    fd = repo / "kitty-specs" / _MISSION_SLUG
    fd.mkdir(parents=True)
    return fd


def _legacy_row(
    *,
    event_type: str,
    aggregate_id: str,
    aggregate_type: str,
    payload: dict,
    project_uuid: str | None,
    project_slug: str | None = "demo",
    event_id: str | None = None,
) -> dict:
    """Build one legacy 9-key envelope dict, matching the exact on-disk
    shape ``lifecycle_events._build_envelope`` produces (verified against
    ``lifecycle_events.py:213-233``)."""
    return {
        "event_id": event_id or f"01{uuid.uuid4().hex[:24].upper()}",
        "event_type": event_type,
        "aggregate_id": aggregate_id,
        "aggregate_type": aggregate_type,
        "schema_version": "5.0.0",
        "timestamp": "2026-02-08T12:00:00+00:00",
        "payload": payload,
        "project_uuid": project_uuid,
        "project_slug": project_slug,
    }


def _write_raw_lines(log_path: Path, rows: list[dict]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _six_legacy_row_fixture(project_uuid: str) -> list[dict]:
    """The exact MIG1 fixture: one of each of ProjectInitialized,
    MissionCreated, WPCreated x2, SpecifyStarted, ReviewerSelfApproval, all
    with project_uuid set -- N=6, expected migrated=5, skipped=1
    (ReviewerSelfApproval has no events model, F1 U5)."""
    return [
        _legacy_row(
            event_type="ProjectInitialized", aggregate_id=project_uuid,
            aggregate_type="Project", payload={"project_uuid": project_uuid},
            project_uuid=project_uuid,
        ),
        _legacy_row(
            event_type="MissionCreated", aggregate_id=_MISSION_SLUG,
            aggregate_type="Mission", payload={"mission_slug": _MISSION_SLUG},
            project_uuid=project_uuid,
        ),
        _legacy_row(
            event_type="WPCreated", aggregate_id="WP01",
            aggregate_type="WorkPackage", payload={"wp_id": "WP01"},
            project_uuid=project_uuid,
        ),
        _legacy_row(
            event_type="WPCreated", aggregate_id="WP02",
            aggregate_type="WorkPackage", payload={"wp_id": "WP02"},
            project_uuid=project_uuid,
        ),
        _legacy_row(
            event_type="SpecifyStarted", aggregate_id=_MISSION_SLUG,
            aggregate_type="Mission", payload={"mission_slug": _MISSION_SLUG},
            project_uuid=project_uuid,
        ),
        _legacy_row(
            event_type="ReviewerSelfApproval", aggregate_id="WP01",
            aggregate_type="WorkPackage", payload={"wp_id": "WP01"},
            project_uuid=project_uuid,
        ),
    ]


def test_mig1_count_and_hash_manifest_exact(feature_dir: Path) -> None:
    project_uuid = str(uuid.uuid4())
    log_path = mission_event_log_path(feature_dir)
    _write_raw_lines(log_path, _six_legacy_row_fixture(project_uuid))

    manifest = migrate_lifecycle_envelope(log_path)

    assert manifest.total_rows == 6
    assert manifest.migrated_count == 5
    assert manifest.skipped_count == 1
    assert manifest.unchanged_count == 0
    for row in manifest.rows:
        assert row.pre_hash == row.post_hash, (
            f"{row.event_type}: payload must be untouched by migration"
        )

    entries = read_lifecycle_events(log_path)
    migrated = [e for e in entries if e["event_type"] != "ReviewerSelfApproval"]
    for entry in migrated:
        assert entry["schema_version"] == "3.0.0"
        assert "aggregate_type" not in entry
        assert "aggregate_id" in entry
    reviewer_row = next(e for e in entries if e["event_type"] == "ReviewerSelfApproval")
    assert reviewer_row["schema_version"] == "5.0.0"  # untouched


def test_mig2_idempotent_rerun(feature_dir: Path) -> None:
    project_uuid = str(uuid.uuid4())
    log_path = mission_event_log_path(feature_dir)
    _write_raw_lines(log_path, _six_legacy_row_fixture(project_uuid))

    migrate_lifecycle_envelope(log_path)
    post_first = log_path.read_text(encoding="utf-8")
    first_node_ids = {
        json.loads(line).get("node_id")
        for line in post_first.splitlines()
        if line.strip() and "node_id" in json.loads(line)
    }

    second = migrate_lifecycle_envelope(log_path)
    post_second = log_path.read_text(encoding="utf-8")

    assert second.migrated_count == 0
    assert second.unchanged_count == 5
    assert second.skipped_count == 1
    assert post_second == post_first, "re-migrating an already-migrated file is a no-op"

    second_node_ids = {
        json.loads(line).get("node_id")
        for line in post_second.splitlines()
        if line.strip() and "node_id" in json.loads(line)
    }
    assert first_node_ids == second_node_ids, (
        "synthesized node_id must be deterministic across runs (generate_node_id "
        "is host+user-derived, not random)"
    )


def test_mig3_migration_touches_only_lifecycle_rows(feature_dir: Path) -> None:
    _seed_planned(feature_dir, "WP01", slug=_MISSION_SLUG)
    emit_status_transition(TransitionRequest(
        feature_dir=feature_dir, mission_slug=_MISSION_SLUG, wp_id="WP01",
        to_lane="claimed", actor="implementer",
    ))
    project_uuid = str(uuid.uuid4())
    emit_wp_created_local(
        feature_dir, mission_slug=_MISSION_SLUG, wp_id="WP01", wp_title="T",
        project_uuid=project_uuid, project_slug="demo",
    )
    log_path = mission_event_log_path(feature_dir)
    raw_lines_before = [
        line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    non_lifecycle_before = [
        line for line in raw_lines_before if json.loads(line).get("event_type") != "WPCreated"
    ]

    manifest = migrate_lifecycle_envelope(log_path)
    assert manifest.total_rows == 1
    assert manifest.migrated_count == 1

    raw_lines_after = [
        line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    non_lifecycle_after = [
        line
        for line in raw_lines_after
        if json.loads(line).get("event_type") not in ("WPCreated",)
        and ("to_lane" in json.loads(line) or "kind" in json.loads(line))
    ]
    # The genesis/planned/claimed StatusEvent rows are byte-identical.
    assert non_lifecycle_before == non_lifecycle_after
    assert len(raw_lines_after) == len(raw_lines_before)


def test_mig4_refuses_when_snapshot_already_exists(feature_dir: Path) -> None:
    project_uuid = str(uuid.uuid4())
    emit_wp_created_local(
        feature_dir, mission_slug=_MISSION_SLUG, wp_id="WP01", wp_title="T",
        project_uuid=project_uuid, project_slug="demo",
    )
    log_path = mission_event_log_path(feature_dir)
    original = log_path.read_text(encoding="utf-8")

    backup_path = log_path.with_name(log_path.name + ".pre-migration.bak")
    backup_path.write_text("PRE-EXISTING SNAPSHOT", encoding="utf-8")

    manifest = migrate_lifecycle_envelope(log_path)

    assert manifest.total_rows == 0
    assert manifest.migrated_count == 0
    assert manifest.refused_reason is not None
    assert log_path.read_text(encoding="utf-8") == original
    assert backup_path.read_text(encoding="utf-8") == "PRE-EXISTING SNAPSHOT"


def test_mig5_null_project_uuid_row_is_skipped_not_migrated(feature_dir: Path) -> None:
    emit_wp_created_local(
        feature_dir, mission_slug=_MISSION_SLUG, wp_id="WP01", wp_title="T",
        project_uuid=None, project_slug=None,
    )
    log_path = mission_event_log_path(feature_dir)
    original = log_path.read_text(encoding="utf-8")

    manifest = migrate_lifecycle_envelope(log_path)

    assert manifest.total_rows == 1
    assert manifest.migrated_count == 0
    assert manifest.skipped_count == 1
    assert manifest.rows[0].action == "skipped_no_project_uuid"
    # migrated_count == 0 means the whole file was never rewritten.
    assert log_path.read_text(encoding="utf-8") == original


def test_dry_run_computes_manifest_without_writing(feature_dir: Path) -> None:
    project_uuid = str(uuid.uuid4())
    emit_wp_created_local(
        feature_dir, mission_slug=_MISSION_SLUG, wp_id="WP01", wp_title="T",
        project_uuid=project_uuid, project_slug="demo",
    )
    log_path = mission_event_log_path(feature_dir)
    original = log_path.read_text(encoding="utf-8")

    manifest = migrate_lifecycle_envelope(log_path, dry_run=True)

    assert manifest.migrated_count == 1
    assert log_path.read_text(encoding="utf-8") == original
    assert not log_path.with_name(log_path.name + ".pre-migration.bak").exists()


def test_compat2_migration_does_not_change_materialized_snapshot(feature_dir: Path) -> None:
    _seed_planned(feature_dir, "WP01", slug=_MISSION_SLUG)
    emit_status_transition(TransitionRequest(
        feature_dir=feature_dir, mission_slug=_MISSION_SLUG, wp_id="WP01",
        to_lane="claimed", actor="implementer",
    ))
    project_uuid = str(uuid.uuid4())
    emit_wp_created_local(
        feature_dir, mission_slug=_MISSION_SLUG, wp_id="WP01", wp_title="T",
        project_uuid=project_uuid, project_slug="demo",
    )
    before = materialize_to_json(materialize_snapshot(feature_dir))

    log_path = mission_event_log_path(feature_dir)
    migrate_lifecycle_envelope(log_path)

    after = materialize_to_json(materialize_snapshot(feature_dir))
    assert before == after


def test_compat6_every_migrated_row_passes_strict_validation(feature_dir: Path) -> None:
    project_uuid = str(uuid.uuid4())
    log_path = mission_event_log_path(feature_dir)
    _write_raw_lines(log_path, _six_legacy_row_fixture(project_uuid))

    migrate_lifecycle_envelope(log_path)

    entries = read_lifecycle_events(log_path)
    migrated_entries = [e for e in entries if e.get("schema_version") == "3.0.0"]
    assert migrated_entries, "expected at least one migrated row"
    for entry in migrated_entries:
        errors = _stub_validate_strict_envelope(entry)
        assert errors == (), f"{entry.get('event_type')}: {errors}"


# ---------------------------------------------------------------------------
# Symlink-escape refusal. Renata HANDBACK finding (HIGH): migration must
# never follow a symlinked log_path to read (and then os.replace-clobber)
# whatever it points at -- the same O_NOFOLLOW guard every other
# reader/writer of these two files enforces.
# ---------------------------------------------------------------------------


def test_symlinked_log_path_is_refused_not_followed(
    feature_dir: Path, tmp_path: Path
) -> None:
    external = tmp_path / "external_outside_mission_dir.jsonl"
    external.write_text('{"secret": "leak-me-not"}\n', encoding="utf-8")

    log_path = mission_event_log_path(feature_dir)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.symlink_to(external)

    with pytest.raises(StoreError, match="symbolic link"):
        migrate_lifecycle_envelope(log_path)

    # Refusing must not have touched the symlink or its target.
    assert log_path.is_symlink()
    assert log_path.resolve() == external.resolve()
    assert external.read_text(encoding="utf-8") == '{"secret": "leak-me-not"}\n'


# ---------------------------------------------------------------------------
# C2 -- crash mid-migration (os.replace failure between backup and final
# replace) leaves the original file untouched. Renata HANDBACK finding
# (MEDIUM): F2.md section 4's C2 row had no dedicated test in this module.
# ---------------------------------------------------------------------------


def test_c2_crash_between_backup_and_final_replace_leaves_original_untouched(
    feature_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """migrate_lifecycle_envelope calls _atomic_replace_file twice: once for
    the .pre-migration.bak snapshot, once for the rewritten log itself. A
    crash (os.replace failure) on the SECOND call -- after the snapshot has
    already landed -- must still leave the live log_path exactly as it was;
    the migration is only "done" once the final replace has completed."""
    project_uuid = str(uuid.uuid4())
    log_path = mission_event_log_path(feature_dir)
    _write_raw_lines(log_path, _six_legacy_row_fixture(project_uuid))
    original = log_path.read_text(encoding="utf-8")

    real_replace = migrate_lifecycle_envelope_module.os.replace
    call_count = {"n": 0}

    def _flaky_replace(src: Path, dst: Path) -> None:
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("simulated crash mid-migration (second os.replace)")
        real_replace(src, dst)

    monkeypatch.setattr(migrate_lifecycle_envelope_module.os, "replace", _flaky_replace)

    with pytest.raises(OSError, match="simulated crash mid-migration"):
        migrate_lifecycle_envelope(log_path)

    assert call_count["n"] == 2, "expected exactly 2 os.replace calls (backup, then final)"
    assert log_path.read_text(encoding="utf-8") == original, (
        "a crash on the final replace must leave the live log untouched -- "
        "the backup landing first must not be observable as a partial migration"
    )
    assert list(log_path.parent.glob(f".{log_path.name}.*.tmp")) == [], (
        "no leftover tmp file after the simulated crash"
    )


# ---------------------------------------------------------------------------
# IB1/IB2 -- invalid-byte (corrupted JSON) lines raise a StoreError-shaped,
# line-numbered failure -- never a raw, unhandled json.JSONDecodeError.
# Renata HANDBACK finding (HIGH + MEDIUM): matches store.read_events_raw's
# existing invalid-byte contract (tests/status/test_store.py
# test_corruption_reports_line_number) so migration fails loud-and-legible
# on exactly the crash-scenario input class F2 exists to guard against.
# ---------------------------------------------------------------------------


def test_ib1_invalid_json_line_in_mission_log_raises_line_numbered_error(
    feature_dir: Path,
) -> None:
    project_uuid = str(uuid.uuid4())
    log_path = mission_event_log_path(feature_dir)
    good_row = _legacy_row(
        event_type="ProjectInitialized",
        aggregate_id=project_uuid,
        aggregate_type="Project",
        payload={"project_uuid": project_uuid},
        project_uuid=project_uuid,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(good_row, sort_keys=True) + "\n")
        fh.write("{this is not valid json\n")
    original = log_path.read_text(encoding="utf-8")

    with pytest.raises(StoreError, match="line 2"):
        migrate_lifecycle_envelope(log_path)

    # A corrupted file must be discoverable via dry_run too -- an operator
    # inspecting before committing to a real migration gets the same
    # graceful, line-numbered failure rather than a surprise crash later.
    with pytest.raises(StoreError, match="line 2"):
        migrate_lifecycle_envelope(log_path, dry_run=True)

    # Never partially written: the raise happens before any lock/snapshot
    # bookkeeping, so the log is exactly as corrupted (and only as
    # corrupted) as it started.
    assert log_path.read_text(encoding="utf-8") == original


def test_ib2_invalid_json_line_in_project_log_raises_same_error_shape(
    repo: Path,
) -> None:
    """Asymmetry pin: the project-level log
    (``.kittify/canonical-events.jsonl``) must raise the identical
    StoreError-shaped, line-numbered failure as the mission-level log (IB1)
    -- migration must not special-case one log location's corruption
    handling relative to the other."""
    log_path = project_event_log_path(repo)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    project_uuid = str(uuid.uuid4())
    good_row = _legacy_row(
        event_type="ProjectInitialized",
        aggregate_id=project_uuid,
        aggregate_type="Project",
        payload={"project_uuid": project_uuid},
        project_uuid=project_uuid,
    )
    with log_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(good_row, sort_keys=True) + "\n")
        fh.write("{also not valid json\n")

    with pytest.raises(StoreError, match="line 2"):
        migrate_lifecycle_envelope(log_path)


# ---------------------------------------------------------------------------
# COMPAT1 -- doctor.py's lifecycle-log reader sees identical results before
# and after migration. Renata HANDBACK finding (MEDIUM): F2.md section 4's
# COMPAT1 row had no dedicated test in this module.
# ---------------------------------------------------------------------------


def test_compat1_doctor_reviewer_self_approval_check_survives_migration(
    feature_dir: Path,
) -> None:
    project_uuid = str(uuid.uuid4())
    log_path = mission_event_log_path(feature_dir)
    _write_raw_lines(log_path, _six_legacy_row_fixture(project_uuid))

    before = check_reviewer_self_approval(feature_dir)
    assert len(before) == 1, "expected exactly the one ReviewerSelfApproval finding"

    migrate_lifecycle_envelope(log_path)

    after = check_reviewer_self_approval(feature_dir)
    assert len(after) == 1
    assert after[0].wp_id == before[0].wp_id
    assert after[0].message == before[0].message
    assert after[0].recommended_action == before[0].recommended_action
