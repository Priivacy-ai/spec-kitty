# Tasks: Single Mission-Surface Resolver

**Mission**: `single-mission-surface-resolver-01KVGCE8` | **Branch**: `feat/single-mission-surface-resolver` → `main` (PR)
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

WPs are decomposed by **coherent module ownership** (disjoint `owned_files`) and sequenced
tidy-BEFORE → equivalence-gate → collapse. The equivalence test (WP02) is the running
**deletion safety gate** (C-004): the collapse WP (WP06) and shim retirement (WP07) are
gated on it green for the relevant input classes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Repoint the 01KVFTFV audit AST walker to surface-resolution callsites | WP01 | [P] |
| T002 | Classify each callsite routed-through-resolver / topology-blind / raw-bypass | WP01 | |
| T003 | Emit `surface-resolution-inventory.md` + known-candidate self-assert | WP01 | |
| T004 | Produce the audited-surface list for WP08's guard | WP01 | |
| T005 | Build the (slug × mid8 × topology) equivalence matrix fixtures | WP02 | [P] |
| T006 | Differential test: every entry point → same dir OR same typed error | WP02 | |
| T007 | Cover all input classes incl. coord-empty + ambiguous-mid8 + `<slug>-<mid8>` handle | WP02 | |
| T008 | Mark the initially-RED cells (documents the divergences the fixes close) | WP02 | |
| T009 | Unify the two divergent `primary_feature_dir_for_mission` → one mid8-composing def (FR-009/T1) | WP03 | |
| T010 | Single composition grammar via `_compose_mission_dir` (T5) | WP03 | |
| T011 | Extract the shared `resolve-dir-or-typed-error` delegator (T4) | WP03 | |
| T012 | Per-caller-class regression tests (bare-slug / `<slug>-<mid8>` / backfilled) | WP03 | |
| T013 | Gates; equivalence matrix mid8-handle cells turn green | WP03 | |
| T014 | Kill `aggregate._find_meta_path` silent-first-match glob → canonical handle resolver (FR-008/T2) | WP04 | |
| T015 | `aggregate._resolve_read_dir` → thin adapter (drop the unmaterialized-coord re-gate, T3) | WP04 | |
| T016 | Negative tests (ambiguous-mid8 → typed error; mutation-verified) | WP04 | |
| T017 | Gates; aggregate's equivalence cells green | WP04 | |
| T018 | Preserve STATUS_READ_PATH_NOT_FOUND / MISSION_AMBIGUOUS_SELECTOR through next/mission_runtime (FR-005) | WP05 | |
| T019 | Reproduce #2010 bug #15 (red) then close (green) | WP05 | |
| T020 | Gates | WP05 | |
| T021 | Make `resolve_status_surface_with_anchor` the sole selection authority (FR-001/FR-007) | WP06 | |
| T022 | Migrate `status_transition.py` coord predicates to the canonical resolver (#1900) | WP06 | |
| T023 | Drain the C-002 topology-ratchet allowlist entry for status_transition.py | WP06 | |
| T024 | Coord-empty hard-fail with the two-path message (FR-006) | WP06 | |
| T025 | ADR for the coord-empty fallback policy (#1716) | WP06 | |
| T026 | Gates; equivalence green across all cells; no regression | WP06 | |
| T027 | Retire `missions/feature_dir_resolver.py` shim; classify the 51 import sites (occurrence_map.yaml, import_paths) | WP07 | |
| T028 | Migrate all callers to the canonical module | WP07 | |
| T029 | Gates; `rg "feature_dir_resolver import" src/` → 0 | WP07 | |
| T030 | Clone the 01KVFTFV load-bearing guard for surface resolution (FR-004) | WP08 | |
| T031 | Load-bearing self-test (real-code raw-bypass mutation + non-empty coverage assertion) | WP08 | |
| T032 | Gates; guard green on the collapsed tree; full suite | WP08 | |

## Work Packages

### WP01 — Surface-resolution audit (read-only inventory)
- **Goal**: Repoint the 01KVFTFV AST walker to enumerate every mission-surface-resolution callsite, classified routed-through-resolver / topology-blind-by-design / raw-bypass. (IC-02; FR-003) No `src/` changes.
- **Priority**: P1 (scopes WP06/WP07/WP08). **Independent test**: re-running reproduces the inventory; known candidates present.
- **Subtasks**: [ ] T001 [ ] T002 [ ] T003 [ ] T004
- **Dependencies**: none. **Est.**: ~280 lines. **Prompt**: [tasks/WP01-surface-resolution-audit.md](./tasks/WP01-surface-resolution-audit.md)

### WP02 — Differential equivalence test (the deletion safety gate)
- **Goal**: A differential test feeding the same (slug, mid8, topology) matrix to every resolution entry point, asserting identical dir OR identical typed error. The C-004 gate. (IC-05; FR-002, NFR-003) Initially RED on known divergences.
- **Priority**: P1 (gates the collapse). **Independent test**: matrix covers all input classes; cells flip green as fixes land.
- **Subtasks**: [ ] T005 [ ] T006 [ ] T007 [ ] T008
- **Dependencies**: none. **Est.**: ~340 lines. **Prompt**: [tasks/WP02-differential-equivalence-test.md](./tasks/WP02-differential-equivalence-test.md)

### WP03 — Unify resolver primitives (tidy-BEFORE)
- **Goal**: Collapse the two divergent `primary_feature_dir_for_mission` (FR-009/T1, mid8-composing wins) over one composition grammar (T5); extract the shared resolve-dir-or-typed-error delegator (T4). (IC-01)
- **Priority**: P1. **Independent test**: one `primary_feature_dir_for_mission`; per-caller-class tests pass; equivalence mid8 cells green.
- **Subtasks**: [ ] T009 [ ] T010 [ ] T011 [ ] T012 [ ] T013
- **Dependencies**: WP02. **Est.**: ~400 lines. **Prompt**: [tasks/WP03-unify-resolver-primitives.md](./tasks/WP03-unify-resolver-primitives.md)

### WP04 — aggregate.py consolidation (glob + thin adapter)
- **Goal**: Kill the silent-first-match glob (FR-008/T2) and make `_resolve_read_dir` a thin adapter (T3). (IC-03 + part IC-06)
- **Priority**: P2. **Independent test**: ambiguous-mid8 → typed error (mutation-verified); aggregate equivalence cells green.
- **Subtasks**: [ ] T014 [ ] T015 [ ] T016 [ ] T017
- **Dependencies**: WP02, WP03. **Est.**: ~320 lines. **Prompt**: [tasks/WP04-aggregate-consolidation.md](./tasks/WP04-aggregate-consolidation.md)

### WP05 — Typed-error pass-through (cheapest behavioral slice)
- **Goal**: Preserve `STATUS_READ_PATH_NOT_FOUND` / `MISSION_AMBIGUOUS_SELECTOR` through next/mission_runtime (FR-005, #2010 bug #15). No resolver change. (IC-04)
- **Priority**: P2 (independent). **Independent test**: bug #15 reproduced red then green.
- **Subtasks**: [ ] T018 [ ] T019 [ ] T020
- **Dependencies**: WP03. **Est.**: ~240 lines. **Prompt**: [tasks/WP05-typed-error-passthrough.md](./tasks/WP05-typed-error-passthrough.md)

### WP06 — Collapse to one resolver + coord-empty hard-fail (GATED on WP02 green)
- **Goal**: `resolve_status_surface_with_anchor` sole authority (FR-001/FR-007); migrate `status_transition.py` predicates + drain its C-002 allowlist (#1900); coord-empty hard-fail with the two-path message (FR-006) + ADR (#1716). (IC-06 + IC-08)
- **Priority**: P1 (the core). **Independent test**: SC-005 (0 raw-bypass besides topology-blind); coord-empty hard-fail message names both paths; #1900 allowlist drained.
- **Subtasks**: [ ] T021 [ ] T022 [ ] T023 [ ] T024 [ ] T025 [ ] T026
- **Dependencies**: WP02, WP03, WP04, WP05. **Est.**: ~480 lines. **Prompt**: [tasks/WP06-collapse-and-hardfail.md](./tasks/WP06-collapse-and-hardfail.md)

### WP07 — Retire the feature_dir_resolver shim (51-importer bulk-edit)
- **Goal**: Retire `missions/feature_dir_resolver.py` (FR-007/T6); migrate the 51 import sites via a scoped `occurrence_map.yaml` (import_paths). (IC-06)
- **Priority**: P2. **Independent test**: `rg "feature_dir_resolver import" src/` → 0; suite green.
- **Subtasks**: [ ] T027 [ ] T028 [ ] T029
- **Dependencies**: WP03, WP06. **Est.**: ~300 lines (bulk-edit). **Prompt**: [tasks/WP07-retire-feature-dir-resolver-shim.md](./tasks/WP07-retire-feature-dir-resolver-shim.md)

### WP08 — Load-bearing architectural guard
- **Goal**: Clone the 01KVFTFV guard — raw-bypass joins fail CI; load-bearing (real-code mutation + non-empty coverage on the WP01 inventory). (IC-07; FR-004)
- **Priority**: P2 (locks the collapse). **Independent test**: injected raw-bypass fails the guard; removing the guard makes the fixture pass.
- **Subtasks**: [ ] T030 [ ] T031 [ ] T032
- **Dependencies**: WP01, WP06. **Est.**: ~280 lines. **Prompt**: [tasks/WP08-load-bearing-guard.md](./tasks/WP08-load-bearing-guard.md)

## Dependency Graph

```
WP01 (audit) ───────────────────────────────────────────────┐
WP02 (equivalence gate) ──┬─▶ WP03 (primitives) ─┬─▶ WP04 ──┐ │
                          │                       ├─▶ WP05 ──┤ │
                          └──────────────(gate)───┴──────────▶ WP06 (collapse+hardfail) ─┬─▶ WP07 (shim retire)
                                                                                          └─▶ WP08 (guard) ◀── WP01
```

## MVP / Sequencing

- **MVP**: WP02 (gate) + WP03 (primitives) + WP06 (collapse) — the single resolver with the safety gate.
- WP01/WP05 start in parallel; WP04 after WP03; WP06 gated on equivalence-green; WP07/WP08 last.
