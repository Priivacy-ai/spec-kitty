# Tasks: Test Suite Acceleration

**Mission**: test-suite-acceleration-01KV3H59
**Branch**: `feat/test-suite-acceleration`
**Evidence**: [`architecture/test-suite-acceleration-plan.md`](../../architecture/test-suite-acceleration-plan.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/behavioral-contracts.md](./contracts/behavioral-contracts.md)

7 work packages, 30 subtasks. WPs are sized 4–6 subtasks each. Tests are the
subject of this mission, so every WP includes its own verification.

## Dependency & parallelization overview

```
WP01 (safe-now)        ─┐
WP02 (safety harness)  ─┤ (all three start in parallel — no deps)
WP04 (HOME isolation)  ─┘
        │        │            │
        │        └─> WP03 (de-dup, needs WP02)
        │                     │
        └────────┬────────────┘
                 └─> WP05 (CI parallel rollout, needs WP01+WP02+WP04)
        WP04 ─────────> WP06 (templated git fixture + hygiene, needs WP04)
        WP04+WP05 ────> WP07 (local default + docs)
```

**MVP / first lane**: WP01 + WP02 + WP04 in parallel. WP01 delivers the
immediate ≥60s/push safe-now win; WP04 unlocks all parallelism.

**Profiles**: reduction WPs are assigned to **randy-reducer** (semantic
compression). Architectural/infra WPs use implementer profiles. The recommended
*review* profiles for the parallelization-architecture and safety WPs are
**architect-alphonso** (WP04/WP05) and **paula-patterns** (WP02 cross-cutting
safety) — these are advisory/review roles whose avoidance boundary excludes
direct implementation.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Convert charter `<0.1` timing floors to `@pytest.mark.timeout` | WP01 | [P] |
| T002 | Reduce ULID volume 100→25 + `SPEC_KITTY_ULID_VOLUME_FULL` env-gate | WP01 | [P] |
| T003 | Sync `_guarded_final_sync` swallow tests → module-scoped sleep no-op | WP01 | [P] |
| T004 | Remove `-v` from `pytest.ini` addopts | WP01 | [P] |
| T005 | Collection-equivalence helper (serial vs xdist nodeids) + tests | WP02 | [P] |
| T006 | Run-twice/run-thrice stability ratchet helper + tests | WP02 | [P] |
| T007 | Architectural guard: no real `~/.spec-kitty` mutation under xdist | WP02 | [P] |
| T008 | Equivalence/mutation-check helper + recipe | WP02 | [P] |
| T009 | Collapse FSM parity matrix (accumulate-all) + mutation proof | WP03 | |
| T010 | Shared read-only migrated-project fixture (3 identical asserts) | WP03 | |
| T011 | Cache whole-tree AST behind fixture (architectural; carve-outs) | WP03 | |
| T012 | Cache DRG graph behind fixture (doctrine; carve-outs) | WP03 | |
| T013 | Per-worker HOME/XDG isolation autouse fixture | WP04 | |
| T014 | Compose existing queue-wipe fixtures under isolated home | WP04 | |
| T015 | Regression test: two workers → distinct homes, real home untouched | WP04 | |
| T016 | Audit import-time `SPEC_KITTY_DIR` reads | WP04 | |
| T017 | Slow-test de-dup (`and not slow` on specify-cli-heavy shard) | WP05 | |
| T018 | Flip charter fast shard to `-n auto --dist loadfile` (ratcheted) | WP05 | |
| T019 | Flip doctrine/cli/sync shards; exclude `release` shard | WP05 | |
| T020 | Flip agent shard (after HOME-isolation guard green) | WP05 | |
| T021 | Daemon/port serial pass (`-n0`) for orphan-sweep | WP05 | |
| T022 | Status re-route (inversion + collection gate + trigger widen) | WP05 | |
| T023 | Templated bare-repo fixture (build once, clone per test) | WP06 | |
| T024 | Adopt template via execution-allowlist; preserve bespoke repos | WP06 | |
| T025 | Trim sync concurrency loops (50→20, 20→10) + nightly variant | WP06 | |
| T026 | xfail strictness hygiene | WP06 | |
| T027 | Consolidate 8× subprocess `--collect-only` path-filter test | WP06 | |
| T028 | Document local parallel command + serial daemon-pass caveat | WP07 | |
| T029 | Testing-parallel docs page + config guidance | WP07 | |
| T030 | Wire quickstart validation helper | WP07 | |

---

## WP01 — Safe-now coverage-neutral reductions

- **Goal**: Land the wave-1 wins that need no parallelism dependency, removing ≥60s/push at zero coverage risk.
- **Priority**: P1 (MVP). **Independent test**: each changed test still passes serially; full-volume variants reachable via env gate.
- **Dependencies**: none.
- **Profile**: randy-reducer (implement). **Est. prompt size**: ~230 lines.
- **Requirements**: FR-006, FR-008, FR-013, NFR-003.

- [x] T001 Convert charter `<0.1` timing floors to `@pytest.mark.timeout` (WP01)
- [x] T002 Reduce ULID volume 100→25 + env-gate full volume (WP01)
- [x] T003 Sync swallow tests → module-scoped sleep no-op + retry assert (WP01)
- [x] T004 Remove `-v` from `pytest.ini` addopts (WP01)

## WP02 — Coverage-safety harness

- **Goal**: Build the safeguards that make every reduction/flip provably coverage-neutral.
- **Priority**: P1 (foundational). **Independent test**: helpers have direct unit tests; the guard fails on a simulated real-home mutation.
- **Dependencies**: none. **Consumed by**: WP03, WP05.
- **Profile**: implementer-ivan (implement); review: paula-patterns. **Est. prompt size**: ~260 lines.
- **Requirements**: FR-004, FR-012, NFR-005, NFR-007.

- [x] T005 Collection-equivalence helper + tests (WP02)
- [x] T006 Stability ratchet helper + tests (WP02)
- [x] T007 Architectural guard: no real home mutation under xdist (WP02)
- [x] T008 Equivalence/mutation-check helper + recipe (WP02)

## WP03 — Item-explosion & read-only de-duplication

- **Goal**: Cut collected-item explosion and per-test rebuilds of read-only state without losing assertions.
- **Priority**: P2. **Independent test**: collapsed/shared tests assert the same outcomes; mutation proof for the FSM collapse.
- **Dependencies**: WP02 (uses equivalence/mutation helpers).
- **Profile**: randy-reducer (implement). **Est. prompt size**: ~280 lines.
- **Requirements**: FR-008, FR-009, NFR-007.

- [x] T009 Collapse FSM parity matrix + mutation proof (WP03)
- [x] T010 Shared read-only migrated-project fixture (WP03)
- [x] T011 Cache whole-tree AST behind fixture (WP03)
- [x] T012 Cache DRG graph behind fixture (WP03)

## WP04 — Per-worker HOME/state isolation (master enabler)

- **Goal**: Give each xdist worker a distinct home so parallel runs never share/truncate the real `~/.spec-kitty/queue.db`.
- **Priority**: P1 (unblocks all parallelism). **Independent test**: regression test proves two workers get distinct homes; real home untouched.
- **Dependencies**: none. **Unblocks**: WP05, WP06, WP07.
- **Profile**: python-pedro (implement); review: architect-alphonso. **Est. prompt size**: ~250 lines.
- **Requirements**: FR-002.

- [x] T013 Per-worker HOME/XDG isolation autouse fixture (WP04)
- [x] T014 Compose existing queue-wipe fixtures under isolated home (WP04)
- [x] T015 Regression test: distinct homes, real home untouched (WP04)
- [x] T016 Audit import-time `SPEC_KITTY_DIR` reads (WP04)

## WP05 — CI fast-shard parallelization rollout

- **Goal**: Flip single-process fast-shards to file-pinned parallel execution, collapsing the critical path; charter first, ratcheted.
- **Priority**: P2 (biggest CI win). **Independent test**: per-shard collection equivalence + N green ratchet runs before each flip merges.
- **Dependencies**: WP01 (charter timing), WP02 (harness/ratchet), WP04 (HOME isolation).
- **Profile**: implementer-ivan (implement); review: architect-alphonso. **Est. prompt size**: ~300 lines.
- **Requirements**: FR-003, FR-004, FR-005, FR-007, FR-012, NFR-002.

- [x] T017 Slow-test de-dup on specify-cli-heavy shard (WP05)
- [x] T018 Flip charter shard to `-n auto --dist loadfile` (WP05)
- [x] T019 Flip doctrine/cli/sync shards; exclude `release` (WP05)
- [x] T020 Flip agent shard (WP05)
- [x] T021 Daemon/port serial pass for orphan-sweep (WP05)
- [x] T022 Status re-route + trigger widen (WP05)

## WP06 — Templated git-repo fixture & structural hygiene

- **Goal**: Replace repeated real `git init` with a templated baseline repo and finish lower-leverage structural cleanups.
- **Priority**: P3. **Independent test**: template-backed tests pass; bespoke repo tests unchanged; high-volume nightly variant retained.
- **Dependencies**: WP04 (parallel-safe).
- **Profile**: implementer-ivan (implement). **Est. prompt size**: ~290 lines.
- **Requirements**: FR-010.

- [x] T023 Templated bare-repo fixture (WP06)
- [x] T024 Adopt via execution-allowlist; preserve bespoke repos (WP06)
- [x] T025 Trim sync concurrency loops + nightly variant (WP06)
- [x] T026 xfail strictness hygiene (WP06)
- [x] T027 Consolidate 8× subprocess `--collect-only` test (WP06)

## WP07 — Local parallel default & contributor docs

- **Goal**: Make safe local multi-process runs the documented default.
- **Priority**: P3. **Independent test**: documented command runs green locally with the serial daemon pass; real home untouched.
- **Dependencies**: WP04, WP05 (charter flip green).
- **Profile**: curator-carla (implement/docs). **Est. prompt size**: ~180 lines.
- **Requirements**: FR-001, FR-011, NFR-001.

- [x] T028 Document local parallel command + caveat (WP07)
- [x] T029 Testing-parallel docs page + config guidance (WP07)
- [x] T030 Wire quickstart validation helper (WP07)
