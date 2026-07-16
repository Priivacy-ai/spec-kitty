# Tasks: Mission-Type DRG Edges + Graph Sharding

**Mission**: `mission-type-drg-edges-01KXKY2N` · **Branch**: `feat/mission-type-drg-edges`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Issues**: #2677 + #2680

Two-phase, edges-first (post-plan squad; see [traces/design-decisions.md](./traces/design-decisions.md) DD-0).
Flat topology; a strict dependency chain enforces **Phase 1 (edges) fully lands before any Phase-2 (sharding)
WP starts**, and routes **every** reader (src + test) through the canonical seam **before** the monolith is
deleted — so no WP ever leaves the suite red.

## Delivery order & dependency chain

```
WP01 (edges → monolith)
  └─ WP02 (Phase-1 tests + orphan gate + residual reconcile)
       └─ WP03 (seam + src readers + snapshot + docstrings)
            └─ WP04 (test-reader migration to the seam fixture)
                 └─ WP05 (write-partition + ATOMIC monolith delete + regenerate sharded)
                      └─ WP06 (equality + partition-totality + silent-degrade proofs)
```

Phase boundary: **WP01–WP02 = Phase 1 (#2677)** ship the edges against the monolith and clear the red orphan
gate (18→10). **WP03–WP06 = Phase 2 (#2680)** are the behavior-preserving sharding migration.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | `extract_mission_type_edges` pass in extractor.py | WP01 | |
| T002 | Concatenate edges into `all_edges` before `calibrate_surfaces` | WP01 | |
| T003 | Add `"mission_type"` to `_KIND_MAP` + retire `:778` caveat | WP01 | |
| T004 | Correct `models.py:46` comment | WP01 | |
| T005 | Regenerate + commit the monolith `graph.yaml` (byte-identity) | WP01 | |
| T006 | [RED] focused generator edge tests (plan=4, documentation=7, 21 total, no orphan) | WP02 | |
| T007 | Re-pin `test_mission_type_nodes_have_no_incident_edges` (invert + docstrings) | WP02 | |
| T008 | Verify orphan gate greens at 10 ≤ 14 (no ceiling raise) | WP02 | |
| T009 | Reconcile `drg-orphan-residual.md` (stale 14 → 10) | WP02 | |
| T010 | DRG/arch gates + freshness `--check` green | WP02 | |
| T011 | Add `load_built_in_graph()`/`built_in_graph_source()` seam + unit test | WP03 | |
| T012 | Route `agent_profiles/repository.py` (`_default_drg_path` + :289) through the seam | WP03 | |
| T013 | Route `pack_validator.py:513` + `calibration/walker.py:430-437` through the seam | WP03 | [P] |
| T014 | Route `charter_runtime/lint/_drg.py:52,85` through the seam | WP03 | [P] |
| T015 | Route the 6 already-safe `load_graph_or_dir` consumers through the seam | WP03 | [P] |
| T016 | Review `snapshot.py:62/:200` filename categorization for fragments | WP03 | |
| T017 | Update `models.py`-family load-bearing docstrings (monolith → sharded) | WP03 | [P] |
| T018 | Add shared seam fixture in `conftest.py` | WP04 | |
| T019 | Migrate the doctrine test modules to the fixture | WP04 | |
| T020 | Migrate the charter test modules to the fixture | WP04 | [P] |
| T021 | Layout-agnostic `_count_orphans` + freshness/stale twins in `test_doctrine_regenerate_graph.py` | WP04 | |
| T022 | Full suite green + grep-gate (zero residual monolith-path reads) | WP04 | |
| T034 | Route the 6 post-task-squad readers (specify_cli/calibration/arch + repo-root sentinels) | WP04 | |
| T023 | [RED] test: fragments present ∧ monolith absent | WP05 | |
| T024 | `generate_graph`/`_write_graph_yaml` → per-populated-kind fragments | WP05 | |
| T025 | Atomic delete of `src/doctrine/graph.yaml` in the same write | WP05 | |
| T026 | Update `regenerate-graph` (+`--check`) for the sharded layout | WP05 | |
| T027 | Regenerate → commit fragments; pin fragment dir == loader glob root | WP05 | |
| T028 | Freshness twins + orphan gate + arch/DRG gates green (sharded) | WP05 | |
| T029 | [RED] merged-graph set-equality under the pinned merge-order contract (DD-9) | WP06 | |
| T030 | Partition-totality test (every populated node-kind round-trips) | WP06 | |
| T031 | Silent-degrade proof: profile `specializes_from` lineage identical before/after | WP06 | |
| T032 | Silent-degrade proof: charter-lint `GraphState` + pack-validator built-in URN set identical | WP06 | |
| T033 | ruff+mypy strict clean; arch/DRG/freshness gates green; `assert_valid` | WP06 | |

---

## WP01 — Mission-type edges → regenerate the monolith (Phase 1, #2677)

**Priority**: MVP · **Prompt**: [tasks/WP01-mission-type-edges.md](./tasks/WP01-mission-type-edges.md) · **Deps**: none · **~300 lines**
**Independent test**: regenerating the DRG emits 21 `mission_type→action` `requires` edges; `assert_valid` passes; the monolith is byte-identical on a second regenerate.

- [x] T001 `extract_mission_type_edges` pass in extractor.py (WP01)
- [x] T002 Concatenate edges into `all_edges` before `calibrate_surfaces` (WP01)
- [x] T003 Add `"mission_type"` to `_KIND_MAP` + retire `:778` caveat (WP01)
- [x] T004 Correct `models.py:46` comment (WP01)
- [x] T005 Regenerate + commit the monolith `graph.yaml` (byte-identity) (WP01)

## WP02 — Phase-1 tests, orphan gate, residual reconcile (Phase 1, #2677)

**Priority**: MVP · **Prompt**: [tasks/WP02-phase1-tests-and-residual.md](./tasks/WP02-phase1-tests-and-residual.md) · **Deps**: WP01 · **~320 lines**
**Independent test**: the re-pinned + new edge tests are green; `test_shipped_graph_orphan_count_within_documented_residual` passes at 10 ≤ 14 without a ceiling change; the residual doc reads 10.

- [x] T006 [RED] focused generator edge tests (plan=4, documentation=7, 21 total, no orphan) (WP02)
- [x] T007 Re-pin `test_mission_type_nodes_have_no_incident_edges` (invert + docstrings) (WP02)
- [x] T008 Verify orphan gate greens at 10 ≤ 14 (no ceiling raise) (WP02)
- [x] T009 Reconcile `drg-orphan-residual.md` (stale 14 → 10) (WP02)
- [x] T010 DRG/arch gates + freshness `--check` green (WP02)

## WP03 — Canonical built-in-graph seam + src readers (Phase 2, #2680)

**Priority**: High · **Prompt**: [tasks/WP03-builtin-graph-seam.md](./tasks/WP03-builtin-graph-seam.md) · **Deps**: WP02 · **~420 lines**
**Independent test**: every shipped-graph src reader routes through `load_built_in_graph()`; behavior is unchanged (monolith still present, `load_graph_or_dir` reads it); seam unit test green.

- [x] T011 Add `load_built_in_graph()`/`built_in_graph_source()` seam + unit test (WP03)
- [x] T012 Route `agent_profiles/repository.py` (`_default_drg_path` + :289) through the seam (WP03)
- [x] T013 Route `pack_validator.py:513` + `calibration/walker.py:430-437` through the seam (WP03)
- [x] T014 Route `charter_runtime/lint/_drg.py:52,85` through the seam (WP03)
- [x] T015 Route the 6 already-safe `load_graph_or_dir` consumers through the seam (WP03)
- [x] T016 Review `snapshot.py:62/:200` filename categorization for fragments (WP03)
- [x] T017 Update `models.py`-family load-bearing docstrings (monolith → sharded) (WP03)

## WP04 — Test-reader migration to the seam fixture (Phase 2, #2680)

**Priority**: High · **Prompt**: [tasks/WP04-test-reader-migration.md](./tasks/WP04-test-reader-migration.md) · **Deps**: WP03 · **~360 lines**
**Independent test**: the grep-gate returns zero built-in-monolith reads across `tests/` (conftest seam excepted); all **22** modules read through the shared fixture / a delete-stable marker; the full suite is green against the still-present monolith.

- [x] T018 Add shared seam fixture in `conftest.py` (WP04)
- [x] T019 Migrate the doctrine test modules to the fixture (WP04)
- [x] T020 Migrate the charter test modules to the fixture (WP04)
- [x] T021 Layout-agnostic `_count_orphans` + freshness/stale twins in `test_doctrine_regenerate_graph.py` (WP04)
- [x] T022 Full suite green + grep-gate: zero residual monolith-path reads (WP04)
- [x] T034 Route the 6 post-task-squad readers (specify_cli/calibration/arch + repo-root sentinels) (WP04)

## WP05 — Generator write-partition + atomic monolith retire (Phase 2, #2680)

**Priority**: High · **Prompt**: [tasks/WP05-shard-write-partition.md](./tasks/WP05-shard-write-partition.md) · **Deps**: WP04 · **~360 lines**
**Independent test**: regenerating writes per-kind `src/doctrine/*.graph.yaml` fragments, the monolith `graph.yaml` is deleted, and `regenerate-graph --check` reports the sharded layout fresh.

- [x] T023 [RED] test: fragments present ∧ monolith absent (WP05)
- [x] T024 `generate_graph`/`_write_graph_yaml` → per-populated-kind fragments (WP05)
- [x] T025 Atomic delete of `src/doctrine/graph.yaml` in the same write (WP05)
- [x] T026 Update `regenerate-graph` (+`--check`) for the sharded layout (WP05)
- [x] T027 Regenerate → commit fragments; pin fragment dir == loader glob root (WP05)
- [x] T028 Freshness twins + orphan gate + arch/DRG gates green (sharded) (WP05)

## WP06 — Behavior-preserving proofs: equality, totality, silent-degrade (Phase 2, #2680)

**Priority**: High · **Prompt**: [tasks/WP06-behavior-preserving-proofs.md](./tasks/WP06-behavior-preserving-proofs.md) · **Deps**: WP05 · **~300 lines**
**Independent test**: the merged sharded graph equals the pre-sharding graph under the pinned merge-order contract; every populated node-kind round-trips; profile lineage, charter-lint `GraphState`, and pack-validator built-in URN set are identical before/after.

- [ ] T029 [RED] merged-graph set-equality under the pinned merge-order contract (DD-9) (WP06)
- [ ] T030 Partition-totality test (every populated node-kind round-trips) (WP06)
- [ ] T031 Silent-degrade proof: profile `specializes_from` lineage identical before/after (WP06)
- [ ] T032 Silent-degrade proof: charter-lint `GraphState` + pack-validator built-in URN set identical (WP06)
- [ ] T033 ruff+mypy strict clean; arch/DRG/freshness gates green; `assert_valid` (WP06)

---

## Parallelization

Cross-WP: **none** — the chain is strictly linear (each WP depends on the prior) because the shared surfaces
(`extractor.py`, the graph artefact, the orphan-gate reader) must be linearized and the monolith delete must
follow all reader migrations. Intra-WP `[P]` markers (WP03 T013/T014/T015/T017, WP04 T020) note independent
files a single implementer can batch.

## MVP scope

**WP01 + WP02** are the shippable MVP: they clear the red-on-main orphan gate (#2677) independently of the
sharding migration. WP03–WP06 (#2680) follow as the behavior-preserving enabler.
