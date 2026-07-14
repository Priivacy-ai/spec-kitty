---
work_package_id: WP15
title: gc2b exact-selection ratchet — scope to orphans
dependencies: []
requirement_refs:
- FR-015
- FR-016
- NFR-002
tracker_refs:
- '2616'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T070
- T071
- T072
- T073
- T074
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_gate_coverage.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_gate_coverage.py
role: implementer
tags: []
shell_pid: "3011971"
shell_pid_created_at: "1783953481.93"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-015 +
[data-model.md](../data-model.md) E-11, and [plan.md](../plan.md) §IC-13. **Lane B root — lands early** so
its relief of the exact-selection firing shrinks the baseline-refreeze burden of WP11/WP16/WP17.

## Objective

Stop the gc2b exact-selection ratchet (`test_gc2b_current_selection_matches_baseline`, ~L742 in
`tests/architectural/test_gate_coverage.py`) from over-firing on **routine test-file add/remove** — which
this mission does 4–5× via new guard/regression files. Resolve #2616 by **scoping the ratchet to orphans**
(preferred) or making it **advisory** (weaker fallback), preserving the load-bearing orphan-detection signal.

## Context

- gc2b compares the current model selection to a frozen baseline in `tests/architectural/baselines/*.txt`;
  any routine add/remove trips it red, forcing a `--freeze-baselines` refreeze on every test-file change.
- The **load-bearing invariant** is orphan detection (a node-id selected by no gate). Scope-to-orphan keeps
  that signal while ignoring routine membership churn; advisory-only is the weaker fallback if scope-to-
  orphan proves infeasible.
- Related sibling guards already exist in this module (`test_gc2b_bites_on_baseline_file_side_injection`,
  `test_gc2b_bites_on_producer_side_selection_shrink`) — preserve their true-positive intent.

## Subtask guidance

- **T070 — re-scope.** Change `test_gc2b_current_selection_matches_baseline` so it asserts the
  **orphan-detection** invariant (a node-id in no gate's selection fails) rather than exact
  baseline-equality on routine add/remove. If scope-to-orphan is infeasible, make the exact-selection
  assertion **advisory** (records drift, does not red the gate) and document why in the PR.
- **T071 — red-first regression.** Add a regression proving (a) a routine test-file add/remove no longer
  trips the ratchet red, AND (b) a genuine orphan (a node-id selected by no gate) still **fails** — the
  load-bearing signal is preserved.
- **T072 — verify signal retained.** Confirm the sibling bite-tests
  (`test_gc2b_bites_on_baseline_file_side_injection`, `..._producer_side_selection_shrink`) still pass /
  still express true-positives.
- **T073 — DoD + gates.** `.venv/bin/python -m pytest tests/architectural/test_gate_coverage.py -q` green;
  `ruff`/`mypy` clean.
- **T074 — tracer.** Append a catalog row for the gc2b ratchet (invariant-vs-shape, verdict).

## Branch Strategy

Lane B root (no dependencies). Branches from the mission base; merges into
`feat/test-suite-friction-remediation`. **Lands early** — WP16/WP17 (and WP11's refreeze) benefit once this
relieves the exact-selection firing.

## Definition of Done (non-fakeable — NFR-002)

- [ ] gc2b re-scoped to orphans (or made advisory with documented rationale) per #2616.
- [ ] A regression proves a routine test-file add/remove no longer trips red.
- [ ] A regression proves a genuine orphan still **fails** — the orphan-detection signal is preserved.
- [ ] The sibling gc2b bite-tests still express true-positives.
- [ ] `test_gate_coverage.py` green; `ruff` + `mypy` clean.
- [ ] **Tracer (FR-016):** append a catalog row for the gc2b exact-selection ratchet + friction log.

## Risks

- **Loosening the ratchet too far** — losing real orphan-detection signal. Scope-to-orphan preserves the
  load-bearing invariant; advisory-only is the weaker fallback and must be justified in the PR.

## Reviewer guidance

- Confirm the orphan-detection true-positive still fires (regression evidence), not just that routine churn
  stopped firing.
- Confirm the sibling bite-tests are intact.

## Activity Log

- 2026-07-13T14:13:31Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – Assigned agent via action command
- 2026-07-13T14:34:13Z – user – shell_pid=2908286 – WP15 claimed
- 2026-07-13T14:34:34Z – user – shell_pid=2908286 – WP15 resuming
- 2026-07-13T14:35:04Z – claude:sonnet:python-pedro:implementer – shell_pid=2908286 – gc2b scoped-to-orphan committed 207898228
- 2026-07-13T14:38:10Z – claude:opus:reviewer-renata:reviewer – shell_pid=3011971 – Started review via action command
- 2026-07-13T15:01:46Z – user – shell_pid=3011971 – Review passed (reviewer-renata/opus)
