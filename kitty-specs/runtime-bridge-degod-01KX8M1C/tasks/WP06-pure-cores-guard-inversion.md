---
work_package_id: WP06
title: Pure cores + guard inversion (FR-009)
dependencies: [WP05]
requirement_refs:
- FR-009
- FR-003
- FR-004
- NFR-003
tracker_refs:
- '2531'
planning_base_branch: design/runtime-bridge-degod
merge_target_branch: design/runtime-bridge-degod
branch_strategy: Planning artifacts for this mission were generated on design/runtime-bridge-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/runtime-bridge-degod unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
phase: Extraction spine
shell_pid: '2442747'
history:
- at: '2026-07-11T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- src/runtime/next/runtime_bridge_cores.py
- tests/runtime/test_bridge_cores.py
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge_cores.py
- src/runtime/next/runtime_bridge.py
- tests/runtime/test_bridge_cores.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Pure cores + guard inversion (FR-009)

## Context

`src/runtime/next/runtime_bridge.py` is the repo's largest module (3,813 LOC). This WP
carves out its **pure leaves** into a new sibling `runtime_bridge_cores.py` — the
zero-dependency tasks.md parse family and the guard-evaluation logic, inverted so the
decision is a pure function over a fact snapshot rather than an I/O-interleaved walk.
It is a **behavior-preserving structural refactor** (C-001): logic is relocated and
re-shaped, never changed.

This is the fifth extraction on the **serial spine** — every extraction edits
`runtime_bridge.py` to move symbols out, so the allocator collapses these WPs onto the
shared parent file. WP06 depends on **WP05** because the guard inversion consumes the
`gather_artifact_presence` fact-port that WP05 lands in `runtime_bridge_io.py`
(data-model.md §ArtifactPresenceSnapshot). It depends on **WP01/WP02** because the parity
oracle and the compat-surface guard are the blocking safety nets (C-004): both MUST be
green before and after this extraction.

**Serial co-ownership note:** `runtime_bridge_cores.py` is *created here* and *also edited by
WP07* (the Decision-builder), which is why WP07 depends on WP06 and both list the file in
`create_intent`. Land the module with a clean top-of-file structure WP07 can append to
without churn.

### What moves here (research.md §Seams; plan.md IC-05)

1. **tasks.md parse family** — the zero-dependency pure leaf at `runtime_bridge.py:343–473`:
   `_extract_wp_heading:343` (CC≈21), `_parse_wp_sections_from_tasks_md:383`,
   `_parse_requirement_refs_from_tasks_md:416`, `_collect_requirement_refs_for_section:424`,
   `_iter_requirement_refs:447`, `_requirement_inline_refs_suffix:452`,
   `_is_requirement_heading:463`. These touch no filesystem, no `meta.json`, no git — pure
   string→data leaves (NFR-003).
2. **Guard inversion (FR-009)** — the `ArtifactPresenceSnapshot` consumer: a pure
   `evaluate_guards(snapshot) -> list[str]` core collapsing **all three** guard offenders
   into one fact-port/pure-core seam:
   - `_check_cli_guards:1057` (CC≈19, `# noqa: C901`)
   - `_check_composed_action_guard:1515` (CC≈45–48, `# noqa: C901`)
   - `_check_requirement_mapping_ready:1122` (CC≈22) — a CLI-guard sub-helper folded into the
     same inversion (T023).

### The load-bearing invariants (SC-007 — highest-risk relocation)

- **Preserve the fail-closed default.** Both guards default to *failing closed* (silent-pass
  was the v1 P1 bug the current code fixes). The relocated `evaluate_guards` MUST reproduce
  both fail-closed defaults exactly.
- **`guard_failures` identical incl. order.** The returned failure list must match the
  pre-refactor list **content and order**, byte-for-byte after normalization, for every guard
  branch and every mission family (software-dev / research / documentation), **including** the
  4-way `tasks` `legacy_step_id` union. These are the named highest-risk fixtures in
  research.md §Parity — assert them explicitly.

## Ordered Steps

### T021 — Create `runtime_bridge_cores.py`; move the tasks.md parse family

1. Create `src/runtime/next/runtime_bridge_cores.py` with a top-of-file docstring naming its
   responsibility (pure cores) and a `#2531` decomposition pointer per the sibling convention
   (FR-007; matches #2057/#2464).
2. Move the parse family verbatim from `runtime_bridge.py:343–473`:
   `_extract_wp_heading`, `_parse_wp_sections_from_tasks_md`,
   `_parse_requirement_refs_from_tasks_md`, `_collect_requirement_refs_for_section`,
   `_iter_requirement_refs`, `_requirement_inline_refs_suffix`, `_is_requirement_heading`.
   Confirm zero non-stdlib imports travel with them — this is the flagship pure leaf.
3. In `runtime_bridge.py`, replace the definitions with a **guarded re-export** so every name
   remains reachable at `runtime_bridge.<name>` (FR-012). Add each moved patched name to the
   explicit compat re-export block; do **not** rely on `__all__` (it governs only `import *`).
4. Import DAG: `cores` may import only stdlib / `Lane` / decision types (research.md §Import
   DAG). No import of `runtime_bridge_io`/`_engine`/`_composition`/`_identity` and no
   `decision → runtime_bridge_*` top-level edge (C-007).

### T022 — `ArtifactPresenceSnapshot` + pure `evaluate_guards(snapshot)`

1. Consume the `ArtifactPresenceSnapshot` value object produced by WP05's
   `gather_artifact_presence(feature_dir, …)` port (fields: `present_artifacts`,
   `status_facts`, `mission_family`, `step_id`/`legacy_step_id` — data-model.md §FR-009). If
   the shape is insufficient to reproduce a branch, extend the snapshot (data-only, no I/O) and
   coordinate the field back into WP05's port rather than re-adding I/O to the core.
2. Write `evaluate_guards(snapshot) -> list[str]` as a **pure** function (no filesystem, no
   git, no `meta.json`) folding the branch logic of `_check_cli_guards`,
   `_check_composed_action_guard`, and `_check_requirement_mapping_ready` over the snapshot
   facts. The port gathers; the core decides.
3. **Preserve the fail-closed default** for both guards and the `tasks` legacy-union path.
   Keep the exact ordering of appended failure strings — the residual/port must call the core
   at the same point in the flow so `guard_failures` is order-identical (SC-007).
4. In `runtime_bridge.py`, rewrite the three guard functions as thin residual delegates that
   build (or receive) the snapshot and return `evaluate_guards(snapshot)`, preserving each
   function's public/patched signature (compat surface — `_check_cli_guards` is patched 26×,
   the heaviest symbol in research.md §Compat). The compat guard (WP02) drives each through its
   reaching entry, so the delegates must stay reachable and behavior-identical.

### T023 — Reduce `_check_requirement_mapping_ready` (CC≈22) ≤15

1. Fold `_check_requirement_mapping_ready:1122` into the same fact-port/pure-core inversion so
   its filesystem/status reads become snapshot facts and its decision becomes part of (or a
   helper of) `evaluate_guards`.
2. Split the remaining branch logic into small named pure helpers so both the residual delegate
   and every core helper land **≤15** (`ruff --select C901` reports zero offenders; radon
   confirms). Do **not** relocate a `# noqa: C901` — remove it (FR-004/NFR-002).

### T024 — Pure unit tests; re-export; oracle + compat green

1. Create `tests/runtime/test_bridge_cores.py` with direct in-memory unit tests (NFR-003 /
   SC-004): no filesystem, no `meta.json`, no git.
   - Parse family: realistic tasks.md fragments (production-shaped WP ids/headings, requirement
     refs) → assert parsed structures.
   - `evaluate_guards`: construct `ArtifactPresenceSnapshot` fixtures per mission family and per
     guard branch; assert `guard_failures` **content and order**. Include the **two fail-closed
     defaults** and the **`tasks` legacy-union** as named fixtures asserting identical failure
     lists.
2. Confirm the guarded re-export identity holds (`runtime_bridge.x is runtime_bridge_cores.x`)
   for every relocated patched symbol.
3. Re-run the acceptance gate (see below).

## Acceptance

- `runtime_bridge_cores.py` exists; parse family + `evaluate_guards` relocated; import DAG
  acyclic (cores importing only stdlib/`Lane`/decision types).
- `evaluate_guards` is pure (no I/O) and preserves the fail-closed default; `guard_failures`
  identical (content + order) before/after across all three mission families incl. the `tasks`
  legacy-union (SC-007).
- `_check_cli_guards`, `_check_composed_action_guard`, and `_check_requirement_mapping_ready`
  are each **≤15**; the two `# noqa: C901` markers on the guards are **removed**, not relocated
  (`ruff --select C901` zero offenders on the touched functions; radon confirms).
- `tests/runtime/test_bridge_cores.py` has ≥1 direct in-memory unit test per pure core with no
  I/O (NFR-003/SC-004).
- **Acceptance gate (every extraction WP):** re-export of the moved patched symbols in place;
  the **WP01 parity oracle green** on all 3 entries at the full coverage floor; the **WP02
  compat-surface guard green** (each relocated symbol's sentinel still fires through its
  reaching entry — no false-green).

## Safeguards

- The two fail-closed defaults + the `tasks` legacy-union are the highest-risk relocation
  fixtures (research.md §Parity, plan.md IC-05). Do not "clean up" a failure string or reorder
  appends — that is a parity break.
- Purity means **no-I/O + port-injected**, NOT "no `specify_cli` import" (FR-003/C-002).
  runtime and specify_cli are co-equal production packages — there is no arch gate between them.
- Keep the compat delegates' signatures byte-identical to what tests patch; `_check_cli_guards`
  is the most-patched symbol in the mission (26×) — a signature drift silently breaks 26 tests.
- Do not touch WP07's future territory in `runtime_bridge_cores.py` (the Decision-builder) —
  leave the module structured so WP07 appends cleanly (serial co-ownership).
- Never stub `next_step` in any oracle re-run — it is the logic under test (contracts/parity-oracle.md).

## References

- `src/runtime/next/runtime_bridge.py:343` — `_extract_wp_heading` (CC≈21), start of the pure parse family (`:343–473`).
- `src/runtime/next/runtime_bridge.py:1057` — `_check_cli_guards` (`# noqa: C901`, CC≈19).
- `src/runtime/next/runtime_bridge.py:1122` — `_check_requirement_mapping_ready` (CC≈22, T023).
- `src/runtime/next/runtime_bridge.py:1515` — `_check_composed_action_guard` (`# noqa: C901`, CC≈45–48).
- `kitty-specs/runtime-bridge-degod-01KX8M1C/data-model.md` — `ArtifactPresenceSnapshot`, `evaluate_guards`, `gather_artifact_presence` port (WP05).
- `kitty-specs/runtime-bridge-degod-01KX8M1C/research.md` §Seams / §Parity — module boundaries, fail-closed fixtures, import DAG.
- `kitty-specs/runtime-bridge-degod-01KX8M1C/contracts/parity-oracle.md` — the acceptance-gate oracle.
- `kitty-specs/runtime-bridge-degod-01KX8M1C/contracts/compat-surface.md` — the compat guard + re-export rules.
- `kitty-specs/runtime-bridge-degod-01KX8M1C/spec.md` — FR-009, FR-003, FR-004, NFR-003, SC-007.

## Activity Log

- 2026-07-11T21:46:42Z – user – shell_pid=2442747 – Moved to for_review
- 2026-07-11T21:54:19Z – user – shell_pid=2442747 – Moved to approved
