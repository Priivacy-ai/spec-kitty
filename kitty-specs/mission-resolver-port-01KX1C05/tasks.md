# Tasks: MissionResolver Port (2173 Phase 2)

**Mission**: `mission-resolver-port-01KX1C05` · **Branch**: `feat/mission-resolver-port-2173`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

7 work packages from the 7 implementation concerns. The DDD rename (WP01) is linearized first; the
resolver core (WP02) → trunk threading (WP03) → gate (WP04) form the spine; #2139 / Clock / InstalledVersion
(WP05–WP07) are independent siblings that only depend on the rename settling.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Rename `ExecutionContext` class + docstring → `MissionExecutionContext` in `context.py` | WP01 | | [D] | [D] |
| T002 | Update the `ActionContext` alias + module docstring to the new name | WP01 | | [D] |
| T003 | Mechanical rename across the ~12 importers + usages (out-of-map, documented) | WP01 | | [D] |
| T004 | Update ADR prose (`2026-06-22-1`, `2026-06-03-1`) | WP01 | | [D] |
| T005 | Verify: full `tests/architectural/` + parity + surface gates green; StrEnum untouched | WP01 | | [D] |
| T006 | Define `MissionResolver` Protocol in `mission_runtime/mission_resolver_port.py` | WP02 | | [D] |
| T007 | `FsMissionResolver` adapter (wrap `_build_index`) in `context/mission_resolver.py` | WP02 | | [D] |
| T008 | `FakeMissionResolver` in-memory adapter | WP02 | | [D] |
| T009 | Free `resolve_mission` gains optional `resolver=None` param (single-site injection) | WP02 | | [D] |
| T010 | Fail-closed cold-miss/ambiguity + `backfill-identity` message (FR-005) | WP02 | | [D] |
| T011 | Resolver unit tests (CT-1…CT-7, FS-free Fake) | WP02 | | [D] |
| T012 | Thread `resolver` through the canonicalizer chain (`_read_path_resolver.py:503`) | WP03 | | [D] |
| T013 | Thread `resolver` through the shell callers (`resolve_action_context`, `mission_context_for`, `resolve_placement_only`) | WP03 | | [D] |
| T014 | Legacy-`<slug>` bootstrap sentinel carve-out + regression test (D-07) | WP03 | | [D] |
| T015 | Adopt the 2 resolve-by-identity consumers (`apply.py`, `vcs/detection.py`) | WP03 | | [D] |
| T016 | Free-function caller audit (verify 8 now trunk; edit only if injection needed) | WP03 | | [D] |
| T017 | FS-free builder identity test (NFR-001, scoped) + layer/purity/no-cache verify | WP03 | | [D] |
| T018 | Write the ADR (trunk, ledger-dodge, no-cache, fail-closed) | WP04 | |
| T019 | New AST gate `test_mission_resolver_walker_gate.py` seeded with full ~16-walker allowlist | WP04 | |
| T020 | Verify gate green on introduction + discriminate enumeration vs single-dir access | WP04 | |
| T021 | Route the ≥9 `target_branch` readers onto `read_target_branch_from_meta` | WP05 | [D] |
| T022 | Delete divergent `"main"`/`""`/`None` defaults; triage `KeyError` dataclass reads OUT | WP05 | [D] |
| T023 | `target_branch` reconcile characterization test | WP05 | [D] |
| T024 | Consolidate the 12 isoformat `_now_utc` copies → one canonical helper | WP06 | [D] |
| T025 | Triage the 2 cross-package copies; preserve 2 stamp + 2 datetime helpers | WP06 | [D] |
| T026 | SAFE campsite: `mission_parsing.py:259` literal → shared constant; NFR-004 byte-identical test | WP06 | [D] |
| T027 | Route the `m_2_1_4` migration version read through `_CliStatusLike` | WP07 | [D] |
| T028 | `#2447`: repoint/remove the phantom doctrine row + terminology guard | WP07 | [D] |
| T029 | Add the "every `src/…` path in `git-operations-matrix.md` resolves" guard test | WP07 | [D] |

---

## WP01 — DDD rename: ExecutionContext → MissionExecutionContext

- **Goal**: Code follows the ubiquitous language (#1619); remove the collision with `ExecutionContext(StrEnum)`.
- **Priority**: P0 (foundation — everything downstream uses the new name).
- **Independent test**: full `tests/architectural/` + `test_execution_context_parity.py` green; `grep -rn "class ExecutionContext" src` shows only the StrEnum in `core/context_validation.py`.
- **Subtasks**: T001–T005. **Depends on**: none. **Prompt**: [tasks/WP01-ddd-rename-mission-execution-context.md](./tasks/WP01-ddd-rename-mission-execution-context.md) (~250 lines)
- **Requirements**: FR-012.

## WP02 — MissionResolver port: Protocol + adapters + free-fn delegate

- **Goal**: The injectable seam over the single walk; `FakeMissionResolver` enables FS-free tests.
- **Priority**: P0 (spine).
- **Independent test**: resolver unit tests CT-1…CT-7 pass, incl. the Fake with no `kitty-specs/` tree.
- **Subtasks**: T006–T011. **Depends on**: WP01. **Prompt**: [tasks/WP02-missionresolver-port-core.md](./tasks/WP02-missionresolver-port-core.md) (~320 lines)
- **Requirements**: FR-001, FR-005.

## WP03 — Thread the trunk: shell + canonicalizer + sentinel

- **Goal**: Make the port the single walk trunk end-to-end; reconcile the bootstrap sentinel; deliver the FS-free builder identity test.
- **Priority**: P0 (spine).
- **Independent test**: FS-free builder identity test green; `test_layer_rules.py` green (zero new ledger edge); bootstrap sentinel regression green.
- **Subtasks**: T012–T017. **Depends on**: WP02. **Prompt**: [tasks/WP03-thread-resolver-trunk.md](./tasks/WP03-thread-resolver-trunk.md) (~360 lines)
- **Requirements**: FR-002, FR-003, FR-004, FR-005.

## WP04 — ADR + AST call-site gate (bind by construction)

- **Goal**: Record the decision; make "one sanctioned walker" structural.
- **Priority**: P1.
- **Independent test**: the new gate passes with the full ~16-walker allowlist and fails a planted raw `iterdir`.
- **Subtasks**: T018–T020. **Depends on**: WP03. **Prompt**: [tasks/WP04-adr-and-walker-gate.md](./tasks/WP04-adr-and-walker-gate.md) (~240 lines)
- **Requirements**: FR-006, FR-007.

## WP05 — #2139 target_branch reconcile (all readers)

- **Goal**: One fail-closed `target_branch` authority; no silent-default divergence.
- **Priority**: P1 (sibling).
- **Independent test**: reconcile characterization test; `grep` shows no `get("target_branch", "main"/"")` outside the authority.
- **Subtasks**: T021–T023. **Depends on**: WP01. **Prompt**: [tasks/WP05-target-branch-reconcile.md](./tasks/WP05-target-branch-reconcile.md) (~220 lines)
- **Requirements**: FR-008.

## WP06 — Clock consolidation (+ Sonar stamp campsite)

- **Goal**: One canonical wall-clock ISO helper; preserve stamp/datetime; on-disk timestamps unchanged.
- **Priority**: P1 (sibling).
- **Independent test**: NFR-004 byte-identical characterization test; one canonical helper reachable from all folded sites.
- **Subtasks**: T024–T026. **Depends on**: WP01. **Prompt**: [tasks/WP06-clock-consolidation.md](./tasks/WP06-clock-consolidation.md) (~240 lines)
- **Requirements**: FR-009.

## WP07 — InstalledVersion routing + #2447 doc tail

- **Goal**: Route the migration version read through the existing Protocol; fix the shipped doctrine phantom + guard it.
- **Priority**: P1 (sibling).
- **Independent test**: migration read goes through `_CliStatusLike`; the doctrine-path guard fails a planted phantom.
- **Subtasks**: T027–T029. **Depends on**: WP01. **Prompt**: [tasks/WP07-installed-version-and-doc-tail.md](./tasks/WP07-installed-version-and-doc-tail.md) (~220 lines)
- **Requirements**: FR-010, FR-011.

---

## Dependencies

```
WP01 (rename) ──┬── WP02 ── WP03 ── WP04
                ├── WP05  [P]
                ├── WP06  [P]
                └── WP07  [P]
```

## MVP / sequencing

WP01→WP02→WP03 is the critical path (the actual #1619 unblock lands at WP03's FS-free identity test).
WP04 hardens it. WP05/WP06/WP07 parallelize after WP01. Per-WP Sonar census at implement (operator
standing instruction): SAFE→fold, ADJACENT→note, OUT→tracked (see tracer-tooling-friction).
