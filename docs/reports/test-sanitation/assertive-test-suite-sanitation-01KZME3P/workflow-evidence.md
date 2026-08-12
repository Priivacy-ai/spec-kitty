---
doc_status: active
updated: '2026-08-11'
---

# Test Sanitation Workflow Evidence

Evidence commit: `f527f8733b87d567957b771101405478309b8b70`  
Environment: macOS host; Python 3.11 mission .venv; integrated lane f527f8733; exact commands and raw receipt hashes below

## Repository and cross-repository gates

| Gate | Command | Result | Duration | Exit | Artifact |
|---|---|---|---:|---:|---|
| integrated full suite | PWHEADLESS=1 .venv/bin/pytest tests/ -n auto --dist loadfile -p no:cacheprovider --ignore=tests/sync/test_orphan_sweep.py | 35912 passed, 88 skipped, 4 xfailed | 1136.45 | 0 | sha256:b15d569a24468673fd808fe09aae01741c40b961c75dbe5885eb76865343e35c |
| serial orphan sweep | .venv/bin/pytest tests/sync/test_orphan_sweep.py | 9 passed | 15.01 | 0 | sha256:5356646b |
| Ruff | .venv/bin/ruff check . | All checks passed | 0 | 0 | sha256:82b3e6a6 |
| project mypy | .venv/bin/mypy src | 10 redundant-cast errors in six files identical to origin/main | 0 | 1 | sha256:55a71953 |
| contract | SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/pytest tests/contract/ -v | 292 passed, 3 skipped | 24.8 | 0 | sha256:ea496739 |
| architecture | .venv/bin/pytest tests/architectural/ -v | 869 passed, 2 skipped, 2 xfailed | 643.47 | 0 | sha256:69ecc698 |
| sibling E2E | SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest scenarios/ -v; then exact dependent-node retry after one daemon restart | original 3 passed, 1 xfailed, 2 failed; dependent_wp_planning_lane retry 1 passed; contract_drift_caught covered by narrow nested-wheel-build mission exception | 143.7 | 1 | sha256:d0bbcba0; retry sha256:2ef51a03e80449fb9f7e1b7ae3f1f18ca7c551208a0f20b8098026b6ddf1dce3 |

## Integrated platform evidence

| Platform | Workflow/job | Commit | Result | URL |
|---|---|---|---|---|
| Linux | doctor restart-daemon NFR-002 timing (blacksmith-4vcpu-ubuntu-2404) | ae7e4f2ee614894aae464f11ad933c23e3b3230a | IN_PROGRESS at evidence bind | https://github.com/Priivacy-ai/spec-kitty/actions/runs/31466089970/job/93699645715 |
| macOS | doctor restart-daemon NFR-002 timing (macos-latest) | ae7e4f2ee614894aae464f11ad933c23e3b3230a | IN_PROGRESS at evidence bind | https://github.com/Priivacy-ai/spec-kitty/actions/runs/31466089970/job/93699645753 |
| Windows | Windows critical (pipx, pytest -m windows_ci) | ae7e4f2ee614894aae464f11ad933c23e3b3230a | SUCCESS | https://github.com/Priivacy-ai/spec-kitty/actions/runs/31466090026/job/93699251138 |

## Fresh-clone starts

| Run | Commit | Publication/body proof | Result | Artifact |
|---:|---|---|---|---|
| 1 | WP02 integrated dependency | progress 0%-100%; JUnit tests=37455 | published one valid venv; no bootstrap cascade | raw/wp02-parallel-clean-starts.txt sha256:29e5808e45becb085f4771e6fb89880a328ebc00d918caa7e55ac03e2d937fd4 |
| 2 | WP02 integrated dependency | 3553 passed cases; controlled SIGINT after body-start oracle | published one valid venv; no bootstrap cascade | raw/wp02-parallel-clean-starts.txt sha256:29e5808e45becb085f4771e6fb89880a328ebc00d918caa7e55ac03e2d937fd4 |
| 3 | WP02 integrated dependency | JUnit tests=7499, 0 failures/errors; controlled SIGINT | published one valid venv; no bootstrap cascade | raw/wp02-parallel-clean-starts.txt sha256:29e5808e45becb085f4771e6fb89880a328ebc00d918caa7e55ac03e2d937fd4 |
