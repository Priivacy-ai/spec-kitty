# Quickstart: Stable 3.2.0 P1 Release Confidence

Run from:

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260504-195327-4esVAN/spec-kitty
```

Mission handle:

```bash
stable-320-p1-release-confidence-01KQTPZC
```

## Baseline Verification

```bash
uv run spec-kitty agent mission check-prerequisites --mission stable-320-p1-release-confidence-01KQTPZC --json
uv run spec-kitty agent decision verify --mission stable-320-p1-release-confidence-01KQTPZC
uv run ruff check src tests
```

## Focused Test Starting Points

Adjust only with justification based on touched files:

```bash
uv run pytest tests/specify_cli/status tests/status tests/specify_cli/cli/commands/agent -q
uv run pytest tests/release tests/contract tests/review tests/post_merge -q
```

## Dependency Drift Verification Sketch

First verify current environment and lockfile:

```bash
uv run python - <<'PY'
from importlib.metadata import version
print("spec-kitty-events", version("spec-kitty-events"))
PY
rg -n 'name = "spec-kitty-events"|version = "4\\.1\\.0"' uv.lock
uv lock --check
```

If a guard is added or hardened, verify its passing and failing paths with focused tests under `tests/release/`.

## Local-Only Smoke Sketch

The exact smoke workspace should be temporary and outside committed mission artifacts. The lifecycle must cover:

```bash
uv run spec-kitty init --help
uv run spec-kitty specify --help
uv run spec-kitty plan --help
uv run spec-kitty tasks --help
uv run spec-kitty implement --help
uv run spec-kitty review --help
uv run spec-kitty merge --help
```

During WP03, replace the help-only skeleton with a fresh disposable workflow that performs setup, specify, plan, tasks, a bounded implement/review or fixture equivalent, merge, and PR-ready evidence without hosted auth, tracker, SaaS, or sync.

## SaaS-Enabled Smoke Rule

For every hosted auth, tracker, SaaS, or sync command on this computer, set:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 <spec-kitty command>
```

Examples:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty auth status
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty agent tracker status --help
```

During WP03, record exactly which hosted/sync commands were run and whether each one used `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

## Release Evidence Checklist

Record:

- #966 fix and regression commands.
- #848 current-gate closure evidence or new guard evidence.
- Local-only smoke result.
- SaaS-enabled smoke result.
- `uv run ruff check src tests` result.
- #971 included/deferred decision.
- P2/P3 deferrals from the spec.
