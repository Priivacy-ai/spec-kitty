# Research: Do Dispatch Open-Op Lifecycle

**Date**: 2026-06-10 · **Mission**: do-dispatch-open-op-lifecycle-01KTSJ2H

## R1 — Why `do` auto-closes today, and what removing it breaks

**Decision**: Remove the auto-close (`do_cmd.py:153`) outright; `do` returns with an open Op like `ask`/`advise`.

**Rationale**: The auto-close was added so "completion write failures cannot masquerade as successful JSON" (comment at `do_cmd.py:150`) — a write-integrity concern, not a semantic one. The same integrity is preserved by the started-event write, which already uses exclusive-create and fails loudly (`InvocationWriteError` → exit 1). Nothing else in the codebase depends on `do` Ops being closed: the auto-commit path triggers only on completed records, so open `do` Ops simply remain untracked working-tree files — exactly the visible-orphan behavior FR-012 wants. Grep confirmed no consumer asserts `do` produces a completed event except `tests/specify_cli/invocation/cli/test_do.py`, which gets rewritten.

**Alternatives considered**: A `--single-shot` compat flag — rejected by user (C-001, pre-release, no transition obligations).

## R2 — Schema split shape

**Decision**: Replace the dual-purpose frozen `InvocationRecord` with two Pydantic v2 frozen models: `OpStartedEvent` (all dispatch-context fields required or meaningfully defaulted; `event: Literal["started"]`) and `OpCompletedEvent` (`event: Literal["completed"]`, required `invocation_id`, `completed_at`, `outcome: Literal["done","failed","abandoned"]`, `closed_by: Literal["agent","doctor_sweep"]`, optional `evidence_ref`). Completed events serialize only their own fields — no started-only fields defaulted to `""`/`"unknown"`.

**Rationale**: The current model makes the #1810 "unreadable record" failure valid by construction: a completed event with blank `action`, `actor: "unknown"`, `outcome: null` passes validation. Distinct models make the invalid state unrepresentable. The JSONL file remains the unit of readability (FR-005): started + completed lines in one file tell the whole story.

**Alternatives considered**: (a) Single model with conditional validators per event type — rejected: validators encode the same split with worse types and no mypy help. (b) Required-outcome-only patch to the existing model — rejected: still serializes misleading blank started fields on completed lines.

## R3 — SaaS envelope compatibility

**Decision**: Envelope changes shape freely with the new event models (decision 01KTSJEQANMNEV16WMSAJP6FR1, resolved by user).

**Rationale**: SaaS-side `OpStarted`/`OpCompleted` handlers are not implemented (#1720 pending, blocked by #1693 OfflineQueue). No consumer exists; a wire-compat shim would preserve a contract nobody reads. CLI behavior locks first; SaaS adopts the new shape when its ingestion lands.

**Alternatives considered**: Translate-at-boundary shim — rejected as dead code until #1720, and it would freeze the bad schema into the contract.

## R4 — Stale sweep semantics and threshold

**Decision**: `doctor ops` stays report-all by default. New `--close-stale` closes open Ops whose started_at is older than `--threshold` hours (default 24; `0` = close all) with `outcome=abandoned`, `closed_by=doctor_sweep`, via the same `complete_invocation` path (so idempotency, evidence gating, and close-time auto-commit apply uniformly). Concurrent manual close → sweep catches `AlreadyClosedError` and reports it as already-closed, exit 0.

**Rationale**: The threshold protects genuinely in-flight work from being closed underneath an active agent; nothing escapes permanently because every orphan eventually crosses the threshold (user-confirmed design). Routing sweep closes through the executor avoids a second close implementation drifting from the canonical one.

**Alternatives considered**: Direct file append in doctor module — rejected: duplicates lifecycle logic and skips auto-commit. Lock-file "heartbeat" for in-flight detection — rejected as over-engineering for a 24 h default.

## R5 — Hook surface feasibility (session-start listing + Stop reminder)

**Decision**: Both are in scope for Claude Code. `ClaudeCodeHookRegistrar` (`src/specify_cli/session_presence/hooks/claude_code_hook.py`) manages `.claude/settings.json` hook entries idempotently for `SessionStart`; the registrar is generalized to also register a `Stop` entry. Session-start output (`spec-kitty session-start`) appends an open-Ops section (id, age, close command) when orphans exist; the Stop hook runs a lightweight `spec-kitty doctor ops` check that prints a reminder when open Ops exist and exits 0 always (never blocks the host).

**Rationale**: FR-009 conditioned the Stop reminder on "no new harness work" — the registrar pattern, atomic settings write, and CLI plumbing all exist; the extension is parameterizing the hook key. Other harnesses (18) rely on capsule text + skill pack this mission (C-003).

**Alternatives considered**: Session-start only — kept as fallback if Stop-event payload constraints surface during implementation; the spec already permits documenting Stop as a follow-up.

## R6 — Legacy record migration strategy

**Decision**: New upgrade migration scans `kitty-ops/*.jsonl` (excluding `ops-index.jsonl`, `lifecycle.jsonl`, `propagation-errors.jsonl`). Per file: parse lines; old-schema started events map 1:1 to `OpStartedEvent`; old completed events map to `OpCompletedEvent` with `outcome` preserved (or `abandoned` when null) and `closed_by="agent"`; link/glossary events pass through unchanged. Files whose started event is unparseable or lacks `invocation_id`/`profile_id` are deleted. Rewrite is atomic (temp file + replace). Idempotency: new-schema files are recognized (completed events carry `closed_by`) and skipped.

**Rationale**: User-confirmed "B or delete — very few are in the wild and even fewer are precious." Rewrite-in-place is the sole sanctioned exception to the append-only contract (C-004) and runs once under the migration framework's detect/apply pattern.

**Alternatives considered**: Read-time tolerance of both schemas forever — rejected: permanent dual-parse complexity for a handful of disposable records.

## R7 — Output contract for orchestrators (JSON mode)

**Decision**: `do --json` payload gains a `close_contract` object: `{"command": "spec-kitty profile-invocation complete --invocation-id <id> --outcome <done|failed|abandoned>", "outcomes": ["done","failed","abandoned"], "evidence_flag": "--evidence", "status": "open"}` alongside the existing fields. Rich output replaces the "Op record written — commit it" hint with the close instruction (commit happens automatically at close per FR-012, so the manual `git add` hint is dropped).

**Rationale**: Success criterion 3 — an agent following only the printed capsule must close correctly. JSON consumers (orchestrator-api, #1229 direction) need the contract machine-readable, not parsed from prose.

**Alternatives considered**: Keep the commit hint — rejected: close-time auto-commit (FR-012) makes it wrong advice (the record changes again at close).
