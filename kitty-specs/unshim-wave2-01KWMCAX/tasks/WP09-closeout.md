---
work_package_id: WP09
title: 'Closeout: governance docs + CHANGELOG + tracker'
dependencies:
- WP04
- WP06
- WP07
- WP08
requirement_refs:
- FR-010
- FR-011
tracker_refs:
- '#'
- '2'
- '2'
- '9'
- '1'
planning_base_branch: tidy/unshim-wave2
merge_target_branch: tidy/unshim-wave2
branch_strategy: Planning artifacts for this mission were generated on tidy/unshim-wave2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/unshim-wave2 unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
phase: Phase 1 - Sequential DAG
assignee: ''
agent: ''
history:
- at: '2026-07-03T17:18:34Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: docs/architecture/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/architecture/05_ownership_manifest.yaml
- docs/architecture/05_ownership_map.md
- docs/plans/degod-unshim-roadmap.md
- CHANGELOG.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – Closeout: governance docs + CHANGELOG + tracker

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Spec FR-010 + FR-011 (IC-08): scrub the live governance docs that would assert
falsehoods post-merge, write the CHANGELOG breaking-removal entry, close out the
tracker, and run the mission-level closing sweep. gh commands: `unset GITHUB_TOKEN;`.

## Subtasks & Detailed Guidance

### Subtask T025 – Doc scrubs (FR-011)
- `docs/architecture/05_ownership_manifest.yaml` (:74,:76,:105,:110-111 per the map) and `05_ownership_map.md` (:185,:205): remove the deleted-shim owned-path entries and the now-executed "3.3.0 removal"/"keep registered" claims.
- `docs/plans/degod-unshim-roadmap.md`: mark the Wave-2 / WS1 rows executed (mission id + date).
- `CHANGELOG.md` (canonical location per repo: check root + docs/changelog/): append the breaking-removal entry for `specify_cli.next` + `specify_cli.glossary` (+ the charter shims). NO version bump — `specify_cli/__init__.py` untouched (verified at plan; state it in the entry rationale if the format allows).

### Subtask T026 – Tracker closeout
- #2290 verdict comment: full-delete executed, defect fix, lock-gate disposition table pointer, charter_activate documented-canonical.
- #2291 verdict comment: both registered removals executed; #612/#613 referenced as completed antecedents.
- #1797 progress comment (registry drained to zero legacy rows; shim surfaces deleted; honest baselines). #2327 final comment (rule bound). #2293 operator-facing prerequisite note (Obligation A landed via #2317; Obligation B open — operator to confirm sufficiency). Do NOT close #2291/#2290/#2326 by hand — record intended PR-body lines (`Closes #2291`, `Closes #2290`, `Closes #2326`).
- Issue-matrix: terminal verdicts (edits happen on the planning branch — coordinate with the orchestrator per the lane guard).

### Subtask T027 – Closing sweep + NFR-002
- Also update the prose comment at `src/runtime/next/_internal_runtime/schema.py:22` naming `specify_cli.next` (unowned residue; no gate catches it).
- Pinned NFR-002 grep (quickstart.md) → paste empty output; `PWHEADLESS=1 pytest tests/architectural/ -q` + full parallel suite + terminology guard; whole-tree mypy 0; ruff. Record tallies. Commit.

## Test Strategy
```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q
```

## Risks & Mitigations
- Premature issue closure (PR closes them); docs-freshness gates (if a page-inventory trips, run the freshen tool per the docs discipline — scripts/docs/freshen_adr_inventory.py pattern).

## Review Guidance
- Both governance docs actually scrubbed (read them); CHANGELOG entry present; every tracker comment posted (verify URLs in log); closing tallies recorded.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T17:18:34Z – system – Prompt created.
