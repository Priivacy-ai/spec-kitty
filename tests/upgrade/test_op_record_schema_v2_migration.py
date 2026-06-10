"""Tests for the kitty-ops Op record v2 schema migration (WP05, FR-011).

Covers every row of the normative migration mapping table in
``kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/data-model.md``, plus
deletion reporting, atomicity (tmp cleanup), double-run idempotency, the
``detect()`` matrix, and the excluded-files guarantee.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from specify_cli.invocation.record import OpCompletedEvent, OpStartedEvent
from specify_cli.upgrade.migrations import m_3_3_0_op_record_schema_v2 as mod
from specify_cli.upgrade.migrations.m_3_3_0_op_record_schema_v2 import (
    EXCLUDED_FILES,
    OpRecordSchemaV2Migration,
)

pytestmark = pytest.mark.fast

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
ULID2 = "01BX5ZZKBKACTAV9WEVGEMMVRZ"


@pytest.fixture
def migration() -> OpRecordSchemaV2Migration:
    return OpRecordSchemaV2Migration()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "kitty-ops").mkdir()
    return tmp_path


def _write(project: Path, name: str, lines: list[str]) -> Path:
    path = project / "kitty-ops" / name
    path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return path


def _legacy_started(**overrides: object) -> str:
    data: dict[str, object] = {
        "event": "started",
        "invocation_id": ULID,
        "profile_id": "python-pedro",
        "action": "implement",
        "request_text": "do the thing",
        "governance_context_hash": "abcd1234abcd1234",
        "governance_context_available": True,
        "actor": "claude",
        "router_confidence": "exact",
        "started_at": "2026-01-01T00:00:00Z",
    }
    data.update(overrides)
    for key in [k for k, v in data.items() if v is ...]:
        del data[key]
    return json.dumps(data)


def _legacy_completed(**overrides: object) -> str:
    data: dict[str, object] = {
        "event": "completed",
        "invocation_id": ULID,
        "completed_at": "2026-01-01T01:00:00Z",
        "outcome": "done",
        "evidence_ref": None,
    }
    data.update(overrides)
    for key in [k for k, v in data.items() if v is ...]:
        del data[key]
    return json.dumps(data)


def _v2_file_lines() -> list[str]:
    started = OpStartedEvent(
        invocation_id=ULID,
        profile_id="python-pedro",
        action="implement",
        request_text="do the thing",
        actor="claude",
        mode_of_work="task_execution",
        governance_context_hash="abcd1234abcd1234",
        governance_context_available=True,
        started_at="2026-01-01T00:00:00Z",
    )
    completed = OpCompletedEvent(
        invocation_id=ULID,
        completed_at="2026-01-01T01:00:00Z",
        outcome="done",
        closed_by="agent",
    )
    return [started.to_jsonl_line(), completed.to_jsonl_line()]


# ---------------------------------------------------------------------------
# Mapping table rows
# ---------------------------------------------------------------------------


class TestMappingTable:
    def test_started_event_rewritten_to_v2(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 1: started with invocation_id + profile_id → OpStartedEvent."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        result = migration.apply(project)
        assert result.success
        line = json.loads(path.read_text().splitlines()[0])
        assert line["mode_of_work"] == "task_execution"  # missing → default
        assert line["actor"] == "claude"  # preserved when non-empty
        assert line["action"] == "implement"
        assert line["profile_id"] == "python-pedro"
        assert line["started_at"] == "2026-01-01T00:00:00Z"
        # round-trips through the v2 model
        OpStartedEvent.model_validate(line)

    def test_mode_of_work_null_becomes_task_execution(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(mode_of_work=None)])
        migration.apply(project)
        line = json.loads(path.read_text().splitlines()[0])
        assert line["mode_of_work"] == "task_execution"

    def test_missing_actor_and_action_become_unrecorded(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 2: missing/empty actor or action → literal "unrecorded"."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(actor=..., action="")])
        migration.apply(project)
        line = json.loads(path.read_text().splitlines()[0])
        assert line["actor"] == "unrecorded"
        assert line["action"] == "unrecorded"

    def test_invalid_mode_of_work_is_deleted_not_skipped(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """A bogus non-empty mode_of_work is not "already v2" and fails closed."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(mode_of_work="bogus")])
        result = migration.apply(project)
        assert not path.exists()
        assert any("Deleted unsalvageable" in change for change in result.changes_made)

    def test_completed_with_outcome_gains_closed_by_agent(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 3: completed with non-null outcome → closed_by="agent"."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(), _legacy_completed(outcome="failed")])
        result = migration.apply(project)
        completed = json.loads(path.read_text().splitlines()[1])
        assert completed["outcome"] == "failed"
        assert completed["closed_by"] == "agent"
        assert completed["completed_at"] == "2026-01-01T01:00:00Z"
        assert not result.warnings
        OpCompletedEvent.model_validate(completed)

    def test_invalid_completed_closed_by_is_repaired_not_skipped(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """A bogus non-empty closed_by is not already-v2; repair to agent."""
        path = _write(
            project,
            f"{ULID}.jsonl",
            [_legacy_started(), _legacy_completed(outcome="done", closed_by="bogus")],
        )
        migration.apply(project)
        completed = json.loads(path.read_text().splitlines()[1])
        assert completed["outcome"] == "done"
        assert completed["closed_by"] == "agent"

    def test_missing_completed_at_falls_back_to_started_at_and_flags(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 3 fallback: missing completed_at → started_at, flagged in report."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(), _legacy_completed(completed_at=None)])
        result = migration.apply(project)
        completed = json.loads(path.read_text().splitlines()[1])
        assert completed["completed_at"] == "2026-01-01T00:00:00Z"
        assert any("completed_at" in w and ULID in w for w in result.warnings)

    def test_null_outcome_becomes_abandoned(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 4: null outcome (old auto-close artifact) → abandoned, agent."""
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(), _legacy_completed(outcome=None)])
        migration.apply(project)
        completed = json.loads(path.read_text().splitlines()[1])
        assert completed["outcome"] == "abandoned"
        assert completed["closed_by"] == "agent"

    def test_link_and_glossary_events_pass_through_byte_identical(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 5: link/glossary events pass through unchanged."""
        link_lines = [
            json.dumps({"event": "artifact_link", "invocation_id": ULID, "path": "a.md"}),
            json.dumps({"event": "commit_link", "invocation_id": ULID, "sha": "deadbeef"}),
            json.dumps({"event": "glossary_checked", "invocation_id": ULID}),
        ]
        path = _write(project, f"{ULID}.jsonl", [_legacy_started(), *link_lines])
        migration.apply(project)
        assert path.read_text().splitlines()[1:] == link_lines

    def test_unsalvageable_files_deleted_and_reported(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 6: unparseable / identity-less started event → delete + report."""
        bad_json = _write(project, "bad-json.jsonl", ["{not json"])
        no_profile = _write(project, "no-profile.jsonl", [_legacy_started(profile_id=...)])
        no_inv = _write(project, "no-inv.jsonl", [_legacy_started(invocation_id="")])
        no_started = _write(project, "no-started.jsonl", [_legacy_completed()])
        result = migration.apply(project)
        for path in (bad_json, no_profile, no_inv, no_started):
            assert not path.exists()
        assert sum("Deleted unsalvageable" in c for c in result.changes_made) == 4
        summary = [w for w in result.warnings if "Deleted 4 unsalvageable" in w]
        assert summary and "bad-json.jsonl" in summary[0]

    def test_already_v2_file_skipped_untouched(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        """Row 7: already-v2 file (completed has closed_by) → skip."""
        path = _write(project, f"{ULID}.jsonl", _v2_file_lines())
        before = path.read_bytes()
        result = migration.apply(project)
        assert path.read_bytes() == before
        assert result.changes_made == []


# ---------------------------------------------------------------------------
# Idempotency / atomicity
# ---------------------------------------------------------------------------


class TestIdempotencyAndAtomicity:
    def test_double_run_is_byte_identical_noop(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        _write(project, f"{ULID}.jsonl", [_legacy_started(), _legacy_completed(outcome=None)])
        _write(project, f"{ULID2}.jsonl", [_legacy_started(invocation_id=ULID2, actor="")])
        _write(project, "bad.jsonl", ["{nope"])
        first = migration.apply(project)
        assert first.changes_made
        snapshot = {p.name: p.read_bytes() for p in (project / "kitty-ops").glob("*.jsonl")}
        second = migration.apply(project)
        assert second.changes_made == []
        assert second.warnings == []
        after = {p.name: p.read_bytes() for p in (project / "kitty-ops").glob("*.jsonl")}
        assert after == snapshot

    def test_detect_false_after_migration(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        _write(project, f"{ULID}.jsonl", [_legacy_started()])
        assert migration.detect(project) is True
        migration.apply(project)
        assert migration.detect(project) is False

    def test_tmp_file_cleaned_up_on_replace_failure(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        original = path.read_bytes()

        def boom(src: object, dst: object) -> None:
            raise OSError("simulated replace failure")

        monkeypatch.setattr(mod.os, "replace", boom)
        with pytest.raises(OSError, match="simulated"):
            migration.apply(project)
        assert path.read_bytes() == original  # original never partially written
        assert list((project / "kitty-ops").glob("*.tmp")) == []

    def test_atomic_rewrite_uses_os_replace(
        self,
        migration: OpRecordSchemaV2Migration,
        project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _write(project, f"{ULID}.jsonl", [_legacy_started()])
        calls: list[tuple[str, str]] = []
        real_replace = os.replace

        def spy(src: object, dst: object) -> None:
            calls.append((str(src), str(dst)))
            real_replace(src, dst)  # type: ignore[arg-type]

        monkeypatch.setattr(mod.os, "replace", spy)
        migration.apply(project)
        assert len(calls) == 1
        assert calls[0][0].endswith(".jsonl.tmp")
        assert calls[0][1].endswith(f"{ULID}.jsonl")

    def test_dry_run_changes_nothing(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        legacy = _write(project, f"{ULID}.jsonl", [_legacy_started()])
        bad = _write(project, "bad.jsonl", ["{nope"])
        before = (legacy.read_bytes(), bad.read_bytes())
        result = migration.apply(project, dry_run=True)
        assert (legacy.read_bytes(), bad.read_bytes()) == before
        assert any(c.startswith("Would rewrite") for c in result.changes_made)
        assert any(c.startswith("Would delete") for c in result.changes_made)
        assert migration.detect(project) is True


# ---------------------------------------------------------------------------
# detect() matrix / exclusions / registration
# ---------------------------------------------------------------------------


class TestDetectMatrix:
    def test_detect_false_without_kitty_ops(self, migration: OpRecordSchemaV2Migration, tmp_path: Path) -> None:
        assert migration.detect(tmp_path) is False

    def test_detect_false_for_empty_ops_dir(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        assert migration.detect(project) is False

    def test_detect_false_when_only_excluded_files_exist(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        for name in EXCLUDED_FILES:
            _write(project, name, [_legacy_started()])  # legacy-looking content
        assert migration.detect(project) is False

    def test_detect_false_for_v2_only(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        _write(project, f"{ULID}.jsonl", _v2_file_lines())
        assert migration.detect(project) is False

    @pytest.mark.parametrize(
        "lines",
        [
            [_legacy_started()],  # legacy started (no mode_of_work)
            _v2_file_lines()[:1] + [_legacy_completed()],  # legacy completed
            ["{nope"],  # unsalvageable
        ],
        ids=["legacy-started", "legacy-completed", "unsalvageable"],
    )
    def test_detect_true_for_legacy_shapes(self, migration: OpRecordSchemaV2Migration, project: Path, lines: list[str]) -> None:
        _write(project, f"{ULID}.jsonl", lines)
        assert migration.detect(project) is True

    def test_excluded_files_never_touched_by_apply(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        excluded = {name: _write(project, name, [_legacy_started(), "{not even json"]) for name in EXCLUDED_FILES}
        _write(project, f"{ULID}.jsonl", [_legacy_started()])
        before = {name: p.read_bytes() for name, p in excluded.items()}
        migration.apply(project)
        assert {name: p.read_bytes() for name, p in excluded.items()} == before

    def test_can_apply_requires_ops_dir(self, migration: OpRecordSchemaV2Migration, project: Path) -> None:
        bare = project / "no-ops-here"
        bare.mkdir()
        ok, _reason = migration.can_apply(bare)
        assert ok is False
        ok, reason = migration.can_apply(project)
        assert ok is True and reason == ""

    def test_migration_is_registered(self) -> None:
        from specify_cli.upgrade.registry import MigrationRegistry

        ids = {m.migration_id for m in MigrationRegistry.get_all()}
        assert "3_3_0_op_record_schema_v2" in ids
