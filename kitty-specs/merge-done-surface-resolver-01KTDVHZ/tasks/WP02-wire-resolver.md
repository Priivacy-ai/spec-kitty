---
work_package_id: WP02
title: Merge-Path Audit and Wire Resolver
dependencies:
- WP01
requirement_refs:
- C-002
- C-005
- C-006
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T000
- T001
- T002
- T003
- T004
- T009
- T010
- T011
- T012
- T013
agent: claude
history:
- date: '2026-06-06'
  event: created
  note: Initial task generation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/merge.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

This WP has two parts that must be done in order:

**Part A (Audit — T001–T004)**: Read the full merge path in `src/specify_cli/cli/commands/merge.py` and every module it calls that touches `status.events.jsonl`. Identify every write site and every read site. Assess each for the locate-vs-observe surface divergence class (coordination branch write vs primary checkout read). Commit a concise audit note inline as a code comment in `merge.py` summarizing the findings.

**Part B (Wire — T009–T013)**: Using `resolve_status_surface` from WP01, update both `_mark_wp_merged_done` and `_assert_merged_wps_reached_done` in `merge.py` to read and write from the same surface. Apply any additional fixes found in Part A. Run the regression suite.

WP01 must be complete before this WP starts.

---

## Context

### The Bug (confirmed by five-paradigm investigation)

When `coordination_branch` is set in `meta.json`:

| | Code site | Surface |
|---|---|---|
| **Write** | `_mark_wp_merged_done` → `emit_status_transition_transactional` → `BookkeepingTransaction` | Coordination worktree (`.worktrees/<slug>-<mid8>-coord/`), committed to coordination branch |
| **Read-back** | `_assert_merged_wps_reached_done` → `get_wp_lane` → `read_events` → `Path.read_text()` | Primary checkout `kitty-specs/<slug>/status.events.jsonl` |

The write goes where the assertion does not look. The assertion fires at line 1797; `safe_commit` (which would flush coord-branch events to primary checkout) is at line 1864 — structurally after the assertion.

### Scope boundary (from spec C-005)

"Merge path" means all code within `merge.py` and any modules it directly calls that touch `status.events.jsonl`. Runtime read sites already fixed by #1589 (`move-task`, `next`, `lane_reader` in non-merge context) are NOT re-audited unless a merge-path call delegates to them.

---

## Subtask T000: Write Failing ATDD Test (ATDD Anchor)

**Purpose**: Commit a RED test that asserts `_assert_merged_wps_reached_done` reads from the coordination surface before any implementation begins. This satisfies charter C-011 (ATDD-First): the failing test must be committed before T001–T013.

**CRITICAL**: This subtask must be completed and committed as a standalone commit (test-only, no implementation) BEFORE proceeding to T001 (audit) or T009 (wire).

**Steps**:

1. Write a test in `tests/specify_cli/cli/commands/test_merge.py` (or `tests/merge/test_merge_done_recording.py`) that:
   - Sets up a minimal mission fixture with `coordination_branch` in `meta.json` and a coordination worktree stub containing a `done` event in `status.events.jsonl`
   - Calls `_assert_merged_wps_reached_done(repo_root, mission_slug, [wp_id])` with the primary checkout's events file absent (or empty)
   - Asserts the function does NOT raise (i.e., the function reads from the coordination surface)
   - This test will FAIL on the current codebase — that is the intent

2. Commit the failing test:
   ```bash
   git add tests/
   git commit -m "test(merge): failing ATDD anchor for coord-branch assertion surface [RED]

   Commit a failing test per ATDD-First (C-011). The test asserts that
   _assert_merged_wps_reached_done reads from the coordination surface
   when coordination_branch is set. It fails until WP02 wires the resolver.

   Relates-to: #1726"
   ```

3. Verify the test is RED (fails on current code before the fix):
   ```bash
   .venv/bin/pytest <test_file>::<test_name> -v
   # Expected: FAILED — confirms the test is the right shape
   ```

Do NOT implement any fix in this subtask. The test must be RED at commit time.

---

## Part A: Merge-Path Status Sites Audit

### Subtask T001: Enumerate Status Write Sites

**Purpose**: Find every place in the merge path where status events are written (appended to `status.events.jsonl`).

**Steps**:
1. Read `src/specify_cli/cli/commands/merge.py` fully. Search for calls to: `emit_status_transition`, `emit_status_transition_transactional`, `append_event`, `safe_commit` (when it flushes status files), and any other pattern that writes to `status.events.jsonl`.
2. For each write site found, record: function name, line number, whether it calls via `emit_status_transition_transactional` (coord-branch-aware) or directly via `append_event` (primary checkout only).
3. If a write site delegates to another module, read that module to trace the full call chain.

**Expected output** (internal, feeds T004): A list of write sites with their routing behaviour.

---

### Subtask T002: Enumerate Status Read Sites

**Purpose**: Find every place in the merge path where status events are read (from `status.events.jsonl`).

**Steps**:
1. In `merge.py`, search for calls to: `get_wp_lane`, `read_events`, `read_current_wp_state_transactional`, `materialize`, `reduce`, `get_wp_state`, and any other pattern that reads from `status.events.jsonl`.
2. For each read site found, record: function name, line number, whether it is coordination-branch-aware (reads from the coordination ref) or reads directly from the primary checkout filesystem path.
3. Note the call ordering relative to `safe_commit` (line ~1864) — does the read happen before or after the flush?

**Expected output** (internal, feeds T004): A list of read sites with their surface awareness.

---

### Subtask T003: Assess Each Site for Divergence

**Purpose**: For each write site identified in T001 and each read site in T002, determine whether a divergence scenario exists where the write goes to the coordination branch but the read does not.

**Assessment criteria** (mark each site as one of):
- `SAFE` — Both write and read are on the same surface (either both coordination-aware, or both primary-checkout).
- `DIVERGENT` — Write is coordination-branch-aware; corresponding read is not (or vice versa).
- `INDETERMINATE` — Cannot determine without runtime topology information; needs flag.
- `ALREADY_FIXED` — Previously addressed by #1589 on the runtime path; not a merge-path issue.

**Key known divergence** (confirmed by five-paradigm investigation):
- `_mark_wp_merged_done` (write via `emit_status_transition_transactional`) vs `_assert_merged_wps_reached_done` (read via `get_wp_lane` → `read_events`) — **DIVERGENT**, confirmed.

Any additional DIVERGENT sites beyond this pair are in-scope for T012.

---

### Subtask T004: Document Audit Findings as Code Comment

**Purpose**: Record the audit results directly in `merge.py` so the finding is co-located with the code.

**Steps**:

Add a comment block in `merge.py` near the done-marking loop (around line 1782) summarizing:

```python
# Merge-path status surface audit (mission merge-done-surface-resolver-01KTDVHZ):
# Write sites: [list function names and whether coord-branch-aware]
# Read sites:  [list function names and whether coord-branch-aware]
# DIVERGENT:   _mark_wp_merged_done (write, coord) vs _assert_merged_wps_reached_done (read, primary) — FIXED below
# Additional DIVERGENT sites: [none found / list any]
# Audit date: 2026-06-06
```

Keep it concise (5–8 lines). This comment is the audit artifact; it replaces the previously planned external audit document.

---

## Part B: Wire Resolver into Done-Marking Loop

### Subtask T009: Read and Understand the Current Callers

**Purpose**: Before making any changes, fully understand how `_mark_wp_merged_done` and `_assert_merged_wps_reached_done` currently work, so the fix is minimal and correct.

**Steps**:

1. Read `_mark_wp_merged_done` at `merge.py:~223`. Answer:
   - What arguments does it receive (`repo_root`, `mission_slug`, `wp_id`, `target_branch`)?
   - Where does it call `emit_status_transition_transactional`? What arguments does it pass?
   - Does it pass `feature_dir` to the emit call, or just `repo_root` + `mission_slug`?
   - Does it call any intermediate function that resolves `feature_dir` before the emit call?

2. Read `_assert_merged_wps_reached_done` at `merge.py:~348`. Answer:
   - What arguments does it receive?
   - How does it derive `feature_dir` before calling `get_wp_lane`?
   - What does `get_wp_lane(feature_dir, wp_id)` expect as `feature_dir` — the mission directory root, or the `status.events.jsonl` file path?

3. Read the done-marking loop at `merge.py:~1782–1797`. Confirm which `repo_root` and `mission_slug` values are passed.

**Output**: Notes on the exact call signatures and the minimal change needed.

---

### Subtask T010: Update `_mark_wp_merged_done`

**Purpose**: Ensure the write side uses `resolve_status_surface`.

**Important**: Read `_mark_wp_merged_done` fully before changing it. The key question from T009 is whether the write already goes through `emit_status_transition_transactional` (which internally routes to the coordination branch when `coordination_branch` is set). If so, the write is already going to the correct surface — the problem is only on the read side.

**Two possible scenarios**:

**Scenario A** (most likely): `emit_status_transition_transactional` already routes to the coordination branch internally. The write is already correct. No change needed to `_mark_wp_merged_done` for the write path itself.
→ In this case, T010 becomes a verification task: confirm the write is already coordination-branch-aware, and document this in the audit comment (T004).

**Scenario B** (less likely): `_mark_wp_merged_done` bypasses `emit_status_transition_transactional` and writes directly to a path derived without topology awareness.
→ In this case, update it to resolve the surface path via `resolve_status_surface(repo_root, mission_slug)` and pass it to the write call.

**Regardless of which scenario**: Add an import for `resolve_status_surface` from `specify_cli.coordination.surface_resolver` at the top of `merge.py`.

---

### Subtask T011: Update `_assert_merged_wps_reached_done`

**Purpose**: Make the read-back assertion read from the same surface as the write.

**Steps**:

1. Find the `feature_dir` derivation in `_assert_merged_wps_reached_done` (`merge.py:~348`). Currently it calls `resolve_feature_dir_for_mission(repo_root, mission_slug)` which returns the primary-checkout `feature_dir`.

2. Replace the `feature_dir` derivation with the surface resolver:
   ```python
   from specify_cli.coordination.surface_resolver import resolve_status_surface

   # Replace:
   feature_dir = resolve_feature_dir_for_mission(repo_root, mission_slug)
   # With:
   surface_path = resolve_status_surface(repo_root, mission_slug)
   feature_dir = surface_path.parent  # surface_path is the .jsonl file; parent is the mission dir
   ```

3. Verify that `get_wp_lane(feature_dir, wp_id)` expects a directory path (not a file path). If it constructs `feature_dir / "status.events.jsonl"` internally, then passing `surface_path.parent` is correct. If it expects the full file path, pass `surface_path` directly and adjust the call.

4. Confirm that the `feature_dir` argument is the only thing that needs to change — i.e., `get_wp_lane` itself does not need modification (it should remain topology-agnostic; only the path it receives changes).

**Invariant to preserve**: After this change, when `coordination_branch` is set, both `_mark_wp_merged_done` and `_assert_merged_wps_reached_done` resolve to paths inside `.worktrees/<slug>-<mid8>-coord/`. When absent, both resolve to `kitty-specs/<slug>/` in the primary checkout.

---

### Subtask T012: Apply Additional Audit Findings

**Purpose**: Apply any additional DIVERGENT site fixes identified in Part A (T001–T003).

**Steps**:

1. Review the audit comment written in T004, section "Additional DIVERGENT sites".

2. **If no additional sites**: The T004 comment already documents this. Proceed to T013.

3. **If additional sites found**: For each DIVERGENT site, apply the same pattern as T011 — use `resolve_status_surface` to determine the correct read path. Keep changes minimal and focused on surface resolution only.

---

### Subtask T013: Run Regression Suite

**Purpose**: Confirm that the fix does not break any existing tests.

**Steps**:

1. Run the existing merge test suite:
   ```bash
   .venv/bin/pytest tests/specify_cli/cli/commands/test_merge.py -v
   .venv/bin/pytest tests/merge/ -v
   ```

2. If any tests fail:
   - Check if the failure is in a test that mocks `emit_status_transition_transactional` or `get_wp_lane`. If so, the mock may now be receiving a different `feature_dir` argument — update the mock's assertion to match the new surface-resolved path, but do **not** weaken the mock's validation.
   - If the failure is in a test that does not mock those functions, investigate the root cause before proceeding.

3. Run mypy on changed files:
   ```bash
   .venv/bin/mypy --strict src/specify_cli/cli/commands/merge.py
   .venv/bin/mypy --strict src/specify_cli/coordination/surface_resolver.py
   ```

4. Run ruff:
   ```bash
   .venv/bin/ruff check src/specify_cli/cli/commands/merge.py
   ```

5. Commit the fix:
   ```bash
   git add src/specify_cli/cli/commands/merge.py
   git commit -m "fix(merge): wire resolve_status_surface into done-marking loop

   Fixes #1726. _assert_merged_wps_reached_done now reads from the same
   surface as _mark_wp_merged_done writes to, eliminating the
   coordination-branch / primary-checkout divergence that caused
   post-merge WPs to remain in approved instead of reaching done."
   ```

---

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: allocated per `lanes.json` when `spec-kitty implement WP02` is run

**To implement this WP**:
```bash
spec-kitty agent action implement WP02 --agent claude
```

---

## Definition of Done

- [ ] All write sites and read sites in the merge path are identified and assessed
- [ ] Audit comment added to `merge.py` near the done-marking loop documenting all findings
- [ ] `_assert_merged_wps_reached_done` reads from `resolve_status_surface(...).parent` (or equivalent)
- [ ] When `coordination_branch` is set, both write and read resolve to the coordination worktree surface
- [ ] When `coordination_branch` is absent, both write and read resolve to the primary checkout surface
- [ ] All additional DIVERGENT sites from the audit are fixed or explicitly documented as not-applicable
- [ ] `pytest tests/specify_cli/cli/commands/test_merge.py` passes
- [ ] `pytest tests/merge/` passes
- [ ] `mypy --strict` passes on `merge.py` and `surface_resolver.py`
- [ ] Changes committed with a fix commit referencing issue #1726

---

## Risks

- **`merge.py` is large (~1900 lines)**: Ensure you read the full file for T001/T002, not just the done-marking loop section.
- **Module delegation**: Some read/write calls may be in utility functions that delegate further. Follow the full chain.
- **`get_wp_lane` expects directory, not file path**: Verify this in T009. Passing a file path where a directory is expected will cause a `CanonicalStatusNotFoundError`.
- **Existing mocks may assert on specific `feature_dir` values**: Some existing tests mock `get_wp_lane` with a specific `feature_dir` argument. After the fix, that argument may change (now a path inside `.worktrees/` for coord-branch missions). Update such mocks to match, but do not remove their assertion entirely.
- **`_mark_wp_merged_done` may already be correct** (Scenario A in T010): Do not add unnecessary complexity if the write path is already coordination-branch-aware. Verify before changing.
