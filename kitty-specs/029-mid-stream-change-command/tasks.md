# Work Packages: Mid-Stream Change Command

**Inputs**: Design documents from `/kitty-specs/029-mid-stream-change-command/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/change-command.openapi.yaml, quickstart.md

**Tests**: Testing is mandatory for this feature. Every work package ends with an explicit testing task, and WP08 runs full integration and typing validation.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently reviewable and keeps runtime behavior deterministic.

**Prompt Files**: Each work package references a matching prompt file in `/tasks/`.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** means the subtask can run in parallel with other marked subtasks in that package.

## Path Conventions
- CLI source: `src/specify_cli/`
- Tests: `tests/unit/`, `tests/integration/`
- Feature docs: `kitty-specs/029-mid-stream-change-command/`

---

## Work Package WP01: Command Surface and Template Foundation (Priority: P0)

**Goal**: Add `/spec-kitty.change` command surfaces and template plumbing so the feature is discoverable and invokable.
**Independent Test**: CLI shows the new command, command templates render for supported agents, and basic command routing smoke tests pass.
**Prompt**: `/tasks/WP01-command-surface-and-template-foundation.md`
**Estimated Prompt Size**: ~360 lines

### Included Subtasks
- [x] T001 Create `src/specify_cli/cli/commands/change.py` with top-level command entrypoints and JSON/human output modes
- [x] T002 Register command in `src/specify_cli/cli/commands/__init__.py` and add agent command wiring in `src/specify_cli/cli/commands/agent/__init__.py`
- [x] T003 Create `src/specify_cli/cli/commands/agent/change.py` with preview/apply/reconcile command stubs
- [x] T004 Add shared command templates at `src/specify_cli/templates/command-templates/change.md` and mission override at `src/specify_cli/missions/software-dev/command-templates/change.md`
- [x] T005 Update command discovery/help references where workflow command lists are enumerated
- [x] T006 Run command registration smoke tests and verify `/spec-kitty.change` appears in rendered command assets

### Implementation Notes
- Keep command style aligned with existing Typer command patterns.
- Maintain both human-readable and `--json` output for agent automation.

### Parallel Opportunities
- T004 and T005 can proceed in parallel after T001 command signature is finalized.

### Dependencies
- None.

### Risks and Mitigations
- Risk: command not discoverable in agent output. Mitigation: verify template rendering and init command output paths.

---

## Work Package WP02: Branch Stash Routing and Request Validation (Priority: P0)

**Goal**: Implement branch-aware stash resolution and strict request validation gates, including ambiguity fail-fast behavior.
**Independent Test**: Main branch routes to embedded main stash, feature branches route to feature stash, and ambiguous requests block before write operations.
**Prompt**: `/tasks/WP02-branch-stash-routing-and-request-validation.md`
**Estimated Prompt Size**: ~420 lines

### Included Subtasks
- [x] T007 Implement stash resolver in `src/specify_cli/core/change_stack.py` for `kitty-specs/change-stack/main/` vs `kitty-specs/<feature>/tasks/`
- [x] T008 Extend feature detection/path helpers in `src/specify_cli/core/feature_detection.py` for embedded main stash scenarios
- [x] T009 Enforce contributor-access and repository-context validation in command preflight
- [x] T010 Implement ambiguity detector and fail-fast error contract before generation (`FR-002A`)
- [x] T011 Implement closed/done target detection and link-only enforcement (`FR-016`)
- [x] T012 Add unit tests for stash resolution, ambiguity blocking, and closed/done safeguards

### Implementation Notes
- Preserve deterministic behavior for all validation outcomes.
- Avoid mutating any WP files when request validation fails.

### Parallel Opportunities
- T008 and T009 are parallel-safe once T007 interface is stable.

### Dependencies
- Depends on WP01.

### Risks and Mitigations
- Risk: false positives in ambiguity detection. Mitigation: include fixture coverage for clear and unclear requests.

---

## Work Package WP03: Deterministic Complexity Scoring and Gating (Priority: P1)

**Goal**: Build deterministic complexity scoring and recommendation gating for `/spec-kitty.specify` handoff decisions.
**Independent Test**: Score breakdown is stable across repeated runs, thresholds map to expected classifications, and continue/stop gating is enforced.
**Prompt**: `/tasks/WP03-deterministic-complexity-scoring-and-gating.md`
**Estimated Prompt Size**: ~330 lines

### Included Subtasks
- [x] T013 Create `src/specify_cli/core/change_classifier.py` implementing fixed weighted rubric and threshold mapping
- [x] T014 Integrate scoring breakdown into preview response and human-readable warning output
- [x] T015 Add explicit continue-or-stop gate in apply flow when classification is `high`
- [x] T016 Persist scoring metadata to change request objects for traceability
- [x] T017 Add unit tests for threshold boundaries, deterministic tie handling, and warning behavior

### Implementation Notes
- No probabilistic or model-based scoring paths are allowed.
- Ensure preview and apply share the same scoring implementation.

### Parallel Opportunities
- T014 and T016 can run in parallel after T013 core classifier is complete.

### Dependencies
- Depends on WP02.

### Risks and Mitigations
- Risk: drift between preview/apply logic. Mitigation: centralize classifier and use shared fixtures.

---

## Work Package WP04: Change WP Synthesis and Adaptive Packaging (Priority: P1) 🎯 MVP

**Goal**: Convert validated requests into single/orchestration/targeted change WPs with required metadata and final testing tasks.
**Independent Test**: Given representative requests, generated WPs follow deterministic mode selection, include required frontmatter, and include final test tasks.
**Prompt**: `/tasks/WP04-change-wp-synthesis-and-adaptive-packaging.md`
**Estimated Prompt Size**: ~470 lines

### Included Subtasks
- [x] T018 Implement deterministic packaging mode selector (`single_wp`, `orchestration`, `targeted_multi`) from coupling/dependency indicators
- [x] T019 Implement WP ID allocation and slugged filename generation in flat `tasks/` directories
- [x] T020 Emit required frontmatter fields (`change_stack`, `change_request_id`, `change_mode`, `stack_rank`, `review_attention`)
- [x] T021 Carry forward guardrails and append mandatory final testing task to each generated change WP (`FR-014`)
- [x] T022 Include correct implementation command hints (`spec-kitty implement WP##` with optional `--base`)
- [x] T023 Add unit tests for packaging mode outputs, deterministic ordering, and metadata completeness

### Implementation Notes
- Generated files must stay in flat `tasks/` directories.
- Keep prompt bodies specific enough for independent implementation by a new engineer.

### Parallel Opportunities
- T019 and T020 can proceed in parallel after mode selection interface in T018 is finalized.

### Dependencies
- Depends on WP03.

### Risks and Mitigations
- Risk: oversized generated prompts. Mitigation: include generation-time size checks and split triggers.

---

## Work Package WP05: Dependency Policy and Closed Reference Linking (Priority: P1)

**Goal**: Enforce dependency integrity while allowing valid change-to-normal dependencies and closed WP historical linking.
**Independent Test**: Dependency graph rejects invalid edges/cycles, accepts allowed change-to-normal dependencies, and keeps closed WPs unchanged.
**Prompt**: `/tasks/WP05-dependency-policy-and-closed-reference-linking.md`
**Estimated Prompt Size**: ~410 lines

### Included Subtasks
- [x] T024 Implement dependency candidate extraction across new change WPs and affected open WPs
- [x] T025 Implement rule allowing change WPs to depend on normal open WPs when ordering requires (`FR-005A`)
- [x] T026 Validate dependency graph using existing core validators (missing refs, self-edge, cycles)
- [x] T027 Implement closed/done WP reference linkage metadata without lane mutation
- [x] T028 Implement blocker output when pending change stack has no ready WP (`FR-017`)
- [x] T029 Add unit tests covering valid and invalid dependency configurations

### Implementation Notes
- Ensure dependencies are represented consistently in `tasks.md` and WP frontmatter.

### Parallel Opportunities
- T027 can run in parallel with T024-T026 after shared models are established.

### Dependencies
- Depends on WP04.

### Risks and Mitigations
- Risk: hidden cycles in mixed dependency graphs. Mitigation: require cycle check before write and fail atomically.

---

## Work Package WP06: Reconciliation and Merge Coordination Jobs (Priority: P1)

**Goal**: Keep planning artifacts consistent after change WP creation and add merge coordination jobs when cross-stream conflict risk is detected.
**Independent Test**: After apply, docs/links are consistent, consistency report is clean, and merge coordination jobs appear only when heuristics trigger.
**Prompt**: `/tasks/WP06-reconciliation-and-merge-coordination-jobs.md`
**Estimated Prompt Size**: ~390 lines

### Included Subtasks
- [x] T030 Implement `tasks.md` reconciliation to include new change WPs and prompt links
- [x] T031 Implement consistency report generation (`updated_tasks_doc`, `broken_links_fixed`, `issues`)
- [x] T032 Implement deterministic merge coordination job heuristics for cross-stream risk
- [x] T033 Persist merge coordination jobs in planning artifacts for downstream implement/review visibility
- [x] T034 Add integration tests for reconciliation outcomes and merge job trigger/no-trigger behavior
- [x] T035 Run package-level regression tests for reconciliation logic

### Implementation Notes
- Reconciliation should be idempotent when rerun with no new changes.

### Parallel Opportunities
- T032 and T034 can run in parallel once T031 consistency report schema is stable.

### Dependencies
- Depends on WP05.

### Risks and Mitigations
- Risk: over-triggering merge jobs. Mitigation: encode explicit heuristics and test both positive and negative cases.

---

## Work Package WP07: Stack-First Implement Selection Integration (Priority: P1)

**Goal**: Integrate stack-first selection into implement workflow and enforce blocker stop behavior.
**Independent Test**: Implement auto-selection chooses ready change WPs first; blocked stacks halt normal progression; normal WPs resume only when stack is empty.
**Prompt**: `/tasks/WP07-stack-first-implement-selection-integration.md`
**Estimated Prompt Size**: ~340 lines

### Included Subtasks
- [x] T036 Update implement auto-selection logic in `src/specify_cli/cli/commands/agent/workflow.py` to prioritize ready change WPs
- [x] T037 Enforce stop-and-report behavior when pending change WPs exist but none are ready
- [x] T038 Add fallback to normal planned WPs only when change stack is empty
- [x] T039 Update workflow guidance/output messages to explain selected source and blockers
- [x] T040 Add integration tests for ready-stack, blocked-stack, and empty-stack scenarios

### Implementation Notes
- Keep output explicit about why a WP was selected or why execution is blocked.

### Parallel Opportunities
- T039 can proceed in parallel with T040 after behavior in T036-T038 stabilizes.

### Dependencies
- Depends on WP05.

### Risks and Mitigations
- Risk: regressions in existing implement auto-detect behavior. Mitigation: add backward-compatible tests for non-change flows.

---

## Work Package WP08: End-to-End Validation and Documentation Hardening (Priority: P2)

**Goal**: Validate complete behavior against success criteria and harden developer documentation for rollout.
**Independent Test**: Full targeted test suite and type checks pass, docs align with implemented behavior, and acceptance scenarios are covered.
**Prompt**: `/tasks/WP08-end-to-end-validation-and-documentation-hardening.md`
**Estimated Prompt Size**: ~300 lines

### Included Subtasks
- [x] T041 Add end-to-end integration scenarios covering main stash routing, feature stash routing, high complexity continue/stop, and ambiguity fail-fast
- [x] T042 Run and stabilize targeted test matrix plus mypy strict checks for touched modules
- [x] T043 Update user and contributor docs for `/spec-kitty.change` behavior, dependency policy, and stack-first semantics
- [x] T044 Validate success criteria mapping (`SC-001` to `SC-005`) and run final encoding/consistency checks

### Implementation Notes
- This package closes gaps between implementation details and published workflow guidance.

### Parallel Opportunities
- T043 can proceed in parallel with T042 once behavior contracts stabilize.

### Dependencies
- Depends on WP06, WP07.

### Risks and Mitigations
- Risk: undocumented behavior drift. Mitigation: cross-check docs directly against integration test assertions.

---

## Dependency and Execution Summary

- **Sequence**: WP01 -> WP02 -> WP03 -> WP04 -> WP05 -> (WP06 and WP07 in parallel) -> WP08.
- **Parallelization**: WP06 and WP07 can run concurrently after WP05; within-package parallel subtasks are called out in each prompt.
- **MVP Scope**: WP01 through WP05 deliver the core `/spec-kitty.change` behavior and deterministic change-WP generation.

```text
WP01 -> WP02 -> WP03 -> WP04 -> WP05 -> +-> WP06 --+
                                           |          |
                                           +-> WP07 --+-> WP08
```

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create top-level change command module | WP01 | P0 | No |
| T002 | Register command routers | WP01 | P0 | No |
| T003 | Add agent change command module | WP01 | P0 | No |
| T004 | Add command templates for change | WP01 | P0 | Yes |
| T005 | Update command discovery/help text | WP01 | P0 | Yes |
| T006 | Run command registration smoke tests | WP01 | P0 | No |
| T007 | Implement stash resolver | WP02 | P0 | No |
| T008 | Extend feature detection helpers | WP02 | P0 | Yes |
| T009 | Enforce contributor/context validation | WP02 | P0 | Yes |
| T010 | Implement ambiguity fail-fast validator | WP02 | P0 | No |
| T011 | Enforce closed/done link-only policy | WP02 | P0 | No |
| T012 | Add stash and validation unit tests | WP02 | P0 | No |
| T013 | Create deterministic complexity classifier | WP03 | P1 | No |
| T014 | Integrate scoring into preview output | WP03 | P1 | Yes |
| T015 | Enforce continue/stop gate | WP03 | P1 | No |
| T016 | Persist scoring metadata | WP03 | P1 | Yes |
| T017 | Add classifier boundary tests | WP03 | P1 | No |
| T018 | Implement adaptive packaging selector | WP04 | P1 | No |
| T019 | Implement WP ID and filename generation | WP04 | P1 | Yes |
| T020 | Emit required change WP frontmatter | WP04 | P1 | Yes |
| T021 | Append guardrails and final testing task | WP04 | P1 | No |
| T022 | Add implementation command hints | WP04 | P1 | No |
| T023 | Add synthesis and ordering unit tests | WP04 | P1 | No |
| T024 | Extract dependency candidates | WP05 | P1 | No |
| T025 | Allow change-to-normal dependencies | WP05 | P1 | No |
| T026 | Validate cycles and invalid refs | WP05 | P1 | No |
| T027 | Add closed reference linkage metadata | WP05 | P1 | Yes |
| T028 | Emit blocker output for no-ready stack | WP05 | P1 | No |
| T029 | Add dependency policy tests | WP05 | P1 | No |
| T030 | Reconcile tasks.md links | WP06 | P1 | No |
| T031 | Generate consistency report output | WP06 | P1 | No |
| T032 | Implement merge coordination heuristics | WP06 | P1 | Yes |
| T033 | Persist merge coordination artifacts | WP06 | P1 | No |
| T034 | Add reconciliation integration tests | WP06 | P1 | Yes |
| T035 | Run WP-level regression tests | WP06 | P1 | No |
| T036 | Prioritize ready change WPs in implement | WP07 | P1 | No |
| T037 | Enforce blocker stop semantics | WP07 | P1 | No |
| T038 | Allow normal fallback only when stack empty | WP07 | P1 | No |
| T039 | Update workflow guidance output | WP07 | P1 | Yes |
| T040 | Add stack selection integration tests | WP07 | P1 | No |
| T041 | Add end-to-end integration scenarios | WP08 | P2 | No |
| T042 | Run and stabilize test matrix + mypy | WP08 | P2 | No |
| T043 | Update documentation and command guidance | WP08 | P2 | Yes |
| T044 | Validate SC coverage and final checks | WP08 | P2 | No |

---

All work packages are sized within 4-6 subtasks (target range 3-7), with no package exceeding 10 subtasks.
