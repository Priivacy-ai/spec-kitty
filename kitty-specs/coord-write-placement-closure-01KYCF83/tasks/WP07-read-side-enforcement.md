---
work_package_id: WP07
title: Read-side placement enforcement + fold
dependencies:
- WP02
- WP06
requirement_refs:
- FR-004
- FR-006
- NFR-002
planning_base_branch: feat/coord-write-placement-closure
merge_target_branch: feat/coord-write-placement-closure
branch_strategy: Planning artifacts for this mission were generated on feat/coord-write-placement-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-write-placement-closure unless the human explicitly redirects the landing branch.
created_at: '2026-07-25T12:00:00+00:00'
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
- T055
phase: Phase 3 - Whole-tree enforcement
history:
- at: '2026-07-25T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/resolution.py
create_intent:
- tests/architectural/test_read_surface_placement_guard.py
execution_mode: code_change
owned_files:
- src/mission_runtime/resolution.py
- src/specify_cli/acceptance/execution_context.py
- src/specify_cli/acceptance/gates_core.py
- tests/architectural/test_read_surface_placement_guard.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – Read-side placement enforcement + fold #2906 guards + read gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objective

Close the read side symmetric to the write side. Route every mission-artifact read through the read-surface authority and fail loud on a partition mismatch, and **fold #2906's accept-time read guards INTO** this authority (delegate, do not double-guard). This is the **highest-blast-radius** WP (~68 read sites) — the delta is *enforcement*, not new routing (`artifact_home_for(kind).read_surface` already exists since #2090).

- **FR-004 / NFR-002**: a read of a coord-homed kind against a primary substitute raises a typed partition-mismatch error; zero silent substitutions at routed sites.
- **FR-006 (read leg — post-tasks squad)**: WP02 reclassifies `traces/` PRIMARY→COORD; this WP owns the **read-side** closure of that reclassification. Every live `traces/` read site must resolve the new COORD read_surface, not the stale PRIMARY location (see T055).

**Done** = `resolution.py:1403` `read_dir` fails loud on mismatch; #2906's guards (`execution_context.py:203-223`, `gates_core.py:436`) delegate to the authority; every current lenient degrade is enumerated and proven still-lenient by a red-first test; a new read gate reuses WP06's scanner; **every `traces/` read site resolves COORD post-reclassification (T055)**.

## Context & Constraints

- Spec: [spec.md](../spec.md) US4, FR-004, NFR-002, SC-003. Plan: [plan.md](../plan.md) IC-05. Contract: [contracts/placement-enforcement.md](../contracts/placement-enforcement.md) "Read". Research D-06.
- **Depends on WP06** (shared scanner) and **WP02** (owns the `commit_target` flip; this WP owns `resolution.py:949`, the sole consumer — apply the consumer adjustment handed over by WP02's T005 audit if it was non-inert).
- **Convergence, not duplication (folded squad finding)**: refactor #2906's substitution-refusal in `execution_context.py` / `gates_core.py` to **delegate** to the new authority — do not leave a parallel guard beside it.
- **Whitelist the sanctioned degrades**: enumerate every current lenient read and prove each is EITHER a true mismatch that *should* now fail OR an explicitly whitelisted degrade. Known lenient paths: `StatusReadPathNotFound` (`resolution.py:365/841/886`), the **coord-worktree-absent degrade** (flatten-when-coord-gone), the #2906 lenient diagnose path. Red-first that each stays lenient.
- **Layering**: **add NO new top-level `specify_cli` import** to `mission_runtime/resolution.py`.

## Branch Strategy

- **Strategy**: generated on `feat/coord-write-placement-closure`; changes merge back into `feat/coord-write-placement-closure`.
- **Planning base branch**: `feat/coord-write-placement-closure`
- **Merge target branch**: `feat/coord-write-placement-closure`

## Subtasks & Detailed Guidance

### Subtask T031 – Enumerate every lenient read + build the whitelist (design-first)

- **Purpose**: NFR-002 without breaking sanctioned degrades — the ~68-site blast radius must be mapped before enforcing.
- **Steps**: Enumerate all current lenient reads: `StatusReadPathNotFound` (`resolution.py:365/841/886`), coord-worktree-absent degrade, #2906 diagnose path, and any silent primary-substitute fallbacks. For each, decide: true mismatch → should fail, OR sanctioned degrade → whitelist. **Also enumerate the `traces/` read sites** (feeds T055): the five known live readers — `src/specify_cli/retrospective/generator.py`, `src/specify_cli/lanes/merge.py`, `src/specify_cli/charter_runtime/freshness/computer.py`, `src/specify_cli/cli/commands/merge_driver.py`, `src/specify_cli/init.py` — **plus any others surfaced by `grep -rn "traces/" src/`**. Each `traces/` reader gets a verdict: resolves-COORD-correctly (post-reclassification) OR still-reads-stale-PRIMARY (must migrate in T055). Record the classification in `tracers/design-decisions.md`.
- **Files**: read-only + tracer note.
- **Validation**: a written enumeration with a fail/whitelist verdict per site, **including a per-reader COORD/stale-PRIMARY verdict for every `traces/` read site**.

### Subtask T032 – Fail-loud `read_dir` authority

- **Purpose**: FR-004 — the read authority raises a typed partition-mismatch error.
- **Steps**: At `resolution.py:1403`, make `read_dir(kind)` resolve through `artifact_home_for(kind).read_surface` and raise a typed `PartitionMismatch`-style error when a coord-homed kind resolves to a primary substitute. Whitelisted degrades from T031 short-circuit BEFORE the raise.
- **Files**: `src/mission_runtime/resolution.py`.
- **Validation**: a coord-homed read against a primary substitute raises; whitelisted degrades do not.

### Subtask T033 – Apply the `resolution.py:949` consumer adjustment (WP02 handoff)

- **Purpose**: FR-002 tail — the sole `commit_target` consumer must tolerate WP02's non-None flip.
- **Steps**: Read WP02's T005 audit note. **Expected outcome (post-tasks squad): the audit is CONFIRMED-INERT** — only `resolution.py:949` reads the port `home.commit_target` and it does not branch on `None`-as-skip (the `tasks_map_requirements.py` hits are a different `MergeState.commit_target`). Therefore this adjustment is **cosmetic**: add a regression **asserting inertness** (the `:949` consumer is unaffected by the non-None flip). Only if WP02's audit came back non-inert do you apply an actual consumer edit here. **Fallback**: if a future change makes the sentinel non-inert, a WP09→WP07 dependency must be added (recorded in WP02 T005) so birth-cutover cannot race this consumer.
- **Files**: `src/mission_runtime/resolution.py`.
- **Validation**: an inertness regression is green (consumer unaffected by the flip); OR, if non-inert, the consumer behaves correctly with the flipped sentinel.

### Subtask T034 – Fold #2906 accept-time guards into the authority

- **Purpose**: convergence — one read authority, not a parallel guard.
- **Steps**: Refactor `acceptance/execution_context.py:203-223` and `acceptance/gates_core.py:436` so their substitution-refusal **delegates** to the new `read_dir` authority. The lenient diagnose path (#2906) must remain lenient (whitelisted in T031).
- **Files**: `src/specify_cli/acceptance/execution_context.py`, `src/specify_cli/acceptance/gates_core.py`.
- **Validation**: accept-time reads still refuse substitution, now via the authority; the diagnose path stays lenient.

### Subtask T035 – New read gate (reuse WP06 scanner)

- **Purpose**: FR-004 — an arch gate symmetric to the write gate.
- **Steps**: Create `tests/architectural/test_read_surface_placement_guard.py` reusing `tests/architectural/_placement_whole_tree_scan.py` (from WP06). Assert mission-artifact reads resolve through `artifact_home_for(kind).read_surface`; a synthetic wrong-partition read reds.
- **Files**: `tests/architectural/test_read_surface_placement_guard.py` (new).
- **Validation**: green; a synthetic substituted read reds and names the site.

### Subtask T036 – Red-first lenient-degrade regressions

- **Purpose**: NFR-002 — prove the whitelisted degrades stay lenient.
- **Steps**: For each whitelisted degrade from T031, add a test asserting it still degrades gracefully (no new raise): `StatusReadPathNotFound` paths, coord-worktree-absent flatten, #2906 diagnose. Add the true-mismatch red counterpart.
- **Files**: extend `tests/architectural/test_read_surface_placement_guard.py` (or a sibling regression under `tests/regression/`).
- **Validation**: lenient paths green (still lenient); true mismatch reds.

### Subtask T055 – Close the `traces/` read leg (FR-006 read-side)

- **Purpose**: FR-006 read leg — WP02 reclassifies `traces/` PRIMARY→COORD (WP03 routes the *writes*), but no WP yet migrates the live `traces/` **read** sites. A read left pointing at the stale PRIMARY location after the write moves to COORD is a silent split.
- **Steps**: Using the T031 enumeration, migrate/verify **every** `traces/` read site to resolve the COORD `read_surface`. Enumerate via `grep -rn "traces/" src/` and cover at least the five named modules: `retrospective/generator.py`, `lanes/merge.py`, `charter_runtime/freshness/computer.py`, `cli/commands/merge_driver.py`, `init.py`. For each: confirm the post-reclassification read resolves **COORD**, not the stale PRIMARY location. These modules are **read-only-touched by this WP's authority routing** — do NOT pre-emptively add them to `owned_files`. **If a specific reader needs an actual edit** to route through the read authority (e.g. it hard-codes the PRIMARY path), make that edit as **documented leeway from WP07** (record the file + rationale in `tracers/design-decisions.md`) since `resolution.py` (the read authority) is WP07-owned and the reader change is a direct consequence of the authority routing; confirm no owned_files overlap with another WP before editing.
- **Files**: read/verify the five named modules (+ any grep surfaces); `resolution.py` (authority); documented-leeway edit to a specific reader only if required.
- **Validation**: T031's whitelist/verdict enumeration includes `traces/`; every `traces/` read resolves COORD post-reclassification (asserted in the read gate / a regression); no reader still resolves the stale PRIMARY `traces/` location.

## Test Strategy

- New: `tests/architectural/test_read_surface_placement_guard.py`.
- Run: the read gate + acceptance suites + the coord/flat degrade regressions.

## Definition of Done

- `read_dir` fails loud on mismatch; whitelisted degrades preserved.
- #2906 guards delegate to the authority (no parallel guard).
- FR-006 read leg closed (T055): every `traces/` read site resolves COORD post-reclassification; no stale-PRIMARY reader remains.
- `resolution.py:949` consumer handled per WP02 handoff (CONFIRMED-INERT → inertness regression, unless non-inert).
- Read gate reuses WP06 scanner; synthetic mismatch reds; no new top-level `specify_cli` import.
- `ruff` + `mypy` clean.

## Risks & Mitigations

- **68-site blast radius breaks a degrade** → T031 enumeration + T036 red-first per degrade.
- **Double-guard drift** → T034 delegates rather than duplicates.
- **Layering regression** → no new top-level `specify_cli` import.

## Review Guidance

- Verify every lenient degrade is enumerated and has a preserving test.
- Verify #2906 guards DELEGATE (not sit beside) the authority.
- Verify no new top-level `specify_cli` import in `resolution.py`.

## Activity Log

- 2026-07-25T12:00:00Z – system – Prompt created.
