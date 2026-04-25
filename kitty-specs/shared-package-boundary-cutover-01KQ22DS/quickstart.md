# Quickstart: Verify the Shared Package Boundary Cutover

**Mission**: `shared-package-boundary-cutover-01KQ22DS`

This document is the local-runnable verification recipe for the cutover. After
the mission merges, anyone can follow these steps to prove on their own
machine that the CLI's runtime is internal and that no `spec-kitty-runtime`
install is required.

---

## Prerequisites

- Python 3.11+ (the CLI's documented minimum).
- A clean shell with no `VIRTUAL_ENV` set.
- `git`, `uv` (preferred) or `pip` + `venv` (fallback).

---

## Step 1: Build the CLI wheel from source

```bash
cd /path/to/spec-kitty
uv build --wheel       # or: python -m build --wheel
ls dist/spec_kitty_cli-*.whl
```

You should see a single wheel file. Note its name — you will install it in a
fresh environment in Step 3.

## Step 2: Confirm the source tree has no vendored events

```bash
test ! -d src/specify_cli/spec_kitty_events && echo OK || echo "FAIL: vendored events tree still present"
```

Expected output: `OK`. If you see `FAIL`, the cutover regressed.

## Step 3: Create a clean, isolated venv with no `spec-kitty-runtime`

```bash
mktemp -d -t cutover-verify
cd "$(mktemp -d -t cutover-verify)"
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# Confirm no spec-kitty-* packages are present yet
pip list | grep -i 'spec-kitty' || echo "OK: clean venv"
```

## Step 4: Install the CLI from the wheel

```bash
pip install /path/to/spec-kitty/dist/spec_kitty_cli-*.whl
```

## Step 5: Verify `spec-kitty-runtime` is NOT installed as a transitive dep

```bash
pip list | grep -i 'spec-kitty-runtime' && echo "FAIL: runtime got pulled in" || echo "OK: no runtime"
```

Expected output: `OK: no runtime`. The grep MUST return zero matches.

## Step 6: Run `spec-kitty next` against a fixture mission

```bash
cp -r /path/to/spec-kitty/tests/fixtures/clean_install_fixture_mission ./fixture
cd fixture
git init -q
git add -A
git -c user.email=t@t -c user.name=t commit -q -m "fixture mission"

spec-kitty agent mission setup-plan --mission <fixture-handle> --json | jq .result
spec-kitty next --agent claude --mission <fixture-handle> --json | jq .result
```

Both calls should return `"success"`. The second call advances the mission's
runtime loop by one step and emits at least one `StatusEvent` in
`kitty-specs/<fixture-mission>/status.events.jsonl`.

## Step 7: Confirm CLI did not implicitly import `spec_kitty_runtime`

```bash
python -c "
import importlib, sys
import specify_cli  # triggers CLI module load
assert 'spec_kitty_runtime' not in sys.modules, sorted(k for k in sys.modules if 'runtime' in k.lower())
print('OK: spec_kitty_runtime not imported by CLI module load')
"
```

Expected output: `OK: spec_kitty_runtime not imported by CLI module load`.

## Step 8: Verify events / tracker are consumed only via public PyPI imports

```bash
python -c "
import spec_kitty_events  # PyPI public surface
import spec_kitty_tracker  # PyPI public surface
print('events:', spec_kitty_events.__file__)
print('tracker:', spec_kitty_tracker.__file__)
"
```

The printed paths should be inside `site-packages/` (the PyPI installs), not
inside the CLI's source tree. If either path points inside `specify_cli/`, the
cutover regressed.

---

## What this verifies (mapped to spec acceptance criteria)

| Step | Acceptance criterion |
|------|----------------------|
| 1 | A1, A6 — wheel build path remains operational |
| 2 | A4 (FR-003), NS-2 from data-model |
| 3 | Setup for A1 |
| 4 | A1, A6 |
| 5 | A1, A2, A3 — proves `spec-kitty-runtime` is not installed |
| 6 | A1, A6 — proves `spec-kitty next` works without runtime |
| 7 | A3 — proves no production import of `spec_kitty_runtime` |
| 8 | A4 — proves events / tracker consumed via PyPI |

---

## Troubleshooting

**`pip list` shows `spec-kitty-runtime` after Step 4.**

The CLI wheel pulled it as a transitive dependency. Inspect with
`pip show spec-kitty-runtime` to find which package required it. If it is
required by an unrelated package the user has installed locally, that is
fine — the assertion that matters is "the CLI does not require it." Re-run
Step 4 in a strictly isolated environment:

```bash
deactivate
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install /path/to/spec-kitty/dist/spec_kitty_cli-*.whl
pip list | grep -i 'spec-kitty-runtime'
```

If the assertion still fails, the cutover regressed. Open a P0 incident and
re-run the architectural test:

```bash
pytest tests/architectural/test_shared_package_boundary.py -v
```

**`spec-kitty next` fails with `ModuleNotFoundError: No module named 'spec_kitty_runtime'`.**

The internalized runtime is missing or `runtime_bridge.py` was not cut over.
This is a hard regression of the cutover. Re-run the architectural test and
file a P0.

**`spec-kitty next` fails with `ModuleNotFoundError: No module named 'specify_cli.spec_kitty_events'`.**

Some consumer was missed during WP04; an old import path is still live.
Re-run:

```bash
grep -rn "specify_cli.spec_kitty_events" src/
```

If anything matches in `src/`, that is the regression site.

---

## CI counterpart

The clean-install verification job in `.github/workflows/ci-quality.yml`
runs the equivalent of Steps 3..7 in a fresh container on every PR. If this
quickstart fails locally but the CI job is green, your local environment is
contaminated — the canonical answer is the CI job.
