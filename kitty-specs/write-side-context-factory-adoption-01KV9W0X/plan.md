# Implementation Plan: Write-Side Context-Factory Adoption (Mission B)

**Branch**: `feat/write-side-context-factory-adoption` (stacked on `feat/read-path-error-fidelity` / Mission A, PR #2015) | **Date**: 2026-06-17 | **Spec**: `kitty-specs/write-side-context-factory-adoption-01KV9W0X/spec.md`
**Input**: Feature specification from `/kitty-specs/write-side-context-factory-adoption-01KV9W0X/spec.md`

## Summary

Adopt the **write** execution path onto Mission A's frozen `build_execution_context` factory + its
projected fragments — completing the read/write symmetry. Phase 0 (`research/write-site-inventory.md` +
`research/reduction-census.md`, verified on HEAD `efb28158f`) established the pivotal fact: **the
write-half fragment fields already EXIST and RESOLVE to the correct authority** — `workspace.primary_root`
(the `.parent.parent` killer), `status_surface.status_write_dir` (resolves to the **coord/status**
authority via `resolve_status_surface`, fail-closed, NOT `primary_root` — C-007 correct), and
`branch_ref.destination_ref`. So Mission B is **PURE CONSUMER-ROUTING**: flip the hand-rolled write-side
re-derivations to read these fragments. **C-001 holds** — the factory authority modules are NOT modified
(the only `mission_runtime/` touch is FR-006 *deletion* of dead scaffolding). The four adoption-target
fragments have **0 live readers** today; adoption flips them load-bearing (verification-by-deletion is the
proof).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, subprocess/pygit2 git, pytest, mypy, ruff (existing spec-kitty stack)
**Storage**: filesystem — three artifact families (meta/primary, status/coord, lanes/coord); git worktrees/coord branches
**Testing**: pytest; function-over-form behavioral + verification-by-deletion; topology-true fixtures (real 26-char ULID + real coord-worktree + real submodule); TDD-first; idempotency-preserving
**Target Platform**: Linux/macOS developer + CI (the spec-kitty CLI)
**Project Type**: single (CLI tool — `src/specify_cli/` + `src/mission_runtime/`)
**Performance Goals**: N/A (correctness/symmetry mission); resolution stays O(existing)
**Constraints**: read/write behavioral equivalence (NFR-001); **idempotency-preserving — no on-disk worktree/coord churn (NFR-004)**; three-artifact-family preservation (C-007); bounded conflict surface (named write seam files only); ruff+mypy clean, complexity ≤15, no suppressions (NFR-005)
**Scale/Scope**: 8 write sites across 6 owning files; ~90–130 LOC (root-walk ~40–55, placement ~15–25, surface consumption ~20–30, FR-006 deletion ~10–15); 7 implementation concerns; no schema/data migration

## Charter Check

*GATE: software-dev-default charter (compact). DIR-001..DIR-013. Re-checked post-design — clean.*

- **DIR-001 (one owning module per concern):** satisfied — each write site is its own module; `coordination/status_transition.py` (R5+S1) is solely WP-COORD.
- **DIR-003 (decisions documented):** D-1..D-5 below; the #1716 defer reuses Mission A's decision `01KV8Q49WEG9RRKCEZ3XYN5DWP`.
- **DIR-031 (bounded-context translation):** routing to factory projections is pure consumption — no new authority (C-001); `branch_naming` stays a collaborator.
- No charter conflicts.

## Decisions (locked)

- **D-1 (C-003 scope — finalize the branch-target context object):** **R1–R5** (`.parent.parent` root walks
  → `workspace.primary_root`), **P1** (`core/worktree.py` placement join ×2 → factory placement projection),
  **S1 surface + target consumption** (`status_transition.py` status write → `status_surface.status_write_dir`
  coord authority + write-target → `branch_ref.destination_ref`, D-2), **FR-008 lanes/coord adoption** (D-6),
  **FR-006 retirement**, and the **NFR-006 simple-case test** (D-7). ~130–200 LOC (the bounded ~90–130 +
  ~40–70 for the write-target + lanes). DEFER only the **S2** write-surface-SELECTION ladder
  (`_read_contract_from_transaction_target`, the #1716 ~2094-LOC topology authority root) — it computes the
  *same value* the factory already does (cleanly deferrable; reduction-not-symmetry).
- **D-2 (FR-004 write-target IN-SCOPE — operator decision 2026-06-17, REVERSES the prior defer):** the
  write/merge-**target** is the *core* of the Lane-based branch-target context object, so it finalizes here:
  the S1 inline `coord_branch or _current_branch` selector is replaced by `branch_ref.destination_ref`.
  randy's divergence (flattened arm `destination_ref`=`target_branch` CWD-invariant vs `_current_branch`=git
  HEAD) is the **latent bug the adoption fixes** — **guarded by two binding tests**: (a) the simple-case
  "all-targets-base → flat" test (NFR-006, D-7) and (b) a before/after on-disk-target idempotency test
  (NFR-004). The earlier defer is reversed because NFR-006 is exactly the missing guard that makes the
  write-target safe to flip. The S2 write-surface-SELECTION *ladder* stays deferred (#1716, D-1).
- **D-3 (#2016 — CROSS-REF, do not fold):** the orchestrator coord-read identity bootstrap is a READ-path
  concern **already fixed by Mission A WP09** (`d4f0cf581`, `commands.py:282-311`); not reachable via
  Mission B's write fragments. Cross-ref + verify-don't-redo; folding a closed read concern into a write
  mission violates C-003/C-007.
- **D-4 (W9/W10 duplication collapse):** R1 (`emit.py::_feature_status_lock_root`) and R2
  (`work_package_lifecycle.py`) are now byte-identical topology-aware lock-root resolvers — routing both to
  `workspace.primary_root` **is** the consolidation (the duplication collapses naturally; no shared-owner WP
  needed).
- **D-5 (NFR-001 equivalence gate):** a topology-true parameterized test (primary/coord/submodule) proving
  read==write resolution for root + surface + **target**.
- **D-6 (#1993 lanes/coord adoption — FR-008, folded in 2026-06-17):** route the lanes-dir write
  (`lanes.json`, coord authority per C-LANES-1) through the context's coord surface —
  `resolve_lanes_dir(<coord feature dir from `status_surface`>)`. **Prefer deriving from the existing
  `status_surface` fragment + the `resolve_lanes_dir` seam (both already exist) over adding a raw factory
  field** — keeps it consumer-routing / minimal factory touch (C-001). The `resolve_lanes_dir` pure seam is
  already done (Mission A); this is the consumer adoption + (if needed) a thin lanes projection.
- **D-7 (simple-case test — NFR-006, KEYSTONE, BINDING):** a dedicated "all-targets-base → flat" test on a
  real single-branch repo (full ULID, no coord, no lanes): every fragment resolves to base, **zero**
  coord/lane paths read or written, behavior byte-identical to the historical pre-lane flat path. This is
  the guard that makes the write-target (D-2) safe and proves the branch-target object degrades cleanly.
- **D-8 (#2000 / #2016 — verified-already-fixed):** #2000's composes are already routed (naming-rider #2012;
  ratchet flags zero offenders) and #2016 is fixed by Mission A WP09 — both cross-ref/verify-already-fixed,
  close on #2015 merge; NOT new WPs. (The stale ratchet `doctor.py` allow-list drift found during this
  check was boy-scout-fixed on this branch.)
- **D-9 (clean-before-touch pre-refactors — squad `research/pre-refactor/`, land FIRST):** the adoption is
  made mechanical by two pre-WPs landed BEFORE the adoption ICs: **IC-CHARNET** (the topology-true
  characterization net — paula's live-evidence trap: the strongest write-path suite passes `repo_root=`
  everywhere so it is BLIND to the swap, and the FR-004 divergence has ZERO witnessing test; add tests that
  drive WITHOUT explicit `repo_root` on real coord/submodule topologies — the gate that makes every later
  deletion provable) and **IC-DEDUP** (PR-1: extract the byte-identical `emit::_feature_status_lock_root` ≡
  `wpl::_repo_root_for_lock` into one shared helper; lands before WP-EMIT/WP-WPL fan out — the only
  cross-file ownership hazard). FR-006 dead-code (PR-4) + the tests that ENCODE its deletion targets as
  contracts (paula S-2/S-3) retire **atomically** in IC-RETIRE; the private-helper lock-root tests (paula
  S-4/S-9) get a public behavioral invariant added FIRST, then retire. PR-3 (store tidy) + PR-5 (placement
  helper) are in-WP boy-scout. **SKIP** (#1716 ~2094-LOC topology authority, out of scope): PR-7
  `_identity_for_request` tidy + PR-8 the S2 selection ladder. **RISKY/defer to IC-COORD** (not a
  behavior-preserving pre-refactor): the `_repo_root_for_feature`→coord-target unification (it's the FR-004
  adoption itself, behind the NFR-006/idempotency guards). Net pre-refactor ~−86 LOC, behavior-preserving.
- **D-10 (Fix, don't litigate — C-008 / #1970 / DIRECTIVE_025, BINDING stance):** campsite-cleaning is the
  DEFAULT — adjacent failing tests / lint / type issues an implementer hits are **fixed in the same change**,
  not litigated pre-existing-vs-introduced or left under "minimal diff." Every WP prompt carries this.
- **D-11 (user-doc — FR-009):** an Explanation page presenting the branch-target routing table + the simple
  case, demystifying lane behaviour (IC-DOCS); inventoried for docs-freshness.
- **D-12 (adoption MECHANISM — route to the existing PUBLIC pure resolver, post-tasks squad alphonso B-1/B-2):**
  adoption does **NOT** thread an `ExecutionContext` into the write sites and does **NOT** consume the composite
  fragment object (the write-site files don't hold a context, and `resolve_action_context` requires an
  `action` token / fails closed — not a write-path entry). Instead each write site routes to the **existing
  public pure resolver** that already sources the fragment value (verified on HEAD `eba2448d8`):
  `primary_root` → `specify_cli.core.paths.resolve_canonical_root` / `get_main_repo_root`; `status_write_dir`
  → `coordination.surface_resolver.resolve_status_surface` (fail-closed, coord authority); `destination_ref` /
  placement → `mission_runtime.resolution.resolve_placement_only` (already exported; its docstring states it
  returns the same `destination_ref` `CommitTarget` the builder computes); lanes → `lanes.persistence.resolve_lanes_dir`.
  **These resolvers already exist and are public — adoption is an import + call, NOT a new authority and NOT an
  edit to `build_execution_context`/`resolution.py` (C-001 fully holds; the only `resolution.py` touch remains
  WP07's FR-006 deletion).** Symmetry proof is reframed accordingly: read and write call the **same** pure
  resolver (the single sourced path), which is what makes them equivalent — see the SC-002 reframe.

## Project Structure

```
src/specify_cli/
├── status/            # WP-EMIT emit.py · WP-WPL work_package_lifecycle.py · WP-LE lifecycle_events.py · WP-STORE store.py · WP-RETIRE aggregate.py
├── coordination/      # WP-COORD status_transition.py
├── core/              # WP-WT worktree.py
src/mission_runtime/   # WP-RETIRE resolution.py + context.py (FR-006 deletion ONLY — factory NOT modified, C-001)
tests/                 # behavioral + topology-true fixtures; FR-005 architectural-guard extension in tests/architectural/
```

**Structure Decision**: Single-project CLI. No new packages. The factory (Mission A's, on the stacked
branch) is **consumed, not modified**.

## Implementation Concern Map

> Concerns are NOT work packages. Seven concerns, **zero owned_files overlap**. Pure consumer-routing onto
> the existing factory — no precondition concern (the factory is already merged), so all are independently
> parallelizable. `branch_naming` + the factory authority modules are OUT (C-001).

### IC-EMIT — `status/emit.py` lock-root adoption (R1)
- **Purpose**: Replace the `_feature_status_lock_root` `.parent.parent` walk with `workspace.primary_root` (meta/primary read). Collapses the W9/W10 duplication (D-4).
- **Relevant requirements**: FR-001 · **Owns**: `src/specify_cli/status/emit.py` · **Family**: meta/primary · **Depends**: none · **Risk**: low.

### IC-WPL — `status/work_package_lifecycle.py` root adoption (R2)
- **Purpose**: Replace the 3× `.parent.parent` root walk with `workspace.primary_root`.
- **FR-001** · **Owns**: `src/specify_cli/status/work_package_lifecycle.py` · meta/primary · none · low.

### IC-LE — `status/lifecycle_events.py` root adoption (R3)
- **Purpose**: Replace the `.parent.parent`/`.parent.parent.parent` walks with `workspace.primary_root`.
- **FR-001** · **Owns**: `src/specify_cli/status/lifecycle_events.py` · meta/primary · none · low.

### IC-STORE — `status/store.py` ancestor-scan adoption (R4)
- **Purpose**: Replace the `KITTY_SPECS_DIR` ancestor scan with `workspace.primary_root`.
- **FR-001** · **Owns**: `src/specify_cli/status/store.py` · meta/primary · none · low.

### IC-WT — `core/worktree.py` placement adoption (P1)
- **Purpose**: Replace the two `feature_dir = worktree_path / KITTY_SPECS_DIR / branch_name` placement joins (`:384` reuse arm, `:396` create arm) with the factory placement projection (`CommitTarget`/`ArtifactPlacementFragment`); naming stays via the `mission_dir_name` seam.
- **FR-002** · **Owns**: `src/specify_cli/core/worktree.py` · meta/primary · none · low-med (placement wiring).

### IC-COORD — `coordination/status_transition.py` root + surface + **write-target** adoption (R5 + S1)
- **Purpose**: Replace `_repo_root_for_feature`'s `.parent.parent` walk (R5) with `workspace.primary_root`; route the status write **surface** to `status_surface.status_write_dir` (the coord authority — C-007); replace the inline `coord_branch or _current_branch` write-**target** with `branch_ref.destination_ref` (FR-004/D-2). DEFER only the S2 selection ladder (#1716). Reduces the second parallel factory (`_identity_for_request`) to consume the projection.
- **FR-003, FR-004, FR-007** · **Owns**: `src/specify_cli/coordination/status_transition.py` · status/coord + meta/primary · none · **med-high** (write-surface + write-target — topology-true fixtures mandatory NFR-002; status writes stay on the coord authority, never `primary_root`; the write-target flip carries the idempotency before/after test).

### IC-LANES — lanes/coord adoption (FR-008, #1993 deeper grain)
- **Purpose**: Route the lanes-dir write (`lanes.json`, coord authority per C-LANES-1/#1991) through the context's coord surface — `resolve_lanes_dir(<coord feature dir from `status_surface`>)`. Prefer deriving from the existing `status_surface` + the `resolve_lanes_dir` seam (D-6) over a raw factory field (C-001). Completes the third artifact family.
- **FR-008** · **Owns**: the lanes-dir write callsite(s) — pinned at Phase-0/tasks (`cli/commands/implement.py` `_lanes_feature_dir` C-LANES-1 region + any peer); + a thin lanes projection in `lanes/persistence.py` if needed · lanes/coord · none · low-med.

### IC-SIMPLECASE — the "simple case still works" test (NFR-006, KEYSTONE)
- **Purpose**: The dedicated binding test (D-7): all-targets-base → flat. On a real single-branch repo (full ULID, no coord, no lanes), assert every adopted fragment resolves to base, zero `.worktrees/`/coord paths read or written, behavior byte-identical to the historical pre-lane flat path. Guards the write-target (D-2) + proves clean degradation.
- **NFR-006, SC-007** · **Owns**: a new `tests/` module (e.g. `tests/specify_cli/coordination/test_simple_case_flat_topology.py`) — test-only, no src overlap.

### IC-RETIRE — fragment-scaffolding retirement (FR-006)
- **Purpose**: Delete the genuinely-dead `prompt_source` fragment (`resolution.py:761-778`, `context.py:177-181`) and the dead `StatusSurfaceFragment.surface=` read-param wiring (`aggregate.py:199,266,309` + the `if surface is not None` branch). Deletion only — no authority change (C-001); the two `MissionStatus.load()` callers never pass `surface=`.
- **FR-006** · **Owns**: `src/mission_runtime/resolution.py`, `src/mission_runtime/context.py`, `src/specify_cli/status/aggregate.py` · n/a · none · low.

### IC-CHARNET — characterization net (clean-before-touch, FIRST — D-9)
- **Purpose**: Add the topology-true characterization tests that make every later deletion provable, fixing paula's **live-evidence trap** (the suites pass `repo_root=` so they're blind to the swap; the FR-004 divergence has no witnessing test). Tests MUST drive **without** explicit `repo_root` on real coord-worktree + submodule topologies (full ULID): the FR-004 before/after divergence (S-1, RED-on-HEAD), a coord-topology parity fixture (S-5), a submodule test (S-6), `store.py::_find_mission_specs_root` coverage (S-7), real-coord lanes placement (S-8).
- **NFR-001/002, SC-002 enabler** · **Owns**: new test modules under `tests/` (test-only, no src overlap) · **Sequence**: FIRST.

### IC-DEDUP — byte-identical lock-root de-dup (clean-before-touch — D-9, PR-1)
- **Purpose**: Extract the byte-identical `status/emit.py::_feature_status_lock_root` ≡ `status/work_package_lifecycle.py::_repo_root_for_lock` into ONE shared helper (e.g. `workspace/root_resolver.py`); both import it. Behavior-preserving (~−28 LOC). Add the public lock-root behavioral invariant (paula S-4/S-9) before retiring the private-helper-by-name tests.
- **(pre-FR-001 enabler)** · **Owns**: `src/specify_cli/workspace/root_resolver.py` (the new shared helper) + the two extraction edits · **Sequence**: **before WP-EMIT/WP-WPL fan out** (the only cross-file ownership hazard — land it first so each adoption lane edits only its own callsite).

### IC-DOCS — branch-target user documentation (FR-009 — D-11)
- **Purpose**: Author the user-facing Explanation page (Divio "Explanation") presenting the branch-target routing table ("this is where everything goes") + the simple case, demystifying lane behaviour. Edit SOURCE `docs/`; add the docs-freshness page-inventory row.
- **FR-009, SC-009** · **Owns**: a new `docs/explanation/` page + the `docs/development/3-2-page-inventory.yaml` row · **Sequence**: any time (independent; describes the finalized behaviour — land late).

**Cross-cutting:** **FR-005** (boundary-contract enforcement) — verified by deletion across IC-EMIT/WPL/LE/STORE/WT/COORD (no write site re-derives `mission_id`/`mid8`/`primary_root` after adoption); an optional ratchet extension in `tests/architectural/` flags write-side re-derivation. **SC-002** (0→load-bearing) is proven once the consumers land. **C-008 Fix-don't-litigate** is in every WP prompt.

### Sequencing (clean-before-touch first)

```
IC-CHARNET (characterization net — makes deletions provable)  ─┐  land FIRST
IC-DEDUP   (lock-root shared helper — before EMIT/WPL fan out) ─┘
   └─> IC-EMIT / IC-WPL (now a one-line swap to the shared helper / primary_root)
       IC-LE / IC-STORE (root walks)                  ┐
       IC-WT (placement)                              ├─ parallel (disjoint files, consume the factory)
       IC-COORD (root + surface + write-target, med-high — D-5 equivalence + idempotency tests)
       IC-LANES (lanes/coord)                         │
       IC-RETIRE (FR-006 deletion + retire S-2/S-3 tests atomically) ┘
IC-SIMPLECASE (the keystone flat test) + IC-DOCS — any time.
```

IC-CHARNET + IC-DEDUP are the two clean-before-touch pre-WPs (D-9). The adoption ICs then each consume the
already-merged factory via its public resolver (D-12 — an import + call, not a shared edit). IC-COORD is
highest-risk (write-surface + write-target).

**IC → WP collapse (12 ICs → 9 WPs in `tasks.md`):** IC-CHARNET → **WP01**; IC-DEDUP + IC-EMIT + IC-WPL →
**WP02** (one WP because all three touch `emit.py`/`work_package_lifecycle.py` — separate WPs would overlap
ownership); IC-LE + IC-STORE → **WP03** (two tiny same-concern status sites); IC-WT → **WP04**; IC-COORD →
**WP05**; IC-LANES → **WP06**; IC-RETIRE → **WP07**; IC-SIMPLECASE (+ the FR-005 ratchet) → **WP08**;
IC-DOCS → **WP09**.

## Post-planning brownfield check

Run before tasks (standing rule). **Outcome (2026-06-17):**
- **Foldable issues:** gh sweep for OPEN write-side/status/coord/topology tickets returned none beyond the
  matrix — #1716/#1878/#1619 (in-mission/deferred) and #2016 (cross-ref) are the complete set. No net-new
  fold.
- **Split-brain / LOC:** the inventory (`research/write-site-inventory.md`) IS the split-brain map — the
  second parallel write factory (`status_transition.py::_identity_for_request` + `CoordinationWorkspace`)
  is the documented duplication; ~90–130 LOC bounded, owning files pinned, no new split introduced.
- **Deprecations:** the FR-006 targets are confirmed due deprecations retired by IC-RETIRE
  (`prompt_source_dir` `context.py:181`; the `surface=` read-param `aggregate.py:199,309`). One ORTHOGONAL
  `DeprecationWarning` at `core/worktree.py:304` (IC-WT's file) is unrelated to placement adoption —
  IC-WT may boy-scout it if due, but it is NOT a Mission B concern.
- **Path drift:** none — all owned files exist; line drift corrected in `research/write-site-inventory.md` §6.

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

## Out of Scope

- The S2 write-surface-SELECTION ladder (`_read_contract_from_transaction_target`) / #1716 topology authority
  root (~2094 LOC); #1878 finalize/merge ff-advance bookkeeping. (FR-004 write-target is now IN scope, D-2.)
- Any change to `build_execution_context`/`branch_naming` beyond consuming the projection + FR-006 deletion (C-001).
- #2016 (read-path, fixed by Mission A WP09); patch-version assignment (C-004).
