"""Tests for the hybrid SCAN stage of ``sync import-history`` — WP-Y2 (#2262).

The SCAN is *hybrid* (§3.4): two mission shapes exist on disk and must both
scan correctly —

* **legacy** — lane transitions only; the creation prefix (mission fields +
  WPs) is SYNTHESIZED from ``meta.json`` + ``tasks/WP*.md`` frontmatter;
* **prefixed** — ``MissionCreated``/``WPCreated`` are read verbatim ON_DISK
  from ``status.events.jsonl``.

Both shapes are built here as synthetic on-disk fixtures under ``tmp_path``
(``_build_legacy_shape_mission`` / ``_build_prefixed_shape_mission``) rather
than pinned to specific ``kitty-specs/`` dogfood missions in this repo: the
dogfood-corpus cutover (#2917) will archive/relocate those directories, and a
mission-keyed ``skipif`` would then silently skip forever instead of failing
(#2884 adversarial-review finding). The builders reproduce the two shapes with
production-realistic data (real ULID-shaped ``mission_id``, realistic WP
frontmatter / on-disk lifecycle payloads) so each test still exercises the
exact discriminating shape it is named for.

The local-only filter and the WPCreated-coverage guard are driven against
smaller synthetic missions so the assertions don't depend on fixture drift.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from specify_cli.status.models import StatusEvent
from specify_cli.sync.history_import.scan import (
    MissionScan,
    MissionScanError,
    PrefixSource,
    _read_importable_lifecycle,
    scan_mission,
    scan_missions,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

# ── fixed ULID-shaped ids (real ``python-ulid`` output, hardcoded for a
# deterministic, production-realistic ``mission_id`` per test) ───────────────
_LEGACY_MISSION_ID = "01KYFV95VETCC5CS96CWFJ9NBF"
_PREFIXED_MISSION_ID = "01KYFV95VETCC5CS96CWFJ9NBG"
_ORDER_LEGACY_MISSION_ID = "01KYFV95VETCC5CS96CWFJ9NBH"
_ORDER_PREFIXED_MISSION_ID = "01KYFV95VETCC5CS96CWFJ9NBJ"
_LANE_EVENT_WP01 = "01KYFV95VETCC5CS96CWFJ9NBK"
_LANE_EVENT_WP02 = "01KYFV95VETCC5CS96CWFJ9NBM"
_LANE_EVENT_WP03 = "01KYFV95VETCC5CS96CWFJ9NBN"


# ── synthetic dual-shape fixture builders ─────────────────────────────────────


def _lane_transition_row(
    *,
    mission_id: str,
    mission_slug: str,
    wp_id: str,
    to_lane: str,
    event_id: str,
    from_lane: str = "planned",
    at: str = "2026-02-07T00:00:00Z",
) -> dict:
    """One realistic lane-transition row, matching the on-disk StatusEvent shape."""
    return {
        "actor": "migration",
        "at": at,
        "event_id": event_id,
        "evidence": None,
        "execution_mode": "direct_repo",
        "force": True,
        "from_lane": from_lane,
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "policy_metadata": None,
        "reason": "historical_frontmatter_to_jsonl:v1",
        "review_ref": None,
        "to_lane": to_lane,
        "wp_id": wp_id,
    }


def _write_events(mission_dir: Path, rows: list[dict]) -> None:
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "status.events.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _append_raw_jsonl_line(mission_dir: Path, raw_json_line: str) -> None:
    """Append one literal JSON-text line to ``status.events.jsonl``.

    For fixture rows that are deliberately malformed (the shape a canonical
    ``spec_kitty_events.lifecycle.*Payload`` model cannot represent by
    definition — that is the point of the test). Writing the line as a
    Python ``str`` literal rather than a hand-rolled ``dict`` keeps the
    fixture faithful to "malformed on-disk bytes" as the actual unit under
    test, and gives the canonical-producer AST lint nothing event-shaped to
    flag (there is no ``ast.Dict`` literal carrying ``event_type``/``payload``
    keys — only opaque text).
    """
    mission_dir.mkdir(parents=True, exist_ok=True)
    path = mission_dir / "status.events.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(raw_json_line + "\n")


def _build_legacy_shape_mission(
    tmp_path: Path,
    *,
    slug: str,
    mission_id: str,
    friendly_name: str = "Legacy Shape Mission",
    mission_number: int = 87,
    source_description: str = "Make CLI events identity-aware and auto-syncing so multiple local projects appear in SaaS dashboards.",
    target_branch: str = "main",
    wp_specs: Sequence[tuple[str, str, list[str]]] = (),
    lane_rows: Sequence[dict] = (),
) -> Path:
    """Build the LEGACY on-disk shape: ``meta.json`` + ``tasks/WP*.md``
    frontmatter, a lane-transitions-ONLY ``status.events.jsonl`` (no on-disk
    ``MissionCreated``/``WPCreated`` prefix) — the SYNTHESIZED half of the
    hybrid-SCAN dual-shape guarantee (§3.4).
    """
    mission_dir = tmp_path / "kitty-specs" / slug
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    meta = {
        "created_at": "2026-02-07T00:00:00Z",
        "friendly_name": friendly_name,
        "mission_id": mission_id,
        "mission_number": mission_number,
        "mission_slug": slug,
        "mission_type": "software-dev",
        "slug": slug,
        "source_description": source_description,
        "status_phase": "1",
        "target_branch": target_branch,
        "vcs": "git",
    }
    (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    for wp_id, title, deps in wp_specs:
        frontmatter = "\n".join(
            [
                "---",
                f"work_package_id: {wp_id}",
                f"title: {title}",
                f"dependencies: {json.dumps(deps)}",
                f"base_branch: {target_branch}",
                "base_commit: fe5dd26eb9160377ee55f83b072f5dc3db322843",
                "created_at: '2026-02-07T07:23:14.221357+00:00'",
                "subtasks:",
                "- T001",
                "- T002",
                "phase: Phase 0 - Foundation",
                "history:",
                "- timestamp: '2026-02-07T00:00:00Z'",
                "  lane: planned",
                "  agent: system",
                "  shell_pid: ''",
                "---",
                "",
                f"# {title}",
                "",
            ]
        )
        file_slug = title.lower().replace(" ", "-").replace("/", "-")
        (tasks_dir / f"{wp_id}-{file_slug}.md").write_text(frontmatter, encoding="utf-8")
    if lane_rows:
        _write_events(mission_dir, list(lane_rows))
    return mission_dir


def _build_prefixed_shape_mission(
    tmp_path: Path,
    *,
    slug: str,
    mission_id: str,
    friendly_name: str = "Prefixed Shape Mission",
    purpose_tldr: str = "Collapse the parallel resolvers into one canonical resolver.",
    purpose_context: str = "Several commands resolve the wrong directory when surfaces diverge.",
    target_branch: str = "main",
    created_at: str = "2026-06-19T16:46:47.321621+00:00",
    wp_specs: Sequence[tuple[str, str, list[str], str, str]] = (),
) -> Path:
    """Build the PREFIXED on-disk shape via the canonical local emitters: a
    real ``MissionCreated`` + ``WPCreated[]`` lifecycle prefix on disk — the
    ON_DISK half of the hybrid-SCAN dual-shape guarantee (§3.4).

    ``wp_specs`` entries are ``(wp_id, title, depends_on, wp_path, created_at)``.
    """
    from specify_cli.status.lifecycle_events import (
        emit_mission_created_local,
        emit_wp_created_local,
    )

    mission_dir = tmp_path / "kitty-specs" / slug
    mission_dir.mkdir(parents=True)
    emit_mission_created_local(
        mission_dir,
        mission_slug=slug,
        mission_id=mission_id,
        mission_number=None,
        mission_type="software-dev",
        target_branch=target_branch,
        wp_count=len(wp_specs),
        friendly_name=friendly_name,
        purpose_tldr=purpose_tldr,
        purpose_context=purpose_context,
        created_at=created_at,
    )
    for wp_id, title, depends_on, wp_path, wp_created_at in wp_specs:
        emit_wp_created_local(
            mission_dir,
            mission_slug=slug,
            wp_id=wp_id,
            wp_title=title,
            wp_path=wp_path,
            depends_on=depends_on,
            created_at=wp_created_at,
        )
    return mission_dir


# ── legacy shape: prefix SYNTHESIZED from meta.json + tasks/ ──────────────────

_LEGACY_WP_SPECS = [
    ("WP01", "ProjectIdentity Module", []),
    ("WP02", "Emitter Identity Injection", ["WP01"]),
    ("WP03", "AuthClient Team Slug", ["WP01"]),
    ("WP04", "Sync Runtime Lazy Singleton", ["WP02"]),
    ("WP05", "Fix Duplicate Emissions", ["WP02", "WP03"]),
    ("WP06", "Integration Tests", ["WP04", "WP05"]),
]


def test_legacy_mission_synthesizes_prefix_from_meta_and_tasks(tmp_path):
    lane_rows = [
        _lane_transition_row(
            mission_id=_LEGACY_MISSION_ID,
            mission_slug="087-legacy-shape-mission",
            wp_id="WP01",
            to_lane="done",
            event_id=_LANE_EVENT_WP01,
        ),
        _lane_transition_row(
            mission_id=_LEGACY_MISSION_ID,
            mission_slug="087-legacy-shape-mission",
            wp_id="WP02",
            to_lane="done",
            event_id=_LANE_EVENT_WP02,
        ),
        _lane_transition_row(
            mission_id=_LEGACY_MISSION_ID,
            mission_slug="087-legacy-shape-mission",
            wp_id="WP03",
            to_lane="in_progress",
            event_id=_LANE_EVENT_WP03,
        ),
    ]
    mission_dir = _build_legacy_shape_mission(
        tmp_path,
        slug="087-legacy-shape-mission",
        mission_id=_LEGACY_MISSION_ID,
        friendly_name="Identity-Aware CLI Event Sync",
        mission_number=87,
        source_description="Make CLI events identity-aware and auto-syncing so multiple local projects appear in SaaS dashboards.",
        wp_specs=_LEGACY_WP_SPECS,
        lane_rows=lane_rows,
    )

    scan = scan_mission(mission_dir)

    assert scan.prefix_source is PrefixSource.SYNTHESIZED
    # Identity + display fields resolve from meta.json (verbatim values).
    assert scan.canonical_mission_id == _LEGACY_MISSION_ID
    assert scan.mission_slug == "087-legacy-shape-mission"
    assert scan.name == "Identity-Aware CLI Event Sync"
    assert scan.mission_number == 87
    assert scan.mission_type == "software-dev"
    # Legacy has no purpose_tldr; source_description back-fills it.
    assert scan.purpose_tldr and scan.purpose_tldr.startswith("Make CLI events identity-aware")

    # WPs synthesized from tasks/WP01..WP06.md, each with a non-empty title.
    wp_ids = {wp.wp_id for wp in scan.work_packages}
    assert {"WP01", "WP02", "WP03", "WP04", "WP05", "WP06"} <= wp_ids
    assert all(wp.source is PrefixSource.SYNTHESIZED for wp in scan.work_packages)
    assert all(wp.wp_title for wp in scan.work_packages)

    # Lane transitions are read (and are real StatusEvents), and every wp_id
    # they reference has a WPCreated (INV-3 coverage).
    assert scan.lane_transitions
    assert all(isinstance(event, StatusEvent) for event in scan.lane_transitions)
    lane_wp_ids = {event.wp_id for event in scan.lane_transitions if event.wp_id}
    assert lane_wp_ids <= wp_ids


# ── prefixed shape: prefix read ON_DISK ───────────────────────────────────────

_PREFIXED_SLUG = "single-mission-surface-resolver-01KYFV95"
_PREFIXED_WP_SPECS = [
    (
        "WP01",
        "Surface-resolution audit (read-only inventory)",
        [],
        f"kitty-specs/{_PREFIXED_SLUG}/tasks/WP01-surface-resolution-audit.md",
        "2026-06-19T17:11:46.841180Z",
    ),
    (
        "WP02",
        "Differential equivalence test (the deletion safety gate)",
        [],
        f"kitty-specs/{_PREFIXED_SLUG}/tasks/WP02-differential-equivalence-test.md",
        "2026-06-19T17:11:46.855890Z",
    ),
    (
        "WP08",
        "Load-bearing architectural guard",
        ["WP01", "WP06"],
        f"kitty-specs/{_PREFIXED_SLUG}/tasks/WP08-load-bearing-guard.md",
        "2026-06-19T17:11:46.833815Z",
    ),
]


def test_prefixed_mission_reads_prefix_from_disk(tmp_path):
    mission_dir = _build_prefixed_shape_mission(
        tmp_path,
        slug=_PREFIXED_SLUG,
        mission_id=_PREFIXED_MISSION_ID,
        friendly_name="Single Mission-Surface Resolver",
        purpose_tldr=(
            "Collapse the 4+ parallel coord/primary mission-surface resolvers into "
            "one canonical resolver so every command agrees which on-disk surface "
            "is authoritative."
        ),
        purpose_context=(
            "When a mission's coordination worktree and primary checkout diverge, "
            "several commands resolve the wrong directory."
        ),
        target_branch="feat/single-mission-surface-resolver",
        wp_specs=_PREFIXED_WP_SPECS,
    )

    scan = scan_mission(mission_dir)

    assert scan.prefix_source is PrefixSource.ON_DISK
    assert scan.canonical_mission_id == _PREFIXED_MISSION_ID
    assert scan.name == "Single Mission-Surface Resolver"

    by_id = {wp.wp_id: wp for wp in scan.work_packages}
    # WP08's on-disk WPCreated payload is read verbatim (title + depends_on).
    assert "WP08" in by_id
    wp08 = by_id["WP08"]
    assert wp08.source is PrefixSource.ON_DISK
    assert wp08.wp_title == "Load-bearing architectural guard"
    assert set(wp08.depends_on) == {"WP01", "WP06"}


# ── local-only lifecycle events are dropped ───────────────────────────────────


def test_local_only_lifecycle_events_are_filtered(tmp_path):
    mission_dir = tmp_path / "synthetic-filter-01AAAA"
    _write_events(
        mission_dir,
        [
            # canonical-event-exempt(exception-flow): on-disk lifecycle row fed into the drop-filter under test
            {"event_type": "MissionCreated", "aggregate_type": "Mission", "payload": {}},
            # canonical-event-exempt(exception-flow): local-only row the filter must drop
            {"event_type": "MissionReopened", "aggregate_type": "Mission", "payload": {}},
            # canonical-event-exempt(exception-flow): local-only row the filter must drop
            {"event_type": "FollowUpRecorded", "aggregate_type": "Mission", "payload": {}},
            # canonical-event-exempt(exception-flow): on-disk lifecycle row fed into the drop-filter under test
            {"event_type": "WPCreated", "aggregate_type": "WorkPackage", "payload": {"wp_id": "WP01"}},
        ],
    )

    kept = {event["event_type"] for event in _read_importable_lifecycle(mission_dir)}
    assert kept == {"MissionCreated", "WPCreated"}
    assert "MissionReopened" not in kept
    assert "FollowUpRecorded" not in kept


# ── WPCreated coverage guard (INV-3) ──────────────────────────────────────────


def test_wp_coverage_backfills_a_wp_referenced_only_by_a_lane_transition(tmp_path):
    """A lane transition for a WP with no task file / no WPCreated still yields
    a WPCreated, so ``WPStatusChanged`` never precedes ``WPCreated``."""
    mission_dir = tmp_path / "synthetic-cov-01BBBB"
    _write_events(
        mission_dir,
        [
            {
                "actor": "migration",
                "at": "2026-02-07T00:00:00Z",
                "event_id": "01KJ5V38V9HRA67BAXKNQDWP99",
                "evidence": None,
                "execution_mode": "direct_repo",
                "force": False,
                "from_lane": "planned",
                "mission_id": None,
                "mission_slug": "synthetic-cov-01BBBB",
                "policy_metadata": None,
                "reason": None,
                "review_ref": None,
                "to_lane": "in_progress",
                "wp_id": "WP99",
            }
        ],
    )

    scan = scan_mission(mission_dir)

    assert scan.lane_transitions and scan.lane_transitions[0].wp_id == "WP99"
    by_id = {wp.wp_id: wp for wp in scan.work_packages}
    assert "WP99" in by_id, "lane-only WP must be backfilled with a WPCreated"
    assert by_id["WP99"].wp_title == "WP99"
    assert by_id["WP99"].source is PrefixSource.SYNTHESIZED
    assert by_id["WP99"].depends_on == ()


def test_work_packages_are_sorted_by_wp_id(tmp_path):
    # Emit WPCreated out of order via the canonical local emitter (not a
    # hand-rolled event); the scan must return them sorted by wp_id.
    from specify_cli.status.lifecycle_events import emit_wp_created_local

    mission_dir = tmp_path / "synthetic-sort-01CCCC"
    mission_dir.mkdir(parents=True)
    for wp_id in ("WP03", "WP01", "WP02"):
        emit_wp_created_local(mission_dir, mission_slug="synthetic-sort-01CCCC", wp_id=wp_id, wp_title=wp_id)

    scan = scan_mission(mission_dir)
    assert [wp.wp_id for wp in scan.work_packages] == ["WP01", "WP02", "WP03"]


# ── batch helper ──────────────────────────────────────────────────────────────


def test_scan_missions_preserves_input_order(tmp_path):
    """SCAN's batch helper preserves caller-given order across BOTH hybrid
    shapes (§3.4) — not an accident of alphabetic sort."""
    legacy_dir = _build_legacy_shape_mission(
        tmp_path,
        slug="087-order-legacy-mission",
        mission_id=_ORDER_LEGACY_MISSION_ID,
        friendly_name="Order Legacy Mission",
    )
    prefixed_dir = _build_prefixed_shape_mission(
        tmp_path,
        slug="order-prefixed-mission-01KYFV95",
        mission_id=_ORDER_PREFIXED_MISSION_ID,
        friendly_name="Order Prefixed Mission",
    )

    scans = scan_missions([prefixed_dir, legacy_dir])
    assert [scan.mission_slug for scan in scans] == [
        "order-prefixed-mission-01KYFV95",
        "087-order-legacy-mission",
    ]
    assert all(isinstance(scan, MissionScan) for scan in scans)


# ── malformed WP frontmatter must not abort the scan (#2883 items 3/4) ────────


def test_corrupt_status_log_raises_named_mission_scan_error(tmp_path):
    """A corrupt status.events.jsonl fails closed as MissionScanError naming the
    mission, not a raw StoreError traceback (Stijn's #2884 review, fix #3)."""
    mission_dir = tmp_path / "synthetic-corrupt-01GGGG"
    mission_dir.mkdir(parents=True)
    # A structurally-broken lane row (not a lifecycle event_type row, so it
    # reaches the lane reader) that read_events rejects with StoreError.
    (mission_dir / "status.events.jsonl").write_text("{ this is not valid json\n", encoding="utf-8")

    with pytest.raises(MissionScanError) as excinfo:
        scan_mission(mission_dir)
    assert "synthetic-corrupt-01GGGG" in str(excinfo.value)


def test_malformed_wp_frontmatter_is_skipped_not_fatal(tmp_path):
    """A WP file whose frontmatter parses to a list (not a dict) raises a
    structural TypeError inside the reader. The scan must skip it, not abort —
    otherwise one bad legacy doc sinks the whole import. The skip is fail-LOUD:
    the scan result carries the skipped file names so the report can surface
    them (B3, #2884 review)."""
    mission_dir = tmp_path / "synthetic-malformed-01FFFF"
    tasks = mission_dir / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "WP01-bad.md").write_text("---\n- a\n- b\n---\nbody\n", encoding="utf-8")
    (tasks / "WP02-good.md").write_text(
        "---\nwork_package_id: WP02\ntitle: Good WP\ndependencies: []\n---\nbody\n",
        encoding="utf-8",
    )

    scan = scan_mission(mission_dir)  # must not raise

    # The skip is counted AND named — never silent.
    assert scan.skipped_wp_files == ("WP01-bad.md",)
    # The good sibling still scans (skip is per-file, not per-mission).
    assert [wp.wp_id for wp in scan.work_packages] == ["WP02"]


def test_legacy_wp_with_retired_frontmatter_field_imports_not_skipped(tmp_path):
    """A WP carrying a retired frontmatter field (e.g. `estimated_lines`) must
    import as a real synthesized WP — with its true title and dependencies —
    not get rejected by `extra="forbid"` and degraded to a bare back-fill.

    Regression for FR-011 (#3406): historical missions legitimately carry fields
    the current schema no longer knows; the strict authoring reader rejected the
    whole WP, so the import lost its title/deps. The lenient import reader drops
    the unknown key while preserving everything the schema still understands.
    """
    mission_dir = tmp_path / "synthetic-legacy-fields-01IIII"
    tasks = mission_dir / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "WP01-legacy.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Legacy WP With Retired Fields\n"
        "dependencies: []\n"
        "estimated_lines: 240\n"  # retired field — must not sink the WP
        "some_other_dead_key: whatever\n"
        "---\nbody\n",
        encoding="utf-8",
    )

    scan = scan_mission(mission_dir)  # must not raise

    # Not skipped, not back-filled — imported as a real synthesized WP.
    assert scan.skipped_wp_files == ()
    by_id = {wp.wp_id: wp for wp in scan.work_packages}
    assert "WP01" in by_id
    assert by_id["WP01"].wp_title == "Legacy WP With Retired Fields"
    assert by_id["WP01"].source is PrefixSource.SYNTHESIZED


def test_malformed_wp_referenced_by_a_lane_transition_is_backfilled_no_orphan(tmp_path):
    """A WP whose task file is malformed (skipped) but which a lane transition
    references must still get a WPCreated via coverage backfill — the exact spot
    an orphan WPStatusChanged would appear if _ensure_wp_coverage regressed."""
    mission_dir = tmp_path / "synthetic-orphan-01HHHH"
    tasks = mission_dir / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "WP01-bad.md").write_text("---\n- a\n- b\n---\nbody\n", encoding="utf-8")  # malformed → skipped
    _write_events(
        mission_dir,
        [
            {
                "actor": "migration",
                "at": "2026-02-07T00:00:00Z",
                "event_id": "01KJ5V38V9HRA67BAXKNQDWP01",
                "evidence": None,
                "execution_mode": "direct_repo",
                "force": False,
                "from_lane": "planned",
                "mission_id": None,
                "mission_slug": "synthetic-orphan-01HHHH",
                "policy_metadata": None,
                "reason": None,
                "review_ref": None,
                "to_lane": "in_progress",
                "wp_id": "WP01",
            }
        ],
    )

    scan = scan_mission(mission_dir)

    by_id = {wp.wp_id: wp for wp in scan.work_packages}
    assert "WP01" in by_id, "malformed-but-referenced WP must be backfilled, not orphaned"
    assert by_id["WP01"].source is PrefixSource.SYNTHESIZED
    # Every wp_id a lane transition references is covered (INV-3).
    assert {event.wp_id for event in scan.lane_transitions} <= set(by_id)


# ── malformed lifecycle rows must be counted, not silently dropped (#2884 A) ──


def test_malformed_event_type_row_is_counted_as_a_skipped_event_row(tmp_path):
    """A row with a null (non-string) ``event_type`` is the genuinely silent
    failure mode named in the review: valid JSON, so ``read_events`` (the
    lane-transition reader) treats it as a skippable non-lane row and does
    NOT fail closed the whole scan — but ``read_lifecycle_events`` also drops
    it (its ``event_type`` isn't a ``str``), so a ``WPCreated`` row shaped
    like this vanishes from BOTH readers with no signal at all. The scan must
    count it (#2884 finding A) so a partial import is loud, not silent."""
    from specify_cli.status.lifecycle_events import emit_mission_created_local

    mission_dir = tmp_path / "synthetic-truncated-01JJJJ"
    mission_dir.mkdir(parents=True)
    emit_mission_created_local(
        mission_dir,
        mission_slug="synthetic-truncated-01JJJJ",
        mission_id=None,
        mission_number=None,
        mission_type="software-dev",
        target_branch="main",
        wp_count=0,
    )
    # Deliberately malformed on-disk WPCreated row under test — null
    # event_type is valid JSON but not a lifecycle row `read_lifecycle_events`
    # will keep. A canonical *Payload model cannot represent this shape (that
    # is the point), so the raw bytes are appended as a literal JSON-text line.
    _append_raw_jsonl_line(
        mission_dir,
        '{"event_type": null, "aggregate_type": "WorkPackage", "payload": {"wp_id": "WP01"}}',
    )

    scan = scan_mission(mission_dir)

    assert scan.skipped_event_rows == 1
    # The mission still scans successfully (fail-loud, not fail-closed) and
    # the malformed WPCreated row truly never reaches work_packages.
    assert scan.prefix_source is PrefixSource.ON_DISK
    assert scan.work_packages == ()


def test_wp_created_payload_with_no_wp_id_is_counted_not_silently_dropped(tmp_path):
    """``_wps_from_prefix``'s ``if not wp_id: continue`` used to drop the row
    with no log and no count. It must now be counted into
    ``skipped_event_rows`` (#2884 finding A)."""
    from specify_cli.status.lifecycle_events import (
        emit_mission_created_local,
        emit_wp_created_local,
    )

    mission_dir = tmp_path / "synthetic-no-wpid-01KKKK"
    mission_dir.mkdir(parents=True)
    emit_mission_created_local(
        mission_dir,
        mission_slug="synthetic-no-wpid-01KKKK",
        mission_id=None,
        mission_number=None,
        mission_type="software-dev",
        target_branch="main",
        wp_count=1,
    )
    # Deliberately malformed on-disk WPCreated row missing wp_id under test —
    # WPCreatedPayload requires wp_id, so a canonical model cannot construct
    # this shape (that is the point); appended as a literal JSON-text line.
    _append_raw_jsonl_line(
        mission_dir,
        '{"event_type": "WPCreated", "aggregate_type": "WorkPackage", "payload": {"wp_title": "No id here"}}',
    )
    emit_wp_created_local(
        mission_dir,
        mission_slug="synthetic-no-wpid-01KKKK",
        wp_id="WP01",
        wp_title="Good",
    )

    scan = scan_mission(mission_dir)

    assert scan.skipped_event_rows == 1
    assert [wp.wp_id for wp in scan.work_packages] == ["WP01"]


def test_no_malformed_rows_yields_zero_skipped_event_rows(tmp_path):
    """The common case: a clean lifecycle prefix counts zero skips."""
    from specify_cli.status.lifecycle_events import (
        emit_mission_created_local,
        emit_wp_created_local,
    )

    mission_dir = tmp_path / "synthetic-clean-01LLLL"
    emit_mission_created_local(
        mission_dir,
        mission_slug="synthetic-clean-01LLLL",
        mission_id=None,
        mission_number=None,
        mission_type="software-dev",
        target_branch="main",
        wp_count=1,
    )
    emit_wp_created_local(
        mission_dir,
        mission_slug="synthetic-clean-01LLLL",
        wp_id="WP01",
        wp_title="WP01",
    )

    scan = scan_mission(mission_dir)

    assert scan.skipped_event_rows == 0


def test_local_only_event_types_have_one_public_owner() -> None:
    """SSOT (#2884): scan's local-only filter and lifecycle's post-mission set are
    the SAME public owner object — no hand-mirrored frozenset copies to drift."""
    from specify_cli.status import (
        FOLLOW_UP_RECORDED,
        LOCAL_ONLY_LIFECYCLE_EVENT_TYPES,
        MISSION_REOPENED,
    )
    from specify_cli.status.lifecycle import _POST_MISSION_EVENT_TYPES
    from specify_cli.sync.history_import.scan import _LOCAL_ONLY_EVENT_TYPES

    # actual == expected (conventional order, #2884 finding D). Bound to local
    # names first: ruff's SIM300 (Yoda-condition) heuristic treats an ALL_CAPS
    # name compared directly against a set literal as a constant-on-the-left
    # false positive, so the operands are named here instead of inlined.
    actual_local_only_types = LOCAL_ONLY_LIFECYCLE_EVENT_TYPES
    expected_local_only_types = frozenset({MISSION_REOPENED, FOLLOW_UP_RECORDED})
    assert actual_local_only_types == expected_local_only_types
    # Identity (``is``), not just equality: both consumers bind the one owner.
    assert _LOCAL_ONLY_EVENT_TYPES is LOCAL_ONLY_LIFECYCLE_EVENT_TYPES
    assert _POST_MISSION_EVENT_TYPES is LOCAL_ONLY_LIFECYCLE_EVENT_TYPES
