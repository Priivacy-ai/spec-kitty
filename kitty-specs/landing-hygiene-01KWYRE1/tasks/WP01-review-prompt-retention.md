---
work_package_id: WP01
title: Review-prompt retention cap + fail-safe cleanup
dependencies: []
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: fix/landing-hygiene
merge_target_branch: fix/landing-hygiene
branch_strategy: Planning artifacts for this mission were generated on fix/landing-hygiene. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/landing-hygiene unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
agent: "reviewer-renata"
shell_pid: "3784548"
history:
- Created for mission landing-hygiene-01KWYRE1
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent:
- tests/specify_cli/review/test_prompt_retention.py
execution_mode: code_change
owned_files:
- src/specify_cli/review/prompt_metadata.py
- tests/specify_cli/review/test_prompt_retention.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your assigned profile (`python-pedro`) via `/ad-hoc-profile-load` before reading anything else.

## Objective
Stop per-invocation review-prompt files from accumulating unbounded within a repo (#2439, LC-7 residual). **FR-001, FR-002, NFR-001, NFR-002.**

## Context (grounded)
`src/specify_cli/review/prompt_metadata.py`: `review_prompt_path()` (~:108) writes each invocation to `<tmpdir>/spec-kitty-review-prompts/<repo-id>/<mission-slug>/<wp-id>/<invocation-id>.md`; `write_review_prompt_with_metadata()` (~:163) does the write. The `<repo-id>` (`safe_repo_identifier`, #959) isolation must stay intact. There is no retention/cleanup today.

## Guidance
**T001 — retention prune (FR-001/FR-002)**: after `write_review_prompt_with_metadata()` successfully writes the current `<invocation-id>.md`, prune that WP dir (`…/<repo-id>/<mission>/<wp>/`) to a **default cap**, newest-preserving (by count and/or mtime age — pick a sensible default, e.g. keep the N newest). Constraints:
- **Never delete the just-written current-invocation file** (pass/know its path; exclude it).
- **Best-effort / fail-safe**: wrap the prune so ANY error (permission, race, missing dir) is swallowed (log at debug, do NOT raise) — a review must never fail on housekeeping (NFR-002).
- Scope the prune strictly to the `spec-kitty-review-prompts/<repo-id>/…` subtree — never walk outside it.
- Do NOT change the path scheme, metadata, or `<repo-id>` isolation (NFR-001).
**T002 — tests** (`tests/specify_cli/review/test_prompt_retention.py`): (a) write N+K invocations → only the retained set remains; (b) the current invocation's file is present after prune; (c) monkeypatch the unlink/scandir to raise → `write_review_prompt_with_metadata` still returns the written path, no exception. Red-first where meaningful.

## Definition of Done
- Bounded retention; current invocation preserved; prune never raises; path scheme unchanged.
- `PWHEADLESS=1 uv run pytest tests/specify_cli/review/test_prompt_retention.py -q` green; `ruff`+`mypy --strict` clean; no suppression.
- Stay within owned files.

## Reviewer guidance
Confirm the current-invocation file can never be pruned, the prune is genuinely fail-safe (test the raise path), and the `<repo-id>` scheme is untouched.

## Activity Log

- 2026-07-07T18:18:47Z – python-pedro – shell_pid=3721246 – Assigned agent via action command
- 2026-07-07T18:19:58Z – python-pedro – shell_pid=3723690 – Assigned agent via action command
- 2026-07-07T18:30:44Z – python-pedro – shell_pid=3723690 – Retention cap + fail-safe prune; 5 tests green; ruff+mypy --strict clean
- 2026-07-07T18:37:12Z – reviewer-renata – shell_pid=3784548 – Started review via action command
