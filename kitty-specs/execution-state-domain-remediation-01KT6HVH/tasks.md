# Tasks: Execution-State Domain Remediation — #1619 Strangler Fig

**Mission**: execution-state-domain-remediation-01KT6HVH  
**Mission ID**: 01KT6HVH3QND4Q3KCGH2419N4J  
**Branch**: `main` → `main`  
**Generated**: 2026-06-03

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Author ADR 1: four-bounded-module domain model + status ownership | WP01 | — |
| T002 | Author ADR 2: ExecutionContext OHS + CommitTarget atomicity | WP01 | [P] with T001 |
| T003 | Author ADR 3: Effector/Actor model (docs-only decision) | WP01 | [P] with T001 |
| T004 | Add/update glossary entries (GovernanceContext, ExecutionContext, InfraContext, Effector, communication-artefact) | WP01 | [P] with T001 |
| T005 | Commit all three ADRs + glossary to main and verify CI | WP01 | — |
| T006 | Create e2e ratchet test fixture (tmp repo + mission + 2 WPs) | WP02 | — |
| T007 | Implement main-CWD command sequence invocations (subprocess with cwd=main) | WP02 | — |
| T008 | Implement lane-CWD command sequence invocations (subprocess with cwd=worktree) | WP02 | [P] with T007 |
| T009 | Add parity assertions (WP identity, lane state, status JSON equality) | WP02 | — |
| T010 | Register test in CI path filter for execution-context paths | WP02 | — |
| T011 | Create tests/architectural/test_status_module_boundary.py with pytestarch rule | WP03 | — |
| T012 | Add AST scanner pass to catch direct status.* submodule imports | WP03 | — |
| T013 | Add injection proof test (synthetic bypass import in tmp file, assert scanner catches it) | WP03 | — |
| T014 | Run grep audit to enumerate all bypass imports outside status/ | WP03 | — |
| T015 | Fix all bypass imports in non-status, non-owned source files | WP03 | [P] within T015 |
| T016 | Verify coordination/status_transition.py is exempt from boundary rule | WP03 | — |
| T017 | Confirm boundary test passes and CI is green | WP03 | — |
| T018 | Create src/specify_cli/status/aggregate.py with ActiveWPStatus dataclass | WP04 | — |
| T019 | Implement MissionStatus dataclass with topology field and load() classmethod | WP04 | — |
| T020 | Implement MissionStatus.claim() using coord-aware read path | WP04 | — |
| T021 | Implement MissionStatus.transition() calling BookkeepingTransaction internally | WP04 | — |
| T022 | Implement MissionStatus.save() returning CommitReceipt | WP04 | — |
| T023 | Export MissionStatus and ActiveWPStatus in status/__init__.py __all__ | WP04 | — |
| T024 | Migrate cli/commands/agent/status.py to MissionStatus.load() + .claim() | WP04 | — |
| T025 | Write unit tests for MissionStatus (load, claim, topology, fail-closed) | WP04 | [P] with T018–T022 |
| T026 | Add optional mission_id and mission_slug to MissionRunSnapshot in schema.py | WP05 | — |
| T027 | Add optional mission_id and mission_slug to MissionRunRef in engine.py | WP05 | — |
| T028 | Plumb mission_id/_resolve_mission_ulid and mission_slug through start_mission_run | WP05 | — |
| T029 | Update all 6 in-engine snapshot-copy sites to carry new fields | WP05 | — |
| T030 | Remove dead write-only inputs["mission_slug"] at engine.py:216 | WP05 | — |
| T031 | Verify backward-compat: test existing state.json loads with None defaults | WP05 | — |
| T032 | Re-run grep investigation to find remaining hardcoded path constructions | WP06 | — |
| T033 | Update feature-runs.json write in runtime_bridge.py to include mission_id + mission_slug | WP06 | — |
| T034 | Route runtime_bridge query-mode through resolve_action_context | WP06 | — |
| T035 | Route workflow.py fix-mode through resolve_action_context | WP06 | [P] with T034 |
| T036 | Delete all unreachable path-builder helper functions | WP06 | — |
| T037 | Verify e2e ratchet still green after all ExecutionContext changes | WP06 | — |

---

## Work Packages

### WP01 — ADRs + Glossary (Gate)

**Goal**: Author and merge three architecture decision records and five glossary entries before any implementation code lands (DIRECTIVE_032, C-001).  
**Priority**: Critical — gates all other WPs  
**Execution mode**: planning_artifact  
**Prompt**: [tasks/WP01-adrs-and-glossary.md](tasks/WP01-adrs-and-glossary.md)  
**Estimated size**: ~250 lines  
**Dependencies**: none

**Subtasks**:
- [x] T001 Author ADR 1: four-bounded-module domain model + status ownership (WP01)
- [x] T002 Author ADR 2: ExecutionContext OHS + CommitTarget atomicity (WP01)
- [x] T003 Author ADR 3: Effector/Actor model (WP01)
- [x] T004 Add/update glossary entries (WP01)
- [x] T005 Commit ADRs + glossary and verify CI (WP01)

**Success criteria**: Three ADR files exist at `architecture/3.x/adr/2026-06-03-*.md` and are merged to `main`. Glossary entries for all five terms updated. CI green.

---

### WP02 — e2e Parity Ratchet (Step 1)

**Goal**: Build the CWD-invariance test that proves `next → implement → move-task → review → status` produces identical results from main-checkout CWD and lane-worktree CWD. Gates all subsequent Strangler steps.  
**Priority**: Critical — gates WP03, WP04, WP06  
**Execution mode**: code_change  
**Prompt**: [tasks/WP02-e2e-parity-ratchet.md](tasks/WP02-e2e-parity-ratchet.md)  
**Estimated size**: ~300 lines  
**Dependencies**: WP01

**Subtasks**:
- [ ] T006 Create e2e ratchet test fixture (WP02)
- [ ] T007 Implement main-CWD command sequence invocations (WP02)
- [ ] T008 Implement lane-CWD command sequence invocations (WP02)
- [ ] T009 Add parity assertions (WP02)
- [ ] T010 Register test in CI path filter (WP02)

**Success criteria**: `tests/architectural/test_execution_context_parity.py` exists, passes locally, and is registered in CI. Test fails if a surface re-derives context independently.

---

### WP03 — status/ Boundary Enforcement (Step 2a)

**Goal**: Create an architectural boundary test that enforces the `status/` module facade and fix all ~245 bypass imports in non-status, non-runtime files.  
**Priority**: High  
**Execution mode**: code_change  
**Prompt**: [tasks/WP03-status-boundary-enforcement.md](tasks/WP03-status-boundary-enforcement.md)  
**Estimated size**: ~400 lines  
**Dependencies**: WP02

**Subtasks**:
- [ ] T011 Create test_status_module_boundary.py with pytestarch rule (WP03)
- [ ] T012 Add AST scanner pass (WP03)
- [ ] T013 Add injection proof test (WP03)
- [ ] T014 Run grep audit — enumerate all bypass imports (WP03)
- [ ] T015 Fix all bypass imports in non-status, non-owned files (WP03)
- [ ] T016 Verify coordination/status_transition.py exemption (WP03)
- [ ] T017 Confirm boundary test passes and CI green (WP03)

**Success criteria**: `test_status_module_boundary.py` passes. `grep -r "from specify_cli.status\." src/ --include="*.py"` (outside `status/`) returns zero hits (excluding exempt files).

---

### WP04 — MissionStatus Aggregate (Step 2b)

**Goal**: Introduce `MissionStatus` as the authoritative read/write owner of mission WP lane state. Migrate `agent/status.py` away from raw path construction.  
**Priority**: High — also needed by WP06  
**Execution mode**: code_change  
**Prompt**: [tasks/WP04-mission-status-aggregate.md](tasks/WP04-mission-status-aggregate.md)  
**Estimated size**: ~450 lines  
**Dependencies**: WP02

**Subtasks**:
- [x] T018 Create aggregate.py with ActiveWPStatus dataclass (WP04)
- [x] T019 Implement MissionStatus.load() with topology resolution + fail-closed (WP04)
- [x] T020 Implement MissionStatus.claim() using coord-aware read path (WP04)
- [x] T021 Implement MissionStatus.transition() calling BookkeepingTransaction internally (WP04)
- [x] T022 Implement MissionStatus.save() returning CommitReceipt (WP04)
- [x] T023 Export MissionStatus + ActiveWPStatus in status/__init__.py (WP04)
- [x] T024 Migrate agent/status.py to MissionStatus.load() + .claim() (WP04)
- [x] T025 Write unit tests for MissionStatus (WP04)

**Success criteria**: `MissionStatus` and `ActiveWPStatus` exist in `status/__init__.py` exports. `agent/status.py` contains no raw `main_repo_root / "kitty-specs"` path construction. Coord-topology missions fail closed when coord unavailable. e2e ratchet (WP02) stays green.

---

### WP05 — MissionRun → Mission Back-Reference (Step 2c)

**Goal**: Add optional `mission_id` and `mission_slug` to `MissionRunSnapshot` and `MissionRunRef` so a run can name its concrete mission without an external index scan.  
**Priority**: Medium (parallelizable with WP03/WP04)  
**Execution mode**: code_change  
**Prompt**: [tasks/WP05-missionrun-back-reference.md](tasks/WP05-missionrun-back-reference.md)  
**Estimated size**: ~350 lines  
**Dependencies**: WP01

**Subtasks**:
- [x] T026 Add optional mission_id + mission_slug to MissionRunSnapshot (WP05)
- [x] T027 Add optional mission_id + mission_slug to MissionRunRef (WP05)
- [x] T028 Plumb mission_id + mission_slug through start_mission_run (WP05)
- [x] T029 Update all 6 in-engine snapshot-copy sites (WP05)
- [x] T030 Remove dead inputs["mission_slug"] at engine.py:216 (WP05)
- [x] T031 Verify backward-compat: existing state.json loads without error (WP05)

**Success criteria**: `MissionRunSnapshot.mission_id` and `mission_slug` populated for new runs. Existing on-disk `state.json` files load with `None` defaults. Pydantic round-trip test passes.

---

### WP06 — ExecutionContext Hardening (Step 3)

**Goal**: Route all residue path-building surfaces through `resolve_action_context`, update `feature-runs.json` to carry mission identity, and delete unreachable path-builder helpers.  
**Priority**: High  
**Execution mode**: code_change  
**Prompt**: [tasks/WP06-executioncontext-hardening.md](tasks/WP06-executioncontext-hardening.md)  
**Estimated size**: ~350 lines  
**Dependencies**: WP02, WP04, WP05

**Subtasks**:
- [ ] T032 Re-run grep investigation for remaining hardcoded paths (WP06)
- [ ] T033 Update feature-runs.json write in runtime_bridge.py (mission_id + mission_slug) (WP06)
- [ ] T034 Route runtime_bridge query-mode through resolve_action_context (WP06)
- [ ] T035 Route workflow.py fix-mode through resolve_action_context (WP06)
- [ ] T036 Delete unreachable path-builder helpers (WP06)
- [ ] T037 Verify e2e ratchet green after all changes (WP06)

**Success criteria**: `grep -rn 'kitty-specs.*mission_slug\|main_repo_root.*kitty\|feature_dir.*slug' src/ --include="*.py" | grep -v 'status/' | grep -v 'core/execution_context'` returns zero hits. e2e ratchet passes. `feature-runs.json` entries include `mission_id` and `mission_slug`.

---

## Parallelization Opportunities

```
WP01 (ADRs) → WP02 (ratchet) → ┌ WP03 (boundary)    ┐
                                 ├ WP04 (aggregate)    ├ → WP06 (hardening)
                                 └ WP05 (back-ref)     ┘
```

WP03, WP04, and WP05 can all run in parallel after WP02 merges. WP06 waits for WP02 + WP04 + WP05 before starting.

## MVP Scope

WP01 + WP02 + WP04 deliver the highest-value outcome: domain model ratified, ratchet green, and `agent/status.py` using the authoritative aggregate. WP03, WP05, and WP06 can follow in a second wave.
