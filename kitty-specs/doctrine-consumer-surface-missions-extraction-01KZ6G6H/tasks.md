# Tasks: Missions/ Doctrine Tree Relocation & Gate Preconditions

**Input**: Design documents from `kitty-specs/doctrine-consumer-surface-missions-extraction-01KZ6G6H/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `occurrence_map.yaml` (all present, all post-plan-squad-revised 2026-08-04)

## Subtask Index

| ID | Description | WP | Parallel |
|----|--------------|----|----------|
| T001 | Extract shared scan helpers (`Site`, `_rel`, `_read_lines`, `_text_files`, root constants) into a new shared module | WP01 | |
| T002 | Create CLI-wide gate module for Gate A + Gate B, with their discriminator-proof and planted-violation tests | WP01 | |
| T003 | Narrow `test_no_dead_doctrine_paths.py` to Gate C only, with its discriminator-proof and planted-violation tests | WP01 | |
| T004 | Give Gate D its own explicitly-named landing module | WP01 | |
| T005 | Verify NFR-003/NFR-004: full gate suite green, no assertion dropped, note coverage-baseline regen if touched | WP01 | |
| T006 | Design and implement a `tmp_path`-planted synthetic fixture for the NFR-002 discriminator proof | WP02 | |
| T007 | Redrive `test_forbidding_mention_would_false_red_without_its_discriminator` against the fixture | WP02 | |
| T008 | Apply the same fixture-decoupling to Gate C's on-disk cross-link case | WP02 | |
| T009 | Remove the `src/doctrine/graph.yaml` mention from `doctrine-daphne.agent.yaml`'s `avoidance-boundary` (the "daphne cleanup") | WP02 | |
| T010 | Verify: full gate suite green with the cleanup applied, and a planted violation still reds | WP02 | |
| T011 | Trace every `doctrine.missions.*` symbol usage across doctrine/kernel/charter/specify_cli/upgrade migrations (not path-literal grep alone) | WP03 | [P] |
| T012 | Record `MissionTemplateRepository.default_missions_root()` and `drg/migration/extractor.py::_missions_root()` explicitly, with move/stay/repoint decisions | WP03 | [P] |
| T013 | Classify the `.py`-vs-data-content split within `src/doctrine/missions/` explicitly | WP03 | [P] |
| T014 | Commit the inventory as a reviewable artifact | WP03 | |
| T015 | Design and implement the kernel-owned sibling-path-resolution primitive | WP04 | [P] |
| T016 | Repoint `kernel.paths.get_package_asset_root()` onto the primitive; remove `_looks_like_missions_root`/`_resolve_env_root` | WP04 | |
| T017 | Converge `doctrine.pack_paths._resolve_built_in()` onto the primitive; preserve `doctrine_package_dir()`; translate the exception to `PackRootNotFound` | WP04 | |
| T018 | Converge `MissionTemplateRepository.default_missions_root()` onto the primitive | WP04 | |
| T019 | Write the new kernel-scoped AST-walk architectural test, with self-mutation non-vacuity proof | WP04 | |
| T020 | Verify NFR-001: full existing suite green (`tests/kernel`, `tests/doctrine`, `tests/charter`) | WP04 | |
| T021 | Move the data subdirectories from `src/doctrine/missions/` to `packs/built-in/missions/` | WP05 | |
| T022 | Repoint every reader WP03's inventory identified (`specify_cli`, `runtime`, upgrade migrations) | WP05 | |
| T023 | Repoint `drg/migration/extractor.py::_missions_root()` to the new location | WP05 | |
| T024 | Regenerate `packs/built-in/mission_type.graph.yaml`/`mission_step_contract.graph.yaml`; diff against committed state | WP05 | |
| T025 | Verify NFR-001/SC-008: full suite green, incl. `test_regen_roundtrip.py`; `.py` modules still importable | WP05 | |
| T026 | Add a red-first reproduction test for the activated-but-unresolvable-profile scenario | WP06 | [P] |
| T027 | Fix `UnknownMissionTypeError`'s message to state the two facts separately | WP06 | |
| T028 | Verify: new reproduction test passes; existing test still passes | WP06 | |
| T029 | Review/refresh `implement.md` against the current canonical template | WP07 | [P] |
| T030 | Review/refresh `review.md` against the current canonical template | WP07 | [P] |
| T031 | Verify: neither file references raw construction or the retired `constitution context` command | WP07 | |

## Work Packages

### WP01 — Gate-file scope split + shared-helper extraction

- **Priority**: P1 (High) · **Requirements**: FR-001, NFR-003, NFR-004
- **Goal**: Split `tests/architectural/test_no_dead_doctrine_paths.py` by actual current scope (Gate A + Gate B together, both `src/`-wide; Gate C alone, doctrine-scoped; Gate D alone, `docs/`-scoped), extracting the shared scan helpers into one common module.
- **Independent test**: Every pre-split assertion passes in its post-split module; no gate's scan root narrowed.
- **Included subtasks**: T001–T005
- **Dependencies**: none — first WP to land (precondition for WP02/WP03/WP05 per spec's binding Sequencing note)
- **Estimated prompt size**: ~350 lines

### WP02 — Synthetic-fixture decoupling + daphne cleanup

- **Priority**: P1 (High) · **Requirements**: FR-002, SC-006
- **Goal**: Redrive the NFR-002 discriminator proof onto a planted synthetic fixture (per issue #3036's own recorded design — explicitly NOT a loosened assertion), then perform the "daphne cleanup" it enables.
- **Independent test**: Removing the daphne repo-local reference passes the gate; a planted violation against the fixture still reds it.
- **Included subtasks**: T006–T010
- **Dependencies**: WP01 (module split lands first)
- **Estimated prompt size**: ~350 lines

### WP03 — Cross-layer `missions/` reader inventory

- **Priority**: P1 (High) · **Requirements**: FR-003, SC-007
- **Goal**: Produce the committed, reviewable reader inventory — by symbol-tracing, not path-literal grepping — explicitly including the two already-identified sites (`MissionTemplateRepository.default_missions_root()`, the DRG extractor) and the `.py`-vs-data split.
- **Independent test**: The inventory artifact exists, every row has a decision + rationale, and the two named sites are present.
- **Included subtasks**: T011–T014
- **Dependencies**: WP01, WP02 (gates land before any relocation-adjacent step, per spec's binding Sequencing note)
- **Estimated prompt size**: ~250 lines (research/analysis WP — `planning_artifact` execution mode)
- **Note**: deliverable lives at `docs/plans/doctrine/missions-reader-inventory-01KZ6G6H.md`, not inside `kitty-specs/<mission>/` — `finalize-tasks` currently rejects any WP `owned_files` entry under `kitty-specs/` (known gap, issue #2643).

### WP04 — Kernel-owned resolution primitive + three-way convergence

- **Priority**: P1 (High) · **Requirements**: FR-004, NFR-002
- **Goal**: Extract the domain-agnostic sibling-path-resolution primitive into `src/kernel/`; converge `pack_paths._resolve_built_in()` and `MissionTemplateRepository.default_missions_root()` onto it; prove kernel is clean with a new AST-walk gate.
- **Independent test**: `src/kernel/paths.py` holds no doctrine/specify_cli-identifying string; the new gate reds on self-mutation.
- **Included subtasks**: T015–T020
- **Dependencies**: none — runs in parallel with WP01/WP02/WP03
- **Estimated prompt size**: ~450 lines

### WP05 — `missions/` data relocation + reader repoint (one atomic change)

- **Priority**: P1 (High) · **Requirements**: FR-005, SC-001, SC-007, SC-008, NFR-001
- **Goal**: Move the data subdirectories to `packs/built-in/missions/` and repoint every identified reader — including the DRG extractor and its two generated fragments — **in one atomically-reviewed change**, per the bulk-edit `occurrence_map.yaml`'s own `moves:` block.
- **Independent test**: `src/doctrine/missions/`'s data subdirectories are gone; `.py` modules still importable; DRG fragments regenerate byte-identical; full suite green.
- **Included subtasks**: T021–T025
- **Dependencies**: WP03 (inventory) **and** WP04 (primitive) — fork/join, both required
- **Estimated prompt size**: ~400 lines
- **Governance**: `change_mode: bulk_edit` — `occurrence_map.yaml` (already authored, schema-valid) governs this WP; do not claim a file outside its `moves:`/exception scope without updating the map first.

### WP06 — Mission-type error message fix

- **Priority**: P2 (Medium) · **Requirements**: FR-006, SC-003
- **Goal**: Fix `UnknownMissionTypeError`'s self-contradictory message, red-first.
- **Independent test**: A new reproduction of the activated-but-unresolvable case passes; the existing unrelated test still passes.
- **Included subtasks**: T026–T028
- **Dependencies**: none — fully independent
- **Estimated prompt size**: ~200 lines

### WP07 — TIER-1 override template refresh

- **Priority**: P3 (Low) · **Requirements**: FR-007, SC-004
- **Goal**: Refresh the two stale dogfood override templates onto the canonical construction pattern; remove the retired command reference.
- **Independent test**: Neither file references raw construction or `constitution context`.
- **Included subtasks**: T029–T031
- **Dependencies**: none — fully independent
- **Estimated prompt size**: ~180 lines

## Dependency Graph

```
WP01 ─→ WP02 ─→ WP03 ─┐
                       ├─→ WP05
              WP04 ────┘

WP06 (independent)
WP07 (independent)
```

## Parallelization

- **Lane A**: WP01 → WP02 → WP03 (sequential — the spec's binding Sequencing note)
- **Lane B**: WP04 (fully parallel to Lane A)
- **Join**: WP05 waits on both Lane A (WP03) and Lane B (WP04)
- **Independent**: WP06, WP07 can run in any lane, any time

## MVP Scope

WP01 + WP02 (the two CI-gate preconditions) is the smallest independently-valuable slice — it unblocks legitimate doctrine-content cleanup even before the relocation itself lands.
