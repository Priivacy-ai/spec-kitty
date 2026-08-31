---
work_package_id: WP03
title: Lifecycle persistence and fan-out split
dependencies: []
requirement_refs:
- FR-009
- FR-010
planning_base_branch: fix/setup-plan-auth-diagnostics-nonfatal
merge_target_branch: fix/setup-plan-auth-diagnostics-nonfatal
branch_strategy: Planning artifacts for this mission were generated on fix/setup-plan-auth-diagnostics-nonfatal. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/setup-plan-auth-diagnostics-nonfatal unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 1 - Lifecycle side-effect seam
history:
- at: '2026-08-23T18:07:49Z'
  actor: system
  action: Prompt created to close implicit lifecycle fan-out bypass
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/status/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/lifecycle_events.py
- tests/status/test_lifecycle_events.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3621
---

# Work Package Prompt: WP03 – Lifecycle persistence and fan-out split

## Do This First: Load Agent Profile

Load `implementer-ivan`, the charter, and the Mission plan. Begin with failing tests in
the lane's first commit. This WP is independent and may run alongside WP01/WP02.

## Objectives & Success Criteria

Refactor lifecycle emission so local JSONL persistence and hosted adapter fan-out are
explicitly separate operations. The existing composed API must remain compatible for
unaffected callers, while setup-plan can request local-only artifact-phase persistence
and receive the event envelope for later guarded fan-out.

Success means:

- local-only emission writes one valid envelope and returns it;
- local-only emission invokes zero registered SaaS fan-out handlers;
- explicit hosted fan-out invokes the handler exactly once when called;
- existing `append_lifecycle_event()` retains local-write-plus-fan-out behavior;
- write failures retain existing no-raise/return semantics;
- validation, Lamport/order, producer conformance, and payloads remain unchanged.

## Context & Constraints

The adversarial review traced
`mission_setup_plan._emit_spec_plan_phase_events` → `emit_artifact_phase` →
`append_lifecycle_event` → `_queue_lifecycle_event_if_enabled` → registered sync handler
→ `OfflineQueue`. The previous plan's “local-only” assumption was false.

Read plan component 3, research decision 5, data-model `LifecycleEventIntent`, contract
hosted-effect boundary, and `docs/context/system-events.md`.

Do not edit sync adapters, event package schemas, status transition emission, setup-plan,
or dossier code. Do not globally unregister adapters.

## Branch Strategy

- **Planning base branch**: `fix/setup-plan-auth-diagnostics-nonfatal`
- **Merge target branch**: `fix/setup-plan-auth-diagnostics-nonfatal`
- **Implementation command**: `spec-kitty agent action implement WP03 --agent <name>`
- Use the independent lane workspace assigned in `lanes.json`.
- Modify only lifecycle source and its owned test file.

## Subtasks & Detailed Guidance

### Subtask T009 – Write and commit rejecting split-seam tests

**Purpose**: Prove the hidden hosted side effect before refactoring.

1. Register a fan-out spy using the same adapter registration path existing tests use.
2. Invoke the proposed local-only append/phase API.
3. Assert one local JSONL event, returned envelope identity, and zero fan-out calls.
4. Separately assert explicit hosted fan-out calls the spy once with the same envelope
   and log context.
5. Pin legacy `append_lifecycle_event()` to one local write plus one fan-out call.
6. Cover local write failure returning `None` without fan-out.
7. Commit the failing tests before production edits; current code must demonstrate the
   coupled behavior.

### Subtask T010 – Extract explicit operations

**Purpose**: Make the side-effect boundary visible in the API.

1. Extract `persist_lifecycle_event_local(...)` (or a convention-consistent name) that
   performs validation, envelope construction, ordering, and JSONL append only.
2. Extract `fanout_lifecycle_event_hosted(envelope, *, log_path)` that invokes the
   existing registered adapter path only.
3. Ensure the local function cannot reach adapter resolution by imports or callbacks.
4. Refactor `append_lifecycle_event()` to compose local persistence followed by hosted
   fan-out only when local persistence returned an envelope.
5. Preserve logging and failure behavior for existing callers.

No event schema or payload change is authorized.

### Subtask T011 – Add local-only artifact-phase emission

**Purpose**: Give WP04 a supported setup-plan path without duplicating event creation.

1. Add an explicit artifact-phase local-only function or mode whose name makes the
   absence of hosted fan-out obvious.
2. Reuse the same payload/envelope builder as `emit_artifact_phase`.
3. Return enough context for WP04 to submit hosted fan-out later through its executor.
4. Keep existing `emit_artifact_phase` behavior unchanged for existing callers.
5. Test started/completed phase types and strict producer validation.

Avoid an ambiguous Boolean such as `skip_sync` if an explicit operation communicates the
boundary more clearly.

### Subtask T012 – Run lifecycle regressions

Run:

```bash
uv run pytest -q tests/status/test_lifecycle_events.py \
  tests/status/test_producer_conformance.py \
  tests/status/test_emit_fanout_after_adapter.py \
  tests/integration/migration/test_lifecycle_events_preserved.py
uv run ruff check src/specify_cli/status/lifecycle_events.py \
  tests/status/test_lifecycle_events.py
uv run mypy --strict src/specify_cli/status/lifecycle_events.py
```

Inspect event counts and JSONL content, not only returned values.

## Test Strategy

Use registered spies rather than patching away the fan-out seam. Tests must prove the
same event is locally persisted and, only when explicitly requested, offered to hosted
fan-out. Existing producer-conformance tests remain authoritative for envelope shape.

## Risks & Mitigations

- **Duplicate event writes**: exact JSONL line counts.
- **Duplicate fan-out**: exact handler counts and envelope ID equality.
- **Legacy callers lose fan-out**: compatibility test for `append_lifecycle_event`.
- **Local path still imports sync**: reviewer import/call trace and zero-handler test.

## Review Guidance

Trace the local-only function transitively. Reject if it can call
`_queue_lifecycle_event_if_enabled`, a registered adapter, or any sync module. Verify
that the composed compatibility function is the only automatic local→hosted bridge and
that WP04 can use the local-only artifact-phase surface without private calls.

## Activity Log

- 2026-08-23T18:07:49Z – system – Prompt created to close implicit lifecycle fan-out bypass.

### Updating Status

Use `spec-kitty agent tasks move-task WP03 --to <status>`.
