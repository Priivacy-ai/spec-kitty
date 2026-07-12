# Quickstart — Verifying CI Test-Topology Changes Locally

How a reviewer/implementer validates a WP without waiting on CI. Run from the repo root with `uv run`.

## 1. Reproduce a targeted job's selection
```bash
# What a job actually collects (used to freeze / diff the E3 baseline):
uv run pytest tests/next/ tests/specify_cli/next/ tests/runtime/ \
  -m 'not windows_ci and (git_repo or integration)' --collect-only -q > /tmp/next-nodeids.txt
```

## 2. Freeze / check the coverage-preservation baseline (GC-2b)
```bash
# Freeze (only when the selection legitimately changes; commit with provenance):
sort -u /tmp/next-nodeids.txt > tests/architectural/baselines/next-nodeids.txt
# Check parity after a topology change (must be empty):
diff <(sort -u tests/architectural/baselines/next-nodeids.txt) <(sort -u /tmp/next-nodeids.txt)
```

## 3. Run the guards (must be green)
```bash
uv run pytest \
  tests/architectural/test_arch_shard_marker_completeness.py \
  tests/architectural/test_next_shard_marker_completeness.py \
  tests/architectural/test_serial_port_preservation.py \
  tests/architectural/test_workflow_dist_lint.py \
  tests/architectural/test_gate_coverage.py -q
```

## 4. Time a job locally (evidence for E4 / NFR budgets)
```bash
# Parallel + durations (mirrors the FR-001 change):
PWHEADLESS=1 uv run pytest tests/next/ tests/specify_cli/next/ tests/runtime/ \
  -m 'not windows_ci and (git_repo or integration)' \
  -n auto --dist loadfile -p no:cacheprovider --durations=25 -q
# Real-port suite stays serial:
PWHEADLESS=1 uv run pytest tests/sync/test_orphan_sweep.py -n0 -q
```

## 5. Coverage-denominator checks (WP-J/K)
```bash
# Confirm the exclusion globs match the intended glue only:
grep -n 'sonar.coverage.exclusions' sonar-project.properties
# UI-e2e with coverage (WP-K):
PWHEADLESS=1 uv run pytest tests/ui/ --cov=src/specify_cli/dashboard --cov-report=xml -q
```

## Gotchas
- **Never `--dist load`** (bare) — always `--dist loadfile` (GC-4).
- **Real-port suites (E2) run `-n0` only** — never under `-n auto`.
- In a worktree/clone, bare `python`/`pytest` imports the primary `src` — always `uv run`.
- Regenerate the E3 baseline **deliberately** (a WP that changes selection), never to silence a red diff.
