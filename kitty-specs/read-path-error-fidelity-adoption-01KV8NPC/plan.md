# Implementation Plan: Read-Path / Error-Fidelity Adoption

**Branch**: `feat/read-path-error-fidelity` (stacked on `feat/naming-rider-3-2-1` / PR #2012) | **Date**: 2026-06-16 | **Spec**: `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/spec.md`
**Input**: Feature specification from `/kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/spec.md`

## Summary

Adoption/routing refactor onto the EXISTING canonical read-path authority
(`resolve_action_context` → `ExecutionContext` / `ActionContextError`,
`mission_runtime/resolution.py:689`). Six commands fail in Robert's #2007 run because they **flatten**
the resolver's typed error or hold a **second authority** wrapping it. This mission finishes the
adoption (route the bypassers, preserve typed errors end-to-end), makes the two root resolvers agree on
the submodule case, adds the missing primary-target-branch leg to the committed-check, and freezes the
`ExecutionContext` composite with a build-time invariant. **C-001: adopt, do not build** — no new
resolver, root authority, or error type. Phase 0 (`research.md` + `research/call-site-inventory.md` +
`research/live-repro.md`) verified every call-site and live-repro'd every fix against HEAD `87697e5e4`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, subprocess/pygit2 git, pytest, mypy, ruff (existing spec-kitty stack)
**Storage**: filesystem — `kitty-specs/<mission>/` planning artifacts, `status.events.jsonl`, git worktrees/coord branches
**Testing**: pytest; function-over-form behavioral tests + verification-by-deletion; topology-true fixtures (real 26-char ULID, real coord-worktree + real submodule); TDD-first for behavioral fixes; the naming architectural ratchet is OUT of scope
**Target Platform**: Linux/macOS developer + CI (the spec-kitty CLI)
**Project Type**: single (CLI tool — `src/specify_cli/` + `src/mission_runtime/` + `src/runtime/`)
**Performance Goals**: N/A (correctness/fidelity mission); resolution stays O(existing)
**Constraints**: behavioral equivalence across primary/coord/submodule input classes (NFR-001); bounded conflict surface — named files only (NFR-005); idempotency-preserving (no on-disk worktree/coord churn); ruff+mypy clean, complexity ≤15, no suppressions (NFR-004)
**Scale/Scope**: ~17 call-sites across 8 owning files; 7 implementation concerns; no schema/data migration

## Charter Check

*GATE: software-dev-default charter (compact mode). Directives DIR-001..DIR-013. Re-checked post-design — clean.*

- **DIR-001 (one owning module per concern):** satisfied — the IC partition assigns each shared file to
  exactly one IC; `agent/mission.py` (4 call-sites) is owned solely by IC-03.
- **DIR-003 (decisions documented):** D-1 recorded as decision `01KV8Q49WEG9RRKCEZ3XYN5DWP` (resolved);
  D-2..D-5 documented below.
- **DIR-031 (bounded-context translation):** the typed-error pass-through + the `decision` escape-check
  fix are pure boundary translations — no new error type (C-001).
- No charter conflicts. Loopback/HTTP, security-hotspot, and terminology gates are not implicated.

## Decisions (locked)

- **D-1 (C-005 scope — decision `01KV8Q49WEG9RRKCEZ3XYN5DWP`):** **DEFER #1716 entirely** (write-side
  topology, ~2094 LOC, not required for read-path equivalence, would violate C-001 + explode NFR-005).
  **CARRY #1993 minimal** (~20 LOC `resolve_lanes_dir` seam, owned by IC-05 with #1832).
- **D-2 (FR-009 rule):** enforce `context.target_branch == branch_ref.target_branch` at build via
  **reject-on-mismatch** (`CONTEXT_INVARIANT_VIOLATION`) + **freeze the `ExecutionContext` composite**.
  Do NOT normalize; do NOT retire the flat substrate (larger #1619 grain, deferred). The spec's
  `branch_name == branch_ref.target_branch` wording is superseded — `branch_name` is the WP lane branch
  and is expected to differ.
- **D-3 (#1827 — FR-012):** **verified-already-fixed**; deliver a full-sequence (incl. resume)
  regression test only, NO code fix (debbie live-repro PASSED on HEAD).
- **D-4 (#8 — FR-003):** delete the escape-walk for *resolved* paths and stop the typed error surfacing
  as a raw traceback; keep `_SAFE_SLUG_RE` traversal-rejection on the raw operator token only.
- **D-5 (FR-006):** narrowed — the hard-failure swallow is already fixed; deliver "report the real
  commit hash + distinguish genuine-unchanged from no-op-against-wrong-surface".
- **D-6 (read/write-symmetry seam — investigation-2/3, synthesis `docs/engineering_notes/context-factory-readwrite-symmetry/00-SYNTHESIS.md`):**
  IC-01 is **re-scoped** from "freeze + invariant" to **"establish the single named context factory
  (`build_execution_context`) + freeze + invariant + declare the write-projection boundary contract."**
  Construction is already single-sited (one `ExecutionContext(` call, `resolution.py:739`); the factory
  *names* that site, freezes the product, and is the sole construction door. **`branch_naming` stays a
  collaborator** (not absorbed — #2012 bounded context). The factory encapsulates identity/topology
  resolution so the deferred write-side (#1716/#1878, Mission B) **adopts against a frozen seam — not a
  rewrite**. **D-1 stays.** Boundary contract: *write surfaces compose names/paths/identity from a
  factory-projected `IdentityFragment` + `BranchRefFragment` (+ workspace/surface); they MUST NOT
  re-derive `mission_id`/`mid8`/`primary_root` independently.* Fragment retirement limited to
  `prompt_source` + the dead `StatusSurfaceFragment surface=` read-param.
  > ⚠️ **The "factory boundary" is a documented docstring CONTRACT (a MUST-NOT-re-derive-identity
  > rule), NOT an importable callable API.** WP01 ships a package-PRIVATE factory + the contract
  > docstring; it does **NOT** add an identity-projection symbol to `mission_runtime.__all__` (which
  > exposes only `resolve_placement_only` / `CommitTarget`, no mid8 door). Consumers (IC-02b/M3,
  > IC-03, IC-04, IC-05) **honor** the contract via the **primitive pattern** — read the real
  > `mission_id` from meta and pass it to `resolve_mid8(slug, mission_id=<real>)` (the `decision.py:421`
  > / `context.py:73` shape) — never by importing a projection callable (none exists) and never by
  > seeding empty identity.
- **D-7 (net-new surfaces — debbie, fold into this mission):** **M1** `context mission-resolve` typed-error
  flatten (`context/resolver.py:164` — corrected from `context/mission_resolver.py`, which has no flatten) and **M2** orchestrator-api flatten across 8 endpoints
  (`orchestrator_api/commands.py:263-266`) extend IC-02; **M3** orchestrator empty-`mid8` suppressing the
  coord-aware fail-closed guard is a read-path SAFETY fix tied to the IC-01 identity boundary. Robert's
  `merge.py` routing (#1956/#1972) is **verify-don't-redo** (no IC owns it).

## Project Structure

### Documentation (this mission)

```
kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/
├── plan.md              # This file
├── research.md          # Phase 0 synthesis (+ research/call-site-inventory.md, research/live-repro.md, research/priti-related-issues-sweep.md)
├── contracts/           # Phase 1 behavioral contracts
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── mission_runtime/        # IC-01: resolution.py, context.py (the SSOT)
├── specify_cli/
│   ├── runtime/next/       # IC-02: runtime_bridge.py
│   ├── cli/commands/       # IC-02 next_cmd.py; IC-03 agent/mission.py; IC-04 decision.py; IC-05 agent/workflow.py; IC-07 charter/_status_collectors.py
│   ├── missions/           # IC-03: _substantive.py
│   ├── core/               # IC-06: paths.py
│   ├── lanes/              # IC-05: persistence.py (#1993 seam)
│   └── workspace/          # IC-05: context.py
tests/                      # behavioral + topology-true fixtures, mirroring src layout
```

**Structure Decision**: Single-project CLI. No new packages — every change lands in an existing module
owned by exactly one IC.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs. Seven
> concerns, **zero file-overlap** (NFR-005). `branch_naming.py` is OUT (prior mission #2012).

### IC-01 — Single context factory + freeze + build-invariant + write-projection boundary (the SSOT spine)
- **Purpose**: Name the single context **factory** (`build_execution_context`, funneling the existing sole `ExecutionContext(` site at `resolution.py:739` + resolving the `:800-808` post-build mutation), **freeze** the composite, assert `context.target_branch == branch_ref.target_branch` at build (reject-on-mismatch → `CONTEXT_INVARIANT_VIOLATION`), and **declare the write-projection boundary contract** so the deferred write-side adopts against a frozen seam (D-6). `branch_naming` stays a collaborator the factory calls — not absorbed.
- **Relevant requirements**: FR-009
- **Affected surfaces**: `src/mission_runtime/context.py`, `src/mission_runtime/resolution.py`
- **Sequencing/depends-on**: none (precondition for IC-02..IC-05). `resolve_action_context` delegates to the factory.
- **Risks**: freezing surfaces the `:800-808` WP-bearing mutation — resolve by constructing once through the factory (function-over-form), not by keeping mutability. Keep the factory package-private (no new public symbol — C-001, ADR-06-07-1 lean API). Est. ~15–60 LOC, ≤7 subtasks (pedro feasibility).

### IC-02 — Typed-error pass-through (`next` family + M1/M2 surfaces)
- **Purpose**: Preserve `ActionContextError.code` + checked-paths across the `next`-family catch-sites AND the two net-new flatten surfaces, instead of collapsing into `MISSION_NOT_FOUND`; the cheapest cut, closes #12/#14/#15 (+M1/M2) with no resolver change.
- **Relevant requirements**: FR-001, FR-002 (folds #1911 richer `next_step`)
- **Affected surfaces**: `src/runtime/next/runtime_bridge.py` (`:3128-3130`, `:3265-3274`), `src/specify_cli/cli/commands/next_cmd.py` (`_resolve_mission_slug` collapse `:361`, emitter `:374-408`); **M1** `src/specify_cli/context/resolver.py` (`:164`); **M2** `src/specify_cli/orchestrator_api/commands.py` (`:263-266`, 8 endpoints). _(M1 cite corrected: the flatten lives in `context/resolver.py:164`, NOT `context/mission_resolver.py` — that file has no flatten.)_
- **Sequencing/depends-on**: IC-01
- **Risks**: mirror the existing `QueryModeValidationError` branch (`next_cmd.py:474-491`) so the typed code+paths reach the JSON envelope; copy the `agent context resolve` reference (`context.py:158`). M2 touches the external orchestrator-api contract — preserve the envelope shape while surfacing the real code.

### IC-02b — Orchestrator-api typed-error + fail-closed identity (M2 + M3, read-path SAFETY)
- **Purpose**: One WP owning `orchestrator_api/commands.py`: **M2** — stop flattening `StatusReadPathNotFound`→`MISSION_NOT_FOUND` across the 8 endpoints (`:263-266`); **M3** — stop seeding `resolve_mid8(mission_slug, mission_id=None)` → empty mid8 (`:261`), which **suppresses the coord-aware fail-closed guard** (external automation reads stale primary status on a coord topology). Honor the factory boundary **contract** (D-6) — read the real `mission_id` from meta and pass it to `resolve_mid8(slug, mission_id=<real>)` (the `decision.py:421` primitive, NOT an importable projection API) — not a primary-only pre-read seeding empty identity; on a coord-only topology where meta `mission_id` is absent, fail closed (do not silently seed empty).
- **Relevant requirements**: FR-001 (M2 typed-error), FR-011 (M3 single-authority / read-path safety)
- **Affected surfaces**: `src/specify_cli/orchestrator_api/commands.py` (M2 `:263-266` + M3 `:261`) — distinct owned file from IC-02 (next family), so no overlap.
- **Sequencing/depends-on**: IC-01 (consumes the factory identity boundary)
- **Risks**: must not regress the external orchestrator-api envelope shape; topology-true coord fixture required to prove the fail-closed guard fires. NOTE: `commands.py:484/787` also pass `mission_id=None` for the *legacy* `{slug}-{lane}` grammar — those are intentional, NOT the M3 bug; touch only the status-read identity seed.

### IC-03 — `mission.py` planning-entry adoption
- **Purpose**: setup-plan exact-one auto-select (in `setup_plan`, NOT the shared helper); finalize-tasks read anchored on primary root (fix #11 fail-closed-pre-read); `is_committed` primary-target-branch leg; `_commit_to_branch` reports the real hash + distinguishes no-op-against-wrong-surface.
- **Relevant requirements**: FR-004, FR-005, FR-006, (#11)
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/mission.py` (SOLE owner — C8/C10/C11/C15), `src/specify_cli/missions/_substantive.py` (C9)
- **Sequencing/depends-on**: IC-01
- **Risks**: `agent/mission.py` is the one true collision surface — keep it a single IC; do NOT add auto-select inside the shared `_find_feature_directory` (would change behavior for all callers).

### IC-04 — `decision` single authority
- **Purpose**: Delete the primary-anchored escape-walk for resolved paths; derive `repo_root` from the canonical root authority; render the typed error as a structured message, not a traceback. `cmd_verify` shares the helper — fix lands once.
- **Relevant requirements**: FR-003 (#8)
- **Affected surfaces**: `src/specify_cli/cli/commands/decision.py` (`_resolve_repo_root_and_slug` `:57-119`)
- **Sequencing/depends-on**: IC-01
- **Risks**: keep `_SAFE_SLUG_RE` traversal-rejection on the raw operator token (DIR-031); the live symptom is an uncaught `ActionContextError` traceback, so catch+structure it too.

### IC-05 — implement single-resolution + #1993 lanes-dir seam
- **Purpose**: `agent action implement` consumes the claim's already-resolved context (single resolution path, kills "no workspace resolved"); extract `resolve_lanes_dir(feature_dir)` and route the 2-3 ad-hoc `feature_dir/lanes.json` derivations (#1993 carry, satisfies must-not-land-alone).
- **Relevant requirements**: FR-008 (#1832), FR-011, (#1993)
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/workflow.py` (`:1341`, `:1377-1381`), `src/specify_cli/lanes/persistence.py`, `src/specify_cli/workspace/context.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: #1993 must NOT land alone — it rides with #1832 here; pure path composition, LOW risk.

### IC-06 — Root-resolver unification (submodule boundary)
- **Purpose**: Make `resolve_canonical_root` stop at the submodule / `.kittify`/`kitty-specs` boundary, mirroring `locate_project_root` (`:122-131`), so the two root authorities AGREE — the live `assert_initialized` guard uses the broken one, so #1944/#1965 never covered #6.
- **Relevant requirements**: FR-007 (#6/#2011)
- **Affected surfaces**: `src/specify_cli/core/paths.py` (`:284-288`)
- **Sequencing/depends-on**: none
- **Risks**: #1971 is a *separate* 3-way `locate_project_root` consolidation — do NOT conflate; #2011 pins THIS resolver.

### IC-07 — Charter status side-effect-free + JSON-safe
- **Purpose**: Make charter status collectors side-effect-free (no `generate_all`/`ensure_..._fresh` write inside read-only status) and emit one normalized, JSON-safe hash.
- **Relevant requirements**: FR-010 (#1914 no-op slice)
- **Affected surfaces**: `src/specify_cli/cli/commands/charter/_status_collectors.py` (`:36-42`)
- **Sequencing/depends-on**: none
- **Risks**: scope to the read-path/status-read no-op slice only; broader #1914 umbrella stays on its own track.

**Cross-cutting:** **FR-011** (single-authority adoption) is satisfied by verification-by-deletion across
IC-02/03/04/05. **FR-012** (#1827 regression test, test-only per D-3) is placed at tasks time (rides
with IC-03's merge/baseline surface or its own thin WP).

> **NIT (verify-or-document follow-up):** there is a latent **4th** empty-mid8 seed
> `resolve_mid8(mission_slug, mission_id=None)` at `agent/tasks.py:4047` — the same empty-identity
> shape as M3, not in any WP/inventory. Likely benign (tasks-finalize context), but it should be
> **verified-or-documented** so the D-6 "callers MUST NOT seed empty identity" boundary contract is
> enforced consistently, not just at M3. No WP owns it; track as a follow-up.

### Sequencing (DIR-003)

```
IC-01 (invariant — trustworthy-context precondition)
   ├─> IC-02 (error pass-through; closes #12/#14/#15)  ┐
   ├─> IC-03 (mission.py planning entry)               ├─ parallel (disjoint files)
   ├─> IC-04 (decision single authority)               │
   └─> IC-05 (implement + #1993)                        ┘
IC-06 (root resolver) and IC-07 (charter no-op) — independent, any time.
```

IC-01 + IC-02 are the safe lead. IC-06/IC-07 have no dependency and can start immediately.

## Post-planning brownfield check (2026-06-16)

Standing discipline run before tasks. Outcome:
- **Foldable issues:** the planner-priti sweep (`research/priti-related-issues-sweep.md`) surfaced 22
  net-new related issues → **6 folded in** (matrix in spec.md), 16 cross-ref'd, #1827 re-test (→ D-3),
  provenance flag (#1888≠#1886) logged.
- **Split-brain / duplication:** mapped by `research/call-site-inventory.md` and assigned to ICs —
  two root resolvers (→ IC-06), `decision` dual authority (→ IC-04), `ExecutionContext` mutability/
  post-freeze write (→ IC-01), `is_committed` surface-blindness (→ IC-03). No NEW split introduced;
  edits are surgical against large god-modules (`agent/mission.py` 3942 LOC — touched in-place, owned
  solely by IC-03; `resolution.py` 823; `workflow.py` 2737).
- **Due deprecations:** scan of the IC-owned files found only **orthogonal** deprecation shims —
  `--feature` hidden alias (`next_cmd.py:73`), `--mission`/`--require-tasks` (`agent/mission.py:1427,1727`),
  legacy `feedback://` warnings (`agent/workflow.py:1733,1818`). NONE belongs to this mission's
  read-path/error-fidelity concern; **no due-deprecation removal is owed here** — bundling them would be
  scope creep (the `--feature` retirement is the separate #1060-A track).
- **Path drift:** none — every IC-owned file exists at the cited path on HEAD; line-number drift
  corrected in `research/call-site-inventory.md` §6.

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

## Out of Scope

- #1716 write-side topology (D-1, stays on #1878); flat-substrate retirement (larger #1619 grain).
- The naming/identity AST ratchet + `branch_naming.py` (prior mission #2012).
- #2008/#2009/#1890/#1891 sibling clusters; patch-version assignment (C-004).
