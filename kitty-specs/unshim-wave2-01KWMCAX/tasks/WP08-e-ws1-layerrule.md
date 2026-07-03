---
work_package_id: WP08
title: 'E: WS1 mission_runtime LayerRule bind'
dependencies: []
requirement_refs:
- FR-009
tracker_refs:
- '#'
- '2'
- '3'
- '2'
- '7'
planning_base_branch: tidy/unshim-wave2
merge_target_branch: tidy/unshim-wave2
branch_strategy: Planning artifacts for this mission were generated on tidy/unshim-wave2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/unshim-wave2 unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
phase: Phase 1 - Sequential DAG
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2802116"
history:
- at: '2026-07-03T17:18:34Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_layer_rules.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – E: WS1 mission_runtime LayerRule bind

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

Spec FR-009 (IC-07; sub-issue #2327 under epic #1868): bind the missing
`mission_runtime` outbound LayerRule with a COMMITTED, CI-selected negative test.
PRE-DECIDED (research D6): the 10+ real upward edges from `mission_runtime/resolution.py`
into `specify_cli.*` are documented as a NAMED allowed-exception set with recorded
rationale — the rule does NOT red on existing code; converting those edges is a
carved-out future mission.

## Subtasks & Detailed Guidance

### Subtask T022 – Derive the allowed set + record the decision
- AST-derive `mission_runtime`'s actual outbound imports (incl. lazy in-function). Expected: `{runtime, charter, glossary, kernel}` + the named `specify_cli` exception list. Record the decision (rule docstring carrying the rationale + the future-mission carve-out; mirror how sibling layers document theirs in `test_layer_rules.py`).

### Subtask T023 – Rule + committed negative test
- Add the LayerRule following the existing `should_not().access_layers_that()` idiom of sibling layers; add the negative test proving the rule's matcher rejects a synthetic out-of-set import (e.g. a fixture module or an in-test AST probe — follow the file's existing theater conventions). Markers MUST be CI-selected (NFR-005/#2034): copy the marker pattern of the neighboring layer tests and verify with the suite-map (grep ci-quality workflow / suite map for the file's marker class).

### Subtask T024 – Gates + #2327 progress
- `PWHEADLESS=1 pytest tests/architectural/test_layer_rules.py -q` green (rule non-vacuous: negative test red-flips if the allowed set is widened to everything — demonstrate once, paste); full `tests/architectural/` sweep green; `unset GITHUB_TOKEN; gh issue comment 2327` with the bound-rule evidence + allowed-set rationale. Commit.

## Test Strategy
```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/architectural/test_layer_rules.py tests/architectural/ -q -p no:cacheprovider
```

## Risks & Mitigations
- Vacuous rule (allow-everything) — the negative test + the demonstrate-once red-flip prove teeth.
- Marker invisibility (#2034) — T023's suite-map check is mandatory evidence.

## Review Guidance
- Re-derive the allowed set yourself (mission_runtime is 4 files); verify the negative test actually exercises the rule's matcher; verify marker CI-selection evidence.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T17:18:34Z – system – Prompt created.
- 2026-07-03T17:41:17Z – claude:opus:python-pedro:implementer – shell_pid=2755799 – Assigned agent via action command
- 2026-07-03T18:00:48Z – claude:opus:python-pedro:implementer – shell_pid=2755799 – Bound mission_runtime->specify_cli outbound LayerRule as a named allowed-exception ledger (9 live subpackages) + 3 committed CI-selected (marker=architectural) tests incl. negative non-vacuity test. Non-vacuity flip: allow-everything matcher REDS test_rule_rejects_out_of_ledger_import, reverted->green. Gates: test_layer_rules.py 16 passed; full tests/architectural/ 644 passed/4 skipped exit0; ruff diff-scoped exit0; mypy src/ Success. --force per known bug #2324: rejection cited T025-T027 which belong to WP09 (closeout), not WP08; WP08's own subtasks T022-T024 are all done.
- 2026-07-03T18:04:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=2802116 – Started review via action command
- 2026-07-03T18:10:52Z – user – shell_pid=2802116 – Review passed (--force per known bug #2324: cited unchecked T025-T027 belong to WP09 closeout, not WP08 whose subtasks T022-T024 are done). Verified: independently AST-derived 9 specify_cli subpackages from src/mission_runtime/ == ledger exactly (no padding/gaps); non-vacuity proven by live flips (allow-everything matcher REDS negative test; synthetic specify_cli.cli edge in artifacts.py REDS bound rule; padding REDS stale-guard); negative test drives REAL matcher; module marker architectural (pytest.ini:45) CI-selected via ci-quality.yml architectural shard; scope clean (commit 0f3a16877 = test_layer_rules.py only); 16 passed, ruff clean.
