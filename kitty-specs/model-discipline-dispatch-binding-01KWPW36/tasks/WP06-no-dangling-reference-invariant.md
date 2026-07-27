---
work_package_id: WP06
title: Durable no-dangling-reference invariant
dependencies:
- WP05
requirement_refs:
- FR-009
tracker_refs:
- '2364'
planning_base_branch: design/model-discipline-dispatch-2364
merge_target_branch: design/model-discipline-dispatch-2364
branch_strategy: Planning artifacts for this mission were generated on design/model-discipline-dispatch-2364. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/model-discipline-dispatch-2364 unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
phase: Phase 1 - Implementation
assignee: ''
agent: "claude"
shell_pid: '661274'
history:
- at: '2026-07-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_charter_references_resolve.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_charter_references_resolve.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Durable no-dangling-reference invariant

## Load Agent Profile (python-pedro)

Use the `/ad-hoc-profile-load` skill to load the `python-pedro` agent profile (role: `implementer`) before doing any work, and behave according to its guidance while executing this prompt.

## Objectives & Success Criteria

- Add a refactor-stable test asserting that EVERY charter `→ \`token\`` reference, across ALL sections of `charter.md` (not just Standing Orders), resolves to a `references.yaml` id-suffix.
- SC-004: the test fails on pre-fix HEAD (both `model_task_routing`/`model-task-routing` and `autonomous-operation-protocol` dangling) and passes post-WP05.
- Guards against the section-level dangling-reference class recurring (the existing "all references resolve" guarantee only covered the Standing Orders section).

## Context & Constraints

- Source of truth: `kitty-specs/model-discipline-dispatch-binding-01KWPW36/spec.md` FR-009, SC-004; `plan.md` IC-06; `tasks.md` WP06 section.
- Depends on **WP05** — this WP's test goes green once WP05's tactic/DRG edges land; it must be RED on pre-fix HEAD.
- **Load-bearing trap — refactor-stable, no literal token list**: parse `→ \`token\`` prose across ALL charter.md sections and resolve each match against `references.yaml` id-suffixes programmatically. Do NOT hardcode/pin a literal list of expected tokens — that would make the test brittle to future charter edits and would not actually guard the class of bug (a new dangling reference added later must also be caught).
- Exclude non-backticked prose — only tokens that appear as `→ \`token\`` (arrow followed by a backticked identifier) count as references to resolve.
- "Resolves" means: the token, once normalized to its expected id form, matches a `references.yaml` entry that is itself reachable via the DRG (not merely string-present) — mirror the resolution semantics already proven correct by WP05's `test_model_task_routing_resolves.py`.
- **Red-first procedure (this WP depends on WP05, so the tokens already resolve on its branch — red-first is unobservable through the normal flow)**: capture RED by running the new test against the pre-WP05 base (e.g. `git stash` WP05's `graph.yaml`/`charter.md` edits, or run on the mission base branch before WP05 landed); RECORD the pre-fix failure (both tokens unresolved); then confirm GREEN on the integrated branch.
- Keep `ruff`/`mypy` clean.

## Subtasks

- [ ] T030 [FR-009] `tests/architectural/test_charter_references_resolve.py`: parse all backticked-after-`→` tokens across every charter.md section; assert each resolves to a `references.yaml` id-suffix. Exclude non-backticked prose.
- [ ] T031 confirm RED on pre-fix HEAD (both tokens absent) + GREEN post-WP05; refactor-stable (no literal token list). Since this WP depends on WP05, capture RED by running the test against the pre-WP05 base (e.g. `git stash` WP05's `graph.yaml`/`charter.md` edits, or run on the mission base branch before WP05 landed); RECORD the pre-fix failure (both tokens unresolved); then confirm GREEN on the integrated branch.
- [ ] T032 `ruff`/`mypy` clean.

## Branch Strategy

- **Strategy**: Planning artifacts are generated on design/model-discipline-dispatch-2364; completed changes merge back there.
- **Planning base branch**: `design/model-discipline-dispatch-2364`
- **Merge target branch**: `design/model-discipline-dispatch-2364`

## Definition of Done

- [ ] `test_charter_references_resolve.py` parses `→ \`token\`` references across every charter.md section (not a hardcoded subset) and asserts each resolves to a `references.yaml` id-suffix.
- [ ] Confirmed RED on pre-fix HEAD (both tokens dangling) and GREEN once WP05 lands.
- [ ] Test is refactor-stable: no literal token list pinned; a future new dangling reference would still be caught.
- [ ] `ruff`/`mypy` clean.
- [ ] No changes outside `owned_files`.

## Activity Log

- 2026-07-04T18:56:58Z – claude – shell_pid=661274 – Moved to for_review
- 2026-07-04T18:57:09Z – user – shell_pid=661274 – APPROVE (opus, uv-run): red-first genuine; see adversarial-review.
