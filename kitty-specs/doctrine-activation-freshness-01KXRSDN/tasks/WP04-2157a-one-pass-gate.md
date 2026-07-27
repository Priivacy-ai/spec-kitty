---
work_package_id: WP04
title: '#2157a one-pass prerequisite gate'
dependencies:
- WP03
requirement_refs:
- FR-006
tracker_refs:
- '#2157'
planning_base_branch: feat/doctrine-activation-freshness
merge_target_branch: feat/doctrine-activation-freshness
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-activation-freshness. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-activation-freshness unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/preflight/
create_intent:
- tests/specify_cli/charter_runtime/test_preflight_one_pass.py
execution_mode: code_change
owned_files:
- src/specify_cli/charter_runtime/preflight/runner.py
- tests/specify_cli/charter_runtime/test_preflight_one_pass.py
role: implementer
tags: []
shell_pid: "3451123"
shell_pid_created_at: "1784326400.75"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (implementer). Do not act on the persona name alone — load the YAML.

## Objective

Stop the implement boundary bouncing a clean mission through its charter-owed prerequisites
**one at a time** (#2157a).

**Actual fix site (verified — do NOT mis-model this):** the user-visible "one at a time"
report is built by **`_build_blocked_reason` (`runner.py:~224`)**, whose logic is "**pick the
first non-passing check**" among the owed set `charter_source → synced_bundle → synthesized_drg`.
That is why the operator fixes one prerequisite, re-runs, and only then discovers the next.
Note: `run_charter_preflight` (`runner.py:~118`) never *raises*; and `_attempt_auto_refresh`
(`runner.py:~327`) already *batches* its sync→synthesize→validate refresh subprocesses — so
neither is the one-at-a-time reporting site. **Primary edit target = `_build_blocked_reason`;**
`_attempt_auto_refresh`'s stop-on-first-failed-refresh is a secondary, optional improvement.

**The fix**: make `_build_blocked_reason` enumerate **all** non-passing checks (with each one's
remediation command) instead of only the first.

**Anchor convention**: line numbers are indicative — resolve by symbol name.

## Hard constraints

- **OUTPUT-SHAPE PIN (ownership)**: `blocked_reason` is a single `str | None` field on
  `CharterPreflightResult` (`preflight/result.py:~95`), consumed as a string by cli/hook/dashboard.
  `result.py` is **NOT owned by this WP**. Emit the one-pass report as a **joined / multi-line
  string** into the existing `blocked_reason` field — do **NOT** change the result schema to a
  `list[str]` (that spills into the un-owned `result.py`).
- **Behavior-preserving except reporting**: the all-pass and single-failing-check outcomes are
  unchanged; the only new behavior is the multi-failure case (enumerate all non-passing checks).
  Per-check verdicts are UNCHANGED — you change *how many* are reported, not *what* each resolves to.
- **C-004 FENCE**: the analyzer-freshness gate `_require_current_analysis_report`
  (`agent/workflow.py:~835` → `analysis_report.check_analysis_report_current`, hashing
  spec/plan/tasks/charter) is a **different subsystem (#2157b)** and is **OUT** — do not touch it.
  (The real owed chain is `charter_source → synced_bundle → synthesized_drg`; `stale_analysis`
  is #2157b, not this WP.)
- Depends on **WP03** (T016 exercises the activation-visible `synthesized_drg` staleness among
  the enumerated checks — end-to-end value for the edge).
- **Campsite (in-WP)**: the three refresh commands (`runner.py:~378/391/403`) share the
  `["spec-kitty", "charter", …]` **prefix** but have different tails (`sync` / `synthesize` /
  `bundle validate`). Hoist the shared prefix (or the repeated `"spec-kitty"`/`"charter"`
  tokens) to a constant — NOT a single identical list.

## Subtasks

### T014 — Red-first
- Add `tests/specify_cli/charter_runtime/test_preflight_one_pass.py`. Construct a state where
  **≥2 owed checks are non-passing at once** (e.g. delete/stale the synced bundle AND the
  synthesized DRG) so that after auto-refresh runs, `_build_blocked_reason` still has ≥2
  non-passing checks to report. Assert the CURRENT behavior: `blocked_reason` names only the
  **FIRST** non-passing check. RED against the desired enumerate-all report.

### T015 — Enumerate-all-checks + campsite
- Refactor `_build_blocked_reason` to enumerate **every** non-passing check (each with its
  remediation command) into the `blocked_reason` **string** (joined/multi-line), instead of
  picking the first. Preserve check ordering.
- Optional secondary: also gather `_attempt_auto_refresh`'s failed-refresh reporting rather than
  stopping at the first failed subprocess (only if it stays within `runner.py` + ≤15 complexity).
- Hoist the shared command prefix per the campsite note above (S1192; tails differ).
- Keep complexity ≤15; do not change `result.py`.

### T016 — Tests + gate
- The T014 test now asserts all non-passing checks appear in the one `blocked_reason` string;
  each check's verdict matches its pre-change value (pin them); the result schema is unchanged
  (still `blocked_reason: str | None`).
- **End-to-end (ties the WP03 dep to value)**: drive one of the enumerated non-passing checks
  via **activation-induced `synthesized_drg` staleness** (WP03's seam) and assert it appears in
  the report — proving the aggregation surfaces the activation-visible signal.
- Add an assertion that the analyzer-freshness path (`check_analysis_report_current`) is not
  invoked/altered by this change (C-004 fence).
- `PWHEADLESS=1 uv run pytest tests/specify_cli/charter_runtime/ -q` green; ruff + mypy
  --strict clean; complexity ≤15.

## Branch Strategy

Planning base + merge target: `feat/doctrine-activation-freshness`. Worktree from `lanes.json`.
Depends on WP03.

## Definition of Done

- [ ] Red-first "only first non-passing check reported" repro written, green after the enumerate-all change.
- [ ] `_build_blocked_reason` enumerates all non-passing checks into the `blocked_reason` STRING; per-check verdicts unchanged; `result.py` schema untouched.
- [ ] Command-prefix literal hoisted (tails differ).
- [ ] C-004 fence: `analysis_report`/2157b untouched.
- [ ] ruff + mypy --strict clean; complexity ≤15.

## Risks

- **Changing a per-prerequisite verdict** (R-07) → pin each verdict value in tests; aggregation is additive.
- **Bleeding into 2157b** → the analyzer gate is a separate module; do not import/edit it.

## Reviewer guidance (reviewer-renata, opus)

Confirm the report enumerates all outstanding prerequisites in one pass, verdicts are unchanged,
the prefix literal is hoisted, and the analyzer-freshness subsystem is untouched.

## Activity Log

- 2026-07-17T21:57:00Z – claude:sonnet:python-pedro:implementer – shell_pid=3417407 – Assigned agent via action command
- 2026-07-17T22:11:16Z – claude:sonnet:python-pedro:implementer – shell_pid=3417407 – _build_blocked_reason enumerates all non-passing checks (string output, schema unchanged); C-004 fence held; gates green
- 2026-07-17T22:13:23Z – claude:opus:reviewer-renata:reviewer – shell_pid=3451123 – Started review via action command
