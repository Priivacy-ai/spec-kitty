# Mission Exception — Cross-Repository Nested Wheel Build

**Operator**: Robert Douglass (`@robertDouglass`)  
**Date**: 2026-08-11  
**Failing scenario**: `scenarios/contract_drift_caught.py::test_contract_drift_caught`

**Failing assertion**: the outer scenario asserted that stderr named `event_id`, `envelope`, or `999.0.0`; the nested run instead raised `subprocess.CalledProcessError` while executing `python -m build --wheel`.

## Failure detail

The scenario requires the intentionally drifted contract run to fail with a diagnostic naming `event_id`, `envelope`, or fake version `999.0.0`. Instead, its nested contract process stops earlier while setting up `test_wheel_does_not_contain_vendored_spec_kitty_events`:

```text
subprocess.CalledProcessError: Command '[.../venv/bin/python, -m, build,
--wheel, --outdir, .../wheel-build0]' returned non-zero exit status 1.
255 passed, 3 skipped, 1 error in 58.15s
```

The outer assertion then fails because this wheel-build error does not contain any of the three drift-diagnostic tokens.

## Environmental rationale

This scenario creates a nested Python 3.13 virtual environment and installs only `pytest>=8`, the fake events package, and an editable Spec Kitty checkout before invoking the repository's entire contract suite. The nested environment does not establish the repository's wheel-build test dependency surface before `python -m build` is invoked. The same integrated checkout's canonical contract gate passed independently (`292 passed, 3 skipped`), so the observed failure occurs in nested environment construction before the scenario reaches its intended drift oracle; it is not evidence that this sanitation mission weakened the contract.

This exception does not cover `scenarios/dependent_wp_planning_lane.py`, the SaaS scenario, any other sibling test, or a product-code failure.

## Reproduction command

```bash
cd spec-kitty-end-to-end-testing
SPEC_KITTY_REPO=/path/to/integrated/spec-kitty \
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
.venv/bin/pytest \
  scenarios/contract_drift_caught.py::test_contract_drift_caught -v
```

Observed receipt: `/tmp/wp08-sibling-e2e-final.log`, SHA-256 `d0bbcba0...`; JUnit `/tmp/wp08-sibling-e2e-final.xml`, SHA-256 `b39bfe8e...`.

## Follow-up

Robert Douglass (`@robertDouglass`) will retry this exact node after the sibling harness explicitly provisions its nested wheel-build dependency (for example, installs the repository's contract/build extras or `build` before running the nested contract suite). The retry must reach the intended drift assertion and name `event_id`, `envelope`, or `999.0.0`; a generic non-zero wheel-build setup error is not an acceptable pass.

Retry window: by 2026-08-18 and before mission merge or release, whichever is earlier.
