# Implementation Plan: Mission-identity naming seam & #1908 panel hardening

**Branch**: `mission/mission-identity-seam-and-1908-panel` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)
**Input**: `kitty-specs/mission-identity-seam-and-1908-panel-01KV6510/spec.md`

## Summary

Two adversarial-review clusters. **Cluster A** consolidates the `slug↔mid8↔name`
mapping onto the existing seam `src/specify_cli/lanes/branch_naming.py`: fix the
idempotency bug in `mission_branch_name` (#1949) and the heuristic false-positive
in `mid8_from_slug` (#1918), add a `worktree_dir_name` grammar (the filesystem
twin, #1899) with a 4th ratchet, and route the two outliers through the seam —
the merge preflight `_check_mission_branch` (#1978, P1 driver) and the worktree
allocator's name-guessing f-string. **Cluster B** lands three independent TDD
fixes: lane-merge atomicity (#1915), base-ref `--` separator (#1917), and moving
accept-gate `ensure_identity` off the readiness path + retiring its stopgap
(#1916). All TDD-first; bounded surface; #1978 sequenced early (dogfooding —
this mission's own slug embeds its mid8). See [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer (CLI), pytest, ruff, mypy; internal:
`specify_cli.lanes.branch_naming` (the seam), `specify_cli.lanes.worktree_allocator`,
`specify_cli.merge.preflight`, `specify_cli.cli.commands.implement`,
`specify_cli.acceptance`, `specify_cli.identity.project`
**Storage**: N/A (git refs + `lanes.json`; no data layer)
**Testing**: pytest — new property/round-trip test for the seam (NFR-003), per-bug
failing-first regression tests (TDD), plus the existing `tests/architectural`
ratchet suite (a 4th ratchet assertion for worktree-name grammar, #1899)
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows)
**Project Type**: single (Python CLI package)
**Performance Goals**: N/A (correctness fixes; no hot-path/throughput change)
**Constraints**: Bounded surface (NFR-001) — diffs limited to `branch_naming.py`,
`worktree_allocator.py`, `merge/preflight.py`, `implement.py`, `acceptance/__init__.py`,
`identity/project.py` (write-boundary only) + their tests; no edits to unrelated
`status/`/`task_utils/` hot paths. TDD-first (C-001). PR-bound (C-003).
**Scale/Scope**: 7 issues across 2 clusters; ~6 implementation concerns; the seam
module + 5 call-site files.

## Charter Check

*GATE: Must pass before Phase 0. Re-check after Phase 1.*

- **ATDD-First (C-011) / DIRECTIVE_003**: every fix lands with a failing-then-passing
  regression test (FR-009/C-001). ✔
- **Single-authority / canonical-seam** (epic #1868): compose+parse bound to one
  module; call sites must not re-derive names. ✔
- **No-test-deletion-to-pass / high-risk discipline**: bug fixes add tests; the
  #1916 stopgap retirement removes code with its now-unneeded filter, not tests. ✔
- **Mission-identity model (083)** is fixed; only name derivation/parsing changes
  (out-of-scope: renaming mid8/mission_id/mission_slug). ✔
- **PR-bound, no direct origin/main push (C-003)**. ✔
- No charter violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)
```
kitty-specs/mission-identity-seam-and-1908-panel-01KV6510/
├── plan.md  ├── spec.md  ├── research.md
├── checklists/requirements.md  ├── decisions/  └── tasks/   (Phase 2)
```

### Source Code (repository root)
```
src/specify_cli/
├── lanes/branch_naming.py            # SEAM — mid8_from_slug(#1918), mission_branch_name(#1949), +worktree_dir_name(#1899)
├── lanes/worktree_allocator.py       # route worktree f-string→seam (#1899); _merge_dependency_lane_tips atomicity (#1915)
├── merge/preflight.py                # _check_mission_branch → use seam/lanes.json mission_branch (#1978)
├── cli/commands/implement.py         # _validate_base_ref `--` separator (#1917)
├── acceptance/__init__.py            # ensure_identity off readiness + retire _filter_accept_owned_project_config (#1916)
└── identity/project.py               # ensure_identity stays; called only at write-authorized boundary

tests/
├── lanes/  (seam round-trip/property + #1949/#1918/#1915 regressions)
├── architectural/  (4th ratchet assertion for worktree-name grammar, #1899)
├── merge/  (#1978 preflight regression)
├── specify_cli/cli/commands/ (#1917 base-ref)
└── (accept readiness regression for #1916)
```

**Structure Decision**: Single Python CLI package; all edits under
`src/specify_cli/lanes|merge|cli/commands|acceptance|identity` + tests. No new
modules (the seam already exists; we extend it).

## Complexity Tracking
*No charter violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Seam core: idempotent compose, demoted parse, worktree grammar (+ property test)
- **Purpose**: Make `branch_naming.py` the genuine single authority: idempotent
  compose keyed on `(slug, mission_id)` (#1949), `mid8_from_slug` demoted to
  best-effort non-authoritative (#1918), a **canonical-first / legacy-failover**
  resolve path (try new style; fall over to legacy `NNN-`/bare only on a miss with
  a one-shot deprecation warning — FR-004), add `worktree_dir_name()` ==
  `lane_branch_name(...)` minus prefix + an emit-don't-guess `worktree_path()`
  (#1899 grammar), and the `(slug, mission_id)`-keyed round-trip property test
  (incl. a legacy-failover-emits-warning case).
- **Requirements**: FR-001, FR-003, FR-004, FR-005 (grammar), NFR-003, FR-009.
- **Surfaces**: `lanes/branch_naming.py`; `tests/lanes/` property test.
- **Sequencing**: first (everything routes through it).
- **Risks (paula F-3/F-4)**: round-trip is keyed on declared `mission_id`, not the
  bare string (unsatisfiable otherwise); `worktree_dir_name` must be byte-identical
  to the existing on-disk f-string form for embedded slugs (no churn). Back-compat
  with legacy `NNN-` (no mid8).

### IC-02 — #1978 false-compose fix via `mission_branch_name_required` (P1 driver)
- **Purpose**: Stop the merge-blocking false-negative for mid8-embedded slugs.
- **Requirements**: FR-002, FR-009, SC-001.
- **Surfaces**: `cli/commands/merge.py:1231` fallback + `merge/preflight.py`
  `_check_mission_branch` + `runtime/next/runtime_bridge.py:109` — replace the
  `kitty/mission-{slug}` f-string with `mission_branch_name_required(slug, mission_id)`
  (fail-closes; `lanes.json` may be absent on legacy/flattened missions — paula F-5).
- **Sequencing**: right after IC-01 (dogfooding C-005 — this mission's own merge).
- **Risks**: must still resolve legacy/non-embedded missions; fail-closed on truly
  unresolvable modern missions (existing `BranchIdentityUnresolved`).

### IC-03 — #1899 route ALL worktree-dir sites + literal-ban ratchet
- **Purpose**: Single-authority worktree dir-names everywhere (paula F-1).
- **Requirements**: FR-005, FR-001, FR-009, SC-002.
- **Surfaces**: route through `worktree_dir_name()`/`worktree_path()` (IC-01) the
  ~12 leak sites — P1 hot-path: `lanes/{worktree_allocator:127, merge:83,
  recovery:392/593/608, lifecycle_sync:150/157, implement_support:120}`,
  `cli/commands/merge.py:2768`; then `workspace/context.py:310/811/847/867`,
  `orchestrator_api/commands.py:475`, `cli/commands/agent/tasks.py:1333`. Replace
  the `tests/architectural` worktree-name spot-check with a **literal-ban** ratchet
  (no `.worktrees/.../f"{…}-{lane…"` outside the seam).
- **Sequencing**: after IC-01.
- **Risks**: emit byte-identical names → no on-disk churn (IC-01 guarantees it).

### IC-07 — #1878 slice: unify the `coordination/` parallel compose/parse (paula F-2)
- **Purpose**: Make the seam the ONLY algorithm — delegate the 3+ duplicate
  coordination impls so FR-001 actually holds.
- **Requirements**: FR-010, FR-001, FR-009.
- **Surfaces**: `coordination/workspace._compose_mission_dir` (:93/154/159),
  `coordination/transaction._mission_specs_dir_name` (:152),
  `coordination/status_transition._transaction_dir_name` (:75),
  `coordination/surface_resolver._coord_mid8` (:363) — delegate to the seam.
- **Sequencing**: after IC-01; independent of IC-02/03 but shares the seam.
- **Risks**: `coordination/` is the #1878 strangler's turf — coordinate; emit
  byte-identical dir names (no coord-worktree churn). HIGH-CARE: status/coord
  read paths depend on these names.

### IC-04 — #1915 lane-merge atomicity
- **Purpose**: Multi-dependency lane merge rolls back fully on a later-dep conflict.
- **Requirements**: FR-006, FR-009, SC-004.
- **Surfaces**: `lanes/worktree_allocator.py::_merge_dependency_lane_tips` —
  snapshot ref before the loop; reset to snapshot on any conflict.
- **Sequencing**: independent.

### IC-05 — #1917 base-ref `--` separator
- **Purpose**: Treat `--base` value as a ref, not an option.
- **Requirements**: FR-007, FR-009, SC-005.
- **Surfaces**: `cli/commands/implement.py::_validate_base_ref`.
- **Sequencing**: independent.

### IC-06 — #1916 accept-gate identity side-effect off readiness
- **Purpose**: `accept --no-commit` is side-effect-free; retire the stopgap.
- **Requirements**: FR-008, FR-009, SC-006.
- **Surfaces**: `acceptance/__init__.py` (move `ensure_identity` off readiness;
  remove `_filter_accept_owned_project_config` + its caller); confirm a
  write-authorized boundary still mints identity.
- **Sequencing**: independent.
- **Risks**: ensure no readiness path still depends on identity being minted;
  removing the filter must not reintroduce a dirty-tree false-positive.

## Phase 0 — Research
Complete. [research.md](research.md): R1 (seam already exists → consolidate),
R2 (call-site map: routed vs. the #1978/#1899 outliers), R3 (the two in-seam
bugs + round-trip invariant), R4 (Cluster B sites), R5 (dogfooding sequencing).

## Phase 1 — Design & Contracts
- **Data model**: none (git refs + `lanes.json`; no entities/schema). data-model.md
  intentionally omitted.
- **Contract** = the seam's behavioral contract, encoded as tests: round-trip +
  idempotency property test (NFR-003), per-bug regressions (#1949/#1918/#1978/
  #1915/#1917/#1916), and the 4th worktree-name ratchet (#1899). No HTTP/API
  contracts apply.
- **Coordination note**: `mission create` spun up a coordination branch/worktree.
  Per the #1797 lesson (flattening broke multi-lane implement), decide flatten-vs-keep
  deliberately at tasks/implement; default to keeping coordination and using the
  consolidate-off-mission fallback only if the multi-lane machinery misfires.

## Post-Planning Brownfield Checks (standing) — DONE

- **Mechanical scan:** found 3 more false-compose sites beyond the spec's original
  2 — `runtime_bridge.py:109` (#1978-class), `merge.py:1231` (the actual #1978
  fallback), `agent/tasks.py:844` (hand-rolled idempotent compose). Deprecation
  check: clean. Foldable: #1887/#1907 are worktree-*placement* bugs under the
  #1878 strangler — **left out** (different class), noted.
- **paula-patterns design review (operator-requested): SOUND-WITH-FIXES.** Verdict:
  `branch_naming.py` is the right authority but the original seam scope was
  materially undersized — ~16 leak sites + a **parallel compose/parse impl in
  `coordination/`**, and the bare-string round-trip invariant is unsatisfiable.
  5 findings (F-1..F-5 blocker/major) folded into the spec/plan:
  - F-1 → IC-03 (route ALL ~12 worktree-dir sites; literal-ban ratchet; NFR-001
    surface expanded).
  - F-2 → **IC-07** (unify `coordination/` parallel impls — #1878 slice; FR-010).
  - F-3 → FR-004/NFR-003 rewritten: round-trip keyed on `(slug, mission_id)`;
    `mid8_from_slug` demoted to non-authoritative.
  - F-4 → IC-01: `worktree_dir_name` derived from `lane_branch_name`,
    idempotency-preserving (no on-disk churn); emit-don't-guess `worktree_path()`.
  - F-5 → IC-02: #1978 via `mission_branch_name_required` (not just lanes.json) +
    `runtime_bridge.py:109`.
  - F-6 → spec invariant "readiness paths are side-effect-free" (#1916).
- **Operator decision:** FULL consolidation (all ~16 sites + `coordination/`).
  Mission re-scoped accordingly; **advances #1878** (does not close it).

## Post-Tasks Squad Remediation (2026-06-15) — IC widening + IC→WP map

A second adversarial squad ran **after** `/spec-kitty.tasks` (paula/alphonso/debbie/renata) and
verified the decomposition was still under-scoped. Operator decisions: **(A) fold the `missions/`
composers into the consolidation; (B) in-place demote `mid8_from_slug` and own ALL callers.** The
spec (FR-004/FR-005/FR-010, NFR-001) and tasks (10 WPs incl. new WP10) were widened accordingly. The
ICs above are extended (not replaced) as follows:

- **IC-01** also adds an authoritative `resolve_mid8(slug, *, mission_id)`, a **bare**
  `mission_dir_name`/coord-branch/coord-dir primitive (the non-lane delegation target the
  coordination/missions composers need), a **legacy-faithful** `worktree_dir_name` (`mission_id=None`
  ⇒ no mid8, so non-embedded slugs do not churn), and a **shared golden-value name table** that is the
  binding byte-identical oracle for all routing WPs. #1949 is treated as a regression-LOCK (already
  idempotent) plus the genuine `mission_id=None` residual.
- **IC-02** site corrected: the two false-compose sites are `cli/commands/merge.py:1231`
  (`_check_mission_branch`) and `merge/preflight.py:86` (NOT a `_check_mission_branch` in preflight);
  plus `runtime_bridge.py:109` and its `mid8_from_slug` callers.
- **IC-03** adds the previously-unrouted `orchestrator_api/commands.py:771` and the assign-then-join
  indirection in `workspace/context.py`; the **literal-ban ratchet bans the recurrence shape**
  (`endswith(f"-{mid8}")` dedup), not just `.worktrees/` literals, + a NFR-001 diff-scan.
- **IC-07** widened to **all** parallel composers: the 4 `coordination/` functions PLUS
  `missions/_create.coordination_branch_name` (live coord-branch composer) and
  `_read_path_resolver._compose_mission_dir` / `feature_dir_resolver`.
- **New concern (no prior IC) — parse-caller routing:** the in-place `mid8_from_slug` demotion's
  ~12-caller blast radius. Caller-owning WPs route their own files; the unowned remainder is **WP10**.

**IC→WP map:** IC-01→WP01 · IC-02→WP02 · IC-03→WP03/WP04/WP05(+WP09 ratchet) · IC-04→WP03 · IC-05→WP07
· IC-06→WP08 · IC-07→WP06 · parse-caller routing→WP10 (+ in-file routing in WP02/WP05/WP06/WP08).
Dep DAG: WP02/03/04/05/06/10 ← WP01; WP09 ← all routing; WP07/WP08 independent.
