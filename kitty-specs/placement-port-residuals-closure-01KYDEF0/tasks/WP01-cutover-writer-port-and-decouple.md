---
work_package_id: WP01
title: 'Cutover writer: port-route _flip_phase + partition-decouple'
dependencies: []
requirement_refs:
- FR-001
- FR-002
planning_base_branch: placement-port-residuals
merge_target_branch: placement-port-residuals
branch_strategy: Planning artifacts for this mission were generated on placement-port-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into placement-port-residuals unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-placement-port-residuals-closure-01KYDEF0
base_commit: 3dff29a5dde481526c4577928e1453ac5d7b0ef5
created_at: '2026-07-26T20:47:07.629884+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- at: '2026-07-25T21:12:34Z'
  actor: tasks
  note: WP created from IC-01+IC-02 (FR-001, FR-002)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/migration/
create_intent:
- tests/specify_cli/migration/test_runtime_state_cutover_placement.py
- tests/specify_cli/migration/test_cutover_partition_decouple.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/migration/runtime_state_cutover.py
- src/specify_cli/migration/backfill_runtime_state.py
- tests/specify_cli/migration/test_runtime_state_cutover_placement.py
- tests/specify_cli/migration/test_cutover_partition_decouple.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading anything else**, load your assigned agent profile via `/ad-hoc-profile-load`
(profile: `python-pedro`, role: `implementer`). Adopt its directives, tactics, and boundaries,
and state which you applied. Only then proceed to the Objective.

## Objective

Make the sole `status_phase` writer PRIMARY-correct **by construction** (FR-001) and close
the COORD-read / PRIMARY-write silent-data-loss residual (FR-002) — both in
`src/specify_cli/migration/runtime_state_cutover.py`, with a supporting internal split of
`backfill_runtime_state`'s read/write coupling.

Read first: `spec.md` (FR-001, FR-002, Domain Language table, Assumptions), `plan.md` (IC-01,
IC-02), `contracts/writer-and-cutover.md`, `quickstart.md`. Note the load-bearing memory
[[reference-write-side-rederivation-gate-grammar]]: `_flip_phase`'s `write_meta` is invisible
to the write-side gate, so FR-001 is enforced by a **runtime assert**, not a static gate.

## Context

- `_flip_phase(feature_dir, …)` (`runtime_state_cutover.py:107-136`) is the ONLY `status_phase`
  writer. Today it writes via `canonicalize_feature_dir(feature_dir)` + `write_meta(validate=False)`,
  PRIMARY-correct only by caller discipline.
- `cutover_mission` (`:147-225`) has a two-leg shape: `status_dir = status_feature_dir if … else feature_dir`
  (`:202`), then `_seed_phase(status_dir)`/`_verify_phase(status_dir)` READ the legacy `tasks/`
  frontmatter from that dir while `_flip_phase(feature_dir)` WRITES the flip.
- The only two-leg caller is `merge/executor.py:996` (birth-cutover, passes `status_feature_dir=COORD`).
  The three single-leg callers — `migration/backfill_runtime_state.py` batch, `cli/commands/migrate_cmd.py:868`,
  `cutover_repo:281` — pass one dir and **already read PRIMARY**. They MUST stay byte-unchanged.
- `LegacyWPRuntime.has_evictable_state()` (`backfill_runtime_state.py:174`) detects genuine runtime.

## Subtasks

### T001 — Red-first FR-001 (off-partition fail-closed) — pin the MECHANISM
Write a failing test in `tests/specify_cli/migration/test_runtime_state_cutover_placement.py` that
drives `cutover_mission(feature_dir, status_feature_dir=…)` with a `feature_dir` whose resolved
PRIMARY home (`resolve_artifact_surface(repo_root, feature_dir.name, PRIMARY_METADATA).path`) differs
from `canonicalize_feature_dir(feature_dir)`, and asserts the flip **fails closed**.
- **CRITICAL (anti-scaffold)**: the RED must come from the **mismatch** branch, NOT from a resolver crash.
  So: (a) assert a **resolver-success precondition** — the fixture mission resolves WITHOUT raising; and
  (b) pin the fail-close to a **distinct, mismatch-specific exception/marker** (not a generic resolver raise),
  so T002's degrade-on-raise handler cannot green this test by swallowing a crash.
- Add a **sibling assertion** that a genuine resolver-**raise** on a well-formed legacy mission **degrades**
  (does NOT fail-close) — so both branches are contract-pinned and can't be conflated.
Construct: a canonical-primary dir present + a divergent `feature_dir` for the same slug + a
verify-passing `status_feature_dir` (so the flip is reached, not blocked at verify). Confirm RED.

### T002 — Route `_flip_phase` through the port (fail-closed)
Resolve the write directory via `resolve_artifact_surface(repo_root, feature_dir.name, PRIMARY_METADATA).path`.
- `repo_root` = the CWD-invariant main-repo root derived from `feature_dir` (never `Path.cwd()`; match the
  module's existing rule at `:19-22`). Use the canonical-root helper the module/port already exposes.
- **Distinguish two failure modes**: an equality **mismatch** (resolved home ≠ passed dir) → fail closed
  (raise, write nothing). A resolver **raise** (e.g. `MissionSelectorAmbiguous`/`StatusReadPathNotFound`)
  on a well-formed legacy corpus mission → MUST NOT abort the flip (catch/degrade to the current path so
  NFR-002's corpus run stays green). Keep `write_meta(..., validate=False)` tolerant write.
- Make T001 green.

### T003 — Red-first FR-002 (two-leg silent loss)
In `tests/specify_cli/migration/test_cutover_partition_decouple.py`, build a PRIMARY `feature_dir`
whose `tasks/*.md` carry `has_evictable_state()==True` frontmatter + an absent/stale COORD
`status_feature_dir/tasks/`. Assert the current behavior loses runtime (`seeded_count==0` while
`flipped==True`). Confirm RED.

### T004 — Decouple read-leg (PRIMARY) from write-leg (COORD)
Internal to `cutover_mission` + `_seed_phase`/`_verify_phase`: read the `tasks/` frontmatter from the
**PRIMARY** leg (`feature_dir`) while the seed-event write (`status.events.jsonl` = STATUS_STATE) and
verify anchor stay on the **COORD** leg (`status_dir`). This requires splitting `backfill_runtime_state`'s
single-dir coupling into a read-dir vs event-write-dir (add a parameter; keep the default so the three
single-leg callers behave identically). **Keep `cutover_mission`'s public signature stable.** Make T003
green: assert `seeded_count>0` AND the event log lands on the COORD leg (NOT PRIMARY — I-02).

### T005 — Corpus validation (NFR-002) — measured, not asserted-on-faith
Run the cutover across the dogfood corpus (`spec-kitty migrate backfill-runtime-state` / the `cutover_repo`
walk). **Attribute out the pre-existing #2917 dogfood-corpus cutover gap**: run the SAME walk on the merge-base
(via `PYTHONPATH=<worktree>/src`) to capture the baseline, and compare — only NEW failures on this branch count.
Assert: 0 NEW genuinely-legacy missions fail to flip; 0 PRIMARY-runtime evictions; and the three single-leg
callers (`m_zz_runtime_state_backfill.py:204`, `migrate_cmd.py:868`, `cutover_repo:281`) are byte-unchanged in
behavior (they already read PRIMARY — do NOT edit them). Record the baseline vs branch delta as evidence.

### T006 — Gate clean
`ruff check` + `mypy --strict` clean on the diff; complexity ≤15; no new suppressions. Run
`PWHEADLESS=1 pytest tests/specify_cli/migration/ -q`.

## Branch Strategy

Planning base: `placement-port-residuals`. Final merge target: `placement-port-residuals` (the mission
lands there; a separate PR takes it to `main`). Your execution worktree is allocated per the computed lane
from `lanes.json` after finalize-tasks — enter it via `spec-kitty agent action implement WP01 --agent claude`.

## Definition of Done
- [ ] T001 + T003 were RED before the fix, GREEN after (red-first evidence captured).
- [ ] `_flip_phase` resolves its target through the port; off-partition → fail closed; resolver-raise on a valid legacy mission does NOT abort.
- [ ] Cutover reads `tasks/` from PRIMARY; event log still lands on COORD; signature stable.
- [ ] Corpus regression-free; 3 single-leg callers untouched.
- [ ] ruff + mypy clean; migration tests green.

## Risks / reviewer guidance
- **Do NOT** swap `status_dir → feature_dir` wholesale — that pushes the event log onto PRIMARY (I-02 violation). Only the `tasks/` READ moves.
- **Do NOT** source `repo_root` from `Path.cwd()` — reintroduces the ambient-root hazard the module bans.
- Reviewer: confirm the two failure modes (mismatch vs resolver-raise) are handled distinctly; confirm events land on COORD in the FR-002 test; confirm the three single-leg callers are unedited.
