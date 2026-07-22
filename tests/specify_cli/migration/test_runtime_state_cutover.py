"""ATDD unit tests for the cutover orchestration helper (WP01 / IC-01).

Non-vacuous, real-fault-injection coverage of the fail-closed contract:

* the happy path seeds -> verifies -> flips ``status_phase`` to ``"1"``;
* a REAL corrupt deterministic seed (a divergent payload under the canonical
  seed ID) makes verify fail -> the flip is
  unreachable and ``meta.json`` is byte-identical (NFR-001 / INV-1);
* a strip-before-verify surfaces as ``MigrationOrderingError`` -> ``error`` set, no flip;
* dry-run and idempotent re-runs write zero bytes (NFR-002 / INV-4);
* the flip target resolves via ``canonicalize_feature_dir`` and nothing lands at the
  repo root (INV-5 / C-003 / #2815).

Every fault test exercises the REAL library verify over a REAL fixture event log — no
``verify_backfill`` / ``cutover_mission`` is mocked to force a pass.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.migration import runtime_state_cutover as rsc
from specify_cli.migration.backfill_runtime_state import backfill_runtime_state, verify_backfill
from specify_cli.migration.mission_state import deterministic_ulid
from specify_cli.migration.strip_frontmatter import strip_mutable_fields
from specify_cli.status import (
    Lane,
    WPInnerStateDelta,
    annotate,
    append_annotations_atomic_verified,
    emit_inner_state_changed,
)
from tests.unit.migration._backfill_fixture import (
    CLAIMED_AT,
    IN_PROGRESS_AT,
    build_mission,
    corrupt_seed_value,
)

pytestmark = [pytest.mark.fast]

_STATUS_PHASE = "status_phase"


def _inject_conflicting_seed(feature_dir: Path, *, slot_value: str = "EVIL-DIVERGENT") -> None:
    """Corrupt the canonical assignee seed payload under its deterministic ID."""
    corrupt_seed_value(
        feature_dir,
        field_name="assignee",
        slot_name="assignee",
        value=slot_value,
    )


# ---------------------------------------------------------------------------
# Phase units
# ---------------------------------------------------------------------------


def test_seed_phase_wraps_backfill(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    result = rsc._seed_phase(feature_dir, dry_run=False)
    assert result.action == "wrote"
    assert result.seeded_count > 0


def test_verify_phase_ok_after_seed(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    rsc._seed_phase(feature_dir, dry_run=False)
    assert rsc._verify_phase(feature_dir).ok


def test_flip_phase_writes_snapshot_authority(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    rsc._seed_phase(feature_dir, dry_run=False)
    rsc._flip_phase(feature_dir)
    assert json.loads((feature_dir / "meta.json").read_text())[_STATUS_PHASE] == "1"


def test_flip_phase_is_byte_idempotent(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    rsc._seed_phase(feature_dir, dry_run=False)
    rsc._flip_phase(feature_dir)
    first = (feature_dir / "meta.json").read_bytes()
    rsc._flip_phase(feature_dir)  # already-authority -> short-circuits, writes nothing
    assert (feature_dir / "meta.json").read_bytes() == first


def test_is_snapshot_authority_parsing() -> None:
    assert rsc._is_snapshot_authority({_STATUS_PHASE: "1"})
    assert rsc._is_snapshot_authority({_STATUS_PHASE: 1})
    assert rsc._is_snapshot_authority({_STATUS_PHASE: 2})
    assert not rsc._is_snapshot_authority({_STATUS_PHASE: 0})
    assert not rsc._is_snapshot_authority({_STATUS_PHASE: "not-a-number"})
    assert not rsc._is_snapshot_authority({})


# ---------------------------------------------------------------------------
# cutover_mission — happy path
# ---------------------------------------------------------------------------


def test_happy_path_seeds_verifies_and_flips(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    result = rsc.cutover_mission(feature_dir)

    assert result.flipped is True
    assert result.would_flip is False
    assert result.error is None
    assert result.seeded_count > 0
    assert result.verify is not None and result.verify.ok
    assert json.loads((feature_dir / "meta.json").read_text())[_STATUS_PHASE] == "1"


def test_malformed_wp_aborts_without_phase_flip(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    meta_path = feature_dir / "meta.json"
    before_meta = meta_path.read_bytes()
    events_path = feature_dir / "status.events.jsonl"
    before_events = events_path.read_bytes()
    (feature_dir / "tasks" / "WP01-demo.md").write_text(
        "---\nwork_package_id: WP01\nbroken: [\n---\n\n# WP01\n",
        encoding="utf-8",
    )

    result = rsc.cutover_mission(feature_dir)

    assert result.flipped is False
    assert result.error is not None and "WP01-demo.md" in result.error
    assert meta_path.read_bytes() == before_meta
    assert events_path.read_bytes() == before_events


# ---------------------------------------------------------------------------
# cutover_mission — refuse-to-flip (NFR-001 / INV-1), real fault injection
# ---------------------------------------------------------------------------


def test_refuse_to_flip_on_conflicting_seed_leaves_meta_untouched(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    backfill_runtime_state(feature_dir)  # legit seeds first
    _inject_conflicting_seed(feature_dir)  # REAL corruption verify must catch
    meta_before = (feature_dir / "meta.json").read_bytes()

    result = rsc.cutover_mission(feature_dir)

    assert result.flipped is False
    assert result.verify is not None and result.verify.ok is False
    assert any("assignee" in m for m in result.verify.mismatches)
    # The flip is structurally unreachable: meta.json is byte-identical.
    assert (feature_dir / "meta.json").read_bytes() == meta_before


def test_refuse_to_flip_guard_is_non_vacuous(tmp_path: Path) -> None:
    """If the verify.ok guard were removed the flip WOULD run — prove verify blocks it."""
    feature_dir = build_mission(tmp_path)
    backfill_runtime_state(feature_dir)
    _inject_conflicting_seed(feature_dir)
    # Directly confirm the library verify is genuinely red on this corpus.
    assert verify_backfill(feature_dir).ok is False
    result = rsc.cutover_mission(feature_dir)
    assert result.flipped is False
    assert _STATUS_PHASE not in json.loads((feature_dir / "meta.json").read_text())


def test_verify_tolerates_later_legitimate_latest_wins_annotation(tmp_path: Path) -> None:
    """A post-seed reassignment is runtime history, not conflicting seed data."""
    feature_dir = build_mission(tmp_path)
    backfill_runtime_state(feature_dir)
    append_annotations_atomic_verified(
        feature_dir,
        [
            annotate(
                "WP01",
                WPInnerStateDelta(assignee="later-owner"),
                actor="reviewer",
                at=CLAIMED_AT,
                event_id="7ZZZZZZZZZZZZZZZZZZZZZZZZZ",
            )
        ],
    )

    result = verify_backfill(feature_dir)
    assert result.ok is True, result.mismatches


def test_verify_tolerates_later_value_for_slot_absent_from_legacy_frontmatter(
    tmp_path: Path,
) -> None:
    feature_dir = build_mission(tmp_path)
    wp_path = feature_dir / "tasks" / "WP01-demo.md"
    text = wp_path.read_text(encoding="utf-8")
    wp_path.write_text(
        "\n".join(line for line in text.splitlines() if not line.startswith("assignee:")) + "\n",
        encoding="utf-8",
    )
    backfill_runtime_state(feature_dir)
    emit_inner_state_changed(
        feature_dir,
        "WP01",
        WPInnerStateDelta(assignee="later-owner"),
        actor="reviewer",
        mission_slug=feature_dir.name,
        at="2026-06-02T00:00:00+00:00",
    )

    result = verify_backfill(feature_dir)
    assert result.ok is True, result.mismatches


def test_strip_before_verify_maps_to_error_no_flip(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    backfill_runtime_state(feature_dir)
    strip_mutable_fields(feature_dir)  # removes frontmatter BEFORE verify (ordering violation)
    meta_before = (feature_dir / "meta.json").read_bytes()

    result = rsc.cutover_mission(feature_dir)

    assert result.flipped is False
    assert result.error is not None
    assert "strip_mutable_fields ran before verify" in result.error
    assert (feature_dir / "meta.json").read_bytes() == meta_before


# ---------------------------------------------------------------------------
# cutover_mission — dry-run & idempotency (NFR-002 / INV-4)
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    events_before = (feature_dir / "status.events.jsonl").read_bytes()
    meta_before = (feature_dir / "meta.json").read_bytes()

    result = rsc.cutover_mission(feature_dir, dry_run=True)

    assert result.flipped is False
    assert result.seeded_count > 0  # would-seed count reported
    # would_flip mirrors verify.ok (False on an un-seeded corpus — seeds not written yet).
    assert result.verify is not None
    assert result.would_flip == result.verify.ok
    # Byte-stable: zero events, zero flips.
    assert (feature_dir / "status.events.jsonl").read_bytes() == events_before
    assert (feature_dir / "meta.json").read_bytes() == meta_before


def test_dry_run_after_seed_reports_would_flip(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    backfill_runtime_state(feature_dir)  # seed so verify passes
    events_before = (feature_dir / "status.events.jsonl").read_bytes()
    meta_before = (feature_dir / "meta.json").read_bytes()

    result = rsc.cutover_mission(feature_dir, dry_run=True)

    assert result.flipped is False
    assert result.would_flip is True
    assert result.seeded_count == 0  # already seeded
    assert (feature_dir / "status.events.jsonl").read_bytes() == events_before
    assert (feature_dir / "meta.json").read_bytes() == meta_before


def test_idempotent_rerun_seeds_and_flips_nothing(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path)
    first = rsc.cutover_mission(feature_dir)
    assert first.flipped and first.seeded_count > 0
    events_after = (feature_dir / "status.events.jsonl").read_bytes()
    meta_after = (feature_dir / "meta.json").read_bytes()

    second = rsc.cutover_mission(feature_dir)

    assert second.flipped is True  # already at authority (verify ok)
    assert second.seeded_count == 0
    assert (feature_dir / "status.events.jsonl").read_bytes() == events_after
    assert (feature_dir / "meta.json").read_bytes() == meta_after


# ---------------------------------------------------------------------------
# INV-5 / C-003 — canonical write target, no repo-root write
# ---------------------------------------------------------------------------


def test_flip_target_resolved_via_canonicalize_feature_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The flip must write to ``canonicalize_feature_dir(...)`` — not the raw alias."""
    feature_dir = build_mission(tmp_path)
    # A DISTINCT canonical dir the flip must resolve to (proves canonicalize is used,
    # not Path.cwd() or the raw passed-in path).
    canonical = tmp_path / "canonical-root" / "kitty-specs" / feature_dir.name
    canonical.mkdir(parents=True)
    (canonical / "meta.json").write_text('{"status_phase": 0}\n', encoding="utf-8")
    monkeypatch.setattr(rsc, "canonicalize_feature_dir", lambda fd: canonical)

    result = rsc.cutover_mission(feature_dir)

    assert result.flipped is True
    # The flip landed in the CANONICAL dir...
    assert json.loads((canonical / "meta.json").read_text())[_STATUS_PHASE] == "1"
    # ...and NOT in the raw feature_dir.
    assert _STATUS_PHASE not in json.loads((feature_dir / "meta.json").read_text())


def test_no_repo_root_artifacts_after_cutover(tmp_path: Path) -> None:
    build_mission(tmp_path, slug="alpha")
    build_mission(tmp_path, slug="beta")

    results = rsc.cutover_repo(tmp_path)

    assert {r.slug for r in results} == {"alpha", "beta"}
    assert all(r.flipped for r in results)
    # No stray event log / meta.json at the repo root (#2815 co-constraint).
    assert not (tmp_path / "status.events.jsonl").exists()
    assert not (tmp_path / "meta.json").exists()
    assert not (tmp_path / "kitty-specs" / "status.events.jsonl").exists()


# ---------------------------------------------------------------------------
# cutover_repo — corpus walk
# ---------------------------------------------------------------------------


def test_cutover_repo_walks_whole_corpus(tmp_path: Path) -> None:
    build_mission(tmp_path, slug="alpha")
    build_mission(tmp_path, slug="beta")
    results = rsc.cutover_repo(tmp_path)
    assert sorted(r.slug for r in results) == ["alpha", "beta"]
    assert all(r.flipped for r in results)


def test_cutover_repo_single_mission_scope(tmp_path: Path) -> None:
    build_mission(tmp_path, slug="alpha")
    build_mission(tmp_path, slug="beta")
    results = rsc.cutover_repo(tmp_path, mission_slug="alpha")
    assert [r.slug for r in results] == ["alpha"]


def test_cutover_repo_unknown_mission_is_empty(tmp_path: Path) -> None:
    build_mission(tmp_path, slug="alpha")
    assert rsc.cutover_repo(tmp_path, mission_slug="ghost") == []


@pytest.mark.parametrize("unsafe_slug", ["../outside", "nested/mission", ".", ".."])
def test_cutover_repo_rejects_unsafe_mission_selector(
    tmp_path: Path,
    unsafe_slug: str,
) -> None:
    (tmp_path / "kitty-specs").mkdir()

    with pytest.raises(ValueError, match="safe path segment"):
        rsc.cutover_repo(tmp_path, mission_slug=unsafe_slug)


def test_cutover_repo_rejects_selected_mission_symlink_escape(tmp_path: Path) -> None:
    kitty_specs = tmp_path / "kitty-specs"
    kitty_specs.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (kitty_specs / "escaped").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="outside kitty-specs"):
        rsc.cutover_repo(tmp_path, mission_slug="escaped")


def test_cutover_repo_skips_enumerated_mission_symlink_escape(tmp_path: Path) -> None:
    kitty_specs = tmp_path / "kitty-specs"
    kitty_specs.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (kitty_specs / "escaped").symlink_to(outside, target_is_directory=True)

    assert rsc.cutover_repo(tmp_path) == []
    assert not (outside / "meta.json").exists()


def test_cutover_repo_no_kitty_specs_is_clean_noop(tmp_path: Path) -> None:
    assert rsc.cutover_repo(tmp_path) == []


# ---------------------------------------------------------------------------
# verify_backfill corpus-correctness (WP03-discovered, FR-002 completion)
# ---------------------------------------------------------------------------


def test_verify_never_claimed_wp_warns_not_fails(tmp_path: Path) -> None:
    """Defect 1: a WP with evictable state + a done subtask in tasks.md but ZERO
    transition events (never claimed → no claim anchor) is SKIPPED by the backfill
    and must NOT fail verify (spec Edge Case: never-claimed → warn, not fail)."""
    feature_dir = build_mission(tmp_path)  # WP01 has transitions (anchored)
    # WP02: evictable frontmatter + a done subtask in tasks.md, but no transitions.
    (feature_dir / "tasks" / "WP02-orphan.md").write_text(
        "---\nwork_package_id: WP02\ntitle: Orphan\nagent: ghost:model:profile\nassignee: nobody\n---\n\n# WP02 body\n",
        encoding="utf-8",
    )
    tasks_md = feature_dir / "tasks.md"
    tasks_md.write_text(tasks_md.read_text() + "\n## WP02 Orphan\n- [x] T010 done subtask\n", encoding="utf-8")

    backfill_runtime_state(feature_dir)  # seeds WP01, skips anchor-less WP02
    result = verify_backfill(feature_dir)

    assert result.ok is True
    assert not any("WP02" in m for m in result.mismatches)


def test_verify_tolerates_duplicate_tracker_refs(tmp_path: Path) -> None:
    """Defect 2: a malformed authored tracker_refs with a duplicate ('2') is folded
    by the reducer as a dedup set-union; verify compares as a set, so the benign
    dedup is not a value mismatch."""
    feature_dir = build_mission(tmp_path, tracker_refs=("#", "2", "2", "9", "1"))
    backfill_runtime_state(feature_dir)
    result = verify_backfill(feature_dir)
    assert result.ok is True
    assert not any("tracker_refs" in m for m in result.mismatches)


def test_verify_tolerates_snapshot_ahead_of_legacy(tmp_path: Path) -> None:
    """Defect 3: a WP whose snapshot carries runtime the legacy frontmatter lacks
    (already event-sourced / the actively-running mission) must NOT fail verify."""
    feature_dir = build_mission(tmp_path)
    backfill_runtime_state(feature_dir)
    # A REAL (non-seed) event advances the snapshot beyond the legacy frontmatter:
    # a subtask completion and an assignee change that tasks.md / frontmatter never had.
    real = annotate(
        "WP01",
        WPInnerStateDelta(subtasks={"T003": Lane.DONE}),
        actor="live:agent",
        at=IN_PROGRESS_AT,
        event_id=deterministic_ulid("real-live-event-ahead-of-legacy"),
    )
    append_annotations_atomic_verified(feature_dir, [real])

    result = verify_backfill(feature_dir)
    assert result.ok is True  # snapshot-ahead-of-legacy is a valid already-migrated state


def test_verify_fails_when_anchored_wp_runtime_missing_from_snapshot(tmp_path: Path) -> None:
    """Non-vacuous fail-closed guard: an ANCHORED WP whose legacy runtime never made
    it into the snapshot (genuine data loss) still aborts — the correctness fixes do
    NOT blunt the real count-loss detection."""
    feature_dir = build_mission(tmp_path)  # WP01 anchored + evictable
    # Verify WITHOUT running the backfill: the snapshot has WP01's transitions but
    # none of its seeded runtime slots -> genuine data-loss count mismatch.
    result = verify_backfill(feature_dir)
    assert result.ok is False
    assert any("legacy carries runtime state but snapshot has none" in m for m in result.mismatches)
