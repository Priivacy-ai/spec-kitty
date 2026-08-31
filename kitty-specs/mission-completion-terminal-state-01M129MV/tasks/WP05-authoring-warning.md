---
work_package_id: WP05
title: Advisory authoring-time un-terminable-work warning
dependencies: []
requirement_refs:
- FR-007
- FR-008
planning_base_branch: fix/mission-completion-terminal-state
merge_target_branch: fix/mission-completion-terminal-state
branch_strategy: Planning artifacts for this mission were generated on fix/mission-completion-terminal-state. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-completion-terminal-state unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-completion-terminal-state-01M129MV
base_commit: 8c9c5d361da36b5f12a56d48dc848327a17646d8
created_at: '2026-08-28T05:33:05.751918+00:00'
subtasks:
- T017
- T018
- T019
- T020
phase: Phase 2 - Authoring prevention (independent)
history:
- at: '2026-08-28T04:51:39Z'
  actor: system
  action: Authored from plan.md WP-E after post-spec squad (F6 detection signal)
- at: '2026-08-28T05:30:00Z'
  actor: system
  action: Reworked after post-tasks squad — own tasks.py wiring, trigger/positive reconcile, real-repo negatives, test pkg __init__ (renata HIGH, pedro/paula MEDIUM)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tasks_authoring/
create_intent:
- src/specify_cli/tasks_authoring/__init__.py
- src/specify_cli/tasks_authoring/post_integration_warning.py
- tests/specify_cli/tasks_authoring/__init__.py
- tests/specify_cli/tasks_authoring/test_post_integration_warning.py
- tests/specify_cli/tasks_authoring/fixtures/README.md
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/tasks_authoring/**
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/tasks_authoring/**
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3590
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Apply its initialization, boundaries, directives, and tactics. State which you applied, then begin.

## Objective

Warn at authoring time when a work package's acceptance criteria can only be satisfied
**post-integration** — the #3590 trap, caught at its source. **Advisory only: it never blocks
authoring** (FR-008). **Independent** of WP01–WP04. No structured post-integration signal exists
(`ownership/models.py` has only `code_change`/`planning_artifact`), so the detector keys on an
enumerable trigger-phrase set validated against a **fixed labeled corpus** (post-spec squad **F6**).
A structured `completion_kind` field is out of scope (#3550, C-003).

> **Post-tasks squad corrections:**
> - **Wiring site (pedro/paula):** the `spec-kitty agent tasks check-terminability` subcommand
>   registers in `src/specify_cli/cli/commands/agent/tasks.py` (the `agent tasks` typer app,
>   mounted at `agent/__init__.py:24`) — now in owned_files. Do **not** touch `mission_finalize.py`
>   (C-005). Referencing it from the tasks command template under
>   `packs/built-in/missions/mission-steps/.../tasks/` is a second small out-of-map wiring touch —
>   record a one-line rationale if you make it.
> - **Trigger/positive reconcile (renata HIGH):** two required positive fixtures ("enable the real
>   system", "prove it with controls") contain **no phrase from the initial trigger set** — reconcile
>   them (make the positives carry genuine post-integration phrasing, or extend the trigger set AND add
>   negatives proving the broader triggers don't over-fire on ordinary code work).
> - **Non-self-serving corpus (renata HIGH):** draw a fraction of the **negative** fixtures from **real
>   existing WP files in this repo** (ordinary code-change WPs that mention CI/merge), not only
>   hand-authored strawmen.

## Context

- Contract: [../contracts/authoring-warning.contract.md](../contracts/authoring-warning.contract.md).
  Decisions: [../research.md](../research.md) R6. Spec FR-007/FR-008/SC-003.

## Subtasks

### T017 — Detector module
New `src/specify_cli/tasks_authoring/post_integration_warning.py` (+ `__init__.py`): pure function
taking a work package's acceptance-criteria / subtask text → warning records
`{wp_id, matched_phrase, criterion_excerpt}` for matches against an enumerable, versioned trigger set
(e.g. "after merge", "post-merge", "on a branch the forge will run", "in CI once enabled",
"consecutive runs", "merge-blocked-when-absent"). No I/O in the matcher. Ensure the set actually covers
the positive corpus (T019) without over-firing on the negatives.

### T018 — Advisory surface (never blocks)
Register `spec-kitty agent tasks check-terminability --mission <slug> --json` in
`cli/commands/agent/tasks.py`, invoking the detector and printing warnings naming the WP + matched
phrase, with guidance to re-home the content to a tracked post-merge obligations document. It MUST NOT
refuse or fail authoring (FR-008). Optionally reference it from the tasks command template
(record rationale). `mission_finalize.py` stays untouched (C-005).

### T019 — Labeled corpus fixtures (self- + non-self-sourced)
`tests/specify_cli/tasks_authoring/fixtures/` (+ `tests/specify_cli/tasks_authoring/__init__.py`):
**positive** fixtures (the #3590 shapes) that MUST warn — reconciled with the trigger set;
**negative / adversarial-near-miss** fixtures that MUST NOT warn, including at least a couple drawn
from **real existing repo WP files** (ordinary code WPs mentioning CI/merge). Add a `README.md`
documenting the corpus as the oracle and its path.

### T020 — Tests
`tests/specify_cli/tasks_authoring/test_post_integration_warning.py` (declare `pytestmark`): 100%
recall on the positive fixtures, 0 false positives on the negatives (SC-003, measured against the
fixed corpus); plus an advisory test proving authoring/`check-terminability` completes successfully
(exit 0) when the warning fires.

## Branch Strategy

Planning + merge target: `fix/mission-completion-terminal-state`. Worktree per `lanes.json`.

## Definition of Done

- Detector + `check-terminability` subcommand exist; warning fires on positives, silent on negatives
  (incl. real-repo negatives), never blocks.
- Corpus committed with README; test pkg has `__init__.py` + `pytestmark`; T020 passes; `ruff` + `mypy`
  clean on owned files; `mission_finalize.py` untouched.

## Risks / Reviewer guidance

- The false-positive fixtures (especially the real-repo ones) are the point — reject a detector that
  warns on ordinary CI-mentioning code work.
- Confirm authoring still succeeds when the warning fires (FR-008); a blocking implementation is wrong.
- Reject a trigger set reverse-engineered to the corpus that would over-fire in the wild (renata).
