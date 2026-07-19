"""Unit tests for the WP03 migration engine (T010–T014).

Covers the ``MUTABLE_FIELDS``/``STATIC_FIELDS`` reclassification (T010),
deterministic namespaced-ULID seeding + clamp honesty (T011), fail-closed verify
including the pre-strip ordering guard (T012), the ``history[]``/``progress``
zero-reader proof (T013), and the idempotency/determinism/precondition assertions
(T014).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import specify_cli
from specify_cli.migration import backfill_runtime_state as b
from specify_cli.migration.strip_frontmatter import (
    MUTABLE_FIELDS,
    RETIRED_FIELDS,
    STATIC_FIELDS,
    strip_mutable_fields,
)
from specify_cli.status.models import Lane, WPInnerStateDelta
from specify_cli.status.reducer import materialize_snapshot
from specify_cli.status.store import (
    append_annotations_atomic_verified,
    read_event_stream,
)
from specify_cli.status.wp_state import annotate
from tests.unit.migration._backfill_fixture import CLAIMED_AT, build_mission

SRC_ROOT = Path(specify_cli.__file__).resolve().parent


# ---------------------------------------------------------------------------
# T010 — MUTABLE_FIELDS / STATIC_FIELDS reclassification
# ---------------------------------------------------------------------------


def test_mutable_fields_gains_evicted_fields() -> None:
    for name in (
        "shell_pid_created_at",
        "review_artifact_override_at",
        "review_artifact_override_actor",
        "review_artifact_override_wp_id",
        "review_artifact_override_reason",
        "reviewer_shell_pid",
        "history",
    ):
        assert name in MUTABLE_FIELDS, name
    # Pre-existing members are untouched.
    for name in ("progress", "shell_pid", "agent", "assignee", "review_status", "reviewed_by", "review_feedback", "lane"):
        assert name in MUTABLE_FIELDS, name


def test_history_moved_out_of_static_and_into_mutable() -> None:
    assert "history" not in STATIC_FIELDS
    assert "history" in MUTABLE_FIELDS


def test_progress_retired_explicitly_not_silently_dropped() -> None:
    # Retired = documented + still stripped (member of MUTABLE_FIELDS).
    assert "progress" in RETIRED_FIELDS
    assert "history" in RETIRED_FIELDS
    assert "progress" in MUTABLE_FIELDS


def test_strip_removes_history_and_new_mutable_keys(tmp_path: Path) -> None:
    from specify_cli.frontmatter import FrontmatterManager

    feature_dir = build_mission(tmp_path)
    strip_mutable_fields(feature_dir)
    frontmatter, _ = FrontmatterManager().read(feature_dir / "tasks" / "WP01-demo.md")
    assert "history" not in frontmatter
    assert "shell_pid" not in frontmatter
    assert "shell_pid_created_at" not in frontmatter
    assert "agent" not in frontmatter
    assert "review_artifact_override_at" not in frontmatter
    # Static intent survives.
    assert frontmatter["work_package_id"] == "WP01"
    assert frontmatter["title"] == "Demo WP"


# ---------------------------------------------------------------------------
# T011 — backfill: seeds, determinism, clamp, idempotency
# ---------------------------------------------------------------------------


def test_backfill_seeds_positive_then_snapshot_matches_old_reader(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    result = b.backfill_runtime_state(feature_dir)
    assert result.action == "wrote"
    assert result.seeded_count > 0

    snap = materialize_snapshot(feature_dir)
    wp = snap.work_packages["WP01"]
    # The lane history is preserved (claim seed slots BEFORE later transitions).
    assert wp["lane"] == str(Lane.IN_PROGRESS)
    # Claim state folded from the seed transition's policy_metadata.
    assert wp["shell_pid"] == 44821
    assert wp["agent"] == "claude:opus:pedro"
    # Annotation-sourced slots.
    assert wp["assignee"] == "pedro"
    assert sorted(wp["tracker_refs"]) == ["JIRA-1", "JIRA-2"]
    assert wp["subtasks"] == {"T001": "done", "T002": "planned"}
    assert wp["review"]["actor"] == "renata"


def test_backfill_is_idempotent(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    first = b.backfill_runtime_state(feature_dir)
    assert first.seeded_count > 0
    second = b.backfill_runtime_state(feature_dir)
    assert second.action == "skip"
    assert second.seeded_count == 0


def test_seed_ids_are_byte_identical_across_independent_runs(tmp_path: Path) -> None:
    fd_a = build_mission(tmp_path / "a")
    fd_b = build_mission(tmp_path / "b")
    b.backfill_runtime_state(fd_a)
    b.backfill_runtime_state(fd_b)

    def seed_annotation_ids(fd: Path) -> dict[str, str]:
        ids: dict[str, str] = {}
        for a in read_event_stream(fd).annotations:
            if a.actor == b.BACKFILL_ACTOR:
                key = next(iter(a.delta.to_dict().keys()))
                ids[key] = a.event_id
        return ids

    assert seed_annotation_ids(fd_a) == seed_annotation_ids(fd_b)
    # And the id is exactly deterministic_ulid over (mission_id|wp|field).
    assert b._seed_id(b._mission_id(fd_a), "WP01", "subtasks") == seed_annotation_ids(fd_a)["subtasks"]


def test_subtask_mark_at_clamps_to_claimed(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    b.backfill_runtime_state(feature_dir)
    subtask_seeds = [a for a in read_event_stream(feature_dir).annotations if a.delta.subtasks]
    assert subtask_seeds, "expected a subtasks seed annotation"
    for seed in subtask_seeds:
        assert seed.at == CLAIMED_AT  # fictional clamp, not a real completion time


def test_never_claimed_wp_skips_runtime_seed(tmp_path: Path) -> None:
    # No transitions at all → no claim anchor → runtime seed skipped, warned.
    feature_dir = build_mission(tmp_path, with_transitions=False)
    result = b.backfill_runtime_state(feature_dir)
    assert result.seeded_count == 0
    assert any("never-claimed" in w for w in result.warnings)


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    before = (feature_dir / "status.events.jsonl").read_text(encoding="utf-8")
    result = b.backfill_runtime_state(feature_dir, dry_run=True)
    assert result.action == "wrote"
    assert result.seeded_count > 0
    after = (feature_dir / "status.events.jsonl").read_text(encoding="utf-8")
    assert before == after


def test_equal_at_transition_and_annotation_do_not_clobber(tmp_path: Path) -> None:
    # The claim seed transition and the annotations share the WP's claimed `at`.
    # The reducer's event-kind partition folds annotations AFTER transitions, so
    # neither clobbers the other at equal `at`.
    feature_dir = build_mission(tmp_path)
    b.backfill_runtime_state(feature_dir)
    wp = materialize_snapshot(feature_dir).work_packages["WP01"]
    assert wp["shell_pid"] == 44821  # transition-sourced slot survived
    assert wp["subtasks"] == {"T001": "done", "T002": "planned"}  # annotation-sourced slot survived


# ---------------------------------------------------------------------------
# T012 — fail-closed verify
# ---------------------------------------------------------------------------


def test_clean_backfill_verifies_ok(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    b.backfill_runtime_state(feature_dir)
    assert b.verify_backfill(feature_dir).ok is True


def test_fault_injected_value_mismatch_aborts_with_count_match(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    b.backfill_runtime_state(feature_dir)
    # Corrupt a seed: flip T001 done→planned. Counts still match; value diverges.
    corrupt = annotate(
        "WP01",
        WPInnerStateDelta(subtasks={"T001": Lane.PLANNED}),
        actor="attacker",
        at=CLAIMED_AT,
        event_id="01ZZZZZZZZZZZZZZZZZZZZZZZ9",
    )
    append_annotations_atomic_verified(feature_dir, [corrupt])
    result = b.verify_backfill(feature_dir)
    assert result.ok is False
    assert any("subtasks mismatch" in m for m in result.mismatches)


def test_scalar_value_mismatch_aborts(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    b.backfill_runtime_state(feature_dir)
    corrupt = annotate(
        "WP01",
        WPInnerStateDelta(shell_pid=999999),
        actor="attacker",
        at=CLAIMED_AT,
        event_id="01YYYYYYYYYYYYYYYYYYYYYYY8",
    )
    append_annotations_atomic_verified(feature_dir, [corrupt])
    result = b.verify_backfill(feature_dir)
    assert result.ok is False
    assert any("shell_pid mismatch" in m for m in result.mismatches)


def test_verify_runs_pre_strip_inverting_order_is_caught(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    b.backfill_runtime_state(feature_dir)
    # Correct order verifies ok BEFORE any strip.
    assert b.verify_backfill(feature_dir).ok is True
    # Inverting the order (strip → verify) is caught fail-closed, not a false green.
    strip_mutable_fields(feature_dir)
    with pytest.raises(b.MigrationOrderingError):
        b.verify_backfill(feature_dir)


def test_unreadable_event_log_is_fail_closed(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    b.backfill_runtime_state(feature_dir)
    (feature_dir / "status.events.jsonl").write_text("{ not valid json", encoding="utf-8")
    result = b.verify_backfill(feature_dir)
    assert result.ok is False


def test_run_backfill_and_verify_raises_on_mismatch(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    b.backfill_runtime_state(feature_dir)
    append_annotations_atomic_verified(
        feature_dir,
        [
            annotate(
                "WP01",
                WPInnerStateDelta(agent="tampered"),
                actor="attacker",
                at=CLAIMED_AT,
                event_id="01XXXXXXXXXXXXXXXXXXXXXXX7",
            )
        ],
    )
    with pytest.raises(b.BackfillVerificationError):
        b.run_backfill_and_verify(feature_dir)


def test_empty_mission_verifies_ok(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "099-empty"
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"mission_id": "X", "mission_slug": "099-empty"}', encoding="utf-8")
    assert b.verify_backfill(feature_dir).ok is True


# ---------------------------------------------------------------------------
# T013 — zero-reader verification for history[] / progress
# ---------------------------------------------------------------------------


def test_progress_has_zero_live_readers_in_src() -> None:
    assert b.find_field_readers(SRC_ROOT, "progress") == []


def test_history_only_touched_by_known_writer_seams() -> None:
    # After excluding the WP07/T028-owned writer seams, history has no consumer.
    remaining = b.find_field_readers(SRC_ROOT, "history", exclude_basenames=b.HISTORY_WRITER_SEAMS)
    assert remaining == [], remaining
    # The exclusion is real (non-vacuous): the writer seams DO still touch history
    # (they are WP07/T028's to delete — this WP proves, it does not delete).
    unfiltered = b.find_field_readers(SRC_ROOT, "history")
    assert unfiltered, "expected the history writer seams to still exist pre-WP07"


def test_assert_zero_readers_passes_for_real_src() -> None:
    # Uses the default HISTORY_WRITER_SEAMS exclusion → both fields prove clean.
    b.assert_zero_readers(SRC_ROOT)


def test_zero_reader_check_is_non_vacuous(tmp_path: Path) -> None:
    stub = tmp_path / "src_stub"
    (stub / "pkg").mkdir(parents=True)
    (stub / "pkg" / "reader.py").write_text(
        "def read(meta):\n    return meta.get('progress')\n", encoding="utf-8"
    )
    assert b.find_field_readers(stub, "progress")
    with pytest.raises(AssertionError):
        b.assert_zero_readers(stub, fields=("progress",))


# ---------------------------------------------------------------------------
# T014 — honesty precondition assertions
# ---------------------------------------------------------------------------


def test_precondition_snapshot_carries_no_subtask_completion_time(tmp_path: Path) -> None:
    # "No data loss" holds only because no consumer reads subtask-completion time.
    # Prove the precondition: the reduced snapshot subtasks slot is a bare
    # id→status map — there is no completion-time field for anyone to read.
    feature_dir = build_mission(tmp_path)
    b.backfill_runtime_state(feature_dir)
    subtasks = materialize_snapshot(feature_dir).work_packages["WP01"]["subtasks"]
    assert set(subtasks.values()) <= {"done", "planned"}
    for value in subtasks.values():
        assert isinstance(value, str)  # a status string, never a {status, at} dict


def test_precondition_no_reliance_on_seed_ulid_chronology(tmp_path: Path) -> None:
    # Reversing the append order of the seed annotations must not change the
    # reduced snapshot — proving nothing relies on seed-ULID chronological order.
    fd_a = build_mission(tmp_path / "a")
    fd_b = build_mission(tmp_path / "b")

    b.backfill_runtime_state(fd_a)

    # Re-seed fd_b manually with the SAME events in reverse order.
    legacy = b.read_legacy_runtime(fd_b)
    anchors = b._claim_anchors(fd_b)
    transitions, annotations = b._build_seed_events(fd_b, legacy, anchors, [])
    from specify_cli.status.store import append_events_atomic_verified

    append_events_atomic_verified(fd_b, transitions)
    append_annotations_atomic_verified(fd_b, list(reversed(annotations)))

    snap_a = materialize_snapshot(fd_a).work_packages["WP01"]
    snap_b = materialize_snapshot(fd_b).work_packages["WP01"]
    for slot in ("shell_pid", "agent", "assignee", "tracker_refs", "subtasks", "review"):
        assert snap_a.get(slot) == snap_b.get(slot), slot
