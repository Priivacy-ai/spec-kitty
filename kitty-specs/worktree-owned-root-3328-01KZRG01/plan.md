# Implementation Plan: Worktree-Owned Root for Mission Create/Next

**Branch**: `fix/worktree-owned-root-3328-v2` | **Date**: 2026-08-11 | **Spec**: `kitty-specs/worktree-owned-root-3328-01KZRG01/spec.md`
**Input**: Feature specification from `kitty-specs/worktree-owned-root-3328-01KZRG01/spec.md`

## Summary

`mission create` and `next` cannot explicitly target the invoking linked worktree as the mission's owned checkout: `mission create` refuses unconditionally on worktree invocation (`is_worktree_context(Path.cwd())`, disconnected from the caller's actual `repo_root`), and `next` either refuses (`.worktrees`-literal paths) or silently redirects through the ambiently-resolved primary checkout (generic linked worktrees). This plan adds a single, shared, git-topology-validated **checkout ownership** primitive that both commands consult through a new, explicit, named CLI affordance — never through `allow_worktree_context` — and threads the validated owned checkout through `safe_commit` and per-checkout runtime-state paths so mission-create writes and `next`'s runtime bookkeeping land in the owned worktree, not the ambient primary. Every caller that does not opt in keeps today's exact behavior (research D-1/D-2; spec C-001/C-002/FR-004).

## Technical Context

**Language/Version**: Python 3.11+ (repo baseline; no new runtime dependency)
**Primary Dependencies**: none new — reuses `subprocess` (git shell-outs already used by `commit_helpers._is_worktree_of` and `coordination.surface_resolver.read_worktree_registry`)
**Storage**: N/A (no persisted business data; see data-model.md for the checkout-ownership domain model)
**Testing**: pytest; existing `tests/architectural/`, `tests/runtime/`, `tests/agent/`, `tests/contract/`, `tests/unit/workspace/` suites plus new ATDD suite invoking the real installed CLI in two real `git worktree add` checkouts
**Target Platform**: Cross-platform (Linux/macOS/Windows per DIR-001) — `git rev-parse`/`git worktree list --porcelain` output is platform-uniform; path comparisons use `Path.resolve()` throughout, consistent with existing `_is_worktree_of`
**Project Type**: Single project (CLI + runtime library) — no frontend/backend split
**Performance Goals**: NFR-001 — at most one additional `git rev-parse` subprocess per `mission create`/`next` invocation versus current baseline
**Constraints**: C-001 (fail-closed default preserved), C-002 (no ambient fallback for the new path), C-004 (immutable-artifact validation only), C-006 (generic linked-worktree recognition)
**Scale/Scope**: Touches ~6 existing modules (`core/mission_creation.py`, `core/paths.py` or a new sibling module, `git/commit_helpers.py`, `cli/commands/next_cmd.py`, `cli/commands/agent/mission_create.py`, `coordination/surface_resolver.py`) plus one new module and one new ADR; no schema/data migration.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority**: the plan introduces exactly ONE new checkout-ownership validation primitive (IC-01) that both `mission create` and `next` consult — it does not add a seventh independent common-dir comparator (research D-2/D-4 identified the existing sprawl; this plan reduces divergence risk by reusing `_is_worktree_of`'s comparison logic, not duplicating it).
- **Architectural alignment**: builds on existing precedent (`BookkeepingTransaction`'s `repo_root`/`worktree_root` split, `get_status_read_root`'s read-vs-write naming convention) rather than inventing a parallel topology.
- **ATDD-first**: FR-012's real two-worktree, real-installed-CLI concurrency test is written and confirmed RED (refused, matching today's behavior) before any production code changes (IC-06/IC-07 precede IC-02/IC-03 completion in the dependency graph — see tasks.md).
- **Locality of change**: no unrelated refactor of the 4 independent root-resolvers (D-2) or the 6+ independent common-dir call sites (D-4 summary) — those are pre-existing sprawl this mission narrows contact with, not eliminates wholesale (that broader consolidation is out of scope; C-003).
- **Terminology canon**: "Mission" used throughout; no "feature" reintroduced in new identifiers.
- **No violations requiring Complexity Tracking justification.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/worktree-owned-root-3328-01KZRG01/
├── plan.md              # This file
├── research.md          # Phase 0 output (completed)
├── data-model.md         # Phase 1 output (completed) — checkout-ownership domain model
├── quickstart.md        # Phase 1 output — manual verification walkthrough
├── contracts/           # Phase 1 output — CLI/API contract for the new ownership affordance
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — not created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/core/
├── checkout_ownership.py     # NEW — OwnershipClaim, OwnershipValidationResult, resolve_ownership_claim()
├── mission_creation.py       # MODIFIED — accept new explicit-ownership param, thread into safe_commit
└── paths.py                  # UNCHANGED read-path resolvers; may export a small shared helper checkout_ownership.py reuses

src/specify_cli/git/
└── commit_helpers.py         # UNCHANGED public signature; _is_worktree_of's internal comparator becomes the reused primitive (imported, not duplicated)

src/specify_cli/coordination/
└── surface_resolver.py       # MODIFIED — expose the raw registry-based nested-worktree check (generic, not .worktrees-literal) for checkout_ownership.py to consume

src/mission_runtime/
├── resolution.py             # MODIFIED — create-time target seam plus explicit owned-root mission-context threading
└── __init__.py                # MODIFIED — export the canonical seam through the umbrella API

src/specify_cli/cli/commands/
├── next_cmd.py                        # MODIFIED — validated owned root remains explicit through mission resolution
└── agent/mission_create.py            # MODIFIED — new CLI option, threads into create_mission_core()

src/runtime/next/
├── decision.py               # MODIFIED — explicitly thread the validated owned root; no ambient inference
├── runtime_bridge.py         # MODIFIED — resolve mission content/meta/runtime against the explicit owned root
└── runtime_bridge_io.py      # UNCHANGED — existing repo-root-keyed runtime-state paths consume the threaded root

src/specify_cli/merge/
└── workspace.py              # UNCHANGED signature (same rationale as above)

tests/
├── architectural/test_no_production_worktree_guard_bypass.py   # MODIFIED — extended assertion or documented retirement rationale per its own docstring intent
├── architectural/test_mission_runtime_surface.py               # MODIFIED — pin the canonical create-time target export in the umbrella API contract
├── core/test_checkout_ownership.py                              # NEW — unit tests for the validation primitive (OWNED/NESTED/FOREIGN/BROKEN_POINTER)
├── e2e/test_worktree_owned_root_concurrency.py                  # NEW — FR-012 ATDD: real installed CLI, two real linked worktrees, forced overlap
├── architectural/surface_resolution_audit/inventory.md          # MODIFIED — re-pin WP02 effective_root callsite descriptor
├── architectural/test_single_mission_surface_resolver.py        # MODIFIED — re-pin the companion resolver descriptor
├── agent/test_agent_feature.py                                  # MODIFIED — extend existing worktree-refusal tests to assert unchanged default behavior (regression net for C-001/C-002)
└── mission_runtime/test_create_time_write_target.py             # NEW — bootstrap target-seam contract and default-path non-regression

docs/adr/3.x/
├── <next-available-date>-checkout-ownership-for-mission-create-and-next.md   # NEW ADR
└── index.md                                                                  # GENERATED — canonical era index row

docs/development/
├── 3-2-page-inventory.yaml                                                   # GENERATED — page-inventory lockfile
└── 3-2-docs-retrieval-index.yaml                                             # GENERATED — docs retrieval index

scripts/docs/freshen_adr_inventory.py                                         # MODIFIED — resolve redirect-stub eras to index.md
tests/docs/test_freshen_adr_inventory.py                                      # MODIFIED — real redirect-stub/index contract
```

**Structure Decision**: Single project, additive. No new top-level directories. The one new production module (`core/checkout_ownership.py`) sits beside `core/paths.py` and `core/mission_creation.py` because it is consumed by both and by `next_cmd.py`; placing it in `core/` (rather than under `cli/`) keeps it importable without pulling in Typer/CLI dependencies, matching the existing layering (`core/paths.py`, `core/context_validation.py` are both dependency-light).

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Shared checkout-ownership validation primitive

- **Purpose**: Provide the ONE function both `mission create` and `next` call to turn an explicit ownership request into a validated `OwnershipClaim` (data-model.md), reusing `_is_worktree_of`'s fail-closed common-dir comparison and `read_worktree_registry`'s generic (non-`.worktrees`-literal) nested-worktree data.
- **Relevant requirements**: FR-003, FR-005, FR-006, FR-011, NFR-004, C-006
- **Affected surfaces**: `src/specify_cli/core/checkout_ownership.py` (new), `src/specify_cli/git/commit_helpers.py` (expose `_is_worktree_of`'s comparator for reuse — rename/export if it stays "private"), `src/specify_cli/coordination/surface_resolver.py` (expose raw registry entries for the ancestor/descendant nested check)
- **Sequencing/depends-on**: none (foundation)
- **Risks**: `_is_worktree_of` is currently module-private (`_`-prefixed) inside `commit_helpers.py` — exposing it for reuse must not widen its contract or break `safe_commit`'s existing behavior; prefer a thin public wrapper over renaming the private function outright to minimize diff (locality of change).

### IC-02 — `mission create` explicit-ownership integration

- **Purpose**: Add the new CLI affordance to `agent mission create`, thread it through `create_mission_core()` as a distinct, validated parameter (never `allow_worktree_context`), and pass the resolved owned checkout as `worktree_root` (with the independently-resolved primary as `repo_root`) into `safe_commit` via `_commit_feature_file`. During the create-time window before mission identity is readable from the primary checkout, resolve `create_mission_core()`'s already-derived `planning_branch` through one canonical `mission_runtime` bootstrap target seam instead of asking `placement_seam()` to infer absent metadata.
- **Relevant requirements**: FR-001, FR-004, FR-008, FR-009, FR-010, C-001, C-002
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/mission_create.py`, `src/specify_cli/core/mission_creation.py`, `src/mission_runtime/resolution.py`, `src/mission_runtime/__init__.py`, `tests/mission_runtime/test_create_time_write_target.py`, `tests/architectural/test_mission_runtime_surface.py`
- **Sequencing/depends-on**: IC-01
- **Bootstrap target-seam contract**: `resolve_create_time_write_target(planning_branch: str) -> CommitTarget` is a pure, explicit-input constructor for this pre-readable-identity window only. It rejects empty and fully-qualified `refs/heads/...` inputs and returns the validated short branch unchanged. It performs no CWD, environment, topology, mission-directory, or ambient-root discovery. Once mission identity is readable, all ordinary writes continue through `placement_seam(...).write_target(...)`; the no-opt-in path does not call the bootstrap seam and stays byte-identical.
- **Risks**: `mission_creation.py`'s existing CWD-vs-`is_worktree_context` guard (line 309-314) must remain intact for non-opted-in callers (C-001) — the new path is an additional branch taken only when the new parameter is supplied, not a replacement of the existing guard's default. The bootstrap seam must not become a second general placement resolver: its narrow signature and tests forbid ambient discovery, and `_commit_feature_file` may receive its target only after an `OWNED` claim binds the current exact checkout root and `create_mission_core()` has derived the explicit `planning_branch` through its existing logic.

### IC-03 — `next` explicit-ownership integration and per-checkout runtime-state rooting

- **Purpose**: Add the same CLI affordance to `next`, validate it through IC-01, and root `feature-runs.json`/merge-lock-directory resolution at the owned checkout instead of the ambiently-resolved primary when ownership is `OWNED`.
- **Relevant requirements**: FR-002, FR-004, FR-007, C-001, C-002
- **Affected surfaces**: `src/specify_cli/cli/commands/next_cmd.py`, (read-only reuse, no signature change expected: `src/runtime/next/runtime_bridge_io.py`, `src/specify_cli/merge/workspace.py`)
- **Sequencing/depends-on**: IC-01
- **Risks**: `next`'s existing `@require_main_repo` decorator (`.worktrees`-literal) must keep gating non-opted-in callers exactly as today (FR-004) — the new affordance is consulted BEFORE that decorator's refusal fires (or the decorator itself gains a narrow, explicit bypass ONLY when a validated `OwnershipClaim.OWNED` is present — a design choice to confirm during implementation, not this plan; tasks.md WP02 records the decision point).

### IC-04 — Structured, distinguishable refusal errors

- **Purpose**: Ensure `NESTED`, `FOREIGN_OR_MISMATCHED`, `BROKEN_POINTER`, and the existing `UNOWNED_NO_OPT_IN` each raise/report a distinguishable error (not one generic string), consumable by `--json` output and by harnesses branching on failure class.
- **Relevant requirements**: FR-011
- **Affected surfaces**: `src/specify_cli/core/checkout_ownership.py` (exception/result types), `src/specify_cli/cli/commands/agent/mission_create.py` and `next_cmd.py` (error rendering / `--json` payload shape)
- **Sequencing/depends-on**: IC-01
- **Risks**: `mission_create.py:_print_worktree_navigation_hint`'s existing substring match on `"worktree"` in the error message must keep working for the UNCHANGED default-refusal path (regression risk if error message wording shifts).

### IC-05 — Architectural fence reconciliation

- **Purpose**: Confirm `tests/architectural/test_no_production_worktree_guard_bypass.py` continues to hold for `allow_worktree_context` (NFR-003) while the new, distinct parameter is explicitly exempted by name (not by weakening the AST scan's target).
- **Relevant requirements**: FR-010, NFR-003
- **Affected surfaces**: `tests/architectural/test_no_production_worktree_guard_bypass.py`
- **Sequencing/depends-on**: IC-02, IC-03
- **Risks**: none identified — this is a verification-only concern once IC-02/IC-03 land.

### IC-06 — Real installed-CLI, two-linked-worktree concurrency ATDD harness

- **Purpose**: Build/install an immutable wheel from the reviewed commit (never editable), create two real linked worktrees via `git worktree add` at generic (non-`.worktrees`) paths, force temporal overlap of two subprocess CLI invocations, and assert distinct mission IDs/slugs/refs/runtime state with clean trees afterward.
- **Relevant requirements**: FR-012, NFR-002, C-004
- **Affected surfaces**: `src/specify_cli/cli/commands/next_cmd.py`, `src/mission_runtime/resolution.py`, `src/runtime/next/decision.py`, `src/runtime/next/runtime_bridge.py`, new `tests/e2e/test_worktree_owned_root_concurrency.py`, `tests/architectural/surface_resolution_audit/inventory.md`, and `tests/architectural/test_single_mission_surface_resolver.py`. The validated `OwnershipClaim`'s effective checkout root is threaded explicitly through command → decision → bridge → mission-context resolution; no layer may reconstruct it from CWD or call `get_main_repo_root` for the opted-in path. The no-flag path retains the existing primary-anchor behavior byte-for-byte. Reuse an existing immutable-wheel fixture if present rather than adding a helper.
- **Sequencing/depends-on**: written RED before IC-02/IC-03 complete (ATDD-first); final GREEN pass depends on IC-01/IC-02/IC-03
- **Risks**: wheel build time inflates CI duration; must confirm an existing build/install fixture isn't already present in the repo (research did not find one — tasks.md WP-level research step should re-confirm before writing a new one) to avoid duplicating packaging-fixture logic.

### IC-07 — Negative/adversarial test coverage

- **Purpose**: Dedicated unit/integration tests for nested, foreign/mismatched-common-dir, broken-gitdir-pointer, and opt-in-without-passing-validation scenarios (spec.md Edge Cases + User Story 2).
- **Relevant requirements**: FR-013, NFR-004
- **Affected surfaces**: `tests/core/test_checkout_ownership.py` (new)
- **Sequencing/depends-on**: IC-01
- **Risks**: none identified.

### IC-08 — ADR authoring

- **Purpose**: Record the new checkout-ownership validation mechanism as an architectural decision (research D-7 confirmed no existing ADR covers this).
- **Relevant requirements**: supports FR-001 through FR-013 collectively; T021 additionally enforces FR-011/NFR-004/C-002 for canonical, fail-closed documentation authority
- **Affected surfaces**: `docs/adr/3.x/<date>-checkout-ownership-for-mission-create-and-next.md` (new), `scripts/docs/freshen_adr_inventory.py`, `tests/docs/test_freshen_adr_inventory.py`, and generator-only outputs `docs/adr/3.x/index.md`, `docs/development/3-2-page-inventory.yaml`, and `docs/development/3-2-docs-retrieval-index.yaml`
- **Sequencing/depends-on**: IC-01 (document the primitive once its shape is settled), can be drafted in parallel with IC-02/IC-03 and finalized after
- **Risks**: date-slot collision with concurrent missions (research risk #3 — confirm the next free date-prefix slot under `docs/adr/3.x/` at task-authoring time, not baked into this plan). The Common Docs move left `README.md` as a redirect stub while the canonical freshener still targeted it; T021 fixes that authority mismatch. A declared `## Index` section is the fail-closed signal for table-maintaining canonical landing pages, while sanctioned 1.x/2.x table-less `index.md` pages remain skipped. Real-tree `--all`/`--all --check`, explicit malformed-target exit-2 parity, legacy fixtures, and containment guards lock that boundary. Every index/inventory byte remains delegated to sanctioned generators (#3345). Prime cycle 1 also proved the ADR must be registered in the generated docs retrieval index or blocking docs-freshness CI reports `DOCS-INDEX-DRIFT`; Prime cycle 2 proved an unconditional `index.md`-without-table refusal breaks the repository's real legacy layout.
