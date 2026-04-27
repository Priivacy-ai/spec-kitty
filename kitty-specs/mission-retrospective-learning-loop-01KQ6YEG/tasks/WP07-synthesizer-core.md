---
work_package_id: WP07
title: Synthesizer Core (apply / conflict / provenance)
dependencies:
- WP02
- WP03
requirement_refs:
- C-012
- FR-019
- FR-020
- FR-022
- FR-023
- FR-024
- NFR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
- T036
agent: "claude:sonnet:implementer:implementer"
shell_pid: "11422"
history:
- at: '2026-04-27T08:18:00Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/doctrine_synthesizer/
execution_mode: code_change
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
owned_files:
- src/specify_cli/doctrine_synthesizer/__init__.py
- src/specify_cli/doctrine_synthesizer/apply.py
- src/specify_cli/doctrine_synthesizer/conflict.py
- src/specify_cli/doctrine_synthesizer/provenance.py
- tests/doctrine_synthesizer/__init__.py
- tests/doctrine_synthesizer/test_apply.py
- tests/doctrine_synthesizer/test_conflict_failclosed.py
- tests/doctrine_synthesizer/test_provenance.py
priority: P1
status: planned
tags: []
---

# WP07 — Synthesizer Core (apply / conflict / provenance)

## Objective

Implement the synthesizer that applies accepted retrospective proposals to project-local doctrine, DRG, and glossary state with conflict + staleness checks and provenance metadata.

This module is the **only** path that mutates project-local doctrine/DRG/glossary from a retrospective. It does not auto-run; WP08's CLI surface is the trigger.

## Spec coverage

- **FR-019** synthesizer materializes accepted proposals.
- **FR-020** auto-apply allowlist limited to `flag_not_helpful`.
- **FR-022** provenance on every synthesized artifact.
- **FR-023** conflict detection fail-closed.
- **FR-024** later mission run sees updated context (verified by WP11).
- **NFR-006** 100% provenance fidelity.
- **C-012** reviewable and reversible.

## Context

Source-of-truth contract is in [`../contracts/synthesizer_hook.md`](../contracts/synthesizer_hook.md). The conflict predicates are pinned in [`../research.md`](../research.md) R-006.

**Note on package name**: the plan referenced `src/specify_cli/doctrine/synthesizer/` as the home. Because `src/doctrine/` is the existing shipped DRG (a separate package boundary), placing this synthesizer under a CLI-internal `src/specify_cli/doctrine_synthesizer/` keeps the boundary clean. Name flexibility is acceptable; pick a name that doesn't collide with the existing `src/doctrine/` shipped package.

## Subtasks

### T031 — `apply_proposals()` API skeleton

In `src/specify_cli/doctrine_synthesizer/apply.py`:

```python
def apply_proposals(
    *,
    mission_id: MissionId,
    repo_root: Path,
    proposals: list[Proposal],
    approved_proposal_ids: set[ProposalId],
    actor: ActorRef,
    dry_run: bool = True,
) -> SynthesisResult: ...
```

`SynthesisResult` per `data-model.md`. The default `dry_run=True` is intentional — callers must explicitly opt in to mutation.

Behavior contract (from `synthesizer_hook.md`):
1. Compute the effective batch: `approved_proposal_ids` ∪ all `flag_not_helpful` proposals.
2. Run conflict detection (T032). If conflicts → fail closed; emit rejection events; return.
3. Run staleness check (T033). Reject stale proposals; surviving proposals continue.
4. If `dry_run`: return planned applications + rejections; emit no events.
5. If not `dry_run`: apply each proposal in deterministic order; write provenance sidecar (T034); emit `proposal.applied` event per success; record `apply_attempts`.

### T032 — Conflict detection per R-006 predicates

In `src/specify_cli/doctrine_synthesizer/conflict.py`:

```python
def detect_conflicts(proposals: list[Proposal]) -> list[ConflictGroup]: ...
```

Implement the pairwise predicates from `research.md` R-006:

- `add_edge(E)` vs `remove_edge(E)`: same `(from_node, to_node, kind)`.
- `add_edge(E)` vs `rewire_edge(E_old → E)`: B's destination equals A's edge.
- `remove_edge(E)` vs `rewire_edge(E → E_new)`: B's source equals A's edge.
- `add_glossary_term(T)` vs `add_glossary_term(T)`: same key, different `definition_hash`.
- `update_glossary_term(T)` vs `update_glossary_term(T)`: same key, different `definition_hash`.
- `synthesize_*(X)` vs `synthesize_*(X)` (same kind): same id, different `body_hash`.
- `flag_not_helpful` does NOT conflict with anything (informational).

Return `ConflictGroup`s where each group references the conflicting proposal ids and a reason string.

### T033 — Staleness check (evidence event reachability)

For each proposal, verify that every `provenance.source_evidence_event_ids` entry exists in the source mission's event log. If any reference is unreachable, the proposal is staged-then-rejected at apply time (`reason: stale_evidence`); the proposal's `state.status` remains `accepted`, only an apply attempt is recorded.

Implementation: read the source mission's event log once, build a `set[EventId]`, check membership per proposal.

### T034 — Provenance sidecar writer

In `src/specify_cli/doctrine_synthesizer/provenance.py`:

```python
def write_provenance(
    *,
    artifact_path: Path,
    artifact_id: str,
    proposal: Proposal,
    actor: ActorRef,
    re_applied: bool = False,
) -> Path: ...
```

The sidecar lives at a deterministic path next to the target artifact. For doctrine artifacts: `<artifact-dir>/.provenance/<artifact-id>.yaml`. For DRG edges/glossary: similar pattern under their respective storage area. The sidecar's required minimum fields are pinned in `synthesizer_hook.md`.

The function returns the absolute path written.

### T035 — Idempotency via provenance presence check

Re-running the synthesizer with the same approved set on the same project state MUST be safe. Implementation:

- Before applying a proposal, check whether a provenance sidecar exists for `(source_mission_id, proposal_id)` at the expected path.
- If yes: treat as already-applied; emit no new event; record in `SynthesisResult.applied` with `re_applied: True`.
- If no: apply normally.

The `re_applied` flag distinguishes a no-op re-run from a fresh application.

### T036 — Tests

In `tests/doctrine_synthesizer/`:

- `test_apply.py` — for each proposal kind (or at minimum `add_glossary_term`, `flag_not_helpful`, `add_edge`): apply succeeds; provenance written; event emitted. Re-run → idempotent (`re_applied=True`).
- `test_conflict_failclosed.py` — pair every conflict predicate from R-006. Build a fixture batch with each conflict pair; assert `apply_proposals` returns no `applied` rows and a non-empty `conflicts` list. With `--apply` (dry_run=False), still nothing is applied and rejection events are emitted.
- `test_provenance.py` — sidecar carries `source: retrospective`, `source_mission_id`, `source_proposal_id`, `source_evidence_event_ids`, `applied_by`, `applied_at`. Re-run sets `re_applied: True`.

Recommend implementing `add_glossary_term` and `flag_not_helpful` first (smallest blast radius); layer in `*_edge` and `synthesize_*` once the test harness is solid.

## Definition of Done

- [ ] `apply_proposals` defaults to `dry_run=True`.
- [ ] All R-006 conflict predicates implemented and tested.
- [ ] Staleness check rejects unreachable evidence references.
- [ ] Provenance sidecar carries the full FR-022 minimum set.
- [ ] Re-run idempotency demonstrated by test.
- [ ] No silent fallback to `applied` on any error path.
- [ ] `mypy --strict` passes.
- [ ] Coverage ≥ 90%.
- [ ] No changes outside `owned_files`.

## Risks

- **Per-kind apply logic complexity**: ship the smallest set first (glossary + flag_not_helpful), then layer.
- **Idempotency check correctness**: provenance path scheme must be canonical; document in code comment.
- **Conflict matrix coverage**: R-006 enumerates predicates; cover them all in tests.

## Reviewer guidance

- Confirm `dry_run=True` is the default in the API signature.
- Confirm the conflict matrix in the test file mirrors R-006 row-for-row.
- Confirm provenance sidecar fields against `synthesizer_hook.md` minimums.
- Confirm idempotency by running the same fixture batch twice in one test.

## Implementation command

```bash
spec-kitty agent action implement WP07 --agent <name>
```

## Activity Log

- 2026-04-27T10:07:02Z – claude:sonnet:implementer:implementer – shell_pid=11422 – Started implementation via action command
- 2026-04-27T10:24:32Z – claude:sonnet:implementer:implementer – shell_pid=11422 – Ready for review: synthesizer core (8 proposal kinds, R-006 conflict matrix, staleness, provenance, idempotency); 69 tests / 95% cov / mypy --strict clean
