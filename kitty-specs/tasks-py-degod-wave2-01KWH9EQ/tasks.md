# Tasks: Tasks Degod Wave 2: Render Seam + Relocation

**Mission**: `tasks-py-degod-wave2-01KWH9EQ` | **Branch**: `degod-follow-ups` | **Generated**: 2026-07-02
**Input**: spec.md (rev 3), plan.md (IC-01..IC-08), research.md (D1–D10), data-model.md, contracts/

Pure-parity refactor: every WP is guarded by the four-layer parity contract
(`contracts/parity-contract.md`). The chain is deliberately LINEAR — every relocation WP
edits the shared `tasks.py` surface, so WPs sequence through dependencies (refactor
missions linearize shared surfaces; parallel lanes would collide on the god-file).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Pin venv to uv.lock; verify typer version | WP01 | |
| T002 | Identify/prepare production-shaped fixture scenarios per emission site | WP01 | |
| T003 | Author byte_contracts.json — 12 compact cases | WP01 | |
| T004 | Add status indent=2 byte case | WP01 | |
| T005 | Write test_tasks_json_bytes.py (byte equality) | WP01 | |
| T006 | Land LOC ceiling gate @4569 + self-mutation proof | WP01 | [P] |
| T007 | Enumerate definitive shared-helper move-set | WP02 | |
| T008 | Create tasks_shared.py with lazy `_tasks.<attr>` routing | WP02 | |
| T009 | tasks.py module bindings for every moved symbol | WP02 | |
| T010 | Seam interception tests for top patched symbols | WP02 | |
| T011 | mypy strict folds in test_tasks.py (attr-defined + redundant cast) | WP02 | |
| T012 | Parity guard + LOC ceiling ratchet | WP02 | |
| T013 | Create tasks_command_adapters.py (3 coord routers, no-cycle proof) | WP03 | |
| T014 | tasks.py bindings + adapter seam checklist | WP03 | |
| T015 | Parity guard + coord harness + ceiling ratchet | WP03 | |
| T016 | RealRender constructor indent param | WP04 | |
| T017 | Delete _StatusRender; status ports use RealRender(indent=2) | WP04 | |
| T018 | Route the 3 shared-helper emission sites through Render | WP04 | |
| T019 | Route the remaining 9 compact sites through Render | WP04 | |
| T020 | Parity guard (13/13 byte-freeze) + ceiling ratchet | WP04 | |
| T021 | #2306 pre-fix: inventory.md 1325→1326 | WP05 | |
| T022 | Create tasks_move_task.py (full family move-set) | WP05 | |
| T023 | Thin move_task wrapper; update inventory.md row to new location | WP05 | |
| T024 | Ratchet re-point: move_task → relocated function (FR-012) | WP05 | |
| T025 | Seam checklist + interception checks; coord skip-arm case (harness label T004) green | WP05 | |
| T026 | Parity guard + targeted surface + ceiling ratchet | WP05 | |
| T027 | Create tasks_map_requirements.py (full family move-set) | WP06 | |
| T028 | Thin map-requirements wrapper + bindings | WP06 | |
| T029 | Ratchet re-point: map_requirements (FR-012); coord refuse-arm case (harness label T005) green | WP06 | |
| T030 | Parity guard + seam checklist + ceiling ratchet | WP06 | |
| T031 | Create tasks_status_cmd.py (full family move-set) | WP07 | |
| T032 | Thin status wrapper + bindings | WP07 | |
| T033 | Ratchet re-point: status (FR-012) | WP07 | |
| T034 | Parity guard (incl. indent byte case) + ceiling ratchet | WP07 | |
| T035 | Create tasks_mark_status.py (full family move-set) | WP08 | |
| T036 | Create tasks_finalize.py (full family move-set) | WP08 | |
| T037 | Thin both wrappers + bindings; coord refuse-arm case green (mark_status) | WP08 | |
| T038 | Parity guard + seam checklists + ceiling ratchet | WP08 | |
| T039 | Final tasks.py registration-shim sweep | WP09 | |
| T040 | AST 0-inline-dumps gate (all evasion forms + theater tests) | WP09 | |
| T041 | tasks_ports.py shim disposition (FR-008) | WP09 | |
| T042 | Final LOC ceiling = min(achieved, 1400) + delta rationale | WP09 | |
| T043 | Full parity + arch gates + tracer close-out appends | WP09 | |
| T044 | Marker-census artifact for the tasks-domain glob | WP10 | |
| T045 | Baseline-growth assertion (no tasks-domain path in orphan baseline) | WP10 | |
| T046 | Draft final #2034 refresh comment + issue-matrix verdict updates | WP10 | |

## Phase 1 — Foundation (parity floor)

### WP01 — Parity floor: byte-freeze suite + LOC ceiling gate

**Goal**: Pin the exact bytes of all 13 JSON emission sites and land the LOC ceiling gate at 4569, BEFORE anything moves. **Priority**: P1 (blocks everything). **Prompt**: [tasks/WP01-parity-floor-byte-freeze.md](tasks/WP01-parity-floor-byte-freeze.md) (~330 lines)
**Independent test**: byte-freeze suite green against the untouched tree; LOC gate red on a synthetic over-ceiling source.
**Dependencies**: none.

- [x] T001 Pin venv to uv.lock; verify typer version (WP01)
- [x] T002 Identify/prepare production-shaped fixture scenarios per emission site (WP01)
- [x] T003 Author byte_contracts.json — 12 compact cases (WP01)
- [x] T004 Add status indent=2 byte case (WP01)
- [x] T005 Write test_tasks_json_bytes.py (WP01)
- [x] T006 Land LOC ceiling gate @4569 + self-mutation proof (WP01)

## Phase 2 — Foundations (seam bridge + adapters + render seam)

### WP02 — Shared-helpers module + seam bridge

**Goal**: `tasks_shared.py` houses the ~30 cross-family helpers with interception-preserving `_tasks.<attr>` routing; establishes the pattern every family move copies. **Priority**: P1. **Prompt**: [tasks/WP02-shared-helpers-seam-bridge.md](tasks/WP02-shared-helpers-seam-bridge.md) (~360 lines)
**Independent test**: parity guard green; interception tests prove patches still bite; mypy strict clean on src+tests together.
**Dependencies**: WP01.

- [x] T007 Enumerate definitive shared-helper move-set (WP02)
- [x] T008 Create tasks_shared.py with lazy routing (WP02)
- [x] T009 tasks.py module bindings (WP02)
- [x] T010 Seam interception tests (WP02)
- [x] T011 mypy strict folds in test_tasks.py (WP02)
- [x] T012 Parity guard + ceiling ratchet (WP02)

### WP03 — Adapters module

**Goal**: The 3 coord-router adapter classes move to `tasks_command_adapters.py` (cycle-break). **Priority**: P1. **Prompt**: [tasks/WP03-command-adapters-module.md](tasks/WP03-command-adapters-module.md) (~220 lines)
**Independent test**: coord harness green; no import cycle (module imports cleanly in isolation).
**Dependencies**: WP02.

- [x] T013 Create tasks_command_adapters.py (WP03)
- [x] T014 tasks.py bindings + adapter seam checklist (WP03)
- [x] T015 Parity guard + coord harness + ceiling ratchet (WP03)

### WP04 — Render seam unification

**Goal**: One Render authority: `RealRender` gains constructor `indent`; `_StatusRender` deleted; all 12 compact sites route through the port. **Priority**: P1 (must precede the status-family move). **Prompt**: [tasks/WP04-render-seam-unification.md](tasks/WP04-render-seam-unification.md) (~340 lines)
**Independent test**: 13/13 byte-freeze cases green through the swap; `_StatusRender` gone.
**Dependencies**: WP03.

- [x] T016 RealRender constructor indent param (WP04)
- [x] T017 Delete _StatusRender (WP04)
- [x] T018 Route the 3 shared-helper emission sites (WP04)
- [x] T019 Route the remaining 9 compact sites (WP04)
- [x] T020 Parity guard + ceiling ratchet (WP04)

## Phase 3 — Family relocations (one family per WP, ratchet re-point in the same WP)

### WP05 — move_task family relocation (+ #2306 fold)

**Goal**: Largest family (orchestrator + 23 `_mt_*` + State + factory) to `tasks_move_task.py`; carries the C-001 divergence wiring and the #2306 inventory fold. **Priority**: P1. **Prompt**: [tasks/WP05-move-task-family.md](tasks/WP05-move-task-family.md) (~380 lines)
**Independent test**: coord-harness skip-arm case (harness label T004: skip-exit-0 + wrong-leg detector) green; inventory gate green; parity green.
**Dependencies**: WP04.

- [x] T021 #2306 pre-fix: inventory.md 1325→1326 (WP05)
- [x] T022 Create tasks_move_task.py (WP05)
- [x] T023 Thin wrapper; update inventory.md row (WP05)
- [x] T024 Ratchet re-point: move_task (WP05)
- [x] T025 Seam checklist + interception; coord skip-arm case green (WP05)
- [x] T026 Parity guard + targeted surface + ceiling ratchet (WP05)

### WP06 — map_requirements family relocation

**Goal**: `_do_map_requirements` + 11 `_mr_*` + State + factory to `tasks_map_requirements.py`. **Priority**: P2. **Prompt**: [tasks/WP06-map-requirements-family.md](tasks/WP06-map-requirements-family.md) (~280 lines)
**Independent test**: coord-harness refuse-arm case (harness label T005: refuse-exit-1) green; parity green.
**Dependencies**: WP05.

- [x] T027 Create tasks_map_requirements.py (WP06)
- [x] T028 Thin wrapper + bindings (WP06)
- [x] T029 Ratchet re-point + coord refuse-arm case green (WP06)
- [x] T030 Parity guard + seam checklist + ceiling ratchet (WP06)

### WP07 — status family relocation

**Goal**: `_do_status` + 14 `_st_*` + State + factory to `tasks_status_cmd.py` (after the render seam collapsed `_StatusRender`). **Priority**: P2. **Prompt**: [tasks/WP07-status-family.md](tasks/WP07-status-family.md) (~270 lines)
**Independent test**: status byte case (indent=2) green; ratchet re-pointed; parity green.
**Dependencies**: WP06.

- [x] T031 Create tasks_status_cmd.py (WP07)
- [x] T032 Thin wrapper + bindings (WP07)
- [x] T033 Ratchet re-point: status (WP07)
- [x] T034 Parity guard + ceiling ratchet (WP07)

### WP08 — mark_status + finalize families relocation

**Goal**: The two remaining families to `tasks_mark_status.py` + `tasks_finalize.py`. **Priority**: P2. **Prompt**: [tasks/WP08-mark-status-finalize-families.md](tasks/WP08-mark-status-finalize-families.md) (~300 lines)
**Independent test**: coord refuse-arm case green for mark_status; parity green.
**Dependencies**: WP07.

- [x] T035 Create tasks_mark_status.py (WP08)
- [x] T036 Create tasks_finalize.py (WP08)
- [x] T037 Thin both wrappers + bindings (WP08)
- [x] T038 Parity guard + seam checklists + ceiling ratchet (WP08)

## Phase 4 — Closure

### WP09 — Registration-shim finalization + AST gate + shim disposition

**Goal**: Final `tasks.py` shape; AST 0-inline-dumps gate (all evasion forms); `tasks_ports.py` disposition; final ceiling `min(achieved, 1400)`. **Priority**: P1. **Prompt**: [tasks/WP09-shim-finalization-gates.md](tasks/WP09-shim-finalization-gates.md) (~350 lines)
**Independent test**: both gates green AND each red on synthetic violations; final LOC recorded with delta rationale.
**Dependencies**: WP08.

- [x] T039 Final tasks.py registration-shim sweep (WP09)
- [x] T040 AST 0-inline-dumps gate + theater tests (WP09)
- [x] T041 tasks_ports.py shim disposition (WP09)
- [x] T042 Final LOC ceiling + delta rationale (WP09)
- [x] T043 Full parity + arch gates + tracer close-out (WP09)

### WP10 — Boyscout: marker census + #2034 refresh

**Goal**: Committed census artifact (file → selecting gate, zero unselected) over the tasks-domain glob incl. all mission-added files; baseline-growth assertion; #2034 final refresh draft. **Priority**: P3. **Prompt**: [tasks/WP10-marker-census-boyscout.md](tasks/WP10-marker-census-boyscout.md) (~230 lines)
**Independent test**: census artifact lists every glob-matching file with its gate; orphan baseline contains no tasks-domain path.
**Dependencies**: WP09.

- [x] T044 Marker-census artifact (WP10)
- [x] T045 Baseline-growth assertion (WP10)
- [x] T046 Draft final #2034 comment + issue-matrix verdicts (WP10)

## Dependency graph (linear — shared-surface refactor)

```
WP01 → WP02 → WP03 → WP04 → WP05 → WP06 → WP07 → WP08 → WP09 → WP10
```

**Parallel opportunities**: intentionally none across WPs (every relocation edits
`tasks.py` and ratchets the same gate file — parallel lanes would collide). Within-WP
subtasks marked [P] can interleave. The mission trades parallelism for zero-conflict
certainty on a 4569-LOC god-file.

## MVP scope

WP01 alone delivers standing value (the byte-level parity contract + the anti-regrowth
ceiling); WP01–WP04 deliver the complete Stream A (render-seam unification) even if the
relocations were paused.
