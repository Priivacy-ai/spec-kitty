# Migration: Shared Package Boundary Cutover

**Mission**: `shared-package-boundary-cutover-01KQ22DS`
**Released**: spec-kitty-cli 3.2.0 (unreleased at time of merge)
**Audience**: operators upgrading `spec-kitty-cli` from a pre-cutover version.

## What changed

`spec-kitty-cli` no longer depends on the `spec-kitty-runtime` PyPI package.
The runtime now lives inside `spec-kitty-cli` under
`src/specify_cli/next/_internal_runtime/`. Events and tracker remain
external PyPI dependencies, but the vendored events copy at
`src/specify_cli/spec_kitty_events/` was removed.

Concretely, after this release:

- `pip install spec-kitty-cli` is the only install step.
- `spec-kitty-events` and `spec-kitty-tracker` are pulled in transitively
  with compatibility ranges (`>=4.0.0,<5.0.0` and `>=0.4,<0.5`,
  respectively); exact versions live in `uv.lock`.
- `spec-kitty-runtime` is not installed and is not referenced.

## Action required

For most operators: nothing. Re-run
`pip install --upgrade spec-kitty-cli` (or
`uv tool upgrade spec-kitty-cli`) and the new release works without
`spec-kitty-runtime`. The retired package may remain installed in your
environment from a previous release; it is harmless and unused.

## Optional cleanup

```bash
pip uninstall spec-kitty-runtime
```

Or, if you used `uv`:

```bash
uv pip uninstall spec-kitty-runtime
```

If your environment was set up with a pre-cutover `constraints.txt`
override (`pip install -e ".[dev]" -c constraints.txt`), drop the
`-c constraints.txt` flag — the file no longer exists in the repo.

## Verification

After upgrading, confirm the cutover landed cleanly:

```bash
# 1. Confirm spec-kitty-runtime is not a dep:
pip show spec-kitty-runtime
# Expected: "WARNING: Package(s) not found: spec-kitty-runtime"

# 2. Confirm the CLI loads without spec-kitty-runtime in sys.modules:
python -c "
import sys, specify_cli
leaked = [k for k in sys.modules if 'spec_kitty_runtime' in k]
assert not leaked, f'spec_kitty_runtime imported: {leaked}'
print('OK: spec_kitty_runtime not imported')
"

# 3. Confirm spec-kitty next runs against your project:
spec-kitty next --agent <agent> --mission <mission>
```

The repo's CI runs an automated equivalent of this check on every PR
(`clean-install-verification` job in `.github/workflows/ci-quality.yml`).

## Developer workflows

If you work across `spec-kitty-cli` and `spec-kitty-events` /
`spec-kitty-tracker` simultaneously (e.g. testing an unreleased events
contract change), see
[`docs/development/local-overrides.md`](../development/local-overrides.md)
for editable-install patterns that don't pollute committed config.

## Why this happened

See [ADR 2026-04-25-1: Shared Package Boundary](../../architecture/2.x/adr/2026-04-25-1-shared-package-boundary.md)
for the full decision rationale and the alternatives considered.

## Supersedes

This mission supersedes [PR #779](https://github.com/Priivacy-ai/spec-kitty/pull/779),
which was rejected for preserving the hybrid model (runtime-shaped code in
the CLI tree alongside live `spec_kitty_runtime` production imports). The
work in this mission completes the cutover that PR #779 attempted.
