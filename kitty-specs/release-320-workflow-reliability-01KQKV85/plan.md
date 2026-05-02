# Implementation Plan: 3.2.0 Workflow Reliability Blockers

**Branch**: `release-320-workflow-reliability-01KQKV85` | **Date**: 2026-05-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/robert/spec-kitty-dev/spec-kitty-20260502-095015-YQAp4h/spec-kitty/kitty-specs/release-320-workflow-reliability-01KQKV85/spec.md`

## Summary

This mission stabilizes the 3.2.0 implement, review, merge, and ship workflow by making local state transitions provable, review prompts isolated, diff references canonical, work-package ownership context active, final-sync diagnostics parseable, and release gates resistant to branch and review-artifact contradictions. The implementation approach is regression-first: build deterministic fixtures for each blocker, then make the smallest local changes in the existing status, workflow, review, policy, sync, and merge modules that satisfy those fixtures without introducing new shared runtime or SaaS coupling.

Engineering alignment: preserve Spec Kitty's event-sourced mission model. A command may report success only after the durable local state it promises can be read back. Hosted sync remains secondary to local correctness and must not corrupt stdout or local command status after a successful local mutation. Review and release commands must derive identity from canonical mission state rather than slug or path reconstruction.

## Technical Context

**Language/Version**: Python 3.11+ for CLI and library code.  
**Primary Dependencies**: Typer, Rich, ruamel.yaml, pytest, mypy; existing internal packages under `src/specify_cli/status`, `src/specify_cli/cli/commands/agent`, `src/specify_cli/review`, `src/specify_cli/policy`, `src/specify_cli/sync`, `src/specify_cli/merge`, and `src/specify_cli/workspace`.  
**Storage**: Local mission files under `/Users/robert/spec-kitty-dev/spec-kitty-20260502-095015-YQAp4h/spec-kitty/kitty-specs/<mission>/`, especially `status.events.jsonl`, `status.json`, `tasks/WP*.md`, `review-cycle-*.md`, `meta.json`, lane/workspace context files, and `.kittify/merge-state.json`; hosted sync is a secondary diagnostic path.  
**Testing**: Focused pytest unit and integration fixtures for status transitions, workflow actions, review prompt isolation, canonical diff refs, active ownership guards, sync output hygiene, merge/ship preflight, and review artifact consistency. JSON command surfaces must be validated with a JSON parser.  
**Target Platform**: Cross-platform Spec Kitty CLI on macOS, Linux, and Windows 10+ with Git available.  
**Project Type**: Single Python CLI/library repository with mission artifacts under `kitty-specs/`.  
**Performance Goals**: Added invariant checks should keep typical local CLI workflow commands under the charter target of 2 seconds for normal projects; regression fixtures should avoid real network latency.  
**Constraints**: Commands touching SaaS, tracker, hosted auth, or sync behavior on this computer must run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`; real hosted network calls are avoided except for explicitly scoped sync paths; planning and task artifacts stay in the repository root checkout.  
**Scale/Scope**: One 3.2.0 stabilization mission covering parent issue #822, blockers #945, #949, #950, #951, #952, #953, #904, and verification issue #944. Expected implementation spans six work streams but remains within the `spec-kitty` repo unless tests prove a sibling contract change is required.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Python 3.11+**: PASS. All planned changes are in the existing Python CLI/library code.
- **typer/rich/ruamel.yaml/pytest/mypy**: PASS. The plan uses existing dependencies and does not introduce new runtime dependencies.
- **90%+ test coverage for new code**: PASS WITH REQUIREMENT. Each work stream includes focused pytest coverage for new behavior.
- **mypy --strict**: PASS WITH REQUIREMENT. New typed helpers must satisfy the existing strict type-checking expectations for touched modules.
- **Integration tests for CLI commands**: PASS. The regression harness explicitly covers command surfaces and JSON output.
- **CLI operation performance under 2 seconds for typical projects**: PASS WITH MONITORING. Readback and metadata validation must be local file checks, not remote sync waits.
- **Cross-platform behavior**: PASS WITH REQUIREMENT. Path and prompt isolation changes must use pathlib and existing workspace resolvers.
- **No hardcoded default branch names**: PASS. The plan uses `current_branch`, `planning_base_branch`, and `merge_target_branch` from command payloads; the actual branch for this mission is `main`.
- **Central CLI-SaaS API contract**: PASS. This mission treats hosted sync as secondary diagnostics; any change to actual CLI-SaaS route or payload shape must update `/Users/robert/spec-kitty-dev/spec-kitty-20260502-095015-YQAp4h/spec-kitty-saas/contracts/cli-saas-current-api.yaml` in the same change.
- **Production safety**: PASS. This mission targets local CLI behavior and the dev sync flag rule, not production SaaS resources.

No charter violations are accepted in this plan.

## Project Structure

### Documentation (this mission)

```
/Users/robert/spec-kitty-dev/spec-kitty-20260502-095015-YQAp4h/spec-kitty/kitty-specs/release-320-workflow-reliability-01KQKV85/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── merge-ship-preflight.yaml
│   ├── review-prompt-metadata.yaml
│   ├── status-transition-atomicity.yaml
│   └── sync-diagnostics-output.yaml
├── checklists/
│   └── requirements.md
└── tasks/
    └── README.md
```

### Source Code (repository root)

```
/Users/robert/spec-kitty-dev/spec-kitty-20260502-095015-YQAp4h/spec-kitty/
├── src/specify_cli/cli/commands/agent/
│   ├── mission.py
│   ├── tasks.py
│   └── workflow.py
├── src/specify_cli/cli/commands/
│   ├── merge.py
│   └── review.py
├── src/specify_cli/status/
│   ├── emit.py
│   ├── reducer.py
│   ├── store.py
│   ├── transition_context.py
│   ├── transitions.py
│   ├── work_package_lifecycle.py
│   └── wp_state.py
├── src/specify_cli/review/
│   ├── artifacts.py
│   ├── baseline.py
│   ├── fix_prompt.py
│   └── lock.py
├── src/specify_cli/policy/
│   ├── commit_guard.py
│   ├── commit_guard_hook.py
│   └── merge_gates.py
├── src/specify_cli/sync/
│   ├── diagnostics.py or existing diagnostic helpers
│   ├── dossier_pipeline.py
│   ├── emitter.py
│   └── runtime_event_emitter.py
├── src/specify_cli/merge/
│   ├── state.py
│   └── workspace.py
├── src/specify_cli/workspace/
│   └── context.py
└── tests/
    ├── status/
    ├── tasks/
    ├── review/
    ├── policy/
    ├── sync/
    ├── merge/
    └── integration/
```

**Structure Decision**: Keep changes local to existing CLI workflow modules and tests. Add small helpers only where they centralize a repeated invariant, such as transition readback, review prompt identity validation, active work-package context resolution, or non-fatal sync diagnostic rendering. Do not introduce a new service layer or external runtime package.

## Complexity Tracking

No charter violations are planned.

## Parallel Work Analysis

### Dependency Graph

```
Regression harness and fixtures
  -> Status transition atomicity and #944 verification
  -> Review prompt isolation and canonical diff refs
  -> Active work-package ownership guard
  -> Sync finalization output hygiene
  -> Merge/ship preflight and review artifact consistency
  -> End-to-end smoke and issue traceability review
```

### Work Distribution

- **Sequential work**: Build shared deterministic fixtures first so every subsequent fix proves behavior against the same mission/worktree/status shapes.
- **Parallel streams**: Status atomicity, review prompt isolation, ownership guard context, sync output hygiene, and merge/review gates can proceed independently once fixtures exist.
- **Agent assignments**: Work packages should use disjoint ownership boundaries: status/task lifecycle modules, review modules, policy/workspace modules, sync modules, merge/release modules, and cross-cutting smoke/docs.

### Coordination Points

- **Sync schedule**: Merge the regression harness before feature fixes, then integrate each stream only after its focused tests pass.
- **Integration tests**: Run the targeted pytest subset for each stream, then a final smoke path covering `init -> specify -> plan -> tasks -> implement/review -> merge -> PR` without manual status-event emission.
- **Traceability**: Each work package should name the linked issue numbers it closes or verifies.

## Phase 0: Research Summary

See [research.md](./research.md).

Key planning decisions:

- Status-changing commands will use local append plus readback invariants as the source of success truth.
- Review prompts will include structured self-identifying metadata and be stored in invocation-specific paths.
- Review diff commands will be derived from canonical mission and lane state.
- Ownership guards will resolve the active work package at guard time.
- Final-sync failures after local success will be rendered as non-fatal diagnostics while preserving stdout contracts.
- Merge/ship readiness will include explicit branch divergence and review-artifact consistency gates.

## Phase 1: Design Summary

See [data-model.md](./data-model.md), [quickstart.md](./quickstart.md), and the contract files in [contracts/](./contracts/).

Design artifacts capture:

- Durable status transition evidence and readback rules.
- Review prompt identity metadata and fail-closed validation.
- Non-fatal sync diagnostic output rules.
- Merge/ship preflight and review artifact consistency decisions.

## Post-Design Charter Recheck

- **Testing requirements**: PASS. The plan defines focused unit and integration tests for every blocker.
- **No unnecessary dependencies**: PASS. No new runtime dependency is planned.
- **Branch terminology governance**: PASS. Planning uses actual branch `main` only where the helper reported `main`.
- **SaaS contract boundary**: PASS. No hosted route changes are planned; if a sync payload changes during implementation, the SaaS contract update becomes mandatory.
- **Production safety**: PASS. No production command is part of this plan.

## Stop Point

This `/spec-kitty.plan` phase stops after planning artifacts. It does not generate `tasks.md`, work package files, or implementation changes.
