---
work_package_id: WP04
title: RISK-2 — Release-Checklist Artifact + Final QA
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-009
- FR-010
- NFR-002
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
agent: claude
history:
- date: '2026-05-02'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: implementer-ivan
authoritative_surface: kitty-specs/dashboard-extraction-followup-01KQMNTW/
execution_mode: planning_artifact
owned_files:
- kitty-specs/dashboard-extraction-followup-01KQMNTW/release-checklist.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

## Objective

Record SC-006 live-verification on the branch via a release-readiness document, then run the full test suite to confirm zero regressions across all four findings.

## Subtasks (already implemented at commit `dcbba9439`)

### T014 — `release-checklist.md`

`kitty-specs/dashboard-extraction-followup-01KQMNTW/release-checklist.md` — sections:

1. **Mandatory verification** — SC-006 live browser smoke-test (operator/date/commit/browser/checklist of dashboard checks)
2. **Standing release gates** — full test pass, daemon-gate pass, CHANGELOG entry, no outstanding ✗ items from the post-merge review

The verifier / date / commit fields are intentionally left blank — the operator who cuts a release downstream of `feature/650-dashboard-ui-ux-overhaul` fills them in. This mission's job is to ensure the artifact exists and is committed; not to perform the manual verification itself (the mission cannot do that — it requires a human with a browser).

### T015 — Final QA run

```bash
PYENV_VERSION=3.13.12 uv run --no-sync pytest tests/test_dashboard/ tests/architectural/ tests/sync/test_daemon_intent_gate.py -q
```

Expected: 310 passed, 1 skipped (the skip is the unrelated retrospective-events boundary test). Result captured in this WP's review record.

## Definition of Done

- [ ] `release-checklist.md` exists with all sections.
- [ ] SC-006 live-verification slots are present and unambiguous.
- [ ] Full test suite is green.

## Reviewer guidance

- Confirm the release-checklist matches the parent mission's checklist style (operator/date/commit/checklist).
- Confirm the standing release gates name the actual tests / artifacts a release operator would consult.
- Confirm the test-suite pass count is recorded.

## Risks

- The release-checklist relies on a future human verifier filling in SC-006 — this mission cannot guarantee it gets filled. Mitigation: the document is committed on the branch so any merge into a downstream release branch carries it forward; the parent mission's release-checklist (if/when one exists) can reference this artifact.

## Activity Log

- 2026-05-02T19:52:58Z – claude – Moved to claimed
- 2026-05-02T19:53:01Z – claude – Moved to in_progress
- 2026-05-02T19:53:06Z – claude – Moved to in_review
- 2026-05-02T19:53:37Z – claude – Moved to approved
- 2026-05-02T19:54:23Z – claude – Moved to done
