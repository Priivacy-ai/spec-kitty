---
work_package_id: WP03
title: 'Unify dispatch: canonical command + aliases + parity'
dependencies: []
requirement_refs:
- FR-004
- FR-005
- NFR-001
- NFR-002
tracker_refs: []
planning_base_branch: feat/mission-lifecycle-dispatch-drg-closeout
merge_target_branch: feat/mission-lifecycle-dispatch-drg-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/mission-lifecycle-dispatch-drg-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-lifecycle-dispatch-drg-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2839132"
history:
- at: '2026-06-13T16:37:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- src/specify_cli/cli/commands/dispatch.py
- tests/specify_cli/invocation/cli/test_dispatch_parity.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/dispatch.py
- src/specify_cli/cli/commands/do_cmd.py
- src/specify_cli/cli/commands/advise.py
- src/specify_cli/cli/commands/__init__.py
- src/specify_cli/invocation/modes.py
- tests/specify_cli/invocation/cli/test_dispatch_parity.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Unify dispatch: canonical command + aliases + parity

## ⚡ Do This First: Load Agent Profile

Load your assigned implementer profile (recommended `python-pedro`) via the profile-load skill —
governed context, not a bare name — before reading further.

## Objectives & Success Criteria

Expose `spec-kitty dispatch` over the existing single mechanism; keep do/ask/advise as byte-identical
first-class aliases; pin parity. **No router/executor/record semantics change.**

- One shared `_dispatch_impl` backs all four verbs.
- `spec-kitty dispatch --profile <p> "<req>"` opens a governed Op identical to the legacy path.
- do/ask/advise outputs, exit codes, JSON envelopes, and Op records are byte/contract-identical
  before vs after (NFR-001), pinned by tests.
- **C-002:** never a commit where the trio is broken — aliases land WITH dispatch, atomically.

## Context & Constraints

- Read: `plan.md` (IC-04, IC-05), `contracts/dispatch-parity.md` (binding), `research.md` (D-B1..D-B3).
- The mechanism already exists: `invocation/executor.py::ProfileInvocationExecutor.invoke()`.
  do (`do_cmd.py`) and advise+ask (`advise.py`) are thin wrappers; `advise.py` already centralizes via
  `_run_invoke()`, `do_cmd.py` does NOT — so there are TWO duplicated helper sets to unify.
- Mode is derived from the entry command in `invocation/modes.py::_ENTRY_COMMAND_MODE`
  (do/ask→task_execution, advise→advisory). Add a `dispatch`→task_execution entry. Do not change
  existing mode mappings.
- Op record path is `kitty-ops/<invocation_id>.jsonl` (from `invocation/writer.py::invocation_path`)
  — the parity test must source the path from there, not hard-code it.
- Preserve each verb's exact argument shape: `ask` keeps mandatory positional profile; `advise`
  keeps advisory mode + `-p`; `do` keeps optional `--profile` + router dispatch.

## Branch Strategy

- **Strategy**: execution worktree per computed lane (lanes.json)
- **Planning base branch**: feat/mission-lifecycle-dispatch-drg-closeout
- **Merge target branch**: feat/mission-lifecycle-dispatch-drg-closeout

## Subtasks & Detailed Guidance

### T011 – ATDD: parity tests first
- In `tests/specify_cli/invocation/cli/test_dispatch_parity.py`, write failing parity tests: for
  equivalent inputs, the Op record JSONL at `invocation_path(<id>)` is byte/contract-identical
  across the canonical command and its alias (except unique invocation_id + timestamps); assert mode
  mapping (do/ask/dispatch→task_execution, advise→advisory) and identical JSON envelopes + exit codes.

### T012 – Extract shared `_dispatch_impl`
- Unify the duplicated helpers (`_get_repo_root`, `_build_executor`, `_detect_actor`,
  `_render_rich_payload`, error-handling) from BOTH `do_cmd.py` and `advise.py` into one
  `_dispatch_impl(request, profile_hint, mode, json_output)`. Behavior-preserving.

### T013 – Canonical `dispatch` + alias rewire (atomic, C-002)
- Add `cli/commands/dispatch.py` with the canonical `dispatch` command calling `_dispatch_impl`.
  Rewire `do`/`ask`/`advise` to call `_dispatch_impl` with their fixed mode/arg shape. This MUST be
  one atomic commit — no intermediate state where a verb references a half-moved helper or the trio
  is unregistered.

### T014 – Mode entry + registration
- Add `dispatch`→`task_execution` to `_ENTRY_COMMAND_MODE` (`invocation/modes.py`). Register
  `dispatch` as a top-level command in `cli/commands/__init__.py`; keep do/ask/advise registrations.

## Test Strategy

- `pytest tests/specify_cli/invocation/cli/` (incl. the new parity test + existing `test_advise.py`)
  green. Diff-scoped ruff + mypy --strict on touched files (exit 0). Verify `spec-kitty do --profile
  … "x"` still works (C-002 smoke). Paste commands + exit codes into handoff.

## Definition of Done

- `dispatch` ships; do/ask/advise byte/contract-identical (parity tests green); mode mapping intact;
  ruff+mypy clean; the change is atomic; `spec-kitty do --profile` unbroken throughout.

## Risks

- Splitting the refactor across commits (breaks C-002). Changing an alias's observable behavior
  (breaks NFR-001). Touching router/executor/record semantics (out of scope).

## Reviewer Guidance

- Reviewer: `reviewer-renata`. Verify byte/contract parity against the real `kitty-ops/<id>.jsonl`
  path, atomicity (single commit, no broken window), and that no executor/router semantics changed.

## Activity Log

- 2026-06-13T16:57:08Z – claude:opus:python-pedro:implementer – shell_pid=2766284 – Assigned agent via action command
- 2026-06-13T17:14:28Z – claude:opus:python-pedro:implementer – shell_pid=2766284 – Ready: canonical spec-kitty dispatch over existing ProfileInvocationExecutor + byte-identical do/ask/advise aliases via shared _dispatch_impl. NFR-001 parity pinned by test_dispatch_parity.py (Op-record JSONL path from writer.invocation_path; mode mapping do/ask/dispatch->task_execution, advise->advisory; --json envelope; exit codes). C-002 atomic single commit (29dbcfc32); do --profile unbroken (smoke verified). Gates: pytest tests/specify_cli/invocation/cli/ = 122 passed; ruff exit 0; mypy --strict exit 0.
- 2026-06-13T17:16:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=2839132 – Started review via action command
- 2026-06-13T17:22:22Z – user – shell_pid=2839132 – Review PASS (renata): NFR-001 parity genuine (real persisted-JSONL), C-002 atomic single-commit, zero executor/router semantics drift, 122 tests green
