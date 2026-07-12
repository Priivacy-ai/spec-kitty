---
work_package_id: WP04
title: Workflow-dist lint + marker-baseline guards
dependencies:
- WP03
requirement_refs:
- C-001
- C-002
- C-005
- C-006
- C-007
tracker_refs: []
planning_base_branch: feat/ci-test-topology-performance
merge_target_branch: feat/ci-test-topology-performance
branch_strategy: Planning artifacts for this mission were generated on feat/ci-test-topology-performance. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-test-topology-performance unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
phase: Phase 1 - Substrate
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1311607"
shell_pid_created_at: "1783885200.62"
history:
- at: '2026-07-12T17:43:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_workflow_dist_lint.py
create_intent:
- tests/architectural/test_workflow_dist_lint.py
- tests/architectural/test_marker_baseline.py
- tests/architectural/marker_baseline.txt
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_workflow_dist_lint.py
- tests/architectural/test_marker_baseline.py
- tests/architectural/marker_baseline.txt
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Workflow-dist lint + marker-baseline guards

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
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
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

Formalize the two mission-wide committed guards that every downstream WP06 topology edit must pass, and that this mission's own C-005/C-007 constraints are otherwise unfalsifiable without:

- **GC-4** (`test_workflow_dist_lint.py`): a committed lint over `.github/workflows/*.yml` proving C-001 (no bare `--dist load`), C-002/C-007 (fixed-range real-port suites never appear under `-n auto`), and C-006 (every sharded matrix carries `strategy.fail-fast: false`).
- **GC-5** (`test_marker_baseline.py` + committed `marker_baseline.txt`): a diff guard proving C-005 — the identity/count of `@slow`/`@stress`/`@quarantine`-marked tests does not grow during this mission, replacing the unfalsifiable "purely to hit a budget" intent clause with an enforced baseline diff.

Done when:
- `test_workflow_dist_lint.py` is GREEN against today's `ci-quality.yml` (before WP06's edits land) and RED when a bare `--dist load`, a fixed-range suite under `-n auto`, or a sharded matrix missing `fail-fast: false` is fault-injected.
- `marker_baseline.txt` is committed with today's exact `@slow`/`@stress`/`@quarantine` node-id set, and `test_marker_baseline.py` fails when the committed set grows (a fault-injection case proves it bites).
- Both guards run under `tests/architectural/` (the `architectural` marker) and are enrolled implicitly by the existing arch-adversarial job — no new job needed for WP04 itself (WP06/T020 handles roster edits for *new jobs*, not these two test files).

## Context & Constraints

- Read `kitty-specs/ci-test-topology-performance-01KXBJRT/contracts/guard-contracts.md` GC-4 and GC-5 before writing anything — those are the literal invariant lists this WP encodes.
- Read `kitty-specs/ci-test-topology-performance-01KXBJRT/spec.md` constraints C-001, C-002, C-005, C-006, C-007 — this WP is the committed-guard realization of those five constraints.
- **Dependency**: WP03 (`tests/_real_port_suites.py`, `FIXED_RANGE_SUITES`) must land first — GC-4's "fixed-range suites never under `-n auto`" check consumes that registry directly rather than re-deriving the daemon-family list. Do not hardcode a second list of real-port test files; import `FIXED_RANGE_SUITES` from `tests/_real_port_suites.py`.
- Model the parsing approach on the existing `tests/architectural/test_serial_port_preservation.py` (also new-in-mission, also parses `.github/workflows/*.yml` run scripts with `yaml.safe_load` + regex over the shell command strings, and already proves the "fault-injection, not vacuous-pass" pattern this mission requires per D-041/D-030). Reuse its YAML-loading helpers if they are already committed by WP03 rather than re-implementing a second parser (canonical-sources discipline).
- `strategy.fail-fast: false` (C-006) is a structural YAML field on the job's `strategy:` block, not a shell-command token — parse it from the loaded job mapping (`job["strategy"]["fail-fast"]`), not with regex over run-script text.
- GC-5's baseline is a **snapshot of today's marker set**, taken before WP06 changes any job selection. Generate it by running the real collector (`pytest --collect-only -q -m "slow or stress or quarantine"`) against the current tree and freezing the resulting node-id list — do not hand-write it.
- This WP has no dependency on WP06 itself; WP06 depends on WP04 landing (transitively via WP03) so its topology edits can be validated against these guards as they are written.

## Branch Strategy

- **Strategy**: Coordination-topology mission — this WP's changes land on a lane/feature branch and merge back through the mission's coordination branch (`kitty/mission-ci-test-topology-performance-01KXBJRT`) into the mission target branch. Confirm the exact lane assignment via `lanes.json` (materialized by `spec-kitty agent mission tasks-finalize`) at implement time — do not assume a lane id here.
- **Planning base branch**: `feat/ci-test-topology-performance`
- **Merge target branch**: `feat/ci-test-topology-performance`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### T012 – `test_workflow_dist_lint.py` (GC-4)

- **Purpose**: Give C-001/C-002/C-006/C-007 a single committed enforcement point, instead of each per-job WP6 subtask re-proving distribution correctness ad hoc. Every future job edit either satisfies this guard or fails CI.
- **Steps**:
  1. Load every `.github/workflows/*.yml` file with `yaml.safe_load` (module scope; parse once, reuse across assertions — mirror the existing `_gate_coverage` / `test_serial_port_preservation.py` loading pattern).
  2. For every job's every `run:` step string, regex-scan for `--dist\s+load\b` (word boundary, so `loadfile` does not false-positive) and for `-n\s+auto` occurrences.
  3. Assert: **no** run-script string matches `--dist\s+load(?!file)` (bare `load`).
  4. Assert: every run-script string containing `-n auto` also contains `--dist loadfile` in the same command (same `run:` block — commands are typically multi-line `|` blocks, so search the whole block, not line-by-line).
  5. Import `FIXED_RANGE_SUITES` from `tests/_real_port_suites.py` (WP03). Assert: no run-script string containing `-n auto` also references any path from `FIXED_RANGE_SUITES` (neither a bare path token nor inside a `-m` marker expression that would still collect it — check both the explicit path arguments and any `--ignore=` counter-evidence is present when the suite is *not* directly named).
  6. For every job that declares a `strategy: {matrix: ...}` block, assert `job["strategy"].get("fail-fast") is False` — a matrix with `fail-fast` absent (defaults to `True` in GitHub Actions) or `fail-fast: true` must fail this assertion (C-006).
  7. Write at least one fault-injection test per invariant (5 total: bare `load`, missing `loadfile` pairing, fixed-range-under-`-n auto`, matrix missing `fail-fast: false`, and the vacuous-pass canary — assert the guard is non-trivially satisfied by counting that it actually inspected `>0` run-script strings and `>0` matrix jobs, so an empty parse can't pass green).
- **Files**: `tests/architectural/test_workflow_dist_lint.py` (new).
- **Parallel?**: Sequential with T013 in this WP (same file surface area, share the YAML-loading helper), but WP04 as a whole is independent of WP04's own T013 in execution order — write T012 first since T013's baseline-diff pattern is simpler and can reuse the same module-scope YAML fixture if convenient.
- **Notes**: This guard must stay GREEN against the *current* (pre-WP06) `ci-quality.yml` — run it before WP06 starts editing, to prove it isn't accidentally already red on the baseline topology. If it is red today (e.g. an existing bare `--dist load` already exists somewhere), that is a real finding — do not weaken the assertion to paper over it; escalate to the WP06 owner so the fix lands as part of that WP's edits.

### T013 – `test_marker_baseline.py` + `marker_baseline.txt` (GC-5)

- **Purpose**: Replace spec constraint C-005's unfalsifiable "no marker moved purely to hit a budget" intent clause with an enforced baseline diff: the *identity and count* of `@slow`/`@stress`/`@quarantine`-marked tests must not grow during this mission.
- **Steps**:
  1. Generate the baseline by running (or programmatically invoking pytest's collection API) against the current tree: `uv run python -m pytest --collect-only -q -m "slow or stress or quarantine" tests/ 2>&1 | grep '::'` (or the project's existing collect-only helper if `tests/architectural/_gate_coverage.py` already exposes one — check before hand-rolling a second collector).
  2. Sort the resulting node-id list deterministically and commit it verbatim as `tests/architectural/marker_baseline.txt` (one node-id per line, no trailing metadata).
  3. Write `test_marker_baseline.py`: at test time, re-collect the same `-m "slow or stress or quarantine"` selection live, and assert `set(current_node_ids) <= set(committed_baseline)` is **not** the check — the invariant is "count/identity does not *grow*", so assert the *symmetric difference restricted to additions* is empty: every currently-collected node-id must already be present in the baseline. Shrinking (a test removed, or a node-id renamed because the underlying test moved) is allowed and does not fail this guard; growth is what fails it.
  4. Add a fault-injection test: monkeypatch/parametrize a synthetic "current" set that includes one extra node-id not in the baseline, and assert the guard's core comparison function reds.
  5. Document in the test module's docstring (mirroring `test_serial_port_preservation.py`'s docstring style) that this guard is deliberately *not* a hard membership-equality check, and why (mission WP06 may legitimately rename/rescope files without adding new slow-marked tests).
- **Files**: `tests/architectural/test_marker_baseline.py` (new), `tests/architectural/marker_baseline.txt` (new, committed data).
- **Parallel?**: Can be written independently of T012 (different guard, different assertions) but both land in this single WP/commit since they share `owned_files`.
- **Notes**: If baseline regeneration is ever legitimately required later in this mission (e.g. WP06 discovers a test that was mis-marked `@slow` and should be `@fast`), regenerate `marker_baseline.txt` deliberately with a comment noting *why*, per the invariant's own "regenerated only when the intended selection legitimately changes; never silently" rule (mirrors E3's baseline-manifest invariant in `data-model.md`).

## Test Strategy

Tests are the deliverable for this WP — there is no product code to modify.

- Run both new guards directly and confirm they select cleanly and pass on today's tree:
  ```bash
  uv run pytest tests/architectural/test_workflow_dist_lint.py tests/architectural/test_marker_baseline.py -v --tb=short
  ```
- Confirm the fault-injection cases actually fail when the injected fixture is malformed (temporarily invert an assertion locally to prove the test would catch a real regression, then revert — do not commit an inverted assertion):
  ```bash
  uv run pytest tests/architectural/test_workflow_dist_lint.py -k "fault_injection or bare_load or fail_fast" -v
  uv run pytest tests/architectural/test_marker_baseline.py -k "fault_injection or grows" -v
  ```
- Confirm collection doesn't silently vacuous-pass (0 items inspected):
  ```bash
  uv run pytest tests/architectural/test_workflow_dist_lint.py --collect-only -q
  ```
- Run the full architectural suite once both files are in place to confirm no regression in sibling guards (e.g. `test_serial_port_preservation.py`, `_gate_coverage`-backed tests):
  ```bash
  uv run pytest tests/architectural/ -m architectural -q --tb=short
  ```
- Verify `ruff check tests/architectural/test_workflow_dist_lint.py tests/architectural/test_marker_baseline.py` and `mypy` on the same two files are clean before marking done.

## Risks & Mitigations

- **Risk**: Regex-based YAML/shell parsing is brittle against multi-line `run: |` blocks with embedded comments (the codebase's existing workflow file has extensive `# PENDING-CI` comment blocks inside `run:` steps — see e.g. `fast-tests-sync`). **Mitigation**: strip full-line `#`-prefixed comments before regex-scanning each run-script string, and test against the real file, not a synthetic fixture, for at least one assertion per invariant.
- **Risk**: GC-4's "fixed-range suite never under `-n auto`" check could false-positive on jobs that merely *ignore* the suite (e.g. `fast-tests-sync`'s `--ignore=tests/sync/test_orphan_sweep.py` inside an `-n auto` command is CORRECT, not a violation). **Mitigation**: the assertion must check for the suite's path being *collected* (present as a positional arg or NOT excluded via `--ignore=<that path>` when the parent directory is collected), not merely "the string exists somewhere in the command" — write this as an explicit test case using the real `fast-tests-sync` job as a positive (should stay green) example.
- **Risk**: Running the real collector to generate `marker_baseline.txt` is slow / environment-sensitive (collection can pick up different tests depending on installed extras). **Mitigation**: generate the baseline with the same `uv sync --frozen --all-extras` environment CI uses, and note the generation command as a comment at the top of `marker_baseline.txt`.

## Review Guidance

- Confirm both guards are RED against at least one fault-injected violation per invariant (do not accept a guard that is provably vacuous).
- Confirm `test_workflow_dist_lint.py` imports `FIXED_RANGE_SUITES` from `tests/_real_port_suites.py` rather than hardcoding a duplicate list (canonical-sources / D-044 unification check).
- Confirm `marker_baseline.txt` reflects a real `pytest --collect-only` run against the current tree, not a hand-typed guess — spot-check a handful of node-ids against `git grep -n "@pytest.mark.slow"` results.
- Confirm `test_marker_baseline.py`'s comparison is "no growth", not "no change" — re-read C-005 and GC-5 to confirm shrink/rename paths are intentionally permitted.
- Confirm `ruff`/`mypy` are clean on both new files with no suppression comments added.

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

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-12T17:43:44Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP04 --to <status>` to change WP status.
- 2026-07-12T19:23:01Z – claude:sonnet:python-pedro:implementer – shell_pid=1278830 – Assigned agent via action command
- 2026-07-12T19:39:03Z – claude:sonnet:python-pedro:implementer – shell_pid=1278830 – Ready: GC-4 a/b/c live-green, check-d strict-xfail (#2590); GC-5 marker-baseline committed; 18 passed/1 xfailed/0 failed; arch regression: two new files pass in isolation, full arch pass deferred to reviewer
- 2026-07-12T19:40:03Z – claude:opus:reviewer-renata:reviewer – shell_pid=1311607 – Started review via action command
- 2026-07-12T19:43:59Z – user – shell_pid=1311607 – Review passed: GC-4 a/b/c live-green + fault-injected, check-d strict-xfail (#2590), GC-5 no-growth via canonical collector; 0 failed
