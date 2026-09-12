---
affected_files: []
cycle_number: 2
mission_slug: annoying-bugs-sweep-01KYHQ9F
reproduction_command:
reviewed_at: '2026-07-27T14:26:40Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

# WP02 Review Cycle 1

**Verdict**: Changes requested

## Blocking Finding

**[HIGH] `src/specify_cli/cli/commands/review/_dead_code.py:101` - Mixed Python
layouts can still produce a false clean verdict.**

`src_python_paths or ...` selects only the `src/` Python paths whenever the
change set contains at least one such path. Any simultaneous supported Python
change outside `src/` is silently removed from `supported_paths`, so its added
public symbols are never extracted. The corpus is then restricted to `src/`,
and the gate can print `0 unreferenced public symbols` even though an
unreferenced public symbol was added elsewhere.

Independent reproduction:

1. Start from a valid Git baseline.
2. Add `src/marker.py` containing only `VALUE = 1`.
3. Add `package/dead.py` containing an unreferenced `def PublicDead(): ...`.
4. Commit both and call `scan_dead_code()` against the baseline.

Observed result:

```text
FINDINGS= []
OUTPUT= ✓  Dead-code scan: 0 unreferenced public symbols
```

This violates FR-015 and the supported-analysis contract requirement to obtain
the baseline-to-HEAD source set without assuming a `src/` root. It also violates
the clean-verdict rule because the selected denominator silently omits part of
the supported changed source set.

**Required repair**:

- Treat all supported, non-test changed Python paths as the discovery set when
  layouts are mixed, or classify a mixed layout as explicitly undeterminable.
  Never silently prefer the `src/` subset.
- Preserve the legacy `src/`-rooted corpus behavior when every supported changed
  Python path is under `src/`, as required by C-008.
- Add a fast regression containing both a `src/` Python change and a non-`src/`
  Python change. It must prove that the outside symbol is reported, or that the
  whole mixed layout is undeterminable, and must forbid the clean-zero output.
- Exercise the repaired case through the production review path as well as the
  extracted helper.

## Verification Performed

- `test_dead_code_baseline.py`: 11 passed.
- `test_review.py` plus diagnostic documentation tests: 34 passed.
- Focused Ruff checks: passed.
- Focused mypy checks: passed.
- The existing post-merge subprocess test reached the production CLI module
  with a PATH spy and observed Git only.
- Issue #2987 is assigned to `stijn-dejongh`; both recorded coordination
  comments exist and name this mission.
- Changed-file ownership is disjoint from other WPs. The evidence file records
  explicit authorization for `_report.py`, `test_review.py`, and
  `test_diagnostic_codes_documented.py`.

## Anti-Pattern Checklist

1. Dead code: PASS.
2. Synthetic-fixture test: PASS.
3. Silent empty return: PASS.
4. FR coverage: FAIL - FR-015 remains open for mixed Python layouts.
5. Frozen surface: PASS.
6. Locked decision: FAIL - mixed layouts contradict the no-source-root
   discovery contract.
7. Shared-file ownership: PASS, with recorded adjunct authorization.
8. Production fragility: PASS.
