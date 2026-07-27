# WP07 Review — Cycle 1 (reviewer-renata)

**Verdict: CHANGES REQUESTED (1 blocking finding).**

The doctrine work (T028) and the guard (T029) are excellent and verified accurate
against code — the only gap is a missing test for the new FR-010 seam branch.

## Anti-pattern checklist
1. Dead code — **PASS** (no new module/function; optional params added to existing helpers, which have live callers).
2. Synthetic-fixture test — **PASS** (guard test invokes the real parser against the real matrix).
3. Silent empty return — **PASS** (no new silent returns; the `except` fallback is pre-existing and documented).
4. FR coverage — **FAIL for FR-010** (see Blocking Issue 1). FR-011 PASS.
5. Frozen surface — **PASS** (only the 3 owned files + shard-map registration).
6. Locked decision — **PASS**.
7. Shared-file ownership — **PASS** (WP07 owns lane-g alone; the 4 touched files are WP07-exclusive).
8. Production fragility — **PASS** (no new raises).

## Blocking Issue 1 — FR-010 injection branch is untested

`m_2_1_4_enforce_command_file_state.py` now has:

```python
if cli_status is not None:
    return cast(str, cli_status.installed_version)
```

This new branch — the entire observable deliverable of FR-010 ("route the version
read through the existing `_CliStatusLike` seam") — has **zero test coverage**.
`tests/upgrade/migrations/test_m_2_1_4_marker_head_scan.py` only calls
`_expected_version_marker()` with no argument (the default path). A grep of `tests/`
finds no test that injects a `_CliStatusLike` into `_get_cli_version` /
`_expected_version_marker`. If lines 72–78 are deleted, every test still passes —
so the FR-010 behavior is asserted nowhere.

This violates:
- The embedded Anti-pattern checklist item 4 ("every FR ... has at least one test
  assertion that references the behavior it names, not just a comment or frontmatter
  entry"). The default-path replay test would pass with the seam deleted.
- The charter/CLAUDE.md Sonar Standing Order: "Every new branch/helper needs tests
  in the same PR ... add narrow tests that execute the new branches/helpers directly."
- The mission's own convention — sibling seams (Resolver/Clock) carry injection
  tests (e.g. `tests/mission_runtime/test_placement_seam.py`); this seam does not.

### Fix (small — ~5 lines)
Add a focused test to `test_m_2_1_4_marker_head_scan.py` that injects a fake
`_CliStatusLike` and asserts the injected version flows into the marker, e.g.:

```python
class _FakeStatus:
    installed_version = "9.9.9-test"
    latest_version = None
    latest_source = "test"

def test_expected_marker_routes_injected_cli_status() -> None:
    marker = _expected_version_marker(_FakeStatus())
    assert "9.9.9-test" in marker
    assert marker != _expected_version_marker()  # proves the seam, not the default
```

That closes the FR-010 coverage gap and proves the routing actually works, without
touching the (correct, byte-for-byte preserved) default path.

## What passed verification (no action needed)

- **T028 / FR-011 doctrine repoint — accurate.** Verified both replacement surfaces
  exist and the rows describe them correctly: `core/git_ops.py::get_current_branch()`
  (line 136, runs `git branch --show-current`) and
  `lanes/branch_naming.py::parse_mission_slug_from_branch()` (line 778). The phantom
  `core/mission_detection.py::_detect_from_branch()` is gone; no inaccuracy was
  swapped in.
- **T029 guard — bites.** Ran `test_git_matrix_paths_resolve.py`: 2 passed, including
  `test_guard_bites_on_planted_phantom_path`. It covers every current `.py` path cell
  (all of which live in the guarded "Python-Executed Git Commands" section).
- **T027 migration replay unchanged.** `test_m_2_1_4_marker_head_scan.py`: 6 passed;
  the default no-injection path is byte-for-byte identical.
- Terminology guard: 3 passed. ruff: clean. mypy: 0 new findings (7 pre-existing
  baseline, unchanged; the `cast(str, ...)` correctly avoids a new no-any-return).
  No scope creep.

**Optional (non-blocking) nit:** the guard scopes to the "Python-Executed" section
only. That covers 100% of today's `.py` cells, but a future path added under
"Agent-Expected Git Commands" would escape it. Consider scanning all sections, or
add a one-line comment noting the intentional scope. Not required for approval.
