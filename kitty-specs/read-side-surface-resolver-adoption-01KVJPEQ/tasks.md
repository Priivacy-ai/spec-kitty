# Tasks: Read-Side Surface-Resolver Adoption

**Mission**: `read-side-surface-resolver-adoption-01KVJPEQ` (#2046) | **Branch**: `feat/read-side-surface-resolver-adoption` (stacked on 01KVGCE8 → `main` via combined PR)
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

WPs decomposed by **coherent module ownership** (disjoint `owned_files`), Tidy-First sequenced:
seam (WP01, foundation) → migrate read paths (WP02 CLIs, WP03 cascades) → flip cells (WP04),
guard+drain (WP05), end-to-end proof (WP06). The seam (WP01) is the foundation everything depends on.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Extract `resolve_handle_to_read_path` seam in `_read_path_resolver.py` (lift `_read_primary_meta` + topology gate) | WP01 | | [D] |
| T002 | Route the seam through `resolve_mission_read_path` (worktree-gated), NEVER the surface (FR-005 invariant) | WP01 | | [D] |
| T003 | Guard the segment via `assert_safe_path_segment` before any join (FR-004) | WP01 | | [D] |
| T004 | Re-point `orchestrator_api/_resolve_mission_dir` to consume the seam (eliminate its now-duplicate cascade) | WP01 | | [D] |
| T005 | Seam unit tests: mid8-derivation, traversal-reject, create-window→PRIMARY, fail-closed empty-mid8 gate | WP01 | | [D] |
| T006 | Migrate `context.py:72` raw-join bootstrap → seam | WP02 | [D] |
| T007 | Migrate `mission.py:1327` + `:1378` raw-join bootstraps → seam | WP02 | | [D] |
| T008 | Migrate `decision.py:464` raw-join bootstrap → seam (D-6 consolidation) | WP02 | | [D] |
| T009 | Behavior-preserving verify for `<slug>-<mid8>`/full-id at the 3 CLIs (NFR-002) | WP02 | | [D] |
| T010 | Migrate `workflow.py:302-324` `_mid8_for_mission_read_path` bespoke cascade → seam | WP03 | [D] |
| T011 | Migrate `mission_runtime/resolution.py:_mid8_from_primary_meta` bespoke cascade → seam | WP03 | | [D] |
| T012 | Migrate `runtime_bridge.py:2431-2450` `_resolve_runtime_feature_dir` → seam (FOLD-IN, C-007) | WP03 | | [D] |
| T025 | Migrate `tasks.py:4047` mid8-blind `resolve_mid8(slug, mission_id=None)` cascade → seam (F7) | WP03 | | [D] |
| T026 | Migrate `acceptance/__init__.py:_status_read_feature_dir` parallel cascade → seam | WP03 | | [D] |
| T013 | Per-site subsumption verify (each of the 5 cascades' behavior preserved by the seam) | WP03 | | [D] |
| T014 | Re-point the matrix read_path leg (`_entry_points`) to the seam; flip ONLY `coord-fresh/bare` + `coord-behind/bare` (remove 2 xfail marks) | WP04 | | [D] |
| T015 | Narrow `coord-empty/bare` + `coord-deleted/bare` reasons to the remaining aggregate divergence (FR-008) | WP04 | | [D] |
| T016 | Gates: assertion body FROZEN; 0 XPASS / 0 unexpected; post-rebase re-verify the 4 cells exist (C-001) | WP04 | | [D] |
| T017 | Selection-authority AST callsite ratchet: new direct `resolve_mission_read_path`/bespoke-`resolve_mid8` call outside seam → FAIL | WP05 | | [D] |
| T018 | Seam runtime empty-mid8-against-declared-coord gate test (mutation) | WP05 | | [D] |
| T019 | Two-axis mutation + pre/post-tree discrimination (passes adopted, would-have-failed pre-mission) | WP05 | | [D] |
| T020 | Drain the 4 read-CLI `_ALLOWLISTED_RAW_JOINS` keys (3 #2046 + decision.py D-6) by re-derivation; update `inventory.md` | WP05 | | [D] |
| T021 | SLUG_NAMES frozen `⊇ {raw_handle, handle}`; re-injection mutation proves net not narrowed (FR-007) | WP05 | | [D] |
| T022 | Per-CLI end-to-end: bare-slug × coord-fresh → COORD dir for context/mission/decision/acceptance (SC-002) | WP06 | | [D] |
| T023 | Create-window mutation: declared-unmaterialized coord + derived non-empty mid8 → PRIMARY (SC-005) | WP06 | | [D] |
| T024 | Traversal-rejection test (FR-004) + no-regression sweep (NFR-002) | WP06 | | [D] |

## Work Packages

### WP01 — Extract the guarded read-side seam (foundation)
- **Goal**: One `resolve_handle_to_read_path` seam lifted from the `_resolve_mission_dir` prototype; routes through `resolve_mission_read_path` (worktree-gated), NEVER the surface; segment-guarded. (IC-01; FR-001/FR-004/FR-005-invariant)
- **Priority**: P1 (foundation — all migrations depend on it). **Independent test**: seam unit tests (mid8/traversal/create-window/fail-closed).
- **Subtasks**: [ ] T001 [ ] T002 [ ] T003 [ ] T004 [ ] T005
- **Dependencies**: none. **Est.**: ~380 lines. **Prompt**: [tasks/WP01-extract-read-side-seam.md](./tasks/WP01-extract-read-side-seam.md)

### WP02 — Migrate the 4 raw-join read-CLI sites (3 #2046 + decision.py D-6)
- **Goal**: Route `context.py:72`, `mission.py:1327/1378` (#2046) + `decision.py:464` (D-6 consolidation) through the seam; behavior-preserving for non-bare-slug. (IC-02a; FR-002)
- **Priority**: P1. **Independent test**: each CLI resolves identically for `<slug>-<mid8>`; the raw joins are gone.
- **Subtasks**: [ ] T006 [ ] T007 [ ] T008 [ ] T009
- **Dependencies**: WP01. **Est.**: ~320 lines. **Prompt**: [tasks/WP02-migrate-cli-raw-joins.md](./tasks/WP02-migrate-cli-raw-joins.md)

### WP03 — Migrate the 5 bespoke cascades (incl. runtime fold-in)
- **Goal**: Route `workflow.py:302-324`, `mission_runtime/resolution.py:_mid8_from_primary_meta`, `runtime_bridge.py:2431-2450` (FOLD-IN, C-007), `tasks.py:4047` (F7 mid8-blind), `acceptance/__init__.py:_status_read_feature_dir` through the seam. (IC-02b; FR-002/C-007)
- **Priority**: P1. **Independent test**: each old cascade's behavior subsumed; no bespoke `resolve_mid8`/`mid8_from_slug` cascade remains at these sites.
- **Subtasks**: [ ] T010 [ ] T011 [ ] T012 [ ] T025 [ ] T026 [ ] T013
- **Dependencies**: WP01. **Est.**: ~440 lines. **Prompt**: [tasks/WP03-migrate-bespoke-cascades.md](./tasks/WP03-migrate-bespoke-cascades.md)

### WP04 — Flip the bare-slug equivalence cells (re-point read_path leg)
- **Goal**: Re-point the matrix read_path observation leg to the seam (option b), then flip ONLY `coord-fresh/bare` + `coord-behind/bare` green with the assertion logic FROZEN; narrow `coord-empty/bare` + `coord-deleted/bare` reasons to the remaining aggregate divergence. (IC-03; FR-003/FR-005/FR-008)
- **Priority**: P2. **Independent test**: matrix 0 XPASS / 0 unexpected; diff = read_path re-point + marker/reason edits only.
- **Subtasks**: [ ] T014 [ ] T015 [ ] T016
- **Dependencies**: WP02, WP03. **Est.**: ~240 lines. **Prompt**: [tasks/WP04-flip-bare-slug-cells.md](./tasks/WP04-flip-bare-slug-cells.md)

### WP05 — Selection-authority guard + drain the residual allowlist
- **Goal**: AST callsite ratchet (new direct/bespoke read-selection call outside the seam → FAIL) + seam runtime empty-mid8 gate; drain the 4 read-CLI allowlist keys (3 #2046 + decision.py D-6) by re-derivation (SLUG_NAMES frozen). (IC-04+IC-05; FR-006/FR-007)
- **Priority**: P2. **Independent test**: two-axis mutation + pre/post discrimination; re-injection mutation; SC-005 allowlist drained.
- **Subtasks**: [ ] T017 [ ] T018 [ ] T019 [ ] T020 [ ] T021
- **Dependencies**: WP02, WP03. **Est.**: ~420 lines. **Prompt**: [tasks/WP05-selection-authority-guard.md](./tasks/WP05-selection-authority-guard.md)

### WP06 — End-to-end CLI proof + create-window + traversal
- **Goal**: Per-read-CLI end-to-end (bare-slug × coord-fresh → coord dir — the proof the matrix cannot give), create-window mutation, traversal-rejection. (IC-06; SC-002/SC-005/FR-004)
- **Priority**: P2. **Independent test**: bare-slug coord read resolves COORD dir per CLI; create-window stays primary; traversal rejected.
- **Subtasks**: [ ] T022 [ ] T023 [ ] T024
- **Dependencies**: WP01, WP02, WP03. **Est.**: ~300 lines. **Prompt**: [tasks/WP06-cli-e2e-proof.md](./tasks/WP06-cli-e2e-proof.md)

## Dependency Graph

```
WP01 (seam) ──┬─▶ WP02 (CLI migrations) ──┐
              ├─▶ WP03 (cascade migrations)─┼─▶ WP04 (flip cells)
              │                             ├─▶ WP05 (guard + drain)
              └──────────────────────────▶ WP06 (e2e proof) ◀── WP02, WP03
```

## MVP / Sequencing

- **MVP**: WP01 (seam) + WP02 (CLI migrations) + WP06 (the bare-slug coord e2e proof) — the user-facing residual closed for the CLIs.
- WP02/WP03 parallel after WP01; WP04/WP05/WP06 after the migrations.
