---
work_package_id: WP01
title: Cancellation-Aware Finalization
dependencies: []
requirement_refs:
- C-001
- C-002
- C-003
- C-004
- C-005
- C-006
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- NFR-005
planning_base_branch: fix/exclude-canceled-work-packages-from-lanes
merge_target_branch: fix/exclude-canceled-work-packages-from-lanes
branch_strategy: Planning artifacts for this mission were generated on fix/exclude-canceled-work-packages-from-lanes. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/exclude-canceled-work-packages-from-lanes unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Red-first cancellation-aware finalization
history:
- at: '2026-08-24T07:00:23Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/cli/commands/agent/finalization_eligibility.py
- tests/specify_cli/cli/commands/agent/test_finalization_eligibility.py
- tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/finalization_eligibility.py
- src/specify_cli/cli/commands/agent/mission_finalize.py
- tests/specify_cli/cli/commands/agent/test_finalization_eligibility.py
- tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py
- tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py
role: implementer
tags:
- lane-allocation
- cancellation
- finalization
task_type: implement
tracker_refs:
- '#3432'
---

# Work Package Prompt: WP01 – Cancellation-Aware Finalization

## Do This First: Load the Agent Profile

Use the `/ad-hoc-profile-load` skill to load the frontmatter profile before interpreting implementation details.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Primary language**: Python

Then enter the Spec Kitty workspace using the exact command output, not a reconstructed path:

```bash
spec-kitty agent action implement WP01 --agent codex --mission exclude-canceled-work-packages-from-lanes-01M0S6W4
```

## Objective

Make canonical work-package cancellation usable during `finalize-tasks`. A current `canceled` work package remains in static definitions and append-only lifecycle history but contributes nothing to ownership validation or execution-lane computation. Any eligible work package still depending directly on canceled work causes one explicit, complete, pre-mutation refusal. When every known work package is canceled, finalization succeeds with a valid zero-execution-lane manifest.

Keep `compute_lanes` pure and status-agnostic. Do not change cancellation transitions, exclude `done`, rewrite dependency declarations, delete prompts, reinterpret #3431 cycle semantics, or take on #3281 allocation retry/history/propagation.

The first implementation commit must contain only the exact-command acceptance test and must be proven RED on the untouched planning-base production code. Production edits start after that evidence exists.

## Required Context

Read before editing:

- `.kittify/charter/charter.md`
- `kitty-specs/exclude-canceled-work-packages-from-lanes-01M0S6W4/spec.md`
- `kitty-specs/exclude-canceled-work-packages-from-lanes-01M0S6W4/plan.md`
- `kitty-specs/exclude-canceled-work-packages-from-lanes-01M0S6W4/research.md`
- `kitty-specs/exclude-canceled-work-packages-from-lanes-01M0S6W4/data-model.md`
- `kitty-specs/exclude-canceled-work-packages-from-lanes-01M0S6W4/contracts/canceled-finalization.md`
- `kitty-specs/exclude-canceled-work-packages-from-lanes-01M0S6W4/quickstart.md`

Ground implementation in the current code, especially:

- `mission_finalize.finalize_tasks`: ordering from dependency resolution through bootstrap, ownership validation, preview, and commit pipeline;
- `_validate_owned_files_not_in_mission_specs`, `_validate_ownership_manifests`, `_emit_validate_only_report`, `_compute_and_write_lanes`, and `_run_commit_pipeline`;
- `resolve_status_surface_with_anchor`, `has_event_log`, and `get_all_wp_lanes`;
- `lanes.compute.compute_lanes`, including the merged #3431 post-collapse cycle gate;
- existing empty-input error `LANE_COMPUTATION_ABORTED_EMPTY_INPUTS`.

## Branch Strategy

- **Planning base**: `fix/exclude-canceled-work-packages-from-lanes`
- **Mission merge target**: `fix/exclude-canceled-work-packages-from-lanes`
- **Execution workspace**: accept only the path returned by Spec Kitty after the action command; the computed `lanes.json` allocation owns the actual worktree and branch.
- **External landing**: a later PR targets `origin/main`. Do not push directly to `main`, mark a draft PR ready, enable auto-merge, or merge without the separate gate.

## Commit and Review Checkpoints

1. **Checkpoint A — RED**: commit only T001's new acceptance test; record the focused command and expected behavior failure.
2. **Checkpoint B — Policy seam**: after T002/T003, review the one-read authority boundary, cut-edge completeness, deterministic ordering, and absence of earlier writers.
3. **Checkpoint C — Consumer parity**: after T004/T005, review every filtered map and distinguish all-canceled success from malformed eligible input.
4. **Checkpoint D — Ready for review**: after T006/T007, provide commands, results, commits, remaining risks, and proposed tracer entries.

## Subtasks and Detailed Guidance

### T001 – Commit exact-command RED cancellation acceptance coverage

**Purpose**: Prove the current finalizer mishandles canonical cancellation and freeze the externally observable contract before production changes.

**Steps**:

1. Create `tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py` using the established real Typer/finalizer fixtures and coordination-aware event helpers. Do not set a fake `lane` field in prompt frontmatter and call that canonical.
2. Seed current lifecycle state through append-only events on the authoritative surface. Include one mixed Mission where canceled work has absent or invalid ownership, one stale eligible-to-canceled dependency, and one all-canceled Mission.
3. Invoke the exact `finalize-tasks` command surface in both normal and `--validate-only --json` modes where applicable.
4. Assert the mixed Mission can retain the canceled prompt while only eligible work reaches ownership/allocation.
5. Assert stale dependency output contains error code `CANCELED_WP_DEPENDENCY`, every direct pair, both IDs per pair, and remove-or-repoint recovery.
6. Snapshot all finalization-owned mutation surfaces before the stale attempt: `meta.json`, issue/acceptance matrices, WP prompts, `tasks.md`, event log, `lanes.json`, dossier candidates, Git HEAD, index, and working-tree paths. Assert no delta.
7. Assert all-canceled finalization produces a valid zero-execution-lane result rather than `LANE_COMPUTATION_ABORTED_EMPTY_INPUTS`.
8. Run against untouched production code and prove failure is the missing cancellation behavior, not fixture setup, status placement, Git topology, or SaaS configuration.
9. Commit only the new acceptance file. Capture `git show --name-only` and the RED command/output for review.

**Validation**:

- Event-derived state is necessary for the test to pass after implementation.
- The stale diagnostic is complete and deterministic, not a substring check for one pair.
- The mutation snapshot is taken after fixture setup and before invoking finalization.
- The RED commit contains no source edit and no weakened/expected-failure marker.

### T002 – Implement and unit-test the immutable eligibility projection

**Purpose**: Centralize cancellation policy in one deterministic, I/O-free model rather than distributing filters through the finalizer.

**Steps**:

1. Create `src/specify_cli/cli/commands/agent/finalization_eligibility.py` with frozen value objects for `FinalizationEligibility` and `StaleCanceledDependency`.
2. Accept explicit known work-package IDs, direct dependencies, and an already-read lifecycle map. The module must not resolve paths, read events, import CLI consoles, emit output, or call `compute_lanes`.
3. Normalize ordering deterministically. `eligible_wp_ids` plus `canceled_wp_ids` must partition known IDs.
4. Treat only exact current `Lane.CANCELED` as excluded. `done`, blocked, approved, and every other valid state remain eligible.
5. Treat a missing per-WP lifecycle entry as eligible so first finalization can bootstrap new work packages. Do not catch or downgrade status-reader failures here.
6. Detect all direct eligible-to-canceled edges before filtering. Exclude edges whose source is canceled; canceled-to-canceled declarations do not block.
7. Return the eligible dependency graph with only eligible keys and prerequisites. A nonempty stale set is a caller-visible invalid result, not silently removed evidence.
8. Add `tests/specify_cli/cli/commands/agent/test_finalization_eligibility.py` covering unchanged input, one canceled node, all canceled, missing status, `done`, reopened/current non-canceled, canceled-source edges, multiple stale edges, duplicate dependency input if legal, and repeat determinism.
9. Add a generic typed keyed-map filter only if it reduces repeated orchestration logic without obscuring types; otherwise construct filtered maps explicitly at one call site.

**Validation**:

- Unit tests do not need a repository or filesystem.
- Projection complexity is linear apart from deterministic diagnostic sorting.
- No lifecycle/status filesystem authority moves into the pure module.
- No allocator changes are needed for T002.

### T003 – Resolve canonical state once and reject stale edges before writes

**Purpose**: Integrate the pure policy at the only orchestration layer that owns status topology and CLI failure rendering.

**Steps**:

1. In `mission_finalize.finalize_tasks`, keep read-only repository/Mission/branch/task/dependency resolution first. Raw dependency coverage and cycle validation must still run before projection.
2. Resolve the authoritative read directory with `resolve_status_surface_with_anchor`; read current lanes once with the canonical event reader. Do not reuse `_execution_has_begun`, whose documented contract deliberately degrades read failures to `False`.
3. If the event log or surface is absent on a genuine first-finalize path, distinguish that valid no-WP-events state from unreadable/corrupt authority using existing status primitives. Never infer cancellation from prompt metadata or prior `lanes.json`.
4. Build the projection from known task-file IDs and the resolved dependency graph.
5. If stale edges exist, emit one human or JSON refusal and raise `typer.Exit(1)`. JSON uses `CANCELED_WP_DEPENDENCY` and the contract's sorted record array. Human mode renders the same full set.
6. Each recovery record must name the dependent and canceled prerequisite and say to remove or repoint that dependent's dependency.
7. Move existing writers behind this guard. Audit at least target-branch override persistence, issue-matrix scaffolding, frontmatter writes, event emission/bootstrap, `tasks.md` regeneration, lane/acceptance artifacts, dossier sync, and commits.
8. Preserve the existing target-branch override rollback contract for errors occurring after persistence; the new stale refusal should occur before persistence and need no rollback.
9. Add phase-level tests for corrupt status, unavailable coordination surface, fresh Mission with no per-WP lifecycle events, complete multi-edge JSON, and complete human rendering.

**Validation**:

- Patch every known writer in a refusal test and assert it was not called.
- Stale results sort by dependent ID then canceled prerequisite ID.
- Re-running the same input emits the same records.
- First finalization without seeded WP lanes remains valid.
- Status corruption fails closed and does not consult secondary state.

### T004 – Filter every ownership and execution-lane consumer

**Purpose**: Ensure one eligible set governs all ownership and allocation behavior, with no canceled work reintroduced by fallback helpers.

**Steps**:

1. After the existing bootstrap/frontmatter gathering needed to preserve static Mission records, derive eligible versions of every keyed input used by execution eligibility: in-memory frontmatter, gathered frontmatter, bodies, ownership manifests, and dependency graph.
2. Pass eligible in-memory frontmatter to `_validate_owned_files_not_in_mission_specs`; a canceled `kitty-specs/` declaration must not block eligible work.
3. Pass eligible manifests and eligible frontmatter together to `_validate_ownership_manifests`. This is load-bearing because `_resolve_wp_manifests_for_validation` rebuilds missing manifests from the supplied frontmatter and would reintroduce canceled work if only manifests were filtered.
4. Preserve overlap, authoritative-surface, literal-path/create-intent, audit-coverage, and execution-mode validation for every eligible work package.
5. Pass the eligible graph, manifests, frontmatter, and bodies to validate-only preview and committed computation.
6. Ensure canceled IDs cannot appear in execution-lane membership, inferred surfaces, lane dependencies, collapse reports, planning-artifact lists, or parallelization-risk output.
7. Preserve complete static requirement traceability and work-package definitions. Do not delete canceled prompt files, remove task-outline sections, or rewrite dependencies.
8. Add tests for canceled invalid authoritative surface, empty ownership, planning-artifact mode, overlapping ownership, unmatched literal paths, and canceled collapse influence. Pair each with an eligible control proving the validation still fires when not canceled.

**Validation**:

- Every execution consumer receives the identical eligible key set.
- Eligible ownership failures retain existing error codes and messages.
- Canceled work remains readable from prompts and canonical lifecycle history after success.
- No new status read appears downstream of the projection.

### T005 – Support normal and validate-only all-canceled success

**Purpose**: Represent zero executable work explicitly without weakening existing malformed-input protection.

**Steps**:

1. Preserve structural validation of the raw known work-package set and dependency graph before projection.
2. Thread enough projection context into `_emit_validate_only_report` and `_compute_and_write_lanes` to distinguish `eligible_count == 0 && canceled_count == known_count > 0` from genuinely absent/malformed input.
3. For the proven all-canceled case, call pure `compute_lanes` with empty eligible maps. Reuse its existing empty-manifest result rather than constructing a competing manifest inline.
4. In normal mode, write the standard `lanes.json` shape with zero execution lanes and keep the rest of successful finalization reporting truthful.
5. In validate-only mode, report `computed: true`, `count: 0`, and an empty lane ID list while preserving the zero-mutation invariant.
6. If any eligible work remains and ownership manifests or the dependency graph are unexpectedly empty, retain `LANE_COMPUTATION_ABORTED_EMPTY_INPUTS` and absence of `lanes.json`.
7. Preserve planning commit provenance behavior in the zero-lane manifest where the existing manifest contract requires it.
8. Add normal, JSON, human, validate-only, repeated-finalize, and prior-nonempty-manifest-to-zero cases.

**Validation**:

- All-canceled success retains prompts and events.
- A Mission of eligible planning-artifact work does not become success merely because its manifest map is empty.
- Validate-only does not write status, frontmatter, tasks, lanes, matrices, or Git state.
- Normal and preview counts agree.

### T006 – Complete compatibility, integrity, determinism, and performance regressions

**Purpose**: Prove cancellation is the only changed dimension and compose safely with merged #3431 behavior.

**Steps**:

1. Add a `done` fixture and assert it remains eligible under C-002.
2. Add a formerly canceled but governed-current-non-canceled fixture and assert current state participates normally.
3. For a no-cancellation fixture, compare execution-lane membership, dependency edges, ownership findings, planning-artifact classification, collapse report, and cycle findings against the existing baseline behavior.
4. Keep `tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py` and lane cycle suites unchanged unless a fixture extension is strictly necessary. The surviving eligible graph must still reach #3431's deterministic post-collapse cycle gate.
5. Cover a canceled node that was the sole member of a prior execution lane and ensure no empty dangling execution-lane dependency survives.
6. Cover direct and transitive shapes: only direct eligible-to-canceled cut edges are diagnosed; an eligible path cannot silently traverse a removed canceled node.
7. Build a deterministic 100-work-package fixture with representative direct edges and canceled nodes. Measure the repository's existing end-to-end finalization target without sleeps or retries; avoid a brittle microbenchmark threshold on shared CI unless the project already provides a performance harness.
8. Run the existing empty-input, ownership, validate-only-readonly, disjoint-fan-in, and post-collapse-cycle regression modules named in `quickstart.md`.
9. Confirm Linux/macOS behavior directly and keep platform-neutral path/order/output code. Record any Windows-only validation limitation explicitly rather than claiming unrun evidence.

**Validation**:

- No-cancellation results are structurally identical aside from allowed timestamps/provenance.
- `done` is not filtered.
- Corrupt status never falls back to frontmatter.
- The 100-WP case meets the two-second target on supported development hardware.
- #3431 cycle tests retain their prior outcome.

### T007 – Run focused quality gates and prepare review evidence

**Purpose**: Close the atomic WP with reproducible evidence, clean implementation boundaries, and a reviewer-ready handoff.

**Steps**:

1. Run the exact focused commands from `quickstart.md` using the managed environment and no retries.
2. Run `ruff check` on both touched source files and the focused tests. Fix causes; do not add blanket `noqa` or exclude rules.
3. Run strict mypy on the new pure module and `mission_finalize.py`. Keep immutable mappings/types explicit enough for strict mode.
4. Run the repository's relevant architecture and terminology gates, including the execution-lane single-seam/cycle protections if available.
5. Run `git diff --check`, inspect changed-file ownership, and confirm no `kitty-specs/` file was edited from the implementation worktree.
6. Check touched functions remain within the charter's complexity ceiling. Extract small helpers instead of adding nested branches to the 2,996-line command.
7. Record the RED commit, production commits, exact test/lint/type commands, results, performance measurement, platform scope, and remaining risks.
8. Propose concise additions for `traces/approach.md`, `traces/design-decisions.md`, and `traces/tooling-friction.md` in the handoff. The orchestrator applies those coordination-owned planning-artifact edits outside this code-change WP.

**Validation**:

- Focused behavior and regression suites pass without retries.
- Lint, strict typing, terminology, architecture, and diff checks pass.
- Commit history proves the RED test preceded production code.
- Handoff evidence is sufficient for an independent reviewer to reproduce claims.

## Definition of Done

- [ ] The first WP commit contains only the exact-command acceptance test and is demonstrably RED on the planning base.
- [ ] Canonical lifecycle state is read once and only exact current `canceled` is excluded.
- [ ] Every direct eligible-to-canceled dependency is reported with both IDs and corrective action before any finalization mutation.
- [ ] Canceled work is absent from every ownership and execution-lane consumer but remains in prompts and append-only history.
- [ ] Mixed Missions contain only eligible execution work.
- [ ] All-canceled Missions produce a persisted zero-lane result and a computed zero-lane validate-only preview.
- [ ] Eligible malformed/empty inputs retain existing refusal behavior.
- [ ] `done`, reopened, first-finalize, no-cancellation, and #3431 cycle behavior remain compatible.
- [ ] Status corruption fails closed without secondary inference.
- [ ] The 100-work-package target is measured and met on supported development hardware.
- [ ] Focused tests, lint, strict typing, architecture/terminology, complexity, and diff gates pass without retries or blanket suppressions.
- [ ] Review handoff contains commit ordering, commands/results, platform limits, risks, and proposed tracer entries.

## Risks and Guardrails

- **Authority drift**: status I/O belongs in `mission_finalize.py`; pure projection accepts data and never finds it.
- **Filter drift**: use one eligible ID set for all keyed maps; tests should compare keys at the consumer seams.
- **Fallback reintroduction**: filtered manifests and frontmatter must travel together.
- **Pre-guard residue**: assert writer call order, not only absence of `lanes.json`.
- **Empty-input regression**: all-canceled success must require nonempty known IDs and proof all are canceled.
- **Allocator coupling**: reject any lifecycle import or status read in `lanes/compute.py`.
- **Cycle regression**: preserve #3431's surviving-graph post-collapse validation.
- **Operator history loss**: never delete or rewrite canceled work-package artifacts to make finalization pass.
- **Flaky performance evidence**: prefer the established CLI target harness and deterministic fixtures; do not retry-to-green.

## Reviewer Guidance

Review the RED commit first. Reject if it does not invoke the real finalizer surface, derives cancellation from frontmatter, fails for fixture/setup reasons, contains production code, or is weakened after implementation.

At the policy checkpoint, verify:

- one coordination-aware canonical status read;
- no reuse of graceful-degradation helpers for correctness;
- complete sorted cut-edge detection before filtering;
- stale refusal precedes every writer.

At the consumer checkpoint, verify:

- identical eligible keys across frontmatter, bodies, manifests, dependencies, preview, committed computation, collapse, and risk reporting;
- filtered frontmatter prevents fallback manifest reconstruction;
- all-canceled success is narrowly distinguished from malformed eligible work;
- `compute_lanes` remains status-agnostic.

At final review, reproduce exact CLI scenarios and focused suites. Inspect the working tree and event/manifest artifacts directly. Do not approve based only on pure unit tests when pre-mutation and persisted-lane behavior are claimed.

This package is intentionally atomic at seven subtasks. Splitting the acceptance contract from the finalizer would create a red-only dependency that cannot reach approval, while splitting integration would overlap the same orchestration and fixtures. Use the internal checkpoints instead of artificial work-package boundaries.

## Activity Log

- 2026-08-24T07:00:23Z – system – Prompt created via governed tasks phase.

### Updating Status

Status is managed through the append-only event log. Use canonical Spec Kitty action/status commands; do not edit lifecycle lane fields in frontmatter.
