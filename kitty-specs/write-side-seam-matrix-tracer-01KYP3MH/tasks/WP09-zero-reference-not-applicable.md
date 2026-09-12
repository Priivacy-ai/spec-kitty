---
work_package_id: WP09
title: Zero-reference Gate 4 not_applicable
dependencies:
- WP08
requirement_refs:
- FR-005
- NFR-005
planning_base_branch: feat/write-side-seam-matrix-tracer
merge_target_branch: feat/write-side-seam-matrix-tracer
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-seam-matrix-tracer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-seam-matrix-tracer unless the human explicitly redirects the landing branch.
created_at: '2026-07-29T09:24:15+00:00'
subtasks:
- T034
- T035
- T044
history:
- at: '2026-07-29T09:24:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/review/
create_intent:
- tests/specify_cli/cli/commands/review/test_zero_reference_not_applicable.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/review/__init__.py
- tests/specify_cli/cli/commands/review/test_zero_reference_not_applicable.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3035'
---

# Work Package Prompt: WP09 – Zero-reference Gate 4 not_applicable

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## Objective

Make post-merge review record Gate 4 `not_applicable` when the spec declares **no** canonical issue references (same definition as finalization), retaining fail-closed behaviour when references **do** exist (#3035). Folded from samuelgoff's work (coordinated, reassigned) — reuse it where possible.

## Context

- Today a zero-reference mission is hard-failed for a matrix it should not need. The completeness/discovery definition comes from **WP08** (dependency) — this WP consumes it, it does not re-define references.
- `not_applicable` is a first-class Gate 4 verdict; the overall review verdict is then decided by the applicable gates — no fabricated matrix.

## Subtasks

### T034 — Zero-reference → not_applicable
In `src/specify_cli/cli/commands/review/__init__.py`, when the discovery (WP08) returns zero canonical references, record Gate 4 `not_applicable` and let applicable gates decide the verdict. Use the WP08 definition, not a local re-scan.

### T035 — Fail-closed retained + both-branch regression
When references exist, retain the fail-closed enforcement. Add `tests/specify_cli/cli/commands/review/test_zero_reference_not_applicable.py` covering **both** branches: zero references → `not_applicable` (no hard fail); references present but unmatched → fail-closed.

### T044 — Issue-matrix reader switch on post-merge review (C-008 / B-1 fix)
`review/__init__.py:295 _evaluate_issue_matrix` hardcodes `issue_matrix_path = feature_dir / "issue-matrix.md"` and `:306 if not issue_matrix_path.exists(): return` a violation ("required in post-merge mode") **before** calling `validate_issue_matrix` — so a greenfield `.json` mission (B3) hard-fails post-merge review despite the matrix existing on coord. Switch this to WP05's dir-based `load_issue_matrix(feature_dir)` and **delete the `.md` `.exists()` precheck**; the `not_applicable` (T034) and fail-closed (T035) branches then evaluate against the JSON via the failover reader.

## Branch Strategy

Both planning and merge target are `feat/write-side-seam-matrix-tracer`. Allocate via `/spec-kitty.implement WP09` (depends on WP08).

## Definition of Done
- Zero-reference → Gate 4 `not_applicable`; references-present → fail-closed.
- `ruff`/`mypy` clean; complexity ≤ 15; both-branch regression green.

## Risks / Reviewer guidance
- **Same definition as finalization** (via WP08) — do not add a local reference scan.
- Both branches must be regression-covered — a one-branch test lets the other silently regress.
- **Commit the completed slice** so worktree progress is durable.
