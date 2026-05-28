# Implementation Plan: Mission Coordination Branch with Atomic Event Log

**Mission**: `mission-coordination-branch-atomic-event-log-01KSPTVW`
**Spec**: [spec.md](spec.md)
**Source Issue**: [Priivacy-ai/spec-kitty#1348](https://github.com/Priivacy-ai/spec-kitty/issues/1348)
**Status**: Draft
**Date**: 2026-05-28
**Branch**: `main` (planning_base_branch == merge_target_branch)

---

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement)

**Primary Dependencies**:
- `typer` — CLI framework (existing)
- `rich` — console output (existing)
- `ruamel.yaml` — frontmatter parsing (existing)
- `pytest` — test framework (existing); coverage target ≥ 90% on new modules (charter policy)
- `mypy --strict` — type checking (existing); enforces required keyword-only `destination_ref` on `safe_commit()`
- Stdlib `os.truncate` / `os.path.getsize` — surgical rollback of `status.events.jsonl` (FR-010)
- Stdlib `subprocess` — git invocation (existing pattern in `specify_cli.git.commit_helpers`)
- Stdlib `pathlib`, `fcntl` — filesystem and lock primitives (existing pattern in `specify_cli.locking`)
- `safe_commit` from `specify_cli.git.commit_helpers` (existing helper; signature change in FR-031)
- Existing feature status lock from `specify_cli.locking` (re-used per FR-026, C-013)

**New Dependencies**: None. All mechanisms use stdlib + existing helpers.

**Storage**: Filesystem only. Coordination worktree under `.worktrees/<slug>-<mid8>-coord/`; lane worktrees under `.worktrees/<slug>-<mid8>-lane-<id>/`. Authoritative `status.events.jsonl` and `status.json` live exclusively on the coordination branch (FR-028).

**Branch Strategy**: Per-mission coordination branch `kitty/mission-<slug>-<mid8>` parents each lane branch; coordination branch merges to canonical target at mission close (two-stage merge per FR-008).

**Concurrency Primitive**: Existing feature status lock at `src/specify_cli/locking.py` (file-based, process-level, exclusive). Re-used per FR-026; no parallel lock introduced (C-013).

**Worktree Composition**: Sparse-checkout policy on lane worktrees excludes `kitty-specs/<mission>/status.events.jsonl` and `kitty-specs/<mission>/status.json` from the lane working tree (FR-029).

**Target Branch**: `main` (canonical merge target; `branch_matches_target == true`).

**Migration Strategy**: Legacy missions (no coordination branch present) fall back to lane-branch as `destination_ref`; pre-flight gate, transaction, lock, rollback, and outbound deferral apply uniformly (FR-017, FR-027).

---

## Branch Contract (restated)

- **Current branch at plan start**: `main`
- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **`branch_matches_target`**: true

---

## Architecture Overview

This work splits cleanly into **three layers**, in order from most fundamental to most surface-level:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 3: Workflow command paths (implement, review, finalize-tasks) │
│   - Call sites that mutate mission state                             │
│   - MUST go through Layer 2; MUST NOT call Layer 1 directly          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ uses
┌────────────────────────────▼────────────────────────────────────────┐
│ Layer 2: BookkeepingTransaction service                              │
│   - resolve coordination worktree                                    │
│   - acquire feature status lock                                      │
│   - assert_allowed(destination_ref)                                  │
│   - append event → materialize status.json → safe_commit             │
│   - defer outbound side effects until commit success                 │
│   - surgical rollback on commit failure                              │
│   - release lock                                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │ uses
┌────────────────────────────▼────────────────────────────────────────┐
│ Layer 1: safe_commit(destination_ref=...) + WorkflowMutationPolicy   │
│   - required keyword-only destination_ref                            │
│   - HEAD == destination_ref assertion                                │
│   - delegates to existing protected-branch check                     │
│   - the ultimate gate against silent commit-target drift             │
└─────────────────────────────────────────────────────────────────────┘
```

**Why this ordering matters**: Layer 1 (helper invariant) is the *structural* property. mypy enforces the required parameter; the HEAD assertion enforces the contract. Once Layer 1 is in place, future callers cannot silently land commits on the wrong branch — even ones that bypass Layer 2. Layer 2 (transaction service) sits on top, providing the higher-level atomicity contract. Layer 3 is mechanical migration of existing call sites.

---

## Phase 0 — Outline & Research

Research artifacts capture the architectural decisions surfaced during specify + plan interrogation. They live in [`research.md`](research.md).

### Resolved unknowns

All `NEEDS CLARIFICATION` items from the spec are resolved. The remaining design choices that `/spec-kitty.plan` interrogation locked down:

- **R-001**: Merge strategy for `status.events.jsonl` → linearize via lock-only writes (FR-028); no merge driver needed because lane branches never author the file.
- **R-002**: `destination_ref` enters at the helper level (`safe_commit()` signature change) with internal `HEAD == destination_ref` assertion (FR-031).
- **R-003**: Lane worktree composition → sparse-checkout excludes status files (FR-029); preserves backward compatibility, no data migration.
- **R-004**: Lane-side reads → CLI mediation (`spec-kitty agent tasks status --mission <handle>`) reads from coordination worktree (FR-030).
- **R-005**: PR ordering → helper invariant first, transaction layer second, hardening third.

Full rationale and alternatives considered are documented in `research.md`.

---

## Phase 1 — Design & Contracts

### Data model

See [`data-model.md`](data-model.md). Summary of new entities:

- `GitChangeSet` — value object carrying `destination_ref`, paths to commit, commit message; passed to `safe_commit()` and the policy gate.
- `BookkeepingTransaction` — aggregate that owns a coordination-tree write attempt under the feature status lock.
- `EventReceipt` — return value from `BookkeepingTransaction.append_event(...)`; carries `event_id`, `committed_at`, `commit_sha`, `destination_ref`.
- `CoordinationWorkspace` — service that resolves and (idempotently) creates `.worktrees/<slug>-<mid8>-coord/`.
- `PolicyVerdict` — result type from `WorkflowMutationPolicy.assert_allowed(...)`: either `Allowed` or `Refused(error_code, message, destination_ref)`.
- No changes to existing `StatusEvent` schema beyond ensuring events are written exclusively by `BookkeepingTransaction`.

### Contracts

API surfaces live under [`contracts/`](contracts/):

- [`contracts/safe_commit_signature.md`](contracts/safe_commit_signature.md) — new keyword-only `destination_ref` requirement; HEAD assertion; error codes.
- [`contracts/bookkeeping_transaction.md`](contracts/bookkeeping_transaction.md) — `acquire(mission_id, destination_ref, operation)` returns context manager; `append_event(event)` returns `EventReceipt`; `commit()` is implicit at context exit on success; rollback is implicit on exception.
- [`contracts/workflow_mutation_policy.md`](contracts/workflow_mutation_policy.md) — `assert_allowed(repo_root, change_set)` semantics, error codes, integration with existing protected-branch check.
- [`contracts/coordination_workspace.md`](contracts/coordination_workspace.md) — coordination worktree lifecycle (create/reuse/teardown); `.gitattributes` and sparse-checkout policy for lane worktrees.
- [`contracts/cli_status_mediation.md`](contracts/cli_status_mediation.md) — `spec-kitty agent tasks status --mission <handle>` resolves coordination worktree path regardless of CWD; same for `agent context resolve`.

### Quickstart

See [`quickstart.md`](quickstart.md). Walks an operator through a 2-lane mission end-to-end on the new topology, including a forced commit failure to demonstrate the rollback path.

---

## Charter Check

Charter loaded; active directives are DIRECTIVE_003 (Decision Documentation), DIRECTIVE_010 (Specification Fidelity), DIR-001..014 (project standards).

| Check                                                  | Status | Notes                                                                                                  |
| ------------------------------------------------------ | ------ | ------------------------------------------------------------------------------------------------------ |
| Cross-platform (Linux, macOS, Windows 10+)             | OK     | `os.truncate`, sparse-checkout, and git worktree are all stdlib/git-portable.                          |
| Python 3.11+                                           | OK     | No new dependencies; type hints meet `mypy --strict`.                                                  |
| Git required                                           | OK     | Hard requirement; this mission deepens the git surface.                                                |
| PyPI distribution                                      | OK     | No packaging changes.                                                                                  |
| Tests for new functionality                            | OK     | Coverage targets named in NFR-006; specific test classes named per `data-model.md`.                    |
| Type annotations (mypy --strict)                       | OK     | `destination_ref` required keyword-only catches missing-arg regressions structurally.                   |
| Docstrings for public APIs                             | OK     | New public surfaces (`BookkeepingTransaction`, updated `safe_commit`) get docstrings; private helpers do not. |
| No security issues                                     | OK     | No new credential/secret handling.                                                                     |
| Breaking changes documented in CHANGELOG.md            | OK     | `safe_commit()` signature change is breaking-ish (internal callers); CHANGELOG entry required.         |
| ASCII-only identifier sanitization (DIR-010 / DIR-011) | OK     | Coordination branch name is derived from `mission_slug` + `mid8` (both already sanitized).             |
| Decision documentation (DIRECTIVE_003)                 | OK     | All architectural decisions in `research.md` with rationale + alternatives.                             |
| Specification fidelity (DIRECTIVE_010)                 | OK     | Plan tracks 31 FRs verbatim; no scope drift.                                                            |

No charter conflicts.

---

## Implementation Sequencing (PR Order)

The cross-review's PR ordering is adopted verbatim. `/spec-kitty.tasks` will materialize this into work packages.

### PR 1 — Helper-level invariant (largest mechanical diff, smallest architectural risk)

1. Update `src/specify_cli/git/commit_helpers.py` — `safe_commit()` gains required keyword-only `destination_ref`; add `HEAD == destination_ref` assertion.
2. Audit every existing call site of `safe_commit()` in the codebase. Migrate each one to pass `destination_ref` explicitly. Today these callers all compute `destination_ref = current branch`, so the migration is mechanical.
3. Update the public `spec-kitty safe-commit` CLI to require `--to-branch` (or resolve via the existing branch-context resolver and pass it explicitly).
4. Add the `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS` cleanup — remove any spec-kitty-internal bypass entries (FR-013).
5. Tests: unit coverage for the new assertion, structured-error JSON shape, mypy strict catches missing-arg.

After PR 1 lands: it is structurally impossible for any future `safe_commit()` caller to commit to the wrong branch silently.

### PR 2 — Coordination branch + BookkeepingTransaction

1. `spec-kitty agent mission create` mints coordination branch `kitty/mission-<slug>-<mid8>` (FR-003); idempotent (FR-018).
2. Lane allocator parents each lane branch on the coordination branch (FR-004).
3. New module `src/specify_cli/coordination/` containing:
   - `CoordinationWorkspace` — resolves/creates `.worktrees/<slug>-<mid8>-coord/` (FR-024).
   - `BookkeepingTransaction` — context-manager service (FR-023).
   - `WorkflowMutationPolicy` — wraps existing protected-branch helper, validates `destination_ref` (FR-019, FR-020).
4. Sparse-checkout policy registered at lane worktree creation (FR-029).
5. Migrate planning-artifact commit site (`src/specify_cli/cli/commands/implement.py:236`) to go through `BookkeepingTransaction` (FR-020).
6. Migrate lifecycle status writes (`src/specify_cli/cli/commands/agent/workflow.py:689` and `:1463`) to go through `BookkeepingTransaction` (FR-009/010/019).
7. Migrate `src/specify_cli/status/emit.py:468` to go through `BookkeepingTransaction` (atomicity precondition for FR-010).
8. Fix `_resolve_planning_branch()` in `src/specify_cli/cli/commands/agent/mission.py:321` to return the canonical merge target, not current branch (FR-012).
9. Two-stage merge: `spec-kitty merge` integrates lanes → coordination, then coordination → target (FR-008).
10. Legacy fallback: when no coordination branch exists, route `destination_ref` to the lane branch; same gate, lock, transaction (FR-017, FR-027).
11. CLI status mediation: `agent tasks status` reads coordination worktree (FR-030).
12. Tests: unit coverage for each module; integration tests for the multi-lane scenarios from `quickstart.md`; stress test for SC-12.

### PR 3 — Hardening (optional, can ship later)

1. Architectural test: forbid direct imports of `safe_commit` from transactional workflow modules (must go through `BookkeepingTransaction`).
2. Optional rename to `_safe_commit_unchecked` to make accidental direct use look unusual.
3. Outbound side-effect deferral instrumentation for SaaS sync / dossier ingress (FR-022, NFR-009, SC-09).
4. Migration runbook for in-flight legacy missions that want to move to the new topology (out of scope of the mission, but documented).

---

## Risk register

| ID    | Risk                                                                                                                                                                   | Severity | Mitigation                                                                                                                          |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| RR-01 | Existing CI shells may not have sparse-checkout enabled by default on older git versions.                                                                              | Med      | Plan tests: assert git >= 2.25 (when `git sparse-checkout` became stable). Document min git version in CHANGELOG.                  |
| RR-02 | Lane integration merge (lane → coordination) may surface real code conflicts when two lanes touch the same file.                                                       | Med      | Standard human review/conflict resolution; surface a conflict via `spec-kitty merge --interactive`. Not a regression vs today.       |
| RR-03 | An external script that previously called `safe_commit()` without `destination_ref` will break loudly after PR 1.                                                      | Low      | Acceptable. The error message names the missing parameter; mypy catches it in any typed caller.                                     |
| RR-04 | Sparse-checkout patterns may be silently overridden by `.git/info/sparse-checkout` edits done by hand.                                                                  | Low      | Doctor check: `spec-kitty doctor` verifies sparse-checkout pattern is current; warns if drift.                                      |
| RR-05 | Legacy missions' `destination_ref` resolution may not match the lane branch the operator's worktree is currently on (timing skew).                                     | Med      | `WorkflowMutationPolicy` requires `HEAD == destination_ref`; legacy path resolves `destination_ref` from worktree HEAD explicitly. |
| RR-06 | The coordination worktree may be deleted by an operator out-of-band (`rm -rf .worktrees/<slug>-<mid8>-coord/`).                                                          | Low      | Idempotent re-creation on next `BookkeepingTransaction.acquire()`; emit a one-line warning.                                          |
| RR-07 | A pre-commit hook that mutates files in the commit (e.g. a formatter) could leave the coordination worktree dirty between transaction commit and lock release.         | Med      | The transaction's commit step uses `safe_commit()` which does not re-stage post-hook changes. If a hook mutates files, the commit either includes the mutation (intended) or fails (caught by rollback). Documented in CHANGELOG. |

---

## Test plan summary

(Full test surface enumerated per work package in `tasks.md` after `/spec-kitty.tasks`.)

- Unit: `safe_commit(destination_ref=...)` happy path + HEAD-mismatch + missing-arg.
- Unit: `BookkeepingTransaction` context manager (acquire / append / commit / release / rollback paths).
- Unit: `WorkflowMutationPolicy.assert_allowed()` for protected-branch / non-protected / unknown-ref cases.
- Unit: `CoordinationWorkspace` create / reuse / teardown.
- Integration: 2-lane mission, parallel `implement` calls, verify event ordering (SC-02, SC-12).
- Integration: Forced pre-commit hook reject on coordination branch, verify SHA-256 of `status.events.jsonl` unchanged (NFR-001, SC-05/06).
- Integration: Run `implement` from a `main` checkout for a coordination-branch mission; verify no main commit, no rollback needed, byte-identical pre/post (SC-08).
- Integration: Run `implement` for a legacy mission (no coordination branch); verify pre-flight gate + rollback apply (SC-11).
- Integration: Full multi-lane → done → merge → verify lane code lands on target (SC-10).
- Integration: `finalize-tasks` from a `prep/` branch records `merge_target_branch: main` in WP frontmatter (SC-04).
- Integration: Implement/review terminal output enumerates every commit produced (SC-03).
- Stress: 20 concurrent `implement` calls, no interleaved partial writes (SC-12).
- Regression: Exact reproduction of issue #1348 sequence; verify it does not reproduce (SC-06).
- Architectural test (PR 3): forbid direct `safe_commit` imports from transactional modules.

---

## Out-of-band coordination

- **CHANGELOG entry** required for PR 1 (`safe_commit` signature change) and PR 2 (new coordination-branch topology, sparse-checkout policy).
- **Doctor command** (`spec-kitty doctor`) gains coordination-worktree health check and sparse-checkout drift detection.
- **No PyPI release until PR 2 lands.** PR 1 alone fixes the silent commit-target drift but does not yet route bookkeeping to a coordination branch.

---

## Next step

Run `/spec-kitty.tasks` to materialize this plan into work packages. Do not start implementation directly — work packages must be reviewed and finalized first.
