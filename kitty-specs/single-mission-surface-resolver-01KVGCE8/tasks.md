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
| T001 | Repoint the 01KVFTFV audit AST walker to surface-resolution callsites | WP01 | [P] | [D] | [D] |
| T002 | Classify each callsite routed-through-resolver / topology-blind / raw-bypass | WP01 | | [D] |
| T003 | Emit `surface-resolution-inventory.md` + known-candidate self-assert | WP01 | | [D] |
| T004 | Produce the audited-surface list for WP08's guard | WP01 | | [D] |
| T005 | Build the (slug × mid8 × topology) equivalence matrix fixtures | WP02 | [D] |
| T006 | Differential test: every entry point → same dir OR same typed error | WP02 | | [D] |
| T007 | Cover all input classes incl. coord-empty + ambiguous-mid8 + `<slug>-<mid8>` handle | WP02 | | [D] |
| T008 | Mark the initially-RED cells (documents the divergences the fixes close) | WP02 | | [D] |
| T009 | Disambiguate the two same-named `primary_feature_dir_for_mission` → canonical raw-slug topology-blind; shim re-exports it (FR-009/T1; NOT a mid8 merge) | WP03 | | [D] |
| T010 | Single composition grammar via `_compose_mission_dir` (T5) | WP03 | | [D] |
| T011 | Extract the shared `resolve-dir-or-typed-error` delegator (T4) | WP03 | | [D] |
| T012 | Per-caller-class regression tests (bare-slug / `<slug>-<mid8>` / backfilled) | WP03 | | [D] |
| T013 | Gates; equivalence matrix mid8-handle cells turn green | WP03 | | [D] |
| T014 | Kill `aggregate._find_meta_path` silent-first-match glob → canonical handle resolver (FR-008/T2) | WP04 | | [D] |
| T015 | `aggregate._resolve_read_dir` → thin adapter (drop the unmaterialized-coord re-gate, T3) | WP04 | | [D] |
| T016 | Negative tests (ambiguous-mid8 → typed error; mutation-verified) | WP04 | | [D] |
| T017 | Gates; aggregate's equivalence cells green | WP04 | | [D] |
| T018 | Translate the un-caught MISSION_AMBIGUOUS_SELECTOR through the resolution.py boundary (FR-005; corrected premise) | WP05 | | [D] |
| T019 | LIVE ambiguous-handle repro red→green (no born-green) | WP05 | | [D] |
| T020 | Gates | WP05 | | [D] |
| T021 | Make `resolve_status_surface_with_anchor` the sole selection authority (FR-001/FR-007) | WP06 | | [D] |
| T022 | Migrate `status_transition.py` coord predicates to the canonical resolver (#1900) | WP06 | | [D] |
| T023 | Drain the C-002 topology-ratchet allowlist entry for status_transition.py | WP06 | | [D] |
| T024 | Coord-empty hard-fail with the two-path message (FR-006) | WP06 | | [D] |
| T025 | ADR for the coord-empty fallback policy (#1716) | WP06 | | [D] |
| T026 | Gates; equivalence green across all cells; no regression | WP06 | | [D] |
| T027 | Retire `missions/feature_dir_resolver.py` shim; classify the 51 import sites (occurrence_map.yaml, import_paths) | WP07 | | [D] |
| T028 | Migrate all callers to the canonical module | WP07 | | [D] |
| T029 | Gates; `rg "feature_dir_resolver import" src/` → 0 | WP07 | | [D] |
| T030 | Clone the 01KVFTFV load-bearing guard for surface resolution (FR-004) | WP08 | | [D] |
| T031 | Load-bearing self-test (real-code raw-bypass mutation + non-empty coverage assertion) | WP08 | | [D] |
| T032 | Gates; guard green on the collapsed tree; full suite | WP08 | | [D] |

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
- **Goal**: Disambiguate the two same-named `primary_feature_dir_for_mission` (FR-009/T1) — keep the canonical **raw-slug topology-blind** form (01KTRC04 FR-003; do NOT merge onto mid8); the shim re-exports it. Single composition grammar (T5); extract the shared resolve-dir-or-typed-error delegator (T4). (IC-01)
- **Priority**: P1. **Independent test**: one `primary_feature_dir_for_mission`; per-caller-class tests pass; equivalence mid8 cells green.
- **Subtasks**: [ ] T009 [ ] T010 [ ] T011 [ ] T012 [ ] T013
- **Dependencies**: WP02. **Est.**: ~400 lines. **Prompt**: [tasks/WP03-unify-resolver-primitives.md](./tasks/WP03-unify-resolver-primitives.md)

### WP04 — aggregate.py consolidation (glob + thin adapter)
- **Goal**: Kill the silent-first-match glob (FR-008/T2) and make `_resolve_read_dir` a thin adapter (T3). (IC-03 + part IC-06)
- **Priority**: P2. **Independent test**: ambiguous-mid8 → typed error (mutation-verified); aggregate equivalence cells green.
- **Subtasks**: [ ] T014 [ ] T015 [ ] T016 [ ] T017
- **Dependencies**: WP02, WP03. **Est.**: ~320 lines. **Prompt**: [tasks/WP04-aggregate-consolidation.md](./tasks/WP04-aggregate-consolidation.md)

### WP05 — Typed-error pass-through (cheapest behavioral slice)
- **Goal**: Translate the **un-caught** `MISSION_AMBIGUOUS_SELECTOR` through the `resolution.py` boundary (FR-005, #2010 bug #15 family). The `STATUS_READ_PATH_NOT_FOUND`/`runtime_bridge` flatten is **already guarded** — corrected premise; no resolver change. (IC-04)
- **Priority**: P2 (independent). **Independent test**: LIVE ambiguous-handle repro red on `main` then green.
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
- **Dependencies**: WP01, WP06, WP07 (final post-shim tree). **Est.**: ~280 lines. **Prompt**: [tasks/WP08-load-bearing-guard.md](./tasks/WP08-load-bearing-guard.md)

## Dependency Graph

```
WP01 (audit) ─────────────────────────────────────────────────────────────┐
WP02 (equivalence gate) ──┬─▶ WP03 (primitives) ─┬─▶ WP04 ──┐               │
                          │                       ├─▶ WP05 ──┤               │
                          └──────────────(gate)───┴──────────▶ WP06 (collapse+hardfail) ─▶ WP07 (shim retire) ─▶ WP08 (guard) ◀── WP01
```
(WP08 depends on WP01 + WP06 + WP07 — the guard locks the FINAL post-shim surface set.)

## MVP / Sequencing

- **MVP**: WP02 (gate) + WP03 (primitives) + WP06 (collapse) — the single resolver with the safety gate.
- WP01/WP05 start in parallel; WP04 after WP03; WP06 gated on equivalence-green; WP07/WP08 last.
