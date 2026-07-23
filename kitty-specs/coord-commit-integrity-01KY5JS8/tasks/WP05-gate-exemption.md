---
work_package_id: WP05
title: Runtime-state gate exemption
dependencies: []
requirement_refs:
- FR-007
planning_base_branch: remediation/coord-trust-2841
merge_target_branch: remediation/coord-trust-2841
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-trust-2841. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-trust-2841 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-coord-commit-integrity-01KY5JS8
base_commit: b696db5b57e8cde1b3cead7f9eba725d7e290590
created_at: '2026-07-22T21:00:07.072714+00:00'
subtasks:
- T013
history:
- at: '2026-07-22T19:33:57Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/bulk_edit/
create_intent:
- tests/bulk_edit/test_runtime_state_exemption.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/bulk_edit/diff_check.py
- src/specify_cli/bulk_edit/gate.py
- tests/bulk_edit/test_runtime_state_exemption.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

(Or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`.) Adopt its directives/tactics; state which you applied.

## Objective

Stop the bulk-edit diff-compliance gate from blocking a mission's OWN runtime state (Symptom B). No
`occurrence_map` exception, no coord hand-commit. Read `contracts/gate-and-doctor-contracts.md` (Runtime-state
gate exemption), `data-model.md` (Runtime-state allowlist), C-004.

## Branch Strategy

Planning base + merge target **`remediation/coord-trust-2841`** (coord). Lane d (parallel). Worktree per lane.

## Subtasks

### T013 — FR-007 own-feature_dir named allowlist exemption

The caller `bulk_edit/gate.py:~199` (`check_review_diff_compliance`) holds the mission's `feature_dir`; the
classifier `bulk_edit/diff_check.py` does not. Thread a NAMED allowlist — `status.events.jsonl`, `status.json`,
`review-cycle-N.md` (glob), issue-matrix, acceptance-matrix, notes — anchored to the RUNNING mission's OWN
`feature_dir` into `assess_file`/`classify_path`. Add an exemption branch BEFORE the path-heuristic (mirroring
the existing move/exception exemptions): a path that is `(under this mission's feature_dir) AND (basename ∈
allowlist)` → `FileAssessment(source="runtime-state", violation=False)`.

**C-004 (binding):** NOT everything under `feature_dir` — `spec.md`/`plan.md`/`tasks.md` stay reviewable.
Anchor to the RUNNING mission's own feature_dir so a bulk-edit renaming ANOTHER mission's runtime files is NOT
exempted.

**Campsite:** extract `_glob_match(posix, pattern)` (dup `_path_matches`/`_exception_for` fnmatch logic) +
`_is_bulk_edit_mission(feature_dir)` (dup guard at `gate.py:54`/`:216`); keep the allowlist filter a pure,
testable `_filter_allowlisted(files, allowlist)` — do NOT inline into `_git_diff_files`.

`tests/bulk_edit/test_runtime_state_exemption.py`: (a) own `status.events.jsonl` → exempt; (b) another
mission's runtime file under a different feature_dir → NOT exempt; (c) `spec.md`/`plan.md`/`tasks.md` under the
same feature_dir → still classify; (d) a non-runtime file under the feature_dir → still classify/violate.

## Definition of Done

- [ ] The mission's own runtime state is exempt (source `runtime-state`, no violation) with NO `occurrence_map` entry.
- [ ] Anchored to the RUNNING mission's own feature_dir (another mission's runtime files NOT exempt); spec/plan/tasks still classify.
- [ ] Exemption branch fires BEFORE the classifier; `_glob_match`/`_is_bulk_edit_mission`/`_filter_allowlisted` extracted; each covered by a focused test.
- [ ] `uv run --extra test ruff check` + `mypy` clean; complexity ≤15; `uv run --extra test pytest tests/bulk_edit -q` green.

## Reviewer guidance

Verify the anchor is the OWN feature_dir (the over-broad-exemption risk — a bulk-edit renaming another
mission's files must NOT slip past); spec/plan/tasks are NOT exempted; the exemption is a NAMED allowlist, not
"everything under feature_dir".

## Risks

- Over-broad exemption (choosing "everything under feature_dir") slips real surface past review — named allowlist + own-feature_dir anchor.
