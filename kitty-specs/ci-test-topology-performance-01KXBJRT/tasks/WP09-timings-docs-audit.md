---
work_package_id: WP09
title: Timings artifact + docs + cross-cutting audit
dependencies:
- WP06
requirement_refs:
- FR-008
- FR-009
tracker_refs: []
planning_base_branch: feat/ci-test-topology-performance
merge_target_branch: feat/ci-test-topology-performance
branch_strategy: Planning artifacts for this mission were generated on feat/ci-test-topology-performance. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-test-topology-performance unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
phase: Phase 4 - Close
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1819151"
shell_pid_created_at: "1783896399.9"
history:
- at: '2026-07-12T17:43:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/plans/testing/
create_intent:
- docs/plans/testing/ci-job-timings.md
execution_mode: code_change
model: ''
owned_files:
- docs/guides/testing-parallel.md
- docs/plans/testing/test-suite-acceleration-plan.md
- docs/plans/testing/ci-job-timings.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – Timings artifact + docs + cross-cutting audit

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Record measured, real per-leg CI wall-clock as a committed artifact so budgets (NFR-001..008) are ratcheted, not asserted live (FR-008).
- Run the cross-cutting audit proving the executed-test *union* is unchanged across every job WP01–WP06 re-topologized (GC-2b), catching anything the per-WP guards missed at the seams.
- Bring the canonical topology docs current with the shipped state so they do not drift the day this mission merges (FR-009).
- **Dependency**: this WP is the last to run — it depends on **WP06** (`.github/workflows/ci-quality.yml` topology edits) because there is nothing real to measure, audit, or document until the topology has actually shipped. Per tasks.md's dependency graph: `WP01 ─┬─> WP02 └─> WP06 ──> WP09`.

## Context & Constraints

Per plan.md IC-07: "budgets are noisy wall-clock — record, don't hard-gate (flakiness policy); docs drift if not landed same-mission." This mirrors the project's own flakiness policy in `docs/guides/testing-flakiness.md`: never retry-to-green, never assert a threshold that a noisy CI runner can flip red. The `_TIMINGS_BASELINE` pattern already exists in `tests/architectural/_gate_coverage.py` (see data-model.md E4) — this WP produces the equivalent shape as a standalone committed artifact rather than adding a new hard-gated test.

**T025 (FR-008, E4)** — after WP06's topology has run for real on CI, capture the actual per-leg/per-job minutes from the workflow run's job summary (or `--durations=25` output added by WP06's T014/T019) into a new committed file `docs/plans/testing/ci-job-timings.md`, shaped like E4 (data-model.md):

| Field | Type | Meaning |
|-------|------|---------|
| `job/leg` | str | job or matrix-leg name, e.g. `integration-tests-next / next_shard_2` |
| `minutes` | float | measured wall-clock |
| `run_id` | str | GitHub Actions run id (provenance) |

Include every job/leg this mission touched: `integration-tests-next` (3 `next_shard_N` legs), `slow-tests`, the new orphan-sweep job (WP06 T016), `fast-tests-core-misc` (rebalanced legs), `fast-tests-charter` (split jobs), `fast-tests-cli` (WP05's split), and the serial `integration-tests-*` jobs swept by WP06 T019. Cross-check each row against its NFR target from spec.md (NFR-001 `integration-tests-next` ≤7min, NFR-002 `slow-tests` ≤4min, NFR-004 `fast-tests-cli` ≤5.5min, NFR-006 shard-skew ≤20%, NFR-007 `fast-tests-core-misc` ≤7min, NFR-008 `fast-tests-charter` ≤7min) and note in the file whether each was met — budgets are recorded facts here, not new pass/fail test assertions.

**T026 (GC-2b audit)** — this is a *verification* task, not new production code: for every job WP01–WP06 changed selection on, confirm the WP-level completeness guard (GC-1/GC-2/GC-2b per contracts/guard-contracts.md) is green, and additionally hand-audit the union across job boundaries — specifically the cross-job disjointness clause of GC-2 ("the serial `-n0` orphan-sweep job's selection ∩ the parallel pool's selection == ∅") and any place two re-topologized jobs could now both select the same node-id (double-run) or where a matrix leg's selection could silently drop items on a `fail-fast` cancellation (C-006 requires `fail-fast: false` everywhere sharded — confirm this held for every new/changed matrix, not just the ones WP02/WP04 directly guard). Report findings; if drift is found, it blocks this WP's completion until the owning WP (WP01–WP06) fixes it — do not paper over a real gap in the docs.

**T026 Definition of Done hardening (reviewer-renata, HIGH)** — as scoped above, T026's audit is a *prose claim*: nothing stops an agent from writing "audit clean" in the Activity Log without actually running a diff. That is not acceptable for a task whose whole purpose is to catch cross-WP seam gaps GC-2b's per-WP guards would miss. The audit is only Done when it produces **committed, real per-job diff evidence**, not a sentence:
- Commit a checked-in audit artifact — either a new `docs/plans/testing/ci-coverage-union-audit.md` OR an appended section in `docs/plans/testing/ci-job-timings.md` (confirm whichever path you pick lives under this WP's owned `docs/plans/testing/**` surface; no ownership change is needed for either option, but verify the exact path before committing).
- That artifact must contain, **per re-topologized job**: the real post-change `pytest --collect-only` node-id count, and the `diff`-vs-WP02-baseline exit status (0 = clean, nonzero = drift, with the drift itself quoted or attached).
- Preferred method: re-run the WP02 GC-2b guard (`pytest tests/architectural/test_gate_coverage.py -k baseline_union` or equivalent per WP02's actual test name) for each job and commit its real output (or a faithful transcript of it) into the audit artifact — do not hand-summarize the guard's result in your own words as a substitute for its actual output.
- An Activity Log sentence like "ran the audit, found no gaps" is insufficient on its own and must be rejected at review if the committed artifact with real per-job diff evidence is missing.

**T027 (FR-009)** — update:
- `docs/guides/testing-parallel.md` — reflect the new `next_shard_N` matrix (mirroring the existing arch-shard documentation pattern), the promoted orphan-sweep job, and the rebalanced `fast-tests-core-misc`/`fast-tests-charter` topology.
- `docs/plans/testing/test-suite-acceleration-plan.md` — mark this mission's WPs as shipped against the plan's original targets; reconcile any target that changed during implementation (e.g., an NFR that landed at a different figure than originally proposed) rather than leaving the plan silently stale.

Per CLAUDE.md's "Pre-push: run the terminology guard" note — this WP touches doctrine-adjacent prose (`docs/guides/`), so `tests/architectural/test_no_legacy_terminology.py` is a required gate here specifically (it only runs in CI's `integration-tests-core-misc` job, not in local fast-tests, so run it explicitly before finishing).

## Branch Strategy

- **Strategy**: Single mission branch — implement directly in the WP's execution workspace created by `spec-kitty implement WP09`. This WP is the terminal node in the dependency graph; do not start it until WP06 is `approved` or `done` (dependency gating enforced by `dependency_readiness_for_wp()`).
- **Planning base branch**: `feat/ci-test-topology-performance`
- **Merge target branch**: `feat/ci-test-topology-performance` (mission branch merges to local `main` via `spec-kitty merge`; a PR to `main` follows per CLAUDE.md's no-direct-push policy).

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T025 – Committed timings artifact (FR-008, E4)

- **Purpose**: Replace "we think it's faster" with a provenance-carrying, committed record.
- **Steps**: trigger (or use) a real post-WP06 CI run of `ci-quality.yml`; pull the job/leg durations (from `--durations=25` output or the Actions run summary); write `docs/plans/testing/ci-job-timings.md` in the E4 shape above with the run id.
- **Files**: `docs/plans/testing/ci-job-timings.md` (new — listed in `create_intent`).
- **Parallel?**: Must follow WP06's merge; can run alongside T026/T027 within this WP.
- **Notes**: If a runner-core-count assumption changes the interim budget (plan.md Technical Context: "assume ≥4 cores"), record the observed core count alongside the run id so a future re-measurement has the same context.

### Subtask T026 – Cross-cutting coverage-union audit (GC-2b)

- **Purpose**: Catch cross-WP seam gaps that no single WP's guard would see (e.g. two independently-correct WPs whose combined selection double-runs or drops a node-id).
- **Steps**: re-run each re-topologized job's completeness guard; diff each job's post-change collected node-ids against its WP02 baseline manifest (`tests/architectural/baselines/<job>-nodeids.txt`); manually confirm the orphan-sweep job (WP06 T016) and the parallel pool it was extracted from have disjoint selections; confirm every sharded matrix touched by this mission carries `fail-fast: false`. **Then commit the evidence** (reviewer-renata, HIGH): write a real per-job node-id count + diff-exit-status table into a committed artifact (`docs/plans/testing/ci-coverage-union-audit.md`, new, OR an appended section in `docs/plans/testing/ci-job-timings.md`) — re-running the WP02 GC-2b guard and committing its actual output is the preferred way to produce this evidence.
- **Files**: `docs/plans/testing/ci-coverage-union-audit.md` (new, if chosen — add to `create_intent`) or an appended section of `docs/plans/testing/ci-job-timings.md` (already owned/`create_intent`-listed via T025); this is otherwise a verification pass reported in the Activity Log and, if it changes recommended doc language, feeding T027.
- **Parallel?**: Depends on WP06's shipped topology same as T025.
- **Notes**: If this audit finds a real gap, it is a blocking finding for the owning WP, not something to silently work around in docs. A prose-only Activity Log claim ("audit clean") without the committed per-job diff artifact is not Done — see the Definition of Done hardening in Context & Constraints.

### Subtask T027 – Update testing docs (FR-009)

- **Purpose**: Keep the canonical topology docs from drifting the moment this mission merges.
- **Steps**: update `docs/guides/testing-parallel.md` and `docs/plans/testing/test-suite-acceleration-plan.md` per Context & Constraints; run `pytest tests/architectural/test_no_legacy_terminology.py` before finishing.
- **Files**: `docs/guides/testing-parallel.md`, `docs/plans/testing/test-suite-acceleration-plan.md`.
- **Parallel?**: Can start once WP06's topology is stable, in parallel with T025/T026 within this WP.
- **Notes**: Do not describe budgets as guaranteed/enforced in the docs — mirror the plan's own framing ("measured-and-recorded targets, not hard CI gates").

## Test Strategy (include only when tests are required)

- No new pytest guard is authored by this WP (T025/T027 are docs/data artifacts; T026 is a verification pass over already-shipped guards).
- Verify each re-topologized job's own completeness guard is green: `pytest tests/architectural/ -k "shard_marker_completeness or gate_coverage or serial_port_preservation or workflow_dist_lint or marker_baseline" -q`.
- **T026 evidence check (reviewer-renata, HIGH)**: confirm the committed audit artifact (`docs/plans/testing/ci-coverage-union-audit.md` or an appended section of `ci-job-timings.md`) exists and contains, per re-topologized job, a real post-change `pytest --collect-only` node-id count and a `diff`-vs-WP02-baseline exit status — not merely an Activity Log sentence. Re-running the WP02 GC-2b guard and committing its output satisfies this.
- Verify the new `docs/plans/testing/ci-job-timings.md` parses as valid Markdown with a real, non-placeholder run id (no `TODO`/`TBD` left in the committed file).
- `pytest tests/architectural/test_no_legacy_terminology.py` — required for the docs prose changes (CLAUDE.md pre-push gate).
- Full local sweep before finishing: `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider` plus the serial real-port pass `PWHEADLESS=1 pytest tests/sync/test_orphan_sweep.py -n0 -q`, confirming green after all mission WPs have landed.

## Risks & Mitigations

- **Risk**: measuring on a single noisy CI run and treating it as gospel. **Mitigation**: note in `ci-job-timings.md` that figures are a single measured run with provenance, not a statistical guarantee; a future re-measurement is expected to update this file, not append a second conflicting one.
- **Risk**: T026's audit surfaces a real gap late, after WP01–WP06 are already `approved`/`done`, creating rework pressure to skip it. **Mitigation**: treat a found gap as a genuine blocking defect (per CLAUDE.md's "Failing-test remediation framework" — never retry-to-green, never paper over); file it back to the owning WP rather than silently adjusting this WP's docs to match broken behavior.
- **Risk**: docs update (T027) becomes stale again immediately if a later WP's numbers shift before merge. **Mitigation**: run T025/T026/T027 as the very last WP, after WP06 (and ideally WP01–WP05, WP07, WP08) have landed, per the dependency graph.

## Review Guidance

- Confirm `docs/plans/testing/ci-job-timings.md` exists, is E4-shaped, and carries a real run id.
- Confirm the audit (T026) is documented with an explicit outcome (clean, or gaps found + how they were resolved) — not silently skipped.
- **Reject a prose-only T026 claim** (reviewer-renata, HIGH): the audit must carry a committed artifact with real per-job evidence (post-change `pytest --collect-only` node-id counts + diff-vs-WP02-baseline exit status per re-topologized job) — an Activity Log sentence like "ran the audit, no gaps found" without that artifact does not satisfy T026's Definition of Done.
- Confirm `docs/guides/testing-parallel.md` and `docs/plans/testing/test-suite-acceleration-plan.md` describe the topology that actually shipped in WP01–WP08, not the original spec-time proposal.
- Confirm `tests/architectural/test_no_legacy_terminology.py` was run and passed.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Common mistakes (DO NOT DO THIS)**:

- Adding new entry at the top (breaks chronological order)
- Using future timestamps (causes acceptance validation to fail)
- Inserting in middle instead of appending to end

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-12T17:43:44Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP09 --to <status>` to change WP status.
- 2026-07-12T22:16:07Z – claude:sonnet:curator-carla:implementer – shell_pid=1676253 – Assigned agent via action command
- 2026-07-12T22:44:52Z – claude:sonnet:curator-carla:implementer – shell_pid=1676253 – Ready: committed coverage-union audit (GC-2b green for integration-tests-next/slow-tests; fast-tests-core-misc RED but proven 0 real drift, filed #2607), timings artifact (post-change wall-clock PENDING real CI run), testing docs updated; terminology guard green
- 2026-07-12T22:46:42Z – claude:opus:reviewer-renata:reviewer – shell_pid=1819151 – Started review via action command
