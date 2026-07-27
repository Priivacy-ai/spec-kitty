# Mission Review Operator Exception

**Operator**: Robert Douglass, robert@spec-kitty.ai
**Date**: 2026-05-05
**Failing scenario**: `scenarios/contract_drift_caught.py::test_contract_drift_caught`
**Failing assertion**: `venv.create(venv_dir, with_pip=True, clear=True)`

The cross-repo E2E scenario failed before reaching the Spec Kitty code under
test. The nested temporary venv created by Python's stdlib `venv` module could
not run `ensurepip` because the uv-managed Python build on this workstation did
not provide `libpython3.11.dylib` or `libpython3.13.dylib` at the copied venv
path. This is an environmental Python-installation issue in the E2E runner, not
a Spec Kitty product defect.

The same run also reported
`scenarios/saas_sync_enabled.py::test_full_mission_with_sync` as XFAIL because
`https://spec-kitty-dev.fly.dev` was unreachable from this machine. That case
did not fail the pytest process, and WP03 separately documents the SaaS-enabled
lifecycle smoke limitation for this workstation.

## Reproduction command

```bash
SPEC_KITTY_REPO=/Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty \
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
UV_CACHE_DIR=/private/tmp/spec-kitty-e2e-uv-cache \
uv run --python 3.11 python -m pytest scenarios/ -v
```

## Follow-up

Retry the cross-repo E2E suite on a trusted runner with a system Python whose
stdlib `venv.create(..., with_pip=True)` can run `ensurepip`, or update
`scenarios/contract_drift_caught.py` to create the nested environment through
`uv venv` instead of stdlib `venv` on macOS uv-managed Python builds.
