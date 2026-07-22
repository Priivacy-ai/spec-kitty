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
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.reducer import materialize_snapshot
from specify_cli.status.store import (
    append_annotations_atomic_verified,
    append_events_atomic_verified,
    read_event_stream,
)
from specify_cli.status.wp_view import reconstruct_wp_view
from tests.unit.migration._backfill_fixture import (
    CLAIMED_AT,
    build_mission,
    corrupt_seed_value,
)

pytestmark = [pytest.mark.fast]

SRC_ROOT = Path(specify_cli.__file__).resolve().parent


@pytest.mark.parametrize("unsafe_slug", ["../outside", "nested/mission", ".", ".."])
def test_repo_backfill_rejects_unsafe_mission_selector(
    tmp_path: Path,
    unsafe_slug: str,
) -> None:
    """The write-capable library validates selectors at its own boundary."""
    (tmp_path / "kitty-specs").mkdir()

    with pytest.raises(ValueError, match="safe path segment"):
        b.backfill_runtime_state_repo(tmp_path, mission_slug=unsafe_slug)


def test_repo_backfill_rejects_selected_mission_symlink_escape(tmp_path: Path) -> None:
    kitty_specs = tmp_path / "kitty-specs"
    kitty_specs.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (kitty_specs / "escaped").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="outside kitty-specs"):
        b.backfill_runtime_state_repo(tmp_path, mission_slug="escaped")


def test_repo_backfill_skips_enumerated_mission_symlink_escape(tmp_path: Path) -> None:
    kitty_specs = tmp_path / "kitty-specs"
    kitty_specs.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (kitty_specs / "escaped").symlink_to(outside, target_is_directory=True)

    assert b.backfill_runtime_state_repo(tmp_path) == []


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
    # No transitions AND no frontmatter claim state at all → genuinely never
    # claimed → no claim anchor (real or synthesized) → runtime seed skipped,
    # warned. (Contrast with test_claim_anchor_synthesized_from_frontmatter_*
    # below: a WP WITH claim state but no event log gets a SYNTHESIZED anchor
    # instead of being skipped — #2848.)
    feature_dir = build_mission(tmp_path, with_transitions=False, with_claim=False)
    result = b.backfill_runtime_state(feature_dir)
    assert result.seeded_count == 0
    assert any("never-claimed" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# #2848 — claim-anchor synthesis for a missing/truncated event log
# ---------------------------------------------------------------------------


def test_claim_anchor_synthesized_from_frontmatter_when_event_log_missing(tmp_path: Path) -> None:
    """Regression for the live-proved defect (debugger-debbie, #2848).

    ``kitty-specs/merge-coord-rollback-transactionality-01KXTM59`` has 5 WPs
    whose frontmatter carries a real claim (``agent="claude"`` + ``shell_pid``)
    but NO ``status.events.jsonl`` at all. Pre-fix, ``_claim_anchors`` found no
    anchor, ``_build_seed_events`` skipped the WP as "never-claimed",
    ``verify_backfill`` returned a VACUOUS ``ok=True, wp_count=0``, and the
    mission flipped to snapshot authority with an EMPTY runtime —
    ``reconstruct_wp_view`` then silently lost the ``agent``/``shell_pid``.

    After the fix: the claim anchor is synthesized from
    ``shell_pid_created_at``, the claim IS seeded, verify is non-vacuous
    (``wp_count > 0``), and the recovered ``agent``/``shell_pid`` round-trip
    through the reduced snapshot and :func:`reconstruct_wp_view`.
    """
    feature_dir = build_mission(tmp_path, with_transitions=False)
    assert not (feature_dir / "status.events.jsonl").exists()

    result = b.backfill_runtime_state(feature_dir)
    assert result.action == "wrote"
    assert result.seeded_count > 0
    assert any("synthesized from frontmatter" in w for w in result.warnings)
    assert not any("never-claimed" in w for w in result.warnings)

    verify = b.verify_backfill(feature_dir)
    assert verify.ok is True
    assert verify.wp_count == 1  # non-vacuous: the pre-fix bug returned wp_count == 0

    snap = materialize_snapshot(feature_dir).work_packages["WP01"]
    assert snap["agent"] == "claude:opus:pedro"
    assert snap["shell_pid"] == 44821

    view = reconstruct_wp_view(feature_dir, "WP01")
    assert view.resolved.agent == "claude:opus:pedro"
    assert view.resolved.shell_pid == "44821"

    # Idempotent: a second run seeds nothing new (deterministic seed ids).
    second = b.backfill_runtime_state(feature_dir)
    assert second.action == "skip"
    assert second.seeded_count == 0


def test_claim_anchor_falls_back_to_mission_created_at(tmp_path: Path) -> None:
    """When ``shell_pid_created_at`` itself is unparseable, fall back to the
    mission's ``meta.json`` ``created_at`` — still deterministic, still real."""
    feature_dir = build_mission(
        tmp_path,
        with_transitions=False,
        shell_pid_created_at="not-a-timestamp",
        meta_created_at="2026-01-01T00:00:00+00:00",
    )
    result = b.backfill_runtime_state(feature_dir)
    assert result.seeded_count > 0
    claim = next(e for e in read_event_stream(feature_dir).transitions if e.wp_id == "WP01")
    assert claim.at == "2026-01-01T00:00:00+00:00"


def test_claim_anchor_unresolvable_without_any_timestamp_stays_never_claimed(tmp_path: Path) -> None:
    """Claim *fields* (``agent``) with NO honest timestamp anywhere (neither a
    parseable ``shell_pid_created_at`` nor a ``meta.json`` ``created_at``) must
    NOT fabricate a time — fail-closed, same as the genuinely never-claimed case."""
    feature_dir = build_mission(tmp_path, with_transitions=False, shell_pid_created_at="not-a-timestamp")
    result = b.backfill_runtime_state(feature_dir)
    assert result.seeded_count == 0
    assert any("never-claimed" in w for w in result.warnings)


def test_malformed_wp_frontmatter_fails_closed(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    wp_file = feature_dir / "tasks" / "WP01-demo.md"
    wp_file.write_text(
        "---\nwork_package_id: WP01\nbroken: [\n---\n\n# WP01\n",
        encoding="utf-8",
    )

    with pytest.raises(b.LegacyRuntimeReadError, match="WP01-demo.md"):
        b.read_legacy_runtime(feature_dir)

    result = b.backfill_runtime_state(feature_dir)
    assert result.action == "error"
    assert "WP01-demo.md" in (result.reason or "")


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
    corrupt_seed_value(
        feature_dir,
        field_name="subtasks",
        slot_name="subtasks",
        value={"T001": "planned", "T002": "planned"},
    )
    result = b.verify_backfill(feature_dir)
    assert result.ok is False
    assert any("subtasks mismatch" in m for m in result.mismatches)


def test_scalar_value_mismatch_aborts(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    b.backfill_runtime_state(feature_dir)
    corrupt_seed_value(
        feature_dir,
        field_name="claim",
        slot_name="shell_pid",
        value=999999,
    )
    result = b.verify_backfill(feature_dir)
    assert result.ok is False
    assert any("claim mismatch" in m for m in result.mismatches)


def test_never_claimed_wp_absent_from_snapshot_warns_not_fails(tmp_path: Path) -> None:
    """Defect 1 (spec Edge Case, WP03 corpus): a never-claimed WP warns, not fails.

    WP02 carries evictable frontmatter runtime state but has no transitions, so it
    has no claim anchor: ``_build_seed_events`` correctly SKIPS its seeds ("no claim
    anchor — runtime seed skipped"), and ``verify_backfill`` must MIRROR that skip —
    an anchor-less WP is never a count mismatch. (The pre-fix code counted it and
    hard-failed 7 real dogfood missions, blocking the whole cutover.)"""
    feature_dir = build_mission(tmp_path)
    (feature_dir / "tasks" / "WP02-extra.md").write_text(
        "---\nwork_package_id: WP02\ntitle: Extra\nagent: ghost:model:profile\n---\n\n# WP02 body\n",
        encoding="utf-8",
    )
    b.backfill_runtime_state(feature_dir)
    result = b.verify_backfill(feature_dir)
    assert result.ok is True
    assert not any("WP02" in m for m in result.mismatches)


def test_phantom_snapshot_only_wp_with_no_wp_file_still_aborts(tmp_path: Path) -> None:
    """Fail-closed preserved: a snapshot WP with NO legacy WP row (phantom/injected).

    A claim seed for WP99 (which has no WP file / no legacy row at all) folds a
    ``shell_pid`` into the snapshot. Unlike an already-migrated WP whose file exists
    but whose runtime is now event-sourced (tolerated — Defect 3), a phantom WP with
    no file is an injected/corrupt entry and MUST still abort fail-closed."""
    feature_dir = build_mission(tmp_path)
    b.backfill_runtime_state(feature_dir)
    append_events_atomic_verified(
        feature_dir,
        [
            StatusEvent(
                event_id="01BBBBBBBBBBBBBBBBBBBBBBB9",
                mission_slug=feature_dir.name,
                wp_id="WP99",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at=CLAIMED_AT,
                actor="attacker",
                force=True,
                execution_mode="worktree",
                policy_metadata={"shell_pid": 12321, "agent": "ghost"},
            )
        ],
    )
    result = b.verify_backfill(feature_dir)
    assert result.ok is False
    assert any("phantom" in m for m in result.mismatches)


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
    corrupt_seed_value(
        feature_dir,
        field_name="claim",
        slot_name="agent",
        value="tampered",
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
