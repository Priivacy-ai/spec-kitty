#!/usr/bin/env python3
"""Build frozen atomic query truth from exact baseline byte literals."""

from __future__ import annotations

import csv
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

REVISION = "cf0f7e3a7"


@dataclass(frozen=True)
class Atom:
    atom_id: str
    query_id: str
    fixture_id: str
    atom_type: str
    subject: str
    predicate: str
    object_: str
    path: str
    literal: str
    occurrence: int = 0
    critical: str = "yes"


ATOMS = [
    Atom(
        "A001",
        "Q1",
        "F-EXEC-WP12",
        "reference",
        "exec:WP12",
        "implements",
        "exec:FR-015",
        "kitty-specs/execution-context-unification-01KTPKST/tasks/WP12-sync-daemon-singleton-reaper.md",
        "- FR-015",
    ),
    Atom(
        "A002",
        "Q1",
        "F-EXEC-WP12",
        "verdict",
        "exec:WP12",
        "review_verdict",
        "approved",
        "kitty-specs/execution-context-unification-01KTPKST/tasks/WP12-sync-daemon-singleton-reaper/review-cycle-2.md",
        "verdict: approved",
    ),
    Atom(
        "A003",
        "Q1",
        "F-EXEC-WP12",
        "proof",
        "exec:WP12",
        "pytest_result",
        "8 passed:SC-7_3-to-1-collapse",
        "kitty-specs/execution-context-unification-01KTPKST/tasks/WP12-sync-daemon-singleton-reaper/review-cycle-2.md",
        "`python -m pytest tests/sync/test_daemon_singleton_reaper_consolidation.py -q`\n"
        "  → **8 passed** (SC-6b reaper-over-kill scope guard + SC-7 3→1 collapse\n"
        "  source-inspection tests)",
    ),
    Atom(
        "A004",
        "Q1",
        "F-EXEC-WP12",
        "acceptance",
        "exec:mission",
        "accepted_at",
        "2026-06-10T05:45:00.743647+00:00",
        "kitty-specs/execution-context-unification-01KTPKST/meta.json",
        '"accepted_at": "2026-06-10T05:45:00.743647+00:00"',
        1,
    ),
    Atom(
        "A005",
        "Q2",
        "F-WORKTREE-WP02",
        "dependency",
        "worktree:WP02",
        "depends_on",
        "worktree:WP01",
        "kitty-specs/worktree-owned-root-3328-01KZRG01/tasks/WP02-mission-create-integration.md",
        "- WP01",
    ),
    Atom(
        "A006",
        "Q2",
        "F-WORKTREE-WP02",
        "constraint",
        "worktree:WP02",
        "merge_target",
        "fix/worktree-owned-root-3328-v2",
        "kitty-specs/worktree-owned-root-3328-01KZRG01/tasks/WP02-mission-create-integration.md",
        "merge_target_branch: fix/worktree-owned-root-3328-v2",
    ),
    Atom(
        "A007",
        "Q3",
        "F-WORKTREE-WP02",
        "reference",
        "worktree:FR-001",
        "implemented_by",
        "worktree:WP02",
        "kitty-specs/worktree-owned-root-3328-01KZRG01/tasks/WP02-mission-create-integration.md",
        "- FR-001",
    ),
    Atom(
        "A008",
        "Q3",
        "F-WORKTREE-WP02",
        "ownership",
        "worktree:WP02",
        "owns",
        "src/specify_cli/cli/commands/agent/mission_create.py",
        "kitty-specs/worktree-owned-root-3328-01KZRG01/tasks/WP02-mission-create-integration.md",
        "- src/specify_cli/cli/commands/agent/mission_create.py",
    ),
    Atom(
        "A009",
        "Q3",
        "F-WORKTREE-WP02",
        "ownership",
        "worktree:WP02",
        "owns",
        "src/specify_cli/core/mission_creation.py",
        "kitty-specs/worktree-owned-root-3328-01KZRG01/tasks/WP02-mission-create-integration.md",
        "- src/specify_cli/core/mission_creation.py",
    ),
    Atom(
        "A010",
        "Q3",
        "F-WORKTREE-WP02",
        "ownership",
        "worktree:WP02",
        "owns",
        "src/mission_runtime/__init__.py",
        "kitty-specs/worktree-owned-root-3328-01KZRG01/tasks/WP02-mission-create-integration.md",
        "- src/mission_runtime/__init__.py",
    ),
    Atom(
        "A011",
        "Q3",
        "F-WORKTREE-WP02",
        "ownership",
        "worktree:WP02",
        "owns",
        "tests/mission_runtime/test_create_time_write_target.py",
        "kitty-specs/worktree-owned-root-3328-01KZRG01/tasks/WP02-mission-create-integration.md",
        "- tests/mission_runtime/test_create_time_write_target.py",
        1,
    ),
    Atom(
        "A012",
        "Q4",
        "F-GATE-PREPLAN",
        "decision",
        "gate-read:plan",
        "sizing_verdict",
        "one mission; two explicit lanes",
        "kitty-specs/gate-read-surface-completion-01KVW9B0/research/priti-preplan.md",
        "## 1. Sizing verdict: ONE mission, TWO explicit lanes",
    ),
    Atom(
        "A013",
        "Q4",
        "F-GATE-PREPLAN",
        "support",
        "gate-read:lane-a",
        "root_cause",
        "#2107 at mission.py:2203-2224",
        "kitty-specs/gate-read-surface-completion-01KVW9B0/research/priti-preplan.md",
        "a single root cause (#2107 live-reproduced at `mission.py:2203-2224`)",
    ),
    Atom(
        "A014",
        "Q4",
        "F-GATE-PREPLAN",
        "countercase",
        "gate-read:split",
        "cost",
        "extra mission overhead for 3-5 tests and one fixture re-pin",
        "kitty-specs/gate-read-surface-completion-01KVW9B0/research/priti-preplan.md",
        "A separate mission adds overhead (spec/plan/tasks cycle) for ~3–5 tests and one fixture re-pin.",
    ),
    Atom(
        "A015",
        "Q5",
        "F-EXEC-LIFECYCLE",
        "requirement_status",
        "exec:FR-015",
        "status",
        "Draft",
        "kitty-specs/execution-context-unification-01KTPKST/spec.md",
        "| FR-015 | **Collapse the duplicate daemon-lifecycle reapers** (C-005/NFR-005): "
        "the three sync orphan-reapers — `owner.is_orphan`/`list_orphan_records`, "
        "`orphan_sweep.sweep_orphans`, `daemon.scan_sync_daemons`/"
        "`cleanup_orphan_sync_daemons` (~390 LOC) — collapse to **one** canonical reaper "
        "keyed on `DaemonOwnerRecord`; dedup the duplicated `_is_process_alive` + "
        "daemon-health-probe shared across `sync/` and `dashboard/lifecycle.py`. The single "
        "reaper is what FR-014(b) wires into the spawn path. | reducer-randy validation / "
        "#1071 | Draft |",
        critical="yes",
    ),
    Atom(
        "A016",
        "Q5",
        "F-EXEC-LIFECYCLE",
        "mission_status",
        "exec:mission",
        "accepted_at",
        "2026-06-10T05:45:00.743647+00:00",
        "kitty-specs/execution-context-unification-01KTPKST/meta.json",
        '"accepted_at": "2026-06-10T05:45:00.743647+00:00"',
        1,
    ),
    Atom(
        "A018",
        "Q6",
        "F-ID-COLLISION",
        "identity",
        "repo:test-suite-friction:FR-001",
        "label",
        "FR-001",
        "kitty-specs/test-suite-friction-remediation-01KXDKBX/spec.md",
        "| FR-001 | The dead-code gate",
        critical="no",
    ),
    Atom(
        "A019",
        "Q6",
        "F-ID-COLLISION",
        "identity",
        "repo:worktree-owned-root:FR-001",
        "label",
        "FR-001",
        "kitty-specs/worktree-owned-root-3328-01KZRG01/tasks/WP02-mission-create-integration.md",
        "- FR-001",
        critical="no",
    ),
    Atom(
        "A020",
        "Q3",
        "F-WORKTREE-WP02",
        "ownership",
        "worktree:WP02",
        "owns",
        "tests/agent/test_agent_feature.py",
        "kitty-specs/worktree-owned-root-3328-01KZRG01/tasks/WP02-mission-create-integration.md",
        "- tests/agent/test_agent_feature.py",
    ),
    Atom(
        "A021",
        "Q3",
        "F-WORKTREE-WP02",
        "ownership",
        "worktree:WP02",
        "owns",
        "tests/architectural/test_mission_runtime_surface.py",
        "kitty-specs/worktree-owned-root-3328-01KZRG01/tasks/WP02-mission-create-integration.md",
        "- tests/architectural/test_mission_runtime_surface.py",
    ),
]


def git_show(path: str) -> bytes:
    return subprocess.run(["git", "show", f"{REVISION}:{path}"], check=True, capture_output=True).stdout


def nth_span(data: bytes, literal: bytes, occurrence: int) -> tuple[int, int]:
    cursor = 0
    found = -1
    for _ in range(occurrence + 1):
        found = data.find(literal, cursor)
        if found < 0:
            raise ValueError(f"literal not found (occurrence {occurrence}): {literal!r}")
        cursor = found + len(literal)
    return found, found + len(literal)


def main() -> None:
    output = Path(__file__).with_name("fixtures") / "gold" / "gold-approved.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[list[str | int]] = []
    for atom in ATOMS:
        data = git_show(atom.path)
        start, end = nth_span(data, atom.literal.encode("utf-8"), atom.occurrence)
        prefix = data[:start]
        start_line = prefix.count(b"\n") + 1
        end_line = data[:end].count(b"\n") + 1
        blob = str(subprocess.run(["git", "rev-parse", f"{REVISION}:{atom.path}"], check=True, capture_output=True, text=True).stdout.strip())
        assert data[start:end] == atom.literal.encode("utf-8")
        rows.append(
            [
                atom.atom_id,
                atom.query_id,
                atom.fixture_id,
                atom.atom_type,
                atom.subject,
                atom.predicate,
                atom.object_,
                atom.path,
                blob,
                start,
                end,
                start_line,
                end_line,
                hashlib.sha256(data[start:end]).hexdigest(),  # noqa: TID251 - frozen evidence span integrity
                atom.critical,
                "P0",
                "approved_two_reviewers_2026-08-18",
            ]
        )
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "atom_id",
                "query_id",
                "fixture_id",
                "atom_type",
                "subject",
                "predicate",
                "object",
                "source_path",
                "source_blob",
                "start_byte",
                "end_byte",
                "start_line",
                "end_line",
                "span_sha256",
                "critical",
                "required_provenance",
                "review_status",
            ]
        )
        writer.writerows(rows)


if __name__ == "__main__":
    main()
