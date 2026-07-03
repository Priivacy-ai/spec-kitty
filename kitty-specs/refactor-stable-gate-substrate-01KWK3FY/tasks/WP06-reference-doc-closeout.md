---
work_package_id: WP06
title: Reference-pattern doc + closeout
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-005
- FR-009
tracker_refs: []
planning_base_branch: tidy/gate-substrate
merge_target_branch: tidy/gate-substrate
branch_strategy: Planning artifacts for this mission were generated on tidy/gate-substrate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/gate-substrate unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
phase: Phase 2 - Closeout
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1840322"
history:
- at: '2026-07-03T06:37:42Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_no_worktree_name_guess.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Reference-pattern doc + closeout

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

Closeout (spec FR-005 reframed + FR-009): document
`test_no_worktree_name_guess.py` as the Design-P REFERENCE implementation with a
docstring note and ZERO key changes (the diff proves it); bring the tracker to
terminal state; close out the tracers and prep the acceptance-matrix evidence. Runs
after all five parallel WPs are approved.

## Context & Constraints

- Spec FR-005's reframing (rev 2): the earlier "convert Family E" plan was CANCELLED
  by the post-spec squad — the file is already the chosen design; converting would
  REGRESS its content-detection. This WP writes that down where future readers look.
- `research.md` D8 (the follow-up candidates the #2072 comment must name: the
  drain-deferred-entries remainder + the audit-twin consolidation).
- Tracker facts: #2310 and #2311 close with the mission (their verdicts go terminal in
  issue-matrix.md); #2072 stays OPEN upstream with the partial-completion comment.
- Coord-topology mission: matrices/tracers commit per the established write paths
  (primary planning branch; the degod precedent).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: tidy/gate-substrate
- **Merge target branch**: tidy/gate-substrate

## Subtasks & Detailed Guidance

### Subtask T023 – Design-P reference docstring note

- **Steps**: Add to `tests/architectural/test_no_worktree_name_guess.py`'s module
  docstring: this file is the REFERENCE implementation of the Design-P content-pinned
  gate-key pattern (frozen tool-derived `(qualname, token)` comparands in
  `_ALLOWED_SITES_FILES` :92 + the staleness guard
  `test_name_compose_offenders_match_pinned_baseline` + drift theater
  `test_composite_key_survives_line_drift`), named by the refactor-stable doctrine
  (testing-principles styleguide) and mission refactor-stable-gate-substrate-01KWK3FY;
  key semantics MUST NOT be converted to seed-derivation (it would regress
  content-detection — see the mission's research D1 proof). ZERO changes to any key,
  allowlist, or test body — `git diff` on the file shows the docstring hunk only.
- **Files**: the one owned file (docstring only).

### Subtask T024 – Tracker closeout + issue-matrix verdicts

- **Steps** (gh with `unset GITHUB_TOKEN;`):
  1. `kitty-specs/refactor-stable-gate-substrate-01KWK3FY/issue-matrix.md`: #2310 →
     `fixed` (styleguide + DRG evidence), #2311 → `fixed` (un-quarantine evidence with
     the final count), #2072 → `deferred-with-followup` with the delivered-here slice
     named (re-key + inventory fold) and the remainder explicit (drain the 10
     allowlisted resolver sites; audit-twin consolidation candidate). #2306/#2308/#2034/
     #2309/#2071 rows updated to current reality.
  2. Post the #2072 partial-completion comment (what landed, what remains, where the
     conversion recipe lives).
  3. Do NOT close #2310/#2311 by hand — they close via the PR's `Closes` lines (the
     orchestrator writes the PR body at merge time; record the intended lines in the
     Activity Log).
- **Files**: issue-matrix.md + tracker comments.

### Subtask T025 – Tracer close-outs + acceptance evidence prep

- **Steps**:
  1. Append close-out sections to all three tracers (what the conversions actually
     cost, surprises vs the plan, the WP04 content-script output location).
  2. Populate `kitty-specs/refactor-stable-gate-substrate-01KWK3FY/acceptance-matrix.json`
     criteria descriptions/evidence pointers from the delivered state (pass_fail stays
     pending until the accept gate; follow the degod mission's format).
  3. Run the mission-level closing sweep: full `tests/architectural/` +
     `tests/doctrine/` + the WP05 shard-form run once more on the merged mission
     branch state; record tallies.

## Test Strategy

```bash
export PATH="$PWD/.venv/bin:$PATH"; PYTHONPATH="$PWD/src"
PWHEADLESS=1 pytest tests/architectural/ tests/doctrine/ -q -p no:cacheprovider
git diff tests/architectural/test_no_worktree_name_guess.py   # FULL diff: docstring hunk ONLY, zero key/body edits
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q  # pre-push guard
```

## Risks & Mitigations

- **Scope creep into key changes**: the FR-005 cancellation is binding — the diff-stat
  proof is the guard.
- **Premature issue closure**: #2310/#2311 close via the PR, not by hand.

## Review Guidance

- The docstring-only diff proof.
- Issue-matrix verdicts terminal and evidence-accurate.
- The #2072 comment names BOTH remainders.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T06:37:42Z – system – Prompt created.
- 2026-07-03T08:00:32Z – claude:opus:python-pedro:implementer – shell_pid=1805673 – Assigned agent via action command
- 2026-07-03T08:12:03Z – claude:opus:python-pedro:implementer – shell_pid=1805673 – Design-P reference docstring (docstring-only diff, 26 ins, zero key/body edits); owned-file 11 passed; full tests/architectural+tests/doctrine sweep 3034 passed/4 skipped; terminology guard 3 passed; -m quarantine collects 0. Tracker: #2072 partial-completion comment posted (issuecomment-4874144446). Planning-dir edits (data-model [inventory-only] broadening, issue-matrix terminal verdicts + #2316/#2309 rows, tracer close-outs, acceptance-matrix evidence) drafted in the final message for the orchestrator (mission dir guard-blocked on lanes).
- 2026-07-03T08:14:56Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1840322 – Started review via action command
