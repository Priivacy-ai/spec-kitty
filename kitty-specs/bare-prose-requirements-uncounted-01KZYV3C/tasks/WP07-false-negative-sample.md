---
work_package_id: WP07
title: False-Negative Sample + Broadened-Predicate Re-Verification
dependencies:
- WP03
requirement_refs:
- C-008
- FR-005
planning_base_branch: pr/bare-prose-requirements-uncounted
merge_target_branch: pr/bare-prose-requirements-uncounted
branch_strategy: Planning artifacts for this mission were generated on pr/bare-prose-requirements-uncounted. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/bare-prose-requirements-uncounted unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
phase: Phase 3 - Consumers (parallel with WP06, after WP05, informational)
history:
- at: '2026-08-14T02:50:21Z'
  actor: system
  action: Prompt authored during tasks-authoring pass (not run via /spec-kitty.tasks)
agent_profile: ''
authoritative_surface: src/specify_cli/requirement_mapping.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/requirement_mapping.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – False-Negative Sample + Broadened-Predicate Re-Verification

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`, or select via `spec-kitty agent profile list` for an
`implement`-typed WP; this is a measurement/documentation task, not a production
behaviour change.

---

## Objectives & Success Criteria

Implement IC-07 (plan.md): a throwaway measurement — NOT shipped production code —
recording the false-negative side of the C-008 disposition (real bare-prose
`C-XXX`/`FR`/`NFR` items the current detector misses, specifically the
`C-XXX`-under-`### Constraints`-heading case), plus a re-verification of the
broadened-predicate false-positive figure plan.md already measured once (PLAN-GOV-002:
5/368 = 1.36%, zero true positives).

Success: both figures — the false-negative sample count and the re-verified
broadened-predicate FP rate — are recorded in `requirement_mapping.py`'s module
docstring alongside WP03's shipped 9/368 figure.

## Context & Constraints

- **Strictly informational — not a shipping gate (Story 4 AC4).** This WP must NOT
  modify `_is_requirement_heading` or any production blocking-scope decision. C-008's
  disposition (b) is already settled in plan.md — do not reopen it.
- Read plan.md's "C-008 decision" section (the full PLAN-GOV-002 measurement narrative)
  before starting — reuse its documented method (corpus scan with the heading predicate
  broadened to also match "constraint", read-only, not committed to production code).
- Read spec.md's Edge Cases entry on "The Constraints-heading blind spot" for the exact
  framing this measurement must address.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `pr/bare-prose-requirements-uncounted`;
  completed changes must merge back into `pr/bare-prose-requirements-uncounted`
  (base `op/3394-requirement-citation-scope` @ `ab15225ea`).
- **Planning base branch**: `pr/bare-prose-requirements-uncounted`.
- **Merge target branch**: `pr/bare-prose-requirements-uncounted`.

## Subtasks & Detailed Guidance

### Subtask T034 [P] – False-negative corpus sample

- **Purpose**: Measure the under-firing side of the C-008 scope decision.
- **Steps**: Write a corpus-scan helper (script or test under `tests/` or `scripts/`,
  implementation's choice) that samples `kitty-specs/*/spec.md` for genuine bare-prose
  `FR-`/`NFR-`/`C-XXX` items under a `### Constraints` heading (the heading
  `_is_requirement_heading` structurally cannot see today) and records how many sampled
  specs contain one.
- **Files**: New helper file (location is implementation's choice; do not modify
  production heading-match logic).

### Subtask T035 – Re-verify the broadened-predicate FP figure

- **Purpose**: Do not reuse the plan-time PLAN-GOV-002 number unverified.
- **Steps**: Re-run the broadened-predicate false-positive scan (heading match also
  including "constraint") against the then-current `kitty-specs/*/spec.md` corpus,
  reusing plan.md's documented read-only-scan method.

### Subtask T036 – Record both figures

- **Purpose**: FR-005's own re-verification precedent — both figures should live
  together with the shipped rate.
- **Steps**: Append the false-negative sample finding and the re-verified
  broadened-predicate FP figure to `requirement_mapping.py`'s module docstring,
  alongside the 9/368 figure WP03/T015 already recorded.

## Test Strategy

- No production-code test is required (informational only). If the corpus-scan helper
  is implemented as a pytest test, mark it clearly as informational/non-gating (e.g. a
  test that always passes and only prints/logs its findings, or a `pytest.ini`
  `-m informational` marker) so it cannot be mistaken for a blocking gate — distinct
  from WP08's actual gating ratchet test.

## Risks & Mitigations

- Scope creep: an implementer reading this WP as license to broaden
  `_is_requirement_heading` in production — explicitly foreclosed above and in
  plan.md's C-008 disposition (b).

## Review Guidance

- Confirm `_is_requirement_heading` in `requirement_mapping.py`'s production code path
  is unchanged in the diff.
- Confirm both figures (FN sample count, re-verified broadened FP rate) are present in
  the docstring, dated at this WP's execution time.

## Activity Log

- 2026-08-14T02:50:21Z – system – Prompt created.
