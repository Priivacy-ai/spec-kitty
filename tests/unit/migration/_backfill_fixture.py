"""Shared corpus builder for the WP03 backfill/verify tests.

Constructs a self-contained mission on disk: ``meta.json``, a ``tasks/WP*.md``
frontmatter carrying the pre-eviction runtime state (``shell_pid`` / ``agent`` /
``assignee`` / ``tracker_refs`` / ``review_artifact_override_*`` / ``history``), a
``tasks.md`` with per-WP checkbox subtasks, and a ``status.events.jsonl`` with the
real ``planned -> claimed -> in_progress`` transitions the claim-anchor derives
from. Both the unit and integration suites import this so the fixture shape lives
in exactly one place.
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.migration.mission_state import deterministic_ulid

MISSION_ID = "01JMISSIONULID0000000000AA"
SLUG = "042-demo"
CLAIMED_AT = "2026-01-02T03:04:05+00:00"
IN_PROGRESS_AT = "2026-01-02T04:00:00+00:00"


def corrupt_seed_value(
    feature_dir: Path,
    *,
    field_name: str,
    slot_name: str,
    value: object,
) -> None:
    """Mutate one deterministic migration seed payload in place for fault tests."""
    meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    seed_id = str(
        deterministic_ulid(
            f"{meta['mission_id']}|WP01|{field_name}"
        )
    )
    events_path = feature_dir / "status.events.jsonl"
    rows = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    matched = False
    for row in rows:
        if row.get("event_id") != seed_id:
            continue
        container_name = "policy_metadata" if field_name == "claim" else "delta"
        row[container_name][slot_name] = value
        matched = True
        break
    assert matched, f"deterministic {field_name!r} seed not found"
    events_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _transition(
    *, event_id: str, slug: str, mission_id: str, wp: str, frm: str, to: str, at: str
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "mission_slug": slug,
        "mission_id": mission_id,
        "wp_id": wp,
        "from_lane": frm,
        "to_lane": to,
        "at": at,
        "actor": "tester",
        "force": False,
        "execution_mode": "worktree",
    }


def build_mission(
    tmp_path: Path,
    *,
    slug: str = SLUG,
    mission_id: str = MISSION_ID,
    shell_pid: int = 44821,
    shell_pid_created_at: str = "1784458183.44",
    agent: str = "claude:opus:pedro",
    assignee: str = "pedro",
    tracker_refs: tuple[str, ...] = ("JIRA-1", "JIRA-2"),
    with_review: bool = True,
    with_history: bool = True,
    with_transitions: bool = True,
    with_claim: bool = True,
    meta_created_at: str | None = None,
    claimed_at: str = CLAIMED_AT,
) -> Path:
    """Materialise a mission corpus and return its feature directory.

    ``with_claim=False`` omits ``shell_pid`` / ``shell_pid_created_at`` /
    ``agent`` from WP01's frontmatter — a genuinely never-claimed WP (as opposed
    to one whose claim anchor must be synthesized from those very fields; see
    ``backfill_runtime_state._resolve_anchor``). ``meta_created_at`` optionally
    seeds ``meta.json``'s ``created_at`` (the claim-anchor synthesis fallback
    when ``shell_pid_created_at`` itself is absent/unparseable).
    """
    feature_dir = tmp_path / "kitty-specs" / slug
    tasks = feature_dir / "tasks"
    tasks.mkdir(parents=True)

    meta: dict[str, str] = {"mission_id": mission_id, "mission_slug": slug, "mission_type": "software-dev"}
    if meta_created_at is not None:
        meta["created_at"] = meta_created_at
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    fm: list[str] = [
        "---",
        "work_package_id: WP01",
        "title: Demo WP",
        "execution_mode: code_change",
    ]
    if with_claim:
        fm += [
            f"shell_pid: {shell_pid}",
            f'shell_pid_created_at: "{shell_pid_created_at}"',
            f"agent: {agent}",
        ]
    fm += [
        f"assignee: {assignee}",
        "tracker_refs:",
        *[f"  - {ref}" for ref in tracker_refs],
    ]
    if with_review:
        fm += [
            'review_artifact_override_at: "2026-01-03T00:00:00+00:00"',
            "review_artifact_override_actor: renata",
            "review_artifact_override_wp_id: WP01",
            "review_artifact_override_reason: manual override",
        ]
    if with_history:
        fm += ["history:", "  - action: claimed"]
    fm += ["---", "", "# WP01 body", ""]
    (tasks / "WP01-demo.md").write_text("\n".join(fm), encoding="utf-8")

    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP01 Demo\n- [x] T001 first subtask\n- [ ] T002 second subtask\n",
        encoding="utf-8",
    )

    if with_transitions:
        events = [
            _transition(
                event_id="01AAAAAAAAAAAAAAAAAAAAAAA1",
                slug=slug,
                mission_id=mission_id,
                wp="WP01",
                frm="planned",
                to="claimed",
                at=claimed_at,
            ),
            _transition(
                event_id="01AAAAAAAAAAAAAAAAAAAAAAA2",
                slug=slug,
                mission_id=mission_id,
                wp="WP01",
                frm="claimed",
                to="in_progress",
                at=IN_PROGRESS_AT,
            ),
        ]
        (feature_dir / "status.events.jsonl").write_text(
            "\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n",
            encoding="utf-8",
        )

    return feature_dir
