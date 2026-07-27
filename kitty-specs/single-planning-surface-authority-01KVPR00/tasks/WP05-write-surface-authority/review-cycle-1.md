---
verdict: approved
reviewer: reviewer-renata
cycle: 1
---

# WP05 — Single write-surface authority + status emission — Review Cycle 1

**Verdict: APPROVED.** Live evidence re-verified for all three critical checks
(#2063/SC-004 read-back, FR-009 backstop-removal non-vacuity, :336 reachable→LEFT).
32/32 WP05 tests green; ruff clean; zero NEW mypy errors; complexity ≤15.

## Per-criterion findings

### 1. FR-007 / NFR-002 two-responsibility split — PASS
`safe_commit_cmd._resolve_commit_target` now discriminates: a `kitty-specs/<slug>/`
artifact for a resolvable mission resolves via the WP03 seam
(`resolve_placement_only`), NEVER `get_current_branch`. The generic operator-file
path keeps `--to-branch`/HEAD. Both proven GREEN:
- generic `--to-branch` → explicit ref; generic no-`--to-branch` → HEAD (NFR-002).
- mission-aware path: seam value used, `get_current_branch` spy NEVER consulted
  (asserts the #2063 root is closed on this path).
- unresolvable-mission path degrades to generic HEAD (no churn / no hard-fail).
Public `safe_commit_command` signature unchanged (CT4) — only `_resolve_commit_target`
gained an internal `files` param.

### 2. #2063 / SC-004 read-back witness — PASS (re-verified live)
`test_spec_commit_lands_and_reads_back_from_coordination_surface` exercises the REAL
seam (`commit_for_mission` + `resolve_placement_only` + `candidate_feature_dir_for_mission`)
on a genuinely protected target repo, no router mock, production-shaped full ULID:
- WRITE leg: `placement_ref == coord branch` (not HEAD).
- READ-BACK leg: committed `spec.md` content recovered from the next-command read
  surface, and that surface IS the coordination worktree (`.worktrees` in path) —
  the SC-004 round-trip, not a write-only proof.
- Negative check: `main:kitty-specs/<slug>/spec.md` does NOT carry the coord-only
  marker — proves the write moved OFF primary HEAD. Re-ran live: GREEN.

### 3. FR-009 call-site audit + backstop-removal non-vacuity — PASS (re-verified live)
The status-emit seam fix lives at the single transactional caller boundary
(`_identity_for_request`), which resolves the CWD-invariant canonical primary
feature dir — so there is no per-caller scatter to convert; convergence is
structural. WP05 modifies no `emit_status_transition` call site in mission.py
(correct: the seam path is supplied upstream).
The non-vacuity proof `test_caller_supplies_seam_feature_dir_even_with_backstop_neutralized`
**neutralizes** `emit.py.canonicalize_feature_dir` to identity passthrough, then
asserts the event STILL lands on the coord branch event log (read back via
`git show coord:...status.events.jsonl`) AND that the primary checkout carries NO
status file. This proves the CALLER supplies the seam path — it would go RED if a
caller regressed to an ad-hoc worktree path with the backstop off. Re-ran live: GREEN.

### 4. status_transition READ-contract (SC-001) — PASS
`_read_contract_from_transaction_target`'s `:558 coordination_branch is None` SURFACE
decision is RETIRED — coord-vs-primary SHAPE now reads stored topology via
`_read_contract_routes_through_coordination` (pure `classify_topology`, no meta write).
SC-001 pinned by an AST-scoped test (scans the function body for any
`identity.coordination_branch` Compare node — docstring mentions cannot mask it).
C-006 transient arms preserved: `worktree_root.exists()` (#1718) and `_branch_exists`
(#1848) still PROBE on-disk state; both witnessed (branch-deleted→primary,
worktree-materialised→coord) and the SHAPE-helper purity (no topology back-fill on
read) is tested.

### 5. T029 :336 drain — reachable → LEFT (genuine, not lazy) — ADJUDICATED CORRECT
The negative-probe is genuine: it forces `:336`'s real reaching condition
(blank/whitespace slug → `resolve_placement_only` raises `ActionContextError`) with
`coord_branch=None` so the `coord_branch or …` short-circuit cannot mask the HEAD
selector, spies `_current_branch`, and asserts the arm IS taken and returns HEAD.
A companion test pins the short-circuit branch (proving WHY happy-path runs never
witness the selector — the Risk #2 trap). Re-ran live: GREEN — the arm is
empirically REACHABLE, so LEFT is the correct call. Draining a reachable
load-bearing arm would re-open the create-window write bug. This is the BEST
outcome and it is genuine. WP00's allow-list was NOT touched (verified: WP05's
commit does not modify `test_no_write_side_rederivation.py`; the `:336` SEED entry
remains, re-keyed onto `composite_key`). Reachability is permanently pinned in the
OWNED `tests/architectural/test_wp05_write_target_drain.py`.

### 6. FR-005 — PASS
Both `.kind is COORDINATION` sites in mission.py (`_planning_commit_worktree`,
`_enforce_analysis_report_write_preflight`) route through `routes_through_coordination`.
grep: zero decision reads remain (the one `:776` hit is a docstring). AST gate pins
zero `.kind is COORDINATION` Compare nodes. `CommitTargetKind` TYPE survives in
`mission_runtime/context.py` and is still constructed in `safe_commit_cmd.py`; the
now-unused mission.py import was removed (correct hygiene — a lingering import is
F401; this is NOT type deletion, which Mission B owns).

### 7. Gates — PASS
- ruff: ALL clean on owned production + test files (default selection — the project gate).
- mypy: 10 `no-any-return` errors total across the 3 owned files, ALL pre-existing on
  untouched lines (status_transition 6 at tip == 6 at base; safe_commit `:71` and
  mission.py `:967/:2449/:3969` are pre-existing functions). The WP05 new helper
  region (544-620) and new safe_commit helpers produce ZERO mypy errors. **Zero NEW
  errors vs base** — criterion satisfied; the pre-existing debt is out of scope
  (DIR-024 locality).
- complexity: C901 clean (≤15).
- suppressions: one `# noqa: PLC0415` in status_transition's new helper — matches the
  13 pre-existing instances in that file (deferred import to avoid circular dep);
  PLC0415 is not in the default ruff selection. No new enforced suppressions.
- equivalence gate (`test_surface_resolution_equivalence.py`) + terminology guard: GREEN.

## Anti-pattern checklist
1. Dead code — PASS (all new helpers have live production callers).
2. Synthetic-fixture — PASS (tests exercise real seams / real git; backstop-neutralized).
3. Silent empty return — PASS (`_resolve_mission_aware_target` `return None` documented:
   intentional fallback to generic path for unresolvable missions).
4. FR coverage — PASS (FR-007, FR-009, FR-005, SC-001, SC-004 each have behavioral asserts).
5. Frozen surface — PASS (no edits to resolution.py / tasks.py / _substantive.py; WP00 guard untouched).
6. Locked decision — PASS (CommitTargetKind type not deleted; signature not widened).
7. Shared-file ownership — PASS (status_transition.py is owned; WP00 guard left untouched per LEFT verdict).
8. Production fragility — PASS (no new bare raise on a transient path).

## Pre-existing (NOT a WP05 defect)
`test_mission_runtime_surface.py::test_public_surface_matches_contract` — WP01 `__all__`
widening vs `_PUBLIC_SURFACE`, confirmed pre-existing on the lane base; orchestrator
handles at pre-merge.
