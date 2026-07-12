---
work_package_id: WP06
title: plan scaffold-block ergonomics — distinct non-error result
dependencies: []
requirement_refs:
- FR-009
- NFR-005
tracker_refs:
- '2566'
planning_base_branch: feat/loop-friction-quickwins-2
merge_target_branch: feat/loop-friction-quickwins-2
branch_strategy: Planning artifacts for this mission were generated on feat/loop-friction-quickwins-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/loop-friction-quickwins-2 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-loop-friction-quickwins-2-01KXBWA4
base_commit: 697c49ccd4173b397df01cf7bafe0de4af4000c4
created_at: '2026-07-12T21:35:19.498940+00:00'
subtasks:
- T021
- T022
- T023
- T024
phase: Ergonomics
agent: "claude"
shell_pid: '1484725'
shell_pid_created_at: '1783892074.19'
history:
- at: '2026-07-12T19:30:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-06; specify twin already shipped — plan side + consumers only)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/mission_setup_plan.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- src/specify_cli/missions/_substantive.py
- src/doctrine/missions/mission-steps/software-dev/plan/prompt.md
- tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 — plan scaffold-block ergonomics

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objectives & Success Criteria

The first happy-path `setup-plan` scaffold write returns a non-error state — **mirroring the shipped specify
twin: `result: "success"` + a `scaffold_only: true` (awaiting-content) flag** — not `blocked`; a
populated-but-insufficient plan still returns `blocked`; a substantive committed plan still `success`
(no flag). The source prompt reads the flag instead of treating the first call as an error.

- **SC (FR-009)**: fresh mission → first `setup-plan` returns `result: success` + `scaffold_only: true` (phase_complete false), NOT `blocked`; 0 write-then-discard round-trips to advance.
- **SC (true-positive, NFR-005)**: a populated-but-insufficient plan still returns `blocked`.

## Context & Constraints

Bug (#2566): `_emit_setup_plan_result` (`mission_setup_plan.py:625`; return `"success"/"blocked"` @ `:646`)
returns `"success"`/`"blocked"` only — a freshly-scaffolded template is non-substantive by construction, so
the first happy-path call ALWAYS reads `blocked`. Root gate is #846 (closed) — correct, but its UX cost
lands on every mission.

**CRITICAL design correction (renata HIGH + alphonso D2) — mirror the twin, do NOT invent a new engine result:**
- The specify twin `mission_create` already returns **`result: "success"` + a separate `scaffold_only: True`
  flag** (`mission_create.py:347`), NOT a new result value. Do the SAME here.
- Do **NOT** emit `result: "scaffolded"` and do **NOT** edit `engine.py`. The `next` engine switches on the
  `next --result` flag whose vocabulary is FIXED — `_VALID_RESULTS = ("success","failed","blocked")` at
  `next_cmd.py:43` — a different contract from the setup-plan JSON. A new `result` value would be rejected
  there (`next_cmd.py:43`) and mislabeled failed (`next_cmd.py:219`). `engine.py`/`next_cmd.py` are therefore
  NOT owned by this WP.
- **Consumer = the source prompt only**: `src/doctrine/missions/mission-steps/software-dev/plan/prompt.md`
  must stop treating the first `setup-plan` call as an error and read `scaffold_only`. Agent copies
  regenerate via `spec-kitty upgrade` (do not hand-edit them).
- This needs a NET-NEW predicate distinguishing a pristine template scaffold from populated-but-insufficient
  content (none exists in `missions/_substantive.py` — only `is_substantive`/`describe_technical_context_gap`).

**SSOT (alphonso D2)**: define ONE token for the flag (`scaffold_only`, matching the twin) — do not introduce
a `scaffolded`-vs-`awaiting_content` split. Extract a pure helper `_resolve_plan_result_state(is_substantive,
is_pristine, committed) -> (result, scaffold_only)` (pedro campsite) so the emitter stays flat and T024 has a
direct unit target.

**KEEP**: populated-but-insufficient still `blocked` (K-1/NFR-005). `is_substantive` semantics unchanged.

Plan: IC-06. Research: R-09. Contract: C-D1.

## Branch Strategy

- **Planning base branch / Merge target**: feat/loop-friction-quickwins-2

## Subtasks & Detailed Guidance

### Subtask T021 — Pristine-vs-insufficient predicate

- **Steps**: Add a predicate near `missions/_substantive.py` that detects a pristine, just-scaffolded
  template (e.g. content byte-equal to the copied template, or no populated Technical Context AND unmodified
  scaffold markers) — distinct from populated-but-insufficient.
- **Files**: `src/specify_cli/missions/_substantive.py`.

### Subtask T022 — Emit success + scaffold_only (mirror the twin)

- **Steps**: Add the pure helper `_resolve_plan_result_state(is_substantive, is_pristine, committed)`
  returning `(result, scaffold_only)`. In `_emit_setup_plan_result`/`_commit_plan_if_substantive`, when the
  pristine predicate holds and nothing substantive is committed yet, return `result: "success"` +
  `scaffold_only: True` (phase_complete False) — exactly like `mission_create`; keep `blocked` for
  populated-but-insufficient; keep `success` (no `scaffold_only`) for substantive-committed. Do NOT add a new
  `result` string.
- **Files**: `mission_setup_plan.py`.

### Subtask T023 — Update the ONE consumer (source prompt)

- **Steps**: Update `src/doctrine/missions/mission-steps/software-dev/plan/prompt.md` so the workflow reads
  `scaffold_only` and does NOT treat the first `setup-plan` call as an error/blocked. Do NOT edit `engine.py`
  or `next_cmd.py` (the setup-plan `result` does not flow through `next --result`). Note in the PR that agent
  copies regenerate via `spec-kitty upgrade` (do not commit hand-edited agent-dir copies).
- **Files**: `src/doctrine/missions/mission-steps/software-dev/plan/prompt.md`.

### Subtask T024 — Red-first tests

- **Steps**: In `test_mission_setup_plan_phases.py`: pristine scaffold → `result: success` + `scaffold_only:
  True`, phase_complete False (NOT `blocked`); populated-but-insufficient → `blocked`; substantive committed
  → `success` without `scaffold_only`. Add a direct unit test of the pristine predicate (byte-equal-to-template
  vs populated-but-insufficient boundary) and of `_resolve_plan_result_state`.
- **Files**: `tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py`.

## Definition of Done

- New pristine predicate + `_resolve_plan_result_state` helper; pristine → `success`+`scaffold_only:true`; `blocked`/`success` preserved; source prompt reads the flag. NO `engine.py`/`next_cmd.py` edit.
- Tests pass (incl. direct predicate + helper units); terminology guard green (prompt.md is under a scanned root — use canonical `Mission`).
- `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py -q` green; `ruff` + `mypy` clean.

## Risks & Reviewer Guidance

- **Risk**: reintroducing a new `result: "scaffolded"` value — reviewer REJECTS it; mirror the twin's `success`+`scaffold_only` (the setup-plan `result` does not flow through `next --result`'s fixed `_VALID_RESULTS`).
- **Risk**: pristine predicate too loose → an insufficient plan reads as `scaffold_only` — reviewer verifies T024's insufficient→blocked case.
- **Note (OUT follow-up)**: `next_step`/`next_cmd` already carry a `# noqa: C901` over-ceiling suppression — a de-god is out of scope here (filed as a follow-up).

## Activity Log

- 2026-07-12T21:56:42Z – claude – shell_pid=1484725 – reviewer-renata APPROVE: mirrors specify twin (success+scaffold_only), byte-equality pristine sound, no engine.py edit
- 2026-07-12T21:56:56Z – claude – shell_pid=1484725 – reviewer-renata APPROVE
