---
work_package_id: WP04
title: '#3311 — re-finalize preserves planning provenance once execution has begun'
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-007
- FR-008
planning_base_branch: fix/mission-a-p0-consistency
merge_target_branch: fix/mission-a-p0-consistency
branch_strategy: Planning artifacts for this mission were generated on fix/mission-a-p0-consistency. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-a-p0-consistency unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
history:
- Created by /spec-kitty.tasks for mission-a-p0-consistency-01KZWHY1
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/mission_finalize.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_finalize_provenance_guard.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_finalize.py
- tests/specify_cli/cli/commands/agent/test_finalize_provenance_guard.py
- tests/regression/test_issue_3311_finalize_rewrites_active_lanes.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile: `/ad-hoc-profile-load python-pedro` and apply it. You are an **implementer**.

## Objective

Re-running `finalize-tasks` after implementation has begun unconditionally recomputes
`lanes.json` and re-captures `planning_commit_sha`, destroying established planning
provenance on an ownership-only amendment. Gate the recompute on an **"execution has
begun"** signal: once begun, preserve `planning_commit_sha` (or refuse before writing);
before execution begins, keep regenerating freely.

## Context (root cause — verified; scope-corrected)

- `_compute_and_write_lanes` (`mission_finalize.py` ~:1205-1252): calls `compute_lanes` (pure recompute) then unconditionally `lanes_manifest.planning_commit_sha = _capture_target_branch_tip(...)` (~:1251) + `write_lanes_json`. It never reads the existing `lanes.json`.
- **Scope correction**: the "topology collapse / lane renumber" narrative does NOT reproduce — scope this WP to the confirmed `planning_commit_sha` clobber only. Do not add topology-preservation behavior.
- First finalize ALWAYS writes `lanes.json` + sets `planning_commit_sha`, so a trigger keyed on file/SHA presence would break the documented idempotent **pre-execution** re-finalize (`mission_finalize.py` docstring ~:326-327).

## Constraints

- **C-005**: the preserve/refuse trigger keys on **"execution has begun"** (status events past `planned` / materialized lane worktrees), never on `lanes.json`/`planning_commit_sha` presence. Respect ADR `2026-07-29-1`/FR-009 single-write provenance freeze — no second commit, no re-capture on the execution-begun path.
- **Status-surface reader recipe (MANDATORY)**: resolve the coord-aware read dir via `coordination/surface_resolver.py::resolve_status_surface_with_anchor(repo_root, mission_slug).read_dir` (the `implement.py:1668-1680` pattern; `_compute_and_write_lanes` already has `repo_root`+`mission_slug`), then a **read-only** lane read `status/lane_reader.py::get_all_wp_lanes(read_dir)` (or `reducer.py::materialize_snapshot`). **NEVER `reducer.materialize()`** — it writes `status.json` to disk. Guard on `lane_reader.has_event_log(read_dir)` — **absent log ⟹ execution not begun** (fresh mission has no log; `get_all_wp_lanes` otherwise raises via `_require_event_log`).

## Subtasks

### T014 — Execution-begun signal (read-only, coord-aware)

Add a small module-local helper (e.g. `_execution_has_begun(repo_root, mission_slug) -> bool`)
that resolves the read dir via `resolve_status_surface_with_anchor`, returns `False` when
`has_event_log(read_dir)` is `False`, else reads `get_all_wp_lanes(read_dir)` and returns
`True` iff any WP's current lane ∉ {`planned`}. No disk writes.

### T015 — Gate the recompute/re-capture

In `_compute_and_write_lanes`, when `_execution_has_begun(...)` is `True`: preserve the
existing `planning_commit_sha` from the on-disk `lanes.json` (read it first) — do NOT
re-capture the branch tip — or refuse before writing any bytes with a clear structured
error (pick preserve as the default; refuse only if preservation cannot be done safely).
When `False`: keep today's behavior (recompute + re-capture). Preserve the single-write
freeze (one write of `lanes.json`).

### T016 — Non-fakeable guard tests [P]

`tests/specify_cli/cli/commands/agent/test_finalize_provenance_guard.py`:
- **execution-begun preservation against a non-`None` tip**: seed lanes + a recorded `planning_commit_sha`; simulate execution-begun via the status event log (a WP past `planned`); run finalize after an ownership-only amendment with the branch tip **differing** from the recorded SHA; assert the recorded SHA is **preserved** (not overwritten with the new tip). (The existing repro only covers the `None`-tip case, which a naive `if sha is not None` fakes.)
- **benign pre-execution regeneration**: with no WP past `planned`, run finalize after an observable `owned_files` amendment (WP01 gains a path WP02 owns); assert regeneration **actually ran** — the amended topology is reflected (two lanes union into one) or `planning_commit_sha` is re-captured to the new tip. "Did not refuse" alone is insufficient.
- **read-does-not-write invariant (renata — the crux hazard, pin it don't eyeball it)**: assert the execution-begun path does **not** create or modify `status.json` — snapshot the resolved status dir's file set + hashes (or mtimes) before/after the finalize call and assert unchanged, and/or spy that `reducer.materialize` is **not** called. This is what makes a lazy `reducer.materialize()` (a disk write from a "read") fail a test rather than pass reviewer-eyeball.

### T017 — Relocate the repro; canonicalize (NFR-005)

Move `tests/regression/test_issue_3311_finalize_rewrites_active_lanes.py` into
`tests/specify_cli/cli/commands/agent/`. Drop `@pytest.mark.regression`; add canonical
marks from `docs/context/testing-taxonomy.md`; rewrite the docstring as a permanent
guard (#3311 fixed; pins provenance preservation on execution-begun re-finalize).

### T018 — Gates

`ruff`/`mypy` clean. Run the finalize suite (serially if it touches the status daemon):
`PWHEADLESS=1 .venv/bin/python -m pytest tests/specify_cli/cli/commands/agent/ -q -k "finalize"`.
**Mechanical regression-exit check** (the repro is *relocated*, so a dropped marker is the fakeable step): `pytest tests/ -m regression -k 3311` must select **nothing**.

## Branch Strategy

Planning base + merge target: `fix/mission-a-p0-consistency`. **This WP depends on
WP01/WP02/WP03** (sequenced last — highest blast radius) — it cannot be claimed until
those are approved/done. Worktree is per-lane from `lanes.json`. Implement via
`spec-kitty agent action implement WP04 --agent claude`.

## Definition of Done

- [ ] Execution-begun signal via the resolved coord-aware surface (never `reducer.materialize()`); `has_event_log` guard.
- [ ] Re-finalize after execution begun preserves `planning_commit_sha` (or refuses); pre-execution re-finalize regenerates.
- [ ] Guard tests: non-`None`-tip preservation + observable regeneration (T016).
- [ ] #3311 repro relocated to `tests/specify_cli/cli/commands/agent/`, marker dropped, canonical marks + guard docstring.
- [ ] `ruff`/`mypy` clean; finalize suite green; no green `regression`-marked #3311 test.

## Risks / Reviewer guidance

- **Reader hazard**: reviewer must confirm the code uses `resolve_status_surface_with_anchor`+`get_all_wp_lanes`/`materialize_snapshot` — **not** `reducer.materialize()` (a disk write from a "read") and not a raw `planning_dir` read (split-brain under coord topology).
- Confirm the trigger is execution-state, not file/SHA presence — else the benign pre-execution re-finalize regresses.
- Keep scope to the provenance clobber; no topology-preservation work.
