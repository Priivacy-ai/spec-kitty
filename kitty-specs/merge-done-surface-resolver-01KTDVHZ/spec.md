# Merge Done-Marking Surface Resolver

**Mission ID:** 01KTDVHZKGCHCW6HQ4V577PNES
**Mission Slug:** merge-done-surface-resolver-01KTDVHZ
**Mission Type:** software-dev
**Status:** Draft
**Source:** https://github.com/Priivacy-ai/spec-kitty/issues/1726

---

## Purpose

After `spec-kitty merge`, work packages (WPs) that were `approved` show as not-`done` when the mission carries a coordination branch. The dashboard reports `Completed: 0 (80.0%)` — the 0.8 weight of `approved` vs 1.0 for `done` — even though the merge succeeded. The merge command reports a post-merge validation failure and exits non-zero.

This mission fixes the immediate structural divergence in the merge done-marking loop and broadens the fix to a full audit of the merge path for any other sites with the same locate-vs-observe failure class. The scope was explicitly broadened from the original issue ACs to include the parity ratchet per issue #1672.

---

## Problem Statement

When a mission carries `coordination_branch` in its metadata, the merge done loop operates on two different status surfaces:

- **Write:** Done events are committed to the coordination branch worktree and ref.
- **Read-back:** The post-merge assertion reads the primary checkout's event log file directly.

These two surfaces diverge. The done event is written where the assertion does not look. The assertion fires before the coordination-branch events are flushed to the primary checkout, so it structurally cannot see the write under the current code path.

This is a class recurrence of issue #1589 (facet 3), which fixed the same divergence on the runtime read path (`move-task`, `next`, `lane_reader`). The merge closeout path was not covered by that fix and carries no recurrence guard.

---

## User Scenarios & Testing

**Primary scenario — merge with coordination branch:**
A developer runs `spec-kitty merge` on a mission that was created with a coordination branch (the standard topology for multi-lane missions). All WPs are in `approved`. The merge completes. The developer expects the dashboard to show `Completed: 1 (100%)` and the merge command to exit zero.

**Current (broken) outcome:** The merge command exits non-zero with "Post-merge status validation failed: merged WPs did not reach done in the canonical event log." The dashboard shows `Completed: 0 (80.0%)`.

**Expected outcome after fix:** The merge command exits zero. All WPs show `done`. The dashboard shows `Completed: 1 (100%)`.

**Secondary scenario — planning-only merge with coordination branch:**
A developer runs `spec-kitty merge` on a planning-artifact-only mission (no code changes, WPs in the `lane-planning` lane) that carries a `coordination_branch`. The same divergence applies; the fix must cover this path identically.

**Regression scenario — legacy mission (no coordination branch):**
A developer runs `spec-kitty merge` on a mission with no `coordination_branch` in its metadata. All existing behavior must be preserved without change.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | A single canonical surface resolver function accepts `(repo_root, mission_slug)` and returns the authoritative status event log path for that mission, correctly accounting for whether `coordination_branch` is set in the mission's metadata. | Proposed |
| FR-002 | `_mark_wp_merged_done` consumes the surface resolver for all status surface lookups, replacing any inline path derivation. | Proposed |
| FR-003 | `_assert_merged_wps_reached_done` consumes the same surface resolver, guaranteeing it reads from the same location written to by `_mark_wp_merged_done`. | Proposed |
| FR-004 | After the fix, the merge done loop no longer depends on worktree-teardown ordering for the read-back assertion to succeed. The assertion and the write resolve to the same surface regardless of when worktrees are torn down. | Proposed |
| FR-005 | A documented audit of the merge path identifies every site where status events are written or read (beyond the done-marking loop), checking each for the same locate-vs-observe divergence class. | Proposed |
| FR-006 | Any additional divergence sites discovered in the audit are closed using the surface resolver, or explicitly documented as out-of-scope with rationale if they require a separate mission. | Proposed |
| FR-007 | Regression tests cover a planning-only merge with `coordination_branch` set in the mission's metadata, exercising `_mark_wp_merged_done` and `_assert_merged_wps_reached_done` without mocking either function, and asserting that done events persist and read back on the same surface. | Proposed |
| FR-008 | Regression tests cover a code-change merge with `coordination_branch` set, under the same constraints as FR-007. | Proposed |
| FR-009 | All existing merge tests that do not set `coordination_branch` continue to pass without modification. | Proposed |
| FR-010 | The merge command exits zero and the dashboard shows `Completed: 1 (100%)` after a successful merge on a mission with `coordination_branch` set and all WPs previously in `approved`. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The surface resolver adds no perceptible latency to the merge done-marking loop. Path resolution is a metadata read (no network, no git I/O beyond the existing `meta.json` read). | Sub-millisecond per WP | Proposed |
| NFR-002 | New code added by this mission meets the project's test coverage threshold. | 90%+ coverage on new code paths | Proposed |
| NFR-003 | The surface resolver is the sole mechanism by which both write and read determine the events file location. No secondary fallback or parallel path is introduced. | Zero additional surface-resolution paths | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The fix must not alter the wire format or schema of `status.events.jsonl`. | Binding |
| C-002 | Missions that lack `coordination_branch` in `meta.json` (legacy topology) must experience no behavioral change. | Binding |
| C-003 | The surface resolver must not introduce circular imports into the module graph. | Binding |
| C-004 | Regression tests (FR-007, FR-008) must not mock `_mark_wp_merged_done` or `_assert_merged_wps_reached_done`. | Binding |
| C-005 | This mission's scope is bounded to the merge path. Runtime read sites already fixed by issue #1589 (`move-task`, `next`, `lane_reader`) are not revisited unless the audit (FR-005) finds that a merge-path site delegates to them incorrectly. | Binding |
| C-006 | The audit findings (FR-005) must be committed as a discoverable artifact before the mission is closed, so the class cannot be re-opened without evidence. | Binding |

---

## Assumptions

- The coordination branch topology is stable: when `coordination_branch` is present in `meta.json`, a corresponding coordination worktree and branch ref exist at merge time.
- `safe_commit` at `merge.py:1864` is the correct flush point for coordination-branch events. The fix does not change when `safe_commit` runs; it changes where the assertion reads from.
- The parity ratchet referenced by issue #1672 means: once the class is fixed, a test must make it structurally impossible to regress silently. FR-007 and FR-008 satisfy this constraint.
- The scope of "merge path" for the FR-005 audit is: all code within `src/specify_cli/cli/commands/merge.py` and any modules it directly calls that touch `status.events.jsonl` (reads or writes).

---

## Key Entities

| Entity | Description |
|--------|-------------|
| Status surface | The filesystem path (and git ref, when coordination branch is active) where `status.events.jsonl` is authoritative for a mission at a given moment. |
| Surface resolver | The single function introduced by this mission that accepts `(repo_root, mission_slug)` and returns the canonical status surface path. |
| Coordination branch | A git ref (`kitty/mission-<slug>-<mid8>`) that holds status events during active mission execution. Present in `meta.json` for missions using the new topology; absent for legacy missions. |
| Done-marking loop | The code block in `merge.py` (~lines 1782–1797) that calls `_mark_wp_merged_done` for each WP and then `_assert_merged_wps_reached_done` for all WPs. |
| Merge-path audit | A documented scan of all status write/read sites on the merge path, checking each for locate-vs-observe divergence. |

---

## Success Criteria

1. After a successful `spec-kitty merge` on a mission with `coordination_branch` set and all WPs previously in `approved`, the dashboard shows `Completed: 1 (100%)` and the merge command exits zero.
2. All regression tests introduced by this mission pass without mocking `_mark_wp_merged_done` or `_assert_merged_wps_reached_done`.
3. No pre-existing merge tests regress.
4. The merge-path audit artifact is committed and lists every site checked, with explicit findings for any discovered divergence sites.
5. The locate-vs-observe divergence class cannot silently recur on the merge path: any future change that bypasses the surface resolver will break the regression tests.
