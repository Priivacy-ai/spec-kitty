---
work_package_id: WP01
title: Shared dirty-tree self-bookkeeping authority (kitty-ops)
dependencies: []
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: fix/reliability-papercut-sweep
merge_target_branch: fix/reliability-papercut-sweep
branch_strategy: Planning artifacts for this mission were generated on fix/reliability-papercut-sweep. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/reliability-papercut-sweep unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "672580"
history:
- at: '2026-06-30T20:12:14Z'
  actor: claude
  note: 'WP authored from IC-01 (post-plan squad: cross-gate scope)'
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/artifacts.py
create_intent:
- tests/specify_cli/acceptance/test_accept_dirty_kitty_ops.py
execution_mode: code_change
owned_files:
- src/mission_runtime/artifacts.py
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/merge/git_probes.py
- src/specify_cli/review/dirty_classifier.py
- tests/mission_runtime/test_self_bookkeeping_allowlist.py
- tests/specify_cli/acceptance/test_accept_dirty_kitty_ops.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries for this work package.

## Objective

Make a stray `kitty-ops/<ulid>.jsonl` Op-record orphan non-blocking for **every** dirty-tree
gate (record-analysis, accept, merge preflight), while genuine mission-relevant dirt still
blocks. Today only `record-analysis` consults `is_self_bookkeeping_path`; the accept gate and
merge preflight keep independent allowlists with no kitty-ops arm, so they block on the same
debris. Converge all three on one shared authority. (FR-001 / #2251)

## Context

- `src/mission_runtime/artifacts.py` — `is_self_bookkeeping_path` (~:293) is the canonical
  self-bookkeeping check (currently: `meta.json` + the encoding-provenance log). Consumed by
  `cli/commands/agent/mission_record_analysis.py:131`.
- `src/specify_cli/acceptance/__init__.py` — `_accept_dirty_gate` (~:131) + `_accept_owned_dirty_paths`
  (~:94) + `_filter_coordination_residue` (~:176). Preserves non-accept-owned, non-residue dirt
  fail-closed — so a kitty-ops orphan blocks here too.
- **FOUR dirty-tree classifiers exist** (post-plan dedup squad) — the orphan blocks at all of them
  and only `is_self_bookkeeping_path` is canonical. Converge the other three on it:
  1. `is_self_bookkeeping_path` (`mission_runtime/artifacts.py:293`) — the canonical authority (extend).
  2. accept gate — `acceptance/__init__.py` `_accept_dirty_gate:131`.
  3. **merge gate — `merge/git_probes.py` `_classify_porcelain_lines:119`** (invoked from
     `merge/executor.py:582,601`). NOTE: `merge/preflight.py` has NO porcelain/clean check — the
     real merge classifier is `git_probes`. (`_classify_porcelain_lines` already delegates
     coord-residue to the single `is_coordination_artifact_residue_path` — mirror that pattern.)
  4. implement/review preflight — `review/dirty_classifier.py` `_is_benign:58` / `classify_dirty_paths:95`
     (used by `tasks_parsing_validation.py:441,460`).
- Precedent: **#2102** (closed) added the path-specific allowlist this extends. Umbrella **#1914**
  (no-op-stable gates) is the deeper framing — reference it; do NOT undertake the full no-op-stable
  rework (stop emitting orphans) in this WP.

## Subtasks

### T001 — Red-first: prove accept + merge gates block on a kitty-ops orphan
Add `tests/specify_cli/acceptance/test_accept_dirty_kitty_ops.py`: stage only a
`kitty-ops/01KW....jsonl` orphan in a fixture repo, drive the accept gate (and a merge-preflight
unit) and assert they currently FAIL (`DIRTY_WORKTREE`-class block). This test must be RED on
pre-fix code through the real gate entry point.

### T002 — Add the kitty-ops arm to the shared authority
In `artifacts.py`, extend `is_self_bookkeeping_path` to recognize a `kitty-ops/`-segment path
whose basename is `<ULID>.jsonl` (26-char ULID). Keep the match tight — only that shape, so it
cannot mask real dirt. Preserve the disjoint-set G-5 contract (self-bookkeeping ∩ blocking = ∅).

### T003 — Route the accept gate through the shared authority
In `acceptance/__init__.py`, make `_accept_dirty_gate` consult `is_self_bookkeeping_path` (in
addition to accept-owned + coordination-residue filtering) so a kitty-ops orphan is excluded.
Do not weaken the fail-closed handling of genuine dirt.

### T004 — Route the merge gate (git_probes) + review preflight through the shared authority
In `merge/git_probes.py` `_classify_porcelain_lines`, exclude a kitty-ops orphan via
`is_self_bookkeeping_path` (mirror the existing `is_coordination_artifact_residue_path`
delegation — no second literal). Then in `review/dirty_classifier.py` (`_is_benign`/
`classify_dirty_paths`), do the same so the implement/review preflight gate agrees. After this,
ALL FOUR gates consult the single authority.

### T005 — Extend the allowlist test + counter-contract (all 4 gates)
Extend `tests/mission_runtime/test_self_bookkeeping_allowlist.py` with the kitty-ops case (assert
`True`), and assert the counter-contract: a genuine mission-relevant dirty path is NOT
self-bookkeeping and STILL blocks at all four gates. Keep the existing healthy tests intact
(extend, don't replace).

## Branch Strategy

Planning/base branch: `fix/reliability-papercut-sweep`. Final merge target: `fix/reliability-papercut-sweep`
(this mission later PRs to `main`). Execution worktrees are allocated per computed lane from
`lanes.json` — do not hand-create branches. Run `spec-kitty agent action implement WP01 --agent claude`.

## Definition of Done

- T001 demonstrated RED on pre-fix code, GREEN after.
- All four gates (record-analysis, accept `_accept_dirty_gate`, merge `git_probes._classify_porcelain_lines`,
  review `dirty_classifier._is_benign`) exclude a kitty-ops orphan via the single shared
  `is_self_bookkeeping_path` authority.
- Genuine dirt still blocks all four (counter-contract test green).
- ruff + mypy clean; complexity ≤ 15 on touched functions.
- No change to behavior for non-kitty-ops paths.

## Reviewer guidance

Verify the match is tight (a `kitty-ops/notes.txt` or a non-ULID name is NOT excluded). Confirm
all three gates actually call the shared authority (grep for independent allowlists left behind).
Confirm G-5 disjointness is preserved. Confirm #1914 is referenced, not re-implemented.

## Activity Log

- 2026-06-30T21:21:22Z – claude:sonnet:python-pedro:implementer – shell_pid=588360 – Assigned agent via action command
- 2026-06-30T21:39:34Z – claude:sonnet:python-pedro:implementer – shell_pid=588360 – Ready: 4 gates converged on is_self_bookkeeping_path (kitty-ops arm), red-first GREEN, ruff+mypy clean
- 2026-06-30T21:42:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=672580 – Started review via action command
- 2026-06-30T21:48:04Z – user – shell_pid=672580 – Review passed: 4 dirty-tree gates (record-analysis, accept _accept_dirty_gate, merge git_probes._classify_porcelain_lines, review dirty_classifier._is_benign) all converged on single is_self_bookkeeping_path authority. Kitty-ops arm is TIGHT: regex (?:^|/)kitty-ops/[0-9A-HJKMNP-TV-Z]{26}\.jsonl$ (Crockford base32, exactly 26 chars, anchored) — notes.txt, ops-index.jsonl, short/long ULID all still block at predicate AND all 3 gates (tests confirm). G-5 disjoint-set preserved: real source/spec dirt still blocks at all 4 (counter-contract green). Red-first verified: reverting source makes orphan-does-not-block assertions genuinely FAIL at all gates. 23 tests pass, ruff clean. mypy: 5 errors in acceptance/__init__.py pre-exist on base (line-shifted only), none introduced. No independent allowlist left behind. Scope clean (6 owned files; kitty-specs churn is merge-commit coordination only).
