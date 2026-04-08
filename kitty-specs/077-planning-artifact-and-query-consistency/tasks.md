# Work Packages: Planning Artifact and Query Consistency

**Mission**: 077-planning-artifact-and-query-consistency
**Date**: 2026-04-08
**Target branch**: main
**Total**: 28 subtasks across 5 work packages
**Prerequisites**: `kitty-specs/077-planning-artifact-and-query-consistency/spec.md`, `kitty-specs/077-planning-artifact-and-query-consistency/plan.md`, `kitty-specs/077-planning-artifact-and-query-consistency/research.md`, `kitty-specs/077-planning-artifact-and-query-consistency/data-model.md`, `kitty-specs/077-planning-artifact-and-query-consistency/quickstart.md`, `kitty-specs/077-planning-artifact-and-query-consistency/contracts/`

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Create a mission-scoped normalized WP metadata loader and cache in `src/specify_cli/workspace_context.py` | WP01 | | [D] |
| T002 | Infer missing `execution_mode` once per mission/session and record `mode_source` diagnostics | WP01 | | [D] |
| T003 | Expand `ResolvedWorkspace` and `resolve_workspace_for_wp()` for repo-root planning resolution | WP01 | | [D] |
| T004 | Emit one actionable compatibility error when legacy normalization cannot classify a WP | WP01 | | [D] |
| T005 | Unit tests for normalization, repo-root resolution, and repeated deterministic lookup | WP01 | [D] |
| T006 | Replace lane-only validation in `src/specify_cli/cli/commands/implement.py` with execution-mode-aware validation | WP02 | |
| T007 | Update `src/specify_cli/lanes/implement_support.py` to branch between lane worktree and repo-root planning execution | WP02 | |
| T008 | Update `src/specify_cli/core/execution_context.py` and `src/specify_cli/next/prompt_builder.py` for nullable lane/branch metadata | WP02 | |
| T009 | Update `src/specify_cli/cli/commands/agent/workflow.py` to surface repo-root planning work cleanly | WP02 | |
| T010 | Update `src/specify_cli/core/worktree_topology.py` to represent repo-root planning entries in mixed missions | WP02 | |
| T011 | Tests for implement, workflow, and topology behavior in mixed missions | WP02 | [P] |
| T012 | Refactor `src/specify_cli/core/stale_detection.py` to emit a structured stale payload with workspace kind | WP03 | |
| T013 | Mark repo-root planning work as `stale.status = not_applicable` with the canonical reason code | WP03 | |
| T014 | Preserve deprecated flat stale fields in `spec-kitty agent tasks status --json` during the transition window | WP03 | |
| T015 | Update human-readable task status output for repo-root planning work and stale `n/a` display | WP03 | |
| T016 | Bypass merge-ancestry gating for planning-artifact `--to done` while preserving code-change enforcement | WP03 | |
| T017 | Tests for stale JSON compatibility and planning-artifact approved/done transitions | WP03 | [P] |
| T018 | Make `--agent` optional in query mode and required only for advancing and answer flows | WP04 | | [D] |
| T019 | Extend `Decision` and `to_dict()` with nullable `agent` and `preview_step` | WP04 | | [D] |
| T020 | Implement fresh-run query resolution with `not_started` and `preview_step` in `runtime_bridge.py` | WP04 | | [D] |
| T021 | Fail query mode clearly when a mission has no issuable first step | WP04 | | [D] |
| T022 | Update human-readable query output to show `not_started` and the next step without `unknown` fallback | WP04 | | [D] |
| T023 | Tests for non-mutating query mode, compatibility `--agent`, `preview_step`, and advancing regression | WP04 | [D] |
| T024 | Update `docs/index.md` and `docs/reference/cli-commands.md` to the canonical query/runtime contract | WP05 | |
| T025 | Update `docs/explanation/runtime-loop.md` and `docs/reference/agent-subcommands.md` for resolver distinction and query/advance split | WP05 | |
| T026 | Add explicit compatibility notes for stale flat-field transition and fresh-run `unknown` removal | WP05 | |
| T027 | Sweep active docs for contradictory lane-membership and query-mode wording | WP05 | [P] |
| T028 | Validate examples against current CLI help and the final implemented contract | WP05 | [P] |

---

## Execution Order and Dependencies

```text
WP01 (resolver + normalization) ---------------- unlocks WP02 and WP03
WP04 (query contract) -------------------------- independent, can run in parallel
WP02 (implement/workflow/topology) ------------- depends on WP01
WP03 (status/stale/done transitions) ----------- depends on WP01
WP05 (docs, planning-artifact dogfood) --------- depends on WP01, WP02, WP03, WP04
```

Recommended start: WP01 and WP04 in parallel. WP05 intentionally stays last because it documents the final public contract and dogfoods the new planning-artifact runtime surface after the code paths are fixed.

---

## Work Packages

### WP01: Session Normalization and Canonical Workspace Resolution

**File**: [tasks/WP01-session-normalization-canonical-workspace.md](tasks/WP01-session-normalization-canonical-workspace.md)
**Priority**: P0
**Dependencies**: None
**Estimated prompt size**: ~360 lines
**Independent Test**: A mixed mission containing a historical WP with missing `execution_mode` and a planning-artifact WP resolves deterministically: code-change WPs still map to their lane worktree, planning-artifact WPs map to repository root, and unresolved legacy WPs fail once with a compatibility error instead of drifting by caller.
**Requirement Refs**: FR-001, FR-002, FR-002a, FR-003, FR-004, FR-006, FR-019
**Prompt**: `tasks/WP01-session-normalization-canonical-workspace.md`

#### Included Subtasks

- [x] T001 Create a mission-scoped normalized WP metadata loader and cache in `src/specify_cli/workspace_context.py` (WP01)
- [x] T002 Infer missing `execution_mode` once per mission/session and record `mode_source` diagnostics (WP01)
- [x] T003 Expand `ResolvedWorkspace` and `resolve_workspace_for_wp()` for repo-root planning resolution (WP01)
- [x] T004 Emit one actionable compatibility error when legacy normalization cannot classify a WP (WP01)
- [x] T005 [P] Unit tests for normalization, repo-root resolution, and repeated deterministic lookup (WP01)

#### Implementation Sketch

- Add one internal normalization seam in `src/specify_cli/workspace_context.py` and make every downstream caller consume normalized metadata through it.
- Reuse `src/specify_cli/ownership/inference.py` instead of inventing new heuristics.
- Extend `ResolvedWorkspace` so it can represent both lane worktrees and repository-root planning work with nullable branch and lane metadata.
- Keep all normalization read-only; no disk writes for inferred compatibility values.

#### Parallel Opportunities

- T005 can be written once T001-T004 stabilize the public helper/API shape.

#### Risks

- `ResolvedWorkspace` type changes will fan out to callers that assume `branch_name` and `lane_id` are always non-null.
- Compatibility errors must be emitted once and clearly, not re-raised differently by every caller.

---

### WP02: Implement, Workflow, and Topology Integration

**File**: [tasks/WP02-implement-workflow-topology-integration.md](tasks/WP02-implement-workflow-topology-integration.md)
**Priority**: P0
**Dependencies**: WP01
**Estimated prompt size**: ~440 lines
**Independent Test**: `spec-kitty agent action implement <planning-artifact-wp>` starts without a lane-membership failure, workflow prompts show the repository-root workspace clearly, and mixed-mission topology rendering no longer disappears when a planning-artifact WP is present.
**Requirement Refs**: FR-006, FR-008, FR-010, FR-019
**Prompt**: `tasks/WP02-implement-workflow-topology-integration.md`

#### Included Subtasks

- [ ] T006 Replace lane-only validation in `src/specify_cli/cli/commands/implement.py` with execution-mode-aware validation (WP02)
- [ ] T007 Update `src/specify_cli/lanes/implement_support.py` to branch between lane worktree and repo-root planning execution (WP02)
- [ ] T008 Update `src/specify_cli/core/execution_context.py` and `src/specify_cli/next/prompt_builder.py` for nullable lane/branch metadata (WP02)
- [ ] T009 Update `src/specify_cli/cli/commands/agent/workflow.py` to surface repo-root planning work cleanly (WP02)
- [ ] T010 Update `src/specify_cli/core/worktree_topology.py` to represent repo-root planning entries in mixed missions (WP02)
- [ ] T011 [P] Tests for implement, workflow, and topology behavior in mixed missions (WP02)

#### Implementation Sketch

- Remove the assumption that `lanes.json` membership is the universal admission ticket for execution.
- Keep lane worktree allocation unchanged for `code_change` WPs.
- Route planning-artifact WPs through the canonical resolver and represent them as explicit repository-root entries in topology output.
- Ensure informational topology remains informative instead of failing closed behind a broad exception.

#### Parallel Opportunities

- T011 can begin once T006-T010 establish the final caller contract and output shapes.

#### Risks

- `implement.py`, `implement_support.py`, and `workflow.py` have independent call chains that can drift unless they share the exact same resolver output.
- `worktree_topology.py` currently assumes every WP has lane and branch metadata; keep the new nullability local and explicit.

---

### WP03: Status, Stale, and Done Transition Cleanup

**File**: [tasks/WP03-status-stale-and-done-transition-cleanup.md](tasks/WP03-status-stale-and-done-transition-cleanup.md)
**Priority**: P0
**Dependencies**: WP01
**Estimated prompt size**: ~470 lines
**Independent Test**: A planning-artifact WP in progress shows `stale.status = not_applicable` plus the deprecated flat fields in JSON, human-readable output says `stale: n/a (repo-root planning work)`, and `spec-kitty agent tasks move-task <wp-id> --to done` succeeds without merge ancestry while a code-change WP still requires merge ancestry or an override.
**Requirement Refs**: FR-005, FR-007, FR-008a, FR-009, FR-019
**Prompt**: `tasks/WP03-status-stale-and-done-transition-cleanup.md`

#### Included Subtasks

- [ ] T012 Refactor `src/specify_cli/core/stale_detection.py` to emit a structured stale payload with workspace kind (WP03)
- [ ] T013 Mark repo-root planning work as `stale.status = not_applicable` with the canonical reason code (WP03)
- [ ] T014 Preserve deprecated flat stale fields in `spec-kitty agent tasks status --json` during the transition window (WP03)
- [ ] T015 Update human-readable task status output for repo-root planning work and stale `n/a` display (WP03)
- [ ] T016 Bypass merge-ancestry gating for planning-artifact `--to done` while preserving code-change enforcement (WP03)
- [ ] T017 [P] Tests for stale JSON compatibility and planning-artifact approved/done transitions (WP03)

#### Implementation Sketch

- Make nested `stale` the canonical machine contract.
- Derive deprecated flat fields from the nested object instead of maintaining two independent logic paths.
- Keep stale detection explicitly `not_applicable` for repository-root planning work.
- Keep the existing `done` ancestry guard for `code_change`, but short-circuit it for planning-artifact WPs per the lifecycle contract.

#### Parallel Opportunities

- T017 can be added once T012-T016 settle the output shape and `done` behavior.

#### Risks

- Removing the ancestry guard too broadly would weaken the safety contract for `code_change` WPs.
- JSON compatibility must be explicit; do not accidentally drop `is_stale`, `minutes_since_commit`, or `worktree_exists` during the same change.

---

### WP04: Query Mode Runtime Bridge Cleanup

**File**: [tasks/WP04-query-mode-runtime-bridge-cleanup.md](tasks/WP04-query-mode-runtime-bridge-cleanup.md)
**Priority**: P0
**Dependencies**: None
**Estimated prompt size**: ~410 lines
**Independent Test**: `spec-kitty next --mission-run <slug> --json` on a fresh run returns `mission_state = not_started` plus `preview_step`, does not advance runtime state, and still allows `spec-kitty next --agent <name> --mission-run <slug> --result success` to advance normally.
**Requirement Refs**: FR-011, FR-012, FR-013, FR-014, FR-014a, FR-015, FR-016, FR-019
**Prompt**: `tasks/WP04-query-mode-runtime-bridge-cleanup.md`

#### Included Subtasks

- [ ] T018 Make `--agent` optional in query mode and required only for advancing and answer flows (WP04)
- [ ] T019 Extend `Decision` and `to_dict()` with nullable `agent` and `preview_step` (WP04)
- [ ] T020 Implement fresh-run query resolution with `not_started` and `preview_step` in `runtime_bridge.py` (WP04)
- [ ] T021 Fail query mode clearly when a mission has no issuable first step (WP04)
- [ ] T022 Update human-readable query output to show `not_started` and the next step without `unknown` fallback (WP04)
- [ ] T023 [P] Tests for non-mutating query mode, compatibility `--agent`, `preview_step`, and advancing regression (WP04)

#### Implementation Sketch

- Split query-mode CLI validation from advancing-mode validation.
- Extend the decision contract once, then reuse it in JSON and human rendering.
- Make fresh-run query state explicit and actionable, not implicit in `unknown`.
- Fail fast when the mission definition itself has no issuable first step instead of fabricating an empty query result.

#### Parallel Opportunities

- T023 can be added once T018-T022 settle the contract and human-readable output.

#### Risks

- `runtime_bridge.py` currently depends on private runtime snapshot helpers; keep the new error path explicit and easy to debug.
- Nullable `agent` will require careful typing updates in any code that assumes query and advancing payloads have the same identity semantics.

---

### WP05: Documentation and Compatibility Updates

**File**: [tasks/WP05-documentation-and-compatibility-updates.md](tasks/WP05-documentation-and-compatibility-updates.md)
**Priority**: P1
**Dependencies**: WP01, WP02, WP03, WP04
**Estimated prompt size**: ~300 lines
**Independent Test**: Active docs consistently teach `spec-kitty next --mission-run <slug>` for query mode, explain `not_started + preview_step`, describe planning-artifact work as repository-root execution outside the lane graph, and this docs-only WP itself can be implemented as planning-artifact work after WP01-WP04 land.
**Requirement Refs**: FR-017, FR-018, FR-020
**Prompt**: `tasks/WP05-documentation-and-compatibility-updates.md`

#### Included Subtasks

- [ ] T024 Update `docs/index.md` and `docs/reference/cli-commands.md` to the canonical query/runtime contract (WP05)
- [ ] T025 Update `docs/explanation/runtime-loop.md` and `docs/reference/agent-subcommands.md` for resolver distinction and query/advance split (WP05)
- [ ] T026 Add explicit compatibility notes for stale flat-field transition and fresh-run `unknown` removal (WP05)
- [ ] T027 [P] Sweep active docs for contradictory lane-membership and query-mode wording (WP05)
- [ ] T028 [P] Validate examples against current CLI help and the final implemented contract (WP05)

#### Implementation Sketch

- Update the high-traffic docs first (`docs/index.md`, `docs/reference/cli-commands.md`).
- Then update deeper reference surfaces (`docs/explanation/runtime-loop.md`, `docs/reference/agent-subcommands.md`).
- Add explicit compatibility notes so machine consumers understand the nested stale object transition and the fresh-run query JSON change.
- End with a validation sweep against current help output and the landed code paths.

#### Parallel Opportunities

- T027 and T028 can run after the main doc edits are drafted.

#### Risks

- This WP is intentionally `planning_artifact` and therefore depends on the earlier runtime fixes being in place; do not start it early.
- Docs can easily drift if examples are updated before the runtime contract lands; keep this WP last.
