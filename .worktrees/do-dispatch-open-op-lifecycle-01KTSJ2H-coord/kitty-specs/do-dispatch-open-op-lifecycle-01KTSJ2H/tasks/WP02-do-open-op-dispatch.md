---
work_package_id: WP02
title: do Open-Op Dispatch
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude:fable:reviewer-renata:reviewer"
shell_pid: "36441"
history:
- '2026-06-10T20:15:38Z: created by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/do_cmd.py
- src/specify_cli/invocation/propagator.py
- tests/specify_cli/invocation/cli/test_do.py
- tests/specify_cli/invocation/test_propagator.py
- tests/specify_cli/invocation/test_propagator_policy.py
- tests/specify_cli/invocation/test_propagator_sync_gate.py
role: implementer
tags: []
---

# WP02 — `do` Open-Op Dispatch

## ⚡ Do This First: Load Agent Profile

Before reading further, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, and boundaries for the remainder of this work package.

## Objective

Make `spec-kitty do` an honest dispatch: open the Op, route, load governance, print the capsule with an explicit close contract — and **leave the Op open**. Add the SaaS propagator that `ask`/`advise` already have. Rebuild the propagator's envelope dicts from the v2 event models (envelope shape changes freely — decision 01KTSJEQANMNEV16WMSAJP6FR1; SaaS handlers are unimplemented, #1720/#1693).

## Context

- Spec: FR-001, FR-002, FR-008; NFR-001 (≤10% dispatch latency regression). Contract: `kitty-specs/do-dispatch-open-op-lifecycle-01KTSJ2H/contracts/cli-do-output.md` — treat its rich/JSON shapes as normative.
- Current behavior: `do()` (`src/specify_cli/cli/commands/do_cmd.py:100`) calls `executor.complete_invocation(payload.invocation_id, outcome="done")` at line ~153 immediately after `invoke()`, then prints `Op record written — commit it: git add kitty-ops/<id>.jsonl`. The auto-close comment claims write-integrity motivation; research.md R1 establishes the started-event write (exclusive create, `InvocationWriteError` → exit 1) already provides it.
- `do`'s executor builder (~lines 39-42) constructs `ProfileInvocationExecutor(router=router)` **without** the propagator; `ask`/`advise` (`src/specify_cli/cli/commands/advise.py:54-58`) include it. This is a known oversight from the single-shot era.
- Breaking change is sanctioned (C-001): no compat flag, CHANGELOG handled in WP06.

## Subtasks

### T006 — Remove auto-close

**Purpose**: `do` never writes a completed event.

**Steps**:
1. Delete the `complete_invocation(...)` call and its surrounding try/except plus the "single-shot" comment block (do_cmd.py ~lines 150-158).
2. Confirm `invoke()` error handling is untouched: `ProfileNotFoundError`, `RouterAmbiguityError`, `InvocationWriteError` paths still exit 1 with their structured messages and create no Op file on routing failure.
3. After this change a successful `do` leaves `kitty-ops/<id>.jsonl` containing exactly one started line (plus optional `glossary_checked`), uncommitted in the working tree (open Ops are never auto-committed — FR-012, enforced in WP03).

**Validation**: run `spec-kitty do "test" --json` in a scratch project; inspect the JSONL file: no `"event": "completed"` line.

### T007 — Wire the SaaS propagator

**Purpose**: parity with `ask`/`advise` (FR-008).

**Steps**:
1. Mirror the builder in `advise.py` (~54-58): construct the propagator and pass it — `ProfileInvocationExecutor(router=router, propagator=propagator)`. Reuse the same factory `advise.py` uses (import or extract a tiny shared builder if both files would otherwise duplicate; prefer importing the existing helper over creating a new module).
2. Propagation stays async/best-effort/sync-gated — no behavior changes inside `propagator.py` for the gate; only envelope shapes change (next step).
3. Update `_build_started_event_dict()` / `_build_completed_event_dict()` in `src/specify_cli/invocation/propagator.py` to build from `OpStartedEvent` / `OpCompletedEvent` — field set follows the v2 contract 1:1. Remove legacy-only fields. No idempotency-key kwarg changes to the client protocol.

**Validation**: propagator unit tests assert the new envelope field sets; sync-gate tests (`test_propagator_sync_gate.py`) still prove local-write-without-propagation when sync disabled.

### T008 — Close-contract block in rich output

**Purpose**: an agent following only the capsule can close correctly (Success Criterion 3).

**Steps**:
1. In `_render_rich_payload` flow (do_cmd.py), replace the commit-hint `console.print` (~lines 160-167) with the contract block:
   ```
   This Op is OPEN. After completing the work, close it with the real outcome:
     spec-kitty profile-invocation complete --invocation-id <id> --outcome <done|failed|abandoned> [--evidence <file>] [--artifact <path>] [--commit <sha>]
   Unclosed Ops are reported by `spec-kitty doctor ops` and swept to 'abandoned' when stale.
   ```
   (dim/styled to match existing capsule aesthetics; `<id>` interpolated).
2. Drop the `git add kitty-ops/...` hint entirely — close-time auto-commit (FR-012) makes it wrong advice.
3. The governance capsule itself (profile, action, confidence, invocation id, glossary warnings, governance context) is unchanged.

**Validation**: rich-output test asserts presence of "This Op is OPEN", the complete command with the real id, and absence of "git add kitty-ops".

### T009 — `status` + `close_contract` in JSON payload

**Purpose**: machine-readable contract for orchestrators (#1229 direction).

**Steps**:
1. Extend the `--json` payload (currently `payload.to_dict()`) with:
   ```json
   "status": "open",
   "close_contract": {
     "command": "spec-kitty profile-invocation complete --invocation-id <id> --outcome <done|failed|abandoned>",
     "outcomes": ["done", "failed", "abandoned"],
     "evidence_flag": "--evidence",
     "artifact_flag": "--artifact",
     "commit_flag": "--commit"
   }
   ```
   `<id>` interpolated with the real invocation id. Add at the do_cmd layer (or `InvocationPayload.to_dict()` if `ask`/`advise` should emit it too — they should: same open semantics; keep one implementation).
2. JSON mode includes no rich hint text (existing `test_json_output_omits_op_record_commit_hint` pattern carries over to the new block).

**Validation**: JSON test parses output, asserts `status == "open"` and the contract object's command contains the id.

### T010 — Rewrite `do` integration tests

**Purpose**: pin the new lifecycle.

**Steps**: rewrite `tests/specify_cli/invocation/cli/test_do.py`:
- successful `do` → exit 0, JSONL has started event only; no completed event; file untracked.
- rich output contains close contract; JSON output contains `status`/`close_contract`.
- routing failure → no Op file (unchanged).
- propagator invoked on started event when sync enabled (mock/spy, mirroring ask/advise tests); not invoked when disabled.
- NFR-001 verification: assert propagator submission is non-blocking — the spy records that `submit()` was called but `do` returns without awaiting delivery (e.g. a propagator stub that blocks on an event the test never sets must not delay command exit). This pins that adding the propagator is latency-neutral, which is the only latency-relevant change in this WP.
- remove/replace all assertions that expected `outcome: "done"` or the commit hint.

**Validation**: `.venv/bin/pytest tests/specify_cli/invocation -q` green; mypy/ruff clean.

## Branch Strategy

Planning base branch: `main`. Final merge target: `main`. Execution worktrees are allocated per computed lane from `lanes.json`. Implement via `spec-kitty agent action implement WP02 --agent <name>` (depends on WP01 being approved/done).

## Definition of Done

- [ ] `do` writes no completed event under any successful path; routing failures create no Op.
- [ ] Propagator wired into `do`; envelopes built from v2 models; async/sync-gate behavior unchanged.
- [ ] Rich + JSON outputs match `contracts/cli-do-output.md`; commit hint gone.
- [ ] Test suite rewritten and green; ≥90% coverage on changed code; mypy --strict + ruff clean.

## Risks & Reviewer Guidance

- **Latency (NFR-001)**: propagator construction must not block dispatch — verify it submits to the background executor exactly like ask/advise.
- **Shared payload changes**: if `close_contract` lands in `InvocationPayload.to_dict()`, `ask`/`advise` JSON output changes too — that is desired (same open semantics) but reviewer should confirm their tests were updated, not silenced.
- **Glossary inline observation** (do_cmd.py ~169-175) must keep working after the code above it is removed — it reads events by invocation_id and is lifecycle-agnostic.

## Activity Log

- 2026-06-10T21:10:00Z – claude:fable:python-pedro:implementer – shell_pid=32762 – Assigned agent via action command
- 2026-06-10T21:19:13Z – claude:fable:python-pedro:implementer – shell_pid=32762 – Ready for review: open-Op dispatch, propagator wired, close contract in rich+JSON
- 2026-06-10T21:19:42Z – claude:fable:reviewer-renata:reviewer – shell_pid=36441 – Started review via action command
- 2026-06-10T21:23:44Z – user – shell_pid=36441 – Review passed: do no longer auto-closes (no complete_invocation in do_cmd.py); rich+JSON close contract matches cli-do-output.md exactly; propagator wired with v2 1:1 envelopes incl. governance_context_available/mode_of_work/closed_by and preserved policy gates; NFR-001 non-blocking test is genuine (blocked worker, <10s exit); executor.py edit additive-only, invoke/complete_invocation untouched; 346 invocation tests pass, ruff clean, mypy clean on WP02 surfaces, 59 pre-existing errors confirmed elsewhere
