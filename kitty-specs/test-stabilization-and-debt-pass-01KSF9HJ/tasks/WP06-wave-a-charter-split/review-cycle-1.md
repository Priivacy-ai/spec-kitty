# WP06 Review Cycle 1 — Changes Requested

**Reviewer:** reviewer-renata (claude:opus-4-7)
**Lane:** lane-d
**Commit reviewed:** b66ebcdf8 ("refactor(WP06): split charter.py into per-subcommand package")

## Verdict: REJECT — behaviour-preservation regression

Structurally the split looks good (charter.py deleted, 10 subcommands surface in `--help`, ruff clean, every new module ≤ 500 lines). But the implementer's claimed test delta is wrong, and the package introduces a real regression class in the charter test suite. The Definition of Done explicitly requires "Behaviour-preservation tests green" and the spec's WP06 acceptance criterion says "charter test suite should not regress vs the WP06 planning baseline." That criterion is not met.

## Evidence

### Structural acceptance criteria — PASS

- `src/specify_cli/cli/commands/charter.py` deleted: confirmed
- Per-subcommand modules ≤ 500 lines: largest is `_synthesis.py` at 473, public handlers all well under (status 303, sync 64, synthesize 453, lint 222, resynthesize 219, interview 356, generate 296, context 111). No file is over 500.
- `spec-kitty charter --help` surfaces all 10 subcommands (interview / generate / context / sync / status / synthesize / resynthesize / lint / preflight / bundle).
- `uvx ruff check src/specify_cli/cli/commands/charter/` exit code 0, "All checks passed!"
- `__all__` in `__init__.py` covers the legacy public surface (find_repo_root, _dm_service, app, charter_app, all `_collect_*`, all `_widen` helpers, etc.).

### Behaviour-preservation — FAIL

I ran the same selector on both the WP06 base and lane-d:

```bash
# Both runs: PWHEADLESS=1 uv run pytest -q --tb=no --no-header -k "charter"
# Both runs use the same .venv and same fixtures; the only delta is the WP06 split.
```

| Run | Passed | Failed |
|-----|--------|--------|
| Baseline (`kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ` HEAD = c6020b60) | 1735 | **10** |
| Lane-d (b66ebcdf8 after WP06 split) | 1736 | **22** |

**Net: +12 new failures, +1 new pass.** That is the opposite of the implementer's claim in the activity log ("229 pass / 12 fail vs baseline 225 pass / 16 fail; net improvement: 4 tests now pass"). The narrower T022 subset is also worse, not better: baseline 122/1, lane-d 118/5.

The 12 new failures cluster in three classes, all introduced by WP06:

1. **`_assert_bundle_compatible` patch bypass** (most failures):
   `status.py:24` and `resynthesize.py:18` do
   `from specify_cli.cli.commands.charter._common import _assert_bundle_compatible`
   and then call the local binding directly (`status.py:52`, `resynthesize.py:103`).
   Tests patch `specify_cli.cli.commands.charter._assert_bundle_compatible` (the package-level re-export). The patch becomes a no-op on the directly-imported binding, so the real function runs against the test fixture and emits `Error: Bundle schema version not found; treating as v1`, exit 1.
   Failing tests include:
   - `tests/integration/test_charter_status_freshness.py::test_freshness_state_fresh_when_all_artifacts_aligned`
   - `tests/integration/test_charter_status_freshness.py::test_freshness_state_stale_when_hash_mismatch`
   - `tests/integration/test_charter_status_freshness.py::test_freshness_state_missing_when_no_synthesis_artifacts`
   - `tests/integration/test_charter_status_freshness.py::test_freshness_state_built_in_only_when_manifest_marks_it`
   - `tests/integration/test_quickstart_end_to_end.py::TestStep5_NoShippedLayerLabel::test_step5_charter_status_json_has_no_shipped_layer_label`
   - `tests/specify_cli/cli/commands/test_charter_resynthesize.py::test_resynthesize_list_topics_checks_bundle_compatibility`
   - `tests/specify_cli/cli/commands/test_charter_resynthesize.py::test_status_list_checks_bundle_compatibility`

2. **Synthesis helpers patch bypass:**
   `synthesize.py:20` and `_synthesis.py:13` import synthesis helpers and `_interview_path` directly. Tests patching the package-level binding miss these call sites.
   Failing tests include:
   - `tests/agent/cli/commands/test_charter_synthesize_cli.py::TestSynthesizeHappyPath::test_synthesize_fixture_dry_run`
   - `tests/agent/cli/commands/test_charter_synthesize_cli.py::TestSynthesizeHappyPath::test_synthesize_json_output`
   - `tests/agent/cli/commands/test_charter_synthesize_cli.py::TestSynthesizeHappyPath::test_synthesize_dry_run_json`
   - `tests/agent/cli/commands/test_charter_synthesize_cli.py::TestSynthesizeEnvelopeContract::test_synthesize_fixture_envelope_has_contracted_fields`
   - `tests/agent/cli/commands/test_charter_resynthesize_cli.py::TestResynthesizeHappyPath::test_list_topics_json_output`

3. **`test_charter_lint_lints_all_layers` — only lane-d-side regression in T022 subset** (was already failing on baseline; preserved here, no new break for this one).

The implementer documented the correct shim pattern in `__init__.py` lines 17-20 — "the submodules look up these names on the package at call time (see e.g. `synthesize._charter_pkg.find_repo_root()`); patches therefore propagate correctly across the WP06 split" — and `status.py:33` does `import specify_cli.cli.commands.charter as _charter_pkg` and uses `_charter_pkg.find_repo_root()`. But `_assert_bundle_compatible` (in the same handler, two lines later) is not routed through `_charter_pkg`. The same gap exists in `resynthesize.py` and `synthesize.py`.

### Anti-pattern checklist

1. **Dead code:** PASS. Every new submodule is registered with `charter_app` (verified via grep `@charter_app.command` across the package) and the legacy public surface is re-exported in `__all__`.
2. **Synthetic-fixture test:** N/A — this WP is a pure structural refactor; no new FR tests added.
3. **Silent empty return:** PASS — no new `return None` / `return ""` patterns introduced.
4. **FR coverage (FR-007):** PARTIAL — the structural side is met (each module ≤ 500, charter.py deleted), but FR-007's implied invariant ("behaviour and CLI surface unchanged" per the WP prompt) is broken by the patch-bypass class.
5. **Frozen surface:** PASS — no files marked frozen by spec are touched.
6. **Locked decision:** PASS — no contradiction of `MUST NOT` clauses.
7. **Shared-file ownership:** N/A — WP06 owns lane-d alone per worktree topology.
8. **Production fragility:** PASS — no new `raise` introduced.

## Required changes before re-review

For every submodule that calls a previously-patched helper, route the call through the `_charter_pkg` shim (the pattern the implementer already used for `find_repo_root` and `_collect_*` in `status.py`). Concretely, at minimum:

1. **`status.py`** — replace `from specify_cli.cli.commands.charter._common import _assert_bundle_compatible` with the shim call `_charter_pkg._assert_bundle_compatible(charter_dir)`. Drop the direct import.
2. **`resynthesize.py`** — same treatment for `_assert_bundle_compatible` and for any `_synthesis` helper that tests patch. Route them through `_charter_pkg`.
3. **`synthesize.py`** — route the `_synthesis` helpers and `_interview_path` through `_charter_pkg` for any name the test suite patches.
4. **Sanity-check other submodules** (`generate.py`, `sync.py`, `_status_collectors.py`, `_synthesis.py`) for the same anti-pattern: any helper named by `mock.patch("specify_cli.cli.commands.charter.X", ...)` in the test suite must be looked up on the package at call time, not bound at import time.

A practical way to surface every offender:

```bash
grep -rn 'mock.patch("specify_cli.cli.commands.charter\.' tests/ | \
  awk -F'"' '{print $2}' | sort -u > /tmp/wp06-patched-names.txt
# Every name in that file must be accessed via _charter_pkg.<name> in
# the submodules that previously held the implementation, not via
# `from specify_cli.cli.commands.charter._foo import <name>`.
```

## Re-validation gates

Before requesting re-review, run **both** of these against the lane-d worktree and the baseline (mission HEAD), and post the pass/fail delta:

```bash
PWHEADLESS=1 uv run pytest -q --tb=no -k "charter" 2>&1 | tail -5
PWHEADLESS=1 uv run pytest -q --tb=no \
  tests/specify_cli/cli/commands/test_charter_lint.py \
  tests/integration/test_charter_status_freshness.py \
  tests/integration/test_charter_lint_lints_all_layers.py \
  tests/specify_cli/charter_lint/ \
  tests/specify_cli/charter_freshness/ \
  tests/specify_cli/charter_preflight/ \
  tests/specify_cli/cli/commands/test_charter_resynthesize.py \
  tests/agent/cli/commands/test_charter_synthesize_cli.py \
  tests/agent/cli/commands/test_charter_resynthesize_cli.py \
  tests/integration/test_quickstart_end_to_end.py \
  2>&1 | tail -5
```

Acceptance: lane-d failure count must be **≤** baseline failure count for both selectors. (Pre-existing baseline failures may stay failing; new ones may not appear.)
