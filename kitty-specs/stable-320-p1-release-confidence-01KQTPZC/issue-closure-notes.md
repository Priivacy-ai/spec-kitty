# Issue Closure Notes

## #966

Recommended update:

The task-board progress ambiguity is fixed by WP01. Human output now separates
done-only completion from weighted readiness, and JSON includes explicit
semantic fields while preserving the existing `progress_percentage` weighted
readiness value for compatibility.

Evidence:

- Commit `acc3a50f feat(WP01): clarify task status progress semantics`.
- Focused status/progress tests passed: 292 tests.
- Ruff passed for changed status/progress surfaces.
- Strict mypy passed for `src/specify_cli/status/progress.py`.
- Regression coverage includes approved-only, done-only, mixed approved/done,
  and empty states.

Closure recommendation: close #966 after the mission merge lands.

## #848

Recommended update:

The dependency drift risk is guarded by WP02. The release drift script now has
an installed-vs-lock mode, release workflows invoke it, and current installed
shared-package versions match `uv.lock`.

Evidence:

- Commit `44a181dc feat(WP02): add installed drift guard`.
- `spec-kitty-events` installed version `4.1.0` matches `uv.lock` `4.1.0`.
- `spec-kitty-tracker` installed version `0.4.3` matches `uv.lock` `0.4.3`.
- `uv lock --check` passed.
- `uv run python scripts/release/check_shared_package_drift.py --check-installed`
  passed.
- `uv run pytest tests/release -q` passed: 75 passed, 7 skipped.
- Mismatch remediation is `uv sync --extra test --extra lint`.

Closure recommendation: close #848 after the mission merge lands.
