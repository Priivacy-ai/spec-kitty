# Review Gates: Pre-PR / Pre-Review Checklist

This page documents the small set of hygiene steps a contributor should run
locally before requesting review or opening a PR. The goal is to catch
trivial environment drift here, so the actual review focuses on the
substance of the change and not on confusing failures unrelated to it.

## Environment hygiene before review/PR

Run the documented sync command from the repository root **before**
running the test gates:

```bash
uv sync --frozen
```

### Why

The CLI consumes `spec-kitty-events` and `spec-kitty-tracker` from PyPI.
Compatibility ranges live in `pyproject.toml`; **exact pins** live in
`uv.lock`. If your installed copy of either shared package drifts away
from `uv.lock` (for example, after an ad-hoc `pip install` against a
sibling checkout, or after switching branches without re-syncing), the
review-gate test suite can fail in ways that look like real defects but
are actually pure environment drift.

### What `uv sync --frozen` does

It installs the **exact resolved versions from `uv.lock`** into your
active virtualenv without re-resolving the dependency graph. This is
the cheapest possible "snap me back to the lockfile" operation:

- It does not modify `pyproject.toml`.
- It does not modify `uv.lock`.
- It does not contact the resolver -- only the package index for the
  pinned wheels.

### When to run it

Run `uv sync --frozen` any time:

- You pull `main` (or any branch with new lock changes).
- You switch branches.
- You change `pyproject.toml` or `uv.lock`.
- You temporarily installed an editable / sibling-checkout copy of
  `spec-kitty-events` or `spec-kitty-tracker` for cross-package work
  (see [`local-overrides.md`](local-overrides.md) for the dev workflow).
- The drift detector fails (see below).

### Automated detection

The architectural test
[`tests/architectural/test_uv_lock_pin_drift.py`](../../tests/architectural/test_uv_lock_pin_drift.py)
detects drift between `uv.lock` and the installed versions of the
governed shared packages (`spec-kitty-events`, `spec-kitty-tracker`).

If that test fails, the failure message names every offending package
and prints the literal command to fix it:

```
uv.lock vs installed-package drift detected for governed shared packages:
  - spec-kitty-events: locked=4.1.0, installed=4.0.7
Run the documented pre-review/pre-PR sync command from the repository root:
  uv sync --frozen
```

That is the **only** documented sync command for this purpose. Do not
substitute `uv pip sync`, `uv pip install`, or any other variant -- they
either re-resolve the graph or skip the lockfile entirely, both of which
defeat the point.

## See also

- [`local-overrides.md`](local-overrides.md) -- developer-only workflow
  for working across `spec-kitty-cli` / `spec-kitty-events` /
  `spec-kitty-tracker` checkouts without committing editable sources.
- [`tests/architectural/test_pyproject_shape.py`](../../tests/architectural/test_pyproject_shape.py)
  -- TOML-shape assertions for the shared-package boundary
  (compatibility ranges, no committed editable sources, etc.).
- The CI job `clean-install-verification` in
  `.github/workflows/ci-quality.yml` performs the equivalent
  fresh-venv check on every PR.
