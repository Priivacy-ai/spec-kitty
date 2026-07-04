---
work_package_id: WP05
title: 'Closeout: roadmap strike, tracker comments, probe evidence, re-derivations'
dependencies:
- WP03
- WP04
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: tidy/ci-suite-map-2034
merge_target_branch: tidy/ci-suite-map-2034
branch_strategy: Planning artifacts for this mission were generated on tidy/ci-suite-map-2034. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/ci-suite-map-2034 unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
phase: Phase 4 - Closeout
assignee: ''
agent: "claude-orchestrator"
shell_pid: '112000'
history:
- at: '2026-07-04T05:27:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: docs/plans/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/plans/degod-unshim-roadmap.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Closeout

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

FR-009: the mission's public record — roadmap strike, tracker comments, probe/re-derivation evidence consolidated. No issue closed by hand (the PR closes #2297/#2296/#2034/#2333).

## Subtasks & Detailed Guidance

### Subtask T015 – Docs + tracker closeout
- `docs/plans/degod-unshim-roadmap.md`: strike the Wave-0 row (`✅ EXECUTED (ci-suite-map-bind-01KWNPMP, <date>)` with the one-line what-shipped); update the WS5 seam-state row (marker→job authority BOUND; remaining WS5 = mypy-scope AC only). Also mark the Wave-1-D tasks.py row EXECUTED (PR #2308) — a known stale row flagged during Wave-0 planning (campsite, one line).
- Tracker comments (`unset GITHUB_TOKEN && gh ...`): #2034 (what closed it: the completeness invariant + residual job; the census showing all 9 named failures were already fixed); #2283 (factor (a) closed; (b)/(c) → CT7 #2077); #1933 (the reconciliation: run_all catch-all = loud alarm + shrink obligation; mapped PRs stay targeted; live unmatched-dir census attached); #1868 (WS5 checklist update: bound ACs enumerated; mypy-scope AC stays open); #2296/#2297/#2333 need no comment beyond the PR's `Closes` lines (verify the PR body carries them).
- If a docs-freshness/inventory gate trips on the roadmap edit, use the canonical freshen script (see docs/ guides), never hand-edit lockfiles.
- HEADS-UP (refresh 2026-07-04): the roadmap file was reshaped upstream since prep (Wave-2∥ row → ✅ EXECUTED, WS1 seam row → DONE, new "first functional pickup #1746" section, `updated: 2026-07-04`). Your three edits are still pending and apply as written — but edit the CURRENT file content and do not regress those upstream additions.

### Subtask T016 – Probes, re-derivations, closing sweep
- Consolidate the C-007 probe evidence (WP03's probe run links A/B/C) + the mission PR's own run into the Activity Log; verify quality-gate on the mission PR shows the residual job + the step-summary table live.
- Re-derivations recorded in one block (NFR-004): residual collect count, marker-state split (i/ii/iii counts), orphan count 0, duplicate count + delta justification, catch-all census (unmatched dirs remaining + the shrink-obligation list).
- Closing sweep: `python -m tests.architectural._gate_coverage --check` (orphans 0); `PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider`; `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider` (full suite — judge-the-test any failure: pre-existing/flake/new, with evidence; never retry-to-green); `PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q` (prose edits).
- Diff-scoped ruff; mypy Success.

## Definition of Done
- Roadmap + seam table truthful; all comments posted with links recorded; evidence block complete; sweeps green — any non-green result carries stash-diff adjudication evidence (`git stash` the mission diff + re-run establishing pre-existing vs mission-caused; stash-diff references logged in the Activity Log). A verdict asserted without the re-run proof does not satisfy this DoD.

## Risks / Reviewer Guidance
- Premature closure = reject (comments inform; the PR closes).
- The full-suite failures, if any, must carry the stashed-diff adjudication evidence (pre-existing vs mission-caused).

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-04T05:27:33Z – system – Prompt created.
