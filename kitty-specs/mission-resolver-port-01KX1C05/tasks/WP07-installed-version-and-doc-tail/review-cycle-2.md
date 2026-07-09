---
affected_files:
- path: tests/upgrade/migrations/test_m_2_1_4_marker_head_scan.py
  line_range: 88-107
cycle_number: 2
mission_slug: mission-resolver-port-01KX1C05
reproduction_command: PWHEADLESS=1 python -m pytest tests/upgrade/migrations/test_m_2_1_4_marker_head_scan.py -q
reviewed_at: '2026-07-08T20:11:22.254486+00:00'
reviewer_agent: claude:opus:reviewer-renata:reviewer
verdict: approved
wp_id: WP07
---

# WP07 Review — Cycle 2 (reviewer-renata)

**Verdict: APPROVED.**

Cycle 1 raised one blocking finding: the FR-010 `_CliStatusLike` injection branch in
`m_2_1_4_enforce_command_file_state.py` (`if cli_status is not None: return cast(str, ...)`)
had zero test coverage. The implementer added
`test_expected_marker_routes_injected_cli_status` to
`tests/upgrade/migrations/test_m_2_1_4_marker_head_scan.py`.

## Verification

- **Injection branch genuinely covered.** The test injects a `_FakeCliStatus`
  (`installed_version = "9.9.9-test"`) and asserts the marker equals
  `<!-- spec-kitty-command-version: 9.9.9-test -->` AND differs from the default-path
  marker. The asserted value can only come from the injected object.
- **Falsification proof (the real gate).** Deleting the injection branch makes the new
  test FAIL (falls back to the real `importlib.metadata` version `3.2.5`, not
  `9.9.9-test`) while the other 6 tests in the module stay green. This is a live FR-010
  assertion, not a synthetic fixture.
- **Test-only cycle-2 diff.** Between cycle-1 code commit and cycle-2 commit, no `src/`
  or `src/doctrine/` file changed — only the test file (+20 lines). All prior verified
  work (doctrine repoint T028, path guard T029, byte-exact migration default path) is
  untouched.
- `tests/upgrade/migrations/` → 7 passed in the module (206 passed dir-wide).
  Diff-scoped `ruff check` on the test file: exit 0.

## Anti-pattern checklist
1. Dead code — PASS. 2. Synthetic-fixture test — PASS (falsification-proven). 3. Silent
empty return — PASS. 4. FR coverage — PASS (FR-010 now asserted; FR-011 already passing).
5. Frozen surface — PASS. 6. Locked decision — PASS. 7. Shared-file ownership — PASS
(WP07 owns lane-g alone). 8. Production fragility — PASS.
