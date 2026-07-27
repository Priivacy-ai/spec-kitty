---
work_package_id: WP03
title: '#2649 — degod _json_safe_output + _run_recover_mode'
dependencies:
- WP02
requirement_refs:
- C-008
- FR-003
- NFR-001
- NFR-002
- NFR-004
tracker_refs:
- '2649'
planning_base_branch: mission/2533-pr-bound-coord-claim-precondition
merge_target_branch: mission/2533-pr-bound-coord-claim-precondition
branch_strategy: Planning artifacts for this mission were generated on mission/2533-pr-bound-coord-claim-precondition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/2533-pr-bound-coord-claim-precondition unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2677586"
shell_pid_created_at: "1784122054.95"
history:
- at: '2026-07-15T07:36:38Z'
  actor: claude
  note: Carved from IC-02 — the heavy S3776 targets, separated from the C-006 symbol (WP02).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_implement_json_safe_output.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/implement.py
- tests/specify_cli/cli/commands/test_implement_json_safe_output.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration.
You are the **implementer**.

## Objective

Reduce the Sonar S3776 cognitive complexity of `_json_safe_output` (`implement.py:135-177`,
≈33 — the worst offender) and `_run_recover_mode` (`implement.py:856`, ≈24) by extracting
module-private helpers, **behavior-preserving**. Characterize the implicit invariants FIRST.

## Context — READ BEFORE CODING

- **Brownfield / characterization-first (DM-D, NFR-002):** `_json_safe_output` has several
  non-obvious, extraction-fragile invariants — pin them before touching:
  - `console._file = None` reset (`:175`) AND `console.quiet` save/restore across the
    `finally` (`:141,:146,:171`) — two separate resets.
  - **Dual exception arms differ by design**: `typer.Exit` is re-raised **verbatim**
    (`:162`); a bare `Exception` is **wrapped** in `typer.Exit(1)` (`:169`). Do NOT merge
    them (same #2576-class trap as `_mt_uncheck`).
  - Summary shape: last-20 **non-blank** rstripped lines (`:156-158`) AND the
    `getattr(exc,"exit_code",1)` guard that suppresses the JSON payload on exit_code 0
    (`:155`).
- `_run_recover_mode`: pin its current observable output/branch behavior before extraction.
- **C-008 / NFR-004:** extracted helpers stay module-private; no net-new public symbol.
- Gate note: both already pass `ruff C901`; the target is S3776 (advisory-post-merge). The
  enforceable local acceptance is extraction + per-helper tests + behavior preservation.
- **Do NOT touch `_resolve_bookkeeping_transaction_identifiers`** — that is WP02's frozen
  surface (C-006).

## Subtasks

### T010 — Characterization tests: _json_safe_output

Create `tests/specify_cli/cli/commands/test_implement_json_safe_output.py` pinning:
1. `console._file=None` reset and `console.quiet` restored to its prior value.
2. `typer.Exit` re-raised verbatim; a bare `Exception` becomes `typer.Exit(1)`.
3. exit_code-0 payload suppression + the last-20-non-blank-lines summary.

**Validation**: all pass against the current function.

### T011 — Characterization tests: _run_recover_mode

`_run_recover_mode` (≈24 cognitive complexity) has ~4 output branches, each with a
**`json_output` vs console** dual rendering — that repeated dual path is the extraction-fragile
invariant a vague floor lets collapse silently. Pin each branch explicitly (matching T010's
specificity), BEFORE extraction:
1. Error path: `TaskCliError`/`typer.Exit` → the json-error emit **vs** `raise typer.Exit(1)`.
2. No-recovery-needed path (empty `needs_recovery`): the json payload **vs** the console
   "no crashed sessions" message.
3. Recovery-needed path (non-empty): the recovery table build + the final json payload **vs**
   the console recovery-complete summary.
Assert both the `--json` and the console rendering for each branch.

**Validation**: all three branch pairs pass against current code.

### T012 — Extract helpers for _json_safe_output

1. Decompose into small `_`-prefixed helpers (e.g. quiet/file guard, exception routing,
   summary builder) to lower S3776, preserving every T010 invariant.

**Validation**: T010 green; behavior identical.

### T013 — Extract helpers for _run_recover_mode

1. Decompose into module-private helpers to lower S3776, preserving T011 behavior.

**Validation**: T011 green.

### T014 — Gate clean

1. `ruff` + `mypy --strict` zero new issues; full `implement` suite green.

**Validation**: clean gate.

## Branch Strategy

Planning branch / final merge target: **mission/2533-pr-bound-coord-claim-precondition**.
Lane A, after WP02.

## Definition of Done

- `_json_safe_output` + `_run_recover_mode` decomposed, S3776 reduced, behavior preserved
  (FR-003, NFR-002).
- Characterization tests (T010/T011) green and enduring.
- No net-new public symbol (C-008, NFR-004); `ruff` + `mypy --strict` clean (NFR-001).

## Risks & Reviewer Guidance

- The dual-exception arms of `_json_safe_output` are the classic merge trap — reviewer must
  confirm `typer.Exit` still passes through un-wrapped after extraction.
- Confirm no change to `_resolve_bookkeeping_transaction_identifiers` (WP02's surface).

## Activity Log

- 2026-07-15T13:11:36Z – claude:sonnet:python-pedro:implementer – shell_pid=2624330 – Started implementation via action command
- 2026-07-15T13:27:00Z – claude:sonnet:python-pedro:implementer – shell_pid=2624330 – Ready for review: json_safe/recover degod, dual-exception + branch invariants pinned
- 2026-07-15T13:27:37Z – claude:opus:reviewer-renata:reviewer – shell_pid=2677586 – Started review via action command
- 2026-07-15T13:30:46Z – user – shell_pid=2677586 – Review passed: behavior-preserving degod. Dual-exception arms PRESERVED (typer.Exit re-raised verbatim via bare raise + exit_code-0 payload suppression via getattr guard; bare Exception wrapped in fresh typer.Exit(1) from exc; arms NOT merged). console._file=None + console.quiet save/restore both in finally. last-20-non-blank-lines summary preserved. _run_recover_mode 4 branches byte-for-byte faithful incl. (TaskCliError,typer.Exit)+raise-from-None error arm and json-omits-contexts_recreated asymmetry. T010/T011 are real characterization tests (invoke production, not synthetic). 45 tests green (incl WP01/WP02). ruff+mypy --strict clean. All 10 helpers _-prefixed (no net-new public symbol, C-008/NFR-004); Callable[...,Any] is annotation-only. Frozen WP01/WP02 surfaces untouched. Scope = implement.py + new test only.
