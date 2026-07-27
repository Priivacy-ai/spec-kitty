---
work_package_id: WP06
title: "IC-TIDY — rollback-reset seam + freshness regression guard + issue-matrix"
dependencies: []
requirement_refs:
- FR-009
- FR-010
- FR-011
tracker_refs: []
planning_base_branch: rework/ray-cluster-aggregation
merge_target_branch: rework/ray-cluster-aggregation
branch_strategy: Planning artifacts for this mission were generated on rework/ray-cluster-aggregation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rework/ray-cluster-aggregation unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
- T031
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "4168956"
history:
- created at planning (tasks) — parallel lane; consolidates rollback resets, pins the #1764 freshness guard, closes the issue-matrix
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_move_task.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_freshness_checkbox_insensitive.py
execution_mode: code_change
model: sonnet
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/specify_cli/cli/commands/agent/test_freshness_checkbox_insensitive.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-009
(regression-guard only — #1764 already ships) + FR-010 (pure consolidation, no new behavior) +
FR-011 (issue-matrix terminal verdicts, spelled out row-by-row) + SC-006, [plan.md](../plan.md)
§IC-TIDY ("no new reset behavior"; "FR-009 must exercise BOTH the write and gate-check paths"),
and [research.md](../research.md) "Verified-already-done: #1862 analysis-freshness
checkbox-insensitivity". This WP is fully independent of WP01-WP05 — it owns
`tasks_move_task.py` exclusively (no other WP touches it, per C-003) and authors the mission's
`issue-matrix.md`, which should summarize the OTHER five WPs' outcomes — write T030 last, or at
minimum re-check it once the other WPs' actual landing evidence (commit SHAs, PR numbers) is
available, since it is bookkeeping over the whole mission's result.

## Objective
Three small, independent closeout items: (1) consolidate the two existing rollback-to-`planned`
resets in `tasks_move_task.py` — clearing `agent`/`shell_pid` frontmatter (from #2514) and
unchecking the WP's subtask rows (from #2513) — through a single named seam so "reset on
rollback" has one home in the code, without changing what either reset does; (2) pin, with a
regression test only (no new logic), that #1764's checkbox-insensitive freshness hashing
continues to work on both the write and gate-check paths, so ticking a subtask never invalidates
an implement-gate analysis; (3) author `issue-matrix.md`, the mission's terminal-verdict record
for every tracker issue this mission touches or closes.

## Subtasks

### T027 — `_mt_reset_for_planned_rollback` consolidation seam
Both resets already exist in `tasks_move_task.py` and are individually correct — this subtask is
pure consolidation, not new behavior. Read both sites carefully first:

1. **Claim-marker clear** — inside the function that persists the WP frontmatter (contains the
   comment `# #2512: rolling a WP back to planned releases the implementation claim`), guarded by
   `if st.target_lane == Lane.PLANNED:` (~:1426): `updated_front = delete_scalar(updated_front,
   "agent")` then `updated_front = delete_scalar(updated_front, "shell_pid")`. This runs **inside**
   `_tasks.feature_status_lock(...)`, as part of persisting the WP file's frontmatter mutation
   in-memory before it is written.
2. **Subtask uncheck** — `_mt_uncheck_rollback_subtasks(st, ports)` (~:1457), called from
   `_mt_execute` (~:1535) **after** the `with feature_status_lock(...)` block has exited:
   `if st.target_lane == Lane.PLANNED: _mt_uncheck_rollback_subtasks(st, ports)` (~:1553).

**These two resets currently run at different points relative to the status lock** (one inside,
one outside) — they cannot be merged into a single function call without either widening the
lock's scope (a real behavior change, out of scope for "no new reset behavior") or restructuring
the lock boundary (also out of scope). The consolidation this WP actually wants, per FR-010's
"single home" framing, is: extract the claim-marker-clear two-liner into its own small, named,
pure helper (e.g. `_mt_clear_rollback_claim_markers(frontmatter: str) -> str`, doing exactly the
two `delete_scalar` calls, called from inside the existing frontmatter-persist function in place
of the inline pair), and introduce a single umbrella entry point —
`_mt_reset_for_planned_rollback(st, ports)` — that `_mt_execute` calls once (replacing its current
direct `if st.target_lane == Lane.PLANNED: _mt_uncheck_rollback_subtasks(st, ports)` line at
~:1553) and that itself is responsible for invoking `_mt_uncheck_rollback_subtasks`. The
frontmatter-clear helper stays called from its original (in-lock) call site, but is now a single
named function referenced by both the persist path and (for discoverability/documentation) named
consistently with the umbrella seam — the goal is that a future reader searching for "what
happens on rollback to planned" finds one clearly-named seam, not that every line physically
moves to one call stack frame. If, after reading the live code, a cleaner single-call-site
consolidation is possible without touching the lock boundary, prefer it — but do not widen the
lock's scope or change the ordering of the two resets relative to each other or the lock to
achieve it. Document whichever shape you land on in the Activity Log, including why the lock
boundary constrains the "one call site" ideal.

### T028 — Test: rollback leaves the WP fully re-implementable
Through the production `move-task --to planned` path (i.e. actually invoke the CLI command /
its underlying `_mt_execute` entry point, not the two reset functions directly), roll back a WP
that has `agent`/`shell_pid` frontmatter set and some `[x]` subtask rows checked. Assert:
- No `[x]` rows remain in the WP's `tasks.md` section afterward (drive the check through
  `core.subtask_rows.count_wp_section_subtask_rows` — WP01's canonical counter — for consistency
  with the rest of the mission, if WP01 has landed by the time you write this; otherwise assert
  directly on the text).
- The WP frontmatter no longer has `agent` or `shell_pid` set.
This is the SC-006 acceptance proof.

### T029 — FR-009 regression guard: checkbox-insensitive freshness hashing
Create `tests/specify_cli/cli/commands/agent/test_freshness_checkbox_insensitive.py` (or place it
under `tests/specify_cli/` wherever `analysis_report.py`'s existing test suite lives if that's a
better fit — check for an existing `test_analysis_report*.py` and colocate there instead if one
exists, to avoid a second suite for the same module). No new normalization logic is authored here
— `analysis_report._normalize_tasks_md` (module-level, ~:147) already strips `[ ]`/`[x]` via
`_CHECKBOX_RE.sub(r"\1[ ]", text)` before hashing, wired into `_artifact_hash_entry` (~:157-163)
which special-cases `tasks.md` specifically, which is consumed by
`collect_input_artifact_hashes(feature_dir, repo_root)` (~:187). Both `write_analysis_report` and
`check_analysis_report_current` route through this **same** `collect_input_artifact_hashes` call —
confirm this by reading both functions' bodies before writing the test. The regression test must:
1. Build a `tasks.md` fixture, call `write_analysis_report` (or drive
   `collect_input_artifact_hashes` directly at this first checkpoint) to get a baseline hash.
2. Flip a `[ ]` to `[x]` (or vice versa) in the WP section — simulating a dashboard progress tick
   — and call `check_analysis_report_current` (or `collect_input_artifact_hashes` again) and
   assert the `tasks.md` hash is **unchanged**.
3. As a negative control, change substantive content (e.g. add a new `T###` row, or edit prose
   outside a checkbox) and assert the hash **does** change — proving the test isn't accidentally
   passing because the whole hashing mechanism is inert.
Cover both the write-path entry (`write_analysis_report`) and the gate-check entry
(`check_analysis_report_current`) — FR-009 explicitly calls out "on both the write and
implement-gate-check paths".

### T030 — Author `issue-matrix.md`
Create `kitty-specs/coord-shadows-arm-closeout-01KXAST2/issue-matrix.md` using the canonical
schema (see `kitty-specs/relocation-hardened-dead-code-scanners-01KX958P/issue-matrix.md` for the
exact table shape — columns `Issue | Verdict | Evidence ref | Scope`, plus a one-line valid-verdict
legend at the top). Rows, per spec.md FR-011:

| Issue | Verdict | Evidence ref | Scope |
|-------|---------|--------------|-------|
| #2504 | fixed | Aggregated fix (PR #2503→#2513 cherry-picks) + WP01/WP02 hardening on this branch | (fill in the actual issue title/summary once confirmed against the tracker) |
| #2510 | fixed | Aggregated fix + WP01/WP02 hardening | ″ |
| #2513 | fixed | Aggregated fix (the uncheck writer itself) + WP01's canonical `_walk_wp_section` correction | ″ |
| #2502 | fixed | Aggregated fix + WP02's emit-layer hardening (all four callers primary-correct) | ″ |
| #2512 | fixed | Aggregated fix (worktree recovery) + WP04's sparse-checkout regression fix (FR-006) + WP06's rollback marker-clear seam (FR-010) | ″ |
| #1231 | fixed | WP05's FR-007 liveness-helper promotion + stale-indicator live-claim suppression | Claim-marker false-stale friction |
| #1862 | verified-already-fixed | #1764 (`analysis_report._normalize_tasks_md`); pinned by WP06's FR-009 regression guard (this WP, T029) | Analysis-freshness checkbox-insensitivity — no new logic, regression guard only |
| #2160 | deferred-with-followup | Follow-up: #2160 (parent epic remains open) | This mission closes the read/gate arm; the epic itself stays open as the umbrella for other coord-shadows children |

Use the exact evidence-ref wording only once each WP has landed and you have real commit
SHAs/PR references to cite — placeholder text above ("Aggregated fix…") should be replaced with
concrete evidence (commit SHA, WP approval reference) at mission close, matching the style of the
reference issue-matrix.md's evidence-ref column (specific, verifiable, not vague). If any listed
issue's title is not already known precisely, look it up via the tracker before finalizing the
row (do not invent titles).

### T031 — Full verification
Run `uv run pytest` over the touched test files
(`tests/specify_cli/cli/commands/agent/test_freshness_checkbox_insensitive.py` and any existing
`tasks_move_task` rollback tests) plus a targeted pass over
`tests/specify_cli/cli/commands/agent/`. `uv run ruff check` + `uv run mypy` on
`tasks_move_task.py` and the new test file — zero new issues, zero new suppressions. Confirm full
`tests/architectural/` 0-failed, and specifically that the issue-matrix validator (if one runs as
part of the arch suite or a dedicated `spec-kitty` check) accepts the canonical
`Issue | Verdict | Evidence ref | Scope` columns and the four valid verdict values.

## Branch Strategy
Planning base branch and merge target branch are both `rework/ray-cluster-aggregation`;
`spec-kitty implement WP06` allocates an execution worktree per the lane computed from
`lanes.json`. No WP dependency — fully parallel with the WP01→WP02→WP03 spine and with WP04/WP05.
Owns `tasks_move_task.py` exclusively; no other WP touches this file (C-003).

## Definition of Done
- Rollback resets (claim-marker clear + subtask uncheck) are routed through one clearly-named
  seam (`_mt_reset_for_planned_rollback` plus, if the lock boundary requires it, a small named
  helper for the frontmatter clear) with no behavior change — proven by T028's production-path
  test (SC-006).
- FR-009 regression guard proves `_normalize_tasks_md`'s checkbox-insensitivity holds on both
  `write_analysis_report` and `check_analysis_report_current`, with a substantive-change negative
  control.
- `issue-matrix.md` records terminal verdicts for #2504/#2510/#2513/#2502/#2512/#1231 (fixed),
  #1862 (verified-already-fixed), #2160 (deferred-with-followup), using the canonical
  `Issue | Verdict | Evidence ref | Scope` schema.
- `uv run pytest` green on touched suites; `uv run ruff check` + `uv run mypy` clean, zero new
  suppressions; full `tests/architectural/` 0-failed.

## Risks
- **Widening the status lock to force a single call site** — the two rollback resets straddle the
  lock boundary today; forcing them into one physical call would change lock scope, which is a
  real behavior change FR-010 explicitly rules out ("no new reset behavior"). Prefer the
  named-seam approach over a structural merge.
- **Issue-matrix evidence drift** — if this WP is implemented before the other five land, its
  evidence-ref column will be speculative; re-verify against actual commit SHAs/PR numbers before
  the mission closes, not just at initial authoring.
- **FR-009 test accidentally validating nothing** — a freshness test that doesn't include the
  negative control (substantive change → hash changes) could pass even if the hashing mechanism
  were entirely broken. Include the negative control.

## Reviewer Guidance
Confirm: the rollback consolidation doesn't change lock scope or reset ordering; T028's test
exercises the actual CLI/production path, not the two reset functions in isolation; FR-009's test
covers both `write_analysis_report` and `check_analysis_report_current` with a positive
(checkbox-only, hash unchanged) and negative (substantive change, hash changes) case;
`issue-matrix.md` uses the canonical 4-column schema with real evidence, not placeholder text, by
the time the WP is submitted for review; ruff/mypy clean; full arch suite 0-failed.

## Activity Log
- {{TIMESTAMP}} — system — Prompt created at planning (tasks).
- 2026-07-12T11:04:00Z – claude:sonnet:python-pedro:implementer – shell_pid=4168956 – Assigned agent via action command
- 2026-07-12T12:17:59Z – user – shell_pid=4168956 – APPROVE (opus renata reject-then-fix): sole finding (new no-any-return mypy error in _mt_clear_rollback_claim_markers) fixed via assign-then-return; mypy back to 2-error baseline, ruff clean, 126 tests green; FR-010 lock-boundary intact, FR-009 test-only, T028 correct (00d7590fc)
