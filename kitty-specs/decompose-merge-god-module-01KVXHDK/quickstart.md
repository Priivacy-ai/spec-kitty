# Quickstart — Verification Recipe

Behavior-preserving refactor of `src/specify_cli/cli/commands/merge.py`. Every WP and
the final acceptance run uses this recipe to prove byte-identity + complexity + gates.

## 0. Golden CLI characterization (capture FIRST, on the pre-refactor module — WP01)

```bash
# Captured against the fully registered app via Typer CliRunner.
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_merge_cli_golden.py -q
```

Pins: `merge --help`, every flag/default, hidden `--feature` alias, the
`--json`-without-`--dry-run` error string + exit 1, the dry-run JSON key set, and the
headline error/exit-code paths. This test must pass UNCHANGED after every seam move.

## 1. Complexity ceiling (NFR-001, FR-005)

```bash
# Every function in the shim and every merge/ seam module must be CC <= 15.
radon cc -s -n B src/specify_cli/cli/commands/merge.py src/specify_cli/merge/
ruff check src/specify_cli/cli/commands/merge.py src/specify_cli/merge/   # C901 aligned at 15
```

Expect: no function reported at CC > 15 (pre-refactor maxCC ~102 → ≤15).

## 2. Static gates (NFR-003, C-004)

```bash
ruff check src/specify_cli/ tests/
mypy --strict src/specify_cli/cli/commands/merge.py src/specify_cli/merge/
```

Expect: zero issues, zero new `# noqa` / `# type: ignore` / Sonar suppressions.

## 3. Per-seam focused coverage (NFR-002, FR-004)

```bash
PWHEADLESS=1 pytest tests/merge/ tests/specify_cli/cli/commands/test_merge*.py \
  --cov=src/specify_cli/merge --cov=src/specify_cli/cli/commands/merge.py \
  --cov-report=term-missing -q
```

Expect: ≥90% line coverage of new/moved code.

## 4. Full importer regression (FR-006)

```bash
# All ~41 importing test files + the 3 src consumers must pass with zero import edits.
PWHEADLESS=1 pytest tests/ -k "merge" -n auto --dist loadfile -p no:cacheprovider -q
PWHEADLESS=1 pytest tests/integration/test_merge_resume.py tests/sync/ -n0 -q   # daemon/real-port serial
```

Spot-check the src consumers import cleanly:

```bash
python -c "from specify_cli.cli.commands.merge import merge, path_is_under_worktrees, _mark_wp_merged_done"
python -c "from specify_cli.cli.commands import merge as m; print('__all__ stable:', bool(m.__all__))"
```

## 5. #1827 baseline-ordering regression (FR-007, INV-5/INV-6)

```bash
PWHEADLESS=1 pytest tests/specify_cli/merge/test_1827_baseline_regression.py -q
# plus the new phase-boundary regression test added in the executor WP:
PWHEADLESS=1 pytest tests/merge/ -k "phase_boundary or baseline_ordering" -q
```

Asserts: baseline record (post-target-merge / pre-bookkeeping-commit) → safe_commit →
baseline assert (post-commit) ordering, and restore-on-`BaselineMergeCommitError`.

## 6. Architectural one-way-import guard (C-006, INV-2)

```bash
# No merge/* seam imports cli.commands.merge.
! grep -rn "from specify_cli.cli.commands.merge\|import.*cli.commands.merge" src/specify_cli/merge/
PWHEADLESS=1 pytest tests/architectural/ -k "boundary" -q
```

## Acceptance gate (final WP)

All of steps 0–6 pass; `cli/commands/merge.py` is ~120 LOC (shim only) with the #2057
pointer comment; the golden test diff is empty.
