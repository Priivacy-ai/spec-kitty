# Research: Mutmut Mutation Testing CI Integration
*Phase 0 output for [plan.md](plan.md)*

## Research Questions

1. What is the correct `pyproject.toml` configuration format for mutmut 3.x?
2. How does `mutmut export-cicd-stats` format its JSON output?
3. How should the mutation score floor be enforced (native vs. script)?
4. What is the correct sequence of mutmut commands to produce HTML + JSON reports?
5. What CI patterns already exist in `ci-quality.yml` for slow, push-only jobs?

---

## Finding 1 — mutmut 3.x pyproject.toml configuration

**Decision**: Use `[tool.mutmut]` section in `pyproject.toml`.

**Rationale**: mutmut 3.x supports configuration via `pyproject.toml` under
`[tool.mutmut]`. The 2.x setup.cfg approach (`[mutmut]`) still works but is
deprecated in favour of the standard PEP 517 approach. The project uses
`pyproject.toml` for all tooling config (ruff, mypy, pytest) so this is
consistent.

**Key settings for this project** (verified against mutmut 3.5.0 source):
```toml
[tool.mutmut]
paths_to_mutate = ["src/specify_cli/"]
tests_dir = ["tests/"]
pytest_add_cli_args = ["-x", "--timeout=30", "-q"]
# Exclude migrations (idempotent, hard to unit-test meaningfully via mutation)
do_not_mutate = [
    "src/specify_cli/upgrade/migrations/",
]
```

**Verified correct key names** (from mutmut `__main__.py` `load_config()`):
- `paths_to_mutate` — list of paths to mutate ✓
- `do_not_mutate` — exclusion patterns (not `exclude` or `exclude_patterns`) ✓
- `tests_dir` — list of test directories ✓
- `pytest_add_cli_args` — extra pytest flags (not `runner` — runner is always pytest in 3.x) ✓
- Note: `runner` is NOT a valid key in 3.x; pytest is hardcoded

**CLI note**: `mutmut run` takes `MUTANT_NAMES` (specific mutant IDs), not file paths.
To run specific files, configure `paths_to_mutate` in `pyproject.toml`.
Mutant names use module-path format: `specify_cli.status.transitions__mutmut_1`.

**Alternatives considered**:
- `setup.cfg` `[mutmut]` section — rejected (deprecated, inconsistent with project tooling style)
- Command-line flags only (no config file) — rejected (hard to reproduce locally vs. CI)

---

## Finding 2 — mutmut 3.x CLI command sequence (VERIFIED against 3.5.0)

**Decision**: Use the following sequence. Note corrections from original research.

```bash
# 1. Run mutation testing (writes metadata to mutants/ directory)
mutmut run

# 2. Export JSON stats — writes to mutants/mutmut-cicd-stats.json (NO --output flag)
mutmut export-cicd-stats
# Then copy to report location:
cp mutants/mutmut-cicd-stats.json out/reports/mutation/mutation-stats.json

# 3. HTML export: mutmut html does NOT exist in 3.5.0
# mutmut browse is an interactive TUI (not an HTML file generator)
# JSON report is the only machine-readable artifact in 3.5.0
```

**Corrections from original research**:
- `mutmut export-cicd-stats --output <path>` is WRONG — `--output` flag does not exist;
  output path is fixed: `mutants/mutmut-cicd-stats.json`
- `mutmut html` command does NOT exist in mutmut 3.5.0 (only `mutmut browse` exists,
  which is an interactive TUI browser)
- `mutmut run` exit codes: exits 0 regardless of surviving mutants (confirmed for 3.5.0)
- mutmut 3.x working directory: `mutants/` (not `mutmut.db` — SQLite is not used)
  Add `mutants/` to `.gitignore`

**JSON schema** (flat, no `summary` wrapper):
```json
{"killed": 0, "survived": 0, "total": 60711, "no_tests": 0, "skipped": 0,
 "suspicious": 0, "timeout": 0, "check_was_interrupted_by_user": 0, "segfault": 0}
```

**Alternatives considered**:
- Parsing `mutmut results` stdout — rejected (text parsing is fragile; JSON is canonical)

---

## Finding 3 — mutation-stats.json schema (VERIFIED against mutmut 3.5.0)

**Decision**: Parse `killed` and `survived` fields from the flat JSON output.

The actual JSON output from `mutmut export-cicd-stats` in 3.5.0 is **flat** (no `summary` wrapper):

```json
{
  "killed": 95,
  "survived": 18,
  "total": 120,
  "no_tests": 0,
  "skipped": 0,
  "suspicious": 4,
  "timeout": 3,
  "check_was_interrupted_by_user": 0,
  "segfault": 0
}
```

The floor check uses `killed / (killed + survived)` to avoid division-by-zero
when all mutants time out or are skipped.

**Zero-mutant edge case**: If `killed + survived == 0` (empty source scope or all
mutants timed out), emit a warning and exit 0.

**check_mutation_floor.py compatibility**: The script uses `data.get("summary", data)`
which falls back to the top-level dict when "summary" key is absent, making it
compatible with the actual flat schema.

---

## Finding 4 — Floor enforcement approach

**Decision**: Thin Python helper script `scripts/check_mutation_floor.py`

**Rationale**: mutmut 3.x has no built-in `--min-score` flag. Options were:

| Option | Pros | Cons |
|--------|------|------|
| Bash one-liner in CI YAML | No extra file | JSON parsing fragile in bash; hard to unit-test |
| Python helper script | Testable, readable, handles edge cases | One extra file in `scripts/` |
| Third-party wrapper (mutation-testing.io) | Rich reporting | New dependency, overkill |

The Python script is ~35 lines and handles:
- Missing/malformed JSON (fail with clear error)
- Zero-mutant case (warn + pass)
- Floor comparison with descriptive exit message
- `MUTATION_FLOOR` env var (integer 0–100, default 0)

---

## Finding 5 — Existing CI pattern for slow, push-only jobs

**Decision**: Model the new job on the existing `integration-smoke` and
`dashboard-tests` patterns already in `ci-quality.yml`.

**Pattern** (from `integration-smoke`):
```yaml
mutation-testing:
  runs-on: ubuntu-latest
  needs: unit-tests
  if: always() && (github.event_name == 'push' || (github.event_name == 'workflow_dispatch' && inputs.run_extended))
  timeout-minutes: 75
```

**Rationale**: Both `integration-smoke` and `dashboard-tests` use this exact
`if:` guard to skip on PRs while still running on push and `workflow_dispatch`.
`always()` ensures the job runs even if `unit-tests` had failures (matching
the existing pattern for parallelism). The timeout is increased to 75 min
(above the 60 min mutation run estimate) to give a safe buffer.

**Note on SonarCloud**: The `sonarcloud` job lists `mutation-testing` in its
`needs:` only if mutation reports should feed into SonarCloud. Since
SonarCloud already runs with `if: always()` and downloads existing coverage
reports, adding `mutation-testing` to `sonarcloud`'s `needs:` is optional
and deferred to FR-008 in WP02.

---

## Finding 6 — Priority squashing scope rationale

**Decision**: `status/`, `glossary/`, `merge/`, `core/` as first-campaign scope.

**Rationale**:

| Module | Why priority |
|--------|-------------|
| `status/` | 7-lane state machine; transition guards; incorrect transitions have real consequences |
| `glossary/` | Semantic integrity pipeline; wrong parsing or rendering corrupts all downstream consumers |
| `merge/` | Merge state persistence and preflight — errors here cause data loss or silent failures |
| `core/` | Core abstractions relied on by multiple subsystems |

**Deferred modules**: `cli/` (thin CLI glue, tested at integration level),
`upgrade/migrations/` (idempotent, hard to unit-test mutation independently),
`dashboard/` (UI, covered by Playwright), `missions/` (config loading, lower
correctness risk).
