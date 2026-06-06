---
work_package_id: WP03
title: Regression Tests
dependencies:
- WP02
requirement_refs:
- C-004
- FR-007
- FR-008
- FR-009
- NFR-002
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-merge-done-surface-resolver-01KTDVHZ
base_commit: d958003666b1c76b4ccc59b0c5344350ddc457e6
created_at: '2026-06-06T08:22:00.494384+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
agent: claude
shell_pid: '39289'
history:
- date: '2026-06-06'
  event: created
  note: Initial task generation
agent_profile: python-pedro
authoritative_surface: tests/
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/test_merge.py
- tests/merge/test_merge_done_recording.py
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

Add regression tests that exercise both `_mark_wp_merged_done` and `_assert_merged_wps_reached_done` without mocking either function, against fixtures that include `coordination_branch` in the mission's `meta.json`. Cover planning-only and code-change merge paths (C-004, FR-007, FR-008).

These tests are the parity ratchet: once they pass, the class of bug documented in issue #1726 cannot silently recur on the merge path.

---

## Context

### The Test Gap (confirmed by five-paradigm investigation)

Across 11 merge-related test files:
- Zero fixtures set `coordination_branch`
- All tests that call both functions live monkeypatch either `emit_status_transition_transactional` or `get_wp_lane` — bypassing the surface routing that causes the bug

After WP02, the fix is in place. These tests prove it works and guard against future regression.

### Constraint (C-004 — BINDING)

**Tests must NOT mock `_mark_wp_merged_done` or `_assert_merged_wps_reached_done`.**

They may mock lower-level git operations, filesystem setup helpers, or unrelated orchestration. But the two done-marking functions must run their real code paths.

### Files to modify

- `tests/specify_cli/cli/commands/test_merge.py` — find the T015 section (live-function tests); add new fixtures and tests there
- `tests/merge/test_merge_done_recording.py` — add a `coordination_branch` variant

### Read first

Before writing tests, read the existing T015 tests in `test_merge.py` to understand:
- How fixtures are constructed (how `meta.json` is written, how worktrees are set up)
- What `_run_lane_based_merge_locked` expects as arguments
- How the test invokes the merge path

Also read `tests/merge/test_merge_done_recording.py` to understand its fixture shape.

---

## Subtask T014: Build the Coordination Branch Fixture

**Purpose**: Create a reusable pytest fixture that sets up a mission with `coordination_branch` in `meta.json` and a real coordination worktree stub on disk. This fixture is shared by T015, T016, and T017.

**What the fixture must provide**:
1. A `tmp_path`-based repo root with:
   - `kitty-specs/<slug>/meta.json` containing `coordination_branch`, `mission_id`, `mission_slug`, and other required fields
   - A coordination worktree at `.worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>/` (directory created)
   - An empty or pre-seeded `status.events.jsonl` in the coordination worktree (not the primary checkout)
2. The fixture does NOT pre-populate the primary checkout's `status.events.jsonl` — it should be absent or contain only pre-merge events (e.g., `approved` transition)

**Fixture shape**:
```python
@pytest.fixture
def coord_branch_mission(tmp_path):
    mission_slug = "test-mission-01KTDVHZ"
    mission_id = "01KTDVHZKGCHCW6HQ4V577PNES"
    mid8 = mission_id[:8]  # "01KTDVHZ"
    coord_branch = f"kitty/coord/{mission_slug}"
    
    # Write meta.json
    meta_dir = tmp_path / "kitty-specs" / mission_slug
    meta_dir.mkdir(parents=True)
    (meta_dir / "meta.json").write_text(json.dumps({
        "mission_id": mission_id,
        "mission_slug": mission_slug,
        "slug": mission_slug,
        "coordination_branch": coord_branch,
        # ... other required fields
    }))
    
    # Create coordination worktree stub
    coord_worktree = tmp_path / ".worktrees" / f"{mission_slug}-{mid8}-coord"
    coord_specs = coord_worktree / "kitty-specs" / mission_slug
    coord_specs.mkdir(parents=True)
    # status.events.jsonl starts empty (done event will be written by the fix)
    (coord_specs / "status.events.jsonl").write_text("")
    
    return {
        "repo_root": tmp_path,
        "mission_slug": mission_slug,
        "mission_id": mission_id,
        "mid8": mid8,
        "coord_branch": coord_branch,
        "coord_events_path": coord_specs / "status.events.jsonl",
        "primary_events_path": meta_dir / "status.events.jsonl",
    }
```

**Important**: The worktree path convention (`<slug>-<mid8>-coord`) must exactly match what `surface_resolver.py` produces (from WP01). If WP01 used a different convention, update the fixture to match.

---

## Subtask T015: Planning-Only Merge Test (no mocking)

**Purpose**: Prove that a planning-only WP merge with `coordination_branch` set exits successfully and the done event is readable on the coordination surface.

**Location**: `tests/specify_cli/cli/commands/test_merge.py`, T015 section

**Test**:
```python
def test_planning_only_merge_with_coord_branch_reaches_done(coord_branch_mission):
    """
    After _mark_wp_merged_done writes the done event to the coordination surface,
    _assert_merged_wps_reached_done must be able to read it back.
    
    This test must NOT mock _mark_wp_merged_done or _assert_merged_wps_reached_done.
    """
    repo_root = coord_branch_mission["repo_root"]
    mission_slug = coord_branch_mission["mission_slug"]
    wp_id = "WP01"
    
    # Seed the coordination surface with an 'approved' event (pre-merge state)
    # Use the real append_event or emit infrastructure (not a mock) to write the approved event
    # ...
    
    # Call _mark_wp_merged_done (real implementation, no mock)
    _mark_wp_merged_done(repo_root, mission_slug, wp_id, target_branch="main")
    
    # Call _assert_merged_wps_reached_done (real implementation, no mock)
    # This should NOT raise — the done event should be readable on the coordination surface
    _assert_merged_wps_reached_done(repo_root, mission_slug, [wp_id])
    
    # Verify the done event is on the coordination surface (not primary checkout)
    from specify_cli.coordination.surface_resolver import resolve_status_surface
    surface = resolve_status_surface(repo_root, mission_slug)
    events_text = surface.read_text()
    assert '"to_lane": "done"' in events_text or '"done"' in events_text
    
    # Verify primary checkout does NOT have the done event (pre-flush state)
    primary_events = coord_branch_mission["primary_events_path"]
    if primary_events.exists():
        assert '"done"' not in primary_events.read_text()
```

Adjust the seeding and assertion patterns to match the project's actual event format (read `status/models.py` for the event structure).

**FR-004 ordering-independence check**: After the main assertions pass, simulate post-teardown state by removing the coordination worktree stub directory (`coord_branch_mission["coord_events_path"].parent.parent.parent`) and calling `_assert_merged_wps_reached_done` again. It must not raise — the resolver (and the assertion) must be independent of worktree existence once the done event has been written to the coordination surface. This satisfies FR-004's structural guarantee.

---

## Subtask T016: Code-Change Merge Test (no mocking)

**Purpose**: Same as T015 but simulating a code-change WP (not planning-only). Confirms the fix covers both WP types.

**Location**: `tests/specify_cli/cli/commands/test_merge.py`, T015 section

The structure is identical to T015. The distinction is in the mission fixture — set up the mission as a code-change WP (e.g., `execution_mode: "code_change"` in meta, or a lane that represents code-change work). If `_mark_wp_merged_done` and `_assert_merged_wps_reached_done` do not branch on WP type, a second test with a different fixture is still valuable as a regression guard for future changes.

```python
def test_code_change_merge_with_coord_branch_reaches_done(coord_branch_mission):
    """Code-change WP variant — see test_planning_only_merge_with_coord_branch_reaches_done."""
    # Same structure as T015, but with execution_mode: code_change in the fixture
    ...
```

---

## Subtask T017: Coordination-Branch Test in test_merge_done_recording.py

**Purpose**: Add a `coordination_branch`-aware test to the recording test file, which already tests the done-marking loop at a lower level.

**Location**: `tests/merge/test_merge_done_recording.py`

**Steps**:
1. Read the existing tests to understand the fixture shape.
2. Add a new test (or parameterize an existing one) that sets `coordination_branch` in the mission fixture.
3. The test must NOT mock `_mark_wp_merged_done` or `_assert_merged_wps_reached_done`.
4. Assert that after `_mark_wp_merged_done`, `get_wp_lane` returns `Lane.DONE` when called with the surface-resolved path — not the primary-checkout path.

Example:
```python
def test_done_event_written_to_coordination_surface(coord_branch_mission):
    """
    Verifies that when coordination_branch is set, the done event is written to
    the coordination surface and is readable via get_wp_lane from that surface.
    """
    from specify_cli.coordination.surface_resolver import resolve_status_surface
    from specify_cli.status.lane_reader import get_wp_lane
    from specify_cli.status.models import Lane
    
    repo_root = coord_branch_mission["repo_root"]
    mission_slug = coord_branch_mission["mission_slug"]
    wp_id = "WP01"
    
    _mark_wp_merged_done(repo_root, mission_slug, wp_id, target_branch="main")
    
    surface_dir = resolve_status_surface(repo_root, mission_slug).parent
    assert Lane(get_wp_lane(surface_dir, wp_id)) == Lane.DONE
```

---

## Subtask T018: Coverage Check

**Purpose**: Verify that the new `surface_resolver.py` module (from WP01) reaches 90%+ coverage with the combined test suite.

**Steps**:
```bash
.venv/bin/pytest \
  tests/specify_cli/coordination/test_surface_resolver.py \
  tests/specify_cli/cli/commands/test_merge.py \
  tests/merge/test_merge_done_recording.py \
  --cov=src/specify_cli/coordination/surface_resolver \
  --cov-report=term-missing \
  -v
```

If coverage is below 90%, identify which lines are uncovered and either:
- Add a targeted test for the uncovered branch, or
- Verify the branch is unreachable (and document why)

Commit all new test files:
```bash
git add tests/specify_cli/cli/commands/test_merge.py
git add tests/merge/test_merge_done_recording.py
git commit -m "test(merge): add regression tests for coord-branch done-marking surface

Adds tests for planning-only and code-change merge with coordination_branch
set, without mocking _mark_wp_merged_done or _assert_merged_wps_reached_done.
Closes the test gap identified in issue #1726 (parity ratchet).

Relates-to: #1726, #1672"
```

---

## Subtask T018b: Dashboard Verification (FR-010)

**Purpose**: Confirm the user-visible output shows `Completed: 1 (100%)` after a successful merge, not `Completed: 0 (80.0%)`.

After all WP03 tests pass, verify the status against the test mission:
```bash
spec-kitty agent tasks status --feature merge-done-surface-resolver-01KTDVHZ
```

If the full merge flow cannot be replicated in the test environment, document the manual verification steps and confirm they were run. This step satisfies FR-010.

---

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: allocated per `lanes.json` when `spec-kitty implement WP03` is run

**To implement this WP**:
```bash
spec-kitty agent action implement WP03 --agent claude
```

---

## Definition of Done

- [ ] `coord_branch_mission` fixture (or equivalent) is defined and reusable
- [ ] T015 test: planning-only merge with `coordination_branch` set, no mocking of the two functions, passes
- [ ] T016 test: code-change merge with `coordination_branch` set, no mocking, passes
- [ ] T017 test: `test_merge_done_recording.py` has a `coordination_branch` variant, passes
- [ ] Neither `_mark_wp_merged_done` nor `_assert_merged_wps_reached_done` is mocked in any of the new tests
- [ ] 90%+ coverage on `src/specify_cli/coordination/surface_resolver.py`
- [ ] Changes committed with a test commit referencing issue #1726

---

## Risks

- **Seeding the coordination surface with pre-merge state**: `_mark_wp_merged_done` may check the current lane before writing `done`. You may need to seed the coordination surface with an `approved` event first. Use the real `append_event` or `emit_status_transition` to do this — do not write raw JSONL by hand, as the format must match exactly.
- **`_mark_wp_merged_done` may require git state**: If it calls `safe_commit` internally, the test needs a real or stubbed git repository. Check the existing T015 tests for how they handle git state.
- **Import paths**: `_mark_wp_merged_done` and `_assert_merged_wps_reached_done` are private functions in `merge.py`. Import them as `from specify_cli.cli.commands.merge import _mark_wp_merged_done, _assert_merged_wps_reached_done` — verify the import path by checking the existing T015 imports.
