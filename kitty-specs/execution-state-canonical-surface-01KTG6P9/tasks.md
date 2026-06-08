---
description: "Work package task list — Execution-State Canonical Domain Surface"
---

# Work Packages: Execution-State Canonical Domain Surface

**Inputs**: Design documents from `/kitty-specs/execution-state-canonical-surface-01KTG6P9/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md, occurrence_map.yaml

**Tests**: Test work is explicit and load-bearing here (the parity ratchet + boundary tests are the acceptance gates).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Finer-grained slicing chosen by operator — the large strangle/facade concerns are split for smaller review surface and more parallelism.

**Prompt Files**: Each WP references a matching prompt file in `/tasks/`.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel (different files/components).

## Path Conventions

- Single project: `src/`, `tests/`. New canonical umbrella: `src/mission_runtime/`.

---

## Work Package WP01: Full-sequence parity ratchet (gate) (Priority: P1) 🎯 GATE

**Goal**: Extend `test_execution_context_parity.py` to the full `next→implement→move-task→review→status` sequence across main / lane / direct-to-target, with a non-vacuous negative control.
**Independent Test**: Ratchet passes for all three modes and fails when re-derivation is injected.
**Prompt**: `/tasks/WP01-parity-ratchet-gate.md`
**Requirement Refs**: FR-020, FR-021, FR-022, FR-023, FR-024

### Included Subtasks

- [x] T001 Author lane-worktree and direct-to-target fixtures in `tests/architectural/test_execution_context_parity.py` (WP01)
- [x] T002 Drive the full `next→implement→move-task→review→status` sequence from the repository-root-checkout CWD (WP01)
- [x] T003 Drive the same sequence from lane-worktree CWD and assert parity of WP identity, lane transitions, status output (WP01)
- [x] T004 Drive direct-to-target mode; assert mode-correct branch and refusal of unauthorized mainline writes (WP01)
- [x] T005 Add non-vacuous negative control (inject re-derivation → ratchet fails) (WP01)
- [x] T006 De-overclaim the docstring; register the ratchet as a CI gate for the targeted paths (WP01)

### Dependencies

- None (gate; authored first per ATDD; gates WP04, WP06, WP07, WP08, WP09, WP10).

### Risks & Mitigations

- Direct-to-target fixture realism → build it against the real mode resolver, not a mock.

---

## Work Package WP02: `mission_runtime/` umbrella + layer registration + ADR (Priority: P1)

**Goal**: Stand up the canonical execution-state umbrella with a curated public API, register it in the layer meta-guard, and ratify the design in an ADR.
**Independent Test**: `test_no_unregistered_src_packages` and the new sole-resolver test pass with the empty-but-registered umbrella.
**Prompt**: `/tasks/WP02-mission-runtime-umbrella.md`
**Requirement Refs**: FR-001, FR-002, FR-005, FR-006, C-006

### Included Subtasks

- [x] T007 Write the design ADR in `architecture/3.x/adr/` (module name, public API shape, context-object abstraction, Strangler migration order) (WP02)
- [x] T008 Create `src/mission_runtime/` package with `__init__.py` exposing the curated `__all__` (WP02)
- [x] T009 Register `mission_runtime` in `_DEFINED_LAYERS` (`tests/architectural/test_layer_rules.py`) and the `conftest.py` landscape fixture (WP02)
- [x] T010 Add `tests/architectural/test_mission_runtime_surface.py` (sole-resolver / no-internal-import enforcement) (WP02)

### Dependencies

- None.

### Risks & Mitigations

- Layer-guard registration must be exact in both files; ADR (FR-006) lands before mass code (C-006).

---

## Work Package WP03: ExecutionContext relocation façade (Priority: P1)

**Goal**: Relocate `resolve_action_context` + the context value object into the umbrella as a Stage-C façade delegating to today's resolver; leave a thin shim.
**Independent Test**: Consumers resolve via `mission_runtime`; parity ratchet (WP01) stays green.
**Prompt**: `/tasks/WP03-executioncontext-relocation.md`
**Requirement Refs**: FR-003, FR-004

### Included Subtasks

- [x] T011 Move `ExecutionContext`/`ActionContext` value object into `src/mission_runtime/context.py` (WP03)
- [x] T012 Relocate `resolve_action_context` into `src/mission_runtime/resolution.py` as a Stage-C façade delegating to the existing resolver (WP03)
- [x] T013 Add a thin re-export shim at `src/specify_cli/core/execution_context.py` (WP03)
- [x] T014 Update internal references; keep the parity ratchet green (WP03)

### Dependencies

- Depends on WP02.

### Risks & Mitigations

- Import cycles; behavior-preserving relocation (NFR-001) — no parallel resolver retained (NFR-002).

---

## Work Package WP04: Residue routing — runtime_bridge + workflow + mode branch (Priority: P2)

**Goal**: Route the primary residue surfaces through the canonical façade and make the gate observe the mode-correct target branch.
**Independent Test**: `runtime_bridge` query-mode and `workflow.py` fix-mode resolve via the façade; ratchet green incl. direct-to-target.
**Prompt**: `/tasks/WP04-residue-routing.md`
**Requirement Refs**: FR-007, FR-008, FR-012, FR-036, C-001, C-002

### Included Subtasks

- [x] T015 Route `runtime/next/runtime_bridge.py` query-mode through `resolve_action_context` (WP04)
- [x] T016 Route `cli/commands/agent/workflow.py` fix-mode `repo_root`/`target_branch` through `resolve_action_context` (WP04)
- [x] T017 Implement mode-correct target-branch resolution (planning/direct-to-target/worktree) and refuse unauthorized mainline writes (WP04)
- [x] T018 Verify the parity ratchet stays green across all modes (WP04)
- [x] T052 Relocate the `runtime_bridge.py` operational-context builders (`build_operational_context_for_claim`, `_build_operational_context_for_decision`, `_resolve_tech_stack_for_profile`) into the umbrella; `runtime_bridge` consumes the umbrella API (bounded runtime_bridge exec-state extraction, operator decision 2026-06-08; realizes IC-02 for the runtime_bridge surface, kept in WP04 since it owns `runtime_bridge.py`) (WP04)
- [x] T053 Collapse the `runtime_bridge.py` path/feature-dir/coord-branch/ULID resolvers (`_primary_runtime_feature_dir`, `_resolve_runtime_feature_dir`, `_resolve_run_dir_for_mission`, `_resolve_coordination_branch`, `_resolve_mission_ulid`) into the umbrella's single resolver; fix `candidate_feature_dir_for_mission` / `coordination/surface_resolver.py::resolve_status_surface` to resolve the coord feature-dir/status path **exactly once** (no nested `.worktrees/<m>-coord/.worktrees/…` double-resolution; ignore nested `.worktrees/`) — FR-036, #1772 Bugs 1/2 (WP04)

### Dependencies

- Depends on WP01, WP03.

### Risks & Mitigations

- Large blast radius; mode-branch logic must honor C-001 (never mainline unauthorized).

---

## Work Package WP05: Collapse duplicate feature-dir resolvers (Priority: P2)

**Goal**: Collapse the 8 duplicate `_resolve_feature_dir` implementations to one canonical resolver and delete the rest.
**Independent Test**: One resolver remains; all former call sites use it; ratchet green.
**Prompt**: `/tasks/WP05-collapse-feature-dir-resolvers.md`
**Requirement Refs**: FR-010, NFR-002

### Included Subtasks

- [x] T019 Inventory the 8 `_resolve_feature_dir`/feature-dir resolver implementations; select the canonical one (WP05)
- [x] T020 Repoint the 7 redundant call sites to the canonical resolver (WP05)
- [x] T021 Delete the redundant implementations (no dead code) (WP05)

### Dependencies

- Depends on WP03.

### Risks & Mitigations

- Subtle behavioral differences between the 8 copies → diff each against the canonical before deleting.

---

## Work Package WP06: Eliminate remaining path-builders (Priority: P2)

**Goal**: Route or delete the remaining ~125 raw `kitty-specs / mission_slug` constructions across ~160 files.
**Independent Test**: SC-004 grep returns zero outside the canonical module and `status/`.
**Prompt**: `/tasks/WP06-eliminate-path-builders.md`
**Requirement Refs**: FR-009, FR-011, NFR-002

### Included Subtasks

- [x] T022 Enumerate the remaining raw `main_repo_root / "kitty-specs" / mission_slug`-class constructions (WP06)
- [x] T023 Route each through the `mission_runtime` canonical surface (WP06)
- [x] T024 Delete now-unreachable path-builder functions (WP06)
- [x] T025 Confirm the SC-004 grep returns zero (WP06)

### Dependencies

- Depends on WP04, WP05.

### Risks & Mitigations

- Volume; work in reviewable batches; ratchet green after each batch.

---

## Work Package WP07: Status facade promote/demote + `__all__` (Priority: P2)

**Goal**: Finalize per-submodule promote/demote decisions and update `status/__init__.py` `__all__`.
**Independent Test**: Promoted symbols importable from the facade; demoted symbols `_`-prefixed; `status/` internal tests green.
**Prompt**: `/tasks/WP07-status-facade-promotions.md`
**Requirement Refs**: FR-013, C-007

### Included Subtasks

- [x] T026 Finalize promote/demote/route decisions per submodule using `occurrence_map.yaml` (resolve all REVIEW entries) (WP07)
- [x] T027 Add promoted symbols to `status/__init__.py` `__all__`; `_`-prefix demoted symbols (WP07)
- [x] T028 Update `status/` internal references for any renames (WP07)

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- Don't promote internals that should stay private — confirm real external consumers per symbol.

---

## Work Package WP08: Route status bypass imports (bulk-edit) (Priority: P2)

**Goal**: Rewrite the ~225 deep `status.*` imports outside `status/` to the facade or `MissionStatus`, per the occurrence map.
**Independent Test**: Zero non-exempt deep `status.*` imports remain.
**Prompt**: `/tasks/WP08-route-status-imports.md`
**Requirement Refs**: FR-014, C-004, C-007

### Included Subtasks

- [x] T029 Consult `occurrence_map.yaml`; rewrite PROMOTE imports to the facade (WP08)
- [x] T030 Rewrite ROUTE imports to `MissionStatus` calls (WP08)
- [x] T031 Handle REVIEW/PRIVATE submodules per the WP07 decision (WP08)
- [x] T032 Preserve the `coordination/` plumbing exemptions (WP08)

### Dependencies

- Depends on WP07.

### Risks & Mitigations

- Bulk-edit guardrail (DIRECTIVE_035) — consult the occurrence map before each touch.

---

## Work Package WP09: Widen status boundary test repo-wide (Priority: P2)

**Goal**: Widen `test_status_module_boundary.py` from the 6 WP03 packages to all of `src/specify_cli`.
**Independent Test**: Boundary test green over all of `src/specify_cli`; injected violation caught; scan ≤15 s.
**Prompt**: `/tasks/WP09-widen-status-boundary-test.md`
**Requirement Refs**: FR-015, FR-016, NFR-003, NFR-005

### Included Subtasks

- [x] T033 Widen the pytestarch rule + AST scan scope to all of `src/specify_cli` (WP09)
- [x] T034 Preserve documented exemptions; keep/extend the injection proof (WP09)
- [x] T035 Confirm zero non-exempt violations and ≤15 s scan time (WP09)

### Dependencies

- Depends on WP08.

### Risks & Mitigations

- Test must bite (non-vacuous); exemptions limited to documented plumbing (C-004).

---

## Work Package WP10: MissionStatus consumption rework (Priority: P3)

**Goal**: Route mission-level status read/write consumers onto `MissionStatus`; eliminate direct `BookkeepingTransaction` calls outside plumbing.
**Independent Test**: SC-005 grep (direct `BookkeepingTransaction`/`emit` outside `status/` + plumbing) returns zero.
**Prompt**: `/tasks/WP10-missionstatus-consumption.md`
**Requirement Refs**: FR-017, FR-018, FR-019, NFR-006

### Included Subtasks

- [x] T036 Rework direct `emit`/`lane_reader`/`store` mission-level calls to `MissionStatus.load()/.claim()/.transition()` (WP10)
- [x] T037 Ensure no direct `BookkeepingTransaction` calls remain outside `status/` and documented plumbing (WP10)
- [x] T038 Confirm SC-005 grep returns zero (WP10)

### Dependencies

- Depends on WP08.

### Risks & Mitigations

- Distinguish mission-level access (route to aggregate) from internal plumbing (exempt); `coordination/transaction.py` internals unchanged (NFR-006).

---

## Work Package WP11: Mission-identity field-drop fold-in (#1663) (Priority: P3)

**Goal**: Carry `mission_id`/`mission_slug` through the `runtime_bridge.py` snapshot reconstructions; close #1663.
**Independent Test**: Regression test proves identity survives the auto-complete reconstruction path.
**Prompt**: `/tasks/WP11-mission-identity-field-drop.md`
**Requirement Refs**: FR-025, FR-026, FR-027

### Included Subtasks

- [x] T039 Carry `mission_id`/`mission_slug` through `runtime/next/runtime_bridge.py:1723` and `:1860` reconstructions (WP11)
- [x] T040 Add a regression test on the auto-complete reconstruction path (WP11)
- [x] T041 Confirm #1663 is closeable (all snapshot sites preserve identity) (WP11)

### Dependencies

- Depends on WP04 (same `runtime_bridge.py` hotspot — edit once, sequence after).

### Risks & Mitigations

- Ensure all six `engine.py` construction sites remain correct.

---

## Work Package WP12: Ownership `scope` backfill-awareness + frontmatter-source port (#1757) (Priority: P3)

**Goal**: Make `scope` flow through one canonical owner on every path (read/backfill/inference) and push the finalize ownership IO boundary through a single frontmatter-source port.
**Independent Test**: A `scope: codebase-wide` added to an already-backfilled WP survives a `backfill_ownership` re-run; `from_frontmatter` is symmetric across input shapes; the resolve→validate path runs without stubbing `read_wp_frontmatter`.
**Prompt**: `/tasks/WP12-ownership-scope-backfill-port.md`
**Requirement Refs**: FR-028, FR-029, FR-030, FR-031, NFR-003

### Included Subtasks

> **ATDD-first (C-011):** author + commit the failing test subtask **T046 RED first**, before the T042–T045 implementation subtasks. Reviewer verifies red→green.

- [x] T042 Add `scope` to the `migration/backfill_ownership.py` "already present" guard and write step (persist `scope` when present) (WP12)
- [x] T043 Document `scope` as human-authored (no inference) in `ownership/inference.py::infer_ownership` (explicit no-op note) (WP12)
- [x] T044 Normalize the `from_frontmatter` raw-dict branch `authoritative_surface` with `... or ""` (provable symmetry) (WP12)
- [x] T045 Introduce a frontmatter-source port so the finalize resolve→validate path (`build_wp_manifests` + `read_wp_frontmatter`) is testable without stubbing the reader; route the finalize caller through it (WP12)
- [x] T046 Add tests: backfill re-run preserves `scope`; `from_frontmatter` symmetry; port-driven resolve→validate (WP12)

### Dependencies

- None (disjoint ownership surface: `ownership/**` + `migration/backfill_ownership.py` + the finalize caller; runs anytime).

### Risks & Mitigations

- Three `scope` representations, one owner (`from_frontmatter`) — Paula-Patterns single-ownership; do not add a parallel scope path.

---

## Work Package WP13: Legacy migration event-rebuild single-port (#1754) (Priority: P3)

**Goal**: Route `migration/runner.py` (Step 4) and `normalize_mission_lifecycle.py` onto a canonical per-mission `mission_state` event-rebuild entry (returning event counts), retiring the deprecated `rebuild_event_log` dependency.
**Independent Test**: Both callers use the canonical entry (not `rebuild_state.rebuild_event_log`); migration fixtures prove behavior preservation; the deprecated symbol has no live callers.
**Prompt**: `/tasks/WP13-legacy-migration-rebuild-port.md`
**Requirement Refs**: FR-032, FR-033, FR-034, NFR-002, NFR-004

### Included Subtasks

> **ATDD-first (C-011):** author + commit the failing test/fixture subtask **T051 RED first**, before the T047–T050 implementation subtasks. Reviewer verifies red→green.

- [x] T047 Expose a per-mission canonical event-rebuild entry on `mission_state` returning event counts (`events_generated`/`events_corrected`/`errors`/`warnings`) — **decision pinned (FR-032): add the per-mission entry; do NOT retire onto `repair_repo`** (it drops per-feature counts; full retirement is a separate fixture-backed change) (WP13)
- [x] T048 Migrate `migration/runner.py` Step 4 per-feature loop onto the canonical entry (WP13)
- [x] T049 Migrate `migration/normalize_mission_lifecycle.py` onto the canonical entry (WP13)
- [x] T050 Remove `rebuild_event_log` (or reduce to a thin shim with no live callers) and clean the `migration/__init__.__all__` lazy-symbol nuisance (#1757.4) (WP13)
- [x] T051 Add migration fixtures covering the per-mission rebuild path; assert behavior preservation and unchanged legacy-mission migration (WP13)

### Dependencies

- None (disjoint ownership surface: the migration runner/normalize/`mission_state`/`rebuild_state` files; runs anytime).

### Risks & Mitigations

- Behavioral change to legacy-project migration — fixture-backed (NFR-004); `repair_repo` is repo-level and not a per-feature drop-in, so the canonical entry must return per-mission event counts.

---

## Work Package WP14: Coordination-topology merge & path/status hardening (#1772) (Priority: P2) 🛡️ DATA-INTEGRITY

**Goal**: Harden `spec-kitty merge` on coordination-topology missions so it never silently drops lane code, and stop `.worktrees/` content from being staged. The resolver-correctness half of #1772 (FR-036 — single coord-aware feature-dir/status resolution, no nested `.worktrees/` double-resolution) is delivered by **WP04** as part of the canonical resolver collapse; WP14 owns the merge-flow + hygiene bugs.
**Independent Test**: On a coord-topology fixture with tracked `.worktrees/` junk + per-WP `done` events pre-recorded from an aborted merge, `spec-kitty merge` integrates the real lane diffs (or fails loudly — never a zero-code squash reported as success); post-merge validation reads the in-branch status path; finalize/recovery never `git add` a `.worktrees/` path and `doctor` flags pre-existing tracked `.worktrees/` content.
**Prompt**: `/tasks/WP14-merge-coord-topology-hardening.md`
**Requirement Refs**: FR-035, FR-037, FR-038, NFR-001, NFR-006

### Included Subtasks

> **ATDD-first (C-011):** author + commit the failing coord-topology merge regression fixture **T057 RED first**, before the T054–T056 fixes. Reviewer verifies red→green.

- [x] T054 Guard finalize/recovery staging to never `git add` a path under `.worktrees/`; add a `spec-kitty doctor` check that flags pre-existing tracked `.worktrees/` content (FR-035, #1772 Bug 0) (WP14)
- [x] T055 Gate merge lane integration on the actual lane tree-diff (not the per-WP `done` event); fail loudly on a would-be zero-diff squash; do not reset lane HEADs on a no-op merge (FR-037, #1772 Bug 3 — data integrity) (WP14)
- [x] T056 Resolve the **in-branch** status path in post-merge validation (`_assert_merged_wps_reached_done`-adjacent), not a `.worktrees/` worktree path (FR-038, #1772 Bug 4) (WP14)
- [x] T057 Add a coord-topology merge regression fixture (tracked `.worktrees/` junk + pre-recorded `done` events) + tests proving FR-035/FR-037/FR-038 (WP14)

### Dependencies

- WP04 (the canonical coord-aware resolver delivering FR-036 — Bugs 1/2 — that WP14's merge flow relies on). Otherwise disjoint (merge/doctor surfaces).

### Risks & Mitigations

- FR-037 touches `merge/executor.py` — broader than the strangler core, but #1772's silent code loss is the operator's stated priority; behavior-preserving for the healthy-merge path. NFR-006 holds: `coordination/transaction.py` internals unchanged. The regression fixture (T057) is the safety net.

---

## Dependency & Execution Summary

- **Sequence**: WP01 (gate) and WP02 (umbrella) have no deps → WP03 (relocation, needs WP02) → WP04 (residue, needs WP01+WP03) & WP05 (dup collapse, needs WP03) → WP06 (path-builders, needs WP04+WP05); facade track WP07 (needs WP01) → WP08 (needs WP07) → WP09 (needs WP08) & WP10 (needs WP08); WP11 (needs WP04).
- **Parallelization**: After WP01+WP02+WP03, the residue track (WP04/05/06) and facade track (WP07/08/09/10) run largely in parallel. WP11 follows WP04. WP12 (#1757) and WP13 (#1754) are dependency-free fold-ins on disjoint surfaces (`ownership/`+`backfill_ownership.py`; the migration runner/normalize files) and run in parallel with everything.
- **MVP / gate scope**: WP01 + WP02 + WP03 establish the gate and the canonical surface; the strangling WPs deliver the remediation.
- **Ownership / finalize-readiness**: WP04, WP05, WP06, WP08, WP10 declare `scope: codebase-wide` (cross-cutting strangler surfaces that legitimately co-edit shared files — the #1756/#1753 exemption now wired end-to-end). The narrow WPs (WP01/02/03/07/09/11/12/13) own disjoint files. This is what makes `finalize-tasks` ownership validation pass.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001, FR-002, FR-005, FR-006 | WP02 |
| FR-003, FR-004 | WP03 |
| FR-007, FR-008, FR-012, FR-036 | WP04 |
| FR-009, FR-010, FR-011 | WP05, WP06 |
| FR-013 | WP07 |
| FR-014, FR-016 | WP08, WP09 |
| FR-015 | WP09 |
| FR-017, FR-018, FR-019 | WP10 |
| FR-020, FR-021, FR-022, FR-023, FR-024 | WP01 |
| FR-025, FR-026, FR-027 | WP11 |
| FR-028, FR-029, FR-030, FR-031 | WP12 |
| FR-032, FR-033, FR-034 | WP13 |
| FR-035, FR-037, FR-038 | WP14 |
| FR-036 | WP04 (coord-aware resolver; WP14 merge flow consumes it) |
| NFR-001 | WP03, WP04, WP14 |
| NFR-002 | WP05, WP06, WP10, WP13 |
| NFR-003 | WP09, WP12 |
| NFR-004 | WP03, WP10, WP13 |
| NFR-005 | WP09 |
| NFR-006 | WP10 |
| NFR-007 | All code_change WPs (global gate; ruff + mypy clean, no disabled checks — SC-008) |
| C-001, C-002 | WP04 |
| C-004 | WP08, WP09 |
| C-006 | WP02 |
| C-007 | WP07, WP08 |
| C-009 | WP03, WP04, WP05, WP06, WP07, WP08, WP09, WP10, WP12, WP13 |
| C-010 | WP12, WP13 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001–T006 | Full-sequence parity ratchet across 3 modes + negative control | WP01 | P1 | No |
| T007–T010 | mission_runtime umbrella + layer reg + ADR + sole-resolver test | WP02 | P1 | Partial |
| T011–T014 | ExecutionContext relocation façade + shim | WP03 | P1 | No |
| T015–T018, T052, T053 | runtime_bridge + workflow routing + mode branch; + relocate operational-context builders → umbrella; collapse runtime_bridge resolvers & single coord-aware resolution (FR-036) | WP04 | P2 | No |
| T019–T021 | Collapse 8 dup feature-dir resolvers | WP05 | P2 | Yes |
| T022–T025 | Eliminate remaining path-builders | WP06 | P2 | Partial |
| T026–T028 | Status facade promote/demote + __all__ | WP07 | P2 | No |
| T029–T032 | Route ~225 status imports (bulk-edit) | WP08 | P2 | Partial |
| T033–T035 | Widen status boundary test repo-wide | WP09 | P2 | No |
| T036–T038 | MissionStatus consumption rework | WP10 | P3 | No |
| T039–T041 | Mission-identity field-drop (#1663) | WP11 | P3 | No |
| T042–T046 | Ownership `scope` backfill-awareness + frontmatter-source port (#1757) | WP12 | P3 | Yes |
| T047–T051 | Legacy migration event-rebuild single-port (#1754) | WP13 | P3 | Yes |
| T054–T057 | Coord-topology merge & path/status hardening (#1772) | WP14 | P2 | Partial |
