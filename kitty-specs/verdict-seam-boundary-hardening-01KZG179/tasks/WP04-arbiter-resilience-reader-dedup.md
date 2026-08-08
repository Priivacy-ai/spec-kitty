---
work_package_id: WP04
title: Arbiter override resilience (conflict-marked review-cycle artifact)
dependencies: []
requirement_refs:
- FR-009
- FR-010
planning_base_branch: hardening/verdict-seam-facade-followup
merge_target_branch: hardening/verdict-seam-facade-followup
branch_strategy: Planning artifacts for this mission were generated on hardening/verdict-seam-facade-followup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into hardening/verdict-seam-facade-followup unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
phase: Phase 2 - Parallel hardening
history:
- at: '2026-08-08T09:55:00Z'
  actor: system
  action: Prompt generated from plan.md IC-03
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/artifacts.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/artifacts.py
- src/specify_cli/review/arbiter.py
- tests/review/test_arbiter.py
- tests/review/test_artifacts_no_verdict_field.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3244'
---

# Work Package Prompt: WP04 – Arbiter override resilience

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` and behave per its guidance before parsing the rest of this prompt.

## Goal

Fix a **latent crash** (reproduced live): after the prior mission's fail-open merge-driver downgrade writes git conflict markers into a `review-cycle-N.md`, a later arbiter override crashes because `persist_arbiter_decision` parses that damaged file's frontmatter. **RED-FIRST** (C-006). **Independent parallel lane.**

> **Scope note:** #3216 (originally folded as T019 — collapse a hand-rolled review-cycle reader) was **descoped**. The post-tasks squad verified the target reader `_get_latest_review_cycle_verdict` was already retired by the prior mission's WP05 (#3245, FR-003); there is no live duplicate left. #3216 is closed as already-resolved. This WP does **not** touch `tasks_parsing_validation.py`.

## Subtasks

### T015 — RED-FIRST regression (do this before any fix)
In `tests/review/test_arbiter.py`, add a regression driving the **public** `persist_arbiter_decision` entry (mirror `test_persist_decision_resolves_via_slug_and_emits_override`) against a WP whose latest `review-cycle-N.md` body begins with git conflict markers (`<<<<<<< ours ... ======= ... >>>>>>> theirs`, **no** valid YAML frontmatter). Assert: no exception raised **and** the override is durably recorded (materialize the snapshot; the review override actor == the arbiter). This test is **RED today** (`ValueError: Review artifact file has no YAML frontmatter`). Commit it RED (or verify red locally) before T016/T017.

### T016 — Add `ReviewCycleArtifact.latest_cycle_number()` + hoist constants
In `review/artifacts.py`, add a filename-only staticmethod that returns the highest cycle number by filename, **no body parse** — reuse the existing `_cycle_number_or_zero` / `_REVIEW_CYCLE_NUMBER_RE`:
```python
@staticmethod
def latest_cycle_number(sub_artifact_dir: Path) -> int:
    candidates = list(sub_artifact_dir.glob(_REVIEW_CYCLE_GLOB))
    return max((_cycle_number_or_zero(p) for p in candidates), default=0)
```
- **Campsite (S1192):** the `"review-cycle-*.md"` glob and `f"review-cycle-{n}.md"` builder appear ~16× in this file. Hoist a `_REVIEW_CYCLE_GLOB` constant and a small filename-builder and route the existing sites + the new helper (and `arbiter.py:468`) through them. **Add `latest_cycle_number` as a THIRD helper** — do NOT merge the deliberately-separate `_parse_review_cycle_candidates` / `_cycle_number_or_zero` (comments at ~L37, L65-66 keep them apart).

### T017 — Swap the arbiter path; leave `.latest`/`from_file` intact (C-004)
In `review/arbiter.py`, `persist_arbiter_decision` currently resolves the cycle number in a two-line guarded form (verbatim, ~L466-467):
```python
latest = ReviewCycleArtifact.latest(wp_subdir) if wp_subdir.exists() else None
cycle_number = latest.cycle_number if latest is not None else 0
```
Replace both lines with the filename-only resolver:
```python
cycle_number = ReviewCycleArtifact.latest_cycle_number(wp_subdir) if wp_subdir.exists() else 0
```
**Do NOT touch `.latest`/`from_file`** — a second consumer (`cli/commands/agent/workflow_executor.py:1134`, out of scope) needs the full parsed body; flag it as a same-shape follow-up, do not change it here.

### T018 — Direct micro-test for the helper
In `tests/review/test_artifacts_no_verdict_field.py`, add a focused test: a directory with mixed valid + conflict-marked `review-cycle-*.md` siblings → `latest_cycle_number` returns the highest number by filename and does **not** raise.

## Census note
`latest_cycle_number` is a cycle-number loader, NOT a verdict reader/writer — it must trip neither the WRITER (`ReviewResult(`/`.from_dict`) nor READER (frontmatter-parse) census predicates, matching the existing `.latest`/`from_file` exclusion rationale (artifacts.py ~L373-378). Verify it adds no `verdict_seam_census.yaml` row.

## Branch Strategy
Independent parallel lane off `hardening/verdict-seam-facade-followup`; merges back to same.

## Definition of Done
- T015 regression is RED before the fix, GREEN after.
- `latest_cycle_number` added (filename-only), arbiter path swapped, `.latest`/`from_file` unchanged.
- Review-cycle glob/filename constants hoisted (S1192); micro-test green.
- `ruff`/`mypy` clean, zero new suppressions. `pytest tests/review/` green.

## Reviewer Guidance
Confirm the regression is genuinely red on the pre-fix tree (not a no-op assertion). Confirm `.latest`/`from_file` are untouched (C-004) and the `workflow_executor.py` twin is only *flagged*, not changed.

## Risks
- Over-eager constant hoist merging the deliberately-separate helpers — keep them separate.
